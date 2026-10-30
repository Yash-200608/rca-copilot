export class ApiError extends Error {
  status: number
  detail: unknown
  constructor(status: number, detail: unknown) {
    super(typeof detail === 'string' ? detail : (detail as { message?: string })?.message ?? `HTTP ${status}`)
    this.status = status
    this.detail = detail
  }
}

export type Identity = { user: string; role: 'investigator' | 'qa' }
const KEY = 'rca.identity'

export function loadIdentity(): Identity {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) || 'null')
    if (v?.role) return v
  } catch { /* storage may be unavailable */ }
  return { user: 'A. Mehta (Investigator)', role: 'investigator' }
}
export function saveIdentity(i: Identity) {
  try { localStorage.setItem(KEY, JSON.stringify(i)) } catch { /* ignore */ }
}
export function demoHeaders(): Record<string, string> {
  const i = loadIdentity()
  return { 'X-Demo-User': i.user, 'X-Demo-Role': i.role }
}

export async function api<T = unknown>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const headers: Record<string, string> = { ...demoHeaders(), ...(init.headers as Record<string, string> | undefined) }
  let body = init.body
  if (init.json !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(init.json)
  }
  const res = await fetch('/api' + path, { ...init, headers, body })
  if (!res.ok) {
    let detail: unknown = res.statusText
    try { const j = await res.json(); detail = j.detail ?? j } catch { /* not json */ }
    throw new ApiError(res.status, detail)
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T)
}
