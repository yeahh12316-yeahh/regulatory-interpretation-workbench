const TRANSIENT_STATUSES = new Set([408, 425, 429, 502, 503, 504])

export function isTransientStatus(status) {
  return TRANSIENT_STATUSES.has(Number(status))
}

export function formatRequestFailure(cause) {
  const message = String(cause?.message || cause || '')
  if (cause?.code === 'REQUEST_TIMEOUT') {
    const error = new Error(cause.phase === 'readiness'
      ? '公开服务唤醒超时，文件尚未上传；请点击“上传并登记”再次尝试。'
      : '法规上传或解析超时，文件可能已安全保存；请再次尝试，系统会继续使用同一上传请求。')
    error.code = cause.code
    error.retryable = true
    error.cause = cause
    return error
  }
  if (cause?.name === 'TypeError' || /load failed|failed to fetch|networkerror|network error/i.test(message)) {
    const error = new Error('公开服务暂时未响应，可能正在从休眠中唤醒，请稍后重试。')
    error.code = 'NETWORK_ERROR'
    error.retryable = true
    error.cause = cause
    return error
  }
  return cause instanceof Error ? cause : new Error(message || '请求失败')
}

export function retryDelay(attempt) {
  return [500, 1500, 3500, 7000][Math.min(attempt, 3)]
}

export function requestTimeoutMs({ path = '', method = 'GET', phase = 'request' } = {}) {
  if (phase === 'readiness' || path === '/ready') return 45_000
  if (path === '/regulations/import' || (method || '').toUpperCase() === 'POST' && path.includes('/regulations/import')) return 180_000
  if (path.includes('/review/llm') || path.includes('/review/qc')) return 180_000
  return 30_000
}

export async function fetchWithTimeout(url, options = {}, timeoutMs, phase = 'request') {
  const controller = new AbortController()
  const externalSignal = options.signal
  let externalAbort
  if (externalSignal) {
    externalAbort = () => controller.abort(externalSignal.reason)
    if (externalSignal.aborted) externalAbort()
    else externalSignal.addEventListener('abort', externalAbort, { once: true })
  }
  const timer = setTimeout(() => {
    const error = new Error(`请求超过 ${timeoutMs} 毫秒未响应`)
    error.code = 'REQUEST_TIMEOUT'
    error.phase = phase
    controller.abort(error)
  }, timeoutMs)
  try {
    return await fetch(url, { ...options, signal: controller.signal })
  } catch (cause) {
    if (controller.signal.aborted && controller.signal.reason?.code === 'REQUEST_TIMEOUT') throw controller.signal.reason
    throw cause
  } finally {
    clearTimeout(timer)
    if (externalSignal && externalAbort) externalSignal.removeEventListener('abort', externalAbort)
  }
}
