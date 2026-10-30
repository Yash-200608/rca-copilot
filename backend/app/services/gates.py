"""Deterministic quality gates ("readiness checklist"). Pure functions over the form dict.

Inspired by what investigators/QA reviewers look for (ICH Q7/Q9/Q10, FDA OOS guidance, MHRA
investigation red flags). A prototype checklist - not a compliance claim."""
from __future__ import annotations

from ..forms import SIX_M, is_protected_item

HUMAN_ERROR_WORDS = ("human error", "operator error", "analyst error", "operator negligence", "personnel error", "retrain", "not trained properly")
TRAINING_WORDS = ("train", "re-train", "retrain", "read and understand", "awareness")


def _gate(gid: str, label: str, level: str, passed: bool, detail: str = "") -> dict:
    return {"id": gid, "label": label, "level": level, "passed": bool(passed), "detail": detail}


def _filled(v) -> bool:
    return bool(str(v).strip()) if v is not None else False


def evaluate(form: dict) -> list[dict]:
    inc, prob, cont = form["incident"], form["problem"], form["containment"]
    rcs, cfs, capas = form["root_causes"], form["contributing_factors"], form["capa"]
    g: list[dict] = []

    ident_missing = [k for k in ("product_name", "process_stage") if not _filled(inc.get(k))]
    if not inc.get("batch_numbers"):
        ident_missing.append("batch_numbers")
    g.append(_gate("identity", "Product, batch and process stage identified", "blocking", not ident_missing,
                   "Missing: " + ", ".join(ident_missing) if ident_missing else ""))
    g.append(_gate("problem", "Cause-free problem statement present", "blocking", _filled(prob.get("problem_statement"))))
    reqs = prob.get("requirements", [])
    g.append(_gate("spec_vs_actual", "At least one requirement vs actual row", "blocking",
                   any(_filled(r.get("requirement")) and _filled(r.get("actual")) for r in reqs)))
    g.append(_gate("containment", "Immediate action / containment recorded", "blocking", bool(cont.get("immediate_actions"))))
    times_missing = [k for k in ("occurrence_datetime", "detection_datetime", "reported_to_qa_datetime") if not _filled(inc.get(k))]
    g.append(_gate("timestamps", "Occurrence, detection and QA-notification times recorded", "warning", not times_missing,
                   "Missing: " + ", ".join(times_missing) if times_missing else ""))
    g.append(_gate("deviation_ref", "Deviation / incident reference present", "warning", _filled(form["header"].get("deviation_ref"))))

    fb_missing = [m for m in SIX_M if not form["fishbone"].get(m)]
    g.append(_gate("fishbone", "Fishbone addresses all six categories (Man, Machine, Material, Method, Measurement, Environment)",
                   "blocking", not fb_missing, "Missing: " + ", ".join(fb_missing) if fb_missing else ""))
    whys = form["five_whys"]
    last = (whys[-1].get("answer", "") if whys else "").lower()
    g.append(_gate("five_whys", "5 Whys has at least 3 levels ending in a systemic, controllable cause", "blocking",
                   len(whys) >= 3 and not any(w in last for w in HUMAN_ERROR_WORDS)))

    g.append(_gate("root_cause", "At least one root cause proposed", "blocking", bool(rcs)))
    bad_ev = []
    for rc in rcs:
        miss = [k for k, v in (("supporting evidence", rc.get("supporting_evidence")), ("contradicting evidence / none-found statement", rc.get("contradicting_evidence")),
                               ("assumptions", rc.get("assumptions")), ("missing evidence", rc.get("missing_evidence")),
                               ("verification test", rc.get("verification_test"))) if not v]
        if miss:
            bad_ev.append(f"{rc.get('statement', '')[:50]}: {', '.join(miss)}")
    g.append(_gate("rc_evidence", "Every root cause lists supporting/contradicting evidence, assumptions, missing evidence and a verification test",
                   "blocking", bool(rcs) and not bad_ev, "; ".join(bad_ev)))
    he = [rc for rc in rcs if rc.get("human_error_flag")]
    g.append(_gate("human_error", "No root cause rests on 'human error' without a systemic explanation", "blocking",
                   not he or all(_filled(rc.get("human_error_justification")) for rc in he)))
    unrev = [x for x in [*rcs, *capas] if not (x.get("meta", {}).get("reviewed") or x.get("meta", {}).get("by") == "user")]
    g.append(_gate("reviewed", "All AI-proposed root causes and CAPA actions reviewed by a human", "blocking", not unrev,
                   f"{len(unrev)} item(s) awaiting review" if unrev else ""))

    # CAPA coverage
    cap_ids = {c.get("id") for c in capas}
    uncovered = [rc["statement"][:50] for rc in rcs if not any(rc["id"] in (c.get("linked_to") or []) and c.get("type") == "corrective" for c in capas)]
    g.append(_gate("capa_coverage", "Every root cause has at least one corrective action", "blocking", bool(rcs) and not uncovered,
                   "No corrective action for: " + "; ".join(uncovered) if uncovered else ""))
    no_eff = [c.get("action", "")[:40] for c in capas if c.get("type") in ("corrective", "preventive") and not _filled((c.get("effectiveness") or {}).get("criterion"))]
    g.append(_gate("capa_effectiveness", "Corrective/preventive actions have a measurable effectiveness check", "blocking", bool(capas) and not no_eff,
                   "; ".join(no_eff)))
    training_only = []
    for rc in rcs:
        linked = [c for c in capas if rc["id"] in (c.get("linked_to") or []) and c.get("type") != "correction"]
        if linked and all(c.get("strength") == "training" for c in linked):
            training_only.append(rc["statement"][:50])
    g.append(_gate("training_only", "No root cause is addressed by retraining alone", "warning", not training_only, "; ".join(training_only)))
    no_owner = [c.get("action", "")[:40] for c in capas if not _filled(c.get("owner"))]
    g.append(_gate("capa_owner", "CAPA actions have a named owner", "warning", bool(capas) and not no_owner, f"{len(no_owner)} action(s) without named owner" if no_owner else ""))
    orphan = [c.get("action", "")[:40] for c in capas if c.get("type") != "correction" and not any(i in {r["id"] for r in [*rcs, *cfs]} for i in (c.get("linked_to") or []))]
    g.append(_gate("capa_linked", "Every corrective/preventive action is linked to a cause", "warning", not orphan, "; ".join(orphan)))

    ob = form["impact"]
    g.append(_gate("other_batches", "Other batches / products assessed (or justified as not applicable)", "blocking",
                   bool(ob.get("other_batches")) or _filled(ob.get("other_batches_note"))))
    g.append(_gate("impact", "Product quality and patient-safety impact assessed", "blocking",
                   _filled(ob.get("product_quality")) and _filled(ob.get("patient_safety"))))
    g.append(_gate("recurrence", "Recurrence / history check performed", "warning", bool(form["classification"]["recurrence"].get("checked"))))
    return g


def summary(gates: list[dict]) -> dict:
    blocking = [x for x in gates if x["level"] == "blocking" and not x["passed"]]
    warnings = [x for x in gates if x["level"] == "warning" and not x["passed"]]
    return {"gates": gates, "blocking_open": len(blocking), "warnings_open": len(warnings), "ready": not blocking}
