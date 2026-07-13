#
#  Copyright (c) 2026
#
import uuid

from django.utils import timezone

from quark.jasmin.models import JasminUser
from quark.jasmin.connection import resolve_jasmin_connection
from quark.messaging.clients import JasminHttpClient
from quark.messaging.models import OutboundMessage, dlr_callback_url


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
    batch_id = uuid.uuid4().hex[:16]
    messages = []
    for to_addr in recipients:
        messages.append(
            submit_outbound_message(
                workspace=workspace,
                jasmin_user=jasmin_user,
                to_addr=to_addr,
                content=content,
                from_addr=from_addr,
                dlr_level=dlr_level,
                batch_id=batch_id,
                batch_kind=OutboundMessage.BATCH_BULK,
                created_by=created_by,
            )
        )
    return batch_id, messages
