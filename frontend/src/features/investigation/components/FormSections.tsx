import { Alert, Card, Col, Input, Row, Tag } from 'antd'
import { useEffect } from 'react'
import { useAppDispatch, useAppSelector } from '../../../app/hooks'
import type { Json } from '../../../lib/paths'
import { CLASSES, DETECTION, EVENT_TYPES, SECTIONS, SHIFTS } from '../formMeta'
import { editField } from '../investigationSlice'
import AiField from './AiField'
import Capa from './Capa'
import Fishbone from './Fishbone'
import FiveWhys from './FiveWhys'
import Gaps from './Gaps'
import ItemTable from './ItemTable'
import Readiness from './Readiness'
import RootCauses from './RootCauses'
import SectionCard from './SectionCard'

const T = (id: string) => SECTIONS.find((s) => s.id === id)!.title

function Recurrence() {
  const rec = useAppSelector((s) => s.investigation.form?.classification?.recurrence)
  if (!rec?.checked) return <div style={{ color: '#8c8c8c', marginTop: 8 }}>Recurrence check runs with the analysis.</div>
  if (!rec.matches.length) return <Alert style={{ marginTop: 8 }} type="success" showIcon message="No similar closed investigation found in the history." />
  return (
    <div style={{ marginTop: 8 }}>
      {rec.matches.map((m: Json) => (
        <Alert key={m.rca_number} type="warning" showIcon style={{ marginBottom: 6 }}
          message={<span><b>{m.rca_number}</b> — {m.title} {m.shared_equipment && <Tag color="orange">same equipment</Tag>}</span>}
          description={<div>Earlier root cause: {m.root_cause || 'n/a'}<br />Earlier CAPA: {m.capa_summary || 'n/a'}<br />
            {m.capa_outcome ? <b style={{ color: '#cf1322' }}>Outcome: {m.capa_outcome}</b> : <i>No effectiveness outcome recorded.</i>}</div>} />
      ))}
      <div style={{ color: '#8c8c8c', fontSize: 12 }}>A repeat event suggests the earlier CAPA or root cause was inadequate — the suggested class was escalated and the new CAPA must explain why it will work this time.</div>
    </div>
  )
}

function Rpn() {
  const c = useAppSelector((s) => s.investigation.form?.classification)
  const dispatch = useAppDispatch()
  const calc = c?.severity && c?.occurrence && c?.detectability ? c.severity * c.occurrence * c.detectability : null
  const current = c?.rpn ?? null
  useEffect(() => {
    if (calc !== current && (calc !== null || current !== null)) dispatch(editField({ path: 'classification.rpn', value: calc }))
  }, [calc, current, dispatch])
  return <AiField path="classification.rpn" label="RPN (S x O x D)" kind="number" hint="computed" />
}

function Narrative() {
  const t = useAppSelector((s) => s.investigation.form?.problem?.originator_narrative)
  return <Input.TextArea rows={5} readOnly value={t ?? ''} placeholder="The original document text appears here (read-only) for traceability." />
}

