"""
horilla/config.py

Horilla app configurations
"""

import importlib
import logging

from django.apps import apps
from django.conf import settings
from django.contrib.auth.context_processors import PermWrapper

from horilla.horilla_apps import SIDEBARS

logger = logging.getLogger(__name__)


def get_apps_in_base_dir():
    return SIDEBARS


def import_method(accessibility):
    module_path, method_name = accessibility.rsplit(".", 1)
    module = __import__(module_path, fromlist=[method_name])
    accessibility_method = getattr(module, method_name)
    return accessibility_method


ALL_MENUS = {}


def sidebar(request):
    # imported here, not at module level: base.role_access pulls in the ORM,
    # and this module is loaded while the app registry is still warming up
    from base.role_access import allowed_pages, can_access
    from base.role_pages import pages_for_path

    base_dir_apps = get_apps_in_base_dir()

    if not request.user.is_anonymous:
        request.MENUS = []
        MENUS = request.MENUS

        for app in base_dir_apps:
            if apps.is_installed(app):
                try:
                    sidebar = importlib.import_module(app + ".sidebar")

                except Exception as e:
                    logger.error(e)
                    continue

                if sidebar:
                    accessibility = None
                    if getattr(sidebar, "ACCESSIBILITY", None):
                        accessibility = import_method(sidebar.ACCESSIBILITY)

                    if not accessibility or accessibility(
                        request,
                        sidebar.MENU,
                        PermWrapper(request.user),
                    ):
                        MENU = {}
                        MENU["menu"] = sidebar.MENU
                        MENU["app"] = app
                        MENU["img_src"] = sidebar.IMG_SRC
                        MENU["submenu"] = []
                        MENUS.append(MENU)
                        for submenu in sidebar.SUBMENUS:

                            accessibility = None

                            if submenu.get("accessibility"):
                                accessibility = import_method(submenu["accessibility"])
                            redirect: str = submenu["redirect"]
                            redirect = redirect.split("?")
                            submenu["redirect"] = redirect[0]

                            if not accessibility or accessibility(
                                request,
                                submenu,
                                PermWrapper(request.user),
                            ):
                                MENU["submenu"].append(submenu)

        # the accessibility callables above can only widen access, so they
        # would still show a role holder the pages their role withholds --
        # which RoleAccessMiddleware then refuses. Drop them here so the menu
        # and the middleware agree, and drop a module left with no entry.
        # Skipped entirely for users no role restricts, which is the common
        # case and spares the URL resolution below.
        if allowed_pages(request.user) is not None:
            for menu in MENUS:
                menu["submenu"] = [
                    submenu
                    for submenu in menu["submenu"]
                    if can_access(request.user, pages_for_path(submenu["redirect"]))
                ]
            MENUS[:] = [menu for menu in MENUS if menu["submenu"]]

        ALL_MENUS[request.session.session_key] = MENUS


def get_MENUS(request):
    ALL_MENUS[request.session.session_key] = []
    sidebar(request)
    return {"sidebar": ALL_MENUS.get(request.session.session_key)}
