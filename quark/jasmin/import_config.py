#
#  Copyright (c) 2026
#  By: Emmanuel Keeya
#
#  Pull live Jasmin configuration into Django for a workspace.
#  Always uses run_on_reactor=False — this never writes back to Jasmin.
#
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import date, time
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
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
from quark.jasmin.reactor import run_in_reactor
from quark.jasmin.router_pb import RouterPBInterface
from quark.jasmin.smpp_pb import SmppPBAdapter
from quark.jasmin.utils.filters import ALL, MO, MT
from quark.jasmin.utils.utils import from_jasmin_mt_creds, from_jasmin_smpp_creds

logger = logging.getLogger(__name__)

# Jasmin stores user passwords as MD5 digests — not recoverable as plaintext.
IMPORTED_PASSWORD_PLACEHOLDER = "*imported*"

IMPORT_TIMEOUT = 120


@dataclass
class ImportStats:
    groups_created: int = 0
    groups_updated: int = 0
    users_created: int = 0
    users_updated: int = 0
    smpp_created: int = 0
    smpp_updated: int = 0
    http_created: int = 0
    http_updated: int = 0
    filters_created: int = 0
    filters_updated: int = 0
    routes_created: int = 0
    routes_updated: int = 0
    interceptors_created: int = 0
    interceptors_updated: int = 0
    skipped: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "groups": {"created": self.groups_created, "updated": self.groups_updated},
            "users": {"created": self.users_created, "updated": self.users_updated},
            "smpp_connectors": {"created": self.smpp_created, "updated": self.smpp_updated},
            "http_connectors": {"created": self.http_created, "updated": self.http_updated},
            "filters": {"created": self.filters_created, "updated": self.filters_updated},
            "routes": {"created": self.routes_created, "updated": self.routes_updated},
            "interceptors": {
                "created": self.interceptors_created,
                "updated": self.interceptors_updated,
            },
            "skipped": self.skipped[:20],
            "errors": self.errors[:20],
            "notes": self.notes,
        }

    def summary_message(self) -> str:
        parts = [
            f"groups {self.groups_created + self.groups_updated}",
            f"users {self.users_created + self.users_updated}",
            f"SMPP {self.smpp_created + self.smpp_updated}",
            f"HTTP {self.http_created + self.http_updated}",
            f"filters {self.filters_created + self.filters_updated}",
            f"routes {self.routes_created + self.routes_updated}",
            f"interceptors {self.interceptors_created + self.interceptors_updated}",
        ]
        msg = "Imported: " + ", ".join(parts) + "."
        if self.errors:
            msg += f" {len(self.errors)} error(s)."
        return msg


def _audit(obj, user):
    if user is None:
        return
    if not getattr(obj, "pk", None) or not getattr(obj, "created_by_id", None):
        obj.created_by = user
    obj.modified_by = user


def _route_entries(raw_list) -> List[Tuple[int, Any]]:
    """Normalize [{order: route}, ...] into [(order, route), ...]."""
    entries = []
    for item in raw_list or []:
        if isinstance(item, dict):
            for order, route in item.items():
                entries.append((int(order), route))
        else:
            # Unexpected shape — skip
            continue
    return entries


def _route_connectors(route) -> list:
    conn = getattr(route, "connector", None)
    if conn is None:
        return []
    if isinstance(conn, (list, tuple)):
        return list(conn)
    return [conn]


def _is_http_connector(connector) -> bool:
    ctype = getattr(connector, "_type", None) or ""
    return str(ctype).lower() == "http" or connector.__class__.__name__ == "HttpConnector"


def _filter_nature(jasmin_filter, context_nature: str) -> str:
    used = getattr(jasmin_filter.__class__, "usedFor", None) or []
    used = [str(u).lower() for u in used]
    if used == ["mo"]:
        return MO
    if used == ["mt"]:
        return MT
    if "mo" in used and "mt" in used:
        return ALL
    return context_nature if context_nature in (MO, MT) else ALL


