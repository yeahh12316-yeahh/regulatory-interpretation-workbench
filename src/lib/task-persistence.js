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
