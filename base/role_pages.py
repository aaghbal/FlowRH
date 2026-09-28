"""
base/role_pages.py

Catalogue of the pages a role can be granted access to.

A role is defined in the language users actually speak -- "Recrutement >
Candidats" -- instead of by picking from the 900+ raw Django permissions.
Each page therefore declares two things:

``perms``
    the `view_*` permissions the page is gated on. Granting a page hands them
    out, so the sidebar's `accessibility` callables and the `permission_required`
    decorators light up on their own. The matching add/change/delete
    permissions are derived from them, so a page granted at the "manage" level
    lets the holder act, not only look.

``routes``
    the URL names the page owns, as prefixes. Granting permissions can only
    ever *add* access, and most pages here carry no permission gate at all
    (`employee.policies` and `employee.disciplinary` are plain `@login_required`
    views reachable by anyone). `base.role_access` turns these routes around and
    uses them to *deny*: once an employee holds a role, every catalogued route
    outside their ticked pages is refused. A URL matched by no route stays open
    to everyone, exactly as it is today -- the catalogue is a deny list for the
    pages it knows, not a whitelist for the whole app.

Scope is limited to the modules actually in use: Recrutement, Intégration,
Congés, Employés, Performance. Adding a module back is a matter of adding its
entry here, nothing else changes.
"""

from functools import lru_cache

from django.utils.translation import gettext_lazy as _

# access levels a page can be granted at
VIEW = "view"
MANAGE = "manage"

ACCESS_LEVELS = [
    (VIEW, _("Consultation")),
    (MANAGE, _("Consultation et modification")),
]

# The home "Tableau de bord" is the one page no role can withhold: it is where
# a refusal sends the holder back to, so denying it would loop. Its tiles are
# pulled from the management views over htmx, and they are listed here so the
# home page shows numbers rather than a wall of refusals for a holder who was
# not granted the page behind the tile. Following a tile through still lands on
# the real page, and that one is refused.
EXEMPT_ROUTES = {
    "get-birthday",
    "total-employees-count",
    "joining-today-count",
    "joining-week-count",
    "not-in-yet",
    "not-out-yet",
    "dashboard-feedback-answer",
    "employee-leave",
    "leave-request-and-approve",
    "get-upcoming-holidays",
    "employee-get-mail-log",
}

# pages ticked for you when a role is created: the self-service pages every
# employee needs whatever else the role is for. An admin has to untick them
# deliberately to shut someone out of their own profile or their own leave.
DEFAULT_PAGES = [
    "personal.profile",
    "personal.my_leave",
    "personal.leave_allocation",
    "personal.news_feed",
]

