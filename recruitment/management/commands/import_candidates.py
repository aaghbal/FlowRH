"""
import_candidates.py

Bulk-import candidates from the per-folder `_candidats.csv` files produced by
extract_cv_data.py, attaching each candidate's CV as the resume.

Candidates are imported WITHOUT a recruitment (recruitment_id = NULL) — they land
in the candidate pool and can be affected to a recruitment later from the UI.

Usage:
    python manage.py import_candidates --dry-run      # preview, no DB writes
    python manage.py import_candidates                # really import
    python manage.py import_candidates --root "CV"    # custom CV root

Notes:
- Requires migration 0005 (email nullable) to be applied.
- Candidates with no email are stored with email = NULL.
- Duplicates are skipped (by email when present, otherwise by name + phone).
"""

import csv
import glob
import os
from datetime import datetime

from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from base.models import Company
from recruitment.models import Candidate

GENDER_MAP = {
    "masculin": "male",
    "homme": "male",
    "male": "male",
    "féminin": "female",
    "feminin": "female",
    "femme": "female",
    "female": "female",
}

DATE_FORMATS = ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y")


def parse_dob(value):
    value = (value or "").strip()
    if not value:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def clean(value):
    return (value or "").strip()


class Command(BaseCommand):
    help = "Import candidates (with CV as resume) from _candidats.csv files, with no recruitment."

    def add_arguments(self, parser):
        parser.add_argument(
            "--root", default="CV", help="Root folder containing the recruitment folders"
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Preview only, do not write to the DB"
        )
        parser.add_argument(
            "--limit", type=int, default=0, help="Import at most N candidates (0 = all)"
        )
        parser.add_argument(
            "--company-id",
            type=int,
            default=None,
            help="Company id to assign to imported candidates (so they show under that company)",
        )

    def handle(self, *args, **opts):
        root = opts["root"]
        dry = opts["dry_run"]
        limit = opts["limit"]

        company = None
        if opts["company_id"]:
            company = Company.objects.filter(id=opts["company_id"]).first()
            if company is None:
                self.stderr.write(self.style.ERROR(f"Company id {opts['company_id']} introuvable"))
                return
            self.stdout.write(self.style.SUCCESS(f"Société assignée: {company.company}"))

        csv_files = sorted(glob.glob(os.path.join(root, "**", "_candidats.csv"), recursive=True))
        if not csv_files:
            self.stderr.write(self.style.ERROR(f"No _candidats.csv found under {root!r}"))
            return

        created = skipped_dup = skipped_err = no_resume = 0
        seen_emails = set()
        seen_namephone = set()

        for csv_path in csv_files:
            folder = os.path.dirname(csv_path)
            with open(csv_path, encoding="utf-8-sig") as fh:
                for row in csv.DictReader(fh):
                    if limit and created >= limit:
                        self.stdout.write(self.style.WARNING(f"Reached limit {limit}."))
                        return self._summary(created, skipped_dup, skipped_err, no_resume, dry)

                    name = clean(row.get("Nom complet")) or "Sans nom"
                    email = clean(row.get("Email")) or None
                    phone = clean(row.get("Numero de telephone"))
                    dob = parse_dob(row.get("Date de naissance"))
                    address = clean(row.get("Adresse")) or None
                    gender = GENDER_MAP.get(clean(row.get("Genre")).lower(), "male")
                    cv_file = clean(row.get("_fichier"))
                    cv_path = os.path.join(folder, cv_file) if cv_file else ""

                    # ---- de-duplication (also makes re-runs safe) ----
                    if email:
                        key = email.lower()
                        if key in seen_emails or Candidate.objects.filter(email=email).exists():
                            skipped_dup += 1
                            continue
                        seen_emails.add(key)
                    else:
                        key = f"{name.lower()}|{phone}"
                        if key in seen_namephone or Candidate.objects.filter(
                            name=name, mobile=phone
                        ).exists():
                            skipped_dup += 1
                            continue
                        seen_namephone.add(key)

                    if not cv_path or not os.path.exists(cv_path):
                        no_resume += 1
                        self.stderr.write(self.style.WARNING(f"  ! CV introuvable: {cv_path}"))
                        # resume is required; without a file we cannot create the candidate
                        continue

                    rec = os.path.relpath(folder, root)
                    self.stdout.write(
                        f"[{rec}] {name} | {email or 'NULL'} | {phone or '-'} | "
                        f"{dob or '-'} | {gender}"
                    )
                    if dry:
                        created += 1
                        continue

                    try:
                        with transaction.atomic():
                            candidate = Candidate(
                                name=name,
                                email=email,
                                mobile=phone[:15],
                                dob=dob,
                                address=address,
                                gender=gender,
                                source="software",
                                recruitment_id=None,
                                stage_id=None,
                                company_id=company,
                                is_active=True,
                            )
                            with open(cv_path, "rb") as f:
                                candidate.resume.save(
                                    os.path.basename(cv_path), File(f), save=False
                                )
                            candidate.save()
                        created += 1
                    except Exception as exc:  # keep going on individual failures
                        skipped_err += 1
                        self.stderr.write(self.style.ERROR(f"  x {name}: {exc}"))

        self._summary(created, skipped_dup, skipped_err, no_resume, dry)

    def _summary(self, created, dup, err, no_resume, dry):
        verb = "À créer" if dry else "Créés"
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"{verb}: {created}"))
        self.stdout.write(f"Doublons ignorés: {dup}")
        self.stdout.write(f"Sans CV (ignorés): {no_resume}")
        self.stdout.write(f"Erreurs: {err}")
        if dry:
            self.stdout.write(self.style.WARNING("DRY-RUN: aucune donnée écrite."))
