#  Copyright (c) 2026
#
"""
Pull live Jasmin user credentials/quotas into Django on a per-workspace schedule.

Celery beat ticks this task frequently; each workspace's
``jasmin_user_sync_interval_mins`` decides whether it is due.
"""
from __future__ import annotations

import logging
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

    Uses a single RouterPB ``user_get_all`` call per run, then updates local rows
    for each due workspace. Does not push anything back to Jasmin.
    """
    from quark.jasmin.models import JasminUser
    from quark.jasmin.reactor import run_in_reactor
    from quark.jasmin.router_pb import RouterPBInterface
    from quark.workspace.models import WorkSpace

    now = timezone.now()
    due = _workspaces_due_for_sync(now=now)
    if not due:
        logger.debug("Jasmin user sync: no workspaces due")
        return {"synced_workspaces": 0, "synced_users": 0}

    try:
        remote_users = run_in_reactor(RouterPBInterface().get_all_users) or []
    except Exception as exc:
        logger.error("Jasmin user sync failed to fetch users: %s", exc)
        raise

    by_uid = {
        getattr(u, "uid", None) or getattr(u, "username", None): u
        for u in remote_users
    }

    synced_users = 0
    for workspace in due:
        locals_qs = JasminUser.objects.filter(group__workspace=workspace)
        for local in locals_qs.iterator():
            remote = by_uid.get(local.username)
            if remote is None:
                continue
            local.apply_jasmin_user(remote, save=True)
            synced_users += 1

        WorkSpace.objects.filter(pk=workspace.pk).update(jasmin_user_last_synced_at=now)
        logger.info(
            "Synced Jasmin users for workspace %s (%s)",
            workspace.prefix or workspace.pk,
            workspace.name,
        )

    result = {"synced_workspaces": len(due), "synced_users": synced_users}
    logger.info("Jasmin user sync finished: %s", result)
    return result
