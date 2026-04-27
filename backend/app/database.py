import os
from google.cloud.sql.connector import Connector
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# --- 1. CONFIGURATION ---
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME", "playshield-db")
INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME", "playshield-ai:us-central1:playshield-db")

# --- 2. BASE MODEL ---
Base = declarative_base()

# --- 3. CLOUD SQL CONNECTOR (LAZY LOADED) ---
_connector = None

async def getconn():
    global _connector
    if _connector is None:
        _connector = Connector()
        
    conn = await _connector.connect_async(
        INSTANCE_CONNECTION_NAME,
        "asyncpg",
        user=DB_USER,
        password=DB_PASS,
        db=DB_NAME,
    )
    return conn

# --- 4. ASYNC ENGINE & POOLING ---
engine = create_async_engine(
    "postgresql+asyncpg://",
    async_creator=getconn,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
)

# --- 5. SESSION FACTORY & ALIASES ---
SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)
async_session_factory = SessionLocal  # Alias for services

# --- 6. DEPENDENCY INJECTION ---
async def get_db():
    """Dependency to provide a database session to FastAPI routers."""
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
