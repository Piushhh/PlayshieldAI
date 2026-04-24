"""Database seed script — creates an initial admin user for production setup."""

import asyncio
import uuid
import os

from app.database import async_session_factory, engine, Base
from app.models import User, UserRole
from app.services.auth_service import hash_password

async def seed():
    """Seed the database with initial admin user."""
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        # Check if admin already exists
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.email == "admin@playshield.ai"))
        if result.scalar_one_or_none():
            print("✅ Admin user already exists. Skipping seed.")
            return

        # ── Users ───────────────────────────
        admin = User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            email="admin@playshield.ai",
            password_hash=hash_password("admin123"),
            role=UserRole.ADMIN,
            is_verified=True,
        )
        db.add(admin)
        await db.commit()
        
        print("✅ Database initialized successfully!")
        print("   Use the registration page to create your own account.")


if __name__ == "__main__":
    asyncio.run(seed())
