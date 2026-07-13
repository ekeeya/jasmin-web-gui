#
#  Copyright (c) 2026
#  Outbound submit helpers: single, bulk (REST sendbatch or async HTTP /send).
#
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Optional

from django.conf import settings
from django.utils import timezone

from quark.jasmin.connection import resolve_jasmin_connection
from quark.jasmin.models import JasminUser
from quark.messaging.clients import JasminHttpClient, JasminRestClient
from quark.messaging.models import OutboundMessage, dlr_callback_url

logger = logging.getLogger(__name__)


@dataclass
class SendItem:
    to_addr: str
    content: str
    client_message_id: str = ""


@dataclass
class SubmitResult:
    batch_id: str
    mode: str  # "single" | "bulk_rest" | "bulk_async"
    message_count: int
    messages: list[OutboundMessage]
    jasmin_batch_ids: list[str]
    client_batch_id: str = ""


def _normalize_msisdn(raw: Any) -> str:
    value = str(raw or "").strip().replace(" ", "").replace("-", "")
    if value.startswith("+"):
        value = value[1:]
    return value


def _clean_client_id(raw: Any, *, field: str = "client_message_id") -> str:
    value = str(raw or "").strip()
    if not value:
        return ""
    if len(value) > 128:
        raise ValueError(f"'{field}' must be at most 128 characters")
    return value


def _destinations_with_client_ids(to_raw, client_message_id, client_message_ids, content: str) -> list[SendItem]:
    destinations = to_raw if isinstance(to_raw, list) else [to_raw]
    if not destinations:
        raise ValueError("'to' must not be empty")

    ids: list[str] = []
    if client_message_ids is not None:
        if not isinstance(client_message_ids, list):
            raise ValueError("'client_message_ids' must be a list")
        if len(client_message_ids) != len(destinations):
            raise ValueError("'client_message_ids' length must match 'to'")
        ids = [_clean_client_id(x) for x in client_message_ids]
    elif client_message_id:
        cid = _clean_client_id(client_message_id)
        if len(destinations) > 1:
            raise ValueError(
                "Use 'client_message_ids' (list) when 'to' has multiple destinations, "
                "or pass one 'client_message_id' per messages[] entry"
            )
        ids = [cid]
    else:
        ids = [""] * len(destinations)

    items: list[SendItem] = []
    for dest, cid in zip(destinations, ids):
        msisdn = _normalize_msisdn(dest)
        if not msisdn.isdigit() or len(msisdn) < 8 or len(msisdn) > 15:
            raise ValueError(f"Invalid destination number: {dest!r}")
        items.append(SendItem(to_addr=msisdn, content=content, client_message_id=cid))
    return items


def expand_send_payload(payload: dict) -> tuple[list[SendItem], str]:
    """
    Normalize API / service payloads into items + optional client_batch_id.

    Optional correlation fields:
      client_batch_id / broadcast_id  — applied to the whole submit
      client_message_id               — single destination
      client_message_ids              — parallel to a multi-value 'to'
      messages[].client_message_id    — per personalized entry
    """
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a JSON object")

    client_batch_id = _clean_client_id(
        payload.get("client_batch_id") or payload.get("broadcast_id"),
        field="client_batch_id",
    )
    items: list[SendItem] = []

    if "messages" in payload:
        messages = payload.get("messages")
        if not isinstance(messages, list) or not messages:
            raise ValueError("'messages' must be a non-empty list")
        for entry in messages:
            if not isinstance(entry, dict):
                raise ValueError("Each messages[] entry must be an object")
            content = (entry.get("content") or "").strip()
            if not content:
                raise ValueError("Each message requires non-empty 'content'")
            to_raw = entry.get("to")
            if to_raw is None:
                raise ValueError("Each message requires 'to'")
            items.extend(
                _destinations_with_client_ids(
                    to_raw,
                    entry.get("client_message_id") or entry.get("message_id"),
                    entry.get("client_message_ids"),
                    content,
                )
            )
        return items, client_batch_id

    content = (payload.get("content") or "").strip()
    if not content:
        raise ValueError("'content' is required")
    to_raw = payload.get("to")
    if to_raw is None:
        raise ValueError("'to' is required")
    items = _destinations_with_client_ids(
        to_raw,
        payload.get("client_message_id") or payload.get("message_id"),
        payload.get("client_message_ids"),
        content,
    )
    return items, client_batch_id


