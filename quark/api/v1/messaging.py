#
#  Copyright (c) 2026
#  External Joyce Messaging API (token auth, single POST /send).
#
from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from quark.jasmin.connection import JasminNotConfigured
from quark.jasmin.models import JasminUser
from quark.messaging.authentication import MessagingAPITokenAuthentication
from quark.messaging.services import expand_send_payload, submit_send

logger = logging.getLogger(__name__)


class MessagingSendAPIView(APIView):
    """
    POST /api/v1/messaging/send/

    Single endpoint for one or many SMS. Joyce chooses single vs bulk from payload.
    Auth: Authorization: Bearer <workspace messaging_api_token>
    """

    authentication_classes = [MessagingAPITokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        workspace = getattr(request, "workspace", None)
        if not workspace or not workspace.messaging_api_enabled:
            return Response(
                {"error": "Messaging API is not enabled for this workspace"},
                status=status.HTTP_403_FORBIDDEN,
            )

        payload = request.data if isinstance(request.data, dict) else {}
        username = (payload.get("username") or "").strip()
        if not username:
            return Response(
                {"error": "'username' (Jasmin user) is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        jasmin_user = (
            JasminUser.objects.filter(
                username=username,
                group__workspace=workspace,
                enabled=True,
            )
            .select_related("group")
            .first()
        )
        if not jasmin_user:
            return Response(
                {"error": f"Enabled Jasmin user '{username}' not found in this workspace"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            items, client_batch_id = expand_send_payload(payload)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        from_addr = (payload.get("from") or payload.get("from_addr") or "").strip()
        try:
            dlr_level = int(payload.get("dlr_level") or payload.get("dlr-level") or 3)
        except (TypeError, ValueError):
            dlr_level = 3
        try:
            priority = int(payload.get("priority") or 0)
        except (TypeError, ValueError):
            priority = 0

        try:
            result = submit_send(
                workspace=workspace,
                jasmin_user=jasmin_user,
                items=items,
                from_addr=from_addr,
                dlr_level=dlr_level,
                priority=priority,
                client_batch_id=client_batch_id,
                created_by=request.user,
            )
        except JasminNotConfigured as exc:
            return Response({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception:
            logger.exception("Messaging send API failed")
            return Response(
                {"error": "Failed to submit messages"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "batch_id": result.batch_id,
                "client_batch_id": result.client_batch_id or None,
                "mode": result.mode,
                "message_count": result.message_count,
                "jasmin_batch_ids": result.jasmin_batch_ids,
                "messages": [
                    {
                        "id": m.pk,
                        "to": m.to_addr,
                        "status": m.status,
                        "client_message_id": m.client_message_id or None,
                        "client_batch_id": m.client_batch_id or None,
                        "jasmin_msg_id": m.jasmin_msg_id or None,
                        "error": m.error_message or None,
                    }
                    for m in result.messages[:100]
                ],
                "messages_truncated": len(result.messages) > 100,
            },
            status=status.HTTP_202_ACCEPTED
            if result.mode == "bulk_async"
            else status.HTTP_200_OK,
        )
