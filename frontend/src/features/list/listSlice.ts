import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import { api } from '../../lib/api'

export type Summary = {
  id: string; rca_number: string; title: string; status: string; product: string; batch_numbers: string[]
  classification: string; event_type: string; root_cause_summary: string; capa_count: number; updated_at: string
}

export const fetchList = createAsyncThunk('list/fetch', () => api<Summary[]>('/investigations'))
export const createInvestigation = createAsyncThunk('list/create', () => api<{ id: string }>('/investigations', { method: 'POST' }))

const slice = createSlice({
  name: 'list',
  initialState: { items: [] as Summary[], loading: false, error: '' },
  reducers: {},
  extraReducers: (b) => {
    b.addCase(fetchList.pending, (s) => { s.loading = true })
    b.addCase(fetchList.fulfilled, (s, a) => { s.items = a.payload; s.loading = false; s.error = '' })
    b.addCase(fetchList.rejected, (s, a) => { s.loading = false; s.error = a.error.message ?? 'Failed to load' })
  },
})
export default slice.reducer
