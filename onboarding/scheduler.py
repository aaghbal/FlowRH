"""
scheduler.py

Background jobs of the onboarding module.
"""

import logging
import sys
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)

# number of days before the end of the first probation period at which the
# "Prolongation de période d'essai" letter is sent to the candidate
PROBATION_EXTENSION_MAIL_DELAY = 7
# article of the employment contract the probation extension refers to
CONTRACT_PROBATION_ARTICLE = "X"


def probation_extension_duration(start_date, end_date):
    """
    Returns the duration between the two dates (both included) written in
    french, the way it is worded in the letter : "1 mois et demi", "2 mois",
    "20 jours"...
    """
    delta = relativedelta(end_date + timedelta(days=1), start_date)
    months = delta.years * 12 + delta.months
    days = delta.days
    if not months:
        return f"{days} jour" if days <= 1 else f"{days} jours"
    if 13 <= days <= 17:
        return f"{months} mois et demi"
    if not days:
        return f"{months} mois"
    return f"{months} mois et {days} jour" if days == 1 else f"{months} mois et {days} jours"


def probation_extension_mail():
    """
    Sends the "Prolongation de votre période d'essai" letter, as a pdf
    attachment, to the candidates whose first probation period ends within a
    week and whose probation is extended, that is the ones having a second
    probation end date while still waiting for a decision.
    """
    from django.core.mail import EmailMessage
    from django.template.loader import render_to_string

    from base.methods import generate_pdf
    from recruitment.models import Candidate

    today = datetime.now().date()
    candidates = Candidate.objects.filter(
        probation_status="attente",
        probation_extension_mail_sent=False,
        probation_end__isnull=False,
        probation_end__gte=today,
        probation_end__lte=today + timedelta(days=PROBATION_EXTENSION_MAIL_DELAY),
        probation_end_2__isnull=False,
        email__isnull=False,
    ).exclude(email="")

    for candidate in candidates:
        # nothing to announce when the second period does not extend the first one
        if candidate.probation_end_2 <= candidate.probation_end:
            continue
        extension_start = candidate.probation_end + timedelta(days=1)
        context = {
            "candidate": candidate,
            "extension_start": extension_start,
            "extension_end": candidate.probation_end_2,
            "extension_duration": probation_extension_duration(
                extension_start, candidate.probation_end_2
            ),
            "contract_article": CONTRACT_PROBATION_ARTICLE,
        }
        try:
            letter = render_to_string(
                "onboarding/mail_templates/prolongation_periode_essai.html", context
            )
            html_message = render_to_string(
                "onboarding/mail_templates/prolongation_periode_essai_mail.html",
                context,
            )
            email = EmailMessage(
                subject="Prolongation de votre période d'essai",
                body=html_message,
                to=[candidate.email],
            )
            email.content_subtype = "html"
            email.attach(
                "Prolongation de periode d'essai.pdf",
                generate_pdf(
                    letter, {}, path=False, title="Prolongation de periode d'essai.pdf"
                ).content,
                "application/pdf",
            )
            email.send()
        except Exception as e:
            # the letter will be sent again on the next run of the job
            logger.error(e)
            continue
        # update() instead of save() to only touch that column, the custom
        # save() of Candidate validates fields this job has nothing to do with
        Candidate.objects.filter(pk=candidate.pk).update(
            probation_extension_mail_sent=True
        )


if not any(
    cmd in sys.argv
    for cmd in ["makemigrations", "migrate", "compilemessages", "flush", "shell"]
):
    """
    Initializes and starts background tasks using APScheduler when the server is running.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        probation_extension_mail,
        CronTrigger(hour=8),
        misfire_grace_time=int(timedelta(days=1).total_seconds()),
    )

    scheduler.start()