# module key -> label, icon (reused from the sidebar), the python package its
# views live in, and its pages.
#   "perms"  -> view permissions that reveal the page in the menu
#   "routes" -> URL name prefixes the page owns; a prefix matches a name that
#               equals it or continues it at a "-" boundary, so "skill-zone"
#               covers "skill-zone-create" but "candidate" never covers
#               "candidates-view". A page may override the module's "app" when
#               its views live elsewhere.
PAGE_CATALOG = {
    "personal": {
        "label": _("Personnel"),
        "icon": "images/ui/employees.svg",
        "app": "employee",
        "pages": {
            "profile": {
                "label": _("Profil"),
                # no permission gates these: they are the holder's own records
                "perms": [],
                "routes": [
                    "employee-profile",
                    "employee-profile-bank-update",
                    "edit-profile",
                    "profile-edit-access",
                    "update-own-profile-image",
                    "remove-own-profile-image",
                    # the profile tabs, shared with the employee detail page so
                    # either grant opens them
                    "about-tab",
                    "note-tab",
                    "shift-tab",
                    "document-tab",
                    "bonus-points-tab",
                    "pms:performance-tab",
                    "leave:leave-tab",
                    "recruitment:employee-interview-tab",
                ],
            },
            "my_leave": {
                "label": _("Mes demandes de congé"),
                "perms": [],
                "app": "leave",
                "routes": ["user-request", "user-leave-filter"],
            },
            "leave_allocation": {
                "label": _("Demande d'attribution de congés"),
                "perms": [],
                "app": "leave",
                "routes": [
                    "leave-allocation-request",
                    "leave-allocation-approve",
                    "allocation-request-add-comment",
                    "allocation-request-view-comment",
                    "allocation-request-delete-comment",
                    "delete-allocation-comment-file",
                ],
            },
            "news_feed": {
                "label": _("Fil d'actualité"),
                "perms": [],
                # fil/urls.py is included at the root, so its paths fall to base
                "app": "base",
                "routes": [
                    "fil_actualite",
                    "create-poll",
                    "create-post",
                    "vote-poll",
                    "toggle_like",
                    "toggle_comment_like",
                    "get_likers",
                    "add_comment",
                    "edit_comment",
                    "delete_comment",
                    "update_post",
                    "delete_post",
                ],
            },
        },
    },
    "recruitment": {
        "label": _("Recrutement"),
        "icon": "images/ui/recruitment.svg",
        "app": "recruitment",
        "pages": {
            "dashboard": {
                "label": _("Tableau de bord recrutement"),
                "perms": ["recruitment.view_recruitment"],
                "routes": [
                    "recruitment-dashboard",
                    "dashboard-hiring",
                    "dashboard-vacancy",
                    "hired-candidate-chart",
                ],
            },
            "pipeline": {
                "label": _("Pipeline de recrutement"),
                "perms": ["recruitment.view_recruitment"],
                "routes": [
                    "pipeline",
                    "recruitment-pipeline",
                    "recruitment-close-pipeline",
                    "recruitment-reopen-pipeline",
                    "recruitment-delete-pipeline",
                    "recruitment-update-pipeline",
                    "recruitment-stage-get",
                    "stage-update-pipeline",
                    "stage-data",
                    "stage-search",
                    "stage-sequence-update",
                    "stage-title-update",
                    "get-stage-count",
                    "add-candidate-to-stage",
                    "candidate-stage-change",
                    "candidate-stage-component",
                    "candidate-stage-update",
                    "candidate-sequence-update",
                    "update-candidate-stage",
                    "update-candidate-sequence",
                    "update-candidate-stage-and-sequence",
                    "get-open-position",
                    "check-vaccancy",
                    "note",
                    "add-note",
                    "create-note",
                    "view-note",
                    "delete-stage-note-file",
                    "delete-individual-note-file",
                    "send-mail",
                    "send-acknowledgement",
                    "get-mail-log-rec",
                ],
            },
            "recruitments": {
                "label": _("Recrutements et postes ouverts"),
                "perms": ["recruitment.view_recruitment"],
                "routes": [
                    "recruitment",
                    "open-recruitments",
                    "remove-recruitment-manager",
                    "recruitment-application-survey",
                    "rec-filter-survey",
                ],
            },
            "candidates": {
                "label": _("Candidats"),
                "perms": ["recruitment.view_candidate"],
                "routes": [
                    "candidate",
                    "candidate-survey",
                    "rec-candidate-archive",
                    "rec-candidate-delete",
                    "rec-candidate-update",
                    "search-candidate",
                    "add-bulk-resume",
                    "view-bulk-resume",
                    "add-more-files",
                    "add-more-files-individual",
                    "delete-resume-file",
                    "delete-profile-image",
                    "matching-resumes",
                    "matching-resume-completion",
                    "resume-completion",
                    "to-skill-zone",
                    "create-candidate-rating",
                    "update-candidate-rating",
                    "self-tracking-feature",
                    "create-skills",
                    "delete-skills",
                    "skills-view",
                    "add-remove-options-field",
                ],
            },
            "interviews": {
                "label": _("Entretiens"),
                "perms": ["recruitment.view_interviewschedule"],
                "routes": [
                    "interview-view",
                    "interview-schedule",
                    "interview-filter-view",
                    "interview-employee-remove",
                    "create-interview-schedule",
                    "edit-interview",
                    "delete-interview",
                    "employee-interview-tab",
                ],
            },
            "surveys": {
                "label": _("Grilles de questionnaires"),
                "perms": ["recruitment.view_recruitmentsurvey"],
                "routes": [
                    "survey-template-create",
                    "survey-template-delete",
                    "survey-template-preview",
                    "survey-template-question-add",
                    "single-survey-view",
                    "update-question-order",
                    "candidate-survey",
                    "recruitment-survey-question-template-create",
                    "recruitment-survey-question-template-delete",
                    "recruitment-survey-question-template-duplicate",
                    "recruitment-survey-question-template-edit",
                    "recruitment-survey-question-template-view",
                ],
            },
            "stages": {
                "label": _("Étapes de recrutement"),
                "perms": ["recruitment.view_stage"],
                "routes": [
                    "rec-stage-create",
                    "rec-stage-delete",
                    "rec-stage-duplicate",
                    "rec-stage-update",
                    "rec-stage-view",
                    "rec-remove-stage-manager",
                ],
            },
            "skill_zone": {
                "label": _("Zone de compétences"),
                "perms": ["recruitment.view_skillzone"],
                "routes": ["skill-zone"],
            },
        },
    },
    "onboarding": {
        "label": _("Intégration"),
        "icon": "images/ui/rocket.svg",
        "app": "onboarding",
        "pages": {
            # onboarding/sidebar.py gates this page on "onboarding.view_onboarding",
            # a permission no model declares, so the menu entry only ever showed
            # for task managers. Grant the permissions that actually exist.
            "onboarding_view": {
                "label": _("Suivi d'intégration"),
                "perms": [
                    "onboarding.view_onboardingstage",
                    "onboarding.view_candidatestage",
                ],
                "routes": [
                    "onboarding-view",
                    "candidate",
                    "onboarding-send-mail",
                    "onboarding-stage-sequence-update",
                    "onboarding-candidate-sequence-update",
                    "onboarding-candidate-bulk-delete",
                    "stage-creation",
                    "stage-update",
                    "stage-delete",
                    "stage-name-update",
                    "get-status",
                    "update-joining",
                    "update-offer-letter-status",
                    "offer-letter-bulk-status-update",
                    "add-to-rejected-candidates",
                    "reject-probation",
                    "validate-probation",
                    "update-probotion-end",
                    "update-probotion-end-2",
                    "employee-creation",
                    "employee-bank-details",
                    "user-creation",
                    "email-send",
                ],
            },
            "onboarding_candidates": {
                "label": _("Candidats en intégration"),
                "perms": ["onboarding.view_candidatestage"],
                # "candidate" is shared with the tracking page above: the two
                # menu entries act on the same candidates
                "routes": [
                    "candidates-view",
                    "hired-candidates-view",
                    "kanban-view",
                    "candidate",
                ],
            },
            "onboarding_tasks": {
                "label": _("Tâches d'intégration"),
                "perms": ["onboarding.view_onboardingtask"],
                "routes": [
                    "task-creation",
                    "task-update",
                    "task-delete",
                    "task-report-onboarding",
                    "assign-task",
                    "change-task-status",
                    "candidate-task-update",
                    "candidate-task-bulk-update",
                    "candidate-tasks-status",
                ],
            },
        },
    },
    "employee": {
        "label": _("Employés"),
        "icon": "images/ui/employees.svg",
        "app": "employee",
        "pages": {
            "employees": {
                "label": _("Employés"),
                "perms": ["employee.view_employee"],
                # spelled out rather than a bare "employee" prefix, which would
                # swallow the holder's own profile pages
                "routes": [
                    "employee-view",
                    "employee-create-personal-info",
                    "employee-update-personal-info",
                    "employee-update",
                    "employee-delete",
                    "employee-archive",
                    "employee-bulk-archive",
                    "employee-bulk-delete",
                    "employee-bulk-mail",
                    "employee-bulk-update",
                    "save-employee-bulk-update",
                    "employee-export",
                    "employee-import",
                    "employee-filter-view",
                    "employee-widget-filter",
                    "employee-select",
                    "employee-select-filter",
                    "employee-tag",
                    "employee-note",
                    "employee-account-block-unblock",
                    "employee-user-group-assign-delete",
                    "employee-bank-details-view-create",
                    "employee-bank-details-view-update",
                    "employee-create-bank-details",
                    "employee-update-bank-details",
                    "add-employee-note",
                    "add-employee-note-post",
                    "delete-employee-note-file",
                    "add-more-files-employee",
                    "search-employee",
                    "replace-employee",
                    "send-mail-employee",
                    "send-mail-to-employee",
                    "export-data-employee",
                    "get-template-employee",
                    "update-profile-image",
                    "remove-profile-image",
                ],
            },
            "work_info": {
                "label": _("Informations professionnelles"),
                "perms": ["employee.view_employeeworkinformation"],
                "routes": [
                    "employee-work-info-view-create",
                    "employee-work-info-view-update",
                    "employee-create-work-info",
                    "employee-update-work-info",
                    "employee-work-information-delete",
                    "work-info-export",
                    "work-info-import",
                ],
            },
            "documents": {
                "label": _("Demandes de documents"),
                "perms": ["horilla_documents.view_documentrequest"],
                # only the management side: "document-create", "document-delete"
                # and "file-upload" also serve the holder's own document tab
                "routes": [
                    "document-request-view",
                    "document-request-create",
                    "document-request-update",
                    "document-request-delete",
                    "document-request-filter-view",
                    "document-approve",
                    "document-reject",
                    "document-bulk-approve",
                    "document-bulk-reject",
                ],
            },
            "disciplinary": {
                "label": _("Actions disciplinaires"),
                "perms": ["employee.view_disciplinaryaction"],
                "routes": [
                    "disciplinary-actions",
                    "disciplinary-filter-view",
                    "duplicate-disciplinary-actions",
                    "remove-employee-disciplinary-action",
                    "search-disciplinary",
                    "create-actions",
                    "update-actions",
                    "delete-actions",
                    "action-type-details",
                    "action-type-name",
                ],
            },
            "policies": {
                "label": _("Règles internes"),
                "perms": ["employee.view_policy"],
                "routes": [
                    "view-policies",
                    "search-policies",
                    "create-policy-folder",
                    "delete-policy-folder",
                    "upload-policy-documents",
                    "delete-policy-document",
                ],
            },
            # These two live in base/urls.py, which is mounted at the root --
            # except for their entry points, whose patterns spell out
            # "employee/..." literally (base/urls.py:577 and :653). So the page
            # is served by base and the menu link by employee, and both have to
            # be declared or the actions would stay open.
            "shift_requests": {
                "label": _("Gestion des horaires"),
                "perms": ["base.view_shiftrequest"],
                "app": "base",
                "routes": [
                    "shift-request",
                    "shift-allocation-request",
                    "shift-select",
                    "view-shift-comment",
                    "delete-shift-comment-file",
                    "add-remove-shift-fields",
                    "employee:shift-request-view",
                ],
            },
            "work_type_requests": {
                "label": _("Demandes de type de travail"),
                "perms": ["base.view_worktyperequest"],
                "app": "base",
                "routes": [
                    "work-type-request",
                    "work-type-select",
                    "view-work-type-comment",
                    "delete-work-type-comment-file",
                    "add-remove-work-type-fields",
                    "employee:work-type-request-view",
                ],
            },
            "company_documents": {
                "label": _("Documents de l'entreprise"),
                "perms": [],
                "routes": [
                    "company-documents-view",
                    "create-company-document",
                    "create-company-document-category",
                    "delete-company-document",
                    "search-company-documents",
                ],
            },
            "org_chart": {
                "label": _("Organigramme"),
                "perms": [],
                "routes": ["organisation-chart"],
            },
        },
    },
    "leave": {
        "label": _("Congés"),
        "icon": "images/ui/leave.svg",
        "app": "leave",
        "pages": {
            "dashboard": {
                "label": _("Tableau de bord congés"),
                "perms": [],
                # one menu entry, two pages: leave/sidebar.py:65 rewrites the
                # redirect to the employee dashboard for anyone without
                # "leave.view_leaverequest", so both have to belong to the page
                # or the entry stays reachable through its alternate URL
                "routes": [
                    "leave-dashboard",
                    "leave-employee-dashboard",
                    "dashboard-leave-requests",
                    "employee-leave-chart",
                    "department-leave-chart",
                    "leave-type-chart",
                    "leave-over-period",
                    "leave-period-info",
                ],
            },
            "requests": {
                "label": _("Demandes de congé"),
                "perms": ["leave.view_leaverequest"],
                # "user-request-*" is deliberately absent: those are the
                # holder's own leave requests, open to every employee
                "routes": [
                    "request-view",
                    "request-creation",
                    "request-update",
                    "request-delete",
                    "request-approve",
                    "request-cancel",
                    "request-filter",
                    "request-manager-approve",
                    "request-manager-reject",
                    "leave-request-create",
                    "leave-request-creation",
                    "leave-request-bulk-delete",
                    "leave-request-select",
                    "leave-request-select-filter",
                    "leave-request-add-comment",
                    "leave-request-view-comment",
                    "leave-request-delete-comment",
                    "leave-requests-bulk-approve",
                    "leave-requests-bulk-reject",
                    "leave-requests-info-export",
                    "delete-leave-comment-file",
                    "one-request-view",
                    "overall-leave",
                    "view-clashes",
                    "leave-cut-penalty",
                ],
            },
            "types": {
                "label": _("Types de congé"),
                "perms": ["leave.view_leavetype"],
                "routes": [
                    "type-view",
                    "type-creation",
                    "type-update",
                    "type-delete",
                    "type-filter",
                    "leave-type-individual-view",
                    "assign-leave-type-excel",
                    "assign-leave-type-info-import",
                ],
            },
            "assigned": {
                "label": _("Congés attribués"),
                "perms": ["leave.view_availableleave"],
                "routes": [
                    "assign",
                    "assign-view",
                    "assign-one",
                    "assign-filter",
                    "assign-delete",
                    "assigned-leave-select",
                    "assigned-leave-select-filter",
                    "assigned-leave-bulk-delete",
                    "assigned-leaves-info-export",
                    "available-leaves",
                    "available-leave-single-view",
                    "available-leave-update",
                ],
            },
            "holidays": {
                "label": _("Jours fériés et congés société"),
                "perms": ["base.view_holidays", "base.view_companyleaves"],
                # the holiday and company-leave views live in base/views.py
                "app": "base",
                "routes": [
                    "holiday",
                    "holidays",
                    "duplicate-holiday",
                    "company-leave",
                ],
            },
            "restrict": {
                "label": _("Restrictions de congé"),
                "perms": ["leave.view_restrictleave"],
                "routes": [
                    "restrict-view",
                    "restrict-creation",
                    "restrict-update",
                    "restrict-delete",
                    "restrict-filter",
                    "restrict-day-select",
                    "restrict-day-select-filter",
                    "restrict-days-bulk-delete",
                    "duplicate-restrict-leave",
                    "get-restrict-job-positions",
                    "employee-past-leave-restriction",
                ],
            },
            "compensatory": {
                "label": _("Congés compensatoires"),
                "perms": ["leave.view_compensatoryleaverequest"],
                "routes": [
                    "view-compensatory-leave",
                    "view-compensatory-leave-comment",
                    "create-compensatory-leave",
                    "create-compensatory-leave-comment",
                    "update-compensatory-leave",
                    "delete-compensatory-leave",
                    "approve-compensatory-leave",
                    "reject-compensatory-leave",
                    "filter-compensatory-leave",
                    "compensatory-leave-individual-view",
                    "compensatory-leave-settings-view",
                    "compensatory-request-delete-comment",
                    "delete-compensatory-comment-file",
                    "enable-compensatory-leave",
                ],
            },
        },
    },
    "pms": {
        "label": _("Performance"),
        "icon": "images/ui/pms.svg",
        "app": "pms",
        "pages": {
            "dashboard": {
                "label": _("Tableau de bord performance"),
                "perms": [],
                "routes": [
                    "dashboard-view",
                    "dashboard-objective-status",
                    "dashboard-feedback-status",
                    "dashbord-key-result-status",
                    "objective-dashboard-view",
                ],
            },
            "objectives": {
                "label": _("Objectifs"),
                "perms": ["pms.view_employeeobjective"],
                "routes": [
                    "objective",
                    "view-employee-objective",
                    "create-employee-objective",
                    "update-employee-objective",
                    "delete-employee-objective",
                    "archive-employee-objective",
                    "change-employee-objective-status",
                    "emp-objective-search",
                    "key-result",
                    "keyresult",
                    "kr-table-view",
                    "view-key-result",
                    "filter-key-result",
                    "create-key-result",
                    "update-key-result",
                    "delete-key-result",
                    "employee-key-result-creation",
                    "employee-key-result-update",
                    "employee-keyresult-update-status",
                    "delete-employee-keyresult",
                    "get-keyresult-data",
                ],
            },
            "feedback": {
                "label": _("Enquêtes de performance"),
                "perms": ["pms.view_feedback"],
                # "feedback-answer-*" stays open: it is how an employee answers
                # a feedback addressed to them
                "routes": [
                    "feedback-view",
                    "feedback-creation",
                    "feedback-creation-ajax",
                    "feedback-update",
                    "feedback-delete",
                    "feedback-archive",
                    "feedback-status",
                    "feedback-bulk-archive",
                    "feedback-bulk-delete",
                    "feedback-list-search",
                    "feedback-detailed-view",
                    "feedback-detailed-view-status",
                    "get-feedback-overview",
                    "add-anonymous-feedback",
                    "edit-anonymous-feedback",
                    "delete-anonymous-feedback",
                    "archive-anonymous-feedback",
                    "single-anonymous-feedback-view",
                ],
            },
            "question_template": {
                "label": _("Modèles de questions"),
                "perms": ["pms.view_questiontemplate"],
                "routes": [
                    "question-template",
                    "question-creation",
                    "question-update",
                    "question-delete",
                    "question-view",
                    "meeting-question-template-view",
                ],
            },
            "meetings": {
                # the sidebar entry labelled "Enquête de performance" points
                # here, at the meetings page -- not at pms.feedback
                "label": _("Réunions (Enquête de performance)"),
                "perms": ["pms.view_meetings"],
                "routes": [
                    "view-meetings",
                    "create-meeting",
                    "meeting-single-view",
                    "meetings-delete",
                    "archive-meeting",
                    "filter-meeting",
                    "meeting-answer-get",
                    "meeting-answer-post",
                    "meeting-answer-view",
                    "meeting-employee-remove",
                    "meeting-manager-remove",
                    "add-assignees",
                    "assignees-remove",
                    "get-collegues",
                ],
            },
            "bonus_points": {
                "label": _("Points de bonus des employés"),
                "perms": ["pms.view_employeebonuspoint"],
                "routes": [
                    "employee-bonus-point",
                    "bonus-point-setting",
                    "bonus-setting-form-values",
                    "create-bonus-point-setting",
                    "update-bonus-point-setting",
                    "delete-bonus-point-setting",
                    "update-isactive-bonuspoint-setting",
                    "create-employee-bonus-point",
                    "update-employee-bonus-point",
                    "delete-employee-bonus-point",
                    # the award/redeem actions live in employee/urls.py
                    "employee:add-bonus-points",
                    "employee:redeem-points",
                ],
            },
        },
    },
}


