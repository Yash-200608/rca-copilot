import { ExperimentOutlined, PlusOutlined } from '@ant-design/icons'
import { Alert, Button, Table, Tag } from 'antd'
import { useEffect } from 'react'
import { useNavigate } from 'react-router'
import { useAppDispatch, useAppSelector } from '../../app/hooks'
import { STATUS_COLOR, STATUS_LABEL } from '../investigation/formMeta'
import { createInvestigation, fetchList, type Summary } from './listSlice'

export default function ListPage() {
  const dispatch = useAppDispatch()
  const nav = useNavigate()
  const { items, loading, error } = useAppSelector((s) => s.list)
  useEffect(() => { dispatch(fetchList()) }, [dispatch])
  const create = async () => {
    const r = await dispatch(createInvestigation())
    if (createInvestigation.fulfilled.match(r)) nav(`/investigations/${r.payload.id}`)
  }
  return (
    <div className="list-page">
      <div className="list-head">
        <div>
          <h1><ExperimentOutlined style={{ color: '#4f46e5' }} /> RCA Copilot</h1>
          <div style={{ color: '#6b7280' }}>API pharmaceutical quality investigation · incident intake → AI-assisted root cause analysis → CAPA → qualified QA review</div>
        </div>
        <Button type="primary" size="large" icon={<PlusOutlined />} onClick={create}>New investigation</Button>
      </div>
      {error && <Alert type="error" showIcon message={`Could not reach the API: ${error}`} style={{ marginBottom: 12 }} />}
      <Table<Summary> rowKey="id" loading={loading} dataSource={items} pagination={{ pageSize: 12 }} scroll={{ x: 1180 }} onRow={(r) => ({ onClick: () => nav(`/investigations/${r.id}`), style: { cursor: 'pointer' } })}
        columns={[
          { title: 'RCA No.', dataIndex: 'rca_number', width: 130, render: (v) => <b>{v}</b> },
          { title: 'Title', dataIndex: 'title', width: 340 },
          { title: 'Product', dataIndex: 'product', width: 160 },
          { title: 'Batch', dataIndex: 'batch_numbers', width: 140, render: (v: string[]) => v?.join(', ') },
          { title: 'Class', dataIndex: 'classification', width: 90, render: (v) => v && <Tag color={v === 'critical' ? 'red' : v === 'major' ? 'orange' : 'default'}>{v}</Tag> },
          { title: 'Root cause (summary)', dataIndex: 'root_cause_summary', ellipsis: true, width: 260 },
          { title: 'CAPA', dataIndex: 'capa_count', width: 70 },
          { title: 'Status', dataIndex: 'status', width: 120, render: (v) => <Tag color={STATUS_COLOR[v]}>{STATUS_LABEL[v] ?? v}</Tag> },
          { title: 'Updated', dataIndex: 'updated_at', width: 150, render: (v) => v && new Date(v).toLocaleString() },
        ]} />
      <div style={{ color: '#9ca3af', marginTop: 16, fontSize: 12 }}>Prototype: GMP-inspired, not a validated GMP / Part 11 system. The three closed investigations are fictional history used for the recurrence check.</div>
    </div>
  )
}
