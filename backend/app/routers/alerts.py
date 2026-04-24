"""Alerts router — test alert endpoints."""

from fastapi import APIRouter, Depends
from app.models import User
from app.services.auth_service import get_current_user
from app.services.alert_service import send_slack_alert, send_email_alert

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/test")
async def test_alerts(user: User = Depends(get_current_user)):
    """Send test alerts to verify configuration."""
    slack_ok = await send_slack_alert("🧪 Test alert from IP Guardian", {
        "confidence": "95%", "asset_title": "Test Asset", "source_url": "https://example.com",
    })
    email_ok = await send_email_alert(
        "[IP Guardian] Test Alert",
        "<h2>Test Alert</h2><p>This is a test alert from IP Guardian.</p>",
    )
    return {"slack": "sent" if slack_ok else "failed/not_configured",
            "email": "sent" if email_ok else "failed/not_configured"}
