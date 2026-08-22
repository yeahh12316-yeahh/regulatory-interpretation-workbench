import { runtimeConfig } from './runtime-config'
import { fetchWithTimeout, formatRequestFailure, isTransientStatus, requestTimeoutMs, retryDelay } from './request-retry'

async function request(path, options = {}, accessToken, retryOptions = {}) {
  const headers = new Headers(options.headers || {})
  headers.set('Accept', 'application/json')
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)

  const retries = retryOptions.retries ?? ((options.method || 'GET').toUpperCase() === 'GET' ? 2 : 0)
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      const response = await fetchWithTimeout(
        `${runtimeConfig.apiBaseUrl}${path}`,
        { ...options, headers },
        requestTimeoutMs({ path, method: options.method }),
      )
      const payload = await response.json().catch(() => ({}))
      if (response.ok) return payload
      if (response.status === 401 && accessToken) {
        window.dispatchEvent(new CustomEvent('regulatory-workbench-auth-expired'))
      }
      if (isTransientStatus(response.status) && attempt < retries) {
        await new Promise((resolve) => window.setTimeout(resolve, retryDelay(attempt)))
        continue
      }
      const detail = payload.detail
      const message = typeof detail === 'string' ? detail : detail?.message || `请求失败（${response.status}）`
      const error = new Error(message)
      error.status = response.status
      error.detail = detail
      error.documentId = detail?.document_id
      error.retryable = detail?.retryable === true || isTransientStatus(response.status)
      throw error
    } catch (cause) {
      if (cause?.status || attempt >= retries) throw formatRequestFailure(cause)
      await new Promise((resolve) => window.setTimeout(resolve, retryDelay(attempt)))
    }
  }
}

async function requestReadiness(retries = 4) {
  const base = runtimeConfig.apiBaseUrl.replace(/\/api\/?$/, '') || '/'
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      const response = await fetchWithTimeout(`${base}/ready`, { headers: { Accept: 'application/json' } }, requestTimeoutMs({ path: '/ready', phase: 'readiness' }), 'readiness')
      const payload = await response.json().catch(() => ({}))
      if (response.ok && payload.status === 'ready') return payload
      if (attempt < retries) {
        await new Promise((resolve) => window.setTimeout(resolve, retryDelay(attempt)))
        continue
      }
      const error = new Error(payload.detail || `公开服务尚未就绪（${response.status}）`)
      error.retryable = true
      throw error
    } catch (cause) {
      if (attempt >= retries) throw formatRequestFailure(cause)
      await new Promise((resolve) => window.setTimeout(resolve, retryDelay(attempt)))
    }
  }
}

export const apiClient = {
  waitUntilReady: () => requestReadiness(),
  guestSession: () => request('/auth/guest', { method: 'POST' }, undefined, { retries: 3 }),
  login: (body) => request('/auth/login', { method: 'POST', body: JSON.stringify(body) }),
  register: (body) => request('/auth/register', { method: 'POST', body: JSON.stringify(body) }),
  me: (token) => request('/auth/me', {}, token),
  organizations: (token) => request('/auth/organizations', {}, token),
  currentOrganization: (token) => request('/organizations/current', {}, token),
  members: (token) => request('/organizations/current/members', {}, token),
  addMember: (token, body) => request('/organizations/current/members', { method: 'POST', body: JSON.stringify(body) }, token),
  updateMemberRole: (token, memberId, body) => request(`/organizations/current/members/${memberId}`, { method: 'PATCH', body: JSON.stringify(body) }, token),
  switchOrganization: (token, organizationId) => request('/auth/switch-organization', { method: 'POST', body: JSON.stringify({ organization_id: organizationId }) }, token),
  importRegulation: async (file, options = {}, token) => {
    await requestReadiness()
    const form = new FormData()
    form.append('file', file)
    if (options.taskId) form.append('task_id', options.taskId)
    if (options.regulationId) form.append('regulation_id', options.regulationId)
    if (options.versionLabel) form.append('version_label', options.versionLabel)
    if (options.versionRole) form.append('version_role', options.versionRole)
    if (options.uploadId) form.append('upload_id', options.uploadId)
    if (options.sourceUrl) form.append('source_url', options.sourceUrl)
    return request('/regulations/import', { method: 'POST', body: form, headers: options.uploadId ? { 'Idempotency-Key': options.uploadId } : {} }, token, { retries: 3 })
  },
  tasks: (token) => request('/tasks', {}, token),
  task: (taskId, token) => request(`/tasks/${taskId}`, {}, token),
  retryRegulationParse: (documentId, token) => request(`/source-documents/${documentId}/retry-parse`, { method: 'POST' }, token),
  regulationParseStatus: (documentId, token) => request(`/source-documents/${documentId}/parse-status`, {}, token),
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
  bulkReview: (taskId, token) => request(`/tasks/${taskId}/review/bulk`, { method: 'POST' }, token),
  updateReviewMetadata: (taskId, body, token) => request(`/tasks/${taskId}/review/metadata`, { method: 'PATCH', body: JSON.stringify(body) }, token),
  updateReviewRequirement: (taskId, requirementId, body, token) => request(`/tasks/${taskId}/review/requirements/${requirementId}`, { method: 'PATCH', body: JSON.stringify(body) }, token),
  updateReviewInterpretation: (taskId, interpretationId, body, token) => request(`/tasks/${taskId}/review/interpretations/${interpretationId}`, { method: 'PATCH', body: JSON.stringify(body) }, token),
  updateReviewEvidence: (taskId, evidenceId, body, token) => request(`/tasks/${taskId}/review/evidence/${evidenceId}`, { method: 'PATCH', body: JSON.stringify(body) }, token),
  runReviewQc: (taskId, token) => request(`/tasks/${taskId}/review/qc`, { method: 'POST' }, token),
  runLlmReview: (taskId, token) => request(`/tasks/${taskId}/review/llm`, { method: 'POST' }, token),
  decideLlmReview: (taskId, body, token) => request(`/tasks/${taskId}/review/llm/decision`, { method: 'POST', body: JSON.stringify(body) }, token),
  reviewDecision: (taskId, body, token) => request(`/tasks/${taskId}/review/decision`, { method: 'POST', body: JSON.stringify(body) }, token),
  exportDocx: (taskId, token) => request(`/tasks/${taskId}/export/docx`, { method: 'POST' }, token),
}
