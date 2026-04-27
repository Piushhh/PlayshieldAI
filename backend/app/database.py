import os
from google.cloud.sql.connector import Connector
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME", "playshield-db")
INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME")

# 1. Define the variable as None at the module level
_connector = None

async def getconn():
    global _connector
    # 2. Only initialize the Connector if it doesn't exist yet, 
    # ensuring it binds to the active worker's event loop.
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

# 3. Create the engine with pooling to prevent Cloud SQL exhaustion
engine = create_async_engine(
    "postgresql+asyncpg://",
    async_creator=getconn,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
)

SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)
async_session_factory = SessionLocal
Base = declarative_base()

async def get_db():
    """Dependency to provide a database session to FastAPI routers."""
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
