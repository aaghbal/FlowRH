"""
base/role_access.py

Turns the roles an employee holds into a decision about a page.

`base.models.Role` grants Django permissions, which can only ever *add*
access. It cannot close the two doors that let a role holder walk into a page
they were never given:

* pages with no gate at all -- ``employee.policies`` and
  ``employee.disciplinary`` are plain ``@login_required`` views, and their
  sidebar entries carry no ``accessibility`` callable, so `horilla.config`
  shows them to everyone;
* ``accessibility.methods.check_is_accessible``, which returns True when no
  ``DefaultAccessibility`` row exists for the feature, and the reporting
  manager bypass OR'd into most of the remaining checks.

So this module works the other way round. Once an employee holds at least one
role, the pages ticked on their roles become the *only* catalogued pages they
may reach; anything else in `base.role_pages.PAGE_CATALOG` is refused. URLs
the catalogue does not know stay open exactly as they are today, and an
employee holding no role is not restricted at all, so nothing changes for
users the feature was never applied to.
"""

from django.contrib.auth.models import Group
from django.core.cache import cache

# cache value standing for "this user holds no role", kept distinct from an
# empty page set, which would mean "holds a role that grants nothing"
UNRESTRICTED = "*"

CACHE_TIMEOUT = 600
_VERSION_KEY = "role_access:version"


def cache_version():
    """Current version stamp; every cached decision is keyed on it."""
    version = cache.get(_VERSION_KEY)
    if version is None:
        version = 1
        cache.set(_VERSION_KEY, version, None)
    return version


def invalidate():
    """
    Drop every cached decision.

    Bumping one shared stamp rather than deleting per-user keys: a role change
    can move any number of employees in or out at once -- editing its job
    positions, or an employee changing job position -- and the holders are not
    all known at the point where the change lands.
    """
    try:
        cache.incr(_VERSION_KEY)
    except ValueError:
        # the stamp expired or was never set; any fresh value invalidates
        cache.set(_VERSION_KEY, 1, None)


def _resolve(user):
    """Read the user's roles from the database. Returns a set or UNRESTRICTED."""
    # queried through Group, whose plain manager is not the company-scoped
    # HorillaCompanyManager on Role: a role hidden by company filtering would
    # silently widen the user's access instead of narrowing it
    groups = Group.objects.filter(user=user, role__isnull=False).select_related("role")
    allowed = set()
    held = False
    for group in groups:
        role = group.role
        if not role.is_active:
            continue
        held = True
        allowed.update(role.pages or {})
    return allowed if held else UNRESTRICTED


def allowed_pages(user):
    """
    The page keys ``user`` may reach, or None when no role restricts them.

    None is returned for anonymous users, superusers and anyone holding no
    role -- the three cases where the deny layer must stand aside.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    if user.is_superuser:
        return None
    key = f"role_access:{cache_version()}:{user.pk}"
    value = cache.get(key)
    if value is None:
        value = _resolve(user)
        cache.set(key, value, CACHE_TIMEOUT)
    return None if value == UNRESTRICTED else value


def can_access(user, page_keys) -> bool:
    """
    Whether ``user`` may reach a URL owned by ``page_keys``.

    An empty ``page_keys`` means the URL is outside the catalogue, which is
    open to everyone. Otherwise holding any one of the owning pages is enough,
    so a route two pages share is reachable from either.
    """
    if not page_keys:
        return True
    allowed = allowed_pages(user)
    if allowed is None:
        return True
    return bool(set(page_keys) & set(allowed))


def can_access_path(user, path: str) -> bool:
    """Same decision, for a caller holding a URL rather than a resolved view."""
    from base.role_pages import pages_for_path

    return can_access(user, pages_for_path(path))
