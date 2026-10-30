"""End-to-end through the HTTP API + the LangGraph workflow (offline LLM fixture, real PostgreSQL)."""
import json
from pathlib import Path

import pytest

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
pytestmark = pytest.mark.asyncio


async def _run(client, iid, form, prov=None, intent="full_analysis", message=""):
    r = await client.post("/api/ai/run", json={"investigation_id": iid, "intent": intent, "message": message, "form": form, "provenance": prov or {}})
    assert r.status_code == 200, r.text
    events, ev = [], None
    for line in r.text.splitlines():
        if line.startswith("event:"):
            ev = line[6:].strip()
        elif line.startswith("data:"):
            events.append((ev, json.loads(line[5:].strip())))
    return events


async def _new(client):
    iid = (await client.post("/api/investigations")).json()["id"]
    return iid, (await client.get(f"/api/investigations/{iid}")).json()


async def _upload(client, iid, name):
    r = await client.post("/api/documents", data={"investigation_id": iid}, files={"file": (name, (SAMPLES / name).read_bytes())})
    return r


async def test_full_analysis_populates_form_and_persists(client):
    iid, inv = await _new(client)
    assert (await _upload(client, iid, "IR-B-26-093_Omeprazole_Stage4.pdf")).status_code == 201
    events = await _run(client, iid, inv["form_data"])
    kinds = [e for e, _ in events]
    assert kinds[0] == "run_started" and kinds[-1] == "done"
    steps = [d["node"] for e, d in events if e == "step" and d["status"] == "done"]
    assert steps == ["extract_incident", "find_similar", "fishbone", "five_whys", "root_cause", "evidence_gaps", "capa", "impact", "summarize"] or \
        set(steps) >= {"extract_incident", "fishbone", "five_whys", "root_cause", "evidence_gaps", "capa", "impact", "summarize"}
    form = inv["form_data"]
    from app.forms import set_path
    for _, d in events:
        pass
    for e, d in events:
        if e == "patch":
            set_path(form, d["patch"]["path"], d["patch"]["value"])
    assert form["incident"]["batch_numbers"] == ["OMZ-2610-017"]
    assert {r["status"] for r in form["problem"]["requirements"]} == {"outside", "within"}
    assert len(form["root_causes"]) == 1 and form["root_causes"][0]["certainty"] in ("possible", "most_probable")
    for rc in form["root_causes"]:  # evidence blocks are mandatory
        assert rc["supporting_evidence"] and rc["contradicting_evidence"] and rc["assumptions"] and rc["missing_evidence"] and rc["verification_test"]
    assert {c["type"] for c in form["capa"]} == {"correction", "corrective", "preventive"}
    assert form["classification"]["recurrence"]["matches"][0]["rca_number"] == "RCA-2025-0041"   # recurrence found
    # AI fields carry provenance with a verbatim quote that really exists in the PDF
    p = next(d["patch"]["prov"] for e, d in events if e == "patch" and d["patch"]["path"] == "incident.product_name")
    assert p["by"] == "ai" and p["grounded"] == "grounded" and "Omeprazole" in p["quote"]

    # save -> reload from PostgreSQL
    prov = {d["patch"]["path"]: d["patch"]["prov"] for e, d in events if e == "patch" and d["patch"].get("prov")}
    saved = await client.put(f"/api/investigations/{iid}", json={"form_data": form, "provenance": prov, "version": inv["version"]})
    assert saved.status_code == 200 and saved.json()["version"] == inv["version"] + 1
    again = (await client.get(f"/api/investigations/{iid}")).json()
    assert again["form_data"]["incident"]["product_name"] == "Omeprazole (API)" and again["root_cause_summary"]
    # stale version is rejected (optimistic locking)
    stale = await client.put(f"/api/investigations/{iid}", json={"form_data": form, "provenance": prov, "version": inv["version"]})
    assert stale.status_code == 409
    audit = (await client.get(f"/api/investigations/{iid}/audit")).json()
    assert any(a["action"] == "ai_applied" for a in audit)