def _filter_param(jasmin_filter) -> Optional[dict]:
    name = jasmin_filter.__class__.__name__
    if name == "TransparentFilter":
        return None
    if name == "UserFilter":
        user = getattr(jasmin_filter, "user", None)
        uid = getattr(user, "uid", None) or getattr(user, "username", None)
        return {"key": "uid", "value": str(uid)} if uid else None
    if name == "GroupFilter":
        group = getattr(jasmin_filter, "group", None)
        gid = getattr(group, "gid", None)
        return {"key": "gid", "value": str(gid)} if gid else None
    if name == "ConnectorFilter":
        connector = getattr(jasmin_filter, "connector", None)
        cid = getattr(connector, "cid", None)
        return {"key": "cid", "value": str(cid)} if cid else None
    if name == "SourceAddrFilter":
        pattern = getattr(jasmin_filter, "source_addr", None)
        value = getattr(pattern, "pattern", pattern)
        return {"key": "source_addr", "value": str(value)} if value is not None else None
    if name == "DestinationAddrFilter":
        pattern = getattr(jasmin_filter, "destination_addr", None)
        value = getattr(pattern, "pattern", pattern)
        return {"key": "destination_addr", "value": str(value)} if value is not None else None
    if name == "ShortMessageFilter":
        pattern = getattr(jasmin_filter, "short_message", None)
        value = getattr(pattern, "pattern", pattern)
        return {"key": "short_message", "value": str(value)} if value is not None else None
    if name == "DateIntervalFilter":
        interval = getattr(jasmin_filter, "dateInterval", None) or []
        if len(interval) == 2:
            start, end = interval

            def _d(v):
                if isinstance(v, date):
                    return v.isoformat()
                return str(v)

            return {"key": "dateInterval", "value": f"{_d(start)};{_d(end)}"}
        return None
    if name == "TimeIntervalFilter":
        interval = getattr(jasmin_filter, "timeInterval", None) or []
        if len(interval) == 2:
            start, end = interval

            def _t(v):
                if isinstance(v, time):
                    return v.strftime("%H:%M:%S")
                return str(v)

            return {"key": "timeInterval", "value": f"{_t(start)};{_t(end)}"}
        return None
    if name == "TagFilter":
        tag = getattr(jasmin_filter, "tag", None)
        return {"key": "tag", "value": tag} if tag is not None else None
    if name == "EvalPyFilter":
        code = getattr(jasmin_filter, "pyCode", None) or ""
        return {"key": "pyCode", "value": code}
    return None


def _filter_fingerprint(filter_type: str, nature: str, param: Optional[dict]) -> str:
    raw = f"{filter_type}|{nature}|{param}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def _make_fid(workspace, filter_type: str, nature: str, param: Optional[dict]) -> str:
    fp = _filter_fingerprint(filter_type, nature, param)
    # fid max_length=64; keep stable & unique per workspace content
    base = f"f{workspace.id}_{fp}"
    return base[:64]


def _parse_rate(route) -> Optional[Decimal]:
    rate = getattr(route, "rate", None)
    if rate is None:
        return None
    try:
        return Decimal(str(rate))
    except (InvalidOperation, TypeError, ValueError):
        return None


