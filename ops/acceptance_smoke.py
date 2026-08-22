"""Run a non-destructive live acceptance smoke test against a deployed API."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from uuid import uuid4

import httpx


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:18000")
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    if not args.pdf.is_file():
        raise SystemExit(f"PDF not found: {args.pdf}")

    suffix = uuid4().hex[:12]
    task_id = f"LIVE_ACCEPTANCE_{suffix}"
    email = f"acceptance-{suffix}@example.com"
    password = f"Acceptance-{uuid4().hex[:16]}!"
    # OCR can take longer than a normal API request for a multi-page scan;
    # keep the client timeout aligned with the overall acceptance budget.
    client = httpx.Client(base_url=args.base_url.rstrip("/"), timeout=args.timeout, trust_env=False)

    def check(response: httpx.Response, expected: set[int]) -> dict:
        if response.status_code not in expected:
            raise RuntimeError(f"{response.request.method} {response.request.url} -> {response.status_code}: {response.text}")
        return response.json()

    try:
        health = check(client.get("/health"), {200})
        ready = check(client.get("/ready"), {200})
        registered = check(
            client.post(
                "/api/auth/register",
                json={
                    "email": email,
                    "password": password,
                    "display_name": "Live Acceptance Reviewer",
                    "organization_name": "外规解读验收机构",
                    "organization_slug": f"acceptance-{suffix}",
                },
            ),
            {201},
        )
        headers = {"Authorization": f"Bearer {registered['access_token']}"}
        task = check(
            client.post(
                "/api/tasks",
                headers=headers,
                json={"task_id": task_id, "task_name": "CASE-001 真实法规验收"},
            ),
            {201},
        )
        with args.pdf.open("rb") as handle:
            imported = check(
                client.post(
                    "/api/regulations/import",
                    headers=headers,
                    files={"file": (args.pdf.name, handle, "application/pdf")},
                    data={"task_id": task_id, "version_label": "2017年版"},
                ),
                {201},
            )
        workflow = check(
            client.post(
                f"/api/tasks/{task_id}/workflow",
                headers=headers,
                json={"institution_type": "商业银行", "business_scope": ["呆账核销"], "region": "中国境内"},
            ),
            {202},
        )

        deadline = time.monotonic() + args.timeout
        while workflow["status"] in {"queued", "running"} and time.monotonic() < deadline:
            time.sleep(2)
            workflow = check(client.get(f"/api/tasks/{task_id}/workflow", headers=headers), {200})
        if workflow["status"] in {"queued", "running"}:
            raise RuntimeError(f"workflow timed out after {args.timeout}s: {workflow['status']}")
        if workflow["status"] != "completed":
            raise RuntimeError(f"workflow did not complete: {json.dumps(workflow, ensure_ascii=False)}")

        interpretation = check(client.get(f"/api/tasks/{task_id}/interpretation", headers=headers), {200})
        review = check(client.get(f"/api/tasks/{task_id}/review", headers=headers), {200})
        qc = check(client.post(f"/api/tasks/{task_id}/review/qc", headers=headers), {200})
        llm = check(client.post(f"/api/tasks/{task_id}/review/llm", headers=headers), {200})
        print(
            json.dumps(
                {
                    "health": health,
                    "ready": ready,
                    "task_id": task_id,
                    "document_id": imported.get("source_document", {}).get("document_id"),
                    "page_count": imported.get("page_count"),
                    "article_count": imported.get("article_count"),
                    "workflow": {
                        "workflow_id": workflow.get("workflow_id"),
                        "status": workflow.get("status"),
                        "progress": workflow.get("progress"),
                        "nodes": [
                            {"node_name": node.get("node_name"), "status": node.get("status")}
                            for node in workflow.get("nodes", [])
                        ],
                    },
                    "interpretation": {
                        "requirements": len(interpretation.get("requirements", [])),
                        "article_interpretations": len(interpretation.get("article_interpretations", [])),
                        "evidence": len(interpretation.get("evidence", [])),
                    },
                    "review": {
                        "summary": review.get("review_summary", {}),
                        "qc_status": qc.get("status"),
                        "qc_blocker_count": qc.get("blocker_count"),
                        "qc_blocker_codes": [item.get("code") for item in qc.get("blockers", [])],
                        "llm_status": llm.get("status"),
                        "llm_provider": llm.get("provider"),
                        "llm_model": llm.get("model"),
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
