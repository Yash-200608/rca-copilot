import { CheckOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import { Button, Input, Select, Table, Tag, Tooltip } from 'antd'
import type { ReactNode } from 'react'
import { useAppDispatch, useAppSelector } from '../../../app/hooks'
import { getByPath, type Json } from '../../../lib/paths'
import { addItem, editField, markReviewed, removeItem } from '../investigationSlice'

export type Col = {
  field: string; title: string; width?: number | string; kind?: 'text' | 'area' | 'select'; options?: string[]
  render?: (item: Json) => ReactNode
}
type Props = {
  listPath: string; columns: Col[]; idPrefix: string; addLabel?: string; blank?: Json; empty?: string; hideAdd?: boolean
}

export function rowClass(item: Json): string {
  const m = item?.meta
  if (!m) return ''
  if (m.by === 'ai' && !m.reviewed) return m.grounded === 'unverified' ? 'row-ai-unverified' : 'row-ai'
  return m.reviewed ? 'row-reviewed' : ''
}

export function SourceTag({ item }: { item: Json }) {
  const m = item?.meta
  if (!m) return null
  if (m.by === 'ai' && !m.reviewed) {
    const verified = m.grounded === 'grounded'
    return (
      <Tooltip title={m.quote ? `Quoted from the document: “${m.quote}”` : verified ? 'Verified against the source' : 'Composed by AI — check against the documents'}>
        <Tag color={verified ? 'blue' : m.grounded === 'unverified' ? 'orange' : 'purple'}>{verified ? 'AI ✓ source' : m.grounded === 'unverified' ? 'AI · verify' : 'AI'}</Tag>
      </Tooltip>
    )
  }
  return <Tag color={m.reviewed && m.by === 'ai' ? 'green' : 'default'}>{m.reviewed && m.by === 'ai' ? 'reviewed' : 'you'}</Tag>
}

export default function ItemTable({ listPath, columns, idPrefix, addLabel = 'Add row', blank = {}, empty = 'Nothing yet', hideAdd }: Props) {
  const dispatch = useAppDispatch()
  const items: Json[] = useAppSelector((s) => getByPath(s.investigation.form, listPath)) ?? []
  const extracted = useAppSelector((s) => !!s.investigation.form?.meta?.extracted)
  const manual = useAppSelector((s) => s.investigation.manual)
  const locked = useAppSelector((s) => s.investigation.status === 'approved' || s.investigation.status === 'closed')
  const disabled = locked || (!extracted && !manual)

  const cols = [
    { title: '', key: '_src', width: 92, render: (_: unknown, it: Json) => <SourceTag item={it} /> },
    ...columns.map((c) => ({
      title: c.title, key: c.field, width: c.width,
      render: (_: unknown, it: Json) => {
        if (c.render) return c.render(it)
        const path = `${listPath}.${it.id}.${c.field}`
        if (c.kind === 'select')
          return <Select size="small" style={{ width: '100%' }} value={it[c.field] || undefined} disabled={disabled} options={(c.options ?? []).map((o) => ({ value: o, label: o }))} onChange={(v) => dispatch(editField({ path, value: v }))} />
        return <Input.TextArea autoSize={{ minRows: 1, maxRows: 6 }} size="small" value={it[c.field] ?? ''} disabled={disabled} onChange={(e) => dispatch(editField({ path, value: e.target.value }))} />
      },
    })),
    {
      title: '', key: '_act', width: 74,
      render: (_: unknown, it: Json) => !locked && (
        <span style={{ whiteSpace: 'nowrap' }}>
          {it.meta?.by === 'ai' && !it.meta.reviewed && <Button size="small" type="text" icon={<CheckOutlined />} title="Mark as reviewed" onClick={() => dispatch(markReviewed(`${listPath}.${it.id}`))} />}
          <Button size="small" type="text" danger icon={<DeleteOutlined />} title="Remove" onClick={() => dispatch(removeItem({ listPath, id: it.id }))} />
        </span>
      ),
    },
  ]
  return (
    <div>
      <Table size="small" rowKey="id" pagination={false} dataSource={items} columns={cols} rowClassName={rowClass}
        locale={{ emptyText: <span style={{ color: '#8c8c8c' }}>{extracted ? empty : 'Awaiting AI extraction…'}</span> }} />
      {!hideAdd && !locked && (extracted || manual) && (
        <Button size="small" type="dashed" icon={<PlusOutlined />} style={{ marginTop: 8 }} onClick={() => dispatch(addItem({ listPath, item: blank, prefix: idPrefix }))}>{addLabel}</Button>
      )}
    </div>
  )
}