def import_workspace_config(workspace, connection, *, user=None) -> ImportStats:
    """
    Fetch Jasmin config over PB and upsert into Django for ``workspace``.

    Does not write anything back to Jasmin. HTTP connectors are discovered from
    MO routes only (Jasmin has no HTTP-connector PB).
    """
    stats = ImportStats()
    stats.notes.append(
        "Filters are not listed by Jasmin over PB; they only exist on the active session "
        "inside routes and interceptors. Joyce tries to derive them from those objects. "
        "If derivation fails for a filter, it cannot be loaded into Joyce."
    )
    stats.notes.append(
        "User passwords cannot be imported (Jasmin stores MD5 hashes). "
        "New users get a placeholder password; set a real one before saving them back to Jasmin."
    )
    stats.notes.append(
        "HTTP connectors have no PB either; only ones referenced by MO routes are imported."
    )

    router = RouterPBInterface(connection)
    smpp = SmppPBAdapter(connection)

    try:
        router_snap = run_in_reactor(router.snapshot_for_import, timeout=IMPORT_TIMEOUT)
    except Exception as exc:
        stats.errors.append(f"Router PB snapshot failed: {exc}")
        logger.exception("Router PB snapshot failed for workspace %s", workspace.id)
        return stats

    try:
        smpp_snap = run_in_reactor(smpp.snapshot_for_import, timeout=IMPORT_TIMEOUT)
    except Exception as exc:
        stats.errors.append(f"SMPP PB snapshot failed: {exc}")
        logger.exception("SMPP PB snapshot failed for workspace %s", workspace.id)
        smpp_snap = []

    with transaction.atomic():
        groups_by_gid = _import_groups(workspace, router_snap.get("groups") or [], user, stats)
        smpp_by_cid = _import_smpp(workspace, smpp_snap or [], user, stats)

        mt_entries = _route_entries(router_snap.get("mt_routes"))
        mo_entries = _route_entries(router_snap.get("mo_routes"))
        mt_ix = _route_entries(router_snap.get("mt_interceptors"))
        mo_ix = _route_entries(router_snap.get("mo_interceptors"))

        http_by_cid = _import_http_from_mo_routes(workspace, mo_entries, user, stats)

        # Collect filters from routes + interceptors
        filter_cache: Dict[str, JasminFilter] = {}
        for nature, entries in ((MT, mt_entries), (MO, mo_entries), (MT, mt_ix), (MO, mo_ix)):
            for _order, obj in entries:
                for jf in getattr(obj, "filters", None) or []:
                    _upsert_filter(workspace, jf, nature, user, stats, filter_cache)

        _import_users(
            workspace,
            router_snap.get("users") or [],
            groups_by_gid,
            user,
            stats,
        )

        _import_routes(workspace, MT, mt_entries, filter_cache, smpp_by_cid, http_by_cid, user, stats)
        _import_routes(workspace, MO, mo_entries, filter_cache, smpp_by_cid, http_by_cid, user, stats)
        _import_interceptors(workspace, MT, mt_ix, filter_cache, user, stats)
        _import_interceptors(workspace, MO, mo_ix, filter_cache, user, stats)

        workspace.jasmin_config_last_imported_at = timezone.now()
        workspace.save(update_fields=["jasmin_config_last_imported_at", "modified_on"])

    return stats


def _import_groups(workspace, groups, user, stats) -> Dict[str, JasminGroup]:
    by_gid: Dict[str, JasminGroup] = {}
    for group in groups:
        gid = str(getattr(group, "gid", "") or "").strip()
        if not gid:
            stats.skipped.append("group with empty gid")
            continue
        if len(gid) > 16:
            stats.skipped.append(f"group gid too long for Joyce: {gid}")
            continue

        existing = JasminGroup.objects.filter(gid=gid).first()
        if existing and existing.workspace_id and existing.workspace_id != workspace.id:
            stats.skipped.append(f"group {gid} owned by another workspace")
            continue

        created = existing is None
        obj = existing or JasminGroup(gid=gid, workspace=workspace)
        obj.workspace = workspace
        obj.is_active = bool(getattr(group, "enabled", True))
        if not obj.description:
            obj.description = f"Imported from Jasmin ({gid})"
        _audit(obj, user)
        obj.save(run_on_reactor=False)
        by_gid[gid] = obj
        if created:
            stats.groups_created += 1
        else:
            stats.groups_updated += 1
    return by_gid


def _import_smpp(workspace, connectors, user, stats) -> Dict[str, JasminSMPPConnector]:
    by_cid: Dict[str, JasminSMPPConnector] = {}
    for item in connectors:
        try:
            obj, created = JasminSMPPConnector.from_smpp_client_config(
                item["config"],
                workspace,
                running=bool(item.get("running")),
                user=user,
            )
            by_cid[obj.cid] = obj
            if created:
                stats.smpp_created += 1
            else:
                stats.smpp_updated += 1
        except Exception as exc:
            cid = item.get("cid") or "?"
            stats.errors.append(f"SMPP {cid}: {exc}")
            logger.exception("Failed importing SMPP connector %s", cid)
    return by_cid


