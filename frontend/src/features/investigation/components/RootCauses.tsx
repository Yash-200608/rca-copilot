import { CheckCircleFilled, CheckOutlined, CloseCircleFilled, DeleteOutlined, PlusOutlined, SafetyCertificateOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Input, Modal, Select, Tag, message } from 'antd'
import { useState } from 'react'
import { useAppDispatch, useAppSelector } from '../../../app/hooks'
import type { Json } from '../../../lib/paths'
import { EVIDENCE_AREAS, SIX_M, SIX_M_LABEL } from '../formMeta'
import { addItem, confirmRootCause, editField, markReviewed, removeItem } from '../investigationSlice'
import { rowClass, SourceTag } from './ItemTable'

const CERT: Record<string, { text: string; color: string }> = {
  possible: { text: 'Possible — hypothesis', color: 'orange' },
  most_probable: { text: 'Most probable — hypothesis', color: 'gold' },
  confirmed: { text: 'Confirmed by QA', color: 'green' },
}

function Block({ title, tone, children }: { title: string; tone?: 'warn'; children: React.ReactNode }) {
  return <div className={`rc-block ${tone ?? ''}`}><div className="rc-block-title">{title}</div>{children}</div>
}

function TagEdit({ path, value, disabled, placeholder }: { path: string; value: string[]; disabled: boolean; placeholder: string }) {
  const dispatch = useAppDispatch()
  return <Select mode="tags" style={{ width: '100%' }} value={value} disabled={disabled} placeholder={placeholder} open={false} suffixIcon={null}
    onChange={(v) => dispatch(editField({ path, value: v }))} />
}

function Card1({ item, kind }: { item: Json; kind: 'root_causes' | 'contributing_factors' }) {
  const dispatch = useAppDispatch()
  const role = useAppSelector((s) => s.session.role)
  const status = useAppSelector((s) => s.investigation.status)
  const locked = status === 'approved' || status === 'closed'
  const [open, setOpen] = useState(false)
  const [note, setNote] = useState('')
  const base = `${kind}.${item.id}`
  const missing = ['supporting_evidence', 'contradicting_evidence', 'assumptions', 'missing_evidence'].filter((k) => !item[k]?.length).concat(item.verification_test ? [] : ['verification_test'])
  const isRc = kind === 'root_causes'
  const cert = CERT[item.certainty] ?? CERT.possible

  const confirm = async () => {
    const r = await dispatch(confirmRootCause({ rcid: item.id, note }))
    if (confirmRootCause.rejected.match(r)) message.error(r.error.message ?? 'Could not confirm')
    else { message.success('Confirmed (prototype review confirmation, recorded in the audit trail)'); setOpen(false); setNote('') }
  }

  return (
    <Card size="small" className={`rc-card ${rowClass(item)}`} style={{ marginBottom: 10 }}
      title={<span><SourceTag item={item} /> <Tag color={cert.color}>{isRc ? cert.text : 'Contributing factor'}</Tag>
        <Tag>{SIX_M_LABEL[item.category_6m] ?? item.category_6m}</Tag><Tag>{item.evidence_area}</Tag>
        <Tag color={item.confidence === 'high' ? 'green' : item.confidence === 'low' ? 'red' : 'default'}>confidence: {item.confidence}</Tag></span>}
      extra={!locked && <span>
        {item.meta?.by === 'ai' && !item.meta.reviewed && <Button size="small" icon={<CheckOutlined />} onClick={() => dispatch(markReviewed(base))}>Mark reviewed</Button>}
        {isRc && role === 'qa' && item.certainty !== 'confirmed' && <Button size="small" type="primary" style={{ marginLeft: 6 }} icon={<SafetyCertificateOutlined />} onClick={() => setOpen(true)}>QA: confirm root cause</Button>}
        <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => dispatch(removeItem({ listPath: kind, id: item.id }))} />
      </span>}>
      <Input.TextArea autoSize={{ minRows: 2, maxRows: 6 }} value={item.statement} disabled={locked} style={{ fontWeight: 500 }}
        onChange={(e) => dispatch(editField({ path: `${base}.statement`, value: e.target.value }))} />
      {item.certainty !== 'confirmed' && isRc && <div className="rc-note">AI hypothesis — not a conclusion. A quote that exists in the document shows the model read it; it does not prove this cause. Only a qualified QA person can confirm it.</div>}
      {item.certainty === 'confirmed' && <div className="rc-note ok">Confirmed by {item.meta?.confirmed_by}: “{item.meta?.confirm_note}” <i>(prototype confirmation, not a legally valid e-signature)</i></div>}
      {missing.length > 0 && <Alert type="error" showIcon style={{ margin: '8px 0' }} message={`Evidence blocks incomplete: ${missing.join(', ').replace(/_/g, ' ')} — add them before this can pass review.`} />}
      <div className="rc-grid">
        <Block title="Supporting evidence (quoted)">
          {(item.supporting_evidence ?? []).map((e: Json, i: number) => (
            <div key={i} className="ev">{e.found ? <CheckCircleFilled style={{ color: '#52c41a' }} /> : <CloseCircleFilled style={{ color: '#fa8c16' }} />} <span className="quote">“{e.quote}”</span> <span className="src">{e.found ? e.source : 'not found in the document'}</span></div>
          ))}
          {!(item.supporting_evidence ?? []).length && <span className="empty">none</span>}
        </Block>
        <Block title="Contradicting evidence"><TagEdit path={`${base}.contradicting_evidence`} value={item.contradicting_evidence ?? []} disabled={locked} placeholder="add (or 'None found in the provided sources')" /></Block>
        <Block title="Assumptions (not stated in the source)" tone="warn"><TagEdit path={`${base}.assumptions`} value={item.assumptions ?? []} disabled={locked} placeholder="add assumption" /></Block>
        <Block title="Missing evidence needed"><TagEdit path={`${base}.missing_evidence`} value={item.missing_evidence ?? []} disabled={locked} placeholder="add missing record" /></Block>
      </div>
      <Block title="Verification test — what would confirm or refute it"><Input.TextArea autoSize={{ minRows: 1, maxRows: 5 }} value={item.verification_test} disabled={locked}
        onChange={(e) => dispatch(editField({ path: `${base}.verification_test`, value: e.target.value }))} /></Block>
      {item.human_error_flag && (
        <Block title="Human-error gate: why were process/system causes not sufficient?" tone="warn">
          <Input.TextArea autoSize={{ minRows: 1, maxRows: 4 }} value={item.human_error_justification} disabled={locked} placeholder="required"
            onChange={(e) => dispatch(editField({ path: `${base}.human_error_justification`, value: e.target.value }))} />
        </Block>
      )}
      <Modal open={open} title="Confirm as root cause (QA)" okText="Confirm" onOk={confirm} onCancel={() => setOpen(false)} okButtonProps={{ disabled: note.trim().length < 15 }}>
        <p>You are confirming this as an established root cause. State the evidence you reviewed (min. 15 characters). This is recorded in the audit trail.</p>
        <Input.TextArea rows={3} value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g. DCS trend and positioner bench test confirm stiction; interlock was bypassed per register." />
        <Alert style={{ marginTop: 8 }} type="info" showIcon message="Prototype: this is a review confirmation, not a legally valid electronic signature." />
      </Modal>
    </Card>
  )
}

