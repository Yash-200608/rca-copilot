"""Conversational nodes: router, edit (chat corrections), grounded Q&A."""
from __future__ import annotations

import re

from langgraph.config import get_stream_writer

from ...forms import STRING_LIST_PATHS, get_path
from ...services.grounding import quote_in_source
from .. import prompts
from ..common import RCAState, digest, put, source_excerpt, step, working_form
from ..llm import structured
from ..outputs import AnswerOut, EditPlan, RouteOut

SCALAR_EDITABLE = [
    "header.deviation_ref", "header.title", "header.investigation_lead", "incident.site", "incident.area", "incident.department",
    "incident.product_name", "incident.batch_size", "incident.process_stage", "incident.step_reference", "incident.occurrence_datetime",
    "incident.occurrence_end_datetime", "incident.detection_datetime", "incident.detection_method", "incident.reported_to_qa_datetime",
    "incident.reported_by", "incident.shift", "classification.event_type", "problem.problem_statement", "containment.batch_status",
    "containment.containment_scope", "impact.product_quality", "impact.patient_safety", "impact.suggested_disposition",
]
LABEL = {
    "incident.batch_numbers": "Batch number(s)", "incident.equipment_ids": "Equipment", "incident.instrument_ids": "Instruments",
    "incident.persons_involved": "Persons involved", "incident.product_name": "Product", "incident.site": "Site",
    "header.title": "Title", "header.deviation_ref": "Deviation reference", "incident.reported_by": "Reported by",
}
ITEM_FIELDS = {"root_causes": ("statement", "verification_test"), "capa": ("action", "owner", "due_date"),
               "evidence_gaps": ("item", "status"), "contributing_factors": ("statement",), "containment.immediate_actions": ("action", "when", "performed_by"),
               "problem.requirements": ("parameter", "requirement", "actual"), "timeline": ("when", "event")}


def _editable_index(form: dict) -> dict[str, str]:
    idx: dict[str, str] = {}
    for p in SCALAR_EDITABLE:
        idx[p] = str(get_path(form, p) or "")
    for p in STRING_LIST_PATHS | {"header.related_records"}:
        idx[p] = " | ".join(get_path(form, p) or [])
    for sec, fields in ITEM_FIELDS.items():
        for it in get_path(form, sec) or []:
            for f in fields:
                idx[f"{sec}.{it['id']}.{f}"] = str(it.get(f) or "")
    return idx


def _label(path: str) -> str:
    if path in LABEL:
        return LABEL[path]
    parts = path.split(".")
    return (parts[0] + " - " + parts[-1]).replace("_", " ") if len(parts) > 2 else parts[-1].replace("_", " ")


async def route(state: RCAState) -> dict:
    intent = state.get("intent", "auto")
    if intent != "auto":
        return {"intent": intent}
    msg = state.get("message", "").strip()
    if not msg:
        return {"intent": "full_analysis"}
    async with step("route", "Understanding your request") as s:
        out, meta = await structured(RouteOut, prompts.ROUTE, f"MESSAGE: {msg}", role="light", max_tokens=300, emit=get_stream_writer())
        s.used(meta)
        s.detail = out.intent
        return {"intent": out.intent}
    return {"intent": "question" if msg.endswith("?") else "edit"}


async def edit(state: RCAState) -> dict:
    patches: list[dict] = []
    w = get_stream_writer()
    async with step("edit", "Applying your correction to the form") as s:
        form = working_form(state)
        idx = _editable_index(form)
        listing = "\n".join(f"{p} = {v[:110]}" for p, v in idx.items() if v or p in SCALAR_EDITABLE[:12])
        user = f"EDITABLE FIELDS (path = current value):\n{listing}\n\nUSER MESSAGE: {state['message']}"
        out, meta = await structured(EditPlan, prompts.EDIT, user, role="light", max_tokens=900, emit=w)
        s.used(meta)
        changes = []
        for e in out.edits:
            if e.path not in idx:
                w({"type": "warning", "text": f"Ignored an edit to an unknown field ({e.path})."})
                continue
            old = idx[e.path]
            if e.path in STRING_LIST_PATHS or e.path == "header.related_records":
                if e.list_values is None:
                    continue
                new_val, new_txt = e.list_values, " | ".join(e.list_values)
            else:
                if e.value is None:
                    continue
                new_val, new_txt = e.value, e.value
            if new_txt == old:
                continue
            prov = {"by": "user", "via": "chat", "reviewed": False, "grounded": "user"}
            patches += put(state, e.path, new_val, prov=prov, mode="force")
            segs = e.path.split(".")
            if any(e.path.startswith(k + ".") for k in ITEM_FIELDS):  # field inside a list item: mark the item human-edited
                patches += put(state, ".".join(segs[:-1]) + ".meta.by", "user", mode="force")
            changes.append({"path": e.path, "label": _label(e.path), "old": old, "new": new_txt})
        text = (out.reply if not changes else "Done - " + "; ".join(f"{c['label']}: \"{c['old'] or 'empty'}\" -> \"{c['new']}\"" for c in changes) + ".")
        w({"type": "message", "text": text, "changes": changes})
        s.detail = f"{len(changes)} field(s) updated"
        return {"patches": patches}
    w({"type": "message", "text": "I could not apply that change automatically - please edit the field directly."})
    return {"patches": patches}


async def answer(state: RCAState) -> dict:
    w = get_stream_writer()
    async with step("answer", "Answering from the documents and analysis") as s:
        form = working_form(state)
        rcs = "\n".join(f"- {r['statement']} [{r['certainty']}]" for r in form["root_causes"])
        user = (f"FACTS:\n{digest(form)}\n\nROOT-CAUSE HYPOTHESES:\n{rcs or 'none yet'}\n\nSOURCE:\n{source_excerpt(state, 3200)}\n\nQUESTION: {state['message']}")
        out, meta = await structured(AnswerOut, prompts.ANSWER, user, role="light", max_tokens=700, emit=w)
        s.used(meta)
        cites = [c for c in out.citations if quote_in_source(c, state.get("source_text", ""))]
        w({"type": "message", "text": out.answer, "citations": cites})
        s.detail = f"{len(cites)} verified citation(s)"
        return {}
    w({"type": "message", "text": "I could not answer that right now."})
    return {}


async def no_source(state: RCAState) -> dict:
    """Guard: analysis needs a readable document. Scanned PDFs are never silently analysed."""
    w = get_stream_writer()
    blocked = state.get("blocked_docs", [])
    if blocked:
        text = ("I can't analyse " + ", ".join(blocked) + " - it has no extractable text (it looks like a scanned image), so OCR is required. "
                "Please paste the text of the report or upload a text-based PDF / email. I will not guess from an unreadable document.")
    else:
        text = "Please attach an incident report (PDF / .eml / .docx / .txt) or paste the text of the report or email first - then I can fill the form."
    w({"type": "warning", "text": text})
    w({"type": "message", "text": text})
    return {}
