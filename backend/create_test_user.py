import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, select
import uuid
from app.models import User, UserRole
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_test_user():
    db_url = os.getenv("DATABASE_URL")
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Check if user exists
        result = await session.execute(select(User).where(User.email == "new@test.com"))
        user = result.scalar_one_or_none()
        
        if user:
            print("User already exists.")
        else:
            print("Creating user...")
            user = User(
                id=uuid.uuid4(),
                email="new@test.com",
                password_hash=pwd_context.hash("12345678"),
                role=UserRole.USER,
                is_verified=True # Auto-verify for test
            )
            session.add(user)
            await session.commit()
            print("User created successfully.")

if __name__ == "__main__":
    asyncio.run(create_test_user())
