"""Groq access: one structured-output helper with per-model pacing, fallbacks and a repair retry.

Why this exists (verified against Groq docs, Oct 2026): the free tier gives ~8K tokens/minute *per
model*, so we (1) keep every request small, (2) track a rolling per-model token budget and pick the
first model in a node's preference list that still has room, (3) fall back across models on
429/5xx, and (4) never retry a 413 (request too large)."""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Awaitable, Callable, TypeVar

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from ..config import settings

T = TypeVar("T", bound=BaseModel)
Emit = Callable[[dict], None]


class LLMUnavailable(RuntimeError):
    pass


class RequestTooLarge(RuntimeError):
    pass


def est_tokens(*texts: str) -> int:
    return sum(len(t) for t in texts) // 3 + 50


class Pacer:
    """Rolling 60 s token window per model + cooldowns after a 429."""

    def __init__(self) -> None:
        self.win: dict[str, deque] = defaultdict(deque)
        self.cool: dict[str, float] = {}
        self.lock = asyncio.Lock()

    def _used(self, model: str, now: float) -> int:
        w = self.win[model]
        while w and now - w[0][0] > 60:
            w.popleft()
        return sum(t for _, t in w)

    async def acquire(self, prefs: list[str], est: int, emit: Emit | None = None, exclude: set[str] | None = None) -> str:
        exclude = exclude or set()
        cands = [m for m in prefs if m not in exclude]
        if not cands:
            raise LLMUnavailable("No model left to try")
        waited = 0.0
        while True:
            async with self.lock:
                now = time.monotonic()
                for m in cands:
                    if self.cool.get(m, 0) > now:
                        continue
                    if self._used(m, now) + est <= settings.tpm_budget:
                        self.win[m].append((now, est))
                        return m
                # nothing free: how long until the first candidate frees enough room?
                soonest = 60.0
                for m in cands:
                    w, used = self.win[m], self._used(m, now)
                    need, t = used + est - settings.tpm_budget, 0.0
                    for ts, tok in w:
                        need -= tok
                        t = max(0.0, 60 - (now - ts))
                        if need <= 0:
                            break
                    soonest = min(soonest, max(t, self.cool.get(m, 0) - now, 1.0))
            if waited > 90:  # give up pacing, just go with the best preference
                return cands[0]
            pause = min(soonest, 15.0)
            if emit:
                emit({"type": "wait", "seconds": round(pause), "models": cands})
            await asyncio.sleep(pause)
            waited += pause

    def adjust(self, model: str, est: int, actual: int) -> None:
        w = self.win[model]
        for i in range(len(w) - 1, -1, -1):
            if w[i][1] == est:
                w[i] = (w[i][0], actual)
                break

    def cooldown(self, model: str, seconds: float) -> None:
        self.cool[model] = time.monotonic() + seconds


pacer = Pacer()


def _build(model: str, max_tokens: int):
    from langchain_groq import ChatGroq

    kw: dict = dict(model=model, temperature=0.1, max_tokens=max_tokens, max_retries=1, timeout=60,
                    api_key=settings.groq_api_key)
    if model.startswith("openai/gpt-oss"):
        kw["reasoning_effort"] = "low"
    elif model.startswith("qwen"):
        kw["reasoning_effort"] = "none"
    return ChatGroq(**kw)


def prefs_for(role: str) -> list[str]:
    a, f, fb = settings.model_analysis, settings.model_fast, settings.model_fallback
    return {
        "extract": [a, f, fb],  # list extraction: qwen's best-effort schemas return empty lists, so it is last resort
        "heavy": [a, fb, f],   # root cause, CAPA
        "mid": [fb, f, a],
        "light": [f, fb, a],   # routing, summaries, gaps
    }[role]


_CACHE = Path(__file__).resolve().parents[2] / ".llm_cache"


def _cache_key(model_hint: str, schema: type, system: str, user: str) -> Path:
    h = hashlib.sha256(f"{schema.__name__}|{system}|{user}".encode()).hexdigest()[:32]
    return _CACHE / f"{h}.json"


