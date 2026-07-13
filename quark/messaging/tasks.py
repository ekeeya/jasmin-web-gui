#
#  Copyright (c) 2026
#  Celery tasks for async bulk HTTP submit and external DLR forwarding.
#
from __future__ import annotations

import logging

import requests
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="quark.messaging.tasks.process_bulk_http_send")
def process_bulk_http_send(batch_id: str):
    """Submit queued bulk messages one-by-one via classic Jasmin HTTP /send."""
    from quark.messaging.models import OutboundMessage
    from quark.jasmin.connection import resolve_jasmin_connection
    from quark.messaging.clients import JasminHttpClient
    from quark.messaging.models import dlr_callback_url

    qs = OutboundMessage.objects.filter(
        batch_id=batch_id,
        status=OutboundMessage.STATUS_QUEUED,
    ).select_related("jasmin_user", "workspace").order_by("id")

    for message in qs.iterator():
        if not message.jasmin_user_id:
            message.status = OutboundMessage.STATUS_FAILED
            message.error_message = "Missing Jasmin user"
            message.save(update_fields=["status", "error_message", "modified_on"])
            continue
        try:
            connection = resolve_jasmin_connection(message.workspace)
            client = JasminHttpClient(base_url=connection.http_api_url)
            result = client.send(
                username=message.jasmin_user.username,
                password=message.jasmin_user.password,
                to=message.to_addr,
                content=message.content,
                from_addr=message.from_addr or "",
                dlr_level=int(message.dlr_level),
                priority=int(message.priority or 0),
                dlr_url=dlr_callback_url(),
            )
            message.submit_response = result.text
            message.submitted_at = timezone.now()
            if result.ok:
                message.status = OutboundMessage.STATUS_SUBMITTED
                message.jasmin_msg_id = result.message_id
                message.error_message = ""
            else:
                message.status = OutboundMessage.STATUS_FAILED
                message.error_message = result.error or result.text or "Submit failed"
            message.save(
                update_fields=[
                    "submit_response",
                    "submitted_at",
                    "status",
                    "jasmin_msg_id",
                    "error_message",
                    "modified_on",
                ]
            )
        except Exception as exc:
            logger.exception("Async bulk send failed for message %s", message.pk)
            message.status = OutboundMessage.STATUS_FAILED
            message.error_message = str(exc)[:2000]
            message.save(update_fields=["status", "error_message", "modified_on"])


@shared_task(
    name="quark.messaging.tasks.forward_external_dlr",
    bind=True,
    max_retries=5,
    default_retry_delay=60,
)
def forward_external_dlr(self, message_id: int, attempt: int = 1):
    """
    Fire-and-forget forward of a DLR payload to the workspace external channel URL.
    Retries up to workspace.external_dlr_max_retries with external_dlr_retry_delay_secs.
    """
    from quark.messaging.models import OutboundMessage

    try:
        message = OutboundMessage.objects.select_related("workspace").get(pk=message_id)
    except OutboundMessage.DoesNotExist:
        logger.warning("forward_external_dlr: message %s missing", message_id)
        return

    workspace = message.workspace
    url = (workspace.external_dlr_url or "").strip()
    if not url:
        return

    max_retries = int(workspace.external_dlr_max_retries or 5)
    delay = int(workspace.external_dlr_retry_delay_secs or 60)
    method = (workspace.external_dlr_method or "POST").upper()
    payload = message.external_dlr_payload()

    try:
        if method == "GET":
            response = requests.get(url, params=payload, timeout=15)
        else:
            # Prefer JSON so nested/mapping fields stay clear for external apps
            response = requests.post(url, json=payload, timeout=15)
        if response.status_code >= 400:
            raise requests.HTTPError(f"HTTP {response.status_code}: {response.text[:200]}")
        message.external_dlr_forwarded_at = timezone.now()
        message.save(update_fields=["external_dlr_forwarded_at", "modified_on"])
        logger.info(
            "Forwarded DLR for message %s to %s (attempt %s)",
            message_id,
            url,
            attempt,
        )
    except Exception as exc:
        logger.warning(
            "External DLR forward failed for message %s attempt %s/%s: %s",
            message_id,
            attempt,
            max_retries,
            exc,
        )
        if attempt < max_retries:
            raise self.retry(
                kwargs={"message_id": message_id, "attempt": attempt + 1},
                countdown=delay,
                exc=exc,
                max_retries=max_retries,
            )
        logger.error(
            "External DLR forward gave up for message %s after %s attempts",
            message_id,
            attempt,
        )


def enqueue_external_dlr_forward(message):
    """Schedule async external DLR forward if the workspace has a channel URL."""
    workspace = message.workspace
    if not workspace or not (workspace.external_dlr_url or "").strip():
        return
    forward_external_dlr.delay(message.pk, 1)
