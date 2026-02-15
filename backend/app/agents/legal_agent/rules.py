"""Jurisdiction-aware rules for the Legal Document Generator.

Maps geographies to governing law clauses, legal structures,
and jurisdiction-specific notes. All rules are deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


# ── Governing law mappings ───────────────────────────────────────────────

GOVERNING_LAW_MAP: Dict[str, str] = {
    "united states": "Laws of the State of Delaware, United States",
    "usa": "Laws of the State of Delaware, United States",
    "us": "Laws of the State of Delaware, United States",
    "united kingdom": "Laws of England and Wales, United Kingdom",
    "uk": "Laws of England and Wales, United Kingdom",
    "canada": "Laws of the Province of Ontario, Canada",
    "australia": "Laws of New South Wales, Australia",
    "germany": "Laws of the Federal Republic of Germany",
    "france": "Laws of the French Republic",
    "india": "Laws of the Republic of India",
    "pakistan": "Laws of the Islamic Republic of Pakistan",
    "uae": "Laws of the Emirate of Dubai, United Arab Emirates",
    "singapore": "Laws of the Republic of Singapore",
    "ireland": "Laws of Ireland",
    "netherlands": "Laws of the Kingdom of the Netherlands",
}

# Countries requiring GDPR compliance in Privacy Policy
GDPR_COUNTRIES = {
    "united kingdom", "uk", "germany", "france", "ireland",
    "netherlands", "italy", "spain", "portugal", "belgium",
    "austria", "sweden", "denmark", "finland", "norway",
    "poland", "czech republic", "romania", "hungary", "greece",
    "eu",
}


@dataclass
class JurisdictionContext:
    """Deterministic context derived from geography and idea inputs."""

    country: str
    governing_law: str
    requires_gdpr: bool
    legal_notes: List[str] = field(default_factory=list)


def resolve_jurisdiction(geography: str) -> JurisdictionContext:
    """Resolve a geography string into a JurisdictionContext."""
    geo_lower = geography.strip().lower()

    governing_law = GOVERNING_LAW_MAP.get(
        geo_lower,
        f"Laws of {geography.strip().title()}",
    )

    requires_gdpr = geo_lower in GDPR_COUNTRIES

    notes: List[str] = []
    if requires_gdpr:
        notes.append(
            "This jurisdiction falls under GDPR. Privacy Policy includes "
            "data subject rights, lawful basis for processing, and DPO contact."
        )
    if geo_lower in ("united states", "usa", "us"):
        notes.append(
            "US jurisdiction — consider state-specific privacy laws (CCPA for California)."
        )
    if geo_lower in ("pakistan", "india"):
        notes.append(
            "Emerging market jurisdiction — regulatory frameworks may be evolving. "
            "Recommend periodic legal review."
        )

    return JurisdictionContext(
        country=geography.strip().title(),
        governing_law=governing_law,
        requires_gdpr=requires_gdpr,
        legal_notes=notes,
    )


# ── Document type validation ────────────────────────────────────────────

VALID_DOCUMENT_TYPES = {
    "nda": "Non-Disclosure Agreement (NDA)",
    "founder_agreement": "Founder Agreement",
    "privacy_policy": "Privacy Policy",
    "terms_of_service": "Terms of Service",
}


def validate_document_type(doc_type: str) -> str:
    """Validate and return the canonical document type label.

    Raises ValueError if doc_type is not one of the four supported types.
    """
    key = doc_type.strip().lower().replace(" ", "_").replace("-", "_")
    if key not in VALID_DOCUMENT_TYPES:
        raise ValueError(
            f"Unsupported document type '{doc_type}'. "
            f"Valid types: {list(VALID_DOCUMENT_TYPES.keys())}"
        )
    return VALID_DOCUMENT_TYPES[key]
