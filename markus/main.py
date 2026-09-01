"""
Markus AI — Main Entry Point

FastAPI server with REST API and WebSocket support.
Serves the backend for the Markus AI platform.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Add markus directory to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Patch bcrypt.__about__ for passlib compatibility
try:
    import bcrypt  # type: ignore
    if not hasattr(bcrypt, "__about__"):
        bcrypt.__about__ = type("about", (), {"__version__": getattr(bcrypt, "__version__", "4.0.0")})()
except Exception:
    pass

from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config.settings import settings
from application.routes import (
    chat, agents, models, system,
    workflows, plugins, files, search, settings as settings_route, projects,
    speech, vision, perception,
)
from application.websocket import ws_manager

# ── Logging Setup ──
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s │ %(name)-28s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("markus")


# ── Lifespan Context Manager (replaces deprecated @app.on_event) ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("=" * 60)
    logger.info("  MARKUS AI — Intelligent Multi-Agent Platform")
    logger.info("=" * 60)
    logger.info(f"  Environment: {settings.env}")
    logger.info(f"  API Docs:    http://localhost:{settings.port}/api/docs")
    logger.info(f"  WebSocket:   ws://localhost:{settings.port}/ws")
    logger.info(f"  OmniRoute:   {settings.omniroute.base_url}")
    logger.info("=" * 60)

    # Check OmniRoute connection
    from core.model_router import model_router
    status = await model_router.check_gateway_status()
    if status["connected"]:
        logger.info(f"  OmniRoute: CONNECTED ({status['model_count']} models)")
    else:
        logger.warning("  OmniRoute: NOT CONNECTED (running in offline mode)")

    # Ensure data directories exist
    for dir_path in ["./data", "./data/documents", "./data/vector_store", "./logs"]:
        Path(dir_path).mkdir(parents=True, exist_ok=True)

    yield

    # Shutdown
    from ai.omniroute_client import omniroute_client
    await omniroute_client.close()
    logger.info("Markus AI shutdown complete")


# ── FastAPI App ──
app = FastAPI(
    title="Markus AI",
    description="Intelligent Multi-Agent Development Platform",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# ── CORS (allow frontend dev server) ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register API Routes ──
app.include_router(chat.router)
app.include_router(agents.router)
app.include_router(models.router)
app.include_router(system.router)
app.include_router(workflows.router)
app.include_router(plugins.router)
app.include_router(files.router)
app.include_router(search.router)
app.include_router(settings_route.router)
app.include_router(projects.router)
app.include_router(speech.router)
app.include_router(vision.router)
app.include_router(perception.router)


# ── WebSocket Endpoint ──
@app.websocket("/ws")
@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # Handle incoming WebSocket messages from the frontend
            msg_type = data.get("type", "")
            if msg_type == "ping":
                await ws_manager.send_personal(websocket, {"type": "pong"})
            elif msg_type == "set_state":
                from config.constants import AIState
                try:
                    state = AIState(data.get("state", "idle"))
                    await ws_manager.set_state(state)
                except ValueError:
                    pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)


# ── Health Check ──
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "Markus AI",
        "version": "0.1.0",
        "websocket_connections": ws_manager.connection_count,
    }


# ── Run ──
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
