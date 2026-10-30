import { configureStore } from '@reduxjs/toolkit'
import copilot from '../features/copilot/copilotSlice'
import investigation from '../features/investigation/investigationSlice'
import list from '../features/list/listSlice'
import session from '../features/session/sessionSlice'

export const store = configureStore({ reducer: { session, list, investigation, copilot } })
export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
