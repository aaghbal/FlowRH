"""
horilla_middlewares.py

This module is used to register horilla's middlewares without affecting the horilla/settings.py
"""

import logging
import threading
import time

from django.http import HttpResponseNotAllowed
from django.shortcuts import render

from horilla.settings import MIDDLEWARE

MIDDLEWARE.append("base.middleware.CompanyMiddleware")
MIDDLEWARE.append("horilla.horilla_middlewares.MethodNotAllowedMiddleware")
MIDDLEWARE.append("horilla.horilla_middlewares.ThreadLocalMiddleware")
MIDDLEWARE.append("accessibility.middlewares.AccessibilityMiddleware")
MIDDLEWARE.append("accessibility.middlewares.AccessibilityMiddleware")
MIDDLEWARE.append("base.middleware.ForcePasswordChangeMiddleware")
# last, so it decides on the request the earlier middlewares have finished
# setting up (notably the selected company and the thread-local request)
MIDDLEWARE.append("base.middleware.RoleAccessMiddleware")
# right after authentication, so it also logs requests that a later middleware
# (role access, forced password change) redirects or refuses
MIDDLEWARE.insert(
    MIDDLEWARE.index("django.contrib.auth.middleware.AuthenticationMiddleware") + 1,
    "horilla.horilla_middlewares.ActivityLogMiddleware",
)
_thread_locals = threading.local()
activity_logger = logging.getLogger("flowrh.activity")


class ThreadLocalMiddleware:
    """
    ThreadLocalMiddleWare
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        response = self.get_response(request)
        return response


class MethodNotAllowedMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if isinstance(response, HttpResponseNotAllowed):
            return render(request, "405.html")
        return response


class ActivityLogMiddleware:
    """
    Writes one line per request to the flowrh.activity logger:
    user, IP, method, path, status code and duration.
    """

    SKIP_PREFIXES = ("/static/", "/media/", "/favicon.ico")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(self.SKIP_PREFIXES):
            return self.get_response(request)

        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = (time.monotonic() - start) * 1000

        user = getattr(request, "user", None)
        username = user.username if user and user.is_authenticated else "anonymous"
        # behind Passenger / a proxy, REMOTE_ADDR is the proxy itself
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        ip = (
            forwarded.split(",")[0].strip()
            if forwarded
            else request.META.get("REMOTE_ADDR", "-")
        )
        activity_logger.info(
            "%s %s %s %s %s %.0fms",
            username,
            ip,
            request.method,
            request.get_full_path(),
            response.status_code,
            duration_ms,
        )
        return response