def page_key(module: str, page: str) -> str:
    """Stable identifier stored on a role, e.g. ``recruitment.candidates``."""
    return f"{module}.{page}"


def iter_pages():
    """Yield ``(key, module_key, module, page_key, page)`` for every page."""
    for module_key, module in PAGE_CATALOG.items():
        for pg_key, page in module["pages"].items():
            yield page_key(module_key, pg_key), module_key, module, pg_key, page


def get_page(key: str):
    """Return the page definition for ``key``, or None when it is unknown."""
    module_key, _, pg_key = key.partition(".")
    module = PAGE_CATALOG.get(module_key)
    if not module:
        return None
    return module["pages"].get(pg_key)


def permissions_for(key: str, level: str) -> list:
    """
    Django permission strings a page grants at ``level``.

    At the "view" level only the sidebar's own gating permissions are handed
    out. At "manage" the add/change/delete counterparts of the very same
    models come along, which is what makes the page actionable.
    """
    page = get_page(key)
    if not page:
        return []
    perms = list(page["perms"])
    if level != MANAGE:
        return perms
    for perm in page["perms"]:
        app_label, _sep, codename = perm.partition(".")
        model = codename.removeprefix("view_")
        perms += [
            f"{app_label}.add_{model}",
            f"{app_label}.change_{model}",
            f"{app_label}.delete_{model}",
        ]
    return perms


