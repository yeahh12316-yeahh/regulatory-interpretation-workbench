/**
 * Frontend runtime contract for the future API-backed workbench.
 * The current high-fidelity screen can run without an API; Step 6 will wire
 * these values into the task and evidence data loaders.
 */
export const runtimeConfig = Object.freeze({
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || '/api',
  environment: import.meta.env.MODE || 'development',
  enableS5: import.meta.env.VITE_ENABLE_S5 === 'true',
})
