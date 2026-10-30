"""OFFLINE DEV FIXTURE (LLM_MODE=fixture). Canned structured outputs for the Omeprazole sample
(samples/IR-B-26-093_Omeprazole_Stage4.pdf) so the pipeline, SSE stream and UI can be tested without
a Groq key. Not an AI result: the UI labels these runs "offline dev fixture". Never used in live mode."""
from __future__ import annotations

import re

from pydantic import BaseModel

from . import outputs as o


def F(value, quote=None, conf="high"):
    return o.Fld(value=value, quote=quote if quote is not None else value, confidence=conf)


NONE = o.Fld(value=None, quote=None, confidence="low")


def identity() -> o.IdentityOut:
    return o.IdentityOut(
        deviation_ref=F("IR/B/26/093", "Incident Report No.: IR/B/26/093"),
        title=F("Temperature excursion during m-CPBA addition in R-204 (Stage-4) and sulfone impurity OOS - Omeprazole OMZ-2610-017", None, "medium"),
        site=F("KESTREL FINE CHEMICALS LTD. - UNIT 3 (API)", "KESTREL FINE CHEMICALS LTD. - UNIT 3 (API), BLOCK B"),
        area=F("Block B", "BLOCK B"), department=F("Production - Block B", "Department: Production - Block B"),
        product_name=F("Omeprazole (API)", "Product: Omeprazole (API)"), process_stage=F("Stage-4 (Oxidation)", "Stage: Stage-4 (Oxidation)"),
        step_reference=F("BMR step 4.12", "as per BMR step 4.12"), batch_size=F("410 kg (input sulfide)", "Batch Size: 410 kg (input sulfide)"),
        detection_method=F("High temperature alarm (DCS) during addition; IPC (HPLC); QC release testing", "the high temperature alarm came", "medium"),
        shift=F("Night shift", "in the night shift of 13/14-Oct-2026"), reported_by=F("Rahul Sharma, Production Officer", "Reported by: Rahul Sharma, Production Officer"),
        occurrence_datetime=F("night shift of 13/14-Oct-2026 (exact time not stated)", "in the night shift of 13/14-Oct-2026", "medium"),
        occurrence_end_datetime=NONE, detection_datetime=NONE, reported_to_qa_datetime=NONE,
        event_type=F("Process deviation (CPP/IPC)", None, "high"),
        problem_statement=F("During m-CPBA addition in R-204 (batch OMZ-2610-017, BMR step 4.12, limit -5 to +5 °C) the reaction mass reached -11.6 °C and then +13.8 °C (about 1 hour outside range); IPC sulfone (Imp-D) was 0.91% vs NMT 0.30% and finished API Imp-D 0.27% vs NMT 0.10% (OOS A.R. QC/26/4471).", None, "medium"),
        batch_status=F("On hold in quarantine (312 kg)", "kept on hold in quarantine area"),
    )


