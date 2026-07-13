# Generated manually for client message/batch id mapping

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("messaging", "0003_batch_and_external_dlr"),
    ]

    operations = [
        migrations.AddField(
            model_name="outboundmessage",
            name="client_batch_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Optional external broadcast/batch id supplied by the caller",
                max_length=128,
            ),
        ),
        migrations.AddField(
            model_name="outboundmessage",
            name="client_message_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Optional external message id supplied by the caller for DLR correlation",
                max_length=128,
            ),
        ),
        migrations.AddIndex(
            model_name="outboundmessage",
            index=models.Index(
                fields=["workspace", "client_message_id"],
                name="msg_ws_client_msgid_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="outboundmessage",
            index=models.Index(
                fields=["workspace", "client_batch_id"],
                name="msg_ws_client_batch_idx",
            ),
        ),
    ]
