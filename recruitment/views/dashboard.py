"""
dashboard.py

This module is used to write dashboard related views
"""

import datetime

from django.core import serializers
from django.db.models import Count, Prefetch, Q, Sum
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

from base.models import Department, JobPosition
from employee.models import EmployeeWorkInformation
from horilla.decorators import login_required
from recruitment.decorators import manager_can_enter
from recruitment.department_heads import (
    is_department_head_only,
    responsible_department_ids,
    viewable_recruitments,
)
from recruitment.models import Candidate, Recruitment, SkillZone, Stage


def _dashboard_scope(user):
    """
    Recruitments and candidates the dashboard reports on: all of them, or only
    the ones of their departments for a department head.
    """
    recruitments = Recruitment.objects.all()
    candidates = Candidate.objects.all()
    if is_department_head_only(user):
        recruitments = viewable_recruitments(user, recruitments)
        candidates = candidates.filter(recruitment_id__in=recruitments)
    return recruitments, candidates


@login_required
@manager_can_enter(perm="recruitment.view_recruitment")
def dashboard(request):
    """
    This method is used to render dashboard for recruitment module
    """
    recruitments, candidates = _dashboard_scope(request.user)
    # Single query per stat instead of loading all objects into Python
    total_candidates = candidates.count()
    total_hired_candidates = candidates.filter(hired=True).count()
    onboarding_count = candidates.filter(start_onboard=True).count()
    onboard_candidates = candidates.filter(hired=True, start_onboard=True)

    joining = EmployeeWorkInformation.objects.filter(
        date_joining__isnull=False
    ).exists()

    vacancy_chart = recruitments.filter(closed=False, is_event_based=False)
    dep_vacancy = 1 if vacancy_chart.exists() else 0

    # Job chart: 1 query instead of 5 × 217 = 1,085 queries
    jobs = JobPosition.objects.all()
    if is_department_head_only(request.user):
        jobs = jobs.filter(department_id__in=responsible_department_ids(request.user))
    stage_counts = (
        candidates.filter(job_position_id__in=jobs)
        .values("job_position_id", "stage_id__stage_type")
        .annotate(count=Count("id"))
    )
    stage_count_dict = {
        (row["job_position_id"], row["stage_id__stage_type"]): row["count"]
        for row in stage_counts
    }
    job_data = [
        (
            job.job_position,
            stage_count_dict.get((job.id, "initial"), 0),
            stage_count_dict.get((job.id, "test"), 0),
            stage_count_dict.get((job.id, "interview"), 0),
            stage_count_dict.get((job.id, "hired"), 0),
            stage_count_dict.get((job.id, "cancelled"), 0),
        )
        for job in jobs
    ]

    # Prefetch managers and stages to avoid N+1 on the recruitment loop
    active_candidates_qs = Candidate.objects.filter(is_active=True)
    stages_qs = Stage.objects.prefetch_related(
        Prefetch("candidate_set", queryset=active_candidates_qs)
    )
    recruitment_obj = recruitments.filter(closed=False).prefetch_related(
        "recruitment_managers",
        Prefetch("stage_set", queryset=stages_qs),
    )
    ongoing_recruitments = recruitment_obj.count()

    stage_chart_count = 0
    total_vacancy = 0
    recruitment_manager_mapping = {}

    for rec in recruitment_obj:
        if rec.vacancy is not None:
            total_vacancy += rec.vacancy

        recruitment_manager_mapping[rec.title] = [
            manager.get_full_name() for manager in rec.recruitment_managers.all()
        ]

        if not stage_chart_count:
            for stage in rec.stage_set.all():
                if stage.candidate_set.all():
                    stage_chart_count = 1
                    break

    conversion_ratio = 0
    hired_ratio = 0
    total_candidate_ratio = 0
    acceptance_ratio = 0
    if total_candidates:
        conversion_ratio = f"{(total_hired_candidates / total_candidates * 100):.1f}"
    if total_vacancy:
        hired_ratio = f"{(total_hired_candidates / total_vacancy * 100):.1f}"
        total_candidate_ratio = f"{(total_candidates / total_vacancy * 100):.1f}"
    if total_hired_candidates:
        acceptance_ratio = f"{(onboarding_count / total_hired_candidates * 100):.1f}"

    skill_zone = SkillZone.objects.filter(is_active=True)
    return render(
        request,
        "dashboard/dashboard.html",
        {
            "ongoing_recruitments": ongoing_recruitments,
            "total_candidate_ratio": total_candidate_ratio,
            "total_hired_candidates": total_hired_candidates,
            "conversion_ratio": conversion_ratio,
            "acceptance_ratio": acceptance_ratio,
            "onboard_candidates": onboard_candidates,
            "job_data": job_data,
            "total_vacancy": total_vacancy,
            "recruitment_manager_mapping": recruitment_manager_mapping,
            "hired_ratio": hired_ratio,
            "joining": joining,
            "dep_vacancy": dep_vacancy,
            "stage_chart_count": stage_chart_count,
            "onboarding_count": onboarding_count,
            "total_candidates": total_candidates,
            "skill_zone": skill_zone,
        },
    )


