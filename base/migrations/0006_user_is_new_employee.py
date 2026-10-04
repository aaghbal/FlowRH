"""
Add the auth_user.is_new_employee column.

The field is attached to django.contrib.auth's User in base/models.py with
User.add_to_class, so makemigrations wrote its migration inside the installed
Django package (auth/0013_user_is_new_employee), which is not part of this
repository. This migration replaces it. It only adds the column when it is
missing, so databases that already ran the old auth migration are untouched.
"""

from django.db import migrations


def add_is_new_employee(apps, schema_editor):
    from django.contrib.auth.models import User

    table = User._meta.db_table
    with schema_editor.connection.cursor() as cursor:
        columns = [
            col.name
            for col in schema_editor.connection.introspection.get_table_description(
                cursor, table
            )
        ]
    if "is_new_employee" not in columns:
        schema_editor.add_field(User, User._meta.get_field("is_new_employee"))


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("base", "0005_alter_jobposition_job_position"),
    ]

    operations = [
        migrations.RunPython(add_is_new_employee, migrations.RunPython.noop),
    ]
