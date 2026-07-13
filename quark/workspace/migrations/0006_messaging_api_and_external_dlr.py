# Generated manually for messaging API + external DLR channel

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workspace", "0005_drop_jasmin_mode_flag"),
    ]

    operations = [
        migrations.AddField(
            model_name="workspace",
            name="jasmin_rest_api_url",
            field=models.URLField(
                blank=True,
                default="",
                help_text="Jasmin RESTful API base (sendbatch). Optional; if empty, bulk uses async HTTP /send.",
                max_length=512,
            ),
        ),
        migrations.AddField(
            model_name="workspace",
            name="messaging_api_enabled",
            field=models.BooleanField(
                default=False,
                help_text="When enabled, external apps can POST SMS via Joyce's token-authenticated API.",
            ),
        ),
        migrations.AddField(
            model_name="workspace",
            name="messaging_api_token",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Bearer token for the Joyce messaging API. Regenerate from workspace settings.",
                max_length=64,
            ),
        ),
        migrations.AddField(
            model_name="workspace",
            name="external_dlr_url",
            field=models.URLField(
                blank=True,
                default="",
                help_text="Optional external channel URL. Joyce forwards DLRs here after internal handling.",
                max_length=512,
            ),
        ),
        migrations.AddField(
            model_name="workspace",
            name="external_dlr_method",
            field=models.CharField(
                choices=[("POST", "POST"), ("GET", "GET")],
                default="POST",
                help_text="HTTP method used when forwarding DLRs to the external channel.",
                max_length=8,
            ),
        ),
        migrations.AddField(
            model_name="workspace",
            name="external_dlr_retry_delay_secs",
            field=models.PositiveIntegerField(
                default=60,
                help_text="Seconds between external DLR forward retries (default 60).",
            ),
        ),
        migrations.AddField(
            model_name="workspace",
            name="external_dlr_max_retries",
            field=models.PositiveIntegerField(
                default=5,
                help_text="Max forward attempts to the external DLR URL (default 5).",
            ),
        ),
    ]
