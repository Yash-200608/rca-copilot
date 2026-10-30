import { createAsyncThunk, createSlice, type PayloadAction } from '@reduxjs/toolkit'
import { api, ApiError } from '../../lib/api'
import { getByPath, itemPathOf, newId, setByPath, type Json } from '../../lib/paths'

export type DocInfo = { id: string; filename: string; kind: string; pages: number; chars: number; scanned: boolean; warnings: string[] }
export type Gate = { id: string; label: string; level: 'blocking' | 'warning'; passed: boolean; detail: string }
export type Gates = { gates: Gate[]; blocking_open: number; warnings_open: number; ready: boolean }
export type Patch = { path: string; value: Json; prov?: Json; mode?: string }

type State = {
  id: string | null; rcaNumber: string; status: string; version: number
  form: Json | null; prov: Record<string, Json>; documents: DocInfo[]
  loading: boolean; error: string; dirty: boolean; saving: boolean; savedAt: string | null
  gates: Gates | null; flash: Record<string, number>; manual: boolean; lastRunId: string | null
}

const initial: State = {
  id: null, rcaNumber: '', status: 'draft', version: 1, form: null, prov: {}, documents: [], loading: false, error: '',
  dirty: false, saving: false, savedAt: null, gates: null, flash: {}, manual: false, lastRunId: null,
}

export const loadInvestigation = createAsyncThunk('inv/load', (id: string) => api<Json>(`/investigations/${id}`))

export const saveInvestigation = createAsyncThunk(
  'inv/save',
  async (arg: { aiRunId?: string | null } | undefined, { getState }) => {
    const s = (getState() as { investigation: State }).investigation
    return api<{ version: number; status: string }>(`/investigations/${s.id}`, {
      method: 'PUT', json: { form_data: s.form, provenance: s.prov, version: s.version, ai_run_id: arg?.aiRunId ?? s.lastRunId },
    })
  },
  { condition: (_a, { getState }) => { const s = (getState() as { investigation: State }).investigation; return !!s.id && !s.saving && s.status !== 'approved' } },
)

export const fetchGates = createAsyncThunk('inv/gates', (_: void, { getState }) => {
  const s = (getState() as { investigation: State }).investigation
  return api<Gates>(`/investigations/${s.id}/gates`)
})

export const confirmRootCause = createAsyncThunk('inv/confirm', async (arg: { rcid: string; note: string }, { getState, dispatch }) => {
  const s = (getState() as { investigation: State }).investigation
  await dispatch(saveInvestigation(undefined))
  const r = await api<{ form_data: Json; version: number }>(`/investigations/${s.id}/root-causes/${arg.rcid}/confirm`, { method: 'POST', json: { note: arg.note } })
  await dispatch(fetchGates())
  return r
})

export const submitInvestigation = createAsyncThunk('inv/submit', async (_: void, { getState, dispatch }) => {
  const s = (getState() as { investigation: State }).investigation
  await dispatch(saveInvestigation(undefined))
  const r = await api<{ status: string; version: number }>(`/investigations/${s.id}/submit`, { method: 'POST' })
  await dispatch(fetchGates())
  return r
})

export const approveInvestigation = createAsyncThunk('inv/approve', async (note: string, { getState }) => {
  const s = (getState() as { investigation: State }).investigation
  return api<{ status: string; version: number }>(`/investigations/${s.id}/approve`, { method: 'POST', json: { note } })
})

function markItems(node: Json) {
  if (Array.isArray(node)) node.forEach(markItems)
  else if (node && typeof node === 'object') {
    if (node.meta && typeof node.meta === 'object' && 'by' in node.meta) node.meta.reviewed = true
    Object.values(node).forEach(markItems)
  }
}

