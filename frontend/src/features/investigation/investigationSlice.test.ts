import { describe, expect, it } from 'vitest'
import { countAi } from '../../lib/review'
import { getByPath, itemPathOf, setByPath } from '../../lib/paths'
import reducer, { acceptSection, addItem, applyPatch, editField, loadInvestigation, markReviewed, removeItem } from './investigationSlice'

const form = () => ({
  meta: { extracted: true, not_in_source: [] },
  incident: { product_name: '', batch_numbers: [] },
  root_causes: [] as unknown[],
})

function loaded() {
  return reducer(undefined, { type: loadInvestigation.fulfilled.type, payload: { id: 'i1', rca_number: 'RCA-1', status: 'draft', version: 1, form_data: form(), provenance: {}, documents: [] } })
}

describe('path helpers', () => {
  it('resolves list items by id and finds the owning item', () => {
    const f = { root_causes: [{ id: 'rc-1', statement: 'a' }] }
    expect(getByPath(f, 'root_causes.rc-1.statement')).toBe('a')
    expect(setByPath(f, 'root_causes.rc-1.statement', 'b')).toBe(true)
    expect(f.root_causes[0].statement).toBe('b')
    expect(itemPathOf(f, 'root_causes.rc-1.statement')).toBe('root_causes.rc-1')
    expect(itemPathOf(f, 'incident.product_name')).toBeNull()
  })
})

describe('investigation slice: AI output vs human edits', () => {
  it('stores AI provenance with a patch, then a human edit takes over and counts as reviewed', () => {
    let s = loaded()
    s = reducer(s, applyPatch({ path: 'incident.product_name', value: 'Omeprazole', prov: { by: 'ai', grounded: 'grounded', quote: 'Product: Omeprazole', reviewed: false } }))
    expect(s.form.incident.product_name).toBe('Omeprazole')
    expect(countAi(s.form, s.prov, [''])).toEqual({ ai: 1, unreviewed: 1 })
    s = reducer(s, editField({ path: 'incident.product_name', value: 'Omeprazole API' }))
    expect(s.prov['incident.product_name']).toMatchObject({ by: 'user', reviewed: true, quote: 'Product: Omeprazole' })
    expect(s.dirty).toBe(true)
  })

  it('marks list items edited/reviewed through their meta, not through a provenance key', () => {
    let s = loaded()
    s = reducer(s, applyPatch({ path: 'root_causes', value: [{ id: 'rc-1', statement: 'hypothesis', meta: { by: 'ai', reviewed: false } }] }))
    expect(countAi(s.form, s.prov, ['root_causes'])).toEqual({ ai: 1, unreviewed: 1 })
    s = reducer(s, editField({ path: 'root_causes.rc-1.statement', value: 'edited hypothesis' }))
    expect(s.form.root_causes[0].meta).toMatchObject({ by: 'user', reviewed: true })
    expect(countAi(s.form, s.prov, ['root_causes'])).toEqual({ ai: 0, unreviewed: 0 })
  })

  it('accepts a whole section and supports add/remove of user items', () => {
    let s = loaded()
    s = reducer(s, applyPatch({ path: 'root_causes', value: [{ id: 'a', statement: 'x', meta: { by: 'ai', reviewed: false } }, { id: 'b', statement: 'y', meta: { by: 'ai', reviewed: false } }] }))
    s = reducer(s, acceptSection(['root_causes']))
    expect(countAi(s.form, s.prov, ['root_causes']).unreviewed).toBe(0)
    s = reducer(s, addItem({ listPath: 'root_causes', prefix: 'rc', item: { statement: 'manual' } }))
    expect(s.form.root_causes).toHaveLength(3)
    expect(s.form.root_causes[2].meta).toEqual({ by: 'user', reviewed: true })
    s = reducer(s, removeItem({ listPath: 'root_causes', id: 'a' }))
    expect(s.form.root_causes).toHaveLength(2)
    s = reducer(s, markReviewed('incident.product_name'))   // no provenance -> no-op, no crash
    expect(s.form.incident.product_name).toBe('')
  })
})
