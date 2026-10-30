"""Analysis nodes: recurrence search, fishbone, 5 Whys, root causes, evidence gaps, CAPA, impact, summary."""
from __future__ import annotations

import json

from langgraph.config import get_stream_writer

from ...db import SessionLocal
from ...forms import SIX_M, ai_meta, new_id, rpn
from ...services.grounding import quote_in_source
from ...services.similar import find_similar as db_find_similar
from .. import prompts
from ..common import RCAState, digest, put, source_excerpt, step, working_form
from ..llm import structured
from ..outputs import CapaOut, FishboneOut, GapsOut, ImpactOut, RootCauseOut, SummaryOut, WhysOut

CLASS_ORDER = ["minor", "major", "critical"]


def _src(state: RCAState) -> str:
    return state.get("source_text", "")


def _m(s) -> str:
    return s.models[0] if s.models else ""


# ------------------------------------------------------------ recurrence
async def find_similar(state: RCAState) -> dict:
    patches: list[dict] = []
    async with step("find_similar", "Checking past investigations for recurrence") as s:
        form = working_form(state)
        async with SessionLocal() as session:
            matches = await db_find_similar(session, state["investigation_id"], form)
        rec = {"checked": True, "matches": matches}
        patches += put(state, "classification.recurrence", rec, mode="force")
        s.detail = f"{len(matches)} similar closed investigation(s)" if matches else "no similar closed investigation found"
        return {"patches": patches, "similar": matches}
    return {"patches": patches, "similar": []}


# -------------------------------------------------------------- fishbone
async def fishbone(state: RCAState) -> dict:
    patches: list[dict] = []
    async with step("fishbone", "Building fishbone (6M) analysis") as s:
        form = working_form(state)
        user = f"FACTS:\n{digest(form)}\n\nSOURCE:\n{source_excerpt(state, 3200)}"
        out, meta = await structured(FishboneOut, prompts.FISHBONE, user, role="light", max_tokens=2200, emit=get_stream_writer())
        s.used(meta)
        src, n = _src(state), 0
        for cat in SIX_M:
            items = []
            for c in getattr(out, cat):
                grounded = quote_in_source(c.evidence_quote, src)
                items.append({"id": new_id("fb"), "cause": c.cause, "evidence_area": c.evidence_area, "disposition": c.disposition,
                              "evidence_quote": c.evidence_quote if grounded else None, "rationale": c.rationale,
                              "meta": ai_meta("fishbone", meta["model"], grounded="grounded" if grounded else "hypothesis", quote=c.evidence_quote if grounded else None)})
            n += len(items)
            patches += put(state, f"fishbone.{cat}", items)
        s.detail = f"{n} candidate causes across 6 categories"
        return {"patches": patches}
    return {"patches": patches}


# ----------------------------------------------------------------- whys
async def five_whys(state: RCAState) -> dict:
    patches: list[dict] = []
    async with step("five_whys", "Running 5 Whys") as s:
        form = working_form(state)
        user = f"FACTS:\n{digest(form)}\n\nSOURCE:\n{source_excerpt(state, 3200)}"
        out, meta = await structured(WhysOut, prompts.WHYS, user, role="mid", max_tokens=1500, emit=get_stream_writer())
        s.used(meta)
        src = _src(state)
        items = []
        for i, w in enumerate(out.whys, 1):
            ok = quote_in_source(w.quote, src)
            basis = "evidence" if (w.basis == "evidence" and ok) else "hypothesis"
            items.append({"id": new_id("why"), "level": i, "question": w.question, "answer": w.answer, "basis": basis,
                          "quote": w.quote if ok else None,
                          "meta": ai_meta("five_whys", meta["model"], grounded="grounded" if basis == "evidence" else "hypothesis", quote=w.quote if ok else None)})
        patches += put(state, "five_whys", items)
        patches += put(state, "meta.whys_stopping", out.stopping_rationale, mode="force")
        s.detail = f"{len(items)} levels ({sum(1 for i in items if i['basis'] == 'evidence')} evidence-backed)"
        return {"patches": patches}
    return {"patches": patches}


