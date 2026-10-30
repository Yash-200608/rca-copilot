import { Drawer, Table, Tag } from 'antd'
import { useEffect, useState } from 'react'
import { useAppSelector } from '../../../app/hooks'
import { api } from '../../../lib/api'

type Row = { id: number; actor: string; role: string; action: string; path: string; old: string | null; new: string | null; reason: string | null; ts: string }
const COLOR: Record<string, string> = { ai_applied: 'blue', user_edit: 'default', confirm: 'green', submit: 'purple', approve: 'green', create: 'default' }

export default function AuditDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const id = useAppSelector((s) => s.investigation.id)
  const version = useAppSelector((s) => s.investigation.version)
  const [rows, setRows] = useState<Row[]>([])
  useEffect(() => { if (open && id) api<Row[]>(`/investigations/${id}/audit`).then(setRows).catch(() => setRows([])) }, [open, id, version])
  return (
    <Drawer open={open} onClose={onClose} size={780} title="Audit trail — who changed what (AI vs human)">
      <p style={{ color: '#8c8c8c' }}>Every save records field-level changes. AI-applied values are attributed to the AI Copilot; edits and confirmations to the demo user. Prototype audit trail, not a validated one.</p>
      <Table size="small" rowKey="id" dataSource={rows} pagination={{ pageSize: 14 }} columns={[
        { title: 'When', dataIndex: 'ts', width: 150, render: (v: string) => new Date(v).toLocaleString() },
        { title: 'Who', dataIndex: 'actor', width: 150 },
        { title: 'Action', dataIndex: 'action', width: 100, render: (v: string) => <Tag color={COLOR[v]}>{v.replace('_', ' ')}</Tag> },
        { title: 'Field', dataIndex: 'path', ellipsis: true },
        { title: 'Change', key: 'chg', render: (_: unknown, r: Row) => r.new || r.old ? <span><s style={{ color: '#bfbfbf' }}>{(r.old ?? '').slice(0, 60)}</s> → {(r.new ?? '').slice(0, 90)}</span> : r.reason },
      ]} />
    </Drawer>
  )
}
