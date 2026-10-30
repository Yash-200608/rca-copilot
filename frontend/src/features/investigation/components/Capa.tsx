import { CheckOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Checkbox, Input, Select, Tag } from 'antd'
import { useAppDispatch, useAppSelector } from '../../../app/hooks'
import type { Json } from '../../../lib/paths'
import { CAPA_COLOR, CAPA_HELP, STRENGTH_LABEL } from '../formMeta'
import { addItem, editField, markReviewed, removeItem } from '../investigationSlice'
import { rowClass, SourceTag } from './ItemTable'

const TYPES = ['correction', 'corrective', 'preventive'] as const
const STATUS_COLOR: Record<string, string> = { proposed: 'default', accepted: 'green', rejected: 'red' }

function CapaCard({ c, causes, locked }: { c: Json; causes: { value: string; label: string }[]; locked: boolean }) {
  const dispatch = useAppDispatch()
  const base = `capa.${c.id}`
  const set = (f: string, v: unknown) => dispatch(editField({ path: `${base}.${f}`, value: v }))
  const eff = c.effectiveness ?? {}
  const needsEff = c.type !== 'correction'
  return (
    <Card size="small" className={`capa-card ${rowClass(c)}`} style={{ marginBottom: 8 }}
      title={<span><SourceTag item={c} /> <Tag color={CAPA_COLOR[c.type]}>{c.type}</Tag>
        <Tag color={c.strength === 'training' ? 'red' : c.strength === 'administrative' ? 'orange' : 'green'}>{STRENGTH_LABEL[c.strength] ?? c.strength}</Tag>
        <Tag color={STATUS_COLOR[c.status] ?? 'default'}>{c.status}</Tag>{c.change_control && <Tag color="cyan">needs change control</Tag>}</span>}
      extra={!locked && <span>
        {c.status !== 'accepted' && <Button size="small" type="primary" ghost icon={<CheckOutlined />} onClick={() => set('status', 'accepted')}>Accept</Button>}
        {c.status !== 'rejected' && <Button size="small" style={{ marginLeft: 4 }} onClick={() => set('status', 'rejected')}>Reject</Button>}
        {c.meta?.by === 'ai' && !c.meta.reviewed && <Button size="small" type="text" icon={<CheckOutlined />} title="Mark as reviewed" onClick={() => dispatch(markReviewed(base))} />}
        <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => dispatch(removeItem({ listPath: 'capa', id: c.id }))} />
      </span>}>
      <Input.TextArea autoSize={{ minRows: 2, maxRows: 6 }} value={c.action} disabled={locked} onChange={(e) => set('action', e.target.value)} style={{ fontWeight: 500 }} />
      <div className="capa-why"><b>Why:</b> <Input.TextArea variant="borderless" autoSize={{ minRows: 1, maxRows: 4 }} value={c.rationale} disabled={locked} onChange={(e) => set('rationale', e.target.value)} /></div>
      <div className="capa-grid">
        <div><label>Addresses</label><Select mode="multiple" style={{ width: '100%' }} size="small" value={c.linked_to ?? []} options={causes} disabled={locked} onChange={(v) => set('linked_to', v)} placeholder={c.type === 'correction' ? 'batch / records' : 'select cause'} /></div>
        <div><label>Owner (name)</label><Input size="small" value={c.owner} disabled={locked} placeholder={c.owner_role ? `role: ${c.owner_role}` : 'assign owner'} onChange={(e) => set('owner', e.target.value)} /></div>
        <div><label>Due date {c.due_days ? `(suggested +${c.due_days} d)` : ''}</label><Input size="small" type="date" value={c.due_date} disabled={locked} onChange={(e) => set('due_date', e.target.value)} /></div>
        <div><label>Control strength</label><Select size="small" style={{ width: '100%' }} value={c.strength} disabled={locked} options={Object.entries(STRENGTH_LABEL).map(([v, l]) => ({ value: v, label: l }))} onChange={(v) => set('strength', v)} /></div>
      </div>
      <div className="eff">
        <b>Effectiveness check{needsEff ? '' : ' (optional for corrections)'}:</b>
        <div className="capa-grid three">
          <Input size="small" placeholder="Measurable criterion" status={needsEff && !eff.criterion ? 'error' : ''} value={eff.criterion} disabled={locked} onChange={(e) => set('effectiveness', { ...eff, criterion: e.target.value })} />
          <Input size="small" placeholder="Method / data source" value={eff.method} disabled={locked} onChange={(e) => set('effectiveness', { ...eff, method: e.target.value })} />
          <Input size="small" placeholder="Window, e.g. next 20 batches" value={eff.window} disabled={locked} onChange={(e) => set('effectiveness', { ...eff, window: e.target.value })} />
        </div>
      </div>
      <Checkbox checked={!!c.change_control} disabled={locked} onChange={(e) => set('change_control', e.target.checked)}>Requires change control (equipment / process / BMR / software)</Checkbox>
    </Card>
  )
}

