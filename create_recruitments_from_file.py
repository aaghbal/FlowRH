"""
Create Recruitments from the "Besoins en recrutement M Automotiv" file.

For every (Site + Poste) group that is "En cours de recrutement", one
Recruitment is created with vacancy = number of positions for that group.
Example: JAC Rabat + Conseiller commercial (3 rows) -> 1 Recruitment, vacancy 3.

- Sites are created in base_site if missing.
- Job positions are created (under the department below) if missing.
- A recruitment is skipped if one with the same title + site already exists,
  so the script is safe to re-run.

Run with:
    python manage.py shell < create_recruitments_from_file.py
"""

from django.utils import timezone
from base.models import Company, Department, JobPosition, Site
from recruitment.models import Recruitment

DEPARTMENT_NAME = "Automotiv"   # department the job positions belong to
COMPANY_NAME = "automotiv"      # used to find the company (case-insensitive contains)
TITLE_MAX = 30                  # Recruitment.title max_length

# (site_name, poste, vacancy) — "En cours de recrutement" groups only.
RECRUITMENTS = [
    ("Contrôle interne", "Contrôleur interne", 1),
    ("Exeed Massira", "Conseiller commercial", 1),
    ("Exeed Rabat", "Conseiller commercial", 1),
    ("Exeed Tanger", "ADV", 1),
    ("Exeed Tanger", "Caissier", 1),
    ("Exeed Tanger", "Chef de ventes", 1),
    ("Exeed Tanger", "Conseiller commercial", 3),
    ("Exeed Tanger", "Convoyeur", 1),
    ("Exeed Tanger", "Metteur en main", 1),
    ("Experience clients", "Chargé d'experience client et qualité", 1),
    ("Finance", "Agent administratif", 1),
    ("Finance", "Comptable", 1),
    ("Finance", "Contrôleur de gestion", 1),
    ("Finance", "Responsable achats", 1),
    ("Finance", "Responsable budget", 1),
    ("Finance", "Responsable import", 1),
    ("FLOTTES - BDG", "Manager Grands Comptes", 3),
    ("GAC", "Directeur de marque", 1),
    ("GAC BDG", "Metteur en main", 1),
    ("GAC Driss Slaoui", "ADV", 1),
    ("GAC Driss Slaoui", "Caissier", 1),
    ("GAC Driss Slaoui", "Chef de ventes", 1),
    ("GAC Driss Slaoui", "Conseiller commercial", 4),
    ("GAC Driss Slaoui", "Metteur en main", 1),
    ("GAC Tanger", "Chef de ventes", 1),
    ("GAC Tanger", "Conseiller commercial", 3),
    ("JAC Had Soualem", "Electricien Co-Tech", 1),
    ("JAC Had Soualem", "Magasinier", 1),
    ("JAC Rabat", "Conseiller commercial", 3),
    ("JAC Tanger", "Chef de ventes", 1),
    ("JAC Tanger", "Conseiller commercial", 6),
    ("JAC Tanger", "Convoyeur", 1),
    ("Juridique", "Juriste", 1),
    ("Juridique", "Responsable juridique", 1),
    ("KGM / JAC Tanger", "ADV", 1),
    ("KGM / JAC Tanger", "Caissier", 1),
    ("KGM / JAC Tanger", "Convoyeur", 1),
    ("KGM / JAC Tanger", "Metteur en main", 1),
    ("KGM Tanger", "Chef de ventes", 1),
    ("KGM Tanger", "Conseiller commercial", 3),
    ("M Occaz", "Chef de ventes", 1),
    ("M Occaz", "Conseiller commercial", 3),
    ("M servcie Targa", "Chef de centre", 1),
    ("M servcie Targa", "Mécanicien", 1),
    ("Magasin M Trade", "Chef de piste", 1),
    ("Magasin M Trade", "Convoyeur", 1),
    ("Magasin M Trade", "Coordinatrice RCL", 1),
    ("Marketing", "Chargé marketing opérationnel", 1),
    ("Marketing", "CRM Manager", 1),
    ("Marketing", "CRM Specialist", 1),
    ("Marketing", "Responsable marketing opérationnel", 1),
    ("Produits", "Chef de produits", 1),
    ("R/D - BDG", "Conseiller commercial", 2),
    ("R/D - Errahma", "Conseiller commercial", 2),
    ("R/D - Sidi Othame", "Conseiller commercial", 2),
    ("Soueast / GAC Tanger", "ADV", 1),
    ("Soueast / GAC Tanger", "Caissier", 1),
    ("Soueast / GAC Tanger", "Convoyeur", 1),
    ("Soueast / GAC Tanger", "Metteur en main", 1),
    ("Soueast Agadir", "ADV", 1),
    ("Soueast Agadir", "Caissier", 1),
    ("Soueast Agadir", "Conseiller commercial", 3),
    ("Soueast Agadir", "Convoyeur", 1),
    ("Soueast Agadir", "Metteur en main", 1),
    ("Soueast El Jadida", "ADV", 1),
    ("Soueast El Jadida", "Conseiller commercial", 2),
    ("Soueast El Jadida", "Metteur en main", 1),
    ("Soueast Tanger", "Chef de ventes", 1),
    ("Soueast Tanger", "Conseiller commercial", 3),
]