def catalog_with_selection(selected: dict = None):
    """
    The catalogue annotated with a role's current selection, ready to render.

    Returns a list of modules, each holding its pages with ``checked`` and
    ``level`` already resolved, so the template needs no dictionary lookup by
    variable key.
    """
    selected = selected or {}
    modules = []
    for module_key, module in PAGE_CATALOG.items():
        pages = []
        for pg_key, page in module["pages"].items():
            key = page_key(module_key, pg_key)
            pages.append(
                {
                    "key": key,
                    "label": page["label"],
                    "checked": key in selected,
                    "level": selected.get(key, VIEW),
                }
            )
        modules.append(
            {
                "key": module_key,
                "label": module["label"],
                "pages": pages,
                "selected_count": sum(1 for page in pages if page["checked"]),
            }
        )
    return modules


_ROUTE_INDEX = None


def _route_index():
    """``{app: {url name prefix: {page key, ...}}}``, built once."""
    global _ROUTE_INDEX
    if _ROUTE_INDEX is None:
        index = {}
        for key, module_key, module, _pg_key, page in iter_pages():
            default_app = page.get("app") or module.get("app") or module_key
            for route in page.get("routes", ()):
                # "app:prefix" for the handful of pages whose actions are
                # served by another app -- the profile tabs, the bonus points
                app, sep, prefix = route.partition(":")
                if not sep:
                    app, prefix = default_app, route
                index.setdefault(app, {}).setdefault(prefix, set()).add(key)
        _ROUTE_INDEX = index
    return _ROUTE_INDEX


