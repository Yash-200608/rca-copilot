import { Collapse, Tag, Tooltip } from 'antd'
import { useAppSelector } from '../../../app/hooks'
import type { Json } from '../../../lib/paths'
import { DISPOSITION_COLOR, DISPOSITION_LABEL, EVIDENCE_AREAS, SIX_M, SIX_M_LABEL } from '../formMeta'
import ItemTable from './ItemTable'

const COLOR: Record<string, string> = { supported: '#cf1322', possible: '#d46b08', needs_evidence: '#d4b106', unlikely: '#8c8c8c', ruled_out: '#bfbfbf' }
const TOP = ['man', 'method', 'material']
const BOTTOM = ['machine', 'measurement', 'environment']

function short(t: string, n = 70) { return t.length > n ? t.slice(0, n - 1) + '…' : t }

function Bone({ cat, causes, top }: { cat: string; causes: Json[]; top: boolean }) {
  return (
    <div className={`fb-cat ${top ? 'top' : 'bottom'}`}>
      <div className="fb-title">{SIX_M_LABEL[cat]}</div>
      {causes.length === 0 && <div className="fb-empty">no causes yet</div>}
      {causes.slice(0, 4).map((c) => (
        <Tooltip key={c.id} title={<div><b>{DISPOSITION_LABEL[c.disposition]}</b> · {c.evidence_area}<div>{c.rationale}</div>{c.evidence_quote && <div style={{ marginTop: 4 }}>“{c.evidence_quote}”</div>}</div>}>
          <div className="fb-cause"><span className="dot" style={{ background: COLOR[c.disposition] ?? '#999' }} />{short(c.cause)}</div>
        </Tooltip>
      ))}
    </div>
  )
}

export default function Fishbone() {
  const fb = useAppSelector((s) => s.investigation.form?.fishbone) ?? {}
  const problem = useAppSelector((s) => s.investigation.form?.header?.title) || 'Problem'
  const extracted = useAppSelector((s) => !!s.investigation.form?.meta?.extracted)
  const any = SIX_M.some((m) => (fb[m] ?? []).length)
  if (!any) return <div style={{ color: '#8c8c8c' }}>{extracted ? 'Run the analysis to build the fishbone.' : 'Awaiting AI analysis…'}</div>
  return (
    <div>
      <div className="fishbone">
        <div className="fb-row">{TOP.map((c) => <Bone key={c} cat={c} causes={fb[c] ?? []} top />)}</div>
        <div className="fb-spine"><div className="fb-line" /><div className="fb-head">{short(problem, 90)}</div></div>
        <div className="fb-row">{BOTTOM.map((c) => <Bone key={c} cat={c} causes={fb[c] ?? []} top={false} />)}</div>
      </div>
      <div className="fb-legend">
        {Object.keys(COLOR).map((k) => <span key={k}><span className="dot" style={{ background: COLOR[k] }} /> {DISPOSITION_LABEL[k]}</span>)}
        <span style={{ marginLeft: 'auto' }}>Candidate causes — dispositions are AI judgements from the document only.</span>
      </div>
      <Collapse size="small" style={{ marginTop: 8 }} items={[{
        key: 'edit', label: 'Review / edit fishbone causes',
        children: SIX_M.map((m) => (
          <div key={m} style={{ marginBottom: 10 }}>
            <b>{SIX_M_LABEL[m]}</b>
            <ItemTable listPath={`fishbone.${m}`} idPrefix="fb" addLabel="Add cause" blank={{ cause: '', evidence_area: 'Process', disposition: 'possible', rationale: '' }}
              columns={[
                { field: 'cause', title: 'Candidate cause', kind: 'area' },
                { field: 'evidence_area', title: 'Evidence area', width: 130, kind: 'select', options: EVIDENCE_AREAS },
                { field: 'disposition', title: 'Disposition', width: 150, kind: 'select', options: Object.keys(DISPOSITION_LABEL) },
                { field: 'rationale', title: 'Why', kind: 'area' },
              ]} />
          </div>
        )),
      }]} />
      <div style={{ marginTop: 6 }}><Tag color={DISPOSITION_COLOR.supported}>supported</Tag> means the document states it; it does not mean it is the root cause.</div>
    </div>
  )
}