export default function Capa() {
  const dispatch = useAppDispatch()
  const capas: Json[] = useAppSelector((s) => s.investigation.form?.capa) ?? []
  const rcs: Json[] = useAppSelector((s) => s.investigation.form?.root_causes) ?? []
  const cfs: Json[] = useAppSelector((s) => s.investigation.form?.contributing_factors) ?? []
  const extracted = useAppSelector((s) => !!s.investigation.form?.meta?.extracted)
  const locked = useAppSelector((s) => s.investigation.status === 'approved' || s.investigation.status === 'closed')
  const causes = [...rcs.map((r, i) => ({ value: r.id, label: `RC-${i + 1}: ${String(r.statement).slice(0, 60)}` })), ...cfs.map((r, i) => ({ value: r.id, label: `CF-${i + 1}: ${String(r.statement).slice(0, 60)}` }))]
  if (!capas.length) return <div style={{ color: '#8c8c8c' }}>{extracted ? 'No CAPA yet — ask the Copilot for CAPA recommendations.' : 'Awaiting AI analysis…'}</div>
  const uncovered = rcs.filter((r) => !capas.some((c) => (c.linked_to ?? []).includes(r.id) && c.type === 'corrective'))
  const trainingOnly = rcs.filter((r) => { const l = capas.filter((c) => (c.linked_to ?? []).includes(r.id) && c.type !== 'correction'); return l.length > 0 && l.every((c) => c.strength === 'training') })
  return (
    <div>
      {uncovered.length > 0 && <Alert type="error" showIcon style={{ marginBottom: 8 }} message={`No corrective action yet for: ${uncovered.map((r) => r.statement.slice(0, 50)).join('; ')}`} />}
      {trainingOnly.length > 0 && <Alert type="warning" showIcon style={{ marginBottom: 8 }} message="Retraining alone is not an adequate action. Pair it with an engineering or procedural control." />}
      {TYPES.map((t) => (
        <div key={t}>
          <h4 className="sub"><Tag color={CAPA_COLOR[t]}>{t}</Tag> <span style={{ color: '#8c8c8c', fontWeight: 400 }}>{CAPA_HELP[t]}</span></h4>
          {capas.filter((c) => c.type === t).map((c) => <CapaCard key={c.id} c={c} causes={causes} locked={locked} />)}
          {!capas.some((c) => c.type === t) && <div style={{ color: '#8c8c8c', marginBottom: 8 }}>none</div>}
        </div>
      ))}
      {!locked && <Button size="small" type="dashed" icon={<PlusOutlined />} onClick={() => dispatch(addItem({ listPath: 'capa', prefix: 'capa', item: { type: 'corrective', action: '', rationale: '', linked_to: [], strength: 'engineering', owner_role: '', owner: '', due_days: 30, due_date: '', change_control: false, effectiveness: { criterion: '', method: '', window: '' }, status: 'accepted' } }))}>Add action</Button>}
    </div>
  )
}
