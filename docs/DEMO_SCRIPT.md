# Video 1 — Product demonstration (target 6–7 min, limit 5–8)

**Before recording**: `scripts\dev.ps1`; run `groq_check.py`; clear old test records (list page should show only the 3 closed
historical investigations); browser at 100 %, window ~1440 wide; Groq key set, `LLM_MODE=live`. Do one rehearsal take first.
If Groq is slow (free tier), start the analysis, narrate the Copilot's step list, and cut the wait in editing.

| Time | Scene | What to show / say |
|---|---|---|
| 0:00 | **Context** (list page) | "API manufacturer. Workflow: deviation → RCA → CAPA. This module is the RCA step." Point at the 3 closed historical investigations: they feed the recurrence check. Click **New investigation**. |
| 0:30 | **The pattern** | Form on the left says *Awaiting AI extraction…* — fields are read-only; the Copilot on the right is the way in. |
| 0:50 | **PDF intake** | Click the sample **Incident report (PDF)** (or drag the file). Watch the step list stream; the form scrolls to each section as it is filled. Mention parsing happens server-side (pdfplumber), the LangGraph runs 9 steps, two analyses in parallel. |
| 1:40 | **Extraction + provenance** | Section 2: blue = verified in the document, amber = verify, *Not provided in source* for times the report never states. Hover a badge → verbatim quote + model + confidence. Mention: "the reference video's AI invented a quantity; here every value is checked against the source." |
| 2:30 | **Problem & spec vs actual** | Requirement vs actual rows computed in code (OUTSIDE badges). Recurrence card: *RCA-2025-0041 same valve, earlier CAPA not effective* → class escalated. |
| 3:15 | **5 Whys + fishbone** | Evidence-backed vs hypothesis levels; stopping rationale. Fishbone: all six categories, colours = disposition. |
| 4:00 | **Root cause (hypothesis)** | Open the card: supporting quotes ✓, contradicting evidence, assumptions, missing evidence, verification test. Say the key sentence: *"a quote existing in the report doesn't prove the cause — it's a hypothesis until QA confirms."* |
| 4:40 | **Missing evidence + CAPA** | Gaps grouped by evidence area (DCS alarm journal, interlock bypass register…). CAPA: correction vs corrective vs preventive, strength, effectiveness check; note no "retrain" shortcut. |
| 5:20 | **Conversational correction** | Type *"ah sorry the batch number is OMZ-2610-018"* → diff card; the field updates, marked as your edit. |
| 5:45 | **Review, edit, save** | Edit a CAPA owner/due date, **Accept all**, show readiness checklist turning green (warnings remain). Show *Saved*. **Reload the page** → everything persists (PostgreSQL). |
| 6:30 | **QA review + audit** | Switch role → QA Head, confirm the root cause with a rationale, approve. Open **Audit trail**: AI-applied vs your edits. Close with the limits slide/sentence: prototype, demo roles, drafts for qualified review. |
| 7:00 | (optional) | Paste the **shift-log text** or the **.eml**, or show the scanned PDF being *blocked* with an OCR-required message. |

Keep it on the user experience and the AI form-filling. Don't read fields aloud one by one.

---

# Video 2 — Code walkthrough (target 7–9 min, limit 5–10)

Open the project in the editor; keep the architecture diagram from the README on screen first (20 s).

| Time | Topic | Where to look |
|---|---|---|
| 0:00 | Architecture & stack | README "Stack"; flow: React/Redux → FastAPI (SSE) → LangGraph → Groq; PostgreSQL |
| 0:40 | **Frontend structure** | `frontend/src/features/` : `investigation` (form, slice), `copilot` (panel, SSE thunk), `list`, `session`; `lib/paths.ts` (dot-paths with item ids) |
| 1:30 | **Form-filling interaction** | `investigationSlice.ts`: `applyPatch` (AI), `editField` (human → provenance `by:user`), `markReviewed`; `AiField.tsx` derives the visual state from provenance |
| 2:30 | **SSE from a POST** | `lib/sse.ts` (fetch + eventsource-parser, because EventSource can't POST), `copilot/actions.ts` (`runCopilot`: event → Redux actions, auto-scroll, autosave) |
| 3:15 | **API endpoints** | `api/investigations.py` (CRUD, optimistic version, gates, confirm/submit/approve, audit), `api/documents.py` (upload/paste), `api/ai.py` (`/ai/run` SSE, background task + queue), `/docs` |
| 4:00 | **Document/text extraction** | `services/parsing.py` (PDF text + tables + scanned detection, .eml incl. attachments, .docx, pasted-email detection) |
| 4:40 | **LangGraph workflow** | `ai/graph.py` docstring diagram: router, fan-out `fishbone ∥ five_whys`, join at `root_cause`, conditional paths (capa / gaps / edit / question / no_source); `ai/common.py` state + `put()` protection rules; show `GET /api/ai/graph` Mermaid |
| 5:30 | **LLM integration** | `ai/llm.py`: strict JSON-schema structured output, per-model token pacing, fallbacks on 429, repair retry; `ai/outputs.py` (schemas with mandatory evidence blocks); model choice & why (README) |
| 6:15 | **How AI output populates the form** | `ai/nodes/extract.py` → `services/grounding.py` (quote + number verification) → patch `{path,value,prov}` → streamed → `applyPatch`; spec status computed in `forms.evaluate_requirement`, not by the LLM |
| 7:00 | **Guardrails & recommendations** | `ai/nodes/analysis.py` (repair passes for evidence blocks and CAPA coverage; recurrence escalation), `services/gates.py` (readiness rules), `ai/prompts.py` |
| 7:40 | **Database & saving** | `models.py` (JSONB `form_data` + `provenance`, tsvector/GIN, `audit_log`, `ai_runs`), `PUT /investigations/{id}`: version check → `audit.diff_forms` → per-field audit rows; `similar.py` recurrence query |
| 8:20 | **Tests** | `pytest` (25) incl. graph run against `rca_test`, protection of human edits, scanned-PDF block; `npm test` |
| 8:50 | Close | Limits: no OCR, demo roles, free-tier throughput; next steps |