# ------------------------------------------------------------ root cause
def _cause_items(out_list, node: str, model: str, src: str, kind: str) -> list[dict]:
    items = []
    for c in out_list:
        support = [{"quote": e.quote, "source": e.source, "found": quote_in_source(e.quote, src)} for e in c.supporting_evidence]
        found = sum(1 for e in support if e["found"])
        certainty, conf = c.certainty, c.confidence
        assumptions = list(c.assumptions)
        if support and not found:
            certainty, conf = "possible", "low"
            assumptions.append("None of the quoted supporting excerpts could be verified in the source documents.")
        items.append({
            "id": new_id("rc" if kind == "rc" else "cf"), "statement": c.statement, "category_6m": c.category_6m,
            "evidence_area": c.evidence_area, "subcategory": c.subcategory, "certainty": certainty, "confidence": conf,
            "supporting_evidence": support, "contradicting_evidence": list(c.contradicting_evidence), "assumptions": assumptions,
            "missing_evidence": list(c.missing_evidence), "verification_test": c.verification_test,
            "human_error_flag": c.human_error_flag, "human_error_justification": c.human_error_justification or "",
            "meta": ai_meta(node, model, grounded="hypothesis", confidence=conf),
        })
    return items


def _incomplete(items: list[dict]) -> list[str]:
    bad = []
    for it in items:
        miss = [k for k in ("supporting_evidence", "contradicting_evidence", "assumptions", "missing_evidence", "verification_test") if not it.get(k)]
        if miss:
            bad.append(f"'{it['statement'][:60]}' lacks: {', '.join(miss)}")
    return bad


async def root_cause(state: RCAState) -> dict:
    patches: list[dict] = []
    async with step("root_cause", "Synthesising root-cause hypotheses") as s:
        form = working_form(state)
        fb = "\n".join(f"{cat.upper()}: " + "; ".join(f"{c['cause']} [{c['disposition']}]" for c in form["fishbone"][cat]) for cat in SIX_M if form["fishbone"][cat])
        whys = "\n".join(f"{w['level']}. {w['question']} -> {w['answer']} ({w['basis']})" for w in form["five_whys"])
        rec = "; ".join(f"{m['rca_number']}: {m['root_cause']} (CAPA: {m['capa_summary'][:100]}; outcome: {m.get('capa_outcome') or 'n/a'})" for m in state.get("similar", []))
        user = (f"FACTS:\n{digest(form)}\n\nFISHBONE:\n{fb or 'n/a'}\n\n5 WHYS:\n{whys or 'n/a'}\n\n"
                f"PAST SIMILAR INVESTIGATIONS: {rec or 'none'}\n\nSOURCE:\n{source_excerpt(state, 3000)}")
        out, meta = await structured(RootCauseOut, prompts.ROOT_CAUSE, user, role="heavy", max_tokens=3200, emit=get_stream_writer())
        s.used(meta)
        src = _src(state)
        rcs = _cause_items(out.root_causes, "root_cause", meta["model"], src, "rc")
        cfs = _cause_items(out.contributing_factors, "root_cause", meta["model"], src, "cf")
        bad = _incomplete(rcs)
        if bad:  # one repair pass: the evidence blocks are mandatory
            user2 = user + "\n\nYOUR PREVIOUS ANSWER WAS INCOMPLETE: " + " | ".join(bad) + "\nReturn the full corrected JSON with every evidence block filled."
            out2, meta2 = await structured(RootCauseOut, prompts.ROOT_CAUSE, user2, role="heavy", max_tokens=3200, emit=get_stream_writer())
            s.used(meta2)
            rcs = _cause_items(out2.root_causes, "root_cause", meta2["model"], src, "rc")
            cfs = _cause_items(out2.contributing_factors, "root_cause", meta2["model"], src, "cf")
        patches += put(state, "root_causes", rcs)
        patches += put(state, "contributing_factors", cfs)
        s.detail = f"{len(rcs)} root-cause hypotheses, {len(cfs)} contributing factors (all labelled hypotheses)"
        return {"patches": patches}
    return {"patches": patches}