def get_or_create_site(name, company):
    site = Site.objects.filter(site_name=name).first()
    if site is None:
        site = Site.objects.create(site_name=name, company_id=company)
        print(f"   + Site created: {name}")
    elif site.company_id is None and company is not None:
        site.company_id = company
        site.save(update_fields=["company_id"])
    return site


def get_or_create_jobposition(name, dept):
    # filter().first() because some postes already have duplicate rows
    jp = JobPosition.objects.filter(job_position=name, department_id=dept).first()
    if jp is None:
        jp = JobPosition.objects.create(job_position=name, department_id=dept)
        print(f"   + Job position created: {name}")
    return jp


dept, dept_created = Department.objects.get_or_create(department=DEPARTMENT_NAME)
print(f"Department '{DEPARTMENT_NAME}': {'CREATED' if dept_created else 'exists'} (id={dept.id})")

# The company every recruitment must belong to, otherwise the company-scoped
# manager hides them from the recruitment list (NULL company is filtered out).
company = Company.objects.filter(company__icontains=COMPANY_NAME).first() or Company.objects.first()
if company is None:
    raise SystemExit("No Company found in the database — create one first.")
print(f"Company used: '{company.company}' (id={company.id})")
print("=" * 60)

today = timezone.now().date()
created = 0
skipped = 0
fixed = 0

for site_name, poste, vacancy in RECRUITMENTS:
    site = get_or_create_site(site_name, company)
    jp = get_or_create_jobposition(poste, dept)
    title = poste[:TITLE_MAX]

    # idempotency: same title + same site means it already exists.
    # Use .default (unscoped) so company-filtered records are still found.
    existing = Recruitment.default.filter(title=title, site=site).first()
    if existing is not None:
        # self-heal: stamp the company on records created earlier with NULL company
        if existing.company_id_id is None:
            existing.company_id = company
            existing.save(update_fields=["company_id"])
            fixed += 1
            print(f"[FIXED  ] {site_name:<22} | {poste:<38} -> company set")
        else:
            skipped += 1
            print(f"[SKIP   ] {site_name:<22} | {poste:<38} (already exists)")
        continue

    rec = Recruitment.objects.create(
        title=title,
        vacancy=vacancy,
        site=site,
        company_id=company,
        job_position_id=None,     # None avoids the (job_position_id, start_date) unique clash
        is_event_based=False,
        is_published=True,
        start_date=today,
    )
    rec.open_positions.add(jp)
    created += 1
    print(f"[CREATED] {site_name:<22} | {poste:<38} vacancy={vacancy}")

print("=" * 60)
print(f"Created: {created} | company-fixed: {fixed} | skipped: {skipped} | plan: {len(RECRUITMENTS)}")
print(f"Total recruitments in DB now: {Recruitment.default.count()}")
