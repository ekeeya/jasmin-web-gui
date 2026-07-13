from django.contrib import admin

from quark.messaging.models import OutboundMessage


@admin.register(OutboundMessage)
class OutboundMessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "workspace",
        "to_addr",
        "status",
        "jasmin_msg_id",
        "batch_kind",
        "created_on",
    )
    list_filter = ("status", "batch_kind", "workspace")
    search_fields = ("to_addr", "jasmin_msg_id", "batch_id", "content")
    readonly_fields = ("created_on", "modified_on", "submitted_at", "delivered_at", "last_dlr_at")
