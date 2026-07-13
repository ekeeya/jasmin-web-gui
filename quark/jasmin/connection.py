#  Copyright (c) 2026
#
"""Resolve which Jasmin instance a workspace should talk to."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from django.conf import settings

from quark.utils.crypto import decrypt_secret


class JasminNotConfigured(Exception):
    """Workspace has not chosen demo or custom Jasmin yet."""


@dataclass(frozen=True)
class JasminEndpoint:
    host: str
    port: int
    username: str
    password: str


@dataclass(frozen=True)
class JasminConnection:
    router_pb: JasminEndpoint
    smpp_pb: JasminEndpoint
    http_api_url: str
    rest_api_url: str
    source: Literal["demo", "custom"]

    @property
    def endpoint_key(self) -> str:
        """Stable key for grouping workspaces that share the same Router PB."""
        r = self.router_pb
        return f"{r.host}:{r.port}:{r.username}:{self.http_api_url}"

    @property
    def has_rest_api(self) -> bool:
        return bool((self.rest_api_url or "").strip())


def _demo_connection() -> JasminConnection:
    """Server-wide Jasmin from JASMIN_* environment settings."""
    return JasminConnection(
        router_pb=JasminEndpoint(
            host=settings.JASMIN_ROUTER_PB_HOST,
            port=int(settings.JASMIN_ROUTER_PB_PORT),
            username=settings.JASMIN_ROUTER_PB_USERNAME,
            password=settings.JASMIN_ROUTER_PB_PASSWORD,
        ),
        smpp_pb=JasminEndpoint(
            host=settings.JASMIN_SMPP_PB_HOST,
            port=int(settings.JASMIN_SMPP_PB_PORT),
            username=settings.JASMIN_SMPP_PB_USERNAME,
            password=settings.JASMIN_SMPP_PB_PASSWORD,
        ),
        http_api_url=str(settings.JASMIN_HTTP_API_URL).rstrip("/"),
        rest_api_url=str(getattr(settings, "JASMIN_REST_API_URL", "") or "").rstrip("/"),
        source="demo",
    )


def resolve_jasmin_connection(workspace=None) -> JasminConnection:
    """
    Return the Jasmin endpoints for this workspace.

    Raises JasminNotConfigured when the workspace has not opted into demo or
    finished a custom connection yet.
    """
    if workspace is None:
        raise JasminNotConfigured("No workspace available to resolve Jasmin connection")

    link = getattr(workspace, "jasmin_link", "") or ""
    if link == workspace.JASMIN_LINK_DEMO:
        return _demo_connection()

    if link == workspace.JASMIN_LINK_CUSTOM:
        if not workspace.jasmin_custom_fields_complete():
            raise JasminNotConfigured(
                f"Workspace '{workspace.name}' custom Jasmin connection is incomplete"
            )
        return JasminConnection(
            router_pb=JasminEndpoint(
                host=workspace.jasmin_router_pb_host,
                port=int(workspace.jasmin_router_pb_port),
                username=workspace.jasmin_router_pb_username,
                password=decrypt_secret(workspace.jasmin_router_pb_password),
            ),
            smpp_pb=JasminEndpoint(
                host=workspace.jasmin_smpp_pb_host,
                port=int(workspace.jasmin_smpp_pb_port),
                username=workspace.jasmin_smpp_pb_username,
                password=decrypt_secret(workspace.jasmin_smpp_pb_password),
            ),
            http_api_url=str(workspace.jasmin_http_api_url).rstrip("/"),
            rest_api_url=str(getattr(workspace, "jasmin_rest_api_url", "") or "").rstrip("/"),
            source="custom",
        )

    raise JasminNotConfigured(
        f"Workspace '{workspace.name}' has not configured a Jasmin connection yet"
    )


def workspace_from_jasmin_model(obj) -> Optional[object]:
    """Best-effort workspace lookup from a BaseJasminModel instance."""
    if hasattr(obj, "workspace_id") and getattr(obj, "workspace_id", None):
        return obj.workspace
    if hasattr(obj, "group_id") and getattr(obj, "group_id", None):
        group = obj.group
        return getattr(group, "workspace", None)
    return None
