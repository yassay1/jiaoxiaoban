"""Run the FastAPI backend with a Windows-compatible asyncio loop."""

from __future__ import annotations

import argparse
import os
import asyncio
import selectors
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def configure_local_compose_env() -> None:
    """Use this project's docker-compose database settings for local runs.

    Some Windows machines have global POSTGRES_* variables from another
    PostgreSQL install. Those make the app try user "postgres" instead of the
    compose user "campus_agent". This launcher is specifically for the local
    compose stack, so it pins the expected values.
    """
    values = {
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "campus_agent",
        "POSTGRES_USER": "campus_agent",
        "POSTGRES_PASSWORD": "campus_agent_dev",
    }
    for key, value in values.items():
        os.environ[key] = value
        os.environ[key.lower()] = value
    # psycopg/libpq and LangGraph can also read global DB variables.
    # Clear conflicting globals, then pin LangGraph to the same compose DB.
    for key in ("PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD"):
        os.environ.pop(key, None)
        os.environ.pop(key.lower(), None)
    os.environ["LANGGRAPH_CHECKPOINT_DB_URI"] = (
        "postgresql://campus_agent:campus_agent_dev@localhost:5432/campus_agent"
    )
    os.environ["langgraph_checkpoint_db_uri"] = os.environ["LANGGRAPH_CHECKPOINT_DB_URI"]


configure_local_compose_env()

import uvicorn


async def serve(host: str, port: int, reload: bool) -> None:
    from app.main import app
    if reload:
        raise SystemExit("--reload is not supported by scripts/run_backend.py on Windows. Restart the command after changes.")
    config = uvicorn.Config(app, host=host, port=port)
    server = uvicorn.Server(config)
    await server.serve()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Campus Agent backend")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    if sys.platform == "win32":
        loop_factory = lambda: asyncio.SelectorEventLoop(selectors.SelectSelector())
        asyncio.run(serve(args.host, args.port, args.reload), loop_factory=loop_factory)
    else:
        asyncio.run(serve(args.host, args.port, args.reload))


if __name__ == "__main__":
    main()
