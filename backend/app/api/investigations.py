import copy
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..forms import default_form, denormalise
from ..models import AuditLog, ChatMessage, Investigation, SourceDocument
from ..services import audit, gates
from .deps import Actor, get_actor

router = APIRouter(prefix="/investigations", tags=["investigations"])


def summary_dict(i: Investigation) -> dict:
    return {
        "id": str(i.id), "rca_number": i.rca_number, "title": i.title, "status": i.status, "product": i.product,
        "batch_numbers": i.batch_numbers, "classification": i.classification, "event_type": i.event_type,
        "root_cause_summary": i.root_cause_summary, "capa_count": i.capa_count, "version": i.version,
        "updated_at": i.updated_at.isoformat() if i.updated_at else None,
    }


async def _get(session: AsyncSession, iid: uuid.UUID) -> Investigation:
    inv = await session.get(Investigation, iid)
    if not inv:
        raise HTTPException(404, "Investigation not found")
    return inv


@router.get("")
async def list_investigations(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(Investigation).order_by(Investigation.updated_at.desc()))).scalars().all()
    return [summary_dict(r) for r in rows]


@router.post("", status_code=201)
async def create_investigation(session: AsyncSession = Depends(get_session), actor: Actor = Depends(get_actor)):
    n = (await session.execute(text("select nextval('rca_number_seq')"))).scalar_one()
    inv = Investigation(
        rca_number=f"RCA-{datetime.now(timezone.utc).year}-{n:04d}", status="draft", form_data=default_form(),
        provenance={}, title="(untitled investigation)",
    )
    session.add(inv)
    await session.flush()
    await audit.log_event(session, inv.id, actor.name, actor.role, "create", reason="Investigation created")
    await session.commit()
    return {**summary_dict(inv), "form_data": inv.form_data, "provenance": inv.provenance, "documents": [], "messages": []}


@router.get("/{iid}")
async def get_investigation(iid: uuid.UUID, session: AsyncSession = Depends(get_session)):
    inv = await _get(session, iid)
    docs = (await session.execute(
        select(SourceDocument).where(SourceDocument.investigation_id == iid).order_by(SourceDocument.created_at))).scalars().all()
    msgs = (await session.execute(
        select(ChatMessage).where(ChatMessage.investigation_id == iid).order_by(ChatMessage.created_at))).scalars().all()
    return {
        **summary_dict(inv), "form_data": inv.form_data, "provenance": inv.provenance,
        "documents": [
            {"id": str(d.id), "filename": d.filename, "kind": d.kind, "pages": d.pages, "chars": len(d.text),
             "scanned": bool(d.meta.get("scanned")), "warnings": d.meta.get("warnings", [])} for d in docs
        ],
        "messages": [{"id": str(m.id), "role": m.role, "content": m.content, "attachments": m.attachments, "meta": m.meta} for m in msgs],
    }


class SaveBody(BaseModel):
    form_data: dict
    provenance: dict
    version: int
    ai_run_id: uuid.UUID | None = None


@router.put("/{iid}")
async def save_investigation(iid: uuid.UUID, body: SaveBody, session: AsyncSession = Depends(get_session),
                             actor: Actor = Depends(get_actor)):
    inv = await _get(session, iid)
    if inv.status in ("approved", "closed"):
        raise HTTPException(409, "This investigation is approved/closed and read-only.")
    if body.version != inv.version:
        raise HTTPException(409, f"Version conflict (server v{inv.version}, yours v{body.version}). Reload to continue.")
    old = copy.deepcopy(inv.form_data)
    n = await audit.write_diff(session, inv.id, old, body.form_data, body.provenance, actor.name, actor.role, ai_run_id=body.ai_run_id)
    for k, v in denormalise(body.form_data).items():
        setattr(inv, k, v)
    inv.form_data = body.form_data  # reassign: in-place JSONB mutations are not tracked
    inv.provenance = body.provenance
    inv.version += 1
    await session.commit()
    await session.refresh(inv)  # server-side onupdate columns are expired after commit
    return {**summary_dict(inv), "changes_logged": n}