export default function FormSections() {
  return (
    <div className="sections">
      <SectionCard id="sec-header" title={T('sec-header')} prefixes={['header']}>
        <Row gutter={12}>
          <Col span={12}><AiField path="header.deviation_ref" label="Deviation / incident reference" /></Col>
          <Col span={12}><AiField path="header.investigation_lead" label="Investigation lead" /></Col>
          <Col span={24}><AiField path="header.title" label="Title (factual, no cause)" /></Col>
          <Col span={24}><AiField path="header.related_records" label="Related records (OOS, A.R., work orders…)" kind="tags" /></Col>
        </Row>
      </SectionCard>

      <SectionCard id="sec-incident" title={T('sec-incident')} prefixes={['incident']}>
        <Row gutter={12}>
          <Col span={12}><AiField path="incident.site" label="Site" /></Col>
          <Col span={12}><AiField path="incident.area" label="Area / block" /></Col>
          <Col span={12}><AiField path="incident.department" label="Department" /></Col>
          <Col span={12}><AiField path="incident.product_name" label="Product" /></Col>
          <Col span={12}><AiField path="incident.batch_numbers" label="Batch number(s)" kind="tags" /></Col>
          <Col span={12}><AiField path="incident.batch_size" label="Batch size" /></Col>
          <Col span={12}><AiField path="incident.process_stage" label="Process stage / unit operation" /></Col>
          <Col span={12}><AiField path="incident.step_reference" label="Controlling document & step" /></Col>
          <Col span={12}><AiField path="incident.equipment_ids" label="Equipment tags" kind="tags" /></Col>
          <Col span={12}><AiField path="incident.instrument_ids" label="Instrument IDs" kind="tags" /></Col>
          <Col span={8}><AiField path="incident.occurrence_datetime" label="Occurred" hint="as written" /></Col>
          <Col span={8}><AiField path="incident.occurrence_end_datetime" label="Ended" /></Col>
          <Col span={8}><AiField path="incident.detection_datetime" label="Detected" /></Col>
          <Col span={8}><AiField path="incident.reported_to_qa_datetime" label="QA notified" /></Col>
          <Col span={8}><AiField path="incident.detection_method" label="Detection method" kind="select" options={DETECTION} /></Col>
          <Col span={8}><AiField path="incident.shift" label="Shift" kind="select" options={SHIFTS} /></Col>
          <Col span={12}><AiField path="incident.reported_by" label="Reported by" /></Col>
          <Col span={12}><AiField path="incident.persons_involved" label="Persons involved" kind="tags" /></Col>
        </Row>
      </SectionCard>

      <SectionCard id="sec-class" title={T('sec-class')} prefixes={['classification']}>
        <Row gutter={12}>
          <Col span={12}><AiField path="classification.event_type" label="Event type" kind="select" options={EVENT_TYPES} /></Col>
          <Col span={12}><AiField path="classification.suggested_class" label="Suggested class (QA decides)" kind="select" options={CLASSES} /></Col>
          <Col span={24}><AiField path="classification.class_rationale" label="Classification rationale" kind="area" /></Col>
          <Col span={6}><AiField path="classification.severity" label="Severity 1-5" kind="number" /></Col>
          <Col span={6}><AiField path="classification.occurrence" label="Occurrence 1-5" kind="number" /></Col>
          <Col span={6}><AiField path="classification.detectability" label="Detectability 1-5" kind="number" hint="5 = hard to detect" /></Col>
          <Col span={6}><Rpn /></Col>
        </Row>
        <Recurrence />
      </SectionCard>

      <SectionCard id="sec-problem" title={T('sec-problem')} prefixes={['problem']}>
        <AiField path="problem.problem_statement" label="Problem statement (cause-free: what, where, when, how much, vs which requirement)" kind="area" rows={3} />
        <div style={{ margin: '6px 0 4px', fontWeight: 500 }}>Requirement vs actual</div>
        <ItemTable listPath="problem.requirements" idPrefix="req" addLabel="Add row" blank={{ parameter: '', requirement: '', actual: '', status: 'unknown' }}
          columns={[
            { field: 'parameter', title: 'Parameter', kind: 'area' },
            { field: 'requirement', title: 'Requirement / limit', width: 150, kind: 'area' },
            { field: 'actual', title: 'Actual', width: 150, kind: 'area' },
            { field: 'status', title: 'Result', width: 90, render: (it) => <Tag color={it.status === 'outside' ? 'red' : it.status === 'within' ? 'green' : 'default'}>{it.status === 'outside' ? 'OUTSIDE' : it.status === 'within' ? 'within' : 'check'}</Tag> },
          ]} />
        <div style={{ margin: '10px 0 4px', fontWeight: 500 }}>Originator narrative (verbatim, read-only)</div>
        <Narrative />
      </SectionCard>

      <SectionCard id="sec-contain" title={T('sec-contain')} prefixes={['containment']}>
        <Row gutter={12}>
          <Col span={12}><AiField path="containment.batch_status" label="Batch status after containment" /></Col>
          <Col span={12}><AiField path="containment.containment_scope" label="Other batches / equipment blocked (or why none)" /></Col>
        </Row>
        <ItemTable listPath="containment.immediate_actions" idPrefix="act" addLabel="Add action" blank={{ action: '', performed_by: '', when: '', outcome: '' }}
          columns={[
            { field: 'action', title: 'Action', kind: 'area' }, { field: 'performed_by', title: 'By', width: 120 },
            { field: 'when', title: 'When', width: 120 }, { field: 'outcome', title: 'Outcome', width: 120 },
          ]} />
      </SectionCard>

      <SectionCard id="sec-timeline" title={T('sec-timeline')} prefixes={['timeline']}>
        <ItemTable listPath="timeline" idPrefix="evt" addLabel="Add event" blank={{ when: '', event: '', source: '' }}
          columns={[{ field: 'when', title: 'When (as written)', width: 170 }, { field: 'event', title: 'Event', kind: 'area' }, { field: 'source', title: 'Source', width: 130 }]} />
      </SectionCard>

      <SectionCard id="sec-fishbone" title={T('sec-fishbone')} prefixes={['fishbone']}><Fishbone /></SectionCard>
      <SectionCard id="sec-whys" title={T('sec-whys')} prefixes={['five_whys']}><FiveWhys /></SectionCard>
      <SectionCard id="sec-rc" title={T('sec-rc')} prefixes={['root_causes', 'contributing_factors']}><RootCauses /></SectionCard>
      <SectionCard id="sec-gaps" title={T('sec-gaps')} prefixes={['evidence_gaps']}><Gaps /></SectionCard>

      <SectionCard id="sec-impact" title={T('sec-impact')} prefixes={['impact']}>
        <Row gutter={12}>
          <Col span={12}><AiField path="impact.product_quality" label="Product quality impact" kind="area" rows={3} /></Col>
          <Col span={12}><AiField path="impact.patient_safety" label="Patient safety" kind="area" rows={3} /></Col>
          <Col span={24}><AiField path="impact.cqas_affected" label="CQAs affected" kind="tags" /></Col>
          <Col span={12}><AiField path="impact.validation_regulatory" label="Validation / regulatory filing impact" kind="area" rows={3} /></Col>
          <Col span={12}><AiField path="impact.suggested_disposition" label="Suggested disposition (recommendation — QA decides)" kind="area" rows={3} /></Col>
        </Row>
        <div style={{ margin: '4px 0' }}><b>Other batches / products to assess</b></div>
        <ItemTable listPath="impact.other_batches" idPrefix="ob" addLabel="Add batch" blank={{ batch: '', link: '', rationale: '' }}
          columns={[{ field: 'batch', title: 'Batch / scope', kind: 'area' }, { field: 'link', title: 'Link', width: 200, kind: 'area' }, { field: 'rationale', title: 'Rationale', kind: 'area' }]} />
        <AiField path="impact.other_batches_note" label="If none can be named: what must be checked / why not applicable" />
      </SectionCard>

      <SectionCard id="sec-capa" title={T('sec-capa')} prefixes={['capa']}><Capa /></SectionCard>

      <SectionCard id="sec-summary" title={T('sec-summary')} prefixes={['summary']}>
        <AiField path="summary.executive_summary" label="Executive summary (AI draft — edit before saving)" kind="area" rows={4} />
        <Card size="small" title="Readiness checklist" style={{ marginTop: 10 }}><Readiness /></Card>
      </SectionCard>
    </div>
  )
}
