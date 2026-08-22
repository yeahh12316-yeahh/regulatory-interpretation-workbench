import test from 'node:test'
import assert from 'node:assert/strict'
import { getLatestReviewGateSummary } from '../../src/lib/review-gate.js'

test('latest QC summary ignores prior runs and reports the actual blocker', () => {
  const summary = getLatestReviewGateSummary(
    { last_checkpoint: { qc_run_id: 'QCRUN_NEW', qc_status: 'blocked' } },
    [
      { qc_id: 'QC_OLD', check_type: 'REVIEW_GATE', status: 'blocker', findings: { qc_run_id: 'QCRUN_OLD', code: 'OLD_BLOCKER' } },
      { qc_id: 'QC_NEW_WARNING', check_type: 'REVIEW_GATE', status: 'warning', findings: { qc_run_id: 'QCRUN_NEW', code: 'S5_SKIPPED' } },
      { qc_id: 'QC_NEW_BLOCKER', check_type: 'REVIEW_GATE', status: 'blocker', findings: { qc_run_id: 'QCRUN_NEW', code: 'S5_NOT_READY', message: 'S5 尚未完成' } },
    ],
  )

  assert.equal(summary.status, 'blocked')
  assert.equal(summary.blockers.length, 1)
  assert.equal(summary.blockers[0].findings.code, 'S5_NOT_READY')
  assert.equal(summary.warnings.length, 1)
})

test('summary falls back to result status for older task payloads', () => {
  const summary = getLatestReviewGateSummary({}, [
    { check_type: 'REVIEW_GATE', status: 'passed', findings: {} },
  ])

  assert.equal(summary.status, 'passed')
  assert.equal(summary.blockers.length, 0)
})

