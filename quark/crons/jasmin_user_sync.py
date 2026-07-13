#  Copyright (c) 2026
#
"""
Pull live Jasmin user credentials/quotas into Django on a per-workspace schedule.

Celery beat ticks this task frequently; each workspace's
``jasmin_user_sync_interval_mins`` decides whether it is due.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


def _workspaces_due_for_sync(*, now=None):
    from quark.workspace.models import WorkSpace

    now = now or timezone.now()
    qs = WorkSpace.objects.filter(is_active=True, is_suspended=False).exclude(
        jasmin_user_sync_interval_mins=0
    )
    due = []
    for workspace in qs.iterator():
        if not workspace.is_jasmin_ready():
            continue
        interval = int(workspace.jasmin_user_sync_interval_mins or 0)
        if interval <= 0:
            continue
        last = workspace.jasmin_user_last_synced_at
        if last is None or (now - last) >= timedelta(minutes=interval):
            due.append(workspace)
    return due


@shared_task(name="quark.crons.jasmin_user_sync.sync_jasmin_users")
def sync_jasmin_users():
    """
    Sync Jasmin user MT/SMPP credentials into Django for workspaces that are due.

    Fetches ``user_get_all`` once per distinct Jasmin endpoint, then updates
    local rows for each due workspace on that endpoint.
    """
    from quark.jasmin.connection import JasminNotConfigured, resolve_jasmin_connection
    from quark.jasmin.models import JasminUser
    from quark.jasmin.reactor import run_in_reactor
    from quark.jasmin.router_pb import RouterPBInterface
    from quark.workspace.models import WorkSpace

    now = timezone.now()
    due = _workspaces_due_for_sync(now=now)
    if not due:
        logger.debug("Jasmin user sync: no workspaces due")
        return {"synced_workspaces": 0, "synced_users": 0}

    by_endpoint = defaultdict(list)
    connections = {}
    for workspace in due:
        try:
            connection = resolve_jasmin_connection(workspace)
        except JasminNotConfigured as exc:
            logger.warning("Skipping workspace %s: %s", workspace.pk, exc)
            continue
        key = connection.endpoint_key
        connections[key] = connection
        by_endpoint[key].append(workspace)

    synced_users = 0
    synced_workspaces = 0
    for key, workspaces in by_endpoint.items():
        connection = connections[key]
        try:
            remote_users = run_in_reactor(RouterPBInterface(connection).get_all_users) or []
        except Exception as exc:
            logger.error("Jasmin user sync failed for endpoint %s: %s", key, exc)
            continue

        by_uid = {
            getattr(u, "uid", None) or getattr(u, "username", None): u
            for u in remote_users
        }

        for workspace in workspaces:
            locals_qs = JasminUser.objects.filter(group__workspace=workspace)
            for local in locals_qs.iterator():
                remote = by_uid.get(local.username)
                if remote is None:
                    continue
                local.apply_jasmin_user(remote, save=True)
                synced_users += 1

            WorkSpace.objects.filter(pk=workspace.pk).update(jasmin_user_last_synced_at=now)
            synced_workspaces += 1
            logger.info(
                "Synced Jasmin users for workspace %s (%s)",
                workspace.prefix or workspace.pk,
                workspace.name,
            )

    result = {"synced_workspaces": synced_workspaces, "synced_users": synced_users}
    logger.info("Jasmin user sync finished: %s", result)
    return result
