"""
company_documents.py

Views for the company documents library.
Admins upload documents (grouped by admin-managed categories),
every logged-in employee can view and download them.
"""

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

from employee.filters import CompanyDocumentFilter
from employee.forms import CompanyDocumentCategoryForm, CompanyDocumentForm
from employee.models import CompanyDocument, CompanyDocumentCategory
from horilla.decorators import (
    hx_request_required,
    login_required,
    permission_required,
)


def _grouped_documents(queryset):
    """
    Return a list of (category, documents) tuples ordered by category name.
    Categories with no matching document are skipped.
    """
    grouped = []
    for category in CompanyDocumentCategory.objects.all():
        docs = queryset.filter(category=category)
        if docs.exists():
            grouped.append((category, docs))
    return grouped


@login_required
def company_documents_view(request):
    """
    Main company documents library page (visible to all logged-in employees).
    """
    documents = CompanyDocument.objects.all()
    document_filter = CompanyDocumentFilter(request.GET, queryset=documents)
    grouped = _grouped_documents(document_filter.qs)
    return render(
        request,
        "company_documents/view_documents.html",
        {
            "grouped_documents": grouped,
            "categories": CompanyDocumentCategory.objects.all(),
            "f": document_filter,
            "total": document_filter.qs.count(),
        },
    )


@login_required
@hx_request_required
def search_company_documents(request):
    """
    Search / filter the company documents (returns the table partial).
    """
    document_filter = CompanyDocumentFilter(
        request.GET, queryset=CompanyDocument.objects.all()
    )
    grouped = _grouped_documents(document_filter.qs)
    return render(
        request,
        "company_documents/records.html",
        {
            "grouped_documents": grouped,
            "total": document_filter.qs.count(),
        },
    )


@login_required
@hx_request_required
@permission_required("employee.add_companydocument")
def create_company_document(request):
    """
    Upload / update a company document (admin only).
    """
    instance_id = request.GET.get("instance_id")
    instance = None
    if instance_id and instance_id.isdigit():
        instance = CompanyDocument.objects.filter(id=instance_id).first()
    form = CompanyDocumentForm(instance=instance)
    if request.method == "POST":
        form = CompanyDocumentForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, _("Document enregistré."))
            return HttpResponse("<script>window.location.reload()</script>")
    return render(request, "company_documents/form.html", {"form": form})


@login_required
@permission_required("employee.delete_companydocument")
def delete_company_document(request, doc_id):
    """
    Delete a company document (admin only).
    """
    document = CompanyDocument.objects.filter(id=doc_id).first()
    if document:
        document.delete()
        messages.success(request, _("Document supprimé."))
    else:
        messages.error(request, _("Document introuvable."))
    return redirect("company-documents-view")


@login_required
@hx_request_required
@permission_required("employee.add_companydocumentcategory")
def create_company_document_category(request):
    """
    Create a new company document category (admin only).
    """
    form = CompanyDocumentCategoryForm()
    if request.method == "POST":
        form = CompanyDocumentCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Catégorie ajoutée."))
            return HttpResponse("<script>window.location.reload()</script>")
    return render(request, "company_documents/category_form.html", {"form": form})