async def structured(schema: type[T], system: str, user: str, *, role: str = "heavy", max_tokens: int = 2200,
                     emit: Emit | None = None, validate: Callable[[T], str | None] | None = None) -> tuple[T, dict]:
    """Run one structured call. Returns (parsed object, meta{model,tokens,seconds,attempts})."""
    if settings.llm_mode == "fixture":
        from . import fixtures

        return fixtures.respond(schema, user), {"model": "offline-fixture", "tokens": 0, "seconds": 0.0, "attempts": 1}
    if not settings.groq_api_key:
        raise LLMUnavailable("GROQ_API_KEY is not set in backend/.env")

    if settings.llm_cache:
        p = _cache_key(role, schema, system, user)
        if p.exists():
            return schema.model_validate_json(p.read_text(encoding="utf-8")), {"model": "cache", "tokens": 0, "seconds": 0.0, "attempts": 0}

    schema_tokens = len(json.dumps(schema.model_json_schema())) // 4
    est = est_tokens(system, user) + schema_tokens + max_tokens
    if est > 7800:
        raise RequestTooLarge(f"Prompt too large for one Groq request (~{est} tokens)")
    pace_est = min(est - max_tokens // 2, settings.tpm_budget)  # completions are usually shorter than max_tokens; never exceed one window
    prefs = prefs_for(role)
    failed: set[str] = set()
    attempts = 0
    last_err = ""
    t0 = time.monotonic()
    while True:
        model = await pacer.acquire(prefs, pace_est, emit, failed)
        attempts += 1
        repaired = False
        msgs = [SystemMessage(content=system), HumanMessage(content=user)]
        while True:
            try:
                chain = _build(model, max_tokens).with_structured_output(schema, method="json_schema", strict=True, include_raw=True)
                res = await chain.ainvoke(msgs)
                raw = res.get("raw")
                tokens = (getattr(raw, "usage_metadata", None) or {}).get("total_tokens", est)
                pacer.adjust(model, pace_est, tokens)
                bad = validate(res["parsed"]) if (validate and res.get("parsed") is not None) else None
                if res.get("parsed") is not None and not bad:
                    if settings.llm_cache:
                        _CACHE.mkdir(exist_ok=True)
                        _cache_key(role, schema, system, user).write_text(res["parsed"].model_dump_json(), encoding="utf-8")
                    return res["parsed"], {"model": model, "tokens": tokens, "seconds": round(time.monotonic() - t0, 1), "attempts": attempts}
                last_err = (bad or str(res.get("parsing_error")))[:300]
                if not repaired:  # one repair retry on the same model
                    repaired = True
                    msgs = msgs + [HumanMessage(content=f"Your previous output was invalid ({last_err}). Return only valid JSON matching the schema.")]
                    continue
                failed.add(model)
                break
            except Exception as e:  # classify Groq / network errors
                name = type(e).__name__
                status = getattr(e, "status_code", None)
                if status == 413:
                    raise RequestTooLarge("Groq rejected the request as too large (413)") from e
                if name == "RateLimitError" or status == 429:
                    ra = 30.0
                    try:
                        ra = float(getattr(e, "response", None).headers.get("retry-after", 30))  # type: ignore[union-attr]
                    except Exception:
                        pass
                    pacer.cooldown(model, ra)
                    last_err = f"429 on {model}"
                    break  # keep the model eligible: the pacer skips it until the cooldown ends
                elif status == 400:
                    last_err = f"400 on {model}: {str(e)[:200]}"
                else:
                    last_err = f"{name} on {model}: {str(e)[:200]}"
                failed.add(model)
                break
        if all(m in failed for m in prefs) or attempts >= 8:
            raise LLMUnavailable(f"All models failed. Last error: {last_err}")


async def list_models() -> list[str]:
    import httpx

    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {settings.groq_api_key}"})
        r.raise_for_status()
        return sorted(m["id"] for m in r.json().get("data", []))
