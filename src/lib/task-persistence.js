const STATUS_LABELS = {
  queued: '处理中',
  processing: '处理中',
  waiting_review: '待复核',
  ready_for_export: '可导出',
  published: '已发布',
  completed: '已完成',
  failed: '失败待处理',
}

function taskUpdatedDate(value) {
  return typeof value === 'string' && value.length >= 10 ? value.slice(0, 10) : '—'
}

export function mapApiTaskToWorkbenchTask(task) {
  const status = task?.task_status || 'draft'
  return {
    id: task.task_id,
    title: task.task_name,
    institution: task.processing_config?.institution_type || '未选择机构类型',
    status: STATUS_LABELS[status] || '未开始',
    updated: taskUpdatedDate(task.updated_at),
    state: status === 'failed' ? 'attention' : 'active',
  }
}

export function chooseCurrentTask(tasks, persistedTaskId) {
  if (!Array.isArray(tasks) || tasks.length === 0) return null
  if (persistedTaskId && tasks.some((task) => task.task_id === persistedTaskId)) return persistedTaskId
  return [...tasks]
    .sort((left, right) => String(right.updated_at || '').localeCompare(String(left.updated_at || '')))
    .at(0)?.task_id || null
}

export function mapPipelineEvidence(result) {
  return (result?.evidence || []).map((item) => ({
    id: item.evidence_id,
    title: `${item.locator?.article_no || '条款'} 原文证据`,
    type: '法规原文证据',
    location: `${item.source_text?.slice(0, 26) || '原文'} · 第${item.locator?.page || '待确认'}页`,
    note: item.description || '已绑定到 S1—S4 解读结果，待人工复核。',
    tone: 'green',
    sourceDocumentId: item.source_document_id,
    sourcePage: item.locator?.page || 1,
  }))
}
