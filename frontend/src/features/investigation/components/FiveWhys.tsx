import { CheckOutlined, DeleteOutlined } from '@ant-design/icons'
import { Alert, Button, Input, Tag } from 'antd'
import { useAppDispatch, useAppSelector } from '../../../app/hooks'
import type { Json } from '../../../lib/paths'
import { editField, markReviewed, removeItem } from '../investigationSlice'
import { rowClass } from './ItemTable'

export default function FiveWhys() {
  const dispatch = useAppDispatch()
  const whys: Json[] = useAppSelector((s) => s.investigation.form?.five_whys) ?? []
  const stopping = useAppSelector((s) => s.investigation.form?.meta?.whys_stopping)
  const extracted = useAppSelector((s) => !!s.investigation.form?.meta?.extracted)
  const locked = useAppSelector((s) => s.investigation.status === 'approved')
  if (!whys.length) return <div style={{ color: '#8c8c8c' }}>{extracted ? 'Run the analysis to build the 5 Whys chain.' : 'Awaiting AI analysis…'}</div>
  const last = (whys[whys.length - 1]?.answer ?? '').toLowerCase()
  return (
    <div className="whys">
      {whys.map((w, i) => (
        <div key={w.id} className={`why ${rowClass(w)}`}>
          <div className="why-level">{i + 1}</div>
          <div className="why-body">
            <div className="why-q">Why? {w.question}</div>
            <Input.TextArea autoSize={{ minRows: 1, maxRows: 5 }} value={w.answer} disabled={locked}
              onChange={(e) => dispatch(editField({ path: `five_whys.${w.id}.answer`, value: e.target.value }))} />
            <div className="why-meta">
              <Tag color={w.basis === 'evidence' ? 'green' : 'orange'}>{w.basis === 'evidence' ? 'stated in the source' : 'hypothesis — to verify'}</Tag>
              {w.quote && <span className="quote">“{w.quote}”</span>}
              {w.meta?.by === 'ai' && !w.meta.reviewed && !locked && <Button size="small" type="text" icon={<CheckOutlined />} onClick={() => dispatch(markReviewed(`five_whys.${w.id}`))}>Reviewed</Button>}
              {!locked && <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => dispatch(removeItem({ listPath: 'five_whys', id: w.id }))} />}
            </div>
          </div>
        </div>
      ))}
      {stopping && <div className="why-stop"><b>Why stop here?</b> {stopping}</div>}
      {whys.length < 3 && <Alert type="warning" showIcon style={{ marginTop: 8 }} message="A 5 Whys chain needs at least 3 levels." />}
      {['human error', 'operator error', 'retrain'].some((w) => last.includes(w)) && <Alert type="warning" showIcon style={{ marginTop: 8 }} message="The chain ends at 'human error' — keep asking why the system allowed it." />}
    </div>
  )
}
