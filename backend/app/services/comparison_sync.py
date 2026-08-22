"""Keep the durable workflow view aligned with an independently confirmed S5 run."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def sync_workflow_s5_node(workflow: Any, stage: dict[str, Any]) -> None:
    node = next((item for item in workflow.nodes if item.node_name == "S5"), None)
    if node is None:
        return

    stage_status = stage.get("stage_status")
    node.status = "completed" if stage_status == "completed" else ("skipped" if stage_status == "skipped" else "blocked")
    node.progress = 100 if node.status in {"completed", "skipped"} else 0
    node.completed_at = datetime.now(timezone.utc) if node.status in {"completed", "skipped"} else None
    node.output = stage.get("output") or {}
    workflow.progress = 100 if node.status in {"completed", "skipped"} else workflow.progress
    if node.status in {"completed", "skipped"}:
        workflow.current_node = None
        workflow.completed_at = workflow.completed_at or datetime.now(timezone.utc)
