import test from 'node:test'
import assert from 'node:assert/strict'

import { selectTaskState } from '../../src/lib/task-selection.js'

test('selecting a persisted task switches the full workflow context', () => {
  assert.deepEqual(selectTaskState('TASK_2017', {
    activeTask: 'TASK_2015',
    pipelineTaskId: 'TASK_2015',
    pipelineResult: { task: { task_id: 'TASK_2015' } },
    workflowState: { workflow_id: 'WF_2015' },
    reviewState: { task_id: 'TASK_2015' },
    activeRegulationId: 'REG_2015',
  }), {
    activeTask: 'TASK_2017',
    pipelineTaskId: 'TASK_2017',
    pipelineResult: null,
    workflowState: null,
    reviewState: null,
    activeRegulationId: null,
  })
})
