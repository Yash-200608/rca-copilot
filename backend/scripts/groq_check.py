"""Step-0 verification against the LIVE Groq API. Run after putting GROQ_API_KEY in backend/.env:

    backend\\.venv\\Scripts\\python backend\\scripts\\groq_check.py

It (1) lists the live model catalogue and checks the three configured models, (2) makes one tiny call per
model and prints YOUR account's real rate-limit headers, (3) runs the largest strict schema (incident
identity extraction) on the sample incident report and prints model / tokens / seconds / result."""
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402

from app.ai import prompts  # noqa: E402
from app.ai.llm import list_models, structured  # noqa: E402
from app.ai.outputs import IdentityOut  # noqa: E402
from app.config import settings  # noqa: E402
from app.services.parsing import parse_upload  # noqa: E402

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "IR-B-26-093_Omeprazole_Stage4.pdf"


async def main() -> None:
    if not settings.groq_api_key:
        print("GROQ_API_KEY is empty in backend/.env"); return
    settings.llm_mode = "live"
    models = {"analysis": settings.model_analysis, "fast": settings.model_fast, "fallback": settings.model_fallback}
    avail = await list_models()
    print(f"Catalogue: {len(avail)} models")
    for role, m in models.items():
        print(f"  {role:9} {m:28} {'AVAILABLE' if m in avail else 'NOT IN CATALOGUE  <-- change MODEL_* in .env'}")
    print("\nRate limits for this account (response headers):")
    async with httpx.AsyncClient(timeout=30) as c:
        for m in models.values():
            r = await c.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                             json={"model": m, "messages": [{"role": "user", "content": "ok"}], "max_tokens": 16})
            h = r.headers
            print(f"  {m:28} HTTP {r.status_code}  req/day limit={h.get('x-ratelimit-limit-requests')}  tokens/min limit={h.get('x-ratelimit-limit-tokens')}  "
                  f"remaining tokens={h.get('x-ratelimit-remaining-tokens')}")
    text = parse_upload(SAMPLE.name, SAMPLE.read_bytes()).text
    t0 = time.time()
    out, meta = await structured(IdentityOut, prompts.IDENTITY, f"SOURCE:\n{text}", role="heavy", max_tokens=2000)
    print(f"\nIdentity extraction: model={meta['model']} tokens={meta['tokens']} seconds={time.time() - t0:.1f} attempts={meta['attempts']}")
    for f in ("product_name", "process_stage", "deviation_ref", "problem_statement", "detection_datetime"):
        v = getattr(out, f)
        print(f"  {f:20} = {v.value!r}   quote={v.quote!r}")


asyncio.run(main())
