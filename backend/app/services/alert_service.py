"""Alert service — transactional email notifications (verification, reset, detection alerts)."""

import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx
import structlog

from app.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


# ─── Email Sending ──────────────────────────────────────

async def _send_email(to: str, subject: str, html_body: str) -> bool:
    """Send an HTML email via SMTP."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP not configured, skipping email", to=to, subject=subject)
        return False
    try:
        msg = MIMEMultipart()
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        logger.info("Email sent", to=to, subject=subject)
        return True
    except Exception as e:
        logger.error("Email send failed", to=to, error=str(e))
        return False


# ─── Transactional Emails ──────────────────────────────

BRAND = "PlayShield AI"
BRAND_COLOR = "#6366f1"

EMAIL_WRAPPER = """
<div style="font-family: 'Inter', -apple-system, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
  <div style="text-align: center; margin-bottom: 32px;">
    <div style="display: inline-block; background: linear-gradient(135deg, #6366f1, #8b5cf6); padding: 12px 16px; border-radius: 12px; margin-bottom: 12px;">
      <span style="color: white; font-size: 20px; font-weight: 700;">🛡️ {brand}</span>
    </div>
  </div>
  <div style="background: #111827; border: 1px solid #1e293b; border-radius: 16px; padding: 32px; color: #f1f5f9;">
    {content}
  </div>
  <p style="text-align: center; color: #64748b; font-size: 12px; margin-top: 24px;">
    © 2026 {brand}. Content Protection Platform.
  </p>
</div>
"""


async def send_verification_email(email: str, token: str) -> bool:
    """Send email verification link to new user."""
    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    content = f"""
    <h2 style="color: #f1f5f9; margin-bottom: 16px;">Verify your email</h2>
    <p style="color: #94a3b8; margin-bottom: 24px;">
      Welcome to {BRAND}! Click the button below to verify your email address and activate your account.
    </p>
    <div style="text-align: center; margin: 32px 0;">
      <a href="{verify_url}"
         style="background: linear-gradient(135deg, {BRAND_COLOR}, #8b5cf6); color: white; padding: 14px 32px; border-radius: 10px; text-decoration: none; font-weight: 600; font-size: 16px;">
        Verify Email
      </a>
    </div>
    <p style="color: #64748b; font-size: 13px;">
      Or copy this link: <a href="{verify_url}" style="color: {BRAND_COLOR};">{verify_url}</a>
    </p>
    <p style="color: #64748b; font-size: 12px; margin-top: 24px;">
      If you didn't create an account, please ignore this email.
    </p>
    """
    html = EMAIL_WRAPPER.format(brand=BRAND, content=content)
    return await _send_email(email, f"[{BRAND}] Verify your email", html)


async def send_reset_email(email: str, token: str) -> bool:
    """Send password reset link."""
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    content = f"""
    <h2 style="color: #f1f5f9; margin-bottom: 16px;">Reset your password</h2>
    <p style="color: #94a3b8; margin-bottom: 24px;">
      We received a request to reset your password. Click the button below to choose a new one.
    </p>
    <div style="text-align: center; margin: 32px 0;">
      <a href="{reset_url}"
         style="background: linear-gradient(135deg, {BRAND_COLOR}, #8b5cf6); color: white; padding: 14px 32px; border-radius: 10px; text-decoration: none; font-weight: 600; font-size: 16px;">
        Reset Password
      </a>
    </div>
    <p style="color: #64748b; font-size: 13px;">
      This link expires in 1 hour.
    </p>
    <p style="color: #64748b; font-size: 12px; margin-top: 24px;">
      If you didn't request a reset, please ignore this email.
    </p>
    """
    html = EMAIL_WRAPPER.format(brand=BRAND, content=content)
    return await _send_email(email, f"[{BRAND}] Reset your password", html)


async def send_detection_notification(
    user_email: str, case_id: str, asset_title: str, confidence: float, source_url: str
) -> bool:
    """Send detection alert to asset owner."""
    case_url = f"{settings.FRONTEND_URL}/cases/{case_id}"
    pct = f"{confidence * 100:.0f}%"
    content = f"""
    <h2 style="color: #f1f5f9; margin-bottom: 16px;">🚨 Potential IP Violation Detected</h2>
    <p style="color: #94a3b8; margin-bottom: 24px;">
      We detected a potential unauthorized use of your protected content.
    </p>
    <div style="background: #1a2236; border: 1px solid #1e293b; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
      <table style="width: 100%; color: #94a3b8; font-size: 14px;">
        <tr><td style="padding: 6px 0; color: #64748b;">Asset:</td><td style="padding: 6px 0; font-weight: 600; color: #f1f5f9;">{asset_title}</td></tr>
        <tr><td style="padding: 6px 0; color: #64748b;">Confidence:</td><td style="padding: 6px 0;"><span style="background: {'#ef444420' if confidence >= 0.85 else '#f59e0b20'}; color: {'#f87171' if confidence >= 0.85 else '#fbbf24'}; padding: 4px 12px; border-radius: 8px; font-weight: 700;">{pct}</span></td></tr>
        <tr><td style="padding: 6px 0; color: #64748b;">Source:</td><td style="padding: 6px 0;"><a href="{source_url}" style="color: {BRAND_COLOR};">{source_url[:60]}...</a></td></tr>
      </table>
    </div>
    <div style="text-align: center; margin: 24px 0;">
      <a href="{case_url}"
         style="background: linear-gradient(135deg, {BRAND_COLOR}, #8b5cf6); color: white; padding: 14px 32px; border-radius: 10px; text-decoration: none; font-weight: 600; font-size: 16px;">
        Review Case
      </a>
    </div>
    """
    html = EMAIL_WRAPPER.format(brand=BRAND, content=content)
    return await _send_email(
        user_email,
        f"[{BRAND}] IP Violation Detected — {asset_title} ({pct} confidence)",
        html,
    )


# ─── Slack Alerts ──────────────────────────────────────

async def send_slack_alert(message: str, case_data: dict | None = None) -> bool:
    """Send alert to Slack webhook."""
    if not settings.SLACK_WEBHOOK_URL or settings.SLACK_WEBHOOK_URL.startswith("https://hooks.slack.com/services/YOUR"):
        return False
    payload = {
        "text": message,
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": f"🛡️ {BRAND} Alert"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": message}},
        ],
    }
    if case_data:
        payload["blocks"].append({
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Confidence:* {case_data.get('confidence', 'N/A')}"},
                {"type": "mrkdwn", "text": f"*Asset:* {case_data.get('asset_title', 'N/A')}"},
                {"type": "mrkdwn", "text": f"*Source:* {case_data.get('source_url', 'N/A')}"},
            ],
        })
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(settings.SLACK_WEBHOOK_URL, json=payload, timeout=10)
            return resp.status_code == 200
    except Exception:
        return False


async def send_email_alert(subject: str, body: str, to: str | None = None) -> bool:
    """Send email alert via SMTP (legacy admin alerts)."""
    return await _send_email(to or settings.ALERT_EMAIL_TO, subject, body)


async def alert_high_confidence_detection(case_data: dict):
    """Send alerts for high-confidence detections (admin Slack + email)."""
    conf = case_data.get("confidence", 0)
    asset = case_data.get("asset_title", "Unknown")
    source = case_data.get("source_url", "Unknown")
    msg = (
        f"🚨 *High-Confidence Match Detected*\n"
        f"Asset: {asset}\nSource: {source}\n"
        f"Confidence: {conf:.0%}\nA new case has been created for review."
    )
    await send_slack_alert(msg, case_data)
