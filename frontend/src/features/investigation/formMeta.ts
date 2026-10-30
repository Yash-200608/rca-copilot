export const SIX_M = ['man', 'machine', 'material', 'method', 'measurement', 'environment'] as const
export const SIX_M_LABEL: Record<string, string> = {
  man: 'Man (people)', machine: 'Machine (equipment)', material: 'Material', method: 'Method (process / procedure)',
  measurement: 'Measurement', environment: 'Environment',
}
export const EVIDENCE_AREAS = ['Equipment', 'Process', 'Materials', 'Analytical', 'Personnel', 'Environment', 'Documentation', 'Historical']
export const EVENT_TYPES = ['Process deviation (CPP/IPC)', 'Equipment failure', 'Utility failure', 'OOS', 'OOT', 'Material/dispensing',
  'Documentation/GDP', 'Data integrity', 'Cleaning/cross-contamination', 'Environmental', 'Other']
export const CLASSES = ['critical', 'major', 'minor']
export const DETECTION = ['Operator observation', 'DCS/SCADA alarm', 'In-process control', 'QC release testing', 'Batch record review', 'Reconciliation / line clearance', 'Self-inspection / audit', 'Customer complaint', 'Other']
export const SHIFTS = ['A', 'B', 'C', 'General', 'Night shift', 'Not applicable']

export const SECTIONS = [
  { id: 'sec-header', short: '1 Header', title: '1. Header & linkage' },
  { id: 'sec-incident', short: '2 Incident', title: '2. Incident details' },
  { id: 'sec-class', short: '3 Class & risk', title: '3. Classification, risk & recurrence' },
  { id: 'sec-problem', short: '4 Problem', title: '4. Problem statement & requirement vs actual' },
  { id: 'sec-contain', short: '5 Containment', title: '5. Immediate actions & containment' },
  { id: 'sec-timeline', short: '6 Timeline', title: '6. Sequence of events' },
  { id: 'sec-fishbone', short: '7 Fishbone', title: '7. Fishbone (6M) analysis' },
  { id: 'sec-whys', short: '8 5 Whys', title: '8. 5 Whys' },
  { id: 'sec-rc', short: '9 Root causes', title: '9. Root causes & contributing factors (AI hypotheses)' },
  { id: 'sec-gaps', short: '10 Evidence gaps', title: '10. Missing evidence & information' },
  { id: 'sec-impact', short: '11 Impact', title: '11. Impact assessment' },
  { id: 'sec-capa', short: '12 CAPA', title: '12. CAPA plan' },
  { id: 'sec-summary', short: '13 Summary', title: '13. Summary, readiness & approval' },
]

export const DISPOSITION_COLOR: Record<string, string> = {
  supported: 'red', possible: 'orange', needs_evidence: 'gold', unlikely: 'default', ruled_out: 'default',
}
export const DISPOSITION_LABEL: Record<string, string> = {
  supported: 'supported by source', possible: 'possible', needs_evidence: 'needs evidence', unlikely: 'unlikely', ruled_out: 'ruled out',
}
export const CAPA_COLOR: Record<string, string> = { correction: 'blue', corrective: 'purple', preventive: 'green' }
export const CAPA_HELP: Record<string, string> = {
  correction: 'Fix / contain the detected problem',
  corrective: 'Eliminate the identified cause',
  preventive: 'Reduce likelihood of similar problems elsewhere',
}
export const STRENGTH_LABEL: Record<string, string> = {
  elimination: 'Elimination (strongest)', engineering: 'Engineering control', administrative: 'Administrative', training: 'Training (weakest)',
}
export const STATUS_COLOR: Record<string, string> = { draft: 'default', in_review: 'processing', approved: 'success', closed: 'default' }
export const STATUS_LABEL: Record<string, string> = { draft: 'Draft', in_review: 'In QA review', approved: 'Approved', closed: 'Closed' }
