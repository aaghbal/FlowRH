import logging
from email.mime.image import MIMEImage
from threading import Thread

from django.contrib.staticfiles import finders
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from base.backends import ConfiguredEmailBackend

logger = logging.getLogger(__name__)


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
        subject = f"Votre candidature a bien été reçue – {position}"
        html_message = render_to_string(
            "candidate/mail_templates/application_received.html",
            {
                "candidate": candidate,
                "position": position,
                "subject": subject,
                "logo_url": "cid:mautomotiv-logo",
            },
        )
        email_backend = ConfiguredEmailBackend()
        email = EmailMessage(
            subject=subject,
            body=html_message,
            from_email=email_backend.dynamic_from_email_with_display_name,
            to=[candidate.email],
            connection=email_backend,
        )
        email.content_subtype = "html"
        # Embed the logo in the email itself: a link to the site would break
        # whenever the server is not reachable from the recipient (e.g. localhost).
        logo_path = finders.find("images/ui/m-automotiv-logo.png")
        if logo_path:
            email.mixed_subtype = "related"
            with open(logo_path, "rb") as logo_file:
                logo = MIMEImage(logo_file.read())
            logo.add_header("Content-ID", "<mautomotiv-logo>")
            logo.add_header("Content-Disposition", "inline", filename="m-automotiv-logo.png")
            email.attach(logo)
        try:
            email.send()
        except Exception as e:
            logger.exception(e)
