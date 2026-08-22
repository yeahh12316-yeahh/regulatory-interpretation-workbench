"""Dependency-free request correlation and Prometheus-compatible metrics."""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import defaultdict
from contextvars import ContextVar
from uuid import uuid4

from fastapi import Request, Response


_request_id: ContextVar[str] = ContextVar("request_id", default="-")
_metrics_lock = threading.Lock()
_request_counts: dict[tuple[str, str, str], int] = defaultdict(int)
_request_latency_sum: dict[tuple[str, str], float] = defaultdict(float)


def current_request_id() -> str:
    return _request_id.get()


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "request_id": getattr(record, "request_id", current_request_id()),
            }
        for field in ("http_method", "http_route", "http_status", "duration_ms"):
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging(json_logs: bool = False) -> logging.Logger:
    logger = logging.getLogger("regagent.http")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            JsonLogFormatter()
            if json_logs
            else logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        )
        logger.addHandler(handler)
    return logger


def _route_label(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", request.url.path)


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def record_request(method: str, route: str, status: int, duration_seconds: float) -> None:
    with _metrics_lock:
        _request_counts[(method, route, str(status))] += 1
        _request_latency_sum[(method, route)] += duration_seconds


def prometheus_text() -> str:
    lines = [
        "# HELP http_requests_total Total HTTP requests handled by the API.",
        "# TYPE http_requests_total counter",
    ]
    with _metrics_lock:
        for (method, route, status), count in sorted(_request_counts.items()):
            lines.append(
                f'http_requests_total{{method="{_escape_label(method)}",route="{_escape_label(route)}",status="{status}"}} {count}'
            )
        lines.extend(
            [
                "# HELP http_request_duration_seconds_sum Cumulative HTTP request duration.",
                "# TYPE http_request_duration_seconds_sum counter",
            ]
        )
        for (method, route), total in sorted(_request_latency_sum.items()):
            lines.append(
                f'http_request_duration_seconds_sum{{method="{_escape_label(method)}",route="{_escape_label(route)}"}} {total:.6f}'
            )
    return "\n".join(lines) + "\n"


async def observe_request(request: Request, call_next, logger: logging.Logger) -> Response:
    request_id = request.headers.get("X-Request-ID") or uuid4().hex
    token = _request_id.set(request_id)
    started = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        duration = time.perf_counter() - started
        route = _route_label(request)
        record_request(request.method, route, status, duration)
        logger.info(
            "request_complete",
            extra={
                "request_id": request_id,
                "http_method": request.method,
                "http_route": route,
                "http_status": status,
                "duration_ms": round(duration * 1000, 2),
            },
        )
        _request_id.reset(token)
