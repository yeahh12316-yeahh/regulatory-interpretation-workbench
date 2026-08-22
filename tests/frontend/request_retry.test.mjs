import test from 'node:test'
import assert from 'node:assert/strict'

import { formatRequestFailure, isTransientStatus } from '../../src/lib/request-retry.js'

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
