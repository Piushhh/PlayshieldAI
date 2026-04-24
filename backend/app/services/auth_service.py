"""Authentication service — JWT tokens, password hashing, RBAC, registration, verification, reset."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import (
    Asset, AuditLog, Case, Detection, Fingerprint, Notification, User, UserRole,
)

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash a plain-text password."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str, role: str) -> str:
    """Create a JWT access token."""
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """Create a JWT refresh token."""
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the current user from the JWT token."""
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def require_role(*roles: UserRole):
    """Dependency that enforces RBAC role checks."""

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {[r.value for r in roles]}",
            )
        return current_user

    return role_checker


async def authenticate_user(email: str, password: str, db: AsyncSession) -> Optional[User]:
    """Authenticate user by email and password."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


async def register_user(email: str, password: str, db: AsyncSession) -> User:
    """Register a new user with email verification token."""
    # Check if email exists
    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    verification_token = secrets.token_urlsafe(32)
    
    # Check if SMTP is configured to decide initial verification status
    is_verified = False
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        # If no email infra, auto-verify for convenience
        is_verified = True
        verification_token = None

    user = User(
        email=email,
        password_hash=hash_password(password),
        role=UserRole.USER,
        is_verified=is_verified,
        verification_token=verification_token,
    )
    db.add(user)
    await db.flush()
    return user


async def verify_email(token: str, db: AsyncSession) -> User:
    """Verify a user's email with the token."""
    result = await db.execute(
        select(User).where(User.verification_token == token)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    user.is_verified = True
    user.verification_token = None
    await db.flush()
    return user


async def initiate_password_reset(email: str, db: AsyncSession) -> Optional[str]:
    """Generate a password reset token. Returns the token or None if user not found."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        return None  # Don't reveal whether email exists

    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    await db.flush()
    return token


async def reset_password(token: str, new_password: str, db: AsyncSession) -> bool:
    """Reset password using a valid reset token."""
    result = await db.execute(
        select(User).where(
            User.reset_token == token,
            User.reset_token_expires > datetime.now(timezone.utc),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.password_hash = hash_password(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    await db.flush()
    return True


async def delete_user_account(user_id: uuid.UUID, db: AsyncSession) -> bool:
    """GDPR-style cascade deletion of user and all associated data."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return False

    # Get user's asset IDs for cascade
    asset_result = await db.execute(select(Asset.id).where(Asset.owner_id == user_id))
    asset_ids = [row[0] for row in asset_result.all()]

    if asset_ids:
        # Delete detections linked to user's assets
        det_result = await db.execute(
            select(Detection.id).where(Detection.asset_id.in_(asset_ids))
        )
        det_ids = [row[0] for row in det_result.all()]

        if det_ids:
            # Delete cases linked to those detections
            await db.execute(delete(Case).where(Case.detection_id.in_(det_ids)))
            # Delete the detections
            await db.execute(delete(Detection).where(Detection.id.in_(det_ids)))

        # Delete fingerprints
        await db.execute(delete(Fingerprint).where(Fingerprint.asset_id.in_(asset_ids)))
        # Delete assets
        await db.execute(delete(Asset).where(Asset.owner_id == user_id))

    # Delete notifications
    await db.execute(delete(Notification).where(Notification.user_id == user_id))

    # Delete audit logs (actor)
    await db.execute(delete(AuditLog).where(AuditLog.actor_user_id == user_id))

    # Delete user
    await db.execute(delete(User).where(User.id == user_id))
    await db.flush()
    return True
