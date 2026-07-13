#
#  Copyright (c) 2026
#  Outbound SMS message log and DLR state for Joyce.
#
from django.conf import settings
from django.db import models
from django.utils import timezone
from smartmin.models import SmartModel


class OutboundMessage(SmartModel):
    """
    One outbound SMS submitted through Joyce to Jasmin's HTTP API.

    Status progresses roughly:
      queued → submitted → (acked) → delivered | failed | expired | rejected
    DLRs from Jasmin's callback update status / dlr fields.
    """

    STATUS_QUEUED = "queued"
    STATUS_SUBMITTED = "submitted"
    STATUS_ACKED = "acked"
    STATUS_DELIVERED = "delivered"
    STATUS_FAILED = "failed"
    STATUS_EXPIRED = "expired"
    STATUS_REJECTED = "rejected"
    STATUS_UNKNOWN = "unknown"

    STATUS_CHOICES = (
        (STATUS_QUEUED, "Queued"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_ACKED, "Acknowledged"),
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_FAILED, "Failed"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_UNKNOWN, "Unknown"),
    )

    BATCH_SINGLE = "single"
    BATCH_BULK = "bulk"
    BATCH_CHOICES = (
        (BATCH_SINGLE, "Single"),
        (BATCH_BULK, "Bulk"),
    )

    workspace = models.ForeignKey(
        "workspace.WorkSpace",
        on_delete=models.CASCADE,
        related_name="outbound_messages",
    )
    jasmin_user = models.ForeignKey(
        "jasmin.JasminUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="outbound_messages",
        help_text="Jasmin HTTP API user used to submit this message",
    )
    batch_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        help_text="Shared id for messages submitted together in a bulk send",
    )
    batch_kind = models.CharField(
        max_length=16,
        choices=BATCH_CHOICES,
        default=BATCH_SINGLE,
    )

    to_addr = models.CharField(max_length=32, db_index=True)
    from_addr = models.CharField(max_length=32, blank=True, default="")
    content = models.TextField()
    coding = models.PositiveSmallIntegerField(default=0)

    dlr_level = models.PositiveSmallIntegerField(
        default=3,
        help_text="1=SMSC only, 2=terminal only, 3=both (Jasmin dlr-level)",
    )
    priority = models.PositiveSmallIntegerField(default=0)

    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_QUEUED,
        db_index=True,
    )
    jasmin_msg_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        help_text="Message id returned by Jasmin /send",
    )
    submit_response = models.TextField(blank=True, default="")
    error_message = models.TextField(blank=True, default="")

    dlr_status = models.CharField(max_length=64, blank=True, default="")
    dlr_raw = models.JSONField(default=dict, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    last_dlr_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "messaging_outbound_message"
        ordering = ("-created_on",)
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["workspace", "-created_on"]),
        ]

    def __str__(self):
        return f"{self.to_addr} [{self.status}] {self.jasmin_msg_id or '—'}"

    @classmethod
    def status_from_dlr(cls, dlr_status: str) -> str:
        """Map Jasmin / SMPP DLR status strings to our status enum."""
        if not dlr_status:
            return cls.STATUS_UNKNOWN
        key = str(dlr_status).strip().upper()
        mapping = {
            "DELIVRD": cls.STATUS_DELIVERED,
            "DELIVERED": cls.STATUS_DELIVERED,
            "ESME_ROK": cls.STATUS_ACKED,
            "ACCEPTD": cls.STATUS_ACKED,
            "ACCEPTED": cls.STATUS_ACKED,
            "ACKED": cls.STATUS_ACKED,
            "ENROUTE": cls.STATUS_SUBMITTED,
            "UNDELIV": cls.STATUS_FAILED,
            "UNDELIVERABLE": cls.STATUS_FAILED,
            "REJECTD": cls.STATUS_REJECTED,
            "REJECTED": cls.STATUS_REJECTED,
            "EXPIRED": cls.STATUS_EXPIRED,
            "DELETED": cls.STATUS_FAILED,
            "UNKNOWN": cls.STATUS_UNKNOWN,
        }
        return mapping.get(key, cls.STATUS_UNKNOWN)

    def apply_dlr(self, payload: dict):
        """Update this message from a Jasmin DLR callback payload."""
        raw = {str(k): (v if not hasattr(v, "urlencode") else str(v)) for k, v in dict(payload).items()}
        dlr_status = (
            raw.get("message_status")
            or raw.get("status")
            or raw.get("stat")
            or ""
        )
        self.dlr_status = str(dlr_status)[:64]
        self.dlr_raw = raw
        self.last_dlr_at = timezone.now()
        mapped = self.status_from_dlr(self.dlr_status)
        if mapped != self.STATUS_UNKNOWN:
            self.status = mapped
        if mapped == self.STATUS_DELIVERED and not self.delivered_at:
            self.delivered_at = self.last_dlr_at
        self.save(
            update_fields=[
                "dlr_status",
                "dlr_raw",
                "last_dlr_at",
                "status",
                "delivered_at",
                "modified_on",
            ]
        )


def dlr_callback_url() -> str:
    """Public URL Jasmin should call for delivery receipts."""
    configured = getattr(settings, "JOYCE_DLR_CALLBACK_URL", "") or ""
    if configured:
        return configured.rstrip("/")
    base = getattr(settings, "JOYCE_PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
    return f"{base}/dlr"
