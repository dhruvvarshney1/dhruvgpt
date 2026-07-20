"""FastAPI application entry point.

Creates the app, adds CORS middleware, includes routers, and exposes a
health-check endpoint for Render.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import chat, conversations

app = FastAPI(
    title="LLM Chat Interface",
    description="A streaming chat API backed by NVIDIA's hosted inference API.",
    version="0.1.0",
)

import logging
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# ── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Ensure all unhandled exceptions return CORS headers and JSON detail."""
    logger.exception("Unhandled error processing %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"message": f"Server error: {exc}"},
    )

# ── Routers ─────────────────────────────────────────────────────────────────
app.include_router(chat.router)
app.include_router(conversations.router)


# ── Health check ────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Health check endpoint for Render."""
    return {"status": "ok"}
