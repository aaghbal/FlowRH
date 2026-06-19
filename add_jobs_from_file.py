"""
Add all the postes (job positions) from the "Besoins en recrutement M Automotiv"
file into the base_jobposition table (JobPosition model), all linked to the
"M Automotiv" department. Each poste is only added if it does not already exist
in that department.

Run with:
    python manage.py shell < add_jobs_from_file.py
"""

from base.models import Department, JobPosition

# ---- The department all these jobs belong to ----
DEPARTMENT_NAME = "Automotiv"   # change here if you want a different name

# Distinct postes from the "Poste" column of the Excel file.
# ("Conseiller Commercial" was merged into "Conseiller commercial".)
JOBS = [
    "ADV",
    "Agent administratif",
    "Caissier",
    "Chargé d'experience client et qualité",
    "Chargé de showroom",
    "Chargé marketing opérationnel",
    "Chef de centre",
    "Chef de piste",
    "Chef de produits",
    "Chef de projets communication interne et bien être",
    "Chef de ventes",
    "Compensation & Benefits Manager",
    "Comptable",
    "Conseiller commercial",
    "Contrôleur de gestion",
    "Contrôleur interne",
    "Convoyeur",
    "Coordinatrice RCL",
    "CRM Manager",
    "CRM Specialist",
    "Directeur de marque",
    "Electricien Co-Tech",
    "Juriste",
    "Magasinier",
    "Manager Grands Comptes",
    "Metteur en main",
    "Mécanicien",
    "Responsable achats",
    "Responsable budget",
    "Responsable de site",
    "Responsable import",
    "Responsable juridique",
    "Responsable marketing opérationnel",
    "Tax Manager",
]

# ---- Get or create the department ----
dept, dept_created = Department.objects.get_or_create(department=DEPARTMENT_NAME)
print(f"Department '{DEPARTMENT_NAME}': {'CREATED' if dept_created else 'already exists'} (id={dept.id})")
print("-" * 50)

created_count = 0
existing_count = 0

for name in JOBS:
    name = name.strip()
    if not name:
        continue
    # Use filter().first() instead of get_or_create: some postes already
    # have duplicate rows in the DB, which would make get_or_create's internal
    # .get() raise MultipleObjectsReturned.
    qs = JobPosition.objects.filter(job_position=name, department_id=dept)
    count = qs.count()
    if count >= 1:
        existing_count += 1
        dup = f"  (WARNING: {count} duplicates)" if count > 1 else ""
        print(f"[EXISTS ] {name}{dup}")
    else:
        obj = JobPosition.objects.create(job_position=name, department_id=dept)
        # link the job to the same companies as its department (if any)
        companies = list(dept.company_id.all())
        if companies:
            obj.company_id.add(*companies)
        created_count += 1
        print(f"[CREATED] {name}")

print("-" * 50)
print(f"Created: {created_count} | Already existed: {existing_count} | Total in file: {len(JOBS)}")
print(f"Total job positions in '{DEPARTMENT_NAME}': {JobPosition.objects.filter(department_id=dept).count()}")
