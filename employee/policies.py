"""
policies.py

This module is used to write operation related to policies
"""

import datetime
import json
from datetime import timedelta
from urllib.parse import parse_qs

from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from base.methods import (
    filtersubordinates,
    get_key_instances,
    paginator_qry,
)
from employee.filters import DisciplinaryActionFilter
from employee.forms import (
    DisciplinaryActionForm,
    PolicyDocumentForm,
    PolicyFolderForm,
)
from employee.models import (
    Actiontype,
    DisciplinaryAction,
    Employee,
    PolicyDocument,
    PolicyFolder,
)
from horilla.decorators import hx_request_required, login_required, permission_required
from notifications.signals import notify


def _requesting_employee(request):
    """
    Employee linked to the logged in user, None when the user has no
    employee profile.
    """
    return Employee.objects.filter(employee_user_id=request.user).first()


def _can_see_everything(request):
    """
    Users holding the policy view permission browse every folder, the
    others only see the folders shared with them.
    """
    return request.user.has_perm("employee.view_policy")


def _accessible_folder(request, folder_id):
    """
    Return the folder matching `folder_id`, or None for the root level.
    A folder the user is not allowed to open is treated as the root.
    """
    if not folder_id or not str(folder_id).isdigit():
        return None
    folder = PolicyFolder.objects.filter(id=folder_id).first()
    if folder is None:
        return None
    if not _can_see_everything(request) and not folder.is_visible_for(
        _requesting_employee(request)
    ):
        return None
    return folder


def _visible_folders(request, folders):
    """
    Keep only the folders the requesting user is allowed to see.
    """
    if _can_see_everything(request):
        return list(folders)
    employee = _requesting_employee(request)
    return [folder for folder in folders if folder.is_visible_for(employee)]


def _explorer_context(request, folder):
    """
    Content of the folder currently opened: breadcrumb, sub folders and
    PDF documents. `folder` is None at the root of the library.
    """
    subfolders = PolicyFolder.objects.filter(parent=folder).order_by("name")
    documents = (
        PolicyDocument.objects.filter(folder=folder).order_by("title")
        if folder is not None
        else PolicyDocument.objects.none()
    )
    return {
        "folder": folder,
        "breadcrumb": folder.get_ancestors() if folder is not None else [],
        "subfolders": _visible_folders(request, subfolders),
        "documents": documents,
    }


def _folder_url(folder):
    """
    Url of the explorer opened on the given folder.
    """
    url = reverse("view-policies")
    if folder is not None:
        url = f"{url}?folder_id={folder.id}"
    return url


@login_required
def view_policies(request):
    """
    Render the policies explorer, at the root or inside a folder.
    """
    folder = _accessible_folder(request, request.GET.get("folder_id"))
    return render(request, "policies/view_policies.html", _explorer_context(request, folder))


@login_required
@hx_request_required
def search_policies(request):
    """
    Search folders and documents in the whole library. Without a search
    term the current folder content is returned back.
    """
    search = request.GET.get("search", "").strip()
    folder = _accessible_folder(request, request.GET.get("folder_id"))
    if not search:
        return render(request, "policies/explorer.html", _explorer_context(request, folder))
    folders = _visible_folders(
        request, PolicyFolder.objects.filter(name__icontains=search).order_by("name")
    )
    documents = PolicyDocument.objects.filter(title__icontains=search).order_by("title")
    if not _can_see_everything(request):
        employee = _requesting_employee(request)
        documents = [
            document
            for document in documents
            if document.folder.is_visible_for(employee)
        ]
    return render(
        request,
        "policies/search_results.html",
        {
            "folder": folder,
            "search": search,
            "found_folders": folders,
            "found_documents": documents,
        },
    )


@login_required
@hx_request_required
@permission_required("employee.add_policy")
def create_policy_folder(request):
    """
    Create a folder inside the opened folder, or rename/update an
    existing one when `instance_id` is given.
    """
    instance_id = request.GET.get("instance_id")
    instance = None
    if instance_id and str(instance_id).isdigit():
        instance = PolicyFolder.objects.filter(id=instance_id).first()
    parent = _accessible_folder(request, request.GET.get("parent_id"))
    form = PolicyFolderForm(instance=instance)
    if request.method == "POST":
        form = PolicyFolderForm(request.POST, instance=instance)
        if form.is_valid():
            folder = form.save(commit=False)
            if instance is None:
                folder.parent = parent
            folder.save()
            form.save_m2m()
            messages.success(request, _("Dossier enregistré."))
            return HttpResponse("<script>window.location.reload()</script>")
    return render(
        request,
        "policies/folder_form.html",
        {"form": form, "parent": parent, "folder": instance},
    )


@login_required
@permission_required("employee.delete_policy")
def delete_policy_folder(request, folder_id):
    """
    Delete a folder with everything it contains (sub folders and PDF).
    """
    folder = PolicyFolder.objects.filter(id=folder_id).first()
    if folder is None:
        messages.error(request, _("Dossier introuvable."))
        return redirect("view-policies")
    parent = folder.parent
    folder.delete()
    messages.success(request, _("Dossier supprimé."))
    return redirect(_folder_url(parent))


