"""Shared building blocks for the LangGraph nodes: state, progress events, patch emission."""
from __future__ import annotations

import copy
import operator
import time
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Annotated, Any, TypedDict

from langgraph.config import get_stream_writer

from .llm import LLMUnavailable
from ..forms import (LIST_PATHS, STRING_LIST_PATHS, get_path, is_protected_scalar, merge_list_fill, set_path)


# Run-level circuit breaker: when the LLM is unavailable (no key / all models failed) the remaining
# nodes of that run are skipped instead of each failing with its own error.
RUN_ID: ContextVar[str | None] = ContextVar("run_id", default=None)
ABORTED: set[str] = set()


class SkipNode(Exception):
    pass


def skippable(fn):
    async def wrapper(state):
        try:
            return await fn(state)
        except SkipNode:
            return {}
    wrapper.__name__ = fn.__name__
    return wrapper


class RCAState(TypedDict, total=False):
    run_id: str
    investigation_id: str
    intent: str
    message: str
    history: list[dict]
    form: dict          # snapshot of the form when the run started (never mutated)
    prov: dict          # snapshot of per-field provenance (used for the "never overwrite human edits" rule)
    sources: list[dict]
    blocked_docs: list[str]
    source_text: str
    patches: Annotated[list, operator.add]   # reducer: parallel branches may both append
    missing_info: list[str]
    similar: list[dict]
    notes: Annotated[list, operator.add]


def working_form(state: RCAState) -> dict:
    """The form as the user sees it *plus* the patches applied so far in this run."""
    f = copy.deepcopy(state["form"])
    for p in state.get("patches", []):
        set_path(f, p["path"], copy.deepcopy(p["value"]))
    return f


class StepCtx:
    def __init__(self, w, node: str, label: str):
        self.w, self.node, self.label = w, node, label
        self.models: list[str] = []
        self.tokens = 0
        self.detail = ""
        self.t0 = time.monotonic()
        self.error: str | None = None

    def used(self, meta: dict) -> None:
        if meta.get("model") and meta["model"] not in self.models:
            self.models.append(meta["model"])
        self.tokens += int(meta.get("tokens") or 0)


@asynccontextmanager
async def step(node: str, label: str):
    w = get_stream_writer()
    rid = RUN_ID.get()
    if rid and rid in ABORTED:
        raise SkipNode()
    ctx = StepCtx(w, node, label)
    w({"type": "step", "node": node, "label": label, "status": "running"})
    try:
        yield ctx
    except Exception as e:  # a failing node degrades the run, it does not kill it
        ctx.error = f"{type(e).__name__}: {e}"
        if isinstance(e, LLMUnavailable) and rid:
            ABORTED.add(rid)
        w({"type": "step", "node": node, "label": label, "status": "error", "detail": ctx.error[:300],
           "seconds": round(time.monotonic() - ctx.t0, 1)})
        w({"type": "warning", "text": f"{label} could not be completed: {ctx.error[:240]}"})
    else:
        w({"type": "step", "node": node, "label": label, "status": "done", "detail": ctx.detail,
           "model": ", ".join(ctx.models), "tokens": ctx.tokens, "seconds": round(time.monotonic() - ctx.t0, 1)})


def emit_wait(w):
    return lambda ev: w(ev)


def put(state: RCAState, path: str, value: Any, *, prov: dict | None = None, mode: str = "fill") -> list[dict]:
    """Create (and stream) a patch. In 'fill' mode human-edited / reviewed content is never overwritten."""
    w = get_stream_writer()
    existing = get_path(state["form"], path)
    is_list = path in LIST_PATHS and path not in STRING_LIST_PATHS
    if mode == "fill":
        if is_list:
            value, _replaced = merge_list_fill(existing or [], value)
        elif is_protected_scalar(state.get("prov", {}), path):
            w({"type": "skipped", "path": path})
            return []
    patch = {"path": path, "value": value, "prov": prov, "mode": mode}
    w({"type": "patch", "patch": patch})
    return [patch]


def source_excerpt(state: RCAState, max_chars: int = 3800) -> str:
    t = state.get("source_text", "")
    return t if len(t) <= max_chars else t[:max_chars] + "\n[...truncated...]"


def digest(form: dict) -> str:
    """Compact fact sheet from the working form (keeps downstream prompts small)."""
    inc, prob = form["incident"], form["problem"]
    lines = [
        f"PRODUCT: {inc.get('product_name') or '?'} | BATCH: {', '.join(inc.get('batch_numbers', [])) or '?'} | STAGE: {inc.get('process_stage') or '?'} | SITE: {inc.get('site') or '?'}",
        f"EQUIPMENT: {', '.join(inc.get('equipment_ids', [])) or '?'} | INSTRUMENTS: {', '.join(inc.get('instrument_ids', [])) or '?'}",
        f"EVENT TYPE: {form['classification'].get('event_type') or '?'}",
        f"PROBLEM: {prob.get('problem_statement') or '?'}",
    ]
    for r in prob.get("requirements", []):
        lines.append(f"REQ: {r.get('parameter')}: requirement {r.get('requirement')} -> actual {r.get('actual')} [{r.get('status', '?')}]")
    for a in form["containment"].get("immediate_actions", []):
        lines.append(f"ACTION: {a.get('action')} ({a.get('when') or 'time n/s'})")
    for t in form.get("timeline", [])[:12]:
        lines.append(f"TIME: {t.get('when') or '?'} - {t.get('event')}")
    return "\n".join(lines)
