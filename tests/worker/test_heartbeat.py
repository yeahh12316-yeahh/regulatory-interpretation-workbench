from worker.app.heartbeat import heartbeat_payload


def test_worker_heartbeat_reports_worker_identity():
    payload = heartbeat_payload()

    assert payload["status"] == "ok"
    assert payload["service"] == "regulatory-interpretation-worker"
    assert payload["mode"] == "scaffold"
