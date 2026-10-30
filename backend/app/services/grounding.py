"""Grounding: check that what the model *quotes* really exists in the source documents.

Important distinction (also shown in the UI): a quote that exists proves the model read the
source - it does NOT prove the model's causal interpretation is right. Extracted facts are
labelled grounded/unverified; root-cause statements are always labelled as hypotheses."""
from __future__ import annotations

import re

from rapidfuzz import fuzz

_WS = re.compile(r"\s+")
_NUMTOK = re.compile(r"\d[\d.,]*")


def norm(text: str) -> str:
    t = (text or "").lower()
    t = t.replace("°", " ").replace("–", "-").replace("—", "-").replace("‘", "'").replace("’", "'")
    return _WS.sub(" ", t).strip()


def quote_in_source(quote: str | None, source: str, threshold: int = 88) -> bool:
    if not quote or len(quote.strip()) < 3:
        return False
    q, s = norm(quote), norm(source)
    if q in s:
        return True
    if len(q) > 400:
        q = q[:400]
    return fuzz.partial_ratio(q, s) >= threshold


def numbers_in_source(value: str | None, source: str) -> bool:
    """Every number that appears in `value` must also appear in the source text."""
    s = norm(source).replace(",", "")
    for tok in _NUMTOK.findall(value or ""):
        t = tok.replace(",", "").rstrip(".")
        if t and t not in s:
            return False
    return True


def ground_scalar(value: str | None, quote: str | None, source: str) -> str:
    """'grounded' (quote found, numbers present) | 'unverified' (value without support) | 'empty'."""
    if value is None or not str(value).strip():
        return "empty"
    if quote_in_source(quote, source) and numbers_in_source(value, source):
        return "grounded"
    # value itself literally in the source also counts
    if norm(str(value)) in norm(source):
        return "grounded"
    return "unverified"


def ground_quotes(quotes: list[str | None], source: str) -> list[bool]:
    return [quote_in_source(q, source) for q in quotes]