# ---------------------------------------------------------- evidence gaps
async def evidence_gaps(state: RCAState) -> dict:
    patches: list[dict] = []
    async with step("evidence_gaps", "Identifying missing evidence") as s:
        form = working_form(state)
        miss = list(state.get("missing_info", []))
        for rc in [*form["root_causes"], *form["contributing_factors"]]:
            miss += [f"[for cause '{rc['statement'][:60]}'] {m}" for m in rc.get("missing_evidence", [])]
        times_missing = [k.replace("_", " ") for k in ("occurrence_datetime", "detection_datetime", "reported_to_qa_datetime") if not form["incident"].get(k)]
        if times_missing:
            miss.append("Not recorded: " + ", ".join(times_missing))
        user = (f"FACTS:\n{digest(form)}\n\nROOT CAUSES:\n" + "\n".join(f"- {r['statement']}" for r in form["root_causes"]) +
                "\n\nMISSING_INFORMATION:\n" + "\n".join(f"- {m}" for m in miss[:40]))
        out, meta = await structured(GapsOut, prompts.GAPS, user, role="light", max_tokens=2200, emit=get_stream_writer())
        s.used(meta)
        items = [{"id": new_id("gap"), "item": g.item, "evidence_area": g.evidence_area, "why_needed": g.why_needed, "linked_to": g.linked_to or "",
                  "priority": g.priority, "suggested_owner": g.suggested_owner, "status": "open",
                  "meta": ai_meta("evidence_gaps", meta["model"], grounded="inferred")} for g in out.gaps]
        patches += put(state, "evidence_gaps", items)
        s.detail = f"{len(items)} evidence gaps ({sum(1 for g in items if g['priority'] == 'high')} high priority)"
        return {"patches": patches}
    return {"patches": patches}


# ------------------------------------------------------------------ CAPA
def _capa_items(out: CapaOut, rcs: list[dict], model: str) -> list[dict]:
    items = []
    for a in out.actions:
        linked = []
        if 0 <= a.linked_cause_index < len(rcs):
            linked = [rcs[a.linked_cause_index]["id"]]
        strength = a.strength
        if strength != "training" and any(w in a.action.lower() for w in ("retrain", "re-train", "training session")) and "interlock" not in a.action.lower():
            strength = "training"
        items.append({"id": new_id("capa"), "type": a.type, "action": a.action, "rationale": a.rationale, "linked_to": linked,
                      "strength": strength, "owner_role": a.owner_role, "owner": "", "due_days": a.due_days, "due_date": "",
                      "change_control": a.change_control_needed,
                      "effectiveness": {"criterion": a.effectiveness_criterion or "", "method": a.effectiveness_method or "", "window": a.effectiveness_window or ""},
                      "status": "proposed", "meta": ai_meta("capa", model, grounded="inferred")})
    return items


def _weak_causes(items: list[dict], rcs: list[dict]) -> list[int]:
    weak = []
    for i, rc in enumerate(rcs):
        linked = [c for c in items if rc["id"] in c["linked_to"] and c["type"] != "correction"]
        if not any(c["type"] == "corrective" for c in linked) or (linked and all(c["strength"] == "training" for c in linked)):
            weak.append(i)
    return weak


async def capa(state: RCAState) -> dict:
    patches: list[dict] = []
    async with step("capa", "Recommending CAPA (correction / corrective / preventive)") as s:
        form = working_form(state)
        rcs = form["root_causes"]
        if not rcs:
            s.detail = "no root causes to address"
            return {"patches": []}
        causes = "\n".join(f"[{i}] {r['statement']} (6M: {r['category_6m']}; verification: {r['verification_test'][:90]})" for i, r in enumerate(rcs))
        cfs = "\n".join(f"- {c['statement']}" for c in form["contributing_factors"])
        rec = "; ".join(f"{m['rca_number']}: CAPA '{m['capa_summary'][:90]}' outcome: {m.get('capa_outcome') or 'n/a'}" for m in state.get("similar", []))
        user = f"FACTS:\n{digest(form)}\n\nROOT CAUSES:\n{causes}\n\nCONTRIBUTING FACTORS:\n{cfs or 'n/a'}\n\nPAST SIMILAR CASES (learn from failed CAPA): {rec or 'none'}"
        out, meta = await structured(CapaOut, prompts.CAPA, user, role="heavy", max_tokens=3000, emit=get_stream_writer())
        s.used(meta)
        items = _capa_items(out, rcs, meta["model"])
        weak = _weak_causes(items, rcs)
        if weak:  # one repair pass for causes without a real corrective action
            user2 = user + f"\n\nThe following root-cause indexes still lack a strong corrective action (or rely on training only): {weak}. Return the COMPLETE corrected action list."
            out2, meta2 = await structured(CapaOut, prompts.CAPA, user2, role="heavy", max_tokens=3000, emit=get_stream_writer())
            s.used(meta2)
            items = _capa_items(out2, rcs, meta2["model"])
            still = _weak_causes(items, rcs)
            if still:
                get_stream_writer()({"type": "warning", "text": "CAPA coverage is incomplete for some root causes - review and add corrective actions."})
        patches += put(state, "capa", items)
        kinds = {k: sum(1 for i in items if i["type"] == k) for k in ("correction", "corrective", "preventive")}
        s.detail = f"{len(items)} actions: {kinds['correction']} correction, {kinds['corrective']} corrective, {kinds['preventive']} preventive"
        return {"patches": patches}
    return {"patches": patches}


