"""Optional model-backed reviewer with an explicit non-configured state."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db.models import QCResult, Task
from backend.app.services.review import _add_finding, _id, _now, get_latest_review_objects, write_audit


def _review_payload(objects: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirements": [
            {
                "requirement_id": item.requirement_id,
                "article_id": item.article_id,
                "source_text": item.source_text,
                "structured_data": item.structured_data,
                "subject": item.subject,
                "action": item.action,
                "condition": item.condition,
                "deadline": item.deadline,
                "threshold": item.threshold,
                "evidence_ids": [evidence.evidence_id for evidence in item.evidence],
            }
            for item in objects["requirements"]
        ],
        "interpretations": [
            {
                "interpretation_id": item.interpretation_id,
                "article_id": item.article_id,
                "summary": item.summary,
                "interpretation": item.interpretation,
                "regulatory_meaning": item.regulatory_meaning,
                "content_blocks": item.content_blocks,
                "evidence_ids": [evidence.evidence_id for evidence in item.evidence],
            }
            for item in [objects["overall"], *objects["article_interpretations"]]
        ],
        "evidence": [
            {"evidence_id": item.evidence_id, "source_text": item.source_text, "locator": item.locator}
            for item in objects["evidence"]
        ],
    }


def _parse_json_content(content: Any) -> dict[str, Any]:
    if isinstance(content, dict):
        return content
    text = str(content or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.rsplit("```", 1)[0].strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("LLM Reviewer 返回的不是 JSON 对象")
    return parsed


def _call_openai_compatible(prompt: str) -> dict[str, Any]:
    settings = get_settings()
    base = settings.llm_base_url.rstrip("/")
    url = base if base.endswith("/chat/completions") else f"{base}/chat/completions"
    request = Request(
        url,
        data=json.dumps(
            {
                "model": settings.llm_model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": "你是外规解读质量复核员。只检查原文、证据、数字和表述一致性，不补充原文没有的法律事实。"},
                    {"role": "user", "content": prompt},
                ],
            },
            ensure_ascii=False,
        ).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {settings.llm_api_key}"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=settings.llm_timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"LLM Reviewer 请求失败：{exc}") from exc
    content = (((payload.get("choices") or [{}])[0]).get("message") or {}).get("content")
    return _parse_json_content(content)


def run_llm_review(db: Session, task: Task, *, actor_id: str) -> dict[str, Any]:
    objects = get_latest_review_objects(db, task)
    settings = get_settings()
    review_run_id = _id("LLMRUN")
    provider = settings.llm_provider.strip().lower()
    configured = provider not in {"", "rule_based", "none", "disabled"} and bool(settings.llm_api_key.strip()) and bool(settings.llm_model.strip())
    if not configured:
        result = _add_finding(
            db,
            task,
            target_type="task",
            target_id=task.task_id,
            check_type="LLM_REVIEW",
            status="not_configured",
            code="LLM_REVIEW_NOT_CONFIGURED",
            message="未配置可调用的 LLM Provider、模型或 API Key；本次没有声称完成模型复核。",
            details={"review_run_id": review_run_id, "provider": settings.llm_provider, "model": settings.llm_model},
        )
        write_audit(db, task=task, actor_id=actor_id, action="RUN_LLM_REVIEW", entity_type="task", entity_id=task.task_id, before_state={}, after_state={"status": "not_configured", "review_run_id": review_run_id})
        db.commit()
        return {"status": "not_configured", "review_run_id": review_run_id, "provider": settings.llm_provider, "model": settings.llm_model, "findings": [result.findings]}

    prompt = json.dumps(
        {
            "task_id": task.task_id,
            "review_scope": "检查监管原文片段是否被准确引用、结构化数字是否一致、内容块是否有证据、解读是否存在超出原文的确定性表述。",
            "data": _review_payload(objects),
            "output_schema": {
                "overall_status": "pass | needs_revision | fail",
                "findings": [{"code": "string", "severity": "info | warning | blocker", "message": "string", "target_type": "string", "target_id": "string"}],
            },
        },
        ensure_ascii=False,
    )
    try:
        model_result = _call_openai_compatible(prompt)
        overall_status = str(model_result.get("overall_status") or "needs_revision").lower()
        findings = [item for item in (model_result.get("findings") or []) if isinstance(item, dict)]
        status = "passed" if overall_status == "pass" and not any(str(item.get("severity")).lower() == "blocker" for item in findings) else ("blocker" if overall_status == "fail" or any(str(item.get("severity")).lower() == "blocker" for item in findings) else "warning")
        code = "LLM_REVIEW_PASSED" if status == "passed" else "LLM_REVIEW_NEEDS_REVISION"
        message = "LLM Reviewer 未发现阻断项。" if status == "passed" else "LLM Reviewer 返回了需要人工处理的发现项。"
    except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
        status = "failed"
        findings = [{"code": "LLM_REVIEW_FAILED", "severity": "warning", "message": str(exc), "target_type": "task", "target_id": task.task_id}]
        code = "LLM_REVIEW_FAILED"
        message = "LLM Reviewer 调用或结构化解析失败，不能视为通过。"

    result = _add_finding(
        db,
        task,
        target_type="task",
        target_id=task.task_id,
        check_type="LLM_REVIEW",
        status=status,
        code=code,
        message=message,
        details={"review_run_id": review_run_id, "provider": settings.llm_provider, "model": settings.llm_model, "findings": findings},
    )
    write_audit(db, task=task, actor_id=actor_id, action="RUN_LLM_REVIEW", entity_type="task", entity_id=task.task_id, before_state={}, after_state={"status": status, "review_run_id": review_run_id})
    db.commit()
    return {"status": status, "review_run_id": review_run_id, "provider": settings.llm_provider, "model": settings.llm_model, "findings": result.findings.get("findings", [result.findings])}
