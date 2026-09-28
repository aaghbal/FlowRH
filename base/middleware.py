"""
middleware.py
"""

from django.apps import apps
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

from asset.models import AssetAssignment, AssetRequest
from attendance.models import (
    Attendance,
    AttendanceActivity,
    AttendanceOverTime,
    WorkRecords,
)
from base.context_processors import AllCompany
from base.horilla_company_manager import HorillaCompanyManager
from base.models import Company, ShiftRequest, WorkTypeRequest
from employee.models import (
    DisciplinaryAction,
    Employee,
    EmployeeBankDetails,
    EmployeeWorkInformation,
)
from helpdesk.models import Ticket
from horilla_documents.models import DocumentRequest
from leave.models import (
    AvailableLeave,
    CompensatoryLeaveRequest,
    LeaveAllocationRequest,
    LeaveRequest,
    RestrictLeave,
)
from offboarding.models import Offboarding
from payroll.models.models import (
    Contract,
    LoanAccount,
    Payslip,
    Reimbursement,
    WorkRecord,
)
from pms.models import EmployeeObjective
from recruitment.models import Candidate, Recruitment


class CompanyMiddleware:
    """
    company middleware class
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        company_id = None
        # Always use company ID 1 (automotiv) for all users
        if getattr(request, "user", False) and not request.user.is_anonymous:
            # Get company ID 1 (automotiv)
            company = Company.objects.filter(id=1).first()
            
            # Always set the selected company to ID 1
            if company:
                request.session["selected_company"] = company.id
                request.session["selected_company_instance"] = {
                    "company": company.company,
                    "icon": company.icon.url if company.icon else "",
                    "text": company.company,
                    "id": company.id,
                }
                company_id = company
            else:
                # Fallback in case company ID 1 doesn't exist (shouldn't happen)
                company = Company.objects.first()
                if company:
                    request.session["selected_company"] = company.id
                    request.session["selected_company_instance"] = {
                        "company": company.company,
                        "icon": company.icon.url if company.icon else "",
                        "text": company.company,
                        "id": company.id,
                    }
                    company_id = company

            # for testing here only get recruitment models
            app_labels = [
                "recruitment",
                "employee",
                "onboarding",
                "attendance",
                "leave",
                "payroll",
                "asset",
                "pms",
                "base",
                "helpdesk",
                "offboarding",
                "horilla_documents",
            ]
            app_models = [
                model
                for model in apps.get_models()
                if model._meta.app_label in app_labels
            ]

            company_models = [
                ShiftRequest,
                WorkTypeRequest,
                Employee,
                EmployeeWorkInformation,
                EmployeeBankDetails,
                DisciplinaryAction,
                Recruitment,
                Candidate,
                LeaveRequest,
                LeaveAllocationRequest,
                CompensatoryLeaveRequest,
                AssetRequest,
                AssetAssignment,
                AttendanceActivity,
                Attendance,
                WorkRecords,
                Contract,
                WorkRecord,
                LoanAccount,
                Reimbursement,
                DocumentRequest,
                Ticket,
                Offboarding,
                Payslip,
                AvailableLeave,
                RestrictLeave,
                AttendanceOverTime,
                EmployeeObjective,
            ]

            # Add company filter to every query
            if company_id:
                for (
                    model
                ) in app_models:  # Replace YourModels with the actual models you have

                    if model in company_models:
                        if getattr(model, "company_id", None):
                            model.add_to_class(
                                "company_filter", Q(company_id=company_id)
                            )
                        elif (
                            isinstance(model.objects, HorillaCompanyManager)
                            and model.objects.related_company_field
                        ):
                            model.add_to_class(
                                "company_filter",
                                Q(**{model.objects.related_company_field: company_id}),
                            )
                    else:
                        if getattr(model, "company_id", None):
                            model.add_to_class(
                                "company_filter",
                                Q(company_id=company_id) | Q(company_id__isnull=True),
                            )
                        elif (
                            isinstance(model.objects, HorillaCompanyManager)
                            and model.objects.related_company_field
                        ):
                            model.add_to_class(
                                "company_filter",
                                Q(**{model.objects.related_company_field: company_id})
                                | Q(
                                    **{
                                        f"{model.objects.related_company_field}__isnull": True
                                    }
                                ),
                            )

        response = self.get_response(request)
        return response


class RoleAccessMiddleware:
    """
    Refuses the pages a role holder was not granted.

    Runs as `process_view` rather than on the request: the URL has to be
    resolved before the page it belongs to can be worked out, and refusing
    there stops the view from running at all, so nothing is written on the way
    out of a POST.

    The decision itself lives in `base.role_access` -- it is shared with
    `horilla.config.sidebar`, which hides the same pages from the menu so a
    holder is not shown links that would bounce them back.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        from base.role_access import allowed_pages, can_access
        from base.role_pages import app_of_path, pages_for_route

        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None
        # nothing restricts this user: skip before touching the catalogue
        if allowed_pages(user) is None:
            return None

        pages = pages_for_route(
            app_of_path(request.path), request.resolver_match.url_name
        )
        if can_access(user, pages):
            return None
        return self.deny(request)

    @staticmethod
    def deny(request):
        """
        Refusal, in the shape the rest of Horilla already uses.

        htmx fragments get `decorator_404.html` so the refusal lands inside the
        panel that asked for it, like `horilla.decorators.permission_required`.
        A full page is sent back where it came from, falling back to the home
        page when the referrer is the refused URL itself, which would loop.
        """
        messages.info(request, _("Votre rôle ne donne pas accès à cette page."))
        if "HTTP_HX_REQUEST" in request.META:
            return render(request, "decorator_404.html")
        referrer = request.META.get("HTTP_REFERER")
        if referrer and request.path not in referrer:
            return redirect(referrer)
        return redirect("/")


# MIDDLEWARE TO CHECK IF EMPLOYEE IS NEW USER OR NOT
class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Exclude specific paths from redirection
        excluded_paths = ["/change-password", "/login", "/logout"]
        if request.path.rstrip("/") in excluded_paths:
            return self.get_response(request)

        # Check if employee is a new employee
        if hasattr(request, "user") and request.user.is_authenticated:
            if getattr(request.user, "is_new_employee", True):
                return redirect("change-password")  # Adjust to match your URL name

        return self.get_response(request)
