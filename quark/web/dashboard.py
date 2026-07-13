#
#  Copyright (c) 2026
#  Dashboard aggregations for Configure and Operate consoles.
#
from __future__ import annotations

from django.db.models import Count, Q
from django.utils import timezone

from quark.jasmin.models import (
    JasminFilter,
    JasminGroup,
    JasminHTTPConnector,
    JasminInterceptor,
    JasminRoute,
    JasminSMPPConnector,
    JasminUser,
)
from quark.messaging.models import OutboundMessage


def operate_dashboard_stats(workspace) -> dict:
    """Outbound SMS metrics for the Operate dashboard."""
    qs = OutboundMessage.objects.filter(workspace=workspace)
    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    totals = qs.aggregate(
        total=Count("id"),
        submitted=Count("id", filter=Q(status=OutboundMessage.STATUS_SUBMITTED)),
        acked=Count("id", filter=Q(status=OutboundMessage.STATUS_ACKED)),
        delivered=Count("id", filter=Q(status=OutboundMessage.STATUS_DELIVERED)),
        failed=Count(
            "id",
            filter=Q(
                status__in=[
                    OutboundMessage.STATUS_FAILED,
                    OutboundMessage.STATUS_REJECTED,
                    OutboundMessage.STATUS_EXPIRED,
                ]
            ),
        ),
        today=Count("id", filter=Q(created_on__gte=today)),
        today_delivered=Count(
            "id",
            filter=Q(created_on__gte=today, status=OutboundMessage.STATUS_DELIVERED),
        ),
        today_failed=Count(
            "id",
            filter=Q(
                created_on__gte=today,
                status__in=[
                    OutboundMessage.STATUS_FAILED,
                    OutboundMessage.STATUS_REJECTED,
                    OutboundMessage.STATUS_EXPIRED,
                ],
            ),
        ),
        bulk=Count("id", filter=Q(batch_kind=OutboundMessage.BATCH_BULK)),
        single=Count("id", filter=Q(batch_kind=OutboundMessage.BATCH_SINGLE)),
    )

    decided = (totals.get("delivered") or 0) + (totals.get("failed") or 0)
    delivery_rate = None
    if decided:
        delivery_rate = round(100.0 * (totals.get("delivered") or 0) / decided, 1)

    status_rows = list(
        qs.values("status").annotate(c=Count("id")).order_by("-c")
    )
    recent = list(qs.select_related("jasmin_user")[:12])

    return {
        "totals": totals,
        "delivery_rate": delivery_rate,
        "status_rows": status_rows,
        "recent": recent,
    }


def configure_dashboard_stats(workspace) -> dict:
    """Gateway inventory + readiness for the Configure dashboard."""
    groups = JasminGroup.objects.filter(workspace=workspace)
    users = JasminUser.objects.filter(group__workspace=workspace)
    smpp = JasminSMPPConnector.objects.filter(workspace=workspace)
    http = JasminHTTPConnector.objects.filter(workspace=workspace)
    filters = JasminFilter.objects.filter(workspace=workspace)
    routes = JasminRoute.objects.filter(workspace=workspace)
    interceptors = JasminInterceptor.objects.filter(workspace=workspace)

    counts = {
        "groups": groups.count(),
        "groups_active": groups.filter(is_active=True).count(),
        "users": users.count(),
        "users_enabled": users.filter(enabled=True).count(),
        "smpp": smpp.count(),
        "smpp_started": smpp.filter(is_active=True).count(),
        "smpp_stopped": smpp.filter(is_active=False).count(),
        "http": http.count(),
        "filters": filters.count(),
        "routes": routes.count(),
        "routes_mt": routes.filter(nature="MT").count(),
        "routes_mo": routes.filter(nature="MO").count(),
        "interceptors": interceptors.count(),
    }

    checklist = [
        {
            "key": "groups",
            "label": "Create at least one Jasmin group",
            "done": counts["groups"] > 0,
            "href": "/jasmingroup/",
        },
        {
            "key": "users",
            "label": "Add an enabled HTTP/SMPP user",
            "done": counts["users_enabled"] > 0,
            "href": "/jasminuser/",
        },
        {
            "key": "connectors",
            "label": "Configure an SMPP or HTTP connector",
            "done": (counts["smpp"] + counts["http"]) > 0,
            "href": "/jasminsmppconnector/",
        },
        {
            "key": "smpp_up",
            "label": "Start at least one SMPP connector",
            "done": counts["smpp"] == 0 or counts["smpp_started"] > 0,
            "optional": counts["smpp"] == 0,
            "href": "/jasminsmppconnector/",
        },
        {
            "key": "routes",
            "label": "Add an MT route for outbound traffic",
            "done": counts["routes_mt"] > 0,
            "href": "/jasminroute/",
        },
        {
            "key": "filters",
            "label": "Define filters (optional)",
            "done": counts["filters"] > 0,
            "optional": True,
            "href": "/jasminfilter/",
        },
    ]
    required = [c for c in checklist if not c.get("optional")]
    ready = all(c["done"] for c in required)
    done_required = sum(1 for c in required if c["done"])

    recent_smpp = list(smpp.order_by("-modified_on")[:8])
    recent_routes = list(routes.order_by("-modified_on")[:6])
    recent_users = list(users.select_related("group").order_by("-modified_on")[:6])

    return {
        "config_counts": counts,
        "checklist": checklist,
        "config_ready": ready,
        "checklist_progress": {"done": done_required, "total": len(required)},
        "recent_smpp": recent_smpp,
        "recent_routes": recent_routes,
        "recent_users": recent_users,
    }


# Backwards-compatible alias used by messaging.views
def dashboard_stats(workspace) -> dict:
    return operate_dashboard_stats(workspace)
