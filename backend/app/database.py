"""Database engine and session management."""

import os
import urllib.parse
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME", "playshield-db")
INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME")

if DB_PASS and INSTANCE_CONNECTION_NAME:
    # URL-encode the password to safely handle special characters like '@'
    SAFE_PASS = urllib.parse.quote_plus(DB_PASS)
    
    # Connect via Cloud Run's native Unix socket sidecar
    DB_URL = f"postgresql+asyncpg://{DB_USER}:{SAFE_PASS}@/{DB_NAME}?host=/cloudsql/{INSTANCE_CONNECTION_NAME}"
    
    engine = create_async_engine(
        DB_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
else:
    # Fallback for local development ONLY
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,
    )

# Use sessionmaker with AsyncSession
SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)

# Alias for backward compatibility (Fixes the Revision 39 Crash)
async_session_factory = SessionLocal

class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass

async def get_db() -> AsyncSession:
    """Yield an async database session."""
    try:
        async with SessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                print(f"CRITICAL: DATABASE EXCEPTION: {e}")
                raise
    except Exception as global_e:
        print(f"CRITICAL: FAILED TO CREATE DATABASE SESSION: {global_e}")
        raise