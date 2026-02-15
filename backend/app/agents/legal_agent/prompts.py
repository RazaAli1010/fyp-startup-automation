"""Prompt templates for the Legal Document Generator (GPT-4.1).

System + User prompt separation. Output is always valid JSON.
JSON enforcement is handled by response_format in the centralized openai_client.
"""

from __future__ import annotations

SYSTEM_PROMPT = """You are a professional startup legal document drafter.

ROLE:
- You generate structured legal documents for startups.
- You adapt documents based on the specified jurisdiction and governing law.
- You use professional, clear legal language appropriate for the jurisdiction.
- You NEVER give legal advice — every document includes a mandatory disclaimer.

OUTPUT FORMAT:
You MUST respond with a single JSON object. No markdown, no explanation, no prose.

The JSON object MUST have these exact keys:
{
  "document_type": "<string>",
  "jurisdiction": "<string>",
  "governing_law": "<string>",
  "disclaimer": "This document is generated for informational purposes only and does not constitute legal advice.",
  "sections": [
    {"title": "<section title>", "content": "<section content>"}
  ],
  "customization_notes": ["<note1>", "<note2>"],
  "legal_risk_notes": ["<risk1>", "<risk2>"]
}

RULES:
1. Every document MUST include the disclaimer exactly as shown above.
2. Sections must be ordered logically for the document type.
3. Each section must have both "title" and "content" keys.
4. Content must be professional legal text, not placeholder text.
5. Adapt legal phrasing, governing law references, and compliance requirements to the specified jurisdiction.
6. For GDPR jurisdictions, include data protection clauses in Privacy Policies.
7. Return ONLY the JSON object. No surrounding text."""


def build_nda_prompt(
    *,
    company_name: str,
    industry: str,
    jurisdiction: str,
    governing_law: str,
    requires_gdpr: bool,
    effective_date: str,
) -> str:
    """Build user prompt for Non-Disclosure Agreement."""
    gdpr_note = ""
    if requires_gdpr:
        gdpr_note = "\n- Include GDPR-compliant data handling clause for any personal data exchanged."

    return f"""Generate a Non-Disclosure Agreement (NDA) with the following parameters:

COMPANY: {company_name}
INDUSTRY: {industry}
JURISDICTION: {jurisdiction}
GOVERNING LAW: {governing_law}
EFFECTIVE DATE: {effective_date}

REQUIREMENTS:
- Mutual NDA (both parties protected)
- Include: definitions, obligations, exclusions, term, remedies, governing law
- Professional tone appropriate for {jurisdiction}
- Dispute resolution clause referencing {governing_law}{gdpr_note}

Generate the complete NDA as a JSON object with sections array."""


def build_founder_agreement_prompt(
    *,
    company_name: str,
    industry: str,
    jurisdiction: str,
    governing_law: str,
    founder_count: int,
    effective_date: str,
) -> str:
    """Build user prompt for Founder Agreement."""
    return f"""Generate a Founder Agreement with the following parameters:

COMPANY: {company_name}
INDUSTRY: {industry}
JURISDICTION: {jurisdiction}
GOVERNING LAW: {governing_law}
NUMBER OF FOUNDERS: {founder_count}
EFFECTIVE DATE: {effective_date}

REQUIREMENTS:
- Cover: equity split framework, roles & responsibilities, vesting schedule, IP assignment
- Include: decision-making process, departure/termination clauses, non-compete, dispute resolution
- Reference {governing_law} for governing law
- Professional tone appropriate for {jurisdiction}
- Assume equal equity split unless otherwise specified

Generate the complete Founder Agreement as a JSON object with sections array."""


def build_privacy_policy_prompt(
    *,
    company_name: str,
    industry: str,
    jurisdiction: str,
    governing_law: str,
    requires_gdpr: bool,
    effective_date: str,
) -> str:
    """Build user prompt for Privacy Policy."""
    gdpr_section = ""
    if requires_gdpr:
        gdpr_section = """
- MANDATORY GDPR sections: lawful basis for processing, data subject rights (access, rectification, erasure, portability), Data Protection Officer contact, cross-border transfer safeguards
- Include cookie consent requirements"""

    return f"""Generate a Privacy Policy with the following parameters:

COMPANY: {company_name}
INDUSTRY: {industry}
JURISDICTION: {jurisdiction}
GOVERNING LAW: {governing_law}
EFFECTIVE DATE: {effective_date}

REQUIREMENTS:
- Cover: data collection, usage, storage, sharing, security measures, user rights
- Include: contact information section, policy updates clause
- Reference {governing_law} for governing law
- Professional tone appropriate for {jurisdiction}{gdpr_section}

Generate the complete Privacy Policy as a JSON object with sections array."""


def build_terms_of_service_prompt(
    *,
    company_name: str,
    industry: str,
    jurisdiction: str,
    governing_law: str,
    requires_gdpr: bool,
    effective_date: str,
) -> str:
    """Build user prompt for Terms of Service."""
    gdpr_note = ""
    if requires_gdpr:
        gdpr_note = "\n- Include GDPR-compliant data processing references"

    return f"""Generate Terms of Service with the following parameters:

COMPANY: {company_name}
INDUSTRY: {industry}
JURISDICTION: {jurisdiction}
GOVERNING LAW: {governing_law}
EFFECTIVE DATE: {effective_date}

REQUIREMENTS:
- Cover: acceptance of terms, user accounts, acceptable use, intellectual property
- Include: limitation of liability, indemnification, termination, dispute resolution
- Reference {governing_law} for governing law
- Professional tone appropriate for {jurisdiction}{gdpr_note}

Generate the complete Terms of Service as a JSON object with sections array."""


# ── Prompt dispatcher ────────────────────────────────────────────────────

PROMPT_BUILDERS = {
    "Non-Disclosure Agreement (NDA)": build_nda_prompt,
    "Founder Agreement": build_founder_agreement_prompt,
    "Privacy Policy": build_privacy_policy_prompt,
    "Terms of Service": build_terms_of_service_prompt,
}
