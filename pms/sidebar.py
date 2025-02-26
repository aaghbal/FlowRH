"""
pms/sidebar.py
"""

from django.urls import reverse
from django.utils.translation import gettext_lazy as trans

from base.templatetags.basefilters import is_reportingmanager

MENU = trans("Performance")
IMG_SRC = "images/ui/pms.svg"


SUBMENUS = [
    {
        "menu": trans("Dashboard"),
        "redirect": reverse("dashboard-view"),
    },
    {
        "menu": trans("Objectives"),
        "redirect": reverse("objective-list-view"),
    },
    {
        "menu": trans("Enquête de performance"),
        "redirect": reverse("view-meetings"),
    },
    {
        "menu": trans("Points de Bonus des Employés"),
        "redirect": reverse("employee-bonus-point"),
    },
    {
        "menu": trans("Question Template"),
        "redirect": reverse("question-template-view"),
        "accessibility": "pms.sidebar.question_template_accessibility",
    },
]


def key_result_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("pms.view_keyresult") or is_reportingmanager(
        request.user
    )


def period_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("pms.view_period") or is_reportingmanager(request.user)


def question_template_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("pms.view_questiontemplate") or is_reportingmanager(
        request.user
    )
