"""The canonical RCA form (a plain JSON document), path utilities, the patch protection
rules ("AI never overwrites what a human edited/reviewed") and small deterministic helpers."""
from __future__ import annotations

import re
import uuid
from typing import Any

SIX_M = ["man", "machine", "material", "method", "measurement", "environment"]
EVIDENCE_AREAS = ["Equipment", "Process", "Materials", "Analytical", "Personnel", "Environment", "Documentation", "Historical"]
LIST_PATHS = {
    "incident.batch_numbers", "incident.equipment_ids", "incident.instrument_ids", "incident.persons_involved",
    "header.related_records", "problem.requirements", "containment.immediate_actions", "timeline",
    "five_whys", "root_causes", "contributing_factors", "evidence_gaps", "capa", "impact.other_batches",
    "impact.cqas_affected", *[f"fishbone.{m}" for m in SIX_M],
}
STRING_LIST_PATHS = {
    "incident.batch_numbers", "incident.equipment_ids", "incident.instrument_ids",
    "incident.persons_involved", "impact.cqas_affected", "header.related_records",
}


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:6]}"


def default_form() -> dict:
    return {
        "header": {"deviation_ref": "", "related_records": [], "title": "", "investigation_lead": "", "target_date": ""},
        "incident": {
            "site": "", "area": "", "department": "", "product_name": "", "batch_numbers": [], "batch_size": "",
            "process_stage": "", "step_reference": "", "equipment_ids": [], "instrument_ids": [],
            "occurrence_datetime": "", "occurrence_end_datetime": "", "detection_datetime": "",
            "detection_method": "", "reported_to_qa_datetime": "", "reported_by": "", "shift": "",
            "persons_involved": [],
        },
        "classification": {
            "event_type": "", "suggested_class": "", "class_rationale": "", "severity": None, "occurrence": None,
            "detectability": None, "rpn": None, "recurrence": {"checked": False, "matches": []},
        },
        "problem": {"problem_statement": "", "originator_narrative": "", "requirements": []},
        "containment": {"immediate_actions": [], "batch_status": "", "containment_scope": ""},
        "timeline": [],
        "fishbone": {m: [] for m in SIX_M},
        "five_whys": [],
        "root_causes": [],
        "contributing_factors": [],
        "evidence_gaps": [],
        "impact": {
            "product_quality": "", "cqas_affected": [], "patient_safety": "", "other_batches": [],
            "other_batches_note": "", "validation_regulatory": "", "suggested_disposition": "", "disposition_note": "",
        },
        "capa": [],
        "summary": {"executive_summary": ""},
        "meta": {"extracted": False, "not_in_source": [], "whys_stopping": ""},
    }


# ---------------------------------------------------------------- path helpers
def _split(path: str) -> list[str]:
    return [p for p in path.split(".") if p != ""]


def _step(node: Any, seg: str) -> Any:
    """Descend one segment: dict key, list index, or list item id."""
    if isinstance(node, dict):
        return node.get(seg)
    if isinstance(node, list):
        if seg.isdigit() and int(seg) < len(node):
            return node[int(seg)]
        for it in node:
            if isinstance(it, dict) and it.get("id") == seg:
                return it
    return None


def get_path(form: dict, path: str) -> Any:
    node: Any = form
    for seg in _split(path):
        node = _step(node, seg)
        if node is None:
            return None
    return node


def set_path(form: dict, path: str, value: Any) -> bool:
    segs = _split(path)
    node: Any = form
    for seg in segs[:-1]:
        node = _step(node, seg)
        if node is None:
            return False
    last = segs[-1]
    if isinstance(node, dict):
        node[last] = value
        return True
    if isinstance(node, list):
        if last.isdigit() and int(last) < len(node):
            node[int(last)] = value
            return True
        for i, it in enumerate(node):
            if isinstance(it, dict) and it.get("id") == last:
                node[i] = value
                return True
    return False


# ------------------------------------------------------------ protection rules
def is_protected_scalar(prov: dict, path: str) -> bool:
    p = (prov or {}).get(path)
    return bool(p) and (p.get("by") == "user" or bool(p.get("reviewed")))