@login_required
@permission_required("employee.add_policy")
def upload_policy_documents(request):
    """
    Upload one or several PDF files inside the opened folder.
    """
    folder = _accessible_folder(request, request.GET.get("folder_id"))
    if folder is None:
        messages.error(request, _("Sélectionnez d'abord un dossier."))
        return redirect("view-policies")
    if request.method == "POST":
        uploaded = 0
        for file in request.FILES.getlist("attachment"):
            if not file.name.lower().endswith(".pdf"):
                messages.warning(
                    request,
                    _("%(name)s ignoré : seuls les fichiers PDF sont acceptés.")
                    % {"name": file.name},
                )
                continue
            PolicyDocument(
                folder=folder,
                title=file.name.rsplit(".", 1)[0],
                attachment=file,
            ).save()
            uploaded += 1
        if uploaded:
            messages.success(
                request,
                _("%(count)s document(s) ajouté(s).") % {"count": uploaded},
            )
        return redirect(_folder_url(folder))
    return render(
        request,
        "policies/document_form.html",
        {"form": PolicyDocumentForm(), "folder": folder},
    )


@login_required
@permission_required("employee.delete_policy")
def delete_policy_document(request, document_id):
    """
    Delete a PDF document from its folder.
    """
    document = PolicyDocument.objects.filter(id=document_id).first()
    if document is None:
        messages.error(request, _("Document introuvable."))
        return redirect("view-policies")
    folder = document.folder
    document.delete()
    messages.success(request, _("Document supprimé."))
    return redirect(_folder_url(folder))


@login_required
def disciplinary_actions(request):
    """
    This method is used to view all Disciplinaryaction
    """
    employee = Employee.objects.filter(employee_user_id=request.user).first()
    if request.user.has_perm("employee.view_disciplinaryaction"):
        dis_actions = DisciplinaryAction.objects.all()
    else:
        dis_actions = filtersubordinates(
            request, DisciplinaryAction.objects.all(), "base.add_disciplinaryaction"
        ).distinct()
        dis_actions = (
            dis_actions
            | DisciplinaryAction.objects.filter(employee_id=employee).distinct()
        )

    form = DisciplinaryActionFilter(request.GET, queryset=dis_actions)
    page_number = request.GET.get("page")
    page_obj = paginator_qry(form.qs, page_number)
    previous_data = request.GET.urlencode()

    return render(
        request,
        "disciplinary_actions/disciplinary_nav.html",
        {
            "data": page_obj,
            "pd": previous_data,
            "f": form,
        },
    )


def get_action_type(action_id):
    """
    This function is used to get the action type by the selection of title in the form.
    """
    action = Actiontype.objects.get(title=action_id["action"])
    return action.action_type


def get_action_type_delete(action_id):
    """
    This function is used to get the action type by the selection of title in the form.
    """
    action = Actiontype.objects.get(title=action_id)
    return action.action_type


def get_action_type(action_id):
    """
    This function is used to get the action type by the selection of title in the form.
    """
    action = Actiontype.objects.get(title=action_id["action"])
    return action.action_type


def get_action_type_delete(action_id):
    """
    This function is used to get the action type by the selection of title in the form.
    """
    action = Actiontype.objects.get(title=action_id)
    return action.action_type


def employee_account_block_unblock(emp_id, result):

    employee = get_object_or_404(Employee, id=emp_id)
    if not employee:
        return redirect(disciplinary_actions)
    user = get_object_or_404(User, id=employee.employee_user_id.id)
    if not user:
        return redirect(disciplinary_actions)
    user.is_active = result
    user.save()
    return HttpResponse("<script>window.location.reload()</script>")


@login_required
@hx_request_required
@permission_required("employee.add_disciplinaryaction")
def create_actions(request):
    """
    Method is used to create Disciplinaryaction
    """
    form = DisciplinaryActionForm()
    employees = []
    dynamic = (
        request.GET.get("dynamic") if request.GET.get("dynamic") != "None" else None
    )
    if request.GET:
        form = DisciplinaryActionForm(request.GET)

    if request.method == "POST":
        form = DisciplinaryActionForm(request.POST, request.FILES)
        if form.is_valid():
            employee_ids = form.cleaned_data["employee_id"]

            for employee in employee_ids:
                user = employee.employee_user_id
                employees.append(user)

            form.save()
            messages.success(request, _("Disciplinary action taken."))
            notify.send(
                request.user.employee_get,
                recipient=employees,
                verb="Disciplinary action is taken on you.",
                verb_ar="تم اتخاذ إجراء disziplinarisch ضدك.",
                verb_de="Disziplinarische Maßnahmen wurden gegen Sie ergriffen.",
                verb_es="Se ha tomado acción disciplinaria en tu contra.",
                verb_fr="Des mesures disciplinaires ont été prises à votre encontre.",
                redirect="/employee/disciplinary-actions/",
                icon="chatbox-ellipses",
            )
        dis = DisciplinaryAction.objects.all()
        if len(dis) == 1:
            return HttpResponse("<script>window.location.reload()</script>")

    return render(
        request, "disciplinary_actions/form.html", {"form": form, "dynamic": dynamic}
    )


