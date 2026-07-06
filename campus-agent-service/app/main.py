import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.api import health, assistant, agents, community_agent, safety, confirmations, rag, agent_runs, reminders, community, frontend_agents, memory
from app.config.settings import get_settings
from app.db.session import engine, Base
from app.db.extensions import ensure_postgres_extensions
from app.db import models  # noqa: F401

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("campus_agent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    conn_string = (
        f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )
    async with engine.begin() as conn:
        await ensure_postgres_extensions(conn)
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncPostgresSaver.from_conn_string(conn_string) as checkpointer:
        await checkpointer.setup()
        app.state.checkpointer = checkpointer
        logger.info("Checkpointer initialized and ready")
        yield
    logger.info("Checkpointer closed")


app = FastAPI(
    title="交小伴 Agent Service",
    description="校园生活智能体平台 - Agent 后端服务层。提供私人助理、专业 Agent、社区管理员 Agent 等 AI 能力。",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(assistant.router)
app.include_router(agents.router)
app.include_router(community_agent.router)
app.include_router(safety.router)
app.include_router(confirmations.router)
app.include_router(rag.router)
app.include_router(agent_runs.router)
app.include_router(reminders.router)
app.include_router(community.router)
app.include_router(frontend_agents.router)
app.include_router(memory.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {exc}")
    settings = get_settings()
    detail = str(exc) if settings.debug else "An unexpected error occurred"
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": detail},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