def _prefix_matches(url_name: str, prefix: str) -> bool:
    """Match on "-" boundaries, so "candidate" never covers "candidates-view"."""
    return url_name == prefix or url_name.startswith(prefix + "-")


def pages_for_route(app: str, url_name: str) -> frozenset:
    """
    Page keys that own ``url_name`` within ``app``.

    The most specific prefix wins -- "recruitment-pipeline" resolves to the
    pipeline page, not to the recruitments page sitting on "recruitment" --
    and pages tied on that same prefix are returned together, so a route
    shared by two pages is reachable from either of them.

    An empty set means the URL is outside the catalogue and stays open.
    """
    if not app or not url_name or url_name in EXEMPT_ROUTES:
        return frozenset()
    longest = 0
    owners = set()
    for prefix, keys in _route_index().get(app, {}).items():
        if not _prefix_matches(url_name, prefix):
            continue
        if len(prefix) > longest:
            longest, owners = len(prefix), set(keys)
        elif len(prefix) == longest:
            owners |= keys
    return frozenset(owners)


# the prefix each app's urls.py is mounted at -- see the apps' `ready()` and
# horilla/urls.py. Anything else is served by base/urls.py at the root.
APP_URL_PREFIXES = frozenset(
    ["recruitment", "onboarding", "leave", "pms", "employee"]
)


