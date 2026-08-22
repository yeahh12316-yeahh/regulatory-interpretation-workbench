import test from 'node:test'
import assert from 'node:assert/strict'

import {
  chooseCurrentTask,
  mapApiTaskToWorkbenchTask,
} from '../../src/lib/task-persistence.js'

test('maps a persisted API task into the public workbench task row', () => {
  const task = mapApiTaskToWorkbenchTask({
    task_id: 'TASK_001',
    task_name: '金融企业呆账核销管理办法解读',
    task_status: 'waiting_review',
    updated_at: '2026-08-22T15:00:00Z',
    processing_config: { institution_type: '商业银行' },
  })

  assert.deepEqual(task, {
    id: 'TASK_001',
    title: '金融企业呆账核销管理办法解读',
    institution: '商业银行',
    status: '待复核',
    updated: '2026-08-22',
    state: 'active',
  })
})

test('prefers the persisted current task and otherwise chooses the newest API task', () => {
  const tasks = [
    { task_id: 'TASK_OLD', task_name: '旧任务', task_status: 'completed', updated_at: '2026-08-21T10:00:00Z' },
    { task_id: 'TASK_NEW', task_name: '新任务', task_status: 'processing', updated_at: '2026-08-22T10:00:00Z' },
  ]

  assert.equal(chooseCurrentTask(tasks, 'TASK_OLD'), 'TASK_OLD')
  assert.equal(chooseCurrentTask(tasks, 'TASK_MISSING'), 'TASK_NEW')
  assert.equal(chooseCurrentTask([], null), null)
})
