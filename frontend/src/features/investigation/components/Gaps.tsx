import { Tag } from 'antd'
import { useAppSelector } from '../../../app/hooks'
import type { Json } from '../../../lib/paths'
import { EVIDENCE_AREAS } from '../formMeta'
import ItemTable from './ItemTable'

export default function Gaps() {
  const gaps: Json[] = useAppSelector((s) => s.investigation.form?.evidence_gaps) ?? []
  const high = gaps.filter((g) => g.priority === 'high' && g.status !== 'received' && g.status !== 'n/a').length
  const byArea = EVIDENCE_AREAS.map((a) => [a, gaps.filter((g) => g.evidence_area === a).length] as const).filter(([, n]) => n)
  return (
    <div>
      {gaps.length > 0 && (
        <div style={{ marginBottom: 8 }}>
          <Tag color="red">{high} high-priority open</Tag>
          {byArea.map(([a, n]) => <Tag key={a}>{a}: {n}</Tag>)}
        </div>
      )}
      <ItemTable listPath="evidence_gaps" idPrefix="gap" addLabel="Add evidence request" empty="No gaps identified yet"
        blank={{ item: '', evidence_area: 'Equipment', why_needed: '', linked_to: '', priority: 'medium', suggested_owner: '', status: 'open' }}
        columns={[
          { field: 'item', title: 'Evidence / information needed', kind: 'area' },
          { field: 'evidence_area', title: 'Area', width: 120, kind: 'select', options: EVIDENCE_AREAS },
          { field: 'why_needed', title: 'Why it is needed', kind: 'area' },
          { field: 'priority', title: 'Priority', width: 90, kind: 'select', options: ['high', 'medium', 'low'] },
          { field: 'suggested_owner', title: 'Owner', width: 120 },
          { field: 'status', title: 'Status', width: 110, kind: 'select', options: ['open', 'requested', 'received', 'n/a'] },
        ]} />
    </div>
  )
}
