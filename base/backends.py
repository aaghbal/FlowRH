"""
email_backend.py

This module is used to write email backends
"""

import html as html_lib
import importlib
import logging
import re

from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.core.mail.backends.smtp import EmailBackend
from django.utils.html import strip_tags

from base.models import DynamicEmailConfiguration, EmailLog
from horilla import settings
from horilla.horilla_middlewares import _thread_locals

logger = logging.getLogger(__name__)


class DefaultHorillaMailBackend(EmailBackend):
    def __init__(
        self,
        host=None,
        port=None,
        username=None,
        password=None,
        use_tls=None,
        fail_silently=None,
        use_ssl=None,
        timeout=None,
        ssl_keyfile=None,
        ssl_certfile=None,
        **kwargs,
    ):
        self.configuration = self.get_dynamic_email_config()
        ssl_keyfile = (
            getattr(self.configuration, "ssl_keyfile", None)
            if self.configuration
            else ssl_keyfile or getattr(settings, "ssl_keyfile", None)
        )
        ssl_certfile = (
            getattr(self.configuration, "ssl_certfile", None)
            if self.configuration
            else ssl_certfile or getattr(settings, "ssl_certfile", None)
        )

        super().__init__(
            host=self.dynamic_host,
            port=self.dynamic_port,
            username=self.dynamic_username,
            password=self.dynamic_password,
            use_tls=self.dynamic_use_tls,
            fail_silently=self.dynamic_fail_silently,
            use_ssl=self.dynamic_use_ssl,
            timeout=self.dynamic_timeout,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
            **kwargs,
        )

    @staticmethod
    def get_dynamic_email_config():
        request = getattr(_thread_locals, "request", None)
        company = None
        if request and not request.user.is_anonymous:
            company = request.user.employee_get.get_company()
        configuration = DynamicEmailConfiguration.objects.filter(
            company_id=company
        ).first()
        if configuration is None:
            configuration = DynamicEmailConfiguration.objects.filter(
                is_primary=True
            ).first()
        return configuration

    @property
    def dynamic_host(self):
        return (
            self.configuration.host
            if self.configuration
            else getattr(settings, "EMAIL_HOST", None)
        )

    @property
    def dynamic_port(self):
        return (
            self.configuration.port
            if self.configuration
            else getattr(settings, "EMAIL_PORT", None)
        )

    @property
    def dynamic_username(self):
        return (
            self.configuration.username
            if self.configuration
            else getattr(settings, "EMAIL_HOST_USER", None)
        )

    @property
    def dynamic_mail_sent_from(self):
        return (
            self.configuration.from_email
            if self.configuration
            else getattr(settings, "DEFAULT_FROM_EMAIL", None)
        )

    @property
    def dynamic_display_name(self):
        return self.configuration.display_name if self.configuration else None

    @property
    def dynamic_from_email_with_display_name(self):
        return (
            f"{self.dynamic_display_name} <{self.dynamic_mail_sent_from}>"
            if self.dynamic_display_name
            else self.dynamic_mail_sent_from
        )

    @property
    def dynamic_password(self):
        return (
            self.configuration.password
            if self.configuration
            else getattr(settings, "EMAIL_HOST_PASSWORD", None)
        )

    @property
    def dynamic_use_tls(self):
        return (
            self.configuration.use_tls
            if self.configuration
            else getattr(settings, "EMAIL_USE_TLS", None)
        )

    @property
    def dynamic_fail_silently(self):
        return (
            self.configuration.fail_silently
            if self.configuration
            else getattr(settings, "EMAIL_FAIL_SILENTLY", True)
        )

    @property
    def dynamic_use_ssl(self):
        return (
            self.configuration.use_ssl
            if self.configuration
            else getattr(settings, "EMAIL_USE_SSL", None)
        )

    @property
    def dynamic_timeout(self):
        return (
            self.configuration.timeout
            if self.configuration
            else getattr(settings, "EMAIL_TIMEOUT", None)
        )


