from django import template
from django.template.defaultfilters import register

from leave.models import LeaveGeneralSetting
from employee.models import Employee

register = template.Library()


@register.filter(name="is_compensatory")
def is_compensatory(user):
    if LeaveGeneralSetting.objects.exists():
        return LeaveGeneralSetting.objects.first().compensatory_leave
    else:
        return False


@register.filter(name="is_reporting_manager_for")
def is_reporting_manager_for(user, leave_request):
    """
    Check if the current user is the reporting manager for the leave request employee.
    """
    try:
        current_employee = Employee.objects.get(employee_user_id=user)
        reporting_manager = leave_request.employee_id.employee_work_info.reporting_manager_id
        return current_employee == reporting_manager
    except:
        return False


@register.filter(name="get_manager_approval_status")
def get_manager_approval_status(leave_request):
    """
    Get the manager approval status for a leave request.
    """
    try:
        approvals = leave_request.multiple_approvals()
        if approvals and approvals.get("manager_approvals"):
            if approvals.get("manager_approved"):
                return "approved"
            elif approvals.get("manager_rejected"):
                return "rejected"
            else:
                return "pending"
        return "not_required"
    except:
        return "not_required"
