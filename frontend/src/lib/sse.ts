import { EventSourceParserStream } from 'eventsource-parser/stream'
import { demoHeaders } from './api'

export type RunEvent = { type: string; [k: string]: unknown }

/** POST + Server-Sent Events: native EventSource cannot send a body, so we parse the fetch stream. */
export async function streamRun(body: unknown, onEvent: (e: RunEvent) => void, signal?: AbortSignal): Promise<void> {
  const res = await fetch('/api/ai/run', {
    method: 'POST', signal,
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream', ...demoHeaders() },
    body: JSON.stringify(body),
  })
  if (!res.ok || !res.headers.get('content-type')?.includes('text/event-stream')) {
    let msg = `The AI service returned HTTP ${res.status}`
    try { const j = await res.json(); msg = JSON.stringify(j.detail ?? j).slice(0, 300) } catch { /* ignore */ }
    throw new Error(msg)
  }
  const reader = res.body!.pipeThrough(new TextDecoderStream()).pipeThrough(new EventSourceParserStream()).getReader()
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    if (!value?.data) continue
    try { onEvent(JSON.parse(value.data) as RunEvent) } catch { /* ignore malformed frame */ }
  }
}