EMAIL_BACKEND = getattr(settings, "EMAIL_BACKEND", "")


BACKEND_CLASS: EmailBackend = DefaultHorillaMailBackend
default = "base.backends.ConfiguredEmailBackend"

setattr(BACKEND_CLASS, "send_messages", DefaultHorillaMailBackend.send_messages)

if EMAIL_BACKEND and EMAIL_BACKEND != default:
    module_path, class_name = EMAIL_BACKEND.rsplit(".", 1)
    module = importlib.import_module(module_path)
    BACKEND_CLASS = getattr(module, class_name)


def html_to_plain_text(html):
    """Build a readable plain-text version from an HTML email body."""
    # keep link targets readable, drop scripts/styles
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", html or "")
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|h[1-6]|div|tr|li|td)>", "\n", text)
    text = strip_tags(text)
    text = html_lib.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


def ensure_plain_text_alternative(message):
    """
    Add a text/plain alternative to HTML-only emails so they are sent as
    multipart/alternative. HTML-only messages are heavily penalised by spam
    filters (SpamAssassin MIME_HTML_ONLY); this improves deliverability.
    """
    try:
        is_html_only = (
            getattr(message, "content_subtype", "plain") == "html"
            and not getattr(message, "alternatives", None)
        )
        if not is_html_only:
            return
        html_body = message.body
        plain_body = html_to_plain_text(html_body)
        # turn the EmailMessage into a multipart/alternative message
        message.__class__ = EmailMultiAlternatives
        message.alternatives = [(html_body, "text/html")]
        message.body = plain_body or " "
        message.content_subtype = "plain"
    except Exception as exc:  # never block sending because of this
        logger.warning("Could not add plain-text alternative: %s", exc)


class ConfiguredEmailBackend(BACKEND_CLASS):

    def send_messages(self, email_messages):
        for message in email_messages:
            ensure_plain_text_alternative(message)
        response = super(BACKEND_CLASS, self).send_messages(email_messages)
        for message in email_messages:
            from_email = self.dynamic_from_email_with_display_name or getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@flowrh.conexusitapps.ma")
            email_log = EmailLog(
                subject=message.subject,
                from_email=from_email,
                to=message.to,
                body=message.body,
                status="sent" if response else "failed",
            )
            email_log.save()
        return response


if EMAIL_BACKEND != default:
    from_mail = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@flowrh.conexusitapps.ma")
    username = getattr(settings, "EMAIL_HOST_USER", "no-reply@flowrh.conexusitapps.ma")
    ConfiguredEmailBackend.dynamic_username = from_mail
    ConfiguredEmailBackend.dynamic_from_email_with_display_name = from_mail


__all__ = ["ConfiguredEmailBackend"]


message_init = EmailMessage.__init__


def new_init(
    self,
    subject="",
    body="",
    from_email=None,
    to=None,
    bcc=None,
    connection=None,
    attachments=None,
    headers=None,
    cc=None,
    reply_to=None,
):
    """
    custom __init_method to override
    """
    request = getattr(_thread_locals, "request", None)

    if request:
        try:
            config = DefaultHorillaMailBackend.get_dynamic_email_config()
            if config and config.display_name:
                system_from = f"{config.display_name} <{config.from_email or config.username}>"
                from_email = from_email or system_from
            else:
                display_email_name = f"{request.user.employee_get.get_full_name()} <{request.user.employee_get.email}>"
                from_email = from_email or display_email_name
                reply_to = [display_email_name] if not reply_to else reply_to

        except Exception as e:
            logger.error(e)

    message_init(
        self,
        subject=subject,
        body=body,
        from_email=from_email,
        to=to,
        bcc=bcc,
        connection=connection,
        attachments=attachments,
        headers=headers,
        cc=cc,
        reply_to=reply_to,
    )


EmailMessage.__init__ = new_init