def details() -> o.DetailsOut:
    return o.DetailsOut(
        batch_numbers=[F("OMZ-2610-017", "Batch No.: OMZ-2610-017")],
        equipment_ids=[F("R-204", "R-204 (5 KL GLR)"), F("TCV-204", "TIC-204 / TCV-204"), F("TIC-204", "TIC-204 / TCV-204"), F("P-206", "dosing pump P-206")],
        instrument_ids=[], persons_involved=[F("Rahul Sharma (Production Officer)"), F("Vikram Rao (HOD Production)", "Reviewed by: Vikram Rao, HOD Production")],
        related_records=[F("A.R. No. QC/26/4471", "A.R. No. QC/26/4471")],
        requirements=[
            o.Req(parameter="Reaction-mass temperature during m-CPBA addition (BMR 4.12)", requirement="-5 °C to +5 °C", actual="-11.6 °C (min) / +13.8 °C (max)", quote="mass temperature went down to -11.6"),
            o.Req(parameter="IPC Sulfone (Imp-D)", requirement="NMT 0.30%", actual="0.91%", quote="Sulfone (Imp-D) 0.91% (IPC limit NMT 0.30%)"),
            o.Req(parameter="Finished API Impurity D (sulfone)", requirement="NMT 0.10%", actual="0.27%", quote="Impurity D (sulfone) 0.27% against specification NMT 0.10%"),
            o.Req(parameter="Total impurities", requirement="NMT 0.5%", actual="0.46%", quote="Total impurities 0.46% (NMT 0.5%)"),
        ],
        immediate_actions=[
            o.Act(action="Batch OMZ-2610-017 (312 kg) kept on hold in quarantine; QA informed", performed_by=None, when=None, outcome="On hold", quote="kept on hold in quarantine area. QA informed."),
            o.Act(action="TCV-204 positioner found faulty and replaced", performed_by="Instrumentation", when="15-Oct-2026", outcome=None, quote="positioner found faulty and replaced on 15-Oct-2026"),
            o.Act(action="R-204 not used for Stage-4 until valve check completed", performed_by=None, when=None, outcome=None, quote="R-204 not used for Stage-4 till valve check was completed"),
        ],
        timeline=[
            o.Evt(when="13/14-Oct-2026 (night shift)", event="m-CPBA addition in R-204; TCV-204 did not respond; mass temperature fell to -11.6 °C; addition continued", source="Incident report", quote="did not respond to the TIC-204 output"),
            o.Evt(when="13/14-Oct-2026 (night shift)", event="Operator put TIC-204 in manual and closed the brine hand valve; temperature rose to +13.8 °C; high temperature alarm", source="DCS / incident report", quote="the high temperature alarm came"),
            o.Evt(when="15-Oct-2026", event="TCV-204 positioner found faulty and replaced", source="Instrumentation", quote="positioner found faulty and replaced on 15-Oct-2026"),
            o.Evt(when="20-Oct-2026", event="QC reported OOS in finished API: Imp-D 0.27% (A.R. QC/26/4471)", source="QC", quote="On 20-Oct-2026 QC reported OOS in the finished API"),
            o.Evt(when="21-Oct-2026", event="Incident report raised (about 7 days after occurrence); QA receipt blank", source="Incident report", quote="Date of Report: 21-Oct-2026"),
        ],
        missing_information=[
            "Exact start/end times of the low (-11.6 °C) and high (+13.8 °C) phases", "Quantity of m-CPBA dosed while below -5 °C and above +5 °C",
            "Whether the high-temperature interlock on P-206 tripped, failed or was bypassed (alarm/event log not referenced)",
            "As-found calibration status of the temperature transmitter and maintenance history of TCV-204 (work order)",
            "Why no deviation was raised on 14-Oct; date/time QA was actually notified (QA receipt blank)",
            "Who authorised continuing to work-up after the IPC failure (0.91% vs NMT 0.30%)",
            "Other Stage-4 batches run in R-204 since TCV-204 last worked correctly", "Names of operator/shift chemist; QC Phase I laboratory conclusion for the OOS",
        ],
    )


def _fb(cause, area, disp, rationale, quote=None):
    return o.FbCause(cause=cause, evidence_area=area, disposition=disp, evidence_quote=quote, rationale=rationale)


def fishbone() -> o.FishboneOut:
    return o.FishboneOut(
        man=[_fb("Operator continued m-CPBA addition while temperature was far below the range and isolated brine by hand without first stopping dosing", "Personnel", "supported", "The report states addition was continued and brine was closed manually.", "Addition was continued."),
             _fb("Event recorded only in BMR remarks; no deviation raised for about 7 days", "Documentation", "supported", "Report dated 21-Oct for an event on 13/14-Oct.", "The operator recorded the event in BMR remarks.")],
        machine=[_fb("TCV-204 brine control valve (positioner) failed and did not follow the controller output", "Equipment", "supported", "Valve did not respond; positioner later found faulty.", "the jacket brine valve TCV-204 did not respond to the TIC-204 output"),
                 _fb("High-temperature dosing interlock on P-206 possibly not active or absent", "Equipment", "needs_evidence", "Dosing continued during the excursion; alarm/interlock status is not stated."),
                 _fb("No low-temperature dosing stop on P-206", "Process", "needs_evidence", "Addition continued at -11.6 °C; control design not described.")],
        material=[_fb("m-CPBA assay/charge higher than calculated", "Materials", "needs_evidence", "Charge calculation and CoA are not provided."),
                  _fb("Sulfone carried in from Stage-3 sulfide", "Materials", "unlikely", "IPC sulfide 0.38% is within its limit.")],
        method=[_fb("BMR step 4.12 states the range but no instruction to stop addition and call QA on excursion", "Documentation", "needs_evidence", "Step text beyond the range is not provided."),
                _fb("Processing continued after failed IPC (0.91% vs NMT 0.30%) without documented QA decision", "Process", "supported", "The batch was taken forward for work-up.", "The batch was taken forward for work-up, isolation and drying.")],
        measurement=[_fb("Temperature transmitter accuracy / calibration status unknown", "Equipment", "needs_evidence", "As-found calibration not stated."),
                     _fb("QC HPLC result for Imp-D invalid", "Analytical", "unlikely", "IPC and release results agree directionally (0.91% then 0.27%).")],
        environment=[_fb("Brine plant supply disturbance during the night shift", "Environment", "needs_evidence", "Utility log not provided."),
                     _fb("Night-shift workload / alarm load", "Personnel", "needs_evidence", "Roster and alarm journal not provided.")],
    )


