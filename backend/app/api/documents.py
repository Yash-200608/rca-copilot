import hashlib
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_session
from ..models import Investigation, SourceDocument
from ..services.parsing import ParsedDoc, UnsupportedDocument, parse_text, parse_upload

router = APIRouter(prefix="/documents", tags=["documents"])


def _doc_out(d: SourceDocument) -> dict:
    return {
        "id": str(d.id), "filename": d.filename, "kind": d.kind, "pages": d.pages, "chars": len(d.text),
        "scanned": bool(d.meta.get("scanned")), "warnings": d.meta.get("warnings", []), "preview": d.text[:280],
    }


async def _store(session: AsyncSession, iid: uuid.UUID, name: str, raw: bytes, parsed: ParsedDoc) -> SourceDocument:
    if not await session.get(Investigation, iid):
        raise HTTPException(404, "Investigation not found")
    doc = SourceDocument(
        investigation_id=iid, filename=name, kind=parsed.kind, sha256=hashlib.sha256(raw).hexdigest(), pages=parsed.pages,
        text=parsed.text, meta={**parsed.meta, "scanned": parsed.scanned, "warnings": parsed.warnings},
    )
    session.add(doc)
    await session.commit()
    return doc


@router.post("", status_code=201)
async def upload(investigation_id: uuid.UUID = Form(...), file: UploadFile = File(...), session: AsyncSession = Depends(get_session)):
    raw = await file.read()
    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File larger than {settings.max_upload_mb} MB")
    if not raw:
        raise HTTPException(422, "Empty file")
    try:
        parsed = parse_upload(file.filename or "upload", raw)
    except UnsupportedDocument as e:
        raise HTTPException(415, str(e))
    except Exception as e:  # corrupt PDF etc.
        raise HTTPException(422, f"Could not read this file: {type(e).__name__}")
    return _doc_out(await _store(session, investigation_id, file.filename or "upload", raw, parsed))


class TextBody(BaseModel):
    investigation_id: uuid.UUID
    text: str
    name: str | None = None


@router.post("/text", status_code=201)
async def upload_text(body: TextBody, session: AsyncSession = Depends(get_session)):
    if len(body.text.strip()) < 20:
        raise HTTPException(422, "Text is too short to analyse")
    parsed = parse_text(body.text)
    name = body.name or ("Pasted email" if parsed.kind == "email" else "Pasted text")
    return _doc_out(await _store(session, body.investigation_id, name, body.text.encode(), parsed))


@router.delete("/{doc_id}", status_code=204)
async def delete_doc(doc_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    d = await session.get(SourceDocument, doc_id)
    if d:
        await session.delete(d)
        await session.commit()
