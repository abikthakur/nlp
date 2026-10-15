"""
FastAPI application entry point.
Serves the chat API and the static frontend from app/static/.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.routers.chat import router as chat_router

app = FastAPI(
    title="SportsBot",
    description="A domain-specific sports chatbot powered by Google Gemini.",
    version="1.0.0",
)

# ── API routes ─────────────────────────────────────────────────────────────────
app.include_router(chat_router)

# ── Static files (frontend) ────────────────────────────────────────────────────
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def root() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "SportsBot"}
