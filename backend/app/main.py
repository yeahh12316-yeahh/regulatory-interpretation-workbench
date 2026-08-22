from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from backend.app.api.crud import router as crud_router
from backend.app.api.health import router as health_router
from backend.app.api.auth import router as auth_router
from backend.app.api.organization import router as organization_router
from backend.app.api.ingest import router as ingest_router
from backend.app.api.pipeline import router as pipeline_router
from backend.app.api.review import router as review_router
from backend.app.api.comparison import router as comparison_router
from backend.app.api.content_package import router as content_package_router
from backend.app.api.workflow import router as workflow_router
from backend.app.core.config import get_settings
from backend.app.observability import configure_logging, observe_request, prometheus_text


settings = get_settings()
http_logger = configure_logging(settings.log_format.lower() == "json")

app = FastAPI(
    title="外规解读智能体工作台 API",
    version="0.1.0",
    description="外规解读智能体工作台的数据服务基础 API。",
)
allowed_origins = [origin.strip().rstrip("/") for origin in settings.web_origin.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(lambda request, call_next: observe_request(request, call_next, http_logger))
app.include_router(health_router)
app.include_router(crud_router)
app.include_router(auth_router)
app.include_router(organization_router)
app.include_router(ingest_router)
app.include_router(pipeline_router)
app.include_router(review_router)
app.include_router(comparison_router)
app.include_router(content_package_router)
app.include_router(workflow_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "regulatory-interpretation-api",
        "status": "data-api",
        "docs": "/docs",
    }


@app.get("/metrics", include_in_schema=False, response_class=PlainTextResponse)
def metrics() -> str:
    if not settings.prometheus_enabled:
        raise HTTPException(status_code=404, detail="metrics disabled")
    return prometheus_text()
