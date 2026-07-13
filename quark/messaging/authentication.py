#
#  Copyright (c) 2026
#  Token authentication for Joyce messaging API.
#
from __future__ import annotations

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from quark.workspace.models import WorkSpace, User


class MessagingAPITokenAuthentication(BaseAuthentication):
    """
    Authenticate with:
      Authorization: Bearer <token>
    or
      X-Joyce-Token: <token>

    Resolves the workspace that owns the token. Sets request.workspace.
    """

    keyword = "Bearer"

    def authenticate(self, request):
        token = self._extract_token(request)
        if not token:
            return None

        workspace = (
            WorkSpace.objects.filter(
                messaging_api_enabled=True,
                messaging_api_token=token,
            )
            .exclude(messaging_api_token="")
            .first()
        )
        if not workspace:
            raise AuthenticationFailed("Invalid or disabled Joyce messaging API token")

        request.workspace = workspace
        # Synthetic user: workspace owner if available, else Anonymous-like staff proxy
        user = workspace.created_by if workspace.created_by_id else None
        if user is None:
            raise AuthenticationFailed("Workspace has no owner for API attribution")
        # Ensure we use the User proxy when possible
        if not isinstance(user, User):
            try:
                user = User.objects.get(pk=user.pk)
            except User.DoesNotExist:
                raise AuthenticationFailed("Workspace owner not found")
        return (user, token)

    def _extract_token(self, request) -> str:
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if header:
            parts = header.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                return parts[1].strip()
        return (request.META.get("HTTP_X_JOYCE_TOKEN") or "").strip()
