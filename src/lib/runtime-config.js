/**
 * Frontend runtime contract for the API-backed workbench.
 * Set VITE_API_BASE_URL to an origin plus /api, for example:
 * http://localhost:8000/api
 */
const configuredApiBaseUrl = import.meta.env?.VITE_API_BASE_URL || ''
const runtimeEnv = import.meta.env || {}

export const runtimeConfig = Object.freeze({
  apiBaseUrl: configuredApiBaseUrl || '/api',
  apiConfigured: Boolean(configuredApiBaseUrl),
  environment: runtimeEnv.MODE || 'development',
  enableS5: runtimeEnv.VITE_ENABLE_S5 === 'true',
})

export function resolveApiUrl(apiBaseUrl, path) {
  if (!path) return apiBaseUrl
  if (/^https?:\/\//i.test(path)) return path
  const base = String(apiBaseUrl || '').replace(/\/+$/, '')
  const normalizedPath = String(path).startsWith('/') ? String(path) : `/${path}`
  if (normalizedPath === '/api' || normalizedPath.startsWith('/api/')) {
    return `${base.replace(/\/api$/, '')}${normalizedPath}`
  }
  return `${base}${normalizedPath}`
}
