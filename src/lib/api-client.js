import { runtimeConfig } from './runtime-config'

async function request(path, options = {}, accessToken) {
  const headers = new Headers(options.headers || {})
  headers.set('Accept', 'application/json')
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)

  const response = await fetch(`${runtimeConfig.apiBaseUrl}${path}`, { ...options, headers })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = payload.detail
    const message = typeof detail === 'string' ? detail : detail?.message || `请求失败（${response.status}）`
    const error = new Error(message)
    error.status = response.status
    error.detail = detail
    error.documentId = detail?.document_id
    error.retryable = detail?.retryable === true
    throw error
  }
  return payload
}

export const apiClient = {
  login: (body) => request('/auth/login', { method: 'POST', body: JSON.stringify(body) }),
  register: (body) => request('/auth/register', { method: 'POST', body: JSON.stringify(body) }),
  me: (token) => request('/auth/me', {}, token),
  organizations: (token) => request('/auth/organizations', {}, token),
  currentOrganization: (token) => request('/organizations/current', {}, token),
  members: (token) => request('/organizations/current/members', {}, token),
  addMember: (token, body) => request('/organizations/current/members', { method: 'POST', body: JSON.stringify(body) }, token),
  updateMemberRole: (token, memberId, body) => request(`/organizations/current/members/${memberId}`, { method: 'PATCH', body: JSON.stringify(body) }, token),
  switchOrganization: (token, organizationId) => request('/auth/switch-organization', { method: 'POST', body: JSON.stringify({ organization_id: organizationId }) }, token),
  importRegulation: (file, options = {}, token) => {
    const form = new FormData()
    form.append('file', file)
    if (options.taskId) form.append('task_id', options.taskId)
    if (options.regulationId) form.append('regulation_id', options.regulationId)
    if (options.versionLabel) form.append('version_label', options.versionLabel)
    if (options.sourceUrl) form.append('source_url', options.sourceUrl)
    return request('/regulations/import', { method: 'POST', body: form }, token)
  },
  retryRegulationParse: (documentId, token) => request(`/source-documents/${documentId}/retry-parse`, { method: 'POST' }, token),
  articles: (regulationId, versionId, token) => request(`/regulations/${regulationId}/versions/${versionId}/articles`, {}, token),
  article: (articleId, token) => request(`/articles/${articleId}`, {}, token),
  runInterpretation: (taskId, body, token) => request(`/tasks/${taskId}/interpret`, { method: 'POST', body: JSON.stringify(body) }, token),
  startWorkflow: (taskId, body, token) => request(`/tasks/${taskId}/workflow`, { method: 'POST', body: JSON.stringify(body) }, token),
  workflow: (workflowId, token) => request(`/workflows/${workflowId}`, {}, token),
  taskWorkflow: (taskId, token) => request(`/tasks/${taskId}/workflow`, {}, token),
  retryWorkflow: (workflowId, token) => request(`/workflows/${workflowId}/retry`, { method: 'POST' }, token),
  rerunWorkflowNode: (workflowId, nodeName, token) => request(`/workflows/${workflowId}/rerun`, { method: 'POST', body: JSON.stringify({ node_name: nodeName }) }, token),
  interpretation: (taskId, token) => request(`/tasks/${taskId}/interpretation`, {}, token),
  requirements: (taskId, token) => request(`/tasks/${taskId}/requirements`, {}, token),
  confirmS5Relation: (taskId, body, token) => request(`/tasks/${taskId}/s5/confirm-relation`, { method: 'POST', body: JSON.stringify(body || {}) }, token),
  compareS5: (taskId, token) => request(`/tasks/${taskId}/s5/compare`, { method: 'POST' }, token),
  createContentPackage: (taskId, token) => request(`/tasks/${taskId}/content-package`, { method: 'POST' }, token),
  contentPackage: (taskId, token) => request(`/tasks/${taskId}/content-package`, {}, token),
  review: (taskId, token) => request(`/tasks/${taskId}/review`, {}, token),
  updateReviewMetadata: (taskId, body, token) => request(`/tasks/${taskId}/review/metadata`, { method: 'PATCH', body: JSON.stringify(body) }, token),
  updateReviewRequirement: (taskId, requirementId, body, token) => request(`/tasks/${taskId}/review/requirements/${requirementId}`, { method: 'PATCH', body: JSON.stringify(body) }, token),
  updateReviewInterpretation: (taskId, interpretationId, body, token) => request(`/tasks/${taskId}/review/interpretations/${interpretationId}`, { method: 'PATCH', body: JSON.stringify(body) }, token),
  updateReviewEvidence: (taskId, evidenceId, body, token) => request(`/tasks/${taskId}/review/evidence/${evidenceId}`, { method: 'PATCH', body: JSON.stringify(body) }, token),
  runReviewQc: (taskId, token) => request(`/tasks/${taskId}/review/qc`, { method: 'POST' }, token),
  runLlmReview: (taskId, token) => request(`/tasks/${taskId}/review/llm`, { method: 'POST' }, token),
  reviewDecision: (taskId, body, token) => request(`/tasks/${taskId}/review/decision`, { method: 'POST', body: JSON.stringify(body) }, token),
  exportDocx: (taskId, token) => request(`/tasks/${taskId}/export/docx`, { method: 'POST' }, token),
}