const slice = createSlice({
  name: 'investigation',
  initialState: initial,
  reducers: {
    reset: () => initial,
    applyPatch(s, a: PayloadAction<Patch>) {
      if (!s.form) return
      const p = a.payload
      if (!setByPath(s.form, p.path, p.value)) return
      if (p.prov) s.prov[p.path] = p.prov
      s.flash[p.path] = Date.now()
      s.dirty = true
    },
    editField(s, a: PayloadAction<{ path: string; value: Json }>) {
      if (!s.form) return
      const { path, value } = a.payload
      const item = itemPathOf(s.form, path)
      setByPath(s.form, path, value)
      if (item) {
        const it = getByPath(s.form, item)
        it.meta = { ...(it.meta || {}), by: 'user', reviewed: true }
      } else {
        s.prov[path] = { ...(s.prov[path] || {}), by: 'user', reviewed: true, grounded: s.prov[path]?.grounded ?? 'user' }
      }
      s.dirty = true
    },
    markReviewed(s, a: PayloadAction<string>) {
      if (!s.form) return
      const item = getByPath(s.form, a.payload)
      if (item && typeof item === 'object' && item.meta) item.meta.reviewed = true
      else if (s.prov[a.payload]) s.prov[a.payload].reviewed = true
      s.dirty = true
    },
    acceptSection(s, a: PayloadAction<string[]>) {
      if (!s.form) return
      for (const prefix of a.payload) {
        for (const k of Object.keys(s.prov)) if (k === prefix || k.startsWith(prefix + '.')) s.prov[k].reviewed = true
        markItems(getByPath(s.form, prefix))
      }
      s.dirty = true
    },
    addItem(s, a: PayloadAction<{ listPath: string; item: Json; prefix: string }>) {
      if (!s.form) return
      const list = getByPath(s.form, a.payload.listPath)
      if (!Array.isArray(list)) return
      list.push({ id: newId(a.payload.prefix), ...a.payload.item, meta: { by: 'user', reviewed: true } })
      s.dirty = true
    },
    removeItem(s, a: PayloadAction<{ listPath: string; id: string }>) {
      if (!s.form) return
      const list = getByPath(s.form, a.payload.listPath)
      if (!Array.isArray(list)) return
      const i = list.findIndex((x: Json) => x.id === a.payload.id)
      if (i >= 0) list.splice(i, 1)
      s.dirty = true
    },
    addDocument(s, a: PayloadAction<DocInfo>) { s.documents.push(a.payload) },
    removeDocument(s, a: PayloadAction<string>) { s.documents = s.documents.filter((d) => d.id !== a.payload) },
    setLastRun(s, a: PayloadAction<string>) { s.lastRunId = a.payload },
    setManual(s, a: PayloadAction<boolean>) { s.manual = a.payload },
    clearError(s) { s.error = '' },
  },
  extraReducers: (b) => {
    b.addCase(loadInvestigation.pending, (s) => { s.loading = true; s.error = '' })
    b.addCase(loadInvestigation.fulfilled, (s, a) => {
      const p = a.payload
      Object.assign(s, { ...initial, id: p.id, rcaNumber: p.rca_number, status: p.status, version: p.version, form: p.form_data, prov: p.provenance || {}, documents: p.documents })
    })
    b.addCase(loadInvestigation.rejected, (s, a) => { s.loading = false; s.error = a.error.message ?? 'Could not load the investigation' })
    b.addCase(saveInvestigation.pending, (s) => { s.saving = true })
    b.addCase(saveInvestigation.fulfilled, (s, a) => { s.saving = false; s.dirty = false; s.version = a.payload.version; s.savedAt = new Date().toISOString(); s.error = '' })
    b.addCase(saveInvestigation.rejected, (s, a) => {
      s.saving = false
      s.error = a.error.message ?? 'Save failed'
    })
    b.addCase(fetchGates.fulfilled, (s, a) => { s.gates = a.payload })
    b.addCase(confirmRootCause.fulfilled, (s, a) => { s.form = a.payload.form_data; s.version = a.payload.version })
    b.addCase(confirmRootCause.rejected, (s, a) => { s.error = a.error.message ?? 'Could not confirm' })
    b.addCase(submitInvestigation.fulfilled, (s, a) => { s.status = a.payload.status; s.version = a.payload.version })
    b.addCase(submitInvestigation.rejected, (s, a) => { s.error = a.error.message ?? 'Submit blocked' })
    b.addCase(approveInvestigation.fulfilled, (s, a) => { s.status = a.payload.status; s.version = a.payload.version })
    b.addCase(approveInvestigation.rejected, (s, a) => { s.error = a.error.message ?? 'Could not approve' })
  },
})

export const { reset, applyPatch, editField, markReviewed, acceptSection, addItem, removeItem, addDocument, removeDocument, setLastRun, setManual, clearError } = slice.actions
export { ApiError }
export default slice.reducer
