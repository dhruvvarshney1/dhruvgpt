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

# ── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ─────────────────────────────────────────────────────────────────
app.include_router(chat.router)
app.include_router(conversations.router)


# ── Health check ────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Health check endpoint for Render."""
    return {"status": "ok"}
