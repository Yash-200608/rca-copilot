"""Structured-output schemas for every LLM call.

Groq strict JSON-schema mode needs every property in `required` (optional => nullable union) and
additionalProperties:false, so NOTHING here has a default value."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Conf = Literal["high", "medium", "low"]
Area = Literal["Equipment", "Process", "Materials", "Analytical", "Personnel", "Environment", "Documentation", "Historical"]
Cat6M = Literal["man", "machine", "material", "method", "measurement", "environment"]


class Fld(BaseModel):
    value: str | None = Field(description="As stated in the source, else null")
    quote: str | None = Field(description="Verbatim source excerpt <=25 words, else null")
    confidence: Conf


# ------------------------------------------------------------- extraction
class IdentityOut(BaseModel):
    deviation_ref: Fld = Field(description="Incident / deviation report number if stated (e.g. 'Incident Report No.')")
    title: Fld = Field(description="Short factual title of the event (no cause, no blame)")
    site: Fld
    area: Fld = Field(description="Block / area / room")
    department: Fld
    product_name: Fld
    process_stage: Fld = Field(description="Synthesis stage or unit operation")
    step_reference: Fld = Field(description="Controlling document and step, e.g. 'BMR step 4.12', or test method / STP number")
    batch_size: Fld
    detection_method: Fld = Field(description="How the event was detected (alarm, IPC, QC release test, batch record review, reconciliation...)")
    shift: Fld
    reported_by: Fld = Field(description="Name and role of the person who reported / logged it")
    occurrence_datetime: Fld = Field(description="When it started, as written in the source (do not invent times)")
    occurrence_end_datetime: Fld
    detection_datetime: Fld
    reported_to_qa_datetime: Fld
    event_type: Fld = Field(description="One of: Process deviation (CPP/IPC) | Equipment failure | Utility failure | OOS | OOT | Material/dispensing | Documentation/GDP | Data integrity | Cleaning/cross-contamination | Environmental | Other")
    problem_statement: Fld = Field(description="Cause-free statement: what happened, where, when, how much, against which requirement. No speculation about cause.")
    batch_status: Fld = Field(description="Status of the affected batch after containment, e.g. 'On QA hold', 'Processing continued', 'Rejected'")


class Req(BaseModel):
    parameter: str
    requirement: str = Field(description="The limit/specification as written, e.g. 'NMT 0.10%' or '-5 to +5 C'")
    actual: str = Field(description="The observed value(s) as written; for an excursion give the observed min and max")
    quote: str | None


class Act(BaseModel):
    action: str
    performed_by: str | None
    when: str | None
    outcome: str | None
    quote: str | None


class Evt(BaseModel):
    when: str | None = Field(description="Date/time/shift exactly as written, or null")
    event: str
    source: str | None = Field(description="Where the fact comes from: DCS trend, BMR, shift log, email, QC result, ...")
    quote: str | None


class DetailsOut(BaseModel):
    batch_numbers: list[Fld]
    equipment_ids: list[Fld] = Field(description="Equipment tags only (reactors, valves, dryers, pumps, controllers)")
    instrument_ids: list[Fld] = Field(description="Instrument / analytical instrument IDs")
    persons_involved: list[Fld] = Field(description="Names/roles as written")
    related_records: list[Fld] = Field(description="OOS numbers, A.R. numbers, work orders, change controls, other incident numbers")
    requirements: list[Req] = Field(description="Every requirement-vs-actual pair stated in the source (CPP limits, IPC limits, specifications)")
    immediate_actions: list[Act]
    timeline: list[Evt] = Field(description="Chronological events stated in the source, oldest first")
    missing_information: list[str] = Field(description="Important facts an investigator needs that the source does NOT state (e.g. exact times, interlock status, calibration status, QA notification time)")


# --------------------------------------------------------------- analysis
class FbCause(BaseModel):
    cause: str
    evidence_area: Area
    disposition: Literal["supported", "possible", "unlikely", "ruled_out", "needs_evidence"]
    evidence_quote: str | None = Field(description="Verbatim source excerpt that supports or refutes it, or null")
    rationale: str = Field(description="One sentence: why this disposition")


class FishboneOut(BaseModel):
    man: list[FbCause]
    machine: list[FbCause]
    material: list[FbCause]
    method: list[FbCause]
    measurement: list[FbCause]
    environment: list[FbCause]


class Why(BaseModel):
    question: str
    answer: str
    basis: Literal["evidence", "hypothesis"] = Field(description="'evidence' only if the source states it; otherwise 'hypothesis'")
    quote: str | None


class WhysOut(BaseModel):
    whys: list[Why]
    stopping_rationale: str


class Support(BaseModel):
    quote: str = Field(description="Verbatim excerpt from the source")
    source: str = Field(description="Where: document name / page")


class CauseItem(BaseModel):
    statement: str = Field(description="Systemic, controllable cause. Never 'human error' or 'operator error' as the cause itself.")
    category_6m: Cat6M
    evidence_area: Area
    subcategory: Literal["design_gap", "maintenance_gap", "calibration_gap", "procedure_gap", "training_gap", "material_supplier", "analytical_method", "utility", "organisational", "human_factors", "other"]
    certainty: Literal["possible", "most_probable"] = Field(description="Never 'confirmed' - only QA can confirm")
    confidence: Conf
    supporting_evidence: list[Support] = Field(description="Verbatim excerpts that support it (at least one)")
    contradicting_evidence: list[str] = Field(description="Facts in the sources that argue against it; if none, write exactly 'None found in the provided sources'")
    assumptions: list[str] = Field(description="What must be true for this cause to hold but is not stated in the source")
    missing_evidence: list[str] = Field(description="Specific records/data needed to confirm or refute it")
    verification_test: str = Field(description="Concrete check or test that would confirm or refute it")
    human_error_flag: bool = Field(description="True if the cause is in essence a human action; then justification is required")
    human_error_justification: str | None = Field(description="Why process/procedure/system causes were or were not sufficient to explain it, if human_error_flag")


class RootCauseOut(BaseModel):
    root_causes: list[CauseItem] = Field(description="1 to 3 most probable root causes")
    contributing_factors: list[CauseItem] = Field(description="2 to 5 contributing factors (incl. why detection/escape happened)")


class GapItem(BaseModel):
    item: str = Field(description="Specific record / data / interview needed")
    evidence_area: Area
    why_needed: str
    linked_to: str | None = Field(description="Short text of the cause or fact it would confirm or refute")
    priority: Literal["high", "medium", "low"]
    suggested_owner: str = Field(description="Function, e.g. Instrumentation, QC, Production, Warehouse, QA")


class GapsOut(BaseModel):
    gaps: list[GapItem]


class CapaItem(BaseModel):
    type: Literal["correction", "corrective", "preventive"]
    action: str = Field(description="Specific action with the equipment/document concerned")
    rationale: str = Field(description="Short explanation of why this action addresses the cause")
    linked_cause_index: int = Field(description="0-based index into root_causes this action addresses; -1 only for a correction of the batch/records")
    strength: Literal["elimination", "engineering", "administrative", "training"]
    owner_role: str
    due_days: int
    change_control_needed: bool
    effectiveness_criterion: str | None = Field(description="Measurable criterion, required for corrective and preventive actions")
    effectiveness_method: str | None
    effectiveness_window: str | None = Field(description="e.g. 'next 20 batches' or '6 months'")


class CapaOut(BaseModel):
    actions: list[CapaItem]


class OtherBatch(BaseModel):
    batch: str
    link: str = Field(description="Why it may be affected: same equipment / campaign / material lot / analytical run / utility")
    rationale: str


class ImpactOut(BaseModel):
    suggested_class: Literal["critical", "major", "minor"]
    class_rationale: str
    severity: Literal[1, 2, 3, 4, 5]
    occurrence: Literal[1, 2, 3, 4, 5]
    detectability: Literal[1, 2, 3, 4, 5] = Field(description="5 = hard to detect before release")
    product_quality: str = Field(description="Impact on the affected batch quality attributes")
    cqas_affected: list[str]
    patient_safety: str
    other_batches: list[OtherBatch]
    other_batches_note: str | None = Field(description="If no other batch can be named, why")
    validation_regulatory: str
    suggested_disposition: str = Field(description="A recommendation for QA only (hold/reject/reprocess pending testing...), never a decision")
    disposition_note: str


class SummaryOut(BaseModel):
    executive_summary: str = Field(description="3-5 sentences: event, most probable cause (labelled as hypothesis), impact, CAPA direction")
    chat_message: str = Field(description="Friendly message to the investigator: what was extracted, key findings, what is missing, what needs their review")


# -------------------------------------------------------- chat / routing
class RouteOut(BaseModel):
    intent: Literal["edit", "question", "analyze", "capa", "gaps", "summarize"]


class Edit(BaseModel):
    path: str = Field(description="Exact editable path from the provided list, e.g. 'incident.batch_numbers' or 'root_causes.<id>.statement'")
    value: str | None = Field(description="New value for a text field, else null")
    list_values: list[str] | None = Field(description="New values for a list-of-text field (batch_numbers, equipment_ids...), else null")
    reason: str


class EditPlan(BaseModel):
    edits: list[Edit]
    reply: str = Field(description="Confirm exactly what was changed, in one or two sentences. If unclear, ask a question and return no edits.")


class AnswerOut(BaseModel):
    answer: str
    citations: list[str] = Field(description="Verbatim excerpts from the source documents that support the answer")
