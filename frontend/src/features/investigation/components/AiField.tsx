import { CheckCircleFilled, CheckOutlined, InfoCircleOutlined, WarningOutlined } from '@ant-design/icons'
import { Button, Input, InputNumber, Popover, Select, Tag } from 'antd'
import { useAppDispatch, useAppSelector } from '../../../app/hooks'
import { getByPath } from '../../../lib/paths'
import { editField, markReviewed } from '../investigationSlice'

type Kind = 'text' | 'area' | 'select' | 'tags' | 'number'
type Props = { path: string; label: string; kind?: Kind; options?: string[]; rows?: number; hint?: string }

type FieldState = 'awaiting' | 'empty' | 'missing' | 'ai-grounded' | 'ai-derived' | 'ai-unverified' | 'reviewed' | 'user'

const BADGE: Record<string, { text: string; color: string }> = {
  'ai-grounded': { text: 'AI · verified in source', color: 'blue' },
  'ai-derived': { text: 'AI · derived — please check', color: 'purple' },
  'ai-unverified': { text: 'AI · not found in source — verify', color: 'orange' },
  missing: { text: 'Not provided in source', color: 'default' },
  reviewed: { text: 'Reviewed', color: 'green' },
  user: { text: 'Edited by you', color: 'default' },
}

export function stateOf(value: unknown, prov: { by?: string; grounded?: string; reviewed?: boolean } | undefined, extracted: boolean, notIn: boolean): FieldState {
  const empty = value == null || value === '' || (Array.isArray(value) && !value.length)
  if (empty) return extracted ? (notIn ? 'missing' : 'empty') : 'awaiting'
  if (prov?.by === 'ai' && !prov.reviewed) return prov.grounded === 'grounded' ? 'ai-grounded' : prov.grounded === 'unverified' ? 'ai-unverified' : 'ai-derived'
  if (prov?.reviewed) return prov.by === 'ai' ? 'reviewed' : 'user'
  return 'user'
}

export function ProvenanceInfo({ prov }: { prov: Record<string, unknown> | undefined }) {
  if (!prov) return <span>No AI provenance (entered by a person).</span>
  return (
    <div style={{ maxWidth: 340, fontSize: 12 }}>
      <div><b>Source:</b> {prov.by === 'ai' ? `AI step “${prov.node}”` : 'person'} {prov.model ? `· ${prov.model}` : ''}</div>
      {prov.quote ? <div style={{ marginTop: 4 }}><b>Quoted from the document:</b><div className="quote">“{String(prov.quote)}”</div></div>
        : <div style={{ marginTop: 4 }}>No verbatim quote — this value was composed by the model from several statements.</div>}
      <div style={{ marginTop: 4 }}><b>Grounding:</b> {String(prov.grounded ?? 'n/a')} · <b>Confidence:</b> {String(prov.confidence ?? 'n/a')}</div>
      <div style={{ marginTop: 4, color: '#8c8c8c' }}>A matching quote shows the model read the document; it does not prove the interpretation is correct.</div>
    </div>
  )
}

export default function AiField({ path, label, kind = 'text', options, rows = 2, hint }: Props) {
  const dispatch = useAppDispatch()
  const value = useAppSelector((s) => getByPath(s.investigation.form, path))
  const prov = useAppSelector((s) => s.investigation.prov[path])
  const extracted = useAppSelector((s) => !!s.investigation.form?.meta?.extracted)
  const notIn = useAppSelector((s) => !!s.investigation.form?.meta?.not_in_source?.includes(path))
  const manual = useAppSelector((s) => s.investigation.manual)
  const flash = useAppSelector((s) => s.investigation.flash[path])
  const locked = useAppSelector((s) => s.investigation.status === 'approved' || s.investigation.status === 'closed')
  const st = stateOf(value, prov, extracted, notIn)
  const disabled = locked || (!extracted && !manual)
  const fresh = flash && Date.now() - flash < 4000
  const onChange = (v: unknown) => dispatch(editField({ path, value: v }))
  const ph = !extracted ? 'Awaiting AI extraction…' : st === 'missing' ? 'Not provided in source' : ''
  const aiState = st.startsWith('ai-')

  return (
    <div className={`aif ${st} ${fresh ? 'fresh' : ''}`} key={flash ?? 0}>
      <div className="aif-label">
        <span>{label}{hint && <span className="aif-hint"> · {hint}</span>}</span>
        <span className="aif-right">
          {BADGE[st] && (
            <Popover content={<ProvenanceInfo prov={prov} />} title="Where this value came from">
              <Tag color={BADGE[st].color} icon={st === 'ai-unverified' ? <WarningOutlined /> : st === 'reviewed' ? <CheckCircleFilled /> : <InfoCircleOutlined />} style={{ marginRight: 0, cursor: 'help' }}>
                {BADGE[st].text}
              </Tag>
            </Popover>
          )}
          {aiState && !locked && <Button size="small" type="text" icon={<CheckOutlined />} title="Mark as reviewed" onClick={() => dispatch(markReviewed(path))} />}
        </span>
      </div>
      {kind === 'area' ? (
        <Input.TextArea rows={rows} value={value ?? ''} disabled={disabled} placeholder={ph} onChange={(e) => onChange(e.target.value)} />
      ) : kind === 'select' ? (
        <Select style={{ width: '100%' }} allowClear showSearch value={value || undefined} disabled={disabled} placeholder={ph} onChange={(v) => onChange(v ?? '')}
          options={(options ?? []).map((o) => ({ value: o, label: o }))} />
      ) : kind === 'tags' ? (
        <Select mode="tags" style={{ width: '100%' }} tokenSeparators={[',']} value={value ?? []} disabled={disabled} placeholder={ph} onChange={(v) => onChange(v)} open={false} suffixIcon={null} />
      ) : kind === 'number' ? (
        <InputNumber style={{ width: '100%' }} min={1} max={5} value={value ?? null} disabled={disabled} placeholder={ph} onChange={(v) => onChange(v)} />
      ) : (
        <Input value={value ?? ''} disabled={disabled} placeholder={ph} onChange={(e) => onChange(e.target.value)} />
      )}
    </div>
  )
}