def _import_http_from_mo_routes(workspace, mo_entries, user, stats) -> Dict[str, JasminHTTPConnector]:
    by_cid: Dict[str, JasminHTTPConnector] = {}
    seen = set()
    for _order, route in mo_entries:
        for connector in _route_connectors(route):
            if not _is_http_connector(connector):
                continue
            cid = str(getattr(connector, "cid", "") or "").strip()
            if not cid or cid in seen:
                continue
            seen.add(cid)
            base_url = getattr(connector, "baseurl", None) or getattr(connector, "base_url", None) or ""
            method = (getattr(connector, "method", None) or "GET").upper()
            if method not in ("GET", "POST"):
                method = "GET"

            obj = JasminHTTPConnector.objects.filter(workspace=workspace, cid=cid).first()
            created = obj is None
            if created:
                obj = JasminHTTPConnector(
                    workspace=workspace,
                    cid=cid,
                    connector_type="HTTP",
                    base_url=base_url or "http://localhost/",
                    method=method,
                    description=f"Imported from Jasmin MO route ({cid})",
                )
            else:
                if base_url:
                    obj.base_url = base_url
                obj.method = method
            _audit(obj, user)
            obj.save()
            by_cid[cid] = obj
            if created:
                stats.http_created += 1
            else:
                stats.http_updated += 1
    return by_cid


def _upsert_filter(workspace, jasmin_filter, context_nature, user, stats, cache) -> Optional[JasminFilter]:
    filter_type = jasmin_filter.__class__.__name__
    nature = _filter_nature(jasmin_filter, context_nature)
    param = _filter_param(jasmin_filter)
    fid = _make_fid(workspace, filter_type, nature, param)
    cache_key = fid
    if cache_key in cache:
        return cache[cache_key]

    existing = JasminFilter.objects.filter(fid=fid).first()
    if existing and existing.workspace_id != workspace.id:
        # Collision with another workspace's generated fid — rare; salt and retry
        fid = (fid[:50] + "_" + str(workspace.id))[:64]
        existing = JasminFilter.objects.filter(fid=fid).first()
        if existing and existing.workspace_id != workspace.id:
            stats.skipped.append(f"filter {filter_type} fid conflict")
            return None

    # Also reuse same-workspace filter with matching content under a different fid
    if existing is None:
        qs = JasminFilter.objects.filter(
            workspace=workspace,
            filter_type=filter_type,
            nature=nature,
            param=param,
        )
        existing = qs.first()

    created = existing is None
    obj = existing or JasminFilter(fid=fid, workspace=workspace)
    obj.fid = obj.fid or fid
    obj.workspace = workspace
    obj.filter_type = filter_type
    obj.nature = nature
    obj.param = param
    _audit(obj, user)
    try:
        obj.save()
    except Exception as exc:
        stats.errors.append(f"filter {filter_type}: {exc}")
        logger.exception("Failed importing filter %s", filter_type)
        return None

    cache[cache_key] = obj
    if created:
        stats.filters_created += 1
    else:
        stats.filters_updated += 1
    return obj


def _import_users(workspace, users, groups_by_gid, user, stats):
    for jasmin_user in users:
        username = str(
            getattr(jasmin_user, "uid", None) or getattr(jasmin_user, "username", None) or ""
        ).strip()
        if not username:
            stats.skipped.append("user with empty username")
            continue

        group_obj = getattr(jasmin_user, "group", None)
        gid = str(getattr(group_obj, "gid", "") or "").strip()
        local_group = groups_by_gid.get(gid)
        if local_group is None:
            stats.skipped.append(f"user {username}: missing group {gid}")
            continue

        existing = JasminUser.objects.filter(username=username).first()
        if existing and existing.group_id and existing.group.workspace_id != workspace.id:
            stats.skipped.append(f"user {username} owned by another workspace")
            continue

        created = existing is None
        obj = existing or JasminUser(username=username, password=IMPORTED_PASSWORD_PLACEHOLDER)
        obj.group = local_group
        obj.enabled = bool(getattr(jasmin_user, "enabled", True))
        obj.mt_credential = from_jasmin_mt_creds(jasmin_user.mt_credential)
        obj.smpps_credential = from_jasmin_smpp_creds(jasmin_user.smpps_credential)
        if created or not obj.password:
            obj.password = IMPORTED_PASSWORD_PLACEHOLDER
        _audit(obj, user)
        obj.save(run_on_reactor=False)
        if created:
            stats.users_created += 1
        else:
            stats.users_updated += 1