def whys() -> o.WhysOut:
    return o.WhysOut(whys=[
        o.Why(question="Why did the finished API fail Imp-D (0.27% vs NMT 0.10%)?", answer="Sulfone formed in Stage-4 (0.91% at IPC) and is only partly removed downstream.", basis="evidence", quote="Sulfone (Imp-D) 0.91% (IPC limit NMT 0.30%)"),
        o.Why(question="Why was so much sulfone formed?", answer="Reaction mass went from -11.6 °C to +13.8 °C during m-CPBA addition, outside the -5 to +5 °C range; oxidant likely accumulated when cold and over-oxidised when temperature rose.", basis="hypothesis", quote="the temperature rose sharply to a maximum of +13.8"),
        o.Why(question="Why did temperature leave the range?", answer="TCV-204 did not respond to the controller output (positioner later found faulty) and brine was then isolated manually.", basis="evidence", quote="positioner found faulty and replaced on 15-Oct-2026"),
        o.Why(question="Why did dosing continue outside the range?", answer="No evidence of a dosing stop outside the CPP range or of an active high-temperature interlock; BMR step may lack a stop-and-call-QA instruction.", basis="hypothesis", quote="Addition was continued."),
        o.Why(question="Why were these safeguards missing?", answer="The Stage-4 control strategy/risk assessment may not cover valve failure and oxidant accumulation; to be verified against the process FMEA and interlock register.", basis="hypothesis", quote=None),
    ], stopping_rationale="The last level is a control-strategy gap that the site can change (interlock, alarm, BMR step); asking further leaves the site's control.")


def _rc(statement, cat, area, sub, cert, conf, support, contra, assump, missing, test, he=False, hej=None):
    return o.CauseItem(statement=statement, category_6m=cat, evidence_area=area, subcategory=sub, certainty=cert, confidence=conf,
                       supporting_evidence=[o.Support(quote=q, source="Incident report p.1") for q in support], contradicting_evidence=contra,
                       assumptions=assump, missing_evidence=missing, verification_test=test, human_error_flag=he, human_error_justification=hej)


def root_cause() -> o.RootCauseOut:
    return o.RootCauseOut(
        root_causes=[
            _rc("Loss of temperature control: TCV-204 brine valve positioner failure left the jacket valve unresponsive, and the Stage-4 control strategy has no automatic dosing stop outside the CPP range, so m-CPBA addition continued during the excursion.",
                "machine", "Equipment", "design_gap", "most_probable", "medium",
                ["the jacket brine valve TCV-204 did not respond to the TIC-204 output", "positioner found faulty and replaced on 15-Oct-2026", "Addition was continued."],
                ["None found in the provided sources"],
                ["The positioner fault (not brine supply or controller tuning) caused the non-response", "No interlock stopped P-206 (its status is not stated)", "Over-oxidation, not an analytical artefact, explains the sulfone result"],
                ["DCS trend and alarm/event journal for TT-204, TIC-204 output, TCV-204 position, P-206 status", "Interlock bypass register and last functional test", "As-found inspection of the removed positioner"],
                "Compare TIC-204 output vs TCV-204 position feedback on the DCS trend; inspect/stroke-test the removed positioner; review the P-206 interlock configuration and bypass register."),
        ],
        contributing_factors=[
            _rc("Processing continued after the failed IPC (0.91% vs NMT 0.30%) with no documented QA decision.", "method", "Documentation", "procedure_gap", "possible", "medium",
                ["The batch was taken forward for work-up, isolation and drying."], ["None found in the provided sources"], ["No QA decision exists that is simply not referenced in the report"],
                ["QA decision record for continuing after the IPC fail"], "Check BMR remarks and QA records for authorisation after the IPC result."),
            _rc("Late escalation: the excursion was recorded only in BMR remarks and the incident report was raised about 7 days later, after the API OOS.", "method", "Documentation", "procedure_gap", "possible", "medium",
                ["The operator recorded the event in BMR remarks.", "Date of Report: 21-Oct-2026"], ["None found in the provided sources"], ["No earlier deviation was raised"],
                ["Deviation log for 14-Oct", "Time QA was notified"], "Review the deviation register and shift handover records for 14-Oct."),
        ],
    )


