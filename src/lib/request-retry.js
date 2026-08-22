const TRANSIENT_STATUSES = new Set([408, 425, 429, 502, 503, 504])

export function isTransientStatus(status) {
  return TRANSIENT_STATUSES.has(Number(status))
}

export function formatRequestFailure(cause) {
  const message = String(cause?.message || cause || '')
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
