"""Database engine and session management using Google Cloud SQL Connector."""

import asyncio
import os
from google.cloud.sql.connector import Connector
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()

# Connection details from environment
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME", "playshield-db")
INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME", "playshield-ai:us-central1:playshield-db")

# Initialize globally and tie it to the active loop
connector = None
connector_loop = None

async def getconn():
    """Create a new asyncpg connection using the Cloud SQL Connector."""
    global connector, connector_loop
    current_loop = asyncio.get_running_loop()

    # Recreate connector when loop changes (e.g., Cloud Run worker lifecycle)
    if connector is None or connector_loop is not current_loop:
        connector = Connector()
        connector_loop = current_loop

    conn = await connector.connect_async(
        INSTANCE_CONNECTION_NAME,
        "asyncpg",
        user=DB_USER,
        password=DB_PASS,
        db=DB_NAME,
    )
    return conn

# Create engine strictly using the async_creator hook for production
if DB_PASS and INSTANCE_CONNECTION_NAME:
    engine = create_async_engine(
        "postgresql+asyncpg://",
        async_creator=getconn,
        echo=settings.DEBUG,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
    )
else:
    # Fallback for local development ONLY
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,
    )

# Use sessionmaker with AsyncSession as requested
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Alias for backward compatibility
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
