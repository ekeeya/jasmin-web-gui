# Generated manually for interceptor unique_together (workspace, nature, order)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("jasmin", "0001_initial"),
        ("workspace", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="jasmininterceptor",
            name="nature",
            field=models.CharField(
                choices=[("MO", "MO"), ("MT", "MT")],
                help_text="MO intercepts inbound SMS before routing; MT intercepts outbound SMS before routing.",
                max_length=2,
            ),
        ),
        migrations.AlterField(
            model_name="jasmininterceptor",
            name="interceptor_type",
            field=models.CharField(
                choices=[
                    ("DefaultInterceptor", "Default Interceptor"),
                    ("StaticMOInterceptor", "Static MO Interceptor"),
                    ("StaticMTInterceptor", "Static MT Interceptor"),
                ],
                default="DefaultInterceptor",
                help_text="DefaultInterceptor (order 0, no filters) or StaticMO/StaticMTInterceptor.",
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="jasmininterceptor",
            name="order",
            field=models.IntegerField(
                help_text="Interceptor order. DefaultInterceptor is always order 0 (lowest / fallback).",
            ),
        ),
        migrations.AlterField(
            model_name="jasmininterceptor",
            name="script",
            field=models.FileField(
                help_text="Upload a Python (.py) interception script. Jasmin copies the source into its core.",
                upload_to="jasmin/scripts/interceptors",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="jasmininterceptor",
            unique_together={("workspace", "nature", "order")},
        ),
    ]
