"""
PostgreSQL Database Connection
"""
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

# Lazy initialization
engine: Optional[create_async_engine] = None
AsyncSessionLocal: Optional[async_sessionmaker] = None

# Base class for models
Base = declarative_base()


def get_engine():
    """Get or create database engine"""
    global engine
    if engine is None:
        from app.core.config.settings import settings
        db_url = settings.get_database_url()
        engine = create_async_engine(
            db_url.replace("postgresql://", "postgresql+asyncpg://"),
            echo=settings.DEBUG,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    return engine


def get_session_local():
    """Get or create session maker"""
    global AsyncSessionLocal
    if AsyncSessionLocal is None:
        AsyncSessionLocal = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return AsyncSessionLocal


async def init_db():
    """Initialize database"""
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connection"""
    global engine
    if engine:
        await engine.dispose()
        engine = None


async def get_db() -> AsyncSession:
    """Get database session"""
    async with get_session_local()() as session:
        yield session
