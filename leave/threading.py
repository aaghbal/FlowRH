import logging
from threading import Thread

from django.contrib import messages
from django.core.mail import EmailMessage
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils.translation import gettext as _

from base.backends import ConfiguredEmailBackend

logger = logging.getLogger(__name__)


class LeaveMailSendThread(Thread):

    def __init__(self, request, leave_request, type):
        Thread.__init__(self)
        self.request = request
        self.leave_request = leave_request
        self.type = type
        self.host = request.get_host()
        self.protocol = "https" if request.is_secure() else "http"

    def send_email(self, subject, content, recipients, leave_request_id="#"):
        email_backend = ConfiguredEmailBackend()
        display_email_name = email_backend.dynamic_from_email_with_display_name
        if self.request:
            try:
                display_email_name = f"{self.request.user.employee_get.get_full_name()} <{self.request.user.employee_get.email}>"
            except:
                logger.error(Exception)

        host = self.host
        protocol = self.protocol
        link = "#"
        if leave_request_id != "#":
            link = int(leave_request_id)
        for recipient in recipients:
            if recipient:
                html_message = render_to_string(
                    "base/mail_templates/leave_request_template.html",
                    {
                        "link": link,
                        "instance": recipient,
                        "host": host,
                        "protocol": protocol,
                        "subject": subject,
                        "content": content,
                    },
                    request=self.request,
                )

                email = EmailMessage(
                    subject=subject,
                    body=html_message,
                    from_email=display_email_name,
                    to=[recipient.email],
                    reply_to=[display_email_name],
                )
                email.content_subtype = "html"
                try:
                    email.send()
                except:
                    messages.error(
                        self.request, f"Mail not sent to {recipient.get_full_name()}"
                    )

    def run(self) -> None:
        super().run()
        if self.type == "request":
            owner = self.leave_request.employee_id
            reporting_manager = self.leave_request.employee_id.get_reporting_manager()

            content_manager = f"Nous vous informons qu'une demande de congé a été déposée par {owner}. Veuillez prendre les mesures nécessaires concernant cette demande. Si vous avez des informations complémentaires ou des mises à jour, n’hésitez pas à les transmettre directement à {owner}."
            subject_manager = f"La demande de congé a été déposée par {owner}"

            self.send_email(
                subject_manager,
                content_manager,
                [reporting_manager],
                self.leave_request.id,
            )

            content_owner = f"Nous vous informons que la demande de congé que vous avez créée a bien été enregistrée dans notre système."
            subject_owner = "Demande de congé créée avec succès"

            self.send_email(
                subject_owner, content_owner, [owner], self.leave_request.id
            )

        elif self.type == "approve":
            owner = self.leave_request.employee_id
            reporting_manager = self.leave_request.employee_id.get_reporting_manager()

            subject = "Votre demande de congé a été approuvée."
            content = f"Nous vous informons que votre demande de congé a été approuvée."

            self.send_email(subject, content, [owner], self.leave_request.id)

        elif self.type == "reject":
            owner = self.leave_request.employee_id
            reporting_manager = self.leave_request.employee_id.get_reporting_manager()

            subject = "Votre demande de congé a été rejetée."
            content = f"Nous vous informons que votre demande de congé a été rejetée."

            self.send_email(subject, content, [owner], self.leave_request.id)

        elif self.type == "cancel":
            owner = self.leave_request.employee_id
            reporting_manager = self.leave_request.employee_id.get_reporting_manager()

            content_manager = f"Nous vous informons qu'une demande de congé a été demandée pour annuler par {owner}. Veuillez prendre les mesures nécessaires concernant cette demande. Si vous avez des informations complémentaires ou des mises à jour, n’hésitez pas à les transmettre directement à {owner}."
            subject_manager = f"La demande de congé a été annulée"

            self.send_email(
                subject_manager,
                content_manager,
                [reporting_manager],
                self.leave_request.id,
            )

            content_owner = f"Nous vous informons que la demande d'annulation de congé que vous avez créée a bien été enregistrée dans notre système. Le manager va maintenant prendre les mesures nécessaires pour traiter la demande de congé. Si vous avez des informations complémentaires ou des mises à jour, n'hésitez pas à les transmettre directement à {reporting_manager}."
            subject_owner = "Demande d'annulation de congé effectuée"

            self.send_email(
                subject_owner, content_owner, [owner], self.leave_request.id
            )

        return


class LeaveClashThread(Thread):

    def __init__(self, leave_request):
        Thread.__init__(self)
        self.leave_request = leave_request

    def count_leave_clashes(self):
        from leave.models import LeaveRequest

        """
        Method to count leave clashes where this employee's leave request overlaps
        with other employees' requested dates.
        """
        overlapping_requests = LeaveRequest.objects.exclude(
            id=self.leave_request.id
        ).filter(
            Q(
                employee_id__employee_work_info__department_id=self.leave_request.employee_id.employee_work_info.department_id
            )
            | Q(
                employee_id__employee_work_info__job_position_id=self.leave_request.employee_id.employee_work_info.job_position_id
            ),
            start_date__lte=self.leave_request.end_date,
            end_date__gte=self.leave_request.start_date,
        )

        return overlapping_requests.count()

    def run(self) -> None:
        from leave.models import LeaveRequest

        super().run()
        dates = self.leave_request.requested_dates()
        leave_requests_to_update = LeaveRequest.objects.filter(
            Q(start_date__in=dates) | Q(end_date__in=dates)
        )

        for leave_request in leave_requests_to_update:
            leave_request.leave_clashes_count = self.count_leave_clashes()
            leave_request.save()
