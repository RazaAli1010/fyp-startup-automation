"""Legal Document Generator — OpenAI-powered (GPT-4.1), jurisdiction-aware.

Uses the centralized OpenAI client (`call_openai_chat`) for single-stage generation.
JSON response format is enforced at the client level. Validates response shape
and returns a LegalDocumentOutput.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from ...services.openai_client import call_openai_chat_async, validate_required_keys
from .prompts import SYSTEM_PROMPT, PROMPT_BUILDERS
from .rules import resolve_jurisdiction, validate_document_type
from .schema import LegalDocumentOutput

#legal document generator
_LEGAL_MAX_TOKENS = 4000
_MANDATORY_DISCLAIMER = (
    "This document is generated for informational purposes only "
    "and does not constitute legal advice."
)
_REQUIRED_KEYS = [
    "document_type",
    "jurisdiction",
    "governing_law",
    "disclaimer",
    "sections",
]


async def generate_legal_document(
    *,
    document_type: str,
    company_name: str,
    industry: str,
    geography: str,
    founder_count: int = 2,
    effective_date: Optional[str] = None,
) -> LegalDocumentOutput:
    """Generate a legal document using OpenAI with jurisdiction-aware prompts.

    Parameters
    ----------
    document_type : str
        One of: nda, founder_agreement, privacy_policy, terms_of_service
    company_name : str
        The legal name of the startup / company.
    industry : str
        The industry vertical.
    geography : str
        Country / jurisdiction for governing law.
    founder_count : int
        Number of founders (used for Founder Agreement).
    effective_date : str or None
        Effective date string. Auto-generated if None.

    Returns
    -------
    LegalDocumentOutput

    Raises
    ------
    ValueError
        If document_type is invalid.
    RuntimeError
        If OpenAI fails after retries or returns invalid JSON.
    """
    # ── Validate document type ──────────────────────────────────
    canonical_type = validate_document_type(document_type)
    print(f"⚖️ [LEGAL] Generating {canonical_type} for company={company_name}")

    # ── Resolve jurisdiction ────────────────────────────────────
    jurisdiction = resolve_jurisdiction(geography)
    print(f"🌍 [LEGAL] Jurisdiction detected: {jurisdiction.country}")
    print(f"🌍 [LEGAL] Governing law: {jurisdiction.governing_law}")
    if jurisdiction.requires_gdpr:
        print("🌍 [LEGAL] GDPR compliance required")

    # ── Effective date ──────────────────────────────────────────
    if not effective_date:
        effective_date = datetime.utcnow().strftime("%B %d, %Y")

    # ── Build prompt ────────────────────────────────────────────
    prompt_builder = PROMPT_BUILDERS.get(canonical_type)
    if prompt_builder is None:
        raise ValueError(f"No prompt builder for document type: {canonical_type}")

    # Build kwargs based on document type
    prompt_kwargs = {
        "company_name": company_name,
        "industry": industry,
        "jurisdiction": jurisdiction.country,
        "governing_law": jurisdiction.governing_law,
        "effective_date": effective_date,
    }

    # Add type-specific kwargs
    if canonical_type == "Founder Agreement":
        prompt_kwargs["founder_count"] = founder_count
    else:
        prompt_kwargs["requires_gdpr"] = jurisdiction.requires_gdpr

    user_prompt = prompt_builder(**prompt_kwargs)

    # ── Call OpenAI ─────────────────────────────────────────────
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    print(f"🧠 [LEGAL] Calling OpenAI (max_tokens={_LEGAL_MAX_TOKENS})")
    result = await call_openai_chat_async(
        messages=messages,
        max_completion_tokens=_LEGAL_MAX_TOKENS,
    )

    if result is None:
        raise RuntimeError(
            "OpenAI failed to generate legal document after retries. "
            "Please try again."
        )

    # ── Validate response keys ──────────────────────────────────
    if not validate_required_keys(result, _REQUIRED_KEYS, context="LEGAL"):
        raise RuntimeError(
            "OpenAI returned an incomplete legal document (missing required fields). "
            "Please try again."
        )

    # ── Validate sections shape ─────────────────────────────────
    sections = result.get("sections", [])
    if not isinstance(sections, list) or len(sections) == 0:
        raise RuntimeError(
            "OpenAI returned empty or invalid sections array. Please try again."
        )

    for i, section in enumerate(sections):
        if not isinstance(section, dict) or "title" not in section or "content" not in section:
            raise RuntimeError(
                f"Section {i} is malformed (missing 'title' or 'content'). Please try again."
            )

    print(f"🧠 [LEGAL] OpenAI generation successful — {len(sections)} sections")

    # ── Assemble output ─────────────────────────────────────────
    # Ensure disclaimer is always the mandatory one
    customization_notes = result.get("customization_notes", [])
    if not isinstance(customization_notes, list):
        customization_notes = []

    # Add jurisdiction notes from rules
    customization_notes.extend(jurisdiction.legal_notes)

    legal_risk_notes = result.get("legal_risk_notes", [])
    if not isinstance(legal_risk_notes, list):
        legal_risk_notes = []

    output = LegalDocumentOutput(
        document_type=canonical_type,
        jurisdiction=jurisdiction.country,
        governing_law=jurisdiction.governing_law,
        disclaimer=_MANDATORY_DISCLAIMER,
        sections=sections,
        customization_notes=customization_notes,
        legal_risk_notes=legal_risk_notes,
        generated_at=datetime.utcnow(),
    )

    print(f"✅ [LEGAL] {canonical_type} generated for {jurisdiction.country}")
    return output
