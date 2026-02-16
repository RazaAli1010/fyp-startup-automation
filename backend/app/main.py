import logging
import os
import time
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

from .database import Base, engine, DATABASE_URL
from .routes.auth import router as auth_router
from .routes.ideas import router as ideas_router
from .routes.evaluation import router as evaluation_router
from .routes.pitch_deck import router as pitch_deck_router
from .routes.market_research import router as market_research_router
from .routes.mvp import router as mvp_router
from .routes.legal import router as legal_router

# Load environment variables from .env file
load_dotenv()


def _get_sqlite_path() -> str | None:
    """Extract the file path from a sqlite:/// URL, or None if not SQLite."""
    if DATABASE_URL.startswith("sqlite:///"):
        return DATABASE_URL.replace("sqlite:///", "", 1)
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Dev-mode DB reset ────────────────────────────────────────
    # Ensure data directory exists for SQLite
    db_path = _get_sqlite_path()
    if db_path:
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

    if os.getenv("ENV", "development") == "development":
        print("⚠️  Running in DEVELOPMENT mode — DB reset enabled")
        if db_path and os.path.exists(db_path):
            os.remove(db_path)
            print("🧹 [DB] Development DB reset")

    Base.metadata.create_all(bind=engine)
    print("✅ [DB] Tables ensured (fresh schema)")

    # Log Google OAuth status at startup
    from .services.google_oauth_config import log_google_oauth_status
    log_google_oauth_status()

    yield
    print("Shutting down StartBot API")


app = FastAPI(
    title="StartBot — Structured Startup Idea Intake",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


_cors_origins = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print(f"🌐 [CORS] Enabled for origins: {_cors_origins}")



# ── Request logging middleware ──────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    method = request.method
    path = request.url.path
    print(f"➡️  [REQ] {method} {path}")
    try:
        response = await call_next(request)
        elapsed = (time.time() - start) * 1000
        print(f"⬅️  [RES] {method} {path} → {response.status_code} ({elapsed:.0f}ms)")
        return response
    except Exception as exc:
        elapsed = (time.time() - start) * 1000
        print(f"❌ [ERR] {method} {path} → EXCEPTION ({elapsed:.0f}ms): {exc}")
        raise


app.include_router(auth_router)
app.include_router(ideas_router)
app.include_router(evaluation_router)
app.include_router(pitch_deck_router)
app.include_router(market_research_router)
app.include_router(mvp_router)
app.include_router(legal_router)

@app.get("/__cors_test")
def cors_test():
    return {"cors": "ok"}
@app.get(
    "/",
    summary="API Root",
    description="Welcome endpoint with API information",
    tags=["General"],
)
async def root():
    """Root endpoint with API information."""
    return {
        "name": "StartBot",
        "version": "1.0.0",
        "description": "Structured startup idea intake and storage",
        "docs": "/docs",
        "endpoints": {
            "submit_idea": "POST /ideas/ - Submit a structured startup idea",
            "health": "GET /health - Service health check",
        },
    }


@app.get(
    "/health",
    summary="Global Health Check",
    description="Check if the API server is running",
    tags=["General"],
)
async def health():
    """Global health check endpoint."""
    return {
        "status": "healthy",
        "service": "startbot",
        "version": "1.0.0",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        raise exc  # ⬅️ VERY IMPORTANT

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc)
            if os.getenv("DEBUG", "false").lower() == "true"
            else "An unexpected error occurred",
        },
    )



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("DEBUG", "true").lower() == "true",
    )

