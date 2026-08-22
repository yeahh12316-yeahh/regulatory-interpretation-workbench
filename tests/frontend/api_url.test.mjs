import test from 'node:test'
import assert from 'node:assert/strict'

import { resolveApiUrl } from '../../src/lib/runtime-config.js'

test('does not duplicate the API prefix for report download paths', () => {
  assert.equal(
    resolveApiUrl('https://regulatory-interpretation-api.onrender.com/api', '/api/tasks/TASK_1/exports/REPORT_1/html'),
    'https://regulatory-interpretation-api.onrender.com/api/tasks/TASK_1/exports/REPORT_1/html',
  )
})

test('keeps ordinary API-relative paths under the configured API base', () => {
  assert.equal(
    resolveApiUrl('https://regulatory-interpretation-api.onrender.com/api', '/source-documents/DOC_1/file'),
    'https://regulatory-interpretation-api.onrender.com/api/source-documents/DOC_1/file',
  )
})
