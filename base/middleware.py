"""
middleware.py
"""

from django.apps import apps
from django.db.models import Q
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect, render

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
