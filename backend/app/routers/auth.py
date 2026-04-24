"""Auth router — registration, login, verification, password reset, user info."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    ForgotPasswordRequest, LoginRequest, RefreshRequest, RegisterRequest,
    ResetPasswordRequest, TokenResponse, UserOut, VerifyEmailRequest,
)
from app.services.auth_service import (
    authenticate_user, create_access_token, create_refresh_token,
    decode_token, get_current_user, initiate_password_reset,
    register_user, reset_password, verify_email,
)
from app.services.alert_service import send_verification_email, send_reset_email
from app.services.audit_service import log_action
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account. Sends verification email if SMTP is configured."""
    user = await register_user(req.email, req.password, db)
    
    # Send verification email (non-blocking) only if user is not already verified
    if not user.is_verified:
        await send_verification_email(user.email, user.verification_token)
    
    await log_action(db, user.id, "user", user.id, "registered")
    return user


@router.post("/verify-email")
async def verify(req: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    """Verify email address with token from verification email."""
    user = await verify_email(req.token, db)
    await log_action(db, user.id, "user", user.id, "email_verified")
    return {"message": "Email verified successfully. You can now log in."}


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await authenticate_user(req.email, req.password, db)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not user.is_verified:
            raise HTTPException(status_code=403, detail="Email not verified. Check your inbox for the verification link.")
        return TokenResponse(
            access_token=create_access_token(str(user.id), user.role.value),
            refresh_token=create_refresh_token(str(user.id)),
        )
    except Exception as e:
        import traceback
        error_msg = f"INTERNAL LOGIN ERROR: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Initiate password reset. Sends reset email if account exists."""
    token = await initiate_password_reset(req.email, db)
    if token:
        await send_reset_email(req.email, token)
    # Always return success to avoid email enumeration
    return {"message": "If an account with that email exists, a reset link has been sent."}


@router.post("/reset-password")
async def do_reset_password(req: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Reset password using token from reset email."""
    await reset_password(req.token, req.new_password, db)
    return {"message": "Password reset successfully. You can now log in."}


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(req.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    from sqlalchemy import select
    import uuid
    result = await db.execute(select(User).where(User.id == uuid.UUID(payload["sub"])))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role.value),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user
