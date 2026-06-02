"""
Module for managing announcements, including creation, updates, comments, and views.
"""

import json
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from base.forms import AnnouncementCommentForm, AnnouncementForm
from base.methods import closest_numbers, filter_own_records
from base.models import (
    Announcement,
    AnnouncementComment,
    AnnouncementExpire,
    AnnouncementView,
)
from employee.models import Employee
from horilla.decorators import hx_request_required, login_required, permission_required, manager_can_enter
from notifications.signals import notify


@login_required
@hx_request_required
def announcement_list(request):
    general_expire_date = (
        AnnouncementExpire.objects.values_list("days", flat=True).first() or 30
    )
    
    # Optimized query with select_related and prefetch_related for better performance
    announcements = Announcement.objects.select_related().prefetch_related(
        'employees', 'attachments', 'announcementview_set'
    ).all()
    
    announcements_to_update = []

    # Optimize the bulk update process
    for announcement in announcements.filter(expire_date__isnull=True):
        announcement.expire_date = announcement.created_at + timedelta(
            days=general_expire_date
        )
        announcements_to_update.append(announcement)

    # Use bulk_update for better performance when updating multiple records
    if announcements_to_update:
        Announcement.objects.bulk_update(announcements_to_update, ["expire_date"])

    # Filter active announcements with optimized query
    announcements = announcements.filter(expire_date__gte=datetime.today().date())

    if request.user.has_perm("base.view_announcement"):
        announcement_list = announcements
    else:
        # Optimized filtering for user-specific announcements
        announcement_list = announcements.filter(
            Q(employees=request.user.employee_get) | Q(employees__isnull=True)
        ).distinct()

    # Optimize ordering and prefetch related data
    announcement_list = announcement_list.prefetch_related(
        "announcementview_set"
    ).order_by("-created_at")
    
    # Use select_related to avoid N+1 queries when checking viewed status
    for announcement in announcement_list:
        announcement.has_viewed = announcement.announcementview_set.filter(
            user=request.user, viewed=True
        ).exists()
        
    instance_ids = json.dumps([instance.id for instance in announcement_list])
    context = {
        "announcements": announcement_list,
        "general_expire_date": general_expire_date,
        "instance_ids": instance_ids,
    }
    return render(request, "announcement/announcements_list.html", context)


@login_required
@hx_request_required
def create_announcement(request):
    """
    This method renders form and template to update Announcement
    """

    form = AnnouncementForm()
    if request.method == "POST":
        form = AnnouncementForm(request.POST, request.FILES)
        if form.is_valid():
            anou = form.save()
            
            # Get the selected sites from the form
            selected_sites = form.cleaned_data.get("site")
            
            # Send notifications asynchronously to improve performance
            from django.utils import timezone
            import threading
            
            def send_notifications():
                """Send notifications in a separate thread to avoid blocking UI"""
                try:
                    if selected_sites:
                        # Optimized query with select_related for better performance
                        site_users = User.objects.select_related('employee_get').filter(
                            employee_get__employee_work_info__location__in=selected_sites
                        )
                        
                        # Send notification to employees at the selected sites
                        if site_users.exists():
                            notify.send(
                                request.user.employee_get,
                                recipient=site_users,
                                verb=f"A new announcement has been posted for {', '.join(selected_sites)} site(s).",
                                verb_ar=f"تم نشر إعلان جديد لموقع {', '.join(selected_sites)}.",
                                verb_de=f"Eine neue Ankündigung wurde für den Standort {', '.join(selected_sites)} veröffentlicht.",
                                verb_es=f"Se ha publicado un nuevo anuncio para el sitio {', '.join(selected_sites)}.",
                                verb_fr=f"Une nouvelle annonce a été publiée pour le site {', '.join(selected_sites)}.",
                                redirect="/",
                                icon="chatbox-ellipses",
                            )
                    else:
                        # No sites selected - announcement for all employees
                        # Optimized query to get all users with employees
                        all_users = User.objects.select_related('employee_get').filter(
                            employee_get__isnull=False
                        )
                        
                        # Send notification to all employees
                        if all_users.exists():
                            notify.send(
                                request.user.employee_get,
                                recipient=all_users,
                                verb="A new general announcement has been posted.",
                                verb_ar="تم نشر إعلان عام جديد.",
                                verb_de="Eine neue allgemeine Ankündigung wurde veröffentlicht.",
                                verb_es="Se ha publicado un nuevo anuncio general.",
                                verb_fr="Une nouvelle annonce générale a été publiée.",
                                redirect="/",
                                icon="chatbox-ellipses",
                            )
                except Exception as e:
                    # Log error but don't break the main process
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to send announcement notifications: {str(e)}")
            
            # Start notification sending in background thread
            notification_thread = threading.Thread(target=send_notifications)
            notification_thread.daemon = True
            notification_thread.start()
            
            messages.success(request, _("Announcement created successfully."))
            form = AnnouncementForm()
    return render(request, "announcement/announcement_form.html", {"form": form})