def _import_routes(workspace, nature, entries, filter_cache, smpp_by_cid, http_by_cid, user, stats):
    for order, route in entries:
        router_type = route.__class__.__name__
        try:
            obj = JasminRoute.objects.filter(
                workspace=workspace, nature=nature, order=order
            ).first()
            created = obj is None
            if created:
                obj = JasminRoute(workspace=workspace, nature=nature, order=order)
            obj.router_type = router_type
            obj.rate = _parse_rate(route)
            _audit(obj, user)
            obj.save(run_on_reactor=False)

            # Wire M2M
            filter_objs = []
            for jf in getattr(route, "filters", None) or []:
                local = _upsert_filter(workspace, jf, nature, user, stats, filter_cache)
                if local:
                    filter_objs.append(local)
            obj.filters.set(filter_objs)

            smpp_objs = []
            http_objs = []
            for connector in _route_connectors(route):
                cid = str(getattr(connector, "cid", "") or "").strip()
                if not cid:
                    continue
                if _is_http_connector(connector):
                    local = http_by_cid.get(cid) or JasminHTTPConnector.objects.filter(
                        workspace=workspace, cid=cid
                    ).first()
                    if local:
                        http_objs.append(local)
                    else:
                        stats.skipped.append(f"route {nature}@{order}: missing HTTP {cid}")
                else:
                    local = smpp_by_cid.get(cid) or JasminSMPPConnector.objects.filter(
                        workspace=workspace, cid=cid
                    ).first()
                    if local:
                        smpp_objs.append(local)
                    else:
                        stats.skipped.append(f"route {nature}@{order}: missing SMPP {cid}")
            obj.smpp_connectors.set(smpp_objs)
            obj.http_connectors.set(http_objs)

            if created:
                stats.routes_created += 1
            else:
                stats.routes_updated += 1
        except Exception as exc:
            stats.errors.append(f"route {nature}@{order}: {exc}")
            logger.exception("Failed importing route %s@%s", nature, order)


def _import_interceptors(workspace, nature, entries, filter_cache, user, stats):
    for order, interceptor in entries:
        itype = interceptor.__class__.__name__
        # Normalize StaticMO/StaticMT class names already match InterceptorChoice
        try:
            script = getattr(interceptor, "script", None)
            source = getattr(script, "pyCode", None) or ""
            if not source.strip():
                stats.skipped.append(f"interceptor {nature}@{order}: empty script")
                continue

            obj = JasminInterceptor.objects.filter(
                workspace=workspace, nature=nature, order=order
            ).first()
            created = obj is None
            if created:
                obj = JasminInterceptor(
                    workspace=workspace,
                    nature=nature,
                    order=order,
                    script_source=source,
                )
            obj.interceptor_type = itype
            obj.order = 0 if itype == "DefaultInterceptor" else order
            obj.script_source = source
            if not obj.script_name:
                obj.script_name = f"imported_{nature}_{order}.py"
            _audit(obj, user)
            obj.save(run_on_reactor=False)

            filter_objs = []
            for jf in getattr(interceptor, "filters", None) or []:
                local = _upsert_filter(workspace, jf, nature, user, stats, filter_cache)
                if local:
                    filter_objs.append(local)
            obj.filters.set(filter_objs)

            if created:
                stats.interceptors_created += 1
            else:
                stats.interceptors_updated += 1
        except Exception as exc:
            stats.errors.append(f"interceptor {nature}@{order}: {exc}")
            logger.exception("Failed importing interceptor %s@%s", nature, order)
