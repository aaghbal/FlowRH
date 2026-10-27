"""
The production database was created with the latin1 charset, which cannot
store emoji (🔹, 🎉, ✅…) nor Arabic text: publishing such a post failed.
Convert the feed tables to utf8mb4, the charset the connection already uses.
No-op on other databases (SQLite in development).
"""

from django.db import migrations

FIL_TABLES = [
    "fil_post",
    "fil_postmedia",
    "fil_poll",
    "fil_polloption",
    "fil_pollvote",
    "fil_comment",
    "fil_like",
    "fil_filsettings",
]


def convert_to_utf8mb4(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return
    with schema_editor.connection.cursor() as cursor:
        for table in FIL_TABLES:
            cursor.execute(
                f"ALTER TABLE `{table}` CONVERT TO CHARACTER SET utf8mb4 "
                "COLLATE utf8mb4_unicode_ci"
            )


class Migration(migrations.Migration):

    dependencies = [
        ("fil", "0003_feed_redesign_fields"),
    ]

    operations = [
        migrations.RunPython(convert_to_utf8mb4, migrations.RunPython.noop),
    ]