@login_required
@manager_can_enter(perm="recruitment.view_recruitment")
def dashboard_pipeline(request):
    """
    This method is used generate recruitment dataset for the dashboard
    """
    active_candidates_qs = Candidate.objects.filter(is_active=True)
    stages_qs = Stage.objects.prefetch_related(
        Prefetch("candidate_set", queryset=active_candidates_qs)
    )
    recruitments, _candidates = _dashboard_scope(request.user)
    recruitment_obj = recruitments.filter(closed=False).prefetch_related(
        Prefetch("stage_set", queryset=stages_qs),
        "candidate",
    )

    labels = [type[1] for type in Stage.stage_types]
    data_set = []

    for rec in recruitment_obj:
        if not rec.candidate.all():
            continue
        data = []
        for stage_type, _label in Stage.stage_types:
            count = sum(
                len(stage.candidate_set.all())
                for stage in rec.stage_set.all()
                if stage.stage_type == stage_type
            )
            data.append(count)
        data_set.append(
            {
                "label": rec.title
                if rec.title is not None
                else f"{rec.job_position_id} {rec.start_date}",
                "data": data,
            }
        )

    return JsonResponse(
        {
            "dataSet": data_set,
            "labels": labels,
            "message": _("Aucun enregistrement disponible actuellement."),
        }
    )


@login_required
@manager_can_enter(perm="recruitment.view_recruitment")
def dashboard_hiring(request):
    """
    This method is used generate employee joining status for the dashboard
    """
    selected_year = request.GET.get("id")

    # One aggregation query instead of loading all rows into Python
    employee_count_per_month = [0] * 12
    work_infos = EmployeeWorkInformation.objects.all()
    if is_department_head_only(request.user):
        work_infos = work_infos.filter(
            department_id__in=responsible_department_ids(request.user)
        )
    result = (
        work_infos.filter(
            date_joining__year=selected_year,
            date_joining__isnull=False,
        )
        .annotate(month=TruncMonth("date_joining"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )
    for row in result:
        employee_count_per_month[row["month"].month - 1] = row["count"]

    labels = [
        _("January"), _("February"), _("March"), _("April"),
        _("May"), _("June"), _("July"), _("August"),
        _("September"), _("October"), _("November"), _("December"),
    ]
    data_set = [
        {
            "label": _("Employees joined in %(year)s") % {"year": selected_year},
            "data": employee_count_per_month,
            "backgroundColor": "rgba(236, 131, 25)",
        }
    ]
    return JsonResponse({"dataSet": data_set, "labels": labels})


@login_required
@manager_can_enter(perm="recruitment.view_recruitment")
def dashboard_vacancy(request):
    """
    This method is used to generate a recruitment vacancy chart for the dashboard
    """
    recruitments, _candidates = _dashboard_scope(request.user)
    recruitment_obj = recruitments.filter(closed=False, is_event_based=False)
    department = Department.objects.all()

    # Aggregate vacancies per department in one query
    vacancy_by_dept = (
        recruitment_obj.filter(vacancy__isnull=False)
        .values("job_position_id__department_id", "id", "vacancy")
    )
    dept_vacancies = {}
    for row in vacancy_by_dept:
        dept_id = row["job_position_id__department_id"]
        dept_vacancies.setdefault(dept_id, []).append(int(row["vacancy"]))

    label = []
    data_set = [{"label": _("Openings"), "data": []}]

    for dep in department:
        vacancies = dept_vacancies.get(dep.id, [])
        count = recruitment_obj.filter(
            job_position_id__department_id=dep, vacancy__isnull=False
        ).count()
        for __ in range(count):
            label.append(dep.department)
        data_set[0]["data"].append([sum(vacancies)])

    return JsonResponse({"dataSet": data_set, "labels": label})


def get_open_position(request):
    """
    This is an ajax method to render the open position to the recruitment

    Returns:
        obj: it returns the list of job positions
    """
    rec_id = request.GET["recId"]
    recruitment_obj = Recruitment.objects.get(id=rec_id)
    queryset = recruitment_obj.open_positions.all()
    job_info = serializers.serialize("json", queryset)
    rec_info = serializers.serialize("json", [recruitment_obj])
    return JsonResponse({"openPositions": job_info, "recruitmentInfo": rec_info})


@login_required
@manager_can_enter(perm="recruitment.view_recruitment")
def candidate_status(request):
    """
    This method is used to generate a Candidate status chart for the dashboard
    """
    # 1 query instead of 5 separate COUNT queries
    statuses = ["not_sent", "sent", "accepted", "rejected", "joined"]
    labels = ["Non Envoyées", "Envoyées", "Acceptées", "Rejetées", "Rejoint"]

    counts = {
        row["offer_letter_status"]: row["count"]
        for row in _dashboard_scope(request.user)[1]
        .values("offer_letter_status")
        .annotate(
            count=Count("id")
        )
    }
    data_set = [
        {"label": labels[i], "data": counts.get(statuses[i], 0)}
        for i in range(len(labels))
    ]
    return JsonResponse({"dataSet": data_set, "labels": labels})
