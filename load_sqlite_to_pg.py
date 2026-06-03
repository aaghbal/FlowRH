"""
Script d'import SQLite → PostgreSQL avec désactivation des signaux.
Usage: myenv/bin/python load_sqlite_to_pg.py
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "horilla.settings")
django.setup()

from django.db.models.signals import post_save
from django.core.management import call_command
from employee.models import Employee

# Disconnect the signal that auto-creates BonusPoint on Employee save
post_save.disconnect(None, sender=Employee, dispatch_uid=None)

# Also disconnect ALL receivers for Employee post_save to be safe
receivers_backup = post_save.receivers[:]
post_save.receivers = [
    r for r in post_save.receivers
    if not (hasattr(r[0], '__self__') and isinstance(getattr(r[0], '__self__', None), type) and issubclass(r[0].__self__, Employee))
]

# Simpler: just disconnect everything for Employee
from django.db.models.signals import post_save, pre_save
import django.dispatch

# Disconnect all Employee signals
employee_receivers = [(key, r) for key, r in post_save.receivers if True]

# Flush existing partial data
print("Flushing existing data...")
call_command("flush", "--no-input", verbosity=0)

# Temporarily disconnect ALL post_save signals
original_receivers = post_save.receivers
post_save.receivers = []

print("Loading fixture (signals disabled)...")
call_command("loaddata", "/home/abdellah/FlowRH/sqlite_dump.json", verbosity=2)

# Restore signals
post_save.receivers = original_receivers

print("Done!")
