import { createAsyncThunk } from '@reduxjs/toolkit'
import type { RootState } from '../../app/store'
import { api } from '../../lib/api'
import { streamRun, type RunEvent } from '../../lib/sse'
import { addDocument, applyPatch, fetchGates, saveInvestigation, setLastRun, type DocInfo } from '../investigation/investigationSlice'
import { addMessage, failRun, finishRun, runStarted, startRun, stepEvent, waitEvent } from './copilotSlice'

// graph node -> form section anchor (the form scrolls to the section being filled)
const SECTION_OF_NODE: Record<string, string> = {
  extract_incident: 'sec-incident', find_similar: 'sec-class', fishbone: 'sec-fishbone', five_whys: 'sec-whys',
  root_cause: 'sec-rc', evidence_gaps: 'sec-gaps', capa: 'sec-capa', impact: 'sec-impact', summarize: 'sec-summary',
}

type RunArg = { message: string; intent?: string; newDocIds?: string[] }

export const runCopilot = createAsyncThunk('copilot/run', async (arg: RunArg, { dispatch, getState }) => {
  const inv = (getState() as RootState).investigation
  dispatch(startRun())
  let runId: string | null = null
  let failed = false
  let lastRun = { tokens: 0, models: [] as string[], modeLabel: '', patches: 0, skipped: 0 }
  try {
    await streamRun(
      { investigation_id: inv.id, intent: arg.intent ?? 'auto', message: arg.message, new_document_ids: arg.newDocIds ?? [], form: inv.form, provenance: inv.prov },
      (e: RunEvent) => {
        switch (e.type) {
          case 'run_started': runId = e.run_id as string; lastRun.modeLabel = e.mode_label as string; dispatch(runStarted(e.mode_label as string)); break
          case 'step':
            dispatch(stepEvent(e))
            if (e.status === 'running') document.getElementById(SECTION_OF_NODE[e.node as string])?.scrollIntoView({ behavior: 'smooth', block: 'start' })
            break
          case 'patch': dispatch(applyPatch(e.patch as never)); break
          case 'wait': dispatch(waitEvent(e.seconds as number)); break
          case 'warning': dispatch(addMessage({ role: 'system', text: e.text as string, warning: true })); break
          case 'message': dispatch(addMessage({ role: 'assistant', text: e.text as string, changes: e.changes as never, citations: e.citations as never })); break
          case 'done': lastRun = { ...lastRun, tokens: e.tokens as number, models: e.models as string[], patches: e.patches as number, skipped: e.skipped_protected as number }; break
          case 'error': failed = true; dispatch(failRun(e.text as string)); break
        }
      },
    )
  } catch (err) {
    failed = true
    dispatch(failRun(`The AI run could not be completed: ${(err as Error).message}`))
  }
  if (!failed) dispatch(finishRun(lastRun))
  if (runId) dispatch(setLastRun(runId))
  await dispatch(saveInvestigation({ aiRunId: runId }))
  await dispatch(fetchGates())
})

/** Composer entry point: uploads attachments, decides whether pasted text is a document or a chat message, runs the graph. */
export const sendMessage = createAsyncThunk('copilot/send', async (arg: { text: string; files: File[] }, { dispatch, getState }) => {
  const id = (getState() as RootState).investigation.id!
  const newDocIds: string[] = []
  const names: string[] = []
  const warn = (t: string) => dispatch(addMessage({ role: 'system', text: t, warning: true }))

  for (const f of arg.files) {
    try {
      const fd = new FormData()
      fd.append('investigation_id', id)
      fd.append('file', f)
      const d = await api<DocInfo>('/documents', { method: 'POST', body: fd })
      dispatch(addDocument(d)); newDocIds.push(d.id); names.push(d.filename)
      d.warnings.forEach((w) => warn(`${d.filename}: ${w}`))
    } catch (e) { warn(`Could not read ${f.name}: ${(e as Error).message}`) }
  }

  const text = arg.text.trim()
  const asDoc = text.length >= 350 && (text.split('\n').length >= 4 || /^\s*(from|subject)\s*:/im.test(text))
  let chatText = text
  if (asDoc) {
    try {
      const d = await api<DocInfo>('/documents/text', { method: 'POST', json: { investigation_id: id, text } })
      dispatch(addDocument(d)); newDocIds.push(d.id); names.push(d.filename)
      chatText = ''
    } catch (e) { warn(`Could not use the pasted text: ${(e as Error).message}`); return }
  }
  dispatch(addMessage({ role: 'user', text: asDoc ? `Pasted ${names[names.length - 1]?.toLowerCase() ?? 'text'} (${text.length} characters)` : chatText, attachments: names }))
  if (!chatText && !newDocIds.length) return
  await dispatch(runCopilot({ message: chatText, intent: newDocIds.length && !chatText ? 'full_analysis' : 'auto', newDocIds }))
})

export const loadSample = createAsyncThunk('copilot/sample', async (name: string, { dispatch }) => {
  const res = await fetch(`/api/samples/${encodeURIComponent(name)}`)
  if (!res.ok) { dispatch(addMessage({ role: 'system', text: 'Could not load that sample file.', warning: true })); return }
  const blob = await res.blob()
  await dispatch(sendMessage({ text: '', files: [new File([blob], name)] }))
})
