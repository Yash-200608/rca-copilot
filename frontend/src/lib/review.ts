import { getByPath, type Json } from './paths'

/** Count AI-generated entries (scalar provenance + list items) under the given path prefixes, and how many still need review. */
export function countAi(form: Json, prov: Record<string, Json>, prefixes: string[]): { ai: number; unreviewed: number } {
  let ai = 0, unreviewed = 0
  for (const prefix of prefixes) {
    for (const [k, p] of Object.entries(prov)) {
      if ((prefix === '' || k === prefix || k.startsWith(prefix + '.')) && p?.by === 'ai') {
        ai++
        if (!p.reviewed) unreviewed++
      }
    }
    const walk = (node: Json) => {
      if (Array.isArray(node)) node.forEach(walk)
      else if (node && typeof node === 'object') {
        if (node.meta?.by === 'ai') { ai++; if (!node.meta.reviewed) unreviewed++ }
        for (const [k, v] of Object.entries(node)) if (k !== 'meta') walk(v)
      }
    }
    if (form) walk(prefix === '' ? form : getByPath(form, prefix))
  }
  return { ai, unreviewed }
}
