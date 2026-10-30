"""Seed three closed historical investigations (fictional) so the recurrence check has history.
One of them (R-204 / TCV-204 brine valve) closed with a CAPA that did not hold."""
from __future__ import annotations

import copy

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .forms import default_form, denormalise
from .models import Investigation


def _hist(num, title, product, batches, equip, stage, problem, rc, rc_cat, capas, summary, event_type="Process deviation (CPP/IPC)", cls="major"):
    f = default_form()
    f["header"]["title"] = title
    f["incident"].update({"product_name": product, "batch_numbers": batches, "equipment_ids": equip, "process_stage": stage,
                          "site": "Kestrel Fine Chemicals Ltd., Unit 3"})
    f["classification"].update({"event_type": event_type, "suggested_class": cls})
    f["problem"]["problem_statement"] = problem
    f["root_causes"] = [{"id": "rc-h1", "statement": rc, "category_6m": rc_cat, "certainty": "confirmed", "confidence": "high",
                         "supporting_evidence": [], "contradicting_evidence": [], "assumptions": [], "missing_evidence": [],
                         "verification_test": "", "meta": {"by": "user", "reviewed": True}}]
    f["capa"] = [{"id": f"capa-h{i}", **c, "meta": {"by": "user", "reviewed": True}} for i, c in enumerate(capas, 1)]
    f["summary"]["executive_summary"] = summary
    return num, f


HISTORY = [
    _hist("RCA-2025-0041", "Brine valve TCV-204 sticking caused temperature excursion in R-204 Stage-4 oxidation",
          "Omeprazole", ["OMZ-2509-011"], ["R-204", "TCV-204", "TIC-204"], "Stage-4 oxidation",
          "Reaction mass temperature exceeded the +5 C CPP limit (max +9.1 C) during m-CPBA addition in R-204; sulfone Imp-D 0.18% vs NMT 0.10%.",
          "Control valve TCV-204 stuck (stiction) and did not follow the controller output; no valve-position deviation alarm.", "machine",
          [{"type": "corrective", "action": "Clean and re-tune TCV-204 positioner; replace valve packing.", "strength": "administrative",
            "effectiveness": {"criterion": "No CPP excursion in the next 10 Stage-4 batches", "result_note": "NOT EFFECTIVE - similar TCV-204 sticking recurred within 6 months (see later investigation)"}},
           {"type": "preventive", "action": "Retrain Block-B operators on temperature-excursion response.", "strength": "training",
            "effectiveness": {"criterion": "Training completion 100%", "result_note": ""}}],
          "TCV-204 stiction caused a CPP excursion; fixed by cleaning/re-tuning the positioner and retraining. No engineering control or diagnostic alarm was added.", cls="major"),
    _hist("RCA-2025-0033", "Residual methanol above limit in Gabapentin after drying - vacuum pump seal liquid",
          "Gabapentin USP", ["GBP-2508-0612"], ["RCVD-03", "VP-03"], "Vacuum drying",
          "Residual methanol 3,640 ppm vs NMT 3000 ppm in dried Gabapentin; LOD within limit.",
          "Liquid-ring vacuum pump seal liquid not replaced on schedule; achievable vacuum degraded.", "machine",
          [{"type": "corrective", "action": "Replace seal liquid; add seal-liquid change to PM schedule.", "strength": "administrative",
            "effectiveness": {"criterion": "Vacuum >= 700 mmHg in next 10 batches", "result_note": "Effective for 10 batches"}}],
          "Seal liquid exhausted; PM updated.", event_type="OOS", cls="major"),
    _hist("RCA-2024-0127", "Wrong-status raw material staged in released rack - Metformin Stage-I",
          "Metformin Hydrochloride", ["MFH-2411-0952"], ["DB-02"], "Raw material dispensing",
          "A bag of material with UNDER TEST status was found in the released rack before dispensing; caught at line clearance.",
          "Quarantine bay capacity exceeded and no controlled overflow location; labels on pallet wrap only.", "method",
          [{"type": "corrective", "action": "Add overflow quarantine zone; label every container.", "strength": "engineering",
            "effectiveness": {"criterion": "Zero status findings in 3 monthly walk-throughs", "result_note": "Effective"}}],
          "No unreleased material was used. Procedure updated.", event_type="Material/dispensing", cls="minor"),
]


async def seed(session: AsyncSession) -> None:
    await session.execute(text("create sequence if not exists rca_number_seq start 100"))
    count = (await session.execute(select(func.count()).select_from(Investigation))).scalar_one()
    if count:
        await session.commit()
        return
    for num, form in HISTORY:
        d = denormalise(form)
        session.add(Investigation(rca_number=num, status="closed", form_data=copy.deepcopy(form), provenance={}, **d))
    await session.commit()
