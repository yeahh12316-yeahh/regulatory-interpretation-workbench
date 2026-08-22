export function getLatestReviewGateSummary(task, qcResults = []) {
  const latestRunId = task?.last_checkpoint?.qc_run_id
  const gateResults = qcResults.filter((item) => {
    if (item.check_type !== 'REVIEW_GATE') return false
    if (!latestRunId) return true
    return item.findings?.qc_run_id === latestRunId
  })
  const blockers = gateResults.filter((item) => item.status === 'blocker')
  const warnings = gateResults.filter((item) => item.status === 'warning')
  const checkpointStatus = task?.last_checkpoint?.qc_status
  const status = checkpointStatus || (blockers.length ? 'blocked' : gateResults.length ? 'passed' : null)

  return { status, gateResults, blockers, warnings }
}