def gaps() -> o.GapsOut:
    def g(i, a, why, link, pr, own):
        return o.GapItem(item=i, evidence_area=a, why_needed=why, linked_to=link, priority=pr, suggested_owner=own)
    return o.GapsOut(gaps=[
        g("DCS trends (1-5 s) for TT-204, TIC-204 SP/PV/OP, TCV-204 position feedback, P-206 status and flow totaliser across the whole addition", "Process", "Fixes true start/end times and how much m-CPBA was dosed while cold and while hot", "Loss of temperature control", "high", "Production / Automation"),
        g("DCS alarm and event journal incl. interlock trip/bypass states and manual-mode change", "Equipment", "Shows whether the high-temperature interlock worked or was bypassed", "No automatic dosing stop", "high", "Automation"),
        g("Interlock bypass register and last post-maintenance functional test", "Equipment", "Confirms the protective layer was active", "No automatic dosing stop", "high", "Engineering"),
        g("Work order and as-found failure description for the TCV-204 positioner; the removed part", "Equipment", "Confirms the failure mode of the valve", "Positioner failure", "high", "Instrumentation"),
        g("As-found/as-left calibration record for the temperature transmitter and loop check", "Equipment", "Rules measurement error in or out", "Measurement validity", "medium", "Instrumentation"),
        g("QC Phase I laboratory investigation record for A.R. QC/26/4471 (peak identity, system suitability, CDS audit trail)", "Analytical", "Confirms the OOS is real before attributing it to the excursion", "Sulfone OOS", "medium", "QC"),
        g("BMR Stage-4 pages: remarks, addition times, m-CPBA charge calculation and lot assay", "Documentation", "Checks over-charge and exact timeline", "Material hypothesis", "medium", "Production"),
        g("QA decision record (or its absence) for continuing after the failed IPC; time QA was notified", "Documentation", "Establishes the escalation timeline", "Late escalation", "medium", "QA"),
        g("Other Stage-4 batches in R-204 since TCV-204 last worked correctly (IPC sulfone trend)", "Historical", "Defines other batches that may be affected", "Scope", "high", "QA"),
        g("Interviews: operator, shift chemist, instrumentation technician; night-shift roster and alarm load", "Personnel", "Understands decisions and workload without assigning blame", "Contributing factors", "low", "QA"),
    ])


def _c(t, action, why, idx, strength, owner, days, cc, crit=None, meth=None, win=None):
    return o.CapaItem(type=t, action=action, rationale=why, linked_cause_index=idx, strength=strength, owner_role=owner, due_days=days,
                      change_control_needed=cc, effectiveness_criterion=crit, effectiveness_method=meth, effectiveness_window=win)


def capa() -> o.CapaOut:
    return o.CapaOut(actions=[
        _c("correction", "Keep batch OMZ-2610-017 (312 kg) on QA hold; complete QC Phase I for A.R. QC/26/4471; QA to decide disposition (reject, or reprocess only under an approved protocol after lab-scale proof that Imp-D can be reduced to <= 0.10%).", "The specified impurity is above its limit and cannot be released without proven removal.", -1, "administrative", "QA / QC", 7, False),
        _c("correction", "Stroke-test and loop-check TCV-204/TIC-204 after the positioner replacement, verify transmitter calibration, remove any interlock bypass and function-test the P-206 dosing trip before R-204 returns to Stage-4.", "Restores the failed loop and proves the protective layer is active.", 0, "engineering", "Instrumentation", 5, False),
        _c("corrective", "Under change control add a two-sided dosing interlock: P-206 stops automatically if TT-204 is below -6 °C or above +6 °C, plus a TCV-204 output-vs-position deviation alarm.", "Removes the failure mode (oxidant accumulation when cold, over-oxidation when hot) instead of relying on operator judgement.", 0, "engineering", "Engineering / Automation", 45, True,
           "Zero CPP temperature excursions during m-CPBA addition", "DCS alarm review + BMR review", "next 20 Stage-4 batches"),
        _c("corrective", "Revise BMR step 4.12 and the CPP-excursion SOP: on any excursion stop addition, inform shift chemist and QA, raise a deviation within the shift; require a documented QA decision before continuing after an excursion or failed IPC.", "Closes the procedure gap that allowed continued dosing, processing past a failed IPC and a 7-day reporting delay.", 0, "administrative", "Production / QA", 30, True,
           "100% of Stage-4 BMRs show excursion handling per the revised step; deviations raised within 24 h", "Review of BMRs and deviation log", "next 20 batches"),
        _c("preventive", "Review all semi-batch exothermic additions on site (oxidations, reductions, quenches) for missing two-sided dosing interlocks; include control-valve positioners in preventive maintenance/diagnostics; update the process FMEA for accumulation hazard.", "The same design gap may exist on other reactors and products.", 0, "engineering", "Engineering / MSAT", 90, True,
           "100% of identified steps upgraded or risk-accepted by the due date; no similar excursion on site", "Gap-assessment closure report", "12 months"),
        _c("preventive", "Put the Stage-4 IPC sulfone result on a control chart with an OOT alert and add a CPP alarm summary to the daily shift report reviewed by QA.", "Earlier detection of drift and of unreported excursions.", 0, "administrative", "QA / QC", 30, False,
           "Control chart live; IPC sulfone <= 0.15% in the next 20 batches", "LIMS trend review", "3 months"),
    ])


