import { CheckCircleFilled, CloseCircleFilled, ExclamationCircleFilled } from '@ant-design/icons'
import { Alert, Button, Input, List, Tag, message } from 'antd'
import { useState } from 'react'
import { useAppDispatch, useAppSelector } from '../../../app/hooks'
import { approveInvestigation, fetchGates, saveInvestigation, submitInvestigation } from '../investigationSlice'

export default function Readiness() {
  const dispatch = useAppDispatch()
  const gates = useAppSelector((s) => s.investigation.gates)
  const status = useAppSelector((s) => s.investigation.status)
  const role = useAppSelector((s) => s.session.role)
  const [note, setNote] = useState('')

  const refresh = async () => { await dispatch(saveInvestigation(undefined)); await dispatch(fetchGates()) }
  const submit = async () => {
    const r = await dispatch(submitInvestigation())
    if (submitInvestigation.rejected.match(r)) message.warning('Blocking checks are still open — see the list.')
    else message.success('Submitted for QA review')
  }
  const approve = async () => {
    const r = await dispatch(approveInvestigation(note))
    if (approveInvestigation.rejected.match(r)) message.error(r.error.message ?? 'Could not approve')
    else message.success('Approved (prototype — not a legally valid e-signature)')
  }

  return (
    <div>
      <Alert type="info" showIcon style={{ marginBottom: 10 }}
        message="Prototype checks, not a compliance claim"
        description="These checks mirror what QA reviewers look for in an investigation. AI-proposed root causes and CAPA stay suggestions until a qualified person has reviewed them." />
      <div style={{ marginBottom: 8 }}>
        <Button size="small" onClick={refresh}>Re-check readiness</Button>
        {gates && <span style={{ marginLeft: 10 }}>{gates.blocking_open === 0 ? <Tag color="green">no blocking items</Tag> : <Tag color="red">{gates.blocking_open} blocking</Tag>}<Tag color="orange">{gates.warnings_open} warnings</Tag></span>}
      </div>
      {!gates ? <div style={{ color: '#8c8c8c' }}>Run the checks after the AI analysis.</div> : (
        <List size="small" bordered dataSource={[...gates.gates].sort((a, b) => Number(a.passed) - Number(b.passed))}
          renderItem={(g) => (
            <List.Item>
              <span style={{ marginRight: 8 }}>{g.passed ? <CheckCircleFilled style={{ color: '#52c41a' }} /> : g.level === 'blocking' ? <CloseCircleFilled style={{ color: '#ff4d4f' }} /> : <ExclamationCircleFilled style={{ color: '#fa8c16' }} />}</span>
              <div style={{ flex: 1 }}>{g.label}{g.detail && !g.passed && <div style={{ color: '#8c8c8c', fontSize: 12 }}>{g.detail}</div>}</div>
              <Tag color={g.level === 'blocking' ? 'red' : 'orange'}>{g.level}</Tag>
            </List.Item>
          )} />
      )}
      <div style={{ marginTop: 12 }}>
        {status === 'draft' && <Button type="primary" disabled={!gates?.ready} onClick={submit}>Submit for QA review</Button>}
        {status === 'in_review' && role === 'qa' && (
          <div>
            <Input.TextArea rows={2} placeholder="Approval note" value={note} onChange={(e) => setNote(e.target.value)} />
            <Button type="primary" style={{ marginTop: 6 }} onClick={approve}>QA: approve investigation</Button>
          </div>
        )}
        {status === 'in_review' && role !== 'qa' && <Alert type="info" showIcon message="Waiting for QA review. Switch the demo role to QA Head to approve." />}
        {status === 'approved' && <Alert type="success" showIcon message="Approved — the record is now read-only." />}
      </div>
    </div>
  )
}
