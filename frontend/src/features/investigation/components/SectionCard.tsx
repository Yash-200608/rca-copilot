import { CheckCircleOutlined, RobotOutlined } from '@ant-design/icons'
import { Button, Card, Tag } from 'antd'
import type { ReactNode } from 'react'
import { shallowEqual } from 'react-redux'
import { useAppDispatch, useAppSelector } from '../../../app/hooks'
import { countAi } from '../../../lib/review'
import { acceptSection } from '../investigationSlice'

type Props = { id: string; title: string; prefixes?: string[]; extra?: ReactNode; children: ReactNode; subtitle?: string }

export default function SectionCard({ id, title, prefixes = [], extra, children, subtitle }: Props) {
  const dispatch = useAppDispatch()
  const { ai, unreviewed } = useAppSelector((s) => countAi(s.investigation.form, s.investigation.prov, prefixes), shallowEqual)
  const locked = useAppSelector((s) => s.investigation.status === 'approved' || s.investigation.status === 'closed')
  return (
    <Card id={id} className="section-card" size="small"
      title={<span>{title}{subtitle && <span className="sec-sub"> {subtitle}</span>}</span>}
      extra={<span className="sec-extra">
        {extra}
        {ai > 0 && (unreviewed > 0
          ? <><Tag color="blue" icon={<RobotOutlined />}>{unreviewed} AI item{unreviewed > 1 ? 's' : ''} to review</Tag>
              {!locked && <Button size="small" onClick={() => dispatch(acceptSection(prefixes))}>Accept all</Button>}</>
          : <Tag color="green" icon={<CheckCircleOutlined />}>all reviewed</Tag>)}
      </span>}>
      {children}
    </Card>
  )
}
