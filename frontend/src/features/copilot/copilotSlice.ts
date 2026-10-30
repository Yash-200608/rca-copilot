import { createSlice, type PayloadAction } from '@reduxjs/toolkit'
import type { Json } from '../../lib/paths'

export type Step = { node: string; label: string; status: 'running' | 'done' | 'error'; detail?: string; model?: string; tokens?: number; seconds?: number }
export type Msg = {
  id: string; role: 'user' | 'assistant' | 'system'; text: string; attachments?: string[]
  changes?: { path: string; label: string; old: string; new: string }[]; citations?: string[]; warning?: boolean
}
type LastRun = { tokens: number; models: string[]; modeLabel: string; patches: number; skipped: number }

type State = {
  messages: Msg[]; running: boolean; steps: Step[]; waitNote: string; modeLabel: string; lastRun: LastRun | null
  samples: { name: string; label: string }[]
}

const mid = () => Math.random().toString(36).slice(2, 10)

const slice = createSlice({
  name: 'copilot',
  initialState: { messages: [], running: false, steps: [], waitNote: '', modeLabel: '', lastRun: null, samples: [] } as State,
  reducers: {
    resetCopilot: (s) => { s.messages = []; s.running = false; s.steps = []; s.waitNote = ''; s.lastRun = null },
    setMessages(s, a: PayloadAction<Msg[]>) { s.messages = a.payload },
    addMessage(s, a: PayloadAction<Omit<Msg, 'id'>>) { s.messages.push({ id: mid(), ...a.payload }) },
    setSamples(s, a: PayloadAction<State['samples']>) { s.samples = a.payload },
    startRun(s) { s.running = true; s.steps = []; s.waitNote = ''; s.modeLabel = '' },
    runStarted(s, a: PayloadAction<string>) { s.modeLabel = a.payload },
    stepEvent(s, a: PayloadAction<Json>) {
      const e = a.payload as Step
      const i = s.steps.findIndex((x) => x.node === e.node)
      if (i >= 0) s.steps[i] = { ...s.steps[i], ...e }
      else s.steps.push(e)
      s.waitNote = ''
    },
    waitEvent(s, a: PayloadAction<number>) { s.waitNote = `Waiting ${a.payload}s for the Groq rate-limit window…` },
    finishRun(s, a: PayloadAction<LastRun>) { s.running = false; s.waitNote = ''; s.lastRun = a.payload },
    failRun(s, a: PayloadAction<string>) {
      s.running = false; s.waitNote = ''
      s.messages.push({ id: mid(), role: 'system', text: a.payload, warning: true })
    },
  },
})

export const { resetCopilot, setMessages, addMessage, setSamples, startRun, runStarted, stepEvent, waitEvent, finishRun, failRun } = slice.actions
export default slice.reducer