def app_of_path(path: str) -> str:
    """
    The app a URL belongs to, read off its mount prefix.

    Not read off the view's ``__module__``: `horilla.decorators` wraps views
    without `functools.wraps`, so every decorated view reports itself as
    living in ``horilla.decorators``. The mount prefix is what actually tells
    ``recruitment``'s "candidate-view" apart from ``onboarding``'s.
    """
    segment = path.lstrip("/").partition("/")[0]
    return segment if segment in APP_URL_PREFIXES else "base"


@lru_cache(maxsize=512)
def pages_for_path(path: str) -> frozenset:
    """
    Page keys owning ``path``.

    A query string is stripped before resolving. `horilla.config.sidebar`
    strips it too, but an `accessibility` callable may append one afterwards
    (leave/sidebar.py:65, recruitment/sidebar.py:78), and an unresolvable path
    would silently come back as "not catalogued", which means open.

    Cached: the sidebar asks this of every menu entry on every request, and
    the URLconf a path resolves against does not change while the process runs.
    """
    from django.urls import Resolver404, resolve

    path = path.split("?")[0].split("#")[0]
    try:
        match = resolve(path)
    except Resolver404:
        return frozenset()
    return pages_for_route(app_of_path(path), match.url_name)


def describe(pages: dict):
    """Human readable summary of a role's pages, for the list view."""
    labels = []
    for module_key, module in PAGE_CATALOG.items():
        count = sum(
            1 for pg_key in module["pages"] if page_key(module_key, pg_key) in pages
        )
        if count:
            labels.append(f"{module['label']} ({count})")
    return labels