def is_protected_item(item: Any) -> bool:
    meta = item.get("meta") if isinstance(item, dict) else None
    return bool(meta) and (meta.get("by") == "user" or bool(meta.get("reviewed")))


def ai_meta(node: str, model: str, *, grounded: str = "inferred", confidence: str = "medium", quote: str | None = None) -> dict:
    return {"by": "ai", "node": node, "model": model, "grounded": grounded, "confidence": confidence,
            "quote": quote, "reviewed": False}


def _item_key(it: dict) -> str:
    return (it.get("statement") or it.get("action") or it.get("cause") or it.get("item") or it.get("event") or "").strip().lower()


def merge_list_fill(existing: list, new_items: list) -> tuple[list, int]:
    """Keep human-edited/reviewed items, replace the rest with the new AI items.
    Returns (merged list, number of previous AI items that were replaced)."""
    existing = existing or []
    kept = [it for it in existing if is_protected_item(it)]
    kept_keys = {_item_key(it) for it in kept if isinstance(it, dict)}
    fresh = [it for it in new_items if not (isinstance(it, dict) and _item_key(it) in kept_keys)]
    return kept + fresh, len(existing) - len(kept)


# -------------------------------------------------------------- denormalisation
def denormalise(form: dict) -> dict:
    inc, cls = form.get("incident", {}), form.get("classification", {})
    rcs = form.get("root_causes", [])
    top = rcs[0]["statement"] if rcs else ""
    text_bits = [
        form.get("header", {}).get("title", ""), inc.get("product_name", ""), inc.get("process_stage", ""),
        " ".join(inc.get("equipment_ids", [])), " ".join(inc.get("instrument_ids", [])),
        form.get("problem", {}).get("problem_statement", ""), top,
        " ".join(c.get("action", "") for c in form.get("capa", [])),
    ]
    return {
        "title": form.get("header", {}).get("title", "") or "(untitled investigation)",
        "product": inc.get("product_name", ""),
        "batch_numbers": inc.get("batch_numbers", []),
        "equipment_tags": [e.upper() for e in inc.get("equipment_ids", [])],
        "classification": cls.get("suggested_class", ""),
        "event_type": cls.get("event_type", ""),
        "root_cause_summary": top,
        "capa_count": len(form.get("capa", [])),
        "search_text": " ".join(b for b in text_bits if b),
    }


# ----------------------------------------------- spec vs actual (deterministic)
_NUM = re.compile(r"[-+]?\d[\d,]*\.?\d*")
_MAXWORDS = re.compile("\\bnmt\\b|not more than|<=|≤|\\bmax")
_MINWORDS = re.compile("\\bnlt\\b|not less than|>=|≥|\\bmin")


def _nums(text: str) -> list[float]:
    out = []
    for m in _NUM.findall(text or ""):
        try:
            out.append(float(m.replace(",", "")))
        except ValueError:
            pass
    return out


def evaluate_requirement(requirement: str, actual: str) -> str:
    """Return 'within' | 'outside' | 'unknown'. Understands NMT/NLT/<=/>=, 'a to b' and 'a-b' ranges.
    `actual` may list several values (e.g. min/max of an excursion): any value outside => 'outside'."""
    req = re.sub(r"(?<=\d)\s*-\s*(?=\d)", " to ", (requirement or "").strip().lower())
    acts = _nums(actual)
    limits = _nums(req)
    if not req or not acts or not limits:
        return "unknown"
    if _MAXWORDS.search(req):
        return "outside" if any(a > limits[0] for a in acts) else "within"
    if _MINWORDS.search(req):
        return "outside" if any(a < limits[0] for a in acts) else "within"
    if len(limits) >= 2:
        lo, hi = sorted(limits[:2])
        return "outside" if any(a < lo or a > hi for a in acts) else "within"
    return "unknown"


def rpn(sev: int | None, occ: int | None, det: int | None) -> int | None:
    return sev * occ * det if sev and occ and det else None
