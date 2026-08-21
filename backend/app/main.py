from fastapi import FastAPI

from backend.app.api.health import router as health_router


app = FastAPI(
    title="外规解读智能体工作台 API",
    version="0.1.0",
    description="Step 6 engineering scaffold; regulatory skills are added in later steps.",
)
app.include_router(health_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "regulatory-interpretation-api",
        "status": "scaffold",
        "docs": "/docs",
    }
