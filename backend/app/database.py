import os
from google.cloud.sql.connector import Connector
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME", "playshield-db")
INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME", "playshield-ai:us-central1:playshield-db")

Base = declarative_base()

async def getconn():
    # Instantiate inside the function to lock to the current event loop.
    connector = Connector()
    conn = await connector.connect_async(
        INSTANCE_CONNECTION_NAME,
        "asyncpg",
        user=DB_USER,
        password=DB_PASS,
        db=DB_NAME,
    )
    return conn

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

async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
