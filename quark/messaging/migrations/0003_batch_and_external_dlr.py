# Generated manually for jasmin_batch_id + external DLR forward tracking

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("messaging", "0002_alter_outboundmessage_dlr_level"),
    ]

    operations = [
        migrations.AddField(
            model_name="outboundmessage",
            name="jasmin_batch_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Jasmin REST sendbatch id for the chunk that included this message",
                max_length=64,
            ),
        ),
        migrations.AddField(
            model_name="outboundmessage",
            name="external_dlr_forwarded_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