export default function RootCauses() {
  const dispatch = useAppDispatch()
  const rcs: Json[] = useAppSelector((s) => s.investigation.form?.root_causes) ?? []
  const cfs: Json[] = useAppSelector((s) => s.investigation.form?.contributing_factors) ?? []
  const extracted = useAppSelector((s) => !!s.investigation.form?.meta?.extracted)
  const locked = useAppSelector((s) => s.investigation.status === 'approved')
  const blank = { statement: '', category_6m: SIX_M[1], evidence_area: EVIDENCE_AREAS[0], subcategory: 'other', certainty: 'possible', confidence: 'low', supporting_evidence: [], contradicting_evidence: [], assumptions: [], missing_evidence: [], verification_test: '', human_error_flag: false, human_error_justification: '' }
  if (!rcs.length && !cfs.length) return <div style={{ color: '#8c8c8c' }}>{extracted ? 'No root-cause hypotheses yet — run the analysis.' : 'Awaiting AI analysis…'}</div>
  return (
    <div>
      <h4 className="sub">Most probable root cause(s)</h4>
      {rcs.map((r) => <Card1 key={r.id} item={r} kind="root_causes" />)}
      {!locked && <Button size="small" type="dashed" icon={<PlusOutlined />} onClick={() => dispatch(addItem({ listPath: 'root_causes', item: blank, prefix: 'rc' }))}>Add root cause manually</Button>}
      <h4 className="sub" style={{ marginTop: 16 }}>Contributing factors</h4>
      {cfs.map((r) => <Card1 key={r.id} item={r} kind="contributing_factors" />)}
    </div>
  )
}
