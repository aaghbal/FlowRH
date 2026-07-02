from django.db import migrations

DEFAULT_CATEGORIES = [
    "Matériel & logistique",
    "Administratif & RH",
    "Finances",
]


def seed_categories(apps, schema_editor):
    CompanyDocumentCategory = apps.get_model("employee", "CompanyDocumentCategory")
    for name in DEFAULT_CATEGORIES:
        CompanyDocumentCategory.objects.get_or_create(name=name)


def remove_categories(apps, schema_editor):
    CompanyDocumentCategory = apps.get_model("employee", "CompanyDocumentCategory")
    CompanyDocumentCategory.objects.filter(name__in=DEFAULT_CATEGORIES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("employee", "0004_companydocumentcategory_companydocument"),
    ]

    operations = [
        migrations.RunPython(seed_categories, remove_categories),
    ]
