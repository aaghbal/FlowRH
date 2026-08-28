from django.db import migrations


def backfill_department(apps, schema_editor):
    """
    Fill the new department on the recruitments and candidates that already
    exist, reading it from the job positions they are already attached to.

    A recruitment only gets a department when all of its open positions share
    one; a recruitment spanning several departments stays empty rather than
    being assigned an arbitrary one.
    """
    Recruitment = apps.get_model("recruitment", "Recruitment")
    Candidate = apps.get_model("recruitment", "Candidate")

    for recruitment in Recruitment.objects.filter(
        department_id__isnull=True
    ).prefetch_related("open_positions"):
        department_ids = {
            position.department_id_id for position in recruitment.open_positions.all()
        }
        if recruitment.job_position_id_id and recruitment.job_position_id:
            department_ids.add(recruitment.job_position_id.department_id_id)
        department_ids.discard(None)
        if len(department_ids) == 1:
            recruitment.department_id_id = department_ids.pop()
            recruitment.save(update_fields=["department_id"])

    candidates = Candidate.objects.filter(department_id__isnull=True).select_related(
        "recruitment_id", "job_position_id"
    )
    for candidate in candidates.iterator():
        department_id = None
        if candidate.recruitment_id is not None:
            department_id = candidate.recruitment_id.department_id_id
        if department_id is None and candidate.job_position_id is not None:
            department_id = candidate.job_position_id.department_id_id
        if department_id is not None:
            candidate.department_id_id = department_id
            # save() on the historical model is not the real Candidate.save(),
            # so this stays a plain column write
            candidate.save(update_fields=["department_id"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("recruitment", "0011_candidate_department_id_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_department, noop),
    ]
