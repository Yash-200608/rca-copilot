"""Audit trail: diff old vs new form on save and tag each change as AI-applied or user-edited."""
from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AuditLog

IGNORE_KEYS = {"meta"}


def _flat(node: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(node, dict):
        for k, v in node.items():
            if k in IGNORE_KEYS:
                continue
            out.update(_flat(v, f"{prefix}.{k}" if prefix else k))
    elif isinstance(node, list):
        if node and all(isinstance(i, dict) and i.get("id") for i in node):
            for it in node:
                out.update(_flat(it, f"{prefix}.{it['id']}"))
        else:
            out[prefix] = node
    else:
        out[prefix] = node
    return out


def _s(v: Any) -> str | None:
    if v is None or v == "" or v == []:
        return None
    return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)


ITEM = re.compile(r"^(.*?\.[a-z]+-[0-9a-f]{6})(?:\.|$)")
SUMMARY_FIELDS = ("statement", "action", "cause", "event", "item", "question", "parameter", "batch", "answer")


def diff_forms(old: dict, new: dict) -> list[tuple[str, str | None, str | None]]:
    """Field-level changes. A list item that was added or removed as a whole becomes ONE row (not one per field)."""
    a, b = _flat(old), _flat(new)
    old_items = {m.group(1) for k in a if (m := ITEM.match(k))}
    new_items = {m.group(1) for k in b if (m := ITEM.match(k))}
    changes: list[tuple[str, str | None, str | None]] = []
    added: set[str] = set()
    removed: set[str] = set()
    for path in sorted(set(a) | set(b)):
        if path.endswith(".id"):
            continue
        ov, nv = _s(a.get(path)), _s(b.get(path))
        if ov == nv:
            continue
        m = ITEM.match(path)
        if m and m.group(1) not in old_items:
            added.add(m.group(1))
        elif m and m.group(1) not in new_items:
            removed.add(m.group(1))
        else:
            changes.append((path, ov, nv))
    def summ(flat: dict, pref: str) -> str:
        for f in SUMMARY_FIELDS:
            v = flat.get(f"{pref}.{f}")
            if isinstance(v, str) and v.strip():
                return v.strip()[:160]
        return "(item)"
    for pref in sorted(added):
        changes.append((pref, None, "added: " + summ(b, pref)))
    for pref in sorted(removed):
        changes.append((pref, "removed: " + summ(a, pref), None))
    return changes


def _item_meta(form: dict, path: str) -> dict | None:
    """Find meta of the list item addressed by `section.<id>.field` paths."""
    segs = path.split(".")
    node: Any = form
    for seg in segs:
        if isinstance(node, dict):
            node = node.get(seg)
        elif isinstance(node, list):
            node = next((i for i in node if isinstance(i, dict) and i.get("id") == seg), None)
        else:
            return None
        if isinstance(node, dict) and "meta" in node:
            return node["meta"]
        if node is None:
            return None
    return None


def actor_kind(new_form: dict, new_prov: dict, path: str, ai_run_id: str | None) -> str:
    """'ai_applied' if the new value came from an AI run (provenance by=ai, unreviewed), else 'user_edit'."""
    p = new_prov.get(path)
    if p and p.get("by") == "ai":
        return "ai_applied"
    meta = _item_meta(new_form, path)
    if meta and meta.get("by") == "ai":
        return "ai_applied"
    return "user_edit"


async def write_diff(session: AsyncSession, investigation_id, old: dict, new: dict, new_prov: dict,
                     actor: str, role: str, ai_run_id=None, reason: str | None = None) -> int:
    n = 0
    for path, ov, nv in diff_forms(old, new):
        kind = actor_kind(new, new_prov, path, ai_run_id)
        session.add(AuditLog(
            investigation_id=investigation_id, actor="AI Copilot" if kind == "ai_applied" else actor,
            role="ai" if kind == "ai_applied" else role, action=kind, path=path,
            old_value=(ov or "")[:2000] or None, new_value=(nv or "")[:2000] or None, reason=reason,
            ai_run_id=ai_run_id,
        ))
        n += 1
    return n


async def log_event(session: AsyncSession, investigation_id, actor: str, role: str, action: str,
                    path: str = "", reason: str | None = None, new_value: str | None = None) -> None:
    session.add(AuditLog(investigation_id=investigation_id, actor=actor, role=role, action=action,
                         path=path, reason=reason, new_value=new_value))
