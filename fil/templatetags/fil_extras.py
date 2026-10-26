from django import template
from django.core.files.storage import default_storage
from django.utils import timezone

register = template.Library()

MONTHS_SHORT = [
    "janv.", "févr.", "mars", "avr.", "mai", "juin",
    "juil.", "août", "sept.", "oct.", "nov.", "déc.",
]


@register.filter
def il_y_a(value):
    """French relative time: "il y a 5 min", "il y a 2 h", "hier", "12 oct."."""
    if not value:
        return ""
    now = timezone.now()
    seconds = (now - value).total_seconds()
    if seconds < 60:
        return "à l'instant"
    if seconds < 3600:
        return f"il y a {int(seconds // 60)} min"
    if seconds < 86400:
        return f"il y a {int(seconds // 3600)} h"
    local_value = timezone.localtime(value)
    days = (timezone.localdate() - local_value.date()).days
    if days == 1:
        return "hier"
    if days < 7:
        return f"il y a {days} j"
    label = f"{local_value.day} {MONTHS_SHORT[local_value.month - 1]}"
    if local_value.year != now.year:
        label += f" {local_value.year}"
    return label


DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


@register.filter
def jour(value):
    """French weekday name, e.g. "samedi"."""
    return DAYS[value.weekday()] if value else ""


@register.filter
def short_date(value):
    """ "21 nov." for the upcoming events list."""
    if not value:
        return ""
    return f"{value.day} {MONTHS_SHORT[value.month - 1]}"


@register.filter
def initials(name):
    parts = [part for part in str(name or "").split() if part]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


@register.filter
def avatar_tone(name):
    """Stable colour variant (1-5) for an initials avatar."""
    return sum(ord(char) for char in str(name or "")) % 5 + 1


@register.filter
def photo_url(employee):
    """Profile picture URL, or "" so the template falls back to initials."""
    profile = getattr(employee, "employee_profile", None)
    if profile and profile.name and default_storage.exists(profile.name):
        return profile.url
    return ""
