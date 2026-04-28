import urllib.parse
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# 1. URL-encode the password to handle the '@' symbol safely
SAFE_PASS = urllib.parse.quote_plus("Th0usan@")

# 2. Hardwire the exact connection string to your true database instance
DB_URL = f"postgresql+asyncpg://postgres:{SAFE_PASS}@/postgres?host=/cloudsql/playshield-ai:us-central1:playshield-sql"

# 3. Create Engine with zero local fallbacks
engine = create_async_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)
async_session_factory = SessionLocal

class Base(DeclarativeBase):
    pass

async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