@router.get("/{iid}/gates")
async def get_gates(iid: uuid.UUID, session: AsyncSession = Depends(get_session)):
    inv = await _get(session, iid)
    return gates.summary(gates.evaluate(inv.form_data))


class ConfirmBody(BaseModel):
    note: str


@router.post("/{iid}/root-causes/{rcid}/confirm")
async def confirm_root_cause(iid: uuid.UUID, rcid: str, body: ConfirmBody, session: AsyncSession = Depends(get_session),
                             actor: Actor = Depends(get_actor)):
    """Prototype review confirmation by the (demo) QA role. NOT a legally valid electronic signature."""
    if actor.role != "qa":
        raise HTTPException(403, "Only the QA role can confirm a root cause (demo role switch).")
    inv = await _get(session, iid)
    form = copy.deepcopy(inv.form_data)
    rc = next((r for r in form["root_causes"] if r["id"] == rcid), None)
    if not rc:
        raise HTTPException(404, "Root cause not found")
    if len(body.note.strip()) < 15:
        raise HTTPException(422, "Give a rationale for the confirmation (at least 15 characters).")
    if not rc.get("supporting_evidence") or not rc.get("verification_test"):
        raise HTTPException(422, "A root cause needs supporting evidence and a verification test before it can be confirmed.")
    rc["certainty"] = "confirmed"
    rc["meta"] = {
        **rc.get("meta", {}), "reviewed": True, "confirmed_by": actor.name,
        "confirmed_at": datetime.now(timezone.utc).isoformat(), "confirm_note": body.note.strip(),
    }
    inv.form_data = form
    inv.version += 1
    await audit.log_event(
        session, inv.id, actor.name, actor.role, "confirm", path=f"root_causes.{rcid}", reason=body.note.strip(),
        new_value="confirmed (prototype review confirmation - not a legally valid e-signature)")
    await session.commit()
    return {"form_data": form, "version": inv.version}


@router.post("/{iid}/submit")
async def submit(iid: uuid.UUID, session: AsyncSession = Depends(get_session), actor: Actor = Depends(get_actor)):
    inv = await _get(session, iid)
    g = gates.summary(gates.evaluate(inv.form_data))
    if not g["ready"]:
        raise HTTPException(422, {"message": "Blocking checks are still open", "gates": g})
    inv.status = "in_review"
    inv.version += 1
    await audit.log_event(session, inv.id, actor.name, actor.role, "submit", reason="Submitted for QA review")
    await session.commit()
    await session.refresh(inv)
    return summary_dict(inv)


@router.post("/{iid}/approve")
async def approve(iid: uuid.UUID, body: ConfirmBody, session: AsyncSession = Depends(get_session), actor: Actor = Depends(get_actor)):
    if actor.role != "qa":
        raise HTTPException(403, "Only the QA role can approve (demo role switch).")
    inv = await _get(session, iid)
    if inv.status != "in_review":
        raise HTTPException(409, "Only investigations that are in QA review can be approved.")
    inv.status = "approved"
    inv.version += 1
    await audit.log_event(
        session, inv.id, actor.name, actor.role, "approve", reason=body.note.strip() or "Approved",
        new_value="approved (prototype - not a legally valid e-signature)")
    await session.commit()
    await session.refresh(inv)
    return summary_dict(inv)


@router.get("/{iid}/audit")
async def get_audit(iid: uuid.UUID, session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(
        select(AuditLog).where(AuditLog.investigation_id == iid).order_by(AuditLog.id.desc()).limit(400))).scalars().all()
    return [
        {"id": r.id, "actor": r.actor, "role": r.role, "action": r.action, "path": r.path, "old": r.old_value, "new": r.new_value,
         "reason": r.reason, "ts": r.ts.isoformat() if r.ts else None} for r in rows
    ]
