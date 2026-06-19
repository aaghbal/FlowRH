import django.db.models.deletion
from django.db import migrations, models

# Known sites historically hard-coded in the announcement / work-info forms.
# Seeded so the Site-backed dropdowns keep all previously available options
# even if no employee currently sits at a given site.
SEED_SITES = [
    "BANDEONG",
    "VITA",
    "LISSASFA",
    "SIDI OTHMANE",
    "DIRECTION POLE",
    "ZENATA",
    "Temara",
    "FINANCE",
    "Errahma",
    "VOVITA",
    "CASA ANFA",
    "VOLISSASFA",
]


def forwards(apps, schema_editor):
    Site = apps.get_model("base", "Site")
    WorkInfo = apps.get_model("employee", "EmployeeWorkInformation")

    cache = {}

    # Seed the known site names first.
    for name in SEED_SITES:
        site, _ = Site.objects.get_or_create(site_name=name)
        cache[name] = site

    # Convert existing free-text locations into Site rows and link them.
    work_infos = WorkInfo.objects.exclude(location_old__isnull=True).exclude(
        location_old__exact=""
    )
    for work_info in work_infos:
        name = (work_info.location_old or "").strip()
        if not name:
            continue
        site = cache.get(name)
        if site is None:
            site, _ = Site.objects.get_or_create(site_name=name)
            cache[name] = site
        work_info.location = site
        work_info.save(update_fields=["location"])


def backwards(apps, schema_editor):
    # Copy the linked Site name back into the temporary text column so the
    # field can be reverted to a CharField without losing data.
    WorkInfo = apps.get_model("employee", "EmployeeWorkInformation")
    for work_info in WorkInfo.objects.exclude(location__isnull=True):
        work_info.location_old = work_info.location.site_name
        work_info.save(update_fields=["location_old"])


class Migration(migrations.Migration):

    dependencies = [
        ("base", "0003_site"),
        ("employee", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="employeeworkinformation",
            old_name="location",
            new_name="location_old",
        ),
        migrations.AddField(
            model_name="employeeworkinformation",
            name="location",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="employee_work_info",
                to="base.site",
                verbose_name="Site",
            ),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.RemoveField(
            model_name="employeeworkinformation",
            name="location_old",
        ),
    ]
