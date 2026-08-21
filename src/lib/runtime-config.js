/**
 * Frontend runtime contract for the API-backed workbench.
 * Set VITE_API_BASE_URL to an origin plus /api, for example:
 * http://localhost:8000/api
 */
const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL || ''

export const runtimeConfig = Object.freeze({
  apiBaseUrl: configuredApiBaseUrl || '/api',
  apiConfigured: Boolean(configuredApiBaseUrl),
  environment: import.meta.env.MODE || 'development',
  enableS5: import.meta.env.VITE_ENABLE_S5 === 'true',
})