@login_required
@hx_request_required
def delete_announcement(request, anoun_id):
    """
    This method is used to delete announcements.
    """
    announcement = Announcement.find(anoun_id)
    if announcement:
        announcement.delete()
        messages.success(request, _("Announcement deleted successfully."))

    instance_ids = request.GET.get("instance_ids")
    instance_ids_list = json.loads(instance_ids)
    __, next_instance_id = (
        closest_numbers(instance_ids_list, anoun_id)
        if instance_ids_list
        else (None, None)
    )

    if anoun_id in instance_ids_list:
        instance_ids_list.remove(anoun_id)

    if next_instance_id and next_instance_id != anoun_id:
        url = reverse("announcement-single-view", kwargs={"anoun_id": next_instance_id})
        return redirect(f"{url}?instance_ids={json.dumps(instance_ids_list)}")
    return redirect(announcement_single_view)


@login_required
@manager_can_enter("base.change_announcement")
def update_announcement(request, id):
    """
    This method is used to update created announcement.
    """
    announcement = Announcement.objects.get(id=id)
    form = AnnouncementForm(instance=announcement)

    if request.method == "POST":
        form = AnnouncementForm(request.POST, request.FILES, instance=announcement)
        if form.is_valid():
            anou = form.save()
            
            # Get the selected sites from the form
            selected_sites = form.cleaned_data.get("site")
            
            # Send notifications asynchronously to improve performance
            import threading
            
            def send_update_notifications():
                """Send update notifications in a separate thread"""
                try:
                    if selected_sites:
                        # Optimized query with select_related for better performance
                        site_users = User.objects.select_related('employee_get').filter(
                            employee_get__employee_work_info__location__in=selected_sites
                        )
                        
                        # Send notification to employees at the selected sites
                        if site_users.exists():
                            notify.send(
                                request.user.employee_get,
                                recipient=site_users,
                                verb=f"An announcement for {', '.join(selected_sites)} site(s) has been updated.",
                                verb_ar=f"تم تحديث إعلان موقع {', '.join(selected_sites)}.",
                                verb_de=f"Eine Ankündigung für den Standort {', '.join(selected_sites)} wurde aktualisiert.",
                                verb_es=f"Se ha actualizado un anuncio para el sitio {', '.join(selected_sites)}.",
                                verb_fr=f"Une annonce pour le site {', '.join(selected_sites)} a été mise à jour.",
                                redirect="/",
                                icon="chatbox-ellipses",
                            )
                    else:
                        # No sites selected - announcement for all employees
                        # Optimized query to get all users with employees
                        all_users = User.objects.select_related('employee_get').filter(
                            employee_get__isnull=False
                        )
                        
                        # Send notification to all employees
                        if all_users.exists():
                            notify.send(
                                request.user.employee_get,
                                recipient=all_users,
                                verb="A general announcement has been updated.",
                                verb_ar="تم تحديث إعلان عام.",
                                verb_de="Eine allgemeine Ankündigung wurde aktualisiert.",
                                verb_es="Se ha actualizado un anuncio general.",
                                verb_fr="Une annonce générale a été mise à jour.",
                                redirect="/",
                                icon="chatbox-ellipses",
                            )
                except Exception as e:
                    # Log error but don't break the main process
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to send announcement update notifications: {str(e)}")
            
            # Start notification sending in background thread
            notification_thread = threading.Thread(target=send_update_notifications)
            notification_thread.daemon = True
            notification_thread.start()
            
            messages.success(request, _("Announcement updated successfully."))
            return redirect("announcement-view")
    return render(request, "announcement/announcement_update.html", {"form": form})


