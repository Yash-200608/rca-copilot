"""extract_incident: documents -> structured facts -> grounded patches for form sections 1-6."""
from __future__ import annotations

import asyncio
import re

from ...forms import ai_meta, evaluate_requirement, new_id
from ...services.grounding import ground_scalar, numbers_in_source, quote_in_source
from .. import prompts
from ..common import RCAState, put, step
from ..llm import structured
from ..outputs import DetailsOut, Fld, IdentityOut

CHUNK = 9000
# fields whose value is composed by the model rather than copied -> 'derived' if no quote supports them
COMPOSED = {"title", "problem_statement", "event_type", "batch_status", "detection_method"}
EVENT_TYPES = ["Process deviation (CPP/IPC)", "Equipment failure", "Utility failure", "OOS", "OOT", "Material/dispensing",
               "Documentation/GDP", "Data integrity", "Cleaning/cross-contamination", "Environmental", "Other"]
SCALAR_PATHS = {
    "deviation_ref": "header.deviation_ref", "title": "header.title", "site": "incident.site", "area": "incident.area",
    "department": "incident.department", "product_name": "incident.product_name", "process_stage": "incident.process_stage",
    "step_reference": "incident.step_reference", "batch_size": "incident.batch_size", "detection_method": "incident.detection_method",
    "shift": "incident.shift", "reported_by": "incident.reported_by", "occurrence_datetime": "incident.occurrence_datetime",
    "occurrence_end_datetime": "incident.occurrence_end_datetime", "detection_datetime": "incident.detection_datetime",
    "reported_to_qa_datetime": "incident.reported_to_qa_datetime", "event_type": "classification.event_type",
    "problem_statement": "problem.problem_statement", "batch_status": "containment.batch_status",
}
LABELS = {p: p.split(".")[-1].replace("_", " ") for p in SCALAR_PATHS.values()}


def _chunks(text: str) -> list[str]:
    if len(text) <= CHUNK:
        return [text]
    parts, cur = [], ""
    for para in re.split(r"\n\s*\n", text):
        if len(cur) + len(para) > CHUNK and cur:
            parts.append(cur)
            cur = ""
        cur += para + "\n\n"
    if cur.strip():
        parts.append(cur)
    return parts


def _merge_fld(a: Fld, b: Fld) -> Fld:
    return a if a.value else b


def _norm_event_type(v: str | None) -> str | None:
    if not v:
        return None
    for et in EVENT_TYPES:
        if v.strip().lower() == et.lower():
            return et
    low = v.lower()
    for et in EVENT_TYPES:
        if et.split(" ")[0].lower() in low:
            return et
    return "Other"


async def _extract_chunk(chunk: str, emit) -> tuple[IdentityOut, DetailsOut, list[dict]]:
    user = f"SOURCE:\n{chunk}"
    (ident, m1), (details, m2) = await asyncio.gather(
        structured(IdentityOut, prompts.IDENTITY, user, role="extract", max_tokens=2000, emit=emit),
        structured(DetailsOut, prompts.DETAILS, user, role="extract", max_tokens=2400, emit=emit,
                   validate=lambda o: None if (o.requirements or o.immediate_actions or o.timeline) else "all lists empty - the source contains requirements/actions/events"),
    )
    return ident, details, [m1, m2]


