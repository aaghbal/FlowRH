import logging
from email.mime.image import MIMEImage
from threading import Thread

from django.contrib.staticfiles import finders
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import translation
from django.utils.formats import date_format

from base.backends import ConfiguredEmailBackend

logger = logging.getLogger(__name__)

LOGO_CID = "mautomotiv-logo"


def build_html_email(subject, html_message, to, reply_to=None):
    """
    Build an HTML email sent through the configured mail server, with the
    M-Automotiv logo embedded in the email itself: a link to the site would
    break whenever the server is not reachable from the recipient (e.g. localhost).
    """
    email_backend = ConfiguredEmailBackend()
    email = EmailMessage(
        subject=subject,
        body=html_message,
        from_email=email_backend.dynamic_from_email_with_display_name,
        to=to,
        reply_to=reply_to,
        connection=email_backend,
    )
    email.content_subtype = "html"
    logo_path = finders.find("images/ui/m-automotiv-logo.png")
    if logo_path:
        email.mixed_subtype = "related"
        with open(logo_path, "rb") as logo_file:
            logo = MIMEImage(logo_file.read())
        logo.add_header("Content-ID", f"<{LOGO_CID}>")
        logo.add_header("Content-Disposition", "inline", filename="m-automotiv-logo.png")
        email.attach(logo)
    return email


class ApplicationReceivedMailThread(Thread):
    """
    Sends the "candidature bien reçue" confirmation email to a candidate
    in the background, so the application form responds immediately.
    """

    def __init__(self, request, candidate):
        Thread.__init__(self)
        self.candidate = candidate

    def run(self):
        candidate = self.candidate
        if not candidate.email:
            return
        position = candidate.job_position_id or candidate.recruitment_id
        subject = "Votre candidature a bien été reçue" + (f" – {position}" if position else "")
        html_message = render_to_string(
            "candidate/mail_templates/application_received.html",
            {
                "candidate": candidate,
                "position": position,
                "subject": subject,
                "logo_url": f"cid:{LOGO_CID}",
            },
        )
        email = build_html_email(subject, html_message, [candidate.email])
        try:
            email.send()
        except Exception as e:
            logger.exception(e)


class InterviewScheduledMailThread(Thread):
    """
    Sends the interview invitation to the candidate and a notice to each
    interviewer when an interview is scheduled.
    """

    def __init__(self, request, interview):
        Thread.__init__(self)
        self.interview = interview
        self.candidate_url = request.build_absolute_uri(
            reverse("candidate-view-individual", args=[interview.candidate_id.id])
        )
        # Candidate replies ("je confirme ma présence") go to whoever scheduled it
        scheduler = getattr(request.user, "employee_get", None)
        scheduler_email = getattr(scheduler, "email", None)
        self.reply_to = [scheduler_email] if scheduler_email else None

    def run(self):
        interview = self.interview
        candidate = interview.candidate_id
        position = candidate.job_position_id or candidate.recruitment_id
        interviewers = list(interview.employee_id.all())
        with translation.override("fr"):
            interview_date = date_format(interview.interview_date, "l j F Y").capitalize()
        interview_time = interview.interview_time.strftime("%Hh%M")
        context = {
            "interview": interview,
            "candidate": candidate,
            "position": position,
            "interview_date": interview_date,
            "interview_time": interview_time,
            "interviewers": [employee.get_full_name() for employee in interviewers],
            "candidate_url": self.candidate_url,
            "logo_url": f"cid:{LOGO_CID}",
        }

        emails = []
        if candidate.email:
            subject = "Invitation à un entretien" + (f" – {position}" if position else "")
            html_message = render_to_string(
                "candidate/mail_templates/interview_scheduled.html",
                {**context, "subject": subject, "for_interviewer": False},
            )
            emails.append(
                build_html_email(subject, html_message, [candidate.email], self.reply_to)
            )

        for employee in interviewers:
            if not employee.email:
                continue
            subject = f"Entretien planifié – {candidate.name} – {interview_date} à {interview_time}"
            html_message = render_to_string(
                "candidate/mail_templates/interview_scheduled.html",
                {
                    **context,
                    "subject": subject,
                    "for_interviewer": True,
                    "recipient_name": employee.get_full_name(),
                    "other_interviewers": [
                        other.get_full_name() for other in interviewers if other != employee
                    ],
                },
            )
            emails.append(build_html_email(subject, html_message, [employee.email]))

        for email in emails:
            try:
                email.send()
            except Exception as e:
                logger.exception(e)
