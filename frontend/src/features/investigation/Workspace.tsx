import { ArrowLeftOutlined, AuditOutlined, ExperimentOutlined, SaveOutlined } from '@ant-design/icons'
import { Alert, Button, Segmented, Spin, Switch, Tag, Tooltip } from 'antd'
import { useEffect, useState } from 'react'
import { shallowEqual } from 'react-redux'
import { Link, useParams } from 'react-router'
import { useAppDispatch, useAppSelector } from '../../app/hooks'
import { countAi } from '../../lib/review'
import { resetCopilot, setMessages } from '../copilot/copilotSlice'
import CopilotPanel from '../copilot/CopilotPanel'
import { setRole } from '../session/sessionSlice'
import AuditDrawer from './components/AuditDrawer'
import FormSections from './components/FormSections'
import { SECTIONS, STATUS_COLOR, STATUS_LABEL } from './formMeta'
import { clearError, fetchGates, loadInvestigation, reset, saveInvestigation, setManual } from './investigationSlice'

export default function Workspace() {
  const { id } = useParams()
  const dispatch = useAppDispatch()
  const inv = useAppSelector((s) => s.investigation)
  const role = useAppSelector((s) => s.session.role)
  const running = useAppSelector((s) => s.copilot.running)
  const counts = useAppSelector((s) => countAi(s.investigation.form, s.investigation.prov, ['']), shallowEqual)
  const [audit, setAudit] = useState(false)
  const locked = inv.status === 'approved' || inv.status === 'closed'

  useEffect(() => {
    if (!id) return
    dispatch(reset()); dispatch(resetCopilot())
    dispatch(loadInvestigation(id)).unwrap().then((p) => {
      dispatch(setMessages((p.messages ?? []).map((m: { id: string; role: 'user' | 'assistant'; content: string; attachments: string[] }) => ({ id: m.id, role: m.role, text: m.content || (m.attachments?.length ? 'Attached documents' : ''), attachments: m.attachments }))))
      if (p.form_data?.meta?.extracted) dispatch(fetchGates())
    }).catch(() => {})
  }, [id, dispatch])

  // autosave: a few seconds after the last edit, never while the AI is writing
  useEffect(() => {
    if (!inv.dirty || inv.saving || running || locked) return
    const t = setTimeout(() => { dispatch(saveInvestigation(undefined)) }, 2500)
    return () => clearTimeout(t)
  }, [inv.dirty, inv.saving, running, locked, inv.form, dispatch])

  if (inv.loading || !inv.form) return <div className="center">{inv.error ? <Alert type="error" message={inv.error} /> : <Spin />}</div>
  const title = inv.form.header?.title || '(untitled investigation)'

  return (
    <div className="ws">
      <header className="ws-head">
        <div className="ws-left">
          <Link to="/"><Button type="text" icon={<ArrowLeftOutlined />} /></Link>
          <ExperimentOutlined style={{ color: '#4f46e5', fontSize: 18 }} />
          <div style={{ minWidth: 0 }}>
            <div className="ws-title"><b>{inv.rcaNumber}</b> <Tag color={STATUS_COLOR[inv.status]}>{STATUS_LABEL[inv.status] ?? inv.status}</Tag> <span className="ws-sub">{title}</span></div>
            <div className="ws-meta">
              {counts.ai > 0 && <span><Tag color="blue">AI fields {counts.ai}</Tag><Tag color={counts.unreviewed ? 'orange' : 'green'}>{counts.ai - counts.unreviewed} reviewed · {counts.unreviewed} to review</Tag></span>}
              <span className="saved">{inv.saving ? 'Saving…' : inv.dirty ? 'Unsaved changes' : inv.savedAt ? `Saved ${new Date(inv.savedAt).toLocaleTimeString()}` : 'Saved'}</span>
            </div>
          </div>
        </div>
        <div className="ws-right">
          <Tooltip title="Fields are read-only until the AI has extracted the document (as in the reference workflow). Enable only as a fallback."><span className="manual">Manual entry <Switch size="small" checked={inv.manual} onChange={(v) => dispatch(setManual(v))} disabled={locked} /></span></Tooltip>
          <Tooltip title="Demo only — a role switch, not authentication"><Segmented size="small" value={role} onChange={(v) => dispatch(setRole(v as 'investigator' | 'qa'))} options={[{ label: 'Investigator', value: 'investigator' }, { label: 'QA Head', value: 'qa' }]} /></Tooltip>
          <Button icon={<AuditOutlined />} onClick={() => setAudit(true)}>Audit trail</Button>
          <Button type="primary" icon={<SaveOutlined />} loading={inv.saving} disabled={locked || !inv.dirty} onClick={() => dispatch(saveInvestigation(undefined)).then(() => dispatch(fetchGates()))}>Save</Button>
        </div>
      </header>
      {inv.error && <Alert type="error" showIcon closable banner message={inv.error} onClose={() => dispatch(clearError())} />}
      <div className="ws-body">
        <section className="form-pane">
          <nav className="sec-nav">{SECTIONS.map((s) => <a key={s.id} onClick={() => document.getElementById(s.id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })}>{s.short}</a>)}</nav>
          <FormSections />
          <footer className="disclaimer">RCA Copilot is a GMP-inspired investigation prototype — not a validated GMP / 21 CFR Part 11 system. Role switch is demo-only; confirmations are not legally valid electronic signatures. AI output is a draft for qualified review.</footer>
        </section>
        <aside className="cp-pane"><CopilotPanel /></aside>
      </div>
      <AuditDrawer open={audit} onClose={() => setAudit(false)} />
    </div>
  )
}
