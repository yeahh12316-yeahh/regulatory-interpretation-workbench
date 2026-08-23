import test from 'node:test'
import assert from 'node:assert/strict'

import { formatRequestFailure, isTransientStatus, requestTimeoutMs } from '../../src/lib/request-retry.js'

test('identifies Render cold-start and gateway statuses as retryable', () => {
  assert.equal(isTransientStatus(502), true)
  assert.equal(isTransientStatus(503), true)
  assert.equal(isTransientStatus(504), true)
  assert.equal(isTransientStatus(422), false)
})

test('turns Safari network failure into a recoverable public-workspace message', () => {
  const error = formatRequestFailure(new TypeError('Load failed'))

  assert.equal(error.message, '公开服务暂时未响应，可能正在从休眠中唤醒，请稍后重试。')
  assert.equal(error.retryable, true)
  assert.equal(error.code, 'NETWORK_ERROR')
})

test('allows Render cold start and PDF parsing longer than ordinary API reads', () => {
  assert.equal(requestTimeoutMs({ path: '/ready', phase: 'readiness' }), 45000)
  assert.equal(requestTimeoutMs({ path: '/regulations/import', method: 'POST' }), 180000)
  assert.equal(requestTimeoutMs({ path: '/tasks/TASK_1/review/llm', method: 'POST' }), 180000)
  assert.equal(requestTimeoutMs({ path: '/tasks/TASK_1/review/qc', method: 'POST' }), 180000)
  assert.equal(requestTimeoutMs({ path: '/tasks/TASK_1' }), 30000)
})

test('turns a readiness timeout into an actionable retry message', () => {
  const error = formatRequestFailure({ code: 'REQUEST_TIMEOUT', phase: 'readiness', message: 'timeout' })

  assert.match(error.message, /唤醒超时/)
  assert.equal(error.retryable, true)
})
