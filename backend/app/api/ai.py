"""AI endpoints. /ai/run streams a LangGraph run as Server-Sent Events.

The graph runs in a background task that feeds an asyncio.Queue; the SSE response only relays the
queue. A closed browser tab therefore does not cancel an analysis half-way (and the result is still
persisted to ai_runs / chat_messages)."""
from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterable
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel
from sqlalchemy import select

from ..ai.common import ABORTED, RUN_ID
from ..ai.graph import GRAPH, mermaid
from ..ai.llm import list_models
from ..config import settings
from ..db import SessionLocal
from ..models import AiRun, ChatMessage, Investigation, SourceDocument
from .deps import Actor, get_actor

router = APIRouter(prefix="/ai", tags=["ai"])
_TASKS: set[asyncio.Task] = set()


class RunRequest(BaseModel):
    investigation_id: uuid.UUID
    intent: Literal["auto", "full_analysis", "analyze", "capa", "gaps", "summarize", "edit", "question"] = "auto"
    message: str = ""
    new_document_ids: list[uuid.UUID] = []
    form: dict
    provenance: dict = {}


def _build_sources(docs: list[SourceDocument]) -> tuple[list[dict], str, list[str]]:
    usable, blocked = [], []
    for d in docs:
        if d.meta.get("scanned"):
            blocked.append(d.filename)
        elif d.text.strip():
            usable.append({"id": str(d.id), "name": d.filename, "kind": d.kind, "text": d.text})
    text = "\n\n".join(f"[Document: {s['name']}]\n{s['text']}" for s in usable)
    return usable, text, blocked


async def _execute(req: RunRequest, actor: Actor, q: asyncio.Queue) -> None:
    run_id = uuid.uuid4()
    steps: list[dict] = []
    warnings: list[str] = []
    messages: list[str] = []
    models: set[str] = set()
    tokens = 0
    n_patches = n_skipped = 0
    errors: list[str] = []
    try:
        async with SessionLocal() as session:
            inv = await session.get(Investigation, req.investigation_id)
            if not inv:
                await q.put({"type": "error", "text": "Investigation not found"})
                return
            docs = (await session.execute(
                select(SourceDocument).where(SourceDocument.investigation_id == req.investigation_id)
                .order_by(SourceDocument.created_at))).scalars().all()
            new_names = [d.filename for d in docs if d.id in set(req.new_document_ids)]
            session.add(ChatMessage(investigation_id=inv.id, role="user", content=req.message, attachments=new_names))
            await session.commit()
        sources, source_text, blocked = _build_sources(list(docs))
        intent = req.intent
        if intent == "auto" and req.new_document_ids and not req.message.strip():
            intent = "full_analysis"
        if settings.llm_mode == "live" and not settings.groq_api_key and intent != "edit":
            await q.put({"type": "error", "text": "GROQ_API_KEY is not set. Add your key to backend/.env (GROQ_API_KEY=...) and restart the backend. "
                         "For an offline UI test without AI set LLM_MODE=fixture."})
            return
        RUN_ID.set(str(run_id))
        await q.put({"type": "run_started", "run_id": str(run_id), "llm_mode": settings.llm_mode,
                     "mode_label": "offline dev fixture (no AI call)" if settings.llm_mode == "fixture" else "Groq"})
        state = {
            "run_id": str(run_id), "investigation_id": str(req.investigation_id), "intent": intent, "message": req.message,
            "form": req.form, "prov": req.provenance, "sources": sources, "source_text": source_text,
            "blocked_docs": blocked, "patches": [], "notes": [],
        }
        async for chunk in GRAPH.astream(state, stream_mode="custom"):
            if not isinstance(chunk, dict):
                continue
            t = chunk.get("type")
            if t == "step":
                if chunk["status"] in ("done", "error"):
                    steps.append({k: chunk.get(k) for k in ("node", "label", "status", "detail", "model", "tokens", "seconds")})
                    tokens += int(chunk.get("tokens") or 0)
                    for m in (chunk.get("model") or "").split(", "):
                        if m:
                            models.add(m)
                    if chunk["status"] == "error":
                        errors.append(f"{chunk['node']}: {chunk.get('detail')}")
            elif t == "patch":
                n_patches += 1
            elif t == "skipped":
                n_skipped += 1
            elif t == "warning":
                warnings.append(chunk["text"])
            elif t == "message":
                messages.append(chunk["text"])
            await q.put(chunk)
        await q.put({"type": "done", "run_id": str(run_id), "patches": n_patches, "skipped_protected": n_skipped,
                     "tokens": tokens, "models": sorted(models), "steps": steps, "warnings": warnings})
    except Exception as e:  # surface, never hang the stream
        errors.append(f"{type(e).__name__}: {e}")
        await q.put({"type": "error", "text": f"{type(e).__name__}: {str(e)[:300]}"})
    finally:
        try:
            async with SessionLocal() as session:
                session.add(AiRun(id=run_id, investigation_id=req.investigation_id, intent=req.intent, prompt_version=settings.prompt_version,
                                  llm_mode=settings.llm_mode, steps=steps, usage={"tokens": tokens, "models": sorted(models), "patches": n_patches},
                                  errors=errors, finished_at=datetime.now(timezone.utc)))
                if messages:
                    session.add(ChatMessage(investigation_id=req.investigation_id, role="assistant", content="\n\n".join(messages),
                                            meta={"run_id": str(run_id), "steps": steps, "warnings": warnings}))
                await session.commit()
        except Exception:
            pass
        ABORTED.discard(str(run_id))
        await q.put(None)


@router.post("/run", response_class=EventSourceResponse)
async def run(req: RunRequest, actor: Actor = Depends(get_actor)) -> AsyncIterable[ServerSentEvent]:
    q: asyncio.Queue = asyncio.Queue()
    task = asyncio.create_task(_execute(req, actor, q))
    _TASKS.add(task)
    task.add_done_callback(_TASKS.discard)
    while True:
        ev = await q.get()
        if ev is None:
            break
        yield ServerSentEvent(data=ev, event=ev["type"])


@router.get("/graph")
async def graph_mermaid():
    return {"mermaid": mermaid()}


@router.get("/models")
async def models():
    """Live check of the Groq catalogue + which configured models are available (used before the demo)."""
    if settings.llm_mode == "fixture" or not settings.groq_api_key:
        raise HTTPException(400, "GROQ_API_KEY not set (or LLM_MODE=fixture)")
    available = await list_models()
    cfg = {"analysis": settings.model_analysis, "fast": settings.model_fast, "fallback": settings.model_fallback}
    return {"configured": {k: {"id": v, "available": v in available} for k, v in cfg.items()}, "available": available}
