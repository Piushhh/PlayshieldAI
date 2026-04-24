"""Gemini service — Vertex AI integration for rationale and draft generation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.config import get_settings

settings = get_settings()

LEGAL_DISCLAIMER = (
    "\n\n---\n⚠️ LEGAL DISCLAIMER: This is an AI-generated draft and requires "
    "human legal review before any action is taken. This document does not "
    "constitute legal advice.\n---"
)

DETERMINISTIC_TEMPLATE = """
TAKEDOWN NOTICE — DRAFT

To: Content Administrator
Re: Unauthorized Use of Protected Content

Dear Sir/Madam,

I am writing to notify you of the unauthorized use of content protected under
intellectual property law, identified on your platform.

ORIGINAL ASSET: {asset_title}
LICENSE: {license_type}
DETECTED AT: {source_url}
CONFIDENCE SCORE: {confidence:.0%}

SCORE BREAKDOWN:
- Perceptual Hash Similarity: {hash_score:.0%}
- Embedding Similarity: {embed_score:.0%}
- Risk Assessment: {risk_score:.0%}

I request the immediate removal of the infringing content and confirmation
of compliance within 48 hours.

This notice is made in good faith based on automated analysis.

{disclaimer}
"""


@dataclass
class GeminiGenerationResult:
    rationale: str
    draft_text: str
    model: str
    provider: str
    status: str
    is_incomplete: bool
    is_fallback: bool
    error_message: str | None = None
    incomplete_reason: str | None = None
    raw_response: dict[str, Any] | None = None


async def generate_case_content(case_data: dict[str, Any]) -> GeminiGenerationResult:
    """Generate rationale + takedown draft for a case."""
    try:
        payload = await _call_gemini(case_data)
        rationale = _compose_rationale(payload)
        draft_text = payload.get("draft_letter", "").strip()
        if not rationale or not draft_text:
            raise ValueError("Gemini returned incomplete structured content")
        if LEGAL_DISCLAIMER not in draft_text:
            draft_text = f"{draft_text}{LEGAL_DISCLAIMER}"
        return GeminiGenerationResult(
            rationale=rationale,
            draft_text=draft_text,
            model=settings.GEMINI_MODEL,
            provider="vertex_ai",
            status="ready",
            is_incomplete=False,
            is_fallback=False,
            raw_response=payload,
        )
    except Exception as exc:
        return GeminiGenerationResult(
            rationale=_deterministic_rationale(case_data),
            draft_text=_deterministic_draft(case_data),
            model="deterministic",
            provider="fallback_template",
            status="fallback",
            is_incomplete=True,
            is_fallback=True,
            error_message=str(exc),
            incomplete_reason=(
                "AI services are delayed or unavailable. A classic takedown template is "
                "available while review and export actions remain fully usable."
            ),
            raw_response={"fallback": True, "error": str(exc)},
        )


async def generate_takedown_draft(case_data: dict) -> tuple[str, str]:
    """Backwards-compatible draft generator used by older routes/tests."""
    result = await generate_case_content(case_data)
    return result.draft_text, result.model


async def _call_gemini(case_data: dict[str, Any]) -> dict[str, Any]:
    """Call Vertex AI Gemini and parse a structured JSON response."""
    import vertexai
    from vertexai.generative_models import GenerativeModel

    vertexai.init(project=settings.GCP_PROJECT_ID, location=settings.VERTEX_AI_LOCATION)
    model = GenerativeModel(settings.GEMINI_MODEL)

    prompt = f"""You are an expert trust-and-safety analyst helping a content protection platform.

Review the case context and return a single JSON object with exactly these keys:
- rationale_title: short string
- rationale_summary: short paragraph
- rationale_bullets: array of 3 to 5 concise bullet strings
- confidence_label: short label such as "High risk" or "Moderate concern"
- draft_letter: a complete takedown notice draft with concrete references to the asset, source, evidence, and next action
- incomplete_reason: null unless the provided evidence is missing something material

Case context:
{json.dumps(case_data, indent=2, default=str)}

Rules:
- Be factual, professional, and concise.
- Mention the confidence, hash, embedding, and risk evidence where relevant.
- Reference the discovery metadata and source URL.
- If "previous_rationale" or "current_draft" are provided in the context, treat this as a refinement request. Improve the existing content rather than starting from scratch, while maintaining the same structure.
- Do not surround the JSON with markdown fences.

"""

    response = await model.generate_content_async(prompt)
    response_text = getattr(response, "text", "") or ""
    if not response_text.strip():
        raise ValueError("Gemini returned an empty response")
    payload = _extract_json_object(response_text)
    payload["_raw_text"] = response_text
    return payload


def _extract_json_object(response_text: str) -> dict[str, Any]:
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        cleaned = cleaned.rsplit("```", 1)[0].strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Gemini response did not contain a JSON object")
    return json.loads(cleaned[start : end + 1])


def _compose_rationale(payload: dict[str, Any]) -> str:
    title = (payload.get("rationale_title") or "Why This Match?").strip()
    summary = (payload.get("rationale_summary") or "").strip()
    bullets = [str(item).strip() for item in payload.get("rationale_bullets") or [] if str(item).strip()]
    confidence_label = (payload.get("confidence_label") or "").strip()

    lines: list[str] = [title]
    if confidence_label:
        lines.append(confidence_label)
    if summary:
        lines.append(summary)
    lines.extend(f"- {bullet}" for bullet in bullets)
    return "\n".join(lines).strip()


def _deterministic_rationale(case_data: dict[str, Any]) -> str:
    detection = case_data.get("detection", {})
    asset = case_data.get("asset", {})
    discovery = case_data.get("discovery", {})
    evidence = case_data.get("evidence", {})

    lines = [
        "Why This Match?",
        "Fallback analysis",
        (
            f"The asset \"{asset.get('title', 'Unknown Asset')}\" was matched against "
            f"{discovery.get('source_url', 'an unknown source')} with "
            f"{detection.get('confidence', 0):.0%} confidence."
        ),
        f"- Hash similarity registered at {detection.get('hash_score', 0):.0%}.",
        f"- Embedding similarity registered at {detection.get('embed_score', 0):.0%}.",
        f"- Risk scoring registered at {detection.get('risk_score', 0):.0%}.",
    ]
    source_platform = discovery.get("platform")
    if source_platform:
        lines.append(f"- Discovery platform: {source_platform}.")
    if evidence:
        lines.append("- Evidence metadata was preserved for reviewer inspection.")
    return "\n".join(lines)


def _deterministic_draft(case_data: dict[str, Any]) -> str:
    """Fallback deterministic template when Gemini is unavailable."""
    detection = case_data.get("detection", {})
    asset = case_data.get("asset", {})
    discovery = case_data.get("discovery", {})

    return DETERMINISTIC_TEMPLATE.format(
        asset_title=asset.get("title", "Unknown Asset"),
        license_type=asset.get("license_type", "All Rights Reserved"),
        source_url=discovery.get("source_url", "Unknown URL"),
        confidence=detection.get("confidence", 0),
        hash_score=detection.get("hash_score", 0),
        embed_score=detection.get("embed_score", 0),
        risk_score=detection.get("risk_score", 0),
        disclaimer=LEGAL_DISCLAIMER,
    )
