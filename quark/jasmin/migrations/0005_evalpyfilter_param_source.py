# EvalPyFilter: store Python source in param.value (not a filesystem path).
# Also drop the legacy max_length=100 on param so scripts can be larger than 100 chars.

import os

from django.db import migrations

import quark.jasmin.utils.utils


def forwards_evalpy_paths_to_source(apps, schema_editor):
    JasminFilter = apps.get_model("jasmin", "JasminFilter")

    for row in JasminFilter.objects.filter(filter_type="EvalPyFilter"):
        param = row.param
        if not isinstance(param, dict):
            continue
        value = param.get("value")
        if value is None:
            continue
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="replace")
        value = str(value).strip()
        if not value:
            continue

        looks_like_path = (
            "\n" not in value
            and value.endswith(".py")
            and (value.startswith("/") or value.startswith("./") or "\\" in value)
        )
        if not looks_like_path:
            # Already source (or a relative name without path separators) — leave as-is
            if param.get("key") != "pyCode":
                param["key"] = "pyCode"
                row.param = param
                row.save(update_fields=["param"])
            continue

        if os.path.isfile(value):
            with open(value, "r", encoding="utf-8", errors="replace") as handle:
                source = handle.read().strip()
            if not source:
                source = "# migrated empty EvalPyFilter script\nresult = True\n"
        else:
            source = (
                f"# migrated from missing path: {value}\n"
                "# Replace this stub with your real filter logic.\n"
                "result = True\n"
            )

        row.param = {"key": "pyCode", "value": source}
        row.save(update_fields=["param"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("jasmin", "0004_interceptor_script_to_db"),
    ]

    operations = [
        migrations.AlterField(
            model_name="jasminfilter",
            name="param",
            field=quark.jasmin.utils.utils.StructuredJSONField(
                blank=True,
                help_text=(
                    "Filter parameter as {'key': '...', 'value': '...'}. "
                    "For EvalPyFilter, key is pyCode and value is the Python source stored in the DB."
                ),
                null=True,
            ),
        ),
        migrations.RunPython(forwards_evalpy_paths_to_source, noop_reverse),
    ]
