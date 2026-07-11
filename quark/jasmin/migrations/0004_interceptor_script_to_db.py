# Generated manually: store interceptor scripts in the database

import os

from django.conf import settings
from django.db import migrations, models


def forwards_copy_scripts(apps, schema_editor):
    JasminInterceptor = apps.get_model("jasmin", "JasminInterceptor")
    media_root = getattr(settings, "MEDIA_ROOT", None)

    for row in JasminInterceptor.objects.all():
        source = ""
        name = ""
        path = getattr(row, "script", None) or ""
        if path:
            name = os.path.basename(path)
            if media_root:
                full_path = os.path.join(str(media_root), path)
                if os.path.isfile(full_path):
                    with open(full_path, "r", encoding="utf-8", errors="replace") as handle:
                        source = handle.read()
        if not source:
            source = "# migrated empty interceptor script\nresult = True\n"
        row.script_name = name
        row.script_source = source
        row.save(update_fields=["script_name", "script_source"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("jasmin", "0003_interceptor_filters_blank"),
    ]

    operations = [
        migrations.AddField(
            model_name="jasmininterceptor",
            name="script_name",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Optional display name (e.g. uploaded filename).",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="jasmininterceptor",
            name="script_source",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Python 3 interception script source. This is what Jasmin receives as pyCode.",
            ),
        ),
        migrations.RunPython(forwards_copy_scripts, noop_reverse),
        migrations.AlterField(
            model_name="jasmininterceptor",
            name="script_source",
            field=models.TextField(
                help_text="Python 3 interception script source. This is what Jasmin receives as pyCode.",
            ),
        ),
        migrations.RemoveField(
            model_name="jasmininterceptor",
            name="script",
        ),
    ]