async def test_ai_never_overwrites_human_edits(client):
    iid, inv = await _new(client)
    await _upload(client, iid, "IR-B-26-093_Omeprazole_Stage4.pdf")
    form = inv["form_data"]
    form["incident"]["product_name"] = "My own product text"
    events = await _run(client, iid, form, prov={"incident.product_name": {"by": "user", "reviewed": True}})
    paths = [d["patch"]["path"] for e, d in events if e == "patch"]
    assert "incident.product_name" not in paths
    assert ("skipped", {"type": "skipped", "path": "incident.product_name"}) in events


async def test_scanned_pdf_blocks_analysis_with_clear_message(client):
    iid, inv = await _new(client)
    r = await _upload(client, iid, "Scanned_Incident_NO_TEXT.pdf")
    assert r.json()["scanned"] is True
    events = await _run(client, iid, inv["form_data"])
    msgs = [d["text"] for e, d in events if e == "message"]
    assert msgs and "OCR" in msgs[0]
    assert not [1 for e, _ in events if e == "patch"]          # nothing was invented from an unreadable file


async def test_chat_correction_updates_only_that_field(client):
    iid, inv = await _new(client)
    await _upload(client, iid, "IR-B-26-093_Omeprazole_Stage4.pdf")
    events = await _run(client, iid, inv["form_data"], intent="edit", message="ah sorry the batch number is OMZ-2610-018")
    patches = [d["patch"] for e, d in events if e == "patch"]
    assert patches[0]["path"] == "incident.batch_numbers" and patches[0]["value"] == ["OMZ-2610-018"] and patches[0]["prov"]["by"] == "user"
    msg = next(d for e, d in events if e == "message")
    assert msg["changes"][0]["new"] == "OMZ-2610-018"


async def test_qa_confirmation_requires_role_and_note(client):
    iid, inv = await _new(client)
    form = inv["form_data"]
    form["root_causes"] = [{"id": "rc-1", "statement": "x", "certainty": "possible", "supporting_evidence": [{"quote": "q"}], "verification_test": "t", "meta": {"by": "ai"}}]
    await client.put(f"/api/investigations/{iid}", json={"form_data": form, "provenance": {}, "version": inv["version"]})
    url = f"/api/investigations/{iid}/root-causes/rc-1/confirm"
    assert (await client.post(url, json={"note": "long enough rationale text"})).status_code == 403      # investigator
    qa = {"X-Demo-Role": "qa", "X-Demo-User": "QA"}
    assert (await client.post(url, json={"note": "short"}, headers=qa)).status_code == 422
    ok = await client.post(url, json={"note": "DCS trend and bench test confirm the failure"}, headers=qa)
    assert ok.status_code == 200 and ok.json()["form_data"]["root_causes"][0]["certainty"] == "confirmed"


async def test_submit_is_blocked_until_gates_pass(client):
    iid, _ = await _new(client)
    r = await client.post(f"/api/investigations/{iid}/submit")
    assert r.status_code == 422 and r.json()["detail"]["gates"]["blocking_open"] > 0


async def test_missing_key_fails_fast_with_clear_message(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "llm_mode", "live")
    monkeypatch.setattr(settings, "groq_api_key", "")
    iid, inv = await _new(client)
    await _upload(client, iid, "IR-B-26-093_Omeprazole_Stage4.pdf")
    events = await _run(client, iid, inv["form_data"])
    err = [d for e, d in events if e == "error"]
    assert len(err) == 1 and "GROQ_API_KEY" in err[0]["text"]
    assert not [1 for e, _ in events if e == "patch"]


async def test_llm_outage_is_reported_once_and_remaining_steps_skipped(client, monkeypatch):
    from app.ai import llm
    from app.ai.nodes import analysis, chat, extract

    async def boom(*a, **k):
        raise llm.LLMUnavailable("All models failed. Last error: 429")
    for mod in (analysis, chat, extract):
        monkeypatch.setattr(mod, "structured", boom)
    iid, inv = await _new(client)
    await _upload(client, iid, "IR-B-26-093_Omeprazole_Stage4.pdf")
    events = await _run(client, iid, inv["form_data"])
    errored = [d["node"] for e, d in events if e == "step" and d["status"] == "error"]
    warns = [d for e, d in events if e == "warning"]
    assert errored == ["extract_incident"] and len(warns) == 1       # one clear warning, later nodes skipped
    assert events[-1][0] == "done"
