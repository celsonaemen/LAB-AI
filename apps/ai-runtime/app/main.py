from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from app.api.knowledge import router as knowledge_router
from app.rag.store import database_ready
from contextlib import asynccontextmanager
from app.api.executions import router as executions_router
from app.api.mcp_tools import router as mcp_tools_router
from app.executions.worker import start_worker
from app.executions.repository import database_ready as executions_ready
import os
from app.security import ServiceAuthentication


@asynccontextmanager
async def lifespan(app):
    stop, thread = start_worker()
    yield
    stop.set()
    if thread:
        thread.join(timeout=1)


app = FastAPI(title="AEGIS AI Runtime", version="0.1.0", lifespan=lifespan)
app.add_middleware(ServiceAuthentication)
app.include_router(knowledge_router)
app.include_router(executions_router)
app.include_router(mcp_tools_router)


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "ai-runtime"
    provider: str = "deterministic"


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(provider=os.getenv('AEGIS_LLM_PROVIDER', 'deterministic'))


@app.get("/health/ready")
def readiness():
    if not database_ready() or not executions_ready():
        return JSONResponse(status_code=503, content={"status": "unavailable", "service": "ai-runtime"})
    return {"status": "ok", "service": "ai-runtime"}
