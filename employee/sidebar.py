"""
employee/sidebar.py

To set Horilla sidebar for employee
"""

from django.urls import reverse
from django.utils.translation import gettext_lazy as trans

from base.templatetags.basefilters import is_reportingmanager

MENU = trans("Employee")
IMG_SRC = "images/ui/employees.svg"

SUBMENUS = [
    {
        "menu": trans("Profile"),
        "redirect": reverse("employee-profile"),
        "accessibility": "employee.sidebar.profile_accessibility",
    },
    {
        "menu": trans("Employees"),
        "redirect": reverse("employee-view"),
        "accessibility": "employee.sidebar.employee_accessibility",
    },
    {
        "menu": trans("Demandes de documents"),
        "redirect": reverse("document-request-view"),
        "accessibility": "employee.sidebar.document_accessibility",
    },
    {
        "menu": trans("Shift Requests"),
        "redirect": reverse("shift-request-view"),
    },
    {
        "menu": trans("Work Type Requests"),
        "redirect": reverse("work-type-request-view"),
    },
    # {
    #     "menu": trans("Rotating Shift Assign"),
    #     "redirect": reverse("rotating-shift-assign"),
    #     "accessibility": "employee.sidebar.rotating_shift_accessibility",
    # },
    # {
    #     "menu": trans("Rotating Work Type Assign"),
    #     "redirect": reverse("rotating-work-type-assign"),
    #     "accessibility": "employee.sidebar.rotating_work_type_accessibility",
    # },
    {
        "menu": trans("Actions disciplinaires"),
        "redirect": reverse("disciplinary-actions"),
    },
    {
        "menu": trans("Règles internes"),
        "redirect": reverse("view-policies"),
    },
    {
        "menu": trans("Documents de l'entreprise"),
        "redirect": reverse("company-documents-view"),
    },
    {
        "menu": trans("Organigramme"),
        "redirect": reverse("organisation-chart"),
    },
]


def profile_accessibility(request, submenu, user_perms, *args, **kwargs):
    accessible = False
    try:
        accessible = request.session["selected_company"] == "all" or str(
            request.user.employee_get.employee_work_info.company_id.id
        ) == str(request.session["selected_company"])
    finally:
        return accessible


def document_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm(
        "horilla_documents.view_documentrequest"
    ) or is_reportingmanager(request.user)


def rotating_shift_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm(
        "base.view_rotatingshiftassign"
    ) or is_reportingmanager(request.user)


def rotating_work_type_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm(
        "base.view_rotatingworktypeassign"
    ) or is_reportingmanager(request.user)


def employee_accessibility(request, submenu, user_perms, *args, **kwargs):
    """
    Employee accessibility method
    """
    # only admins (employee view permission) see the employee list; reporting
    # managers and employees only have their own profile. Not based on the
    # accessibility settings: without rule, that feature is open to everyone.
    return request.user.has_perm("employee.view_employee")
