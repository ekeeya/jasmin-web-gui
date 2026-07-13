#
#  Copyright (c) 2026
#  Dashboard aggregations for Configure and Operate consoles.
#
from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
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

_FAIL_STATUSES = (
    OutboundMessage.STATUS_FAILED,
    OutboundMessage.STATUS_REJECTED,
    OutboundMessage.STATUS_EXPIRED,
)


def _delivery_rate(delivered: int, failed: int):
    decided = (delivered or 0) + (failed or 0)
    if not decided:
        return None
    return round(100.0 * (delivered or 0) / decided, 1)


def operate_dashboard_stats(workspace) -> dict:
    """Business-side outbound SMS metrics for the Operate dashboard."""
    qs = OutboundMessage.objects.filter(workspace=workspace)
    now = timezone.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=6)
    series_start = today - timedelta(days=13)
    fail_q = Q(status__in=_FAIL_STATUSES)

    totals = qs.aggregate(
        total=Count("id"),
        submitted=Count("id", filter=Q(status=OutboundMessage.STATUS_SUBMITTED)),
        acked=Count("id", filter=Q(status=OutboundMessage.STATUS_ACKED)),
        delivered=Count("id", filter=Q(status=OutboundMessage.STATUS_DELIVERED)),
        failed=Count("id", filter=fail_q),
        today=Count("id", filter=Q(created_on__gte=today)),
        today_delivered=Count(
            "id",
            filter=Q(created_on__gte=today, status=OutboundMessage.STATUS_DELIVERED),
        ),
        today_failed=Count("id", filter=Q(created_on__gte=today) & fail_q),
        week=Count("id", filter=Q(created_on__gte=week_ago)),
        week_delivered=Count(
            "id",
            filter=Q(created_on__gte=week_ago, status=OutboundMessage.STATUS_DELIVERED),
        ),
        week_failed=Count("id", filter=Q(created_on__gte=week_ago) & fail_q),
        bulk=Count("id", filter=Q(batch_kind=OutboundMessage.BATCH_BULK)),
        single=Count("id", filter=Q(batch_kind=OutboundMessage.BATCH_SINGLE)),
    )

    delivery_rate = _delivery_rate(totals.get("delivered") or 0, totals.get("failed") or 0)
    week_delivery_rate = _delivery_rate(
        totals.get("week_delivered") or 0, totals.get("week_failed") or 0
    )

    status_rows = list(qs.values("status").annotate(c=Count("id")).order_by("-c"))

    daily_raw = {
        row["day"]: row["c"]
        for row in (
            qs.filter(created_on__gte=series_start)
            .annotate(day=TruncDate("created_on"))
            .values("day")
            .annotate(c=Count("id"))
        )
        if row["day"] is not None
    }
    daily_series = []
    for offset in range(13, -1, -1):
        day = (today - timedelta(days=offset)).date()
        daily_series.append(
            {
                "date": day.isoformat(),
                "label": day.strftime("%b %d"),
                "count": daily_raw.get(day, 0),
            }
        )

    outcome_by_day = {
        row["day"]: row
        for row in (
            qs.filter(created_on__gte=series_start)
            .annotate(day=TruncDate("created_on"))
            .values("day")
            .annotate(
                delivered=Count(
                    "id", filter=Q(status=OutboundMessage.STATUS_DELIVERED)
                ),
                failed=Count("id", filter=fail_q),
            )
        )
        if row["day"] is not None
    }
    daily_outcomes = []
    for offset in range(13, -1, -1):
        day = (today - timedelta(days=offset)).date()
        row = outcome_by_day.get(day) or {}
        daily_outcomes.append(
            {
                "date": day.isoformat(),
                "label": day.strftime("%b %d"),
                "delivered": row.get("delivered") or 0,
                "failed": row.get("failed") or 0,
            }
        )

    user_rows = []
    for row in (
        qs.values("jasmin_user_id", "jasmin_user__username")
        .annotate(
            total=Count("id"),
            today=Count("id", filter=Q(created_on__gte=today)),
            week=Count("id", filter=Q(created_on__gte=week_ago)),
            delivered=Count("id", filter=Q(status=OutboundMessage.STATUS_DELIVERED)),
            failed=Count("id", filter=fail_q),
            bulk=Count("id", filter=Q(batch_kind=OutboundMessage.BATCH_BULK)),
            single=Count("id", filter=Q(batch_kind=OutboundMessage.BATCH_SINGLE)),
        )
        .order_by("-week", "-total")[:25]
    ):
        username = row["jasmin_user__username"] or "Unassigned"
        rate = _delivery_rate(row["delivered"] or 0, row["failed"] or 0)
        user_rows.append(
            {
                "username": username,
                "total": row["total"] or 0,
                "today": row["today"] or 0,
                "week": row["week"] or 0,
                "delivered": row["delivered"] or 0,
                "failed": row["failed"] or 0,
                "bulk": row["bulk"] or 0,
                "single": row["single"] or 0,
                "delivery_rate": rate,
            }
        )

    active_users_week = (
        qs.filter(created_on__gte=week_ago, jasmin_user_id__isnull=False)
        .values("jasmin_user_id")
        .distinct()
        .count()
    )
    enabled_users = JasminUser.objects.filter(
        group__workspace=workspace, enabled=True
    ).count()

    chart = {
        "volume_labels": [d["label"] for d in daily_series],
        "volume_counts": [d["count"] for d in daily_series],
        "outcome_labels": [d["label"] for d in daily_outcomes],
        "outcome_delivered": [d["delivered"] for d in daily_outcomes],
        "outcome_failed": [d["failed"] for d in daily_outcomes],
        "status_labels": [r["status"] for r in status_rows],
        "status_counts": [r["c"] for r in status_rows],
        "kind_labels": ["Single", "Bulk"],
        "kind_counts": [totals.get("single") or 0, totals.get("bulk") or 0],
        "user_labels": [u["username"] for u in user_rows[:10]],
        "user_week": [u["week"] for u in user_rows[:10]],
    }

    recent = list(qs.select_related("jasmin_user")[:8])

    return {
        "totals": totals,
        "delivery_rate": delivery_rate,
        "week_delivery_rate": week_delivery_rate,
        "status_rows": status_rows,
        "user_rows": user_rows,
        "daily_series": daily_series,
        "active_users_week": active_users_week,
        "enabled_users": enabled_users,
        "chart": chart,
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