# ---------------------------------------------------------------- impact
async def impact(state: RCAState) -> dict:
    patches: list[dict] = []
    async with step("impact", "Assessing impact and preliminary classification") as s:
        form = working_form(state)
        rec = "; ".join(f"{m['rca_number']} ({m['title'][:70]})" for m in state.get("similar", []))
        user = f"FACTS:\n{digest(form)}\n\nRECURRENCE: {rec or 'none found'}\n\nSOURCE:\n{source_excerpt(state, 2500)}"
        out, meta = await structured(ImpactOut, prompts.IMPACT, user, role="mid", max_tokens=1800, emit=get_stream_writer())
        s.used(meta)
        cls, why = out.suggested_class, out.class_rationale
        if any(r.get("status") == "outside" for r in form["problem"]["requirements"]) and cls == "minor":
            cls, why = "major", why + " (Raised to major: a specification/CPP result is outside its limit.)"
        if state.get("similar") and cls != "critical":
            cls = CLASS_ORDER[min(CLASS_ORDER.index(cls) + 1, 2)]
            why += f" (Escalated one level: similar earlier event {state['similar'][0]['rca_number']}.)"
        prov = ai_meta("impact", meta["model"], grounded="inferred")
        patches += put(state, "classification.suggested_class", cls, prov=prov)
        patches += put(state, "classification.class_rationale", why, prov=prov)
        for k, v in (("severity", out.severity), ("occurrence", out.occurrence), ("detectability", out.detectability)):
            patches += put(state, f"classification.{k}", v, prov=prov)
        patches += put(state, "classification.rpn", rpn(out.severity, out.occurrence, out.detectability), prov=prov)
        for path, val in (("impact.product_quality", out.product_quality), ("impact.patient_safety", out.patient_safety),
                          ("impact.validation_regulatory", out.validation_regulatory), ("impact.suggested_disposition", out.suggested_disposition),
                          ("impact.disposition_note", out.disposition_note), ("impact.other_batches_note", out.other_batches_note or "")):
            patches += put(state, path, val, prov=prov)
        patches += put(state, "impact.cqas_affected", out.cqas_affected, prov=prov)
        patches += put(state, "impact.other_batches", [{"id": new_id("ob"), "batch": b.batch, "link": b.link, "rationale": b.rationale,
                                                        "meta": ai_meta("impact", meta["model"], grounded="inferred")} for b in out.other_batches])
        s.detail = f"suggested class: {cls}; RPN {rpn(out.severity, out.occurrence, out.detectability)}; {len(out.other_batches)} other batch(es) to assess"
        return {"patches": patches}
    return {"patches": patches}


# --------------------------------------------------------------- summary
async def summarize(state: RCAState) -> dict:
    patches: list[dict] = []
    w = get_stream_writer()
    async with step("summarize", "Drafting summary") as s:
        form = working_form(state)
        rcs = "\n".join(f"- {r['statement']} [{r['certainty']}]" for r in form["root_causes"])
        capas = "\n".join(f"- ({c['type']}) {c['action']}" for c in form["capa"])
        gaps = "\n".join(f"- {g['item']} [{g['priority']}]" for g in form["evidence_gaps"][:8])
        user = (f"FACTS:\n{digest(form)}\n\nROOT-CAUSE HYPOTHESES:\n{rcs or 'none yet'}\n\nCAPA:\n{capas or 'none yet'}\n\nTOP MISSING EVIDENCE:\n{gaps or 'none'}\n"
                f"NOT STATED IN SOURCE: {', '.join(form.get('meta', {}).get('not_in_source', [])[:12]) or 'n/a'}")
        out, meta = await structured(SummaryOut, prompts.SUMMARY, user, role="light", max_tokens=900, emit=w)
        s.used(meta)
        patches += put(state, "summary.executive_summary", out.executive_summary, prov=ai_meta("summarize", meta["model"], grounded="inferred"))
        w({"type": "message", "text": out.chat_message})
        s.detail = "summary and message drafted"
        return {"patches": patches}
    w({"type": "message", "text": "The analysis finished with some steps incomplete - see the warnings above and review what was filled in."})
    return {"patches": patches}