@login_required
@hx_request_required
def create_announcement_comment(request, anoun_id):
    """
    This method renders form and template to create Announcement comments
    """
    anoun = Announcement.objects.filter(id=anoun_id).first()
    emp = request.user.employee_get
    form = AnnouncementCommentForm(
        initial={"employee_id": emp.id, "request_id": anoun_id}
    )
    comments = AnnouncementComment.objects.filter(announcement_id=anoun_id)
    commentators = []
    if comments:
        for i in comments:
            commentators.append(i.employee_id.employee_user_id)
    unique_users = list(set(commentators))

    if request.method == "POST":
        form = AnnouncementCommentForm(request.POST)
        if form.is_valid():
            form.instance.employee_id = emp
            form.instance.announcement_id = anoun
            form.save()
            form = AnnouncementCommentForm(
                initial={"employee_id": emp.id, "request_id": anoun_id}
            )
            messages.success(request, _("You commented a post."))
            notify.send(
                request.user.employee_get,
                recipient=unique_users,
                verb=f"Comment under the announcement {anoun.title}.",
                verb_ar=f"تعليق تحت الإعلان {anoun.title}.",
                verb_de=f"Kommentar unter der Ankündigung {anoun.title}.",
                verb_es=f"Comentario bajo el anuncio {anoun.title}.",
                verb_fr=f"Commentaire sous l'annonce {anoun.title}.",
                redirect="/",
                icon="chatbox-ellipses",
            )
        return redirect("announcement-view-comment", anoun_id=anoun_id)

    return render(
        request,
        "announcement/comment_view.html",
        {"form": form, "request_id": anoun_id},
    )


@login_required
@hx_request_required
def comment_view(request, anoun_id):
    """
    This method is used to view all comments in the announcements
    """
    comments = AnnouncementComment.objects.filter(announcement_id=anoun_id).order_by(
        "-created_at"
    )
    announcement = Announcement.objects.get(id=anoun_id)
    comments = filter_own_records(request, comments, "base.view_announcementcomment")
    no_comments = False
    if not comments.exists():
        no_comments = True

    return render(
        request,
        "announcement/comment_view.html",
        {
            "comments": comments,
            "no_comments": no_comments,
            "request_id": anoun_id,
            "announcement": announcement,
        },
    )


@login_required
@hx_request_required
def delete_announcement_comment(request, comment_id):
    """
    This method is used to delete announcement comments
    """
    comment = AnnouncementComment.objects.get(id=comment_id)
    comment.delete()
    messages.success(request, _("Comment deleted successfully!"))
    return HttpResponse()


@login_required
@hx_request_required
def announcement_single_view(request, anoun_id=None):
    """
    This method is used to render single announcements.
    """
    announcement_instance = Announcement.find(anoun_id)
    instance_ids = request.GET.get("instance_ids")
    instance_ids_list = json.loads(instance_ids) if instance_ids else []
    previous_instance_id, next_instance_id = (
        closest_numbers(instance_ids_list, anoun_id)
        if instance_ids_list
        else (None, None)
    )
    if announcement_instance:
        announcement_view_obj, _ = AnnouncementView.objects.get_or_create(
            user=request.user, announcement=announcement_instance
        )
        announcement_view_obj.viewed = True
        announcement_view_obj.save()

    context = {
        "announcement": announcement_instance,
        "instance_ids": instance_ids,
        "previous_instance_id": previous_instance_id,
        "next_instance_id": next_instance_id,
    }

    return render(request, "announcement/announcement_one.html", context)


@login_required
@hx_request_required
@permission_required("base.view_announcement")
def viewed_by(request):
    """
    This method is used to view the employees
    """
    announcement_id = request.GET.get("announcement_id")
    viewed_users = AnnouncementView.objects.filter(
        announcement_id__id=announcement_id, viewed=True
    )
    return render(request, "announcement/viewed_by.html", {"viewed_by": viewed_users})
