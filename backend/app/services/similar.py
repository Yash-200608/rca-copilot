"""Recurrence check: find closed historical investigations that look like the current one.
Signals: shared equipment tags (JSONB), same product, and Postgres full-text rank over a
denormalised `search_text` (tsvector + GIN index)."""
from __future__ import annotations

import re

from sqlalchemy import ARRAY, Text, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

STOP = {"the", "and", "for", "with", "was", "were", "that", "this", "from", "into", "not", "has", "had", "after", "during", "batch", "api"}


def _tokens(*parts: str) -> list[str]:
    seen: list[str] = []
    for p in parts:
        for t in re.findall(r"[A-Za-z0-9]{3,}", p or ""):
            t = t.lower()
            if t not in STOP and t not in seen:
                seen.append(t)
    return seen[:25]


async def find_similar(session: AsyncSession, investigation_id, form: dict, limit: int = 3) -> list[dict]:
    inc = form.get("incident", {})
    tags = [e.upper() for e in inc.get("equipment_ids", [])]
    toks = _tokens(inc.get("product_name", ""), inc.get("process_stage", ""), " ".join(tags),
                   form.get("header", {}).get("title", ""), form.get("problem", {}).get("problem_statement", ""))
    if not toks and not tags:
        return []
    q = " | ".join(toks) if toks else "zzzznomatch"
    stmt = text(
        """
        select id, rca_number, title, product, status, root_cause_summary, form_data,
               jsonb_exists_any(equipment_tags, :tags) as eq,
               ts_rank(search_vector, to_tsquery('english', :q)) as rank
        from investigations
        where status in ('closed', 'approved')
          and id <> :self
          and (search_vector @@ to_tsquery('english', :q) or jsonb_exists_any(equipment_tags, :tags))
        order by eq desc, rank desc
        limit :lim
        """
    ).bindparams(bindparam("tags", type_=ARRAY(Text)))
    rows = (await session.execute(stmt, {"tags": tags, "q": q, "self": investigation_id, "lim": limit})).mappings().all()
    out = []
    prod = (inc.get("product_name", "") or "").lower().split(" ")[0]
    for r in rows:
        # relevance: shared equipment tag, or the same product (first word), otherwise it is just word overlap
        if not (r["eq"] or (prod and prod in (r["product"] or "").lower())):
            continue
        capas = (r["form_data"] or {}).get("capa", [])
        outcome = next((c.get("effectiveness", {}).get("result_note") for c in capas if c.get("effectiveness", {}).get("result_note")), "")
        out.append({
            "rca_number": r["rca_number"], "title": r["title"], "product": r["product"],
            "root_cause": r["root_cause_summary"], "shared_equipment": bool(r["eq"]),
            "capa_summary": "; ".join(c.get("action", "") for c in capas[:3]), "capa_outcome": outcome,
            "score": round(float(r["rank"] or 0), 3),
        })
    return out