@login_required
@hx_request_required
@permission_required("employee.change_disciplinaryaction")
def update_actions(request, action_id):
    """
    Method is used to update Disciplinaryaction
    """

    action = DisciplinaryAction.objects.get(id=action_id)
    form = DisciplinaryActionForm(instance=action)
    employees = []
    if request.method == "POST":
        form = DisciplinaryActionForm(request.POST, request.FILES, instance=action)

        if form.is_valid():
            employee_ids = form.cleaned_data["employee_id"]

            for employee in employee_ids:
                name = employee.employee_user_id
                employees.append(name)

            form.save()
            messages.success(request, _("Disciplinary action updated."))

            notify.send(
                request.user.employee_get,
                recipient=employees,
                verb="Disciplinary action is taken on you.",
                verb_ar="تم اتخاذ إجراء disziplinarisch ضدك.",
                verb_de="Disziplinarische Maßnahmen wurden gegen Sie ergriffen.",
                verb_es="Se ha tomado acción disciplinaria en tu contra.",
                verb_fr="Des mesures disciplinaires ont été prises à votre encontre.",
                redirect="/employee/disciplinary-actions/",
                icon="chatbox-ellipses",
            )
    return render(request, "disciplinary_actions/update_form.html", {"form": form})


@login_required
@hx_request_required
@permission_required("employee.change_disciplinaryaction")
def remove_employee_disciplinary_action(request, action_id, emp_id):
    dis_action = DisciplinaryAction.objects.get(id=action_id)
    employee = Employee.objects.get(id=emp_id)

    action_type = get_action_type_delete(dis_action.action)

    if action_type == "dismissal" or action_type == "suspension":
        emp = get_object_or_404(Employee, id=emp_id)
        user = get_object_or_404(User, id=emp.employee_user_id.id)
        if user.is_active:
            pass
        else:
            messages.warning(
                request, _("Employees login credentials will be unblocked.")
            )
            user.is_active = True
            user.save()

    dis_action.employee_id.remove(employee)

    employees = len(dis_action.employee_id.all())

    if employees == 0:
        dis_action.delete()

    messages.success(
        request, _("Employee removed from disciplinary action successfully.")
    )
    return redirect(f"/employee/disciplinary-filter-view?click_id={dis_action.id}")


@login_required
@hx_request_required
@permission_required("employee.delete_disciplinaryaction")
def delete_actions(request, action_id):
    """
    This method is used to delete Disciplinary action
    """

    dis = DisciplinaryAction.objects.get(id=action_id)

    action_type = get_action_type_delete(dis.action)

    for dis_emp in dis.employee_id.all():

        if action_type == "dismissal" or action_type == "suspension":
            employee = get_object_or_404(Employee, id=dis_emp.id)
            user = get_object_or_404(User, id=employee.employee_user_id.id)
            if user.is_active:
                pass
            else:
                messages.warning(
                    request, _("Employees login credentials will be unblocked.")
                )
                user.is_active = True
                user.save()

    dis.delete()
    messages.success(request, _("Disciplinary action deleted."))
    dis_actions = DisciplinaryAction.objects.all()

    if dis_actions.exists():
        return redirect(disciplinary_filter_view)
    return HttpResponse("<script>window.location.reload()</script>")


@login_required
def action_type_details(request):
    """
    This method is used to get the action type by the selection of title in the form.
    """
    action_id = request.POST["action_type"]
    action = Actiontype.objects.get(id=action_id)
    action_type = action.action_type
    return JsonResponse({"action_type": action_type})


@login_required
def action_type_name(request):
    """
    This method is used to get the action type name by the selection of type in the form.
    """
    action_type = request.POST["action_type"]
    return JsonResponse({"action_type": action_type})


@login_required
@hx_request_required
def disciplinary_filter_view(request):
    """
    This method is used to filter Disciplinary Action.
    """

    previous_data = request.GET.urlencode()
    action_id = request.GET.get("click_id") if request.GET.get("click_id") else None
    dis_filter = DisciplinaryActionFilter(request.GET).qs
    page_number = request.GET.get("page")
    page_obj = paginator_qry(dis_filter, page_number)
    data_dict = parse_qs(previous_data)
    get_key_instances(DisciplinaryAction, data_dict)
    return render(
        request,
        "disciplinary_actions/disciplinary_records.html",
        {
            "data": page_obj,
            "pd": previous_data,
            "filter_dict": data_dict,
            "dashboard": request.GET.get("dashboard"),
            "action_id": action_id,
        },
    )


@login_required
def search_disciplinary(request):
    """
    This method is used to search in Disciplinary Actions
    """
    disciplinary = DisciplinaryActionFilter(request.GET).qs
    return render(
        request,
        "disciplinary_actions/disciplinary_records.html",
        {
            "data": paginator_qry(disciplinary, request.GET.get("page")),
            "pd": request.GET.urlencode(),
        },
    )