async def extract_incident(state: RCAState) -> dict:
    out_patches: list[dict] = []
    async with step("extract_incident", "Extracting incident facts from the documents") as s:
        from langgraph.config import get_stream_writer

        w = get_stream_writer()
        src = state["source_text"]
        idents, dets = [], []
        for ch in _chunks(src):
            i, d, metas = await _extract_chunk(ch, w)
            idents.append(i)
            dets.append(d)
            for m in metas:
                s.used(m)
        ident = idents[0]
        for other in idents[1:]:
            for name in IdentityOut.model_fields:
                setattr(ident, name, _merge_fld(getattr(ident, name), getattr(other, name)))
        not_in_source: list[str] = []
        n_ground = n_unver = 0

        for fname, path in SCALAR_PATHS.items():
            f: Fld = getattr(ident, fname)
            value = f.value.strip() if f.value else None
            if fname == "event_type":
                value = _norm_event_type(value)
            if not value:
                not_in_source.append(path)
                continue
            g = ground_scalar(value, f.quote, src)
            if g == "unverified" and fname in COMPOSED:
                # composed (not copied) text: judge it by its numbers only
                g = "derived" if numbers_in_source(value, src) else "unverified"
            n_ground += g == "grounded"
            n_unver += g == "unverified"
            meta = ai_meta("extract_incident", s.models[0] if s.models else "", grounded=g, confidence=f.confidence, quote=f.quote)
            out_patches += put(state, path, value, prov=meta)

        # string lists
        def vals(flds: list[Fld]) -> tuple[list[str], str]:
            seen, grounded_all = [], True
            for f in flds:
                v = (f.value or "").strip()
                if v and v not in seen:
                    seen.append(v)
                    grounded_all &= ground_scalar(v, f.quote, src) == "grounded"
            return seen, "grounded" if grounded_all else "unverified"

        def merged(attr: str) -> list[Fld]:
            return [f for d in dets for f in getattr(d, attr)]

        for attr, path in (("batch_numbers", "incident.batch_numbers"), ("equipment_ids", "incident.equipment_ids"),
                           ("instrument_ids", "incident.instrument_ids"), ("persons_involved", "incident.persons_involved"),
                           ("related_records", "header.related_records")):
            items, g = vals(merged(attr))
            if items:
                out_patches += put(state, path, items, prov=ai_meta("extract_incident", s.models[0] if s.models else "", grounded=g))
            else:
                not_in_source.append(path)

        # requirement vs actual (status computed in code, not by the LLM)
        reqs = []
        for d in dets:
            for r in d.requirements:
                reqs.append({"id": new_id("req"), "parameter": r.parameter, "requirement": r.requirement, "actual": r.actual,
                             "status": evaluate_requirement(r.requirement, r.actual), "quote": r.quote,
                             "meta": ai_meta("extract_incident", s.models[0] if s.models else "",
                                             grounded="grounded" if quote_in_source(r.quote, src) else "unverified", quote=r.quote)})
        out_patches += put(state, "problem.requirements", reqs)
        if not reqs:
            not_in_source.append("problem.requirements")
        acts = [{"id": new_id("act"), "action": a.action, "performed_by": a.performed_by or "", "when": a.when or "", "outcome": a.outcome or "",
                 "meta": ai_meta("extract_incident", s.models[0] if s.models else "", grounded="grounded" if quote_in_source(a.quote, src) else "unverified", quote=a.quote)}
                for d in dets for a in d.immediate_actions]
        out_patches += put(state, "containment.immediate_actions", acts)
        tl = [{"id": new_id("evt"), "when": e.when or "", "event": e.event, "source": e.source or "",
               "meta": ai_meta("extract_incident", s.models[0] if s.models else "", grounded="grounded" if quote_in_source(e.quote, src) else "unverified", quote=e.quote)}
              for d in dets for e in d.timeline]
        out_patches += put(state, "timeline", tl)

        missing = [m for d in dets for m in d.missing_information]
        # verbatim narrative of the first document, kept read-only for traceability
        narrative = state["sources"][0]["text"][:6000] if state.get("sources") else ""
        out_patches += put(state, "problem.originator_narrative", narrative, prov={"by": "system", "grounded": "grounded", "reviewed": True}, mode="force")
        out_patches += put(state, "meta.extracted", True, mode="force")
        out_patches += put(state, "meta.not_in_source", not_in_source, mode="force")
        s.detail = f"{len(SCALAR_PATHS) - len([p for p in not_in_source if p in SCALAR_PATHS.values()])} fields filled, {n_ground} source-verified, {n_unver} to verify; {len(reqs)} spec rows, {len(acts)} actions, {len(tl)} events"
        return {"patches": out_patches, "missing_info": missing}
    return {"patches": out_patches, "missing_info": []}