def batch_callback_url() -> str:
    base = getattr(settings, "JOYCE_PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
    return f"{base}/batch-callback"


def submit_outbound_message(
    *,
    workspace,
    jasmin_user: JasminUser,
    to_addr: str,
    content: str,
    from_addr: str = "",
    dlr_level: int = 3,
    priority: int = 0,
    batch_id: str = "",
    batch_kind: str = OutboundMessage.BATCH_SINGLE,
    client_batch_id: str = "",
    client_message_id: str = "",
    created_by=None,
) -> OutboundMessage:
    """Persist a message row and submit it to Jasmin /send."""
    callback = dlr_callback_url()
    message = OutboundMessage(
        workspace=workspace,
        jasmin_user=jasmin_user,
        to_addr=to_addr,
        from_addr=from_addr or "",
        content=content,
        dlr_level=int(dlr_level),
        priority=int(priority or 0),
        batch_id=batch_id or "",
        batch_kind=batch_kind,
        client_batch_id=client_batch_id or "",
        client_message_id=client_message_id or "",
        status=OutboundMessage.STATUS_QUEUED,
        created_by=created_by,
        modified_by=created_by,
    )
    message.save()

    connection = resolve_jasmin_connection(workspace)
    client = JasminHttpClient(base_url=connection.http_api_url)
    result = client.send(
        username=jasmin_user.username,
        password=jasmin_user.password,
        to=to_addr,
        content=content,
        from_addr=from_addr or "",
        dlr_level=int(dlr_level),
        priority=int(priority or 0),
        dlr_url=callback,
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
    message.modified_by = created_by
    message.save()
    return message


def submit_bulk(
    *,
    workspace,
    jasmin_user: JasminUser,
    recipients: list[str],
    content: str,
    from_addr: str = "",
    dlr_level: int = 3,
    created_by=None,
) -> tuple[str, list[OutboundMessage]]:
    """UI bulk helper: same content to many recipients (async or REST via submit_send)."""
    items = [SendItem(to_addr=r, content=content) for r in recipients]
    result = submit_send(
        workspace=workspace,
        jasmin_user=jasmin_user,
        items=items,
        from_addr=from_addr,
        dlr_level=dlr_level,
        created_by=created_by,
    )
    return result.batch_id, result.messages


def _create_queued_messages(
    *,
    workspace,
    jasmin_user: JasminUser,
    items: list[SendItem],
    from_addr: str,
    dlr_level: int,
    priority: int,
    batch_id: str,
    batch_kind: str,
    client_batch_id: str,
    created_by,
) -> list[OutboundMessage]:
    messages = [
        OutboundMessage(
            workspace=workspace,
            jasmin_user=jasmin_user,
            to_addr=item.to_addr,
            from_addr=from_addr or "",
            content=item.content,
            dlr_level=int(dlr_level),
            priority=int(priority or 0),
            batch_id=batch_id,
            batch_kind=batch_kind,
            client_batch_id=client_batch_id or "",
            client_message_id=item.client_message_id or "",
            status=OutboundMessage.STATUS_QUEUED,
            created_by=created_by,
            modified_by=created_by,
        )
        for item in items
    ]
    return OutboundMessage.objects.bulk_create(messages)


def _submit_via_rest(
    *,
    workspace,
    jasmin_user: JasminUser,
    messages: list[OutboundMessage],
    from_addr: str,
    dlr_level: int,
    priority: int,
    connection,
) -> list[str]:
    """Chunk and POST sendbatch. Returns Jasmin batch ids."""
    client = JasminRestClient(base_url=connection.rest_api_url)
    callback = dlr_callback_url()
    batch_cb = batch_callback_url()
    globals_ = {
        "dlr": "yes",
        "dlr-level": int(dlr_level),
        "dlr-method": "POST",
        "dlr-url": callback,
        "priority": int(priority or 0),
    }
    if from_addr:
        globals_["from"] = from_addr

    batch_config = {
        "callback_url": batch_cb,
        "errback_url": batch_cb,
    }

    # Group consecutive identical content for denser chunks
    same_chunk = int(getattr(settings, "JOYCE_SENDBATCH_SAME_CONTENT_CHUNK", 2000))
    personal_chunk = int(getattr(settings, "JOYCE_SENDBATCH_PERSONALIZED_CHUNK", 500))

    jasmin_batch_ids: list[str] = []
    # Build message groups: same content → one REST message with many tos
    groups: list[tuple[str, list[OutboundMessage]]] = []
    for msg in messages:
        if groups and groups[-1][0] == msg.content:
            groups[-1][1].append(msg)
        else:
            groups.append((msg.content, [msg]))

    # Flatten into REST payloads of limited size
    rest_chunks: list[tuple[list[dict], list[OutboundMessage]]] = []
    current_msgs: list[dict] = []
    current_objs: list[OutboundMessage] = []
    current_count = 0

    def flush():
        nonlocal current_msgs, current_objs, current_count
        if current_msgs:
            rest_chunks.append((current_msgs, current_objs))
        current_msgs, current_objs, current_count = [], [], 0

    for content, objs in groups:
        if len(objs) == 1:
            entry = {"to": objs[0].to_addr, "content": content}
            limit = personal_chunk
            if current_count + 1 > limit and current_msgs:
                flush()
            current_msgs.append(entry)
            current_objs.extend(objs)
            current_count += 1
            if current_count >= personal_chunk:
                flush()
        else:
            # Split large same-content groups
            for i in range(0, len(objs), same_chunk):
                part = objs[i : i + same_chunk]
                entry = {"to": [m.to_addr for m in part], "content": content}
                if current_msgs:
                    flush()
                rest_chunks.append(([entry], part))

    flush()

    for payload_msgs, objs in rest_chunks:
        result = client.sendbatch(
            username=jasmin_user.username,
            password=jasmin_user.password,
            messages=payload_msgs,
            globals_=globals_,
            batch_config=batch_config,
        )
        now = timezone.now()
        if result.ok and result.data:
            data = result.data.get("data") or {}
            jbid = str(data.get("batchId") or "")
            jasmin_batch_ids.append(jbid)
            OutboundMessage.objects.filter(pk__in=[m.pk for m in objs]).update(
                status=OutboundMessage.STATUS_SUBMITTED,
                jasmin_batch_id=jbid,
                submit_response=result.text[:2000],
                submitted_at=now,
                error_message="",
                modified_on=now,
            )
        else:
            err = result.error or result.text or "sendbatch failed"
            OutboundMessage.objects.filter(pk__in=[m.pk for m in objs]).update(
                status=OutboundMessage.STATUS_FAILED,
                submit_response=result.text[:2000],
                error_message=err[:2000],
                submitted_at=now,
                modified_on=now,
            )
            logger.error("REST sendbatch failed for workspace %s: %s", workspace.id, err)

    return jasmin_batch_ids


def submit_send(
    *,
    workspace,
    jasmin_user: JasminUser,
    items: list[SendItem],
    from_addr: str = "",
    dlr_level: int = 3,
    priority: int = 0,
    client_batch_id: str = "",
    created_by=None,
) -> SubmitResult:
    """
    Smart submit: one item → sync single send; many → REST sendbatch if available,
    else queue async HTTP /send (one-by-one via Celery).
    """
    if not items:
        raise ValueError("No messages to send")

    batch_id = uuid.uuid4().hex[:16]
    client_batch_id = (client_batch_id or "").strip()

    if len(items) == 1:
        msg = submit_outbound_message(
            workspace=workspace,
            jasmin_user=jasmin_user,
            to_addr=items[0].to_addr,
            content=items[0].content,
            from_addr=from_addr,
            dlr_level=dlr_level,
            priority=priority,
            batch_id=batch_id,
            batch_kind=OutboundMessage.BATCH_SINGLE,
            client_batch_id=client_batch_id,
            client_message_id=items[0].client_message_id,
            created_by=created_by,
        )
        return SubmitResult(
            batch_id=batch_id,
            mode="single",
            message_count=1,
            messages=[msg],
            jasmin_batch_ids=[],
            client_batch_id=client_batch_id,
        )

    connection = resolve_jasmin_connection(workspace)
    messages = _create_queued_messages(
        workspace=workspace,
        jasmin_user=jasmin_user,
        items=items,
        from_addr=from_addr,
        dlr_level=dlr_level,
        priority=priority,
        batch_id=batch_id,
        batch_kind=OutboundMessage.BATCH_BULK,
        client_batch_id=client_batch_id,
        created_by=created_by,
    )

    if connection.has_rest_api:
        jasmin_batch_ids = _submit_via_rest(
            workspace=workspace,
            jasmin_user=jasmin_user,
            messages=messages,
            from_addr=from_addr,
            dlr_level=dlr_level,
            priority=priority,
            connection=connection,
        )
        # Refresh from DB
        messages = list(
            OutboundMessage.objects.filter(batch_id=batch_id).order_by("id")
        )
        return SubmitResult(
            batch_id=batch_id,
            mode="bulk_rest",
            message_count=len(messages),
            messages=messages,
            jasmin_batch_ids=jasmin_batch_ids,
            client_batch_id=client_batch_id,
        )

    # Async one-by-one classic /send
    from quark.messaging.tasks import process_bulk_http_send

    process_bulk_http_send.delay(batch_id)
    return SubmitResult(
        batch_id=batch_id,
        mode="bulk_async",
        message_count=len(messages),
        messages=messages,
        jasmin_batch_ids=[],
        client_batch_id=client_batch_id,
    )


def apply_batch_callback(payload: dict) -> Optional[OutboundMessage]:
    """
    Update an OutboundMessage from a Jasmin REST sendbatch success/error callback.
    Parameters: batchId, to, status, statusText
    """
    from quark.messaging.clients import SUCCESS_MSG_ID_RE

    jbid = str(payload.get("batchId") or "").strip()
    to_addr = _normalize_msisdn(payload.get("to"))
    status_flag = str(payload.get("status") or "").strip()
    status_text = str(payload.get("statusText") or "")

    if not jbid or not to_addr:
        return None

    message = (
        OutboundMessage.objects.filter(jasmin_batch_id=jbid, to_addr=to_addr)
        .order_by("-created_on")
        .first()
    )
    if not message:
        message = (
            OutboundMessage.objects.filter(to_addr=to_addr, status=OutboundMessage.STATUS_SUBMITTED)
            .filter(jasmin_batch_id=jbid)
            .order_by("-created_on")
            .first()
        )
    if not message:
        return None

    match = SUCCESS_MSG_ID_RE.search(status_text)
    if match:
        message.jasmin_msg_id = match.group(1)

    if status_flag == "1" or status_flag.lower() in ("success", "true"):
        message.status = OutboundMessage.STATUS_SUBMITTED
        message.error_message = ""
    else:
        message.status = OutboundMessage.STATUS_FAILED
        message.error_message = status_text[:2000] or "Batch send failed"

    message.submit_response = status_text[:2000]
    if not message.submitted_at:
        message.submitted_at = timezone.now()
    message.save(
        update_fields=[
            "jasmin_msg_id",
            "status",
            "error_message",
            "submit_response",
            "submitted_at",
            "modified_on",
        ]
    )
    return message