def impact() -> o.ImpactOut:
    return o.ImpactOut(
        suggested_class="major", class_rationale="Critical process parameter excursion with a confirmed out-of-specification result for a specified impurity (0.27% vs NMT 0.10%) on a held batch; no evidence of distribution.",
        severity=4, occurrence=3, detectability=3,
        product_quality="Impurity D (sulfone) is 0.27%, above the 0.10% specification and above the ICH Q3A qualification threshold (0.15%) for this dose range; other results (total impurities, assay) comply.",
        cqas_affected=["Impurity D (sulfone)", "Total impurities"],
        patient_safety="Release is not justified at 0.27%: the impurity exceeds its qualification threshold. The batch is on hold, so no patient exposure is expected; toxicology input needed if reprocessing is considered.",
        other_batches=[o.OtherBatch(batch="Other Stage-4 batches run in R-204 since TCV-204 last worked correctly", link="Same reactor and control valve", rationale="TCV-204 positioner fault may pre-date 14-Oct; check IPC sulfone history.")],
        other_batches_note=None, validation_regulatory="Check whether the -5 to +5 °C range and Imp-D limit are registered commitments (DMF/CEP). Process validation is not affected if the root cause is equipment failure and the control is restored.",
        suggested_disposition="Recommend QA keeps the batch on hold; reject unless a lab-scale reprocessing trial proves removal of Imp-D and an approved reprocessing protocol exists.",
        disposition_note="Recommendation only - QA decides.")


def summary() -> o.SummaryOut:
    return o.SummaryOut(
        executive_summary="During m-CPBA addition in R-204 (batch OMZ-2610-017) the reaction mass left its -5 to +5 °C range (-11.6 °C then +13.8 °C) after brine valve TCV-204 stopped responding, and addition continued. The finished API is OOS for Impurity D (0.27% vs NMT 0.10%). The most probable cause (a hypothesis pending DCS, interlock and positioner evidence) is loss of temperature control without an automatic dosing stop. Corrective direction: engineering interlock and alarm, BMR/SOP revision, and a site-wide review of similar additions.",
        chat_message="I read the incident report and filled the form. Extracted values are tagged: green = verified in the document, amber = please verify. The most likely cause is loss of temperature control with no automatic dosing stop - this is a hypothesis, not a conclusion. Key gaps: exact excursion times, interlock/alarm status, calibration and QA notification time. Please review each root cause and CAPA action before saving.")


def respond(schema: type[BaseModel], user: str) -> BaseModel:
    name = schema.__name__
    if name == "IdentityOut":
        return identity()
    if name == "DetailsOut":
        return details()
    if name == "FishboneOut":
        return fishbone()
    if name == "WhysOut":
        return whys()
    if name == "RootCauseOut":
        return root_cause()
    if name == "GapsOut":
        return gaps()
    if name == "CapaOut":
        return capa()
    if name == "ImpactOut":
        return impact()
    if name == "SummaryOut":
        return summary()
    if name == "RouteOut":
        msg = user.split("MESSAGE:", 1)[-1].strip().lower()
        return o.RouteOut(intent="question" if msg.endswith("?") else "edit")
    if name == "EditPlan":
        msg = user.split("USER MESSAGE:", 1)[-1]
        m = re.search(r"batch number is\s+([A-Za-z0-9\-/]+)", msg, re.I)
        if m:
            return o.EditPlan(edits=[o.Edit(path="incident.batch_numbers", value=None, list_values=[m.group(1).strip(".")], reason="User correction")], reply="Updated the batch number.")
        return o.EditPlan(edits=[], reply="Which field should I change, and to what?")
    if name == "AnswerOut":
        return o.AnswerOut(answer="TCV-204 did not respond to the TIC-204 output, the temperature fell to -11.6 °C and later reached +13.8 °C; the report does not state whether the P-206 high-temperature interlock tripped.", citations=["the jacket brine valve TCV-204 did not respond to the TIC-204 output"])
    raise KeyError(name)
