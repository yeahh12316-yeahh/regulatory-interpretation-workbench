from worker.app.celery_app import celery_app


@celery_app.task(name="workflow.execute", bind=True, acks_late=True)
def execute_workflow(self, workflow_id: str) -> None:
    from backend.app.services.workflow import execute_workflow_from_worker

    execute_workflow_from_worker(workflow_id)
