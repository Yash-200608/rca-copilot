/* eslint-disable @typescript-eslint/no-explicit-any */
// Dot-path access into the canonical form. A segment can be an object key, a list index or a list item id.
export type Json = any

const segs = (p: string) => p.split('.').filter(Boolean)
const isIdx = (s: string) => /^\d+$/.test(s)

function step(node: Json, seg: string): Json {
  if (Array.isArray(node)) return isIdx(seg) ? node[+seg] : node.find((i: Json) => i && i.id === seg)
  return node == null ? undefined : node[seg]
}

export function getByPath(root: Json, path: string): Json {
  let node = root
  for (const s of segs(path)) {
    node = step(node, s)
    if (node === undefined || node === null) return node
  }
  return node
}

/** Mutating setter (use inside an immer reducer). Returns false if the path does not resolve. */
export function setByPath(root: Json, path: string, value: Json): boolean {
  const s = segs(path)
  let node = root
  for (let i = 0; i < s.length - 1; i++) {
    node = step(node, s[i])
    if (node === undefined || node === null) return false
  }
  const last = s[s.length - 1]
  if (Array.isArray(node)) {
    const idx = isIdx(last) ? +last : node.findIndex((x: Json) => x && x.id === last)
    if (idx < 0) return false
    node[idx] = value
    return true
  }
  node[last] = value
  return true
}

/** If `path` points inside a list item addressed by id, return the path of that item, else null. */
export function itemPathOf(root: Json, path: string): string | null {
  const s = segs(path)
  let node = root
  for (let i = 0; i < s.length; i++) {
    const parent = node
    node = step(node, s[i])
    if (Array.isArray(parent) && !isIdx(s[i]) && node && i < s.length - 1) return s.slice(0, i + 1).join('.')
    if (node === undefined || node === null) return null
  }
  return null
}

export const newId = (prefix: string) => `${prefix}-${Math.random().toString(36).slice(2, 8)}`
