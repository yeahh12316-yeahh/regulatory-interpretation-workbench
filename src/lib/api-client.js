import { runtimeConfig } from './runtime-config'

async function request(path, options = {}, accessToken) {
  const headers = new Headers(options.headers || {})
  headers.set('Accept', 'application/json')
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)

  const response = await fetch(`${runtimeConfig.apiBaseUrl}${path}`, { ...options, headers })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    const error = new Error(payload.detail || `请求失败（${response.status}）`)
    error.status = response.status
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
  articles: (regulationId, versionId, token) => request(`/regulations/${regulationId}/versions/${versionId}/articles`, {}, token),
  article: (articleId, token) => request(`/articles/${articleId}`, {}, token),
  runInterpretation: (taskId, body, token) => request(`/tasks/${taskId}/interpret`, { method: 'POST', body: JSON.stringify(body) }, token),
  interpretation: (taskId, token) => request(`/tasks/${taskId}/interpretation`, {}, token),
  requirements: (taskId, token) => request(`/tasks/${taskId}/requirements`, {}, token),
}
