"""
Add the recruitment sites from the "Besoins en recrutement M Automotiv" file
into the base_site table (Site model), only if they do not already exist.

Run with:
    python manage.py shell < add_sites_from_file.py
"""

from base.models import Site

# Sites taken from the "Site d'affectation" column of the Excel file.
# (Order preserved; "M servcie Targa" kept as-is to match the source file —
#  change it here if you want the corrected "M service Targa".)
SITES = [
    "Finance",
    "Marketing",
    "Experience clients",
    "Produits",
    "RH",
    "Contrôle interne",
    "Juridique",
    "R/D - Sidi Othame",
    "R/D - Errahma",
    "FLOTTES - BDG",
    "R/D - BDG",
    "Exeed Massira",
    "Exeed Rabat",
    "Soueast El Jadida",
    "GAC",
    "GAC Driss Slaoui",
    "GAC BDG",
    "JAC Had Soualem",
    "Magasin M Trade",
    "M Occaz",
    "M servcie Targa",
    "Soueast Agadir",
    "Soueast Tanger",
    "Soueast / GAC Tanger",
    "GAC Tanger",
    "Exeed Tanger",
    "KGM Tanger",
    "JAC Tanger",
    "KGM / JAC Tanger",
    "JAC Rabat",
]

created_count = 0
existing_count = 0

for name in SITES:
    name = name.strip()
    if not name:
        continue
    obj, created = Site.objects.get_or_create(site_name=name)
    if created:
        created_count += 1
        print(f"[CREATED] {name}")
    else:
        existing_count += 1
        print(f"[EXISTS ] {name}")

print("-" * 50)
print(f"Created: {created_count} | Already existed: {existing_count} | Total in file: {len(SITES)}")
print(f"Total sites in DB now: {Site.objects.count()}")
