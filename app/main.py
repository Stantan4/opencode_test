"""
FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config.settings import settings
from app.database.redis import init_redis, close_redis
from app.database.postgresql import init_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    try:
        await init_db()
    except Exception as e:
        print(f"Database initialization skipped: {e}")
    try:
        await init_redis()
    except Exception as e:
        print(f"Redis initialization skipped: {e}")
    yield
    # Shutdown
    try:
        await close_db()
    except Exception:
        pass
    try:
        await close_redis()
    except Exception:
        pass


app = FastAPI(
    title="Account Risk Early Warning System",
    description="基于深度学习的社交媒体账号被盗风险预警系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Account Risk Early Warning System",
        "version": "1.0.0",
        "docs": "/docs"
    }
