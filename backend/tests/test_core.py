import copy
from pathlib import Path

import pytest

from app.forms import default_form, evaluate_requirement, merge_list_fill, set_path, get_path
from app.services import audit, gates
from app.services.grounding import ground_scalar, numbers_in_source, quote_in_source
from app.services.parsing import UnsupportedDocument, parse_text, parse_upload

SAMPLES = Path(__file__).resolve().parents[2] / "samples"


# ------------------------------------------------------------------ parsing
def test_pdf_text_extracted_with_page_markers():
    d = parse_upload("x.pdf", (SAMPLES / "IR-B-26-093_Omeprazole_Stage4.pdf").read_bytes())
    assert d.kind == "pdf" and not d.scanned and "[Page 1]" in d.text and "TCV-204" in d.text


def test_scanned_pdf_is_flagged_not_silently_accepted():
    d = parse_upload("scan.pdf", (SAMPLES / "Scanned_Incident_NO_TEXT.pdf").read_bytes())
    assert d.scanned is True and d.warnings and "OCR" in d.warnings[0]


def test_eml_and_pasted_email_detection():
    d = parse_upload("a.eml", (SAMPLES / "OOS_Gabapentin_GBP-26-0734.eml").read_bytes())
    assert d.kind == "email" and "Methanol" in d.text and d.meta["headers"]["Subject"].startswith("OOS")
    pasted = parse_text("From: a@b.c\nSubject: OOS result\nSent: today\n\nBatch X failed assay.")
    assert pasted.kind == "email"
    assert parse_text("Shift log: charged lot 0912").kind == "text"


def test_legacy_msg_rejected_with_helpful_message():
    with pytest.raises(UnsupportedDocument):
        parse_upload("mail.msg", b"\xd0\xcf\x11\xe0" + b"\x00" * 50)


# ---------------------------------------------------------------- grounding
SRC = "The mass temperature went down to -11.6 °C. Sulfone (Imp-D) 0.91% (IPC limit NMT 0.30%)."


def test_grounding_detects_invented_values():
    assert quote_in_source("temperature went down to -11.6 C", SRC)
    assert not quote_in_source("operator fell asleep", SRC)
    assert numbers_in_source("0.91% vs 0.30%", SRC)
    assert not numbers_in_source("12 capsules", SRC)  # the reference demo's hallucination
    assert ground_scalar("0.91%", "Sulfone (Imp-D) 0.91%", SRC) == "grounded"
    assert ground_scalar("4.5%", "Sulfone 4.5%", SRC) == "unverified"
    assert ground_scalar(None, None, SRC) == "empty"


# --------------------------------------------------------- spec vs actual
@pytest.mark.parametrize("req,actual,expected", [
    ("NMT 0.10%", "0.27%", "outside"), ("NMT 0.30%", "0.91%", "outside"), ("NMT 0.5%", "0.46%", "within"),
    ("-5 °C to +5 °C", "-11.6 / +13.8", "outside"), ("-5 to +5 C", "+2", "within"),
    ("98.0-102.0%", "99.4%", "within"), ("NLT 700 mmHg", "710", "within"), ("NMT 3000 ppm", "4,220 ppm", "outside"),
    ("see SOP", "ok", "unknown"),
])
def test_evaluate_requirement(req, actual, expected):
    assert evaluate_requirement(req, actual) == expected


# ------------------------------------------------- human edits are protected
def test_merge_list_fill_keeps_human_items():
    existing = [{"id": "a", "statement": "mine", "meta": {"by": "user", "reviewed": True}},
                {"id": "b", "statement": "old ai", "meta": {"by": "ai", "reviewed": False}}]
    merged, replaced = merge_list_fill(existing, [{"id": "n", "statement": "new ai", "meta": {"by": "ai"}}, {"id": "dup", "statement": "MINE", "meta": {"by": "ai"}}])
    assert [m["id"] for m in merged] == ["a", "n"] and replaced == 1   # duplicate of a human item is dropped


# -------------------------------------------------------------------- gates
def test_gates_block_empty_form_and_pass_review_rules():
    f = default_form()
    g = gates.summary(gates.evaluate(f))
    assert not g["ready"] and g["blocking_open"] >= 8
    f["root_causes"] = [{"id": "rc1", "statement": "Valve stuck", "supporting_evidence": [{"quote": "q"}], "contradicting_evidence": [],
                         "assumptions": ["a"], "missing_evidence": ["m"], "verification_test": "t", "meta": {"by": "ai", "reviewed": False}}]
    ids = {x["id"]: x for x in gates.evaluate(f)}
    assert not ids["rc_evidence"]["passed"]          # contradicting evidence block missing
    assert not ids["reviewed"]["passed"]             # unreviewed AI item
    f["root_causes"][0]["contradicting_evidence"] = ["None found in the provided sources"]
    f["root_causes"][0]["meta"]["reviewed"] = True
    f["capa"] = [{"id": "c1", "type": "corrective", "action": "retrain operators", "linked_to": ["rc1"], "strength": "training",
                  "effectiveness": {"criterion": "x"}, "owner": "", "meta": {"by": "user"}}]
    ids = {x["id"]: x for x in gates.evaluate(f)}
    assert ids["rc_evidence"]["passed"] and ids["reviewed"]["passed"] and ids["capa_coverage"]["passed"]
    assert not ids["training_only"]["passed"]        # retraining alone is flagged


# -------------------------------------------------------------------- audit
def test_audit_diff_collapses_items_and_ignores_ids():
    o = default_form(); n = copy.deepcopy(o)
    set_path(n, "incident.product_name", "Omeprazole")
    n["timeline"] = [{"id": "evt-abc123", "when": "x", "event": "Valve stuck", "meta": {"by": "ai"}}]
    ch = audit.diff_forms(o, n)
    assert ("incident.product_name", None, "Omeprazole") in ch
    assert ("timeline.evt-abc123", None, "added: Valve stuck") in ch and len(ch) == 2
    assert get_path(n, "timeline.evt-abc123.event") == "Valve stuck"
