"""
department_heads.py

Read-only recruitment access for department heads ("Responsable département").

An employee with responsible departments can consult every recruitment whose
department is one of them (pipeline, candidates, interviews, dashboard), but
gets no write access from it: only the view permissions below let them in.
Rights coming from being a recruitment or stage manager are kept untouched.
"""

from django.db.models import Q

DEPARTMENT_HEAD_PERMS = {
    "recruitment.view_recruitment",
    "recruitment.view_candidate",
    "recruitment.view_stagenote",
    "recruitment.view_interviewschedule",
}


def responsible_department_ids(user):
    """
    Ids of the departments headed by the user, cached on the user object for
    the duration of the request.
    """
    if not getattr(user, "is_authenticated", False):
        return []
    if not hasattr(user, "_responsible_department_ids"):
        employee = getattr(user, "employee_get", None)
        user._responsible_department_ids = (
            list(employee.responsible_departments.values_list("id", flat=True))
            if employee
            else []
        )
    return user._responsible_department_ids


def is_department_head(user):
    """
    True when the user heads at least one department.
    """
    return bool(responsible_department_ids(user))


def is_manager(user):
    """
    True when the user is a recruitment manager or a stage manager.
    """
    employee = getattr(user, "employee_get", None)
    if employee is None:
        return False
    return employee.stage_set.exists() or employee.recruitment_set.exists()


def is_department_head_only(user):
    """
    Department head whose recruitment access comes only from that role
    (no global view permission, not a recruitment/stage manager).
    """
    return (
        is_department_head(user)
        and not user.has_perm("recruitment.view_recruitment")
        and not is_manager(user)
    )


def viewable_recruitments(user, queryset):
    """
    Restrict a Recruitment queryset to what the user may consult: everything
    with the global view permission, otherwise the recruitments they manage
    (recruitment or stage manager) and the ones of the departments they head.
    """
    if user.has_perm("recruitment.view_recruitment"):
        return queryset
    employee = getattr(user, "employee_get", None)
    condition = Q(department_id__in=responsible_department_ids(user))
    if employee is not None:
        condition |= Q(recruitment_managers=employee) | Q(
            stage_set__stage_managers=employee
        )
    return queryset.filter(condition).distinct()


def viewable_candidates(user, queryset):
    """
    Restrict a Candidate queryset to the candidates of the recruitments the
    user may consult, unless they hold the global candidate view permission.
    """
    from recruitment.models import Recruitment

    if user.has_perm("recruitment.view_candidate"):
        return queryset
    return queryset.filter(
        recruitment_id__in=viewable_recruitments(user, Recruitment.objects.all())
    )


def can_view_recruitment(user, recruitment):
    """
    Whether the user may consult this recruitment.
    """
    if recruitment is None:
        return False
    if user.has_perm("recruitment.view_recruitment"):
        return True
    if recruitment.department_id_id in responsible_department_ids(user):
        return True
    employee = getattr(user, "employee_get", None)
    if employee is None:
        return False
    return (
        recruitment.recruitment_managers.filter(id=employee.id).exists()
        or recruitment.stage_set.filter(stage_managers=employee).exists()
    )


def department_head_denied(user, recruitment):
    """
    True when a department head tries to open a recruitment outside of their
    scope. Users that are not department heads keep their previous behaviour.
    """
    return is_department_head(user) and not can_view_recruitment(user, recruitment)
