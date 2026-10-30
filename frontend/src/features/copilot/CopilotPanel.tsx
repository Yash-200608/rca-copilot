import { CheckCircleFilled, CloseCircleFilled, FileTextOutlined, LoadingOutlined, PaperClipOutlined, RobotOutlined, SendOutlined, UserOutlined, WarningFilled } from '@ant-design/icons'
import { Button, Input, Tag, Tooltip } from 'antd'
import { useEffect, useRef, useState } from 'react'
import { useAppDispatch, useAppSelector } from '../../app/hooks'
import { api } from '../../lib/api'
import { loadSample, runCopilot, sendMessage } from './actions'
import { setSamples } from './copilotSlice'

const CHIPS: { label: string; intent: string; msg: string }[] = [
  { label: 'Re-run full analysis', intent: 'analyze', msg: 'Re-run the root cause analysis' },
  { label: 'More CAPA', intent: 'capa', msg: 'Recommend CAPA' },
  { label: 'What evidence is missing?', intent: 'gaps', msg: 'What evidence is missing?' },
  { label: 'Draft summary', intent: 'summarize', msg: 'Summarise the investigation' },
]

function StepIcon({ s }: { s: string }) {
  if (s === 'running') return <LoadingOutlined style={{ color: '#4f46e5' }} />
  if (s === 'error') return <CloseCircleFilled style={{ color: '#ff4d4f' }} />
  return <CheckCircleFilled style={{ color: '#52c41a' }} />
}

export default function CopilotPanel() {
  const dispatch = useAppDispatch()
  const { messages, running, steps, waitNote, modeLabel, lastRun, samples } = useAppSelector((s) => s.copilot)
  const extracted = useAppSelector((s) => !!s.investigation.form?.meta?.extracted)
  const locked = useAppSelector((s) => s.investigation.status === 'approved')
  const [text, setText] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const fileRef = useRef<HTMLInputElement>(null)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => { api<{ name: string; label: string }[]>('/samples').then((s) => dispatch(setSamples(s))).catch(() => {}) }, [dispatch])
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages.length, steps.length])

  const send = () => {
    if (running || locked || (!text.trim() && !files.length)) return
    dispatch(sendMessage({ text, files }))
    setText(''); setFiles([])
  }
  const onDrop = (e: React.DragEvent) => { e.preventDefault(); setFiles((f) => [...f, ...Array.from(e.dataTransfer.files)]) }

  return (
    <div className="copilot" onDragOver={(e) => e.preventDefault()} onDrop={onDrop}>
      <div className="cp-head">
        <div><RobotOutlined /> <b>RCA Copilot</b><div className="cp-sub">Drop an incident report, paste an email or shift log, or ask a question.</div></div>
        <Tag color={running ? 'processing' : 'success'} className="cp-dot">{running ? 'working' : 'ready'}</Tag>
      </div>

      <div className="cp-body">
        <div className="bubble ai">
          <RobotOutlined className="av" />
          <div>
            I can read an <b>incident report (PDF)</b>, an <b>email (.eml)</b> or <b>pasted text</b>, fill the investigation form, run a <b>5 Whys</b> and <b>fishbone</b>,
            propose root-cause <i>hypotheses</i> with evidence for and against, list <b>missing evidence</b>, and recommend <b>CAPA</b>. I only use what the documents say — and
            everything I propose is a suggestion for you to review.
            {!extracted && samples.length > 0 && (
              <div className="samples">
                <div style={{ marginBottom: 4, color: '#8c8c8c' }}>Try a sample document:</div>
                {samples.map((s) => <Button key={s.name} size="small" icon={<FileTextOutlined />} disabled={running} onClick={() => dispatch(loadSample(s.name))}>{s.label}</Button>)}
              </div>
            )}
          </div>
        </div>

        {messages.map((m) => (
          <div key={m.id} className={`bubble ${m.role === 'user' ? 'me' : m.role === 'system' ? 'sys' : 'ai'}`}>
            {m.role === 'user' ? <UserOutlined className="av" /> : m.role === 'system' ? <WarningFilled className="av warn" /> : <RobotOutlined className="av" />}
            <div>
              {m.attachments?.map((a) => <Tag key={a} icon={<PaperClipOutlined />}>{a}</Tag>)}
              <div style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>
              {m.changes && m.changes.length > 0 && (
                <div className="diff">{m.changes.map((c) => <div key={c.path}><b>{c.label}</b>: <s>{c.old || 'empty'}</s> → <span className="new">{c.new}</span></div>)}</div>
              )}
              {m.citations && m.citations.length > 0 && <div className="cites">{m.citations.map((c, i) => <div key={i} className="quote">“{c}”</div>)}</div>}
            </div>
          </div>
        ))}

        {(running || steps.length > 0) && (
          <div className="runcard">
            <div className="runcard-title">{running ? 'Analysing…' : 'Analysis steps'} {modeLabel && <Tag color={modeLabel.startsWith('offline') ? 'orange' : 'blue'}>{modeLabel}</Tag>}</div>
            {steps.map((s) => (
              <div key={s.node} className="runstep">
                <StepIcon s={s.status} />
                <div><div>{s.label}</div>
                  {(s.detail || s.model) && <div className="rs-detail">{s.detail}{s.model ? ` · ${s.model}` : ''}{s.seconds ? ` · ${s.seconds}s` : ''}</div>}</div>
              </div>
            ))}
            {waitNote && <div className="rs-wait">{waitNote}</div>}
            {!running && lastRun && <div className="rs-detail" style={{ marginTop: 4 }}>{lastRun.patches} fields written · {lastRun.skipped} protected (your edits kept) · {lastRun.tokens} tokens</div>}
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="cp-foot">
        {extracted && (
          <div className="chips">{CHIPS.map((c) => <Tag key={c.label} className="chip" onClick={() => !running && dispatch(runCopilot({ message: c.msg, intent: c.intent }))}>{c.label}</Tag>)}</div>
        )}
        {files.length > 0 && <div style={{ marginBottom: 4 }}>{files.map((f, i) => <Tag key={i} closable icon={<PaperClipOutlined />} onClose={() => setFiles(files.filter((_, j) => j !== i))}>{f.name}</Tag>)}</div>}
        <div className="composer">
          <input ref={fileRef} type="file" hidden multiple accept=".pdf,.eml,.txt,.docx" onChange={(e) => { setFiles((f) => [...f, ...Array.from(e.target.files ?? [])]); e.target.value = '' }} />
          <Tooltip title="Attach PDF, .eml, .docx or .txt"><Button type="text" icon={<PaperClipOutlined />} onClick={() => fileRef.current?.click()} disabled={running || locked} /></Tooltip>
          <Input.TextArea autoSize={{ minRows: 1, maxRows: 6 }} value={text} onChange={(e) => setText(e.target.value)} disabled={locked}
            placeholder={extracted ? 'Ask a question or correct a value, e.g. “the batch number is OMZ-2610-018”…' : 'Paste an incident report / email / shift log, or attach a file…'}
            onPressEnter={(e) => { if (!e.shiftKey) { e.preventDefault(); send() } }} />
          <Button type="primary" icon={<SendOutlined />} onClick={send} loading={running} disabled={locked} />
        </div>
        <div className="cp-powered">Powered by LangGraph + Groq · prototype — AI output is a draft for qualified review</div>
      </div>
    </div>
  )
}
