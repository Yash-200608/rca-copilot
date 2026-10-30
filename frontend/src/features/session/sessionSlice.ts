import { createSlice, type PayloadAction } from '@reduxjs/toolkit'
import { loadIdentity, saveIdentity, type Identity } from '../../lib/api'

// DEMO ONLY: a role switch, not authentication.
const slice = createSlice({
  name: 'session',
  initialState: loadIdentity(),
  reducers: {
    setRole(state, a: PayloadAction<Identity['role']>) {
      state.role = a.payload
      state.user = a.payload === 'qa' ? 'S. Iyer (QA Head)' : 'A. Mehta (Investigator)'
      saveIdentity({ user: state.user, role: state.role })
    },
  },
})
export const { setRole } = slice.actions
export default slice.reducer
