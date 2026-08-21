from fastapi import FastAPI

from backend.app.api.crud import router as crud_router
from backend.app.api.health import router as health_router


app = FastAPI(
    title="外规解读智能体工作台 API",
    version="0.1.0",
    description="外规解读智能体工作台的数据服务基础 API。",
)
app.include_router(health_router)
app.include_router(crud_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "regulatory-interpretation-api",
        "status": "data-api",
        "docs": "/docs",
    }
