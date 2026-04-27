"""PlayShield AI — FastAPI Main Application."""

import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, assets, cases, scan, alerts, audit, dashboard, notifications, account
from app.services.detection_service import load_faiss_index

settings = get_settings()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    logger.info("Starting PlayShield AI", version=settings.APP_VERSION)
    load_faiss_index()
    yield
    logger.info("Shutting down PlayShield AI")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered content protection platform — detect unauthorized reuse of protected media assets",
    lifespan=lifespan,
)

from fastapi import Request, Response

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex="https://.*playshieldai\.dev",
    allow_credentials=False, # Must be False for allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    logger.error("GLOBAL CRASH", error=str(exc), path=request.url.path)
    print(traceback.format_exc())
    return Response(
        status_code=500,
        content=f"Internal Server Error: {str(exc)}"
    )

@app.options("/{rest_of_path:path}")
async def preflight_handler(request: Request, rest_of_path: str):
    origin = request.headers.get("origin")
    headers = {
        "Access-Control-Allow-Origin": origin if origin in origins else origins[0],
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Credentials": "true",
    }
    return Response(status_code=200, headers=headers)


# Routers
app.include_router(auth.router)
app.include_router(assets.router)
app.include_router(cases.router)
app.include_router(scan.router)
app.include_router(alerts.router)
app.include_router(audit.router)
app.include_router(dashboard.router)
app.include_router(notifications.router)
app.include_router(account.router)


@app.get("/healthz")
async def healthz():
    """Health check endpoint."""
    from sqlalchemy import text

    db_status = "connected"
    redis_status = "connected"
    try:
        from app.database import engine

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"
    try:
        import redis as r

        rc = r.from_url(settings.REDIS_URL)
        rc.ping()
    except Exception:
        redis_status = "error"
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "db": db_status,
        "redis": redis_status,
    }


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8080)) # Cloud Run default is usually 8080
    uvicorn.run(app, host="0.0.0.0", port=port)
