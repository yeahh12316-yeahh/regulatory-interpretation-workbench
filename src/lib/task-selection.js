export function selectTaskState(taskId, current = {}) {
  return {
    ...current,
    activeTask: taskId,
    pipelineTaskId: taskId,
    pipelineResult: null,
    workflowState: null,
    reviewState: null,
    activeRegulationId: null,
  }
}
