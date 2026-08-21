import { runtimeConfig } from './runtime-config'

async function request(path, options = {}, accessToken) {
  const headers = new Headers(options.headers || {})
  headers.set('Accept', 'application/json')
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
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
}
