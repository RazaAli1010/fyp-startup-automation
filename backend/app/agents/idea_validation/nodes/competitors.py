"""
Competitor Analysis Node (Async Optimized)

Uses Exa AI to search for competitors with improved categorization,
relaxed relevance thresholds, and better parked domain detection.

PERFORMANCE OPTIMIZATIONS:
- Async HTTP calls with httpx
- Concurrent query execution
- Batched embedding calls
- 10s timeout per request
- Max 2 retries with 1.5s backoff
"""

import os
import re
import math
import asyncio
from typing import Dict, List, Any, Optional, Tuple

import httpx
from openai import AsyncOpenAI

from ..state import (
    ValidationState, CompetitorAnalysis, CompetitorInfo, 
    QualityMetrics, MarketStructure
)
from ..timing import StepTimer, log_timing
from ..http_client import Timeouts, RetryConfig
from ..epistemic_types import (
    CompetitorType, COMPETITOR_WEIGHTS, FundingStage,
    FUNDING_DOMINANCE_FACTORS, NOISE_INDICATORS, PRODUCT_SIGNALS,
    ClassifiedCompetitor, KILL_SWITCH_THRESHOLDS,
    SCORING_COMPETITOR_TYPES, NON_SCORING_COMPETITOR_TYPES
)



# Configuration - LOWERED threshold for sparse web text
RELEVANCE_THRESHOLD = 0.35  # Lowered from 0.55
DIRECT_COMPETITOR_THRESHOLD = 0.50  # Lowered from 0.75
MAX_RESULTS = 30
EMBEDDING_MODEL = "text-embedding-3-small"

# Exa API URL
EXA_API_URL = "https://api.exa.ai/search"

# Domain-specific logic is now handled dynamically via intent_keywords
# Removed hardcoded KNOWN_PARKING_COMPETITORS and formatting lists

# Funding validation ranges (in millions USD)
FUNDING_RANGES = {
    "pre-seed": (0.01, 1.5),
    "seed": (0.1, 8.0),
    "series a": (2.0, 30.0),
    "series b": (10.0, 80.0),
    "series c": (30.0, 200.0),
    "series d": (50.0, 400.0),
}

# Competitor Taxonomy - NOW USES STRICT ENUM FROM epistemic_types
# Legacy mapping for backward compatibility (DEPRECATED - use new 6-type system)
COMPETITOR_TYPES = {
    "DIRECT_PRODUCT": CompetitorType.DIRECT_PRODUCT.value,
    "ADJACENT_PRODUCT": CompetitorType.ADJACENT_PRODUCT.value, 
    "DIRECTORY": CompetitorType.DIRECTORY_OR_LIST.value,
    "CONTENT_MEDIA": CompetitorType.CONTENT_OR_MEDIA.value,
    "NON_COMPETITOR": CompetitorType.NOISE.value
}


# Heuristics for classification
CONTENT_INDICATORS = [
    "best", "top", "vs", "compare", "alternatives", "review", 
    "guide", "how to", "list", "blog", "article", "news",
    "directory", "software", "tools", "apps"
]

PRODUCT_INDICATORS = [
    "pricing", "login", "sign up", "get started", "book a demo",
    "features", "solutions", "customers", "enterprise", "download"
]

# ============================================================================
# STRICT 6-TYPE CLASSIFICATION SYSTEM
# ============================================================================

# Directory/aggregator domains (NON-SCORING: directory_or_list)
DIRECTORY_DOMAINS = frozenset({
    "capterra.com", "g2.com", "g2crowd.com", "crunchbase.com", "yelp.com",
    "alternativeto.net", "slant.co", "getapp.com", "softwareadvice.com",
    "trustradius.com", "sourceforge.net", "softwaresuggest.com",
    "financesonline.com", "saasworthy.com", "goodfirms.co"
})

# Content/media domains (NON-SCORING: content_or_media)
CONTENT_DOMAINS = frozenset({
    "medium.com", "substack.com", "wordpress.com", "blogspot.com",
    "techcrunch.com", "forbes.com", "entrepreneur.com", "inc.com",
    "producthunt.com", "news.ycombinator.com", "reddit.com",
    "twitter.com", "x.com", "linkedin.com", "quora.com"
})

# URL patterns indicating content (NON-SCORING)
CONTENT_URL_PATTERNS = [
    '/blog', '/article', '/news', '/updates', '/press', '/post',
    '/stories', '/posts/', '/newsletter', '/podcast', '/video'
]

# URL patterns indicating product pages (SCORING if matched)
PRODUCT_URL_PATTERNS = [
    '/pricing', '/features', '/product', '/solutions', '/platform',
    '/app', '/dashboard', '/signup', '/sign-up', '/register',
    '/demo', '/get-started', '/download', '/enterprise'
]

# App store patterns (strong SCORING signal)
APP_STORE_PATTERNS = [
    'apps.apple.com', 'play.google.com', 'apps.shopify.com',
    'chrome.google.com/webstore', 'addons.mozilla.org'
]

# Title patterns indicating listicles (NON-SCORING: content_or_media)
LISTICLE_TITLE_PATTERNS = [
    r'^top\s*\d+', r'^\d+\s*best', r'^best\s+\d+', r'^the\s+best',
    r'\bvs\.?\b', r'\bversus\b', r'\balternatives?\s+to\b',
    r'\breview\s+of\b', r'\bcomparison\b', r'\bcompared\b',
    r'^how\s+to\b', r'^what\s+is\b', r'^guide\s*:', r'\broundup\b'
]

# Platform/tool indicators (NON-SCORING if core function differs)
PLATFORM_TOOL_INDICATORS = [
    "virtual office", "coworking software", "video conferencing",
    "project management", "crm", "erp", "hr software", "accounting"
]


def classify_competitor_strict(
    url: str,
    title: str,
    description: str,
    idea_keywords: List[str]
) -> Tuple[CompetitorType, str, float]:
    """
    STRICT 6-TYPE CLASSIFICATION with justification.
    
    Returns: (CompetitorType, justification_string, confidence)
    
    Classification order (first match wins):
    1. Domain-based detection (directories, content sites)
    2. URL pattern detection (blogs, product pages)
    3. Title pattern detection (listicles, reviews)
    4. Content signal analysis (product vs content indicators)
    5. Default: NOISE (ambiguous = exclusion)
    
    RULE: If classification is ambiguous, default to exclusion.
    """
    url_lower = url.lower()
    title_lower = title.lower()
    desc_lower = description.lower() if description else ""
    combined = f"{title_lower} {desc_lower}"
    
    # Extract domain from URL
    domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url_lower)
    domain = domain_match.group(1) if domain_match else ""
    
    # =========================================================================
    # LAYER 1: Domain-based detection (highest confidence)
    # =========================================================================
    
    # Check for directory/aggregator domains
    for dir_domain in DIRECTORY_DOMAINS:
        if dir_domain in domain:
            return (
                CompetitorType.DIRECTORY_OR_LIST,
                f"Domain '{dir_domain}' is a known aggregator/directory site",
                0.95
            )
    
    # Check for content/media domains
    for content_domain in CONTENT_DOMAINS:
        if content_domain in domain:
            return (
                CompetitorType.CONTENT_OR_MEDIA,
                f"Domain '{content_domain}' is a known content/media platform",
                0.95
            )
    
    # =========================================================================
    # LAYER 2: URL pattern detection
    # =========================================================================
    
    # Check for content URL patterns
    for pattern in CONTENT_URL_PATTERNS:
        if pattern in url_lower:
            return (
                CompetitorType.CONTENT_OR_MEDIA,
                f"URL contains content pattern '{pattern}'",
                0.90
            )
    
    # Check for app store patterns (strong product signal)
    for pattern in APP_STORE_PATTERNS:
        if pattern in url_lower:
            return (
                CompetitorType.DIRECT_PRODUCT,
                f"URL is an app store listing ({pattern})",
                0.95
            )
    
    # =========================================================================
    # LAYER 3: Title pattern detection
    # =========================================================================
    
    # Check for listicle/comparison patterns in title
    for pattern in LISTICLE_TITLE_PATTERNS:
        if re.search(pattern, title_lower):
            return (
                CompetitorType.CONTENT_OR_MEDIA,
                f"Title matches listicle/comparison pattern",
                0.85
            )
    
    # =========================================================================
    # LAYER 4: Content signal analysis
    # =========================================================================
    
    # Count product signals
    product_signals = []
    for signal in PRODUCT_SIGNALS:
        if signal in combined:
            product_signals.append(signal)
    
    # Count noise signals
    noise_signals = []
    for signal in NOISE_INDICATORS:
        if signal in combined:
            noise_signals.append(signal)
    
    # Strong product signals = potential product
    if len(product_signals) >= 3 and len(noise_signals) <= 1:
        # Check URL for product page indicators
        has_product_url = any(p in url_lower for p in PRODUCT_URL_PATTERNS)
        
        if has_product_url:
            return (
                CompetitorType.DIRECT_PRODUCT,
                f"Strong product signals ({', '.join(product_signals[:3])}) + product URL pattern",
                0.80
            )
        else:
            # Product signals but no product URL - could be adjacent
            return (
                CompetitorType.ADJACENT_PRODUCT,
                f"Product signals present ({', '.join(product_signals[:3])}) but no clear product URL",
                0.65
            )
    
    # Some product signals with low noise
    if len(product_signals) >= 1 and len(product_signals) > len(noise_signals):
        # Check if it's a platform/tool that doesn't substitute
        for indicator in PLATFORM_TOOL_INDICATORS:
            if indicator in combined:
                return (
                    CompetitorType.PLATFORM_OR_TOOL,
                    f"Platform/tool indicator '{indicator}' - different core function",
                    0.70
                )
        
        return (
            CompetitorType.ADJACENT_PRODUCT,
            f"Some product signals ({', '.join(product_signals[:2])}) - partial overlap",
            0.60
        )
    
    # More noise signals than product signals
    if len(noise_signals) > len(product_signals):
        return (
            CompetitorType.CONTENT_OR_MEDIA,
            f"Noise signals dominate ({', '.join(noise_signals[:2])})",
            0.75
        )
    
    # =========================================================================
    # LAYER 5: Default to NOISE (ambiguity = exclusion)
    # =========================================================================
    return (
        CompetitorType.NOISE,
        "No clear product or content signals - ambiguous classification defaults to noise",
        0.50
    )


def is_scoring_competitor(comp_type: CompetitorType) -> bool:
    """Check if a competitor type should influence scoring."""
    return comp_type in SCORING_COMPETITOR_TYPES



def _get_api_keys() -> Tuple[str, str]:
    """Get API keys from environment."""
    exa_key = os.getenv("EXA_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not exa_key:
        raise ValueError("EXA_API_KEY environment variable not set")
    if not openai_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    return exa_key, openai_key


def _generate_competitor_queries(idea: str, intent_keywords: List[str]) -> List[str]:
    """Generate queries optimized for finding competitors using intent keywords."""
    queries = []
    
    # Intent-anchored queries
    if intent_keywords:
        # Use top 3 keywords to form specific queries
        core_terms = " ".join(intent_keywords[:2])
        queries.append(f"{core_terms} startup")
        queries.append(f"{core_terms} marketplace competitors")
        queries.append(f"apps for {core_terms}")
        
    # General idea-based queries
    queries.append(f"{idea} competitors")
    
    # Extract core terms from idea (fallback)
    idea_lower = idea.lower()
    words = re.split(r'[\s\-_,;:\.!?\'\"()\[\]{}]+', idea_lower)
    meaningful = [w for w in words if len(w) > 3 and w.isalpha()]
    
    if meaningful:
        core = ' '.join(meaningful[:3])
        queries.append(f"{core} startup company")
        queries.append(f"{core} alternatives")
    
    # Deduplicate
    seen = set()
    unique = []
    for q in queries:
        q_lower = q.lower().strip()
        if q_lower not in seen:
            seen.add(q_lower)
            unique.append(q)
    
    return unique[:8]


def _is_known_competitor(name: str, url: str) -> bool:
    """
    Check if this is a known competitor.
    Deprecated: Dynamic logic should not rely on hardcoded lists.
    """
    return False


def _has_domain_signals(content: str, intent_keywords: List[str]) -> float:
    """
    Check for domain-specific signals that boost relevance using intent keywords.
    Returns boost value (0-0.3).
    """
    content_lower = content.lower()
    boost = 0.0
    
    if not intent_keywords:
        return 0.0
        
    # Check for presence of intent keywords in content
    matches = sum(1 for kw in intent_keywords if kw.lower() in content_lower)
    
    if matches >= 3:
        boost += 0.20
    elif matches >= 1:
        boost += 0.10
    
    # Check for marketplace indicators (generic)
    marketplace_signals = [
        "marketplace", "platform", "connect", "host", "peer to peer", "p2p", "sharing economy"
    ]
    if any(sig in content_lower for sig in marketplace_signals):
        boost += 0.05
    
    return min(boost, 0.30)


def _is_parked_or_dead(content: str, title: str, url: str) -> Tuple[bool, str]:
    """
    Detect parked domains with RELAXED rules.
    Returns (is_parked, reason).
    
    RELAXED: Allow JS-heavy pages, only flag explicit sale patterns.
    """
    combined = f"{title} {content}".lower()
    
    # Explicit domain sale patterns (strict)
    sale_patterns = [
        r'this\s*domain\s*(?:is\s*)?(?:for\s*sale|available\s*for\s*purchase)',
        r'buy\s*this\s*(?:premium\s*)?domain',
        r'domain\s*(?:is\s*)?(?:for\s*sale|expired|parked)',
        r'inquire\s*about\s*(?:purchasing\s*)?this\s*domain',
        r'make\s*(?:an?\s*)?offer\s*(?:on|for)\s*(?:this\s*)?domain',
        r'godaddy\s*auctions?',
        r'sedo\.com',
        r'hugedomains',
        r'dan\.com/buy',
        r'is\s*for\s*sale',
        r'domain\s*name\s*for\s*sale'
    ]
    
    for pattern in sale_patterns:
        if re.search(pattern, combined):
            return True, "domain_for_sale"
    
    # Empty placeholder patterns
    placeholder_patterns = [
        r'^coming\s*soon\.?$',
        r'^under\s*construction\.?$',
        r'^site\s*under\s*maintenance\.?$',
        r'^launching\s*soon\.?$',
        r'^website\s*coming\s*soon\.?$',
    ]
    
    for pattern in placeholder_patterns:
        if re.search(pattern, combined.strip()):
            return True, "placeholder_page"
    
    # RELAXED: Only flag if content is VERY short (<50 chars, not 100)
    # This allows JS-heavy pages that might have minimal text
    if len(content.strip()) < 50 and len(title.strip()) < 20:
        # Double-check it's not a real company with minimal landing page
        if not any(sig in combined for sig in ["app", "platform", "service", "download", "sign up", "get started"]):
            return True, "no_content"
    
    return False, ""


def _clean_description(content: str) -> str:
    """Clean description by removing boilerplate."""
    if not content:
        return ""
    
    # Remove common boilerplate patterns
    patterns = [
        r'<[^>]+>',  # HTML tags
        r'&\w+;',  # HTML entities
        r'cookie\s*(policy|consent)',
        r'privacy\s*policy',
        r'terms\s*of\s*service',
        r'sign\s*up\s*for\s*newsletter',
        r'subscribe\s*to',
        r'javascript:',
        r'data:[^;]+;base64,[A-Za-z0-9+/=]+',
    ]
    
    for pattern in patterns:
        content = re.sub(pattern, '', content, flags=re.IGNORECASE)
    
    # Remove excessive whitespace
    content = re.sub(r'\s+', ' ', content)
    content = content.strip()
    
    return content[:300] if content else ""


def _extract_company_name(title: str, url: str) -> str:
    """Extract company name from title or URL."""
    if title:
        parts = re.split(r'[\|\-–—:]', title)
        if parts:
            name = parts[0].strip()
            name = re.sub(r'\s*\(.*?\)\s*', '', name)
            if 2 < len(name) < 50:
                return name
    
    domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
    if domain_match:
        domain = domain_match.group(1)
        parts = domain.split('.')
        if len(parts) >= 2:
            return parts[0].title()
    
    return "Unknown Company"


def _classify_competitor_type(
    title: str,
    content: str,
    url: str,
    is_known: bool
) -> Tuple[CompetitorType, float]:
    """
    DEPRECATED: Use classify_competitor_strict instead.
    
    Legacy function for backward compatibility.
    Classify as DIRECT_PRODUCT, ADJACENT_PRODUCT, or NOISE.
    
    Returns (CompetitorType enum, classification_confidence).
    """
    title_lower = title.lower()
    content_lower = content.lower()
    url_lower = url.lower()
    combined = f"{title_lower} {content_lower}"
    
    # =========================================================================
    # NOISE DETECTION (weight=0, will be discarded)
    # =========================================================================
    
    # 1. Listicle/comparison content - ALWAYS NOISE
    listicle_patterns = [
        r'top\s*\d+', r'best\s+\d+', r'\d+\s+best',
        r'vs\.', r'versus', r'alternatives\s+to',
        r'review\s+of', r'comparison', r'compared'
    ]
    for pattern in listicle_patterns:
        if re.search(pattern, title_lower):
            return CompetitorType.NOISE, 0.95
    
    # 2. Directory sites - ALWAYS NOISE
    directory_indicators = [
        "capterra", "g2.com", "g2crowd", "crunchbase", "yelp",
        "directory", "producthunt.com/posts", "alternativeto.net",
        "slant.co", "getapp", "softwareadvice", "trustradius"
    ]
    if any(ind in url_lower for ind in directory_indicators):
        return CompetitorType.DIRECTORY_OR_LIST, 0.98
    
    # 3. Blog/article URLs - ALWAYS NOISE
    blog_patterns = ["/blog/", "/article/", "/news/", "/post/", "/stories/"]
    if any(pattern in url_lower for pattern in blog_patterns):
        return CompetitorType.CONTENT_OR_MEDIA, 0.90
    
    # 4. Content indicator keywords in title - likely NOISE
    noise_title_indicators = [
        "how to", "guide", "tutorial", "what is", "explained",
        "list of", "best of", "top picks", "roundup"
    ]
    if any(ind in title_lower for ind in noise_title_indicators):
        return CompetitorType.CONTENT_OR_MEDIA, 0.85
    
    # =========================================================================
    # PRODUCT DETECTION (DIRECT or ADJACENT)
    # =========================================================================
    
    # Count product signals (transactional indicators)
    product_signal_count = 0
    for signal in PRODUCT_SIGNALS:
        if signal in combined:
            product_signal_count += 1
    
    # Count noise signals
    noise_signal_count = 0
    for signal in NOISE_INDICATORS:
        if signal in combined:
            noise_signal_count += 1
    
    # Known competitor - trust the flag
    if is_known:
        return CompetitorType.DIRECT_PRODUCT, 1.0
    
    # Strong product signals + low noise = DIRECT PRODUCT
    if product_signal_count >= 3 and noise_signal_count <= 1:
        return CompetitorType.DIRECT_PRODUCT, 0.80
    
    # Some product signals = ADJACENT PRODUCT
    if product_signal_count >= 1 and product_signal_count > noise_signal_count:
        return CompetitorType.ADJACENT_PRODUCT, 0.65
    
    # More noise than product signals = NOISE
    if noise_signal_count > product_signal_count:
        return CompetitorType.NOISE, 0.70
    
    # Ambiguous - default to ADJACENT (conservative, still has some weight)
    return CompetitorType.ADJACENT_PRODUCT, 0.50


def _extract_and_validate_funding(content: str) -> str:
    """Extract and validate funding information."""
    content_lower = content.lower()
    
    funding_patterns = [
        r'raised\s*\$?([\d\.]+)\s*(million|m|billion|b)(?:\s*in)?\s*(?:a\s*)?(seed|series\s*[a-f]|pre-seed)?',
        r'(seed|series\s*[a-f]|pre-seed)\s*(?:round|funding)?\s*(?:of)?\s*\$?([\d\.]+)\s*(million|m|billion|b)',
        r'\$?([\d\.]+)\s*(million|m|billion|b)\s*(?:in\s*)?(seed|series\s*[a-f]|pre-seed)',
    ]
    
    for pattern in funding_patterns:
        match = re.search(pattern, content_lower)
        if match:
            groups = match.groups()
            
            amount_str = None
            unit = None
            stage = None
            
            for g in groups:
                if g is None:
                    continue
                g_clean = g.strip().lower()
                
                if re.match(r'[\d\.]+', g_clean):
                    amount_str = g_clean
                elif g_clean in ('million', 'm', 'billion', 'b'):
                    unit = g_clean
                elif re.match(r'(seed|series\s*[a-f]|pre-seed)', g_clean):
                    stage = g_clean
            
            if amount_str:
                try:
                    amount = float(amount_str)
                    
                    if unit in ('billion', 'b'):
                        amount *= 1000
                    
                    # Validate against ranges
                    is_valid = False
                    if stage:
                        stage_clean = stage.replace(' ', '').lower()
                        for range_stage, (min_val, max_val) in FUNDING_RANGES.items():
                            if range_stage.replace(' ', '').replace('-', '') in stage_clean.replace('-', ''):
                                if min_val * 0.3 <= amount <= max_val * 2.5:
                                    is_valid = True
                                break
                    else:
                        is_valid = 0.01 <= amount <= 500
                    
                    if not is_valid:
                        return "Unknown"
                    
                    if amount >= 1000:
                        funding_str = f"${amount/1000:.1f}B"
                    elif amount >= 1:
                        funding_str = f"${amount:.1f}M"
                    else:
                        funding_str = f"${amount*1000:.0f}K"
                    
                    if stage:
                        funding_str += f" {stage.title()}"
                    
                    return funding_str
                except ValueError:
                    continue
    
    return "Unknown"


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity."""
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)


def _extract_differentiation_opportunities(
    idea: str,
    competitors: List[Dict]
) -> List[str]:
    """Identify differentiation opportunities."""
    opportunities = []
    descriptions = " ".join([c.get("description", "") for c in competitors]).lower()
    idea_lower = idea.lower()
    
    # Segment-based opportunities
    segment_checks = [
        ("small business", "Focus on SMB segment"),
        ("enterprise", "Enterprise-focused offering"),
        ("mobile", "Mobile-first experience"),
        ("residential", "Residential neighborhood focus"),
        ("commercial", "Commercial/office parking focus"),
    ]
    
    for segment, opportunity in segment_checks:
        if segment in idea_lower and segment not in descriptions:
            opportunities.append(opportunity)
    
    # Feature-based opportunities
    feature_checks = [
        (["instant", "real-time"], "Real-time availability"),
        (["insurance", "protection"], "Built-in insurance coverage"),
        (["verified", "trust"], "Verified host/guest system"),
        (["subscription", "monthly"], "Flexible subscription model"),
    ]
    
    for keywords, opportunity in feature_checks:
        if any(kw in idea_lower for kw in keywords) and not any(kw in descriptions for kw in keywords):
            opportunities.append(opportunity)
    
    # Add generic opportunities
    generic = [
        "Better pricing model",
        "Superior user experience",
        "Faster host onboarding",
        "Better customer support",
        "Niche market focus"
    ]
    
    for opp in generic:
        if len(opportunities) >= 5:
            break
        if opp not in opportunities:
            opportunities.append(opp)
    
    return opportunities[:5]


def _calculate_total_funding(competitors: List[Dict]) -> str:
    """Calculate approximate total funding in the space."""
    total = 0.0
    funded_count = 0
    
    for comp in competitors:
        funding = comp.get("funding", "Unknown")
        if funding and funding != "Unknown":
            match = re.search(r'\$([\d\.]+)([MBK])', funding)
            if match:
                amount = float(match.group(1))
                unit = match.group(2)
                if unit == 'B':
                    amount *= 1000
                elif unit == 'K':
                    amount /= 1000
                total += amount
                funded_count += 1
    
    if funded_count == 0:
        return "Unknown"
    elif total >= 1000:
        return f"${total/1000:.1f}B+"
    elif total >= 100:
        return f"${total:.0f}M+"
    elif total > 0:
        return f"${total:.1f}M+"
    else:
        return "Unknown"

def _parse_funding_amount(funding_str: str) -> float:
    """Parse funding string to numeric value in millions USD."""
    if not funding_str or funding_str == "Unknown":
        return 0.0
    
    match = re.search(r'\$?([\d\.]+)\s*([MBK])', funding_str, re.IGNORECASE)
    if match:
        amount = float(match.group(1))
        unit = match.group(2).upper()
        if unit == 'B':
            return amount * 1000
        elif unit == 'K':
            return amount / 1000
        return amount
    return 0.0


def _estimate_dominance_factor(funding_str: str) -> float:
    """Estimate dominance factor based on funding stage."""
    funding_amount = _parse_funding_amount(funding_str)
    
    if funding_amount >= 100:  # $100M+ = Series C+
        return FUNDING_DOMINANCE_FACTORS[FundingStage.SERIES_C_PLUS]
    elif funding_amount >= 30:  # $30M+ = Series B
        return FUNDING_DOMINANCE_FACTORS[FundingStage.SERIES_B]
    elif funding_amount >= 10:  # $10M+ = Series A
        return FUNDING_DOMINANCE_FACTORS[FundingStage.SERIES_A]
    elif funding_amount >= 1:   # $1M+ = Seed
        return FUNDING_DOMINANCE_FACTORS[FundingStage.SEED]
    elif funding_amount > 0:    # Some funding = Pre-seed
        return FUNDING_DOMINANCE_FACTORS[FundingStage.PRE_SEED]
    else:
        return FUNDING_DOMINANCE_FACTORS[FundingStage.UNKNOWN]


def _calculate_weighted_pressure(competitors: List[Dict]) -> Tuple[float, List[str], int]:
    """
    Calculate weighted market pressure score.
    
    Formula: Score = Σ(relevance × dominance × type_weight)
    
    Returns: (pressure_score, dominant_players, noise_discarded_count)
    """
    pressure = 0.0
    dominant_players = []
    noise_count = 0
    
    for comp in competitors:
        comp_type_str = comp.get("competitor_type", comp.get("type", ""))
        
        # Get weight for this type
        if comp_type_str == CompetitorType.DIRECT_PRODUCT.value:
            type_weight = COMPETITOR_WEIGHTS[CompetitorType.DIRECT_PRODUCT]
        elif comp_type_str == CompetitorType.ADJACENT_PRODUCT.value:
            type_weight = COMPETITOR_WEIGHTS[CompetitorType.ADJACENT_PRODUCT]
        else:
            # NON-SCORING types - weight is 0, discard from calculation
            type_weight = 0.0
            noise_count += 1
            continue
        
        relevance = comp.get("relevance_score", 0.5)
        funding = comp.get("funding", "Unknown")
        dominance = _estimate_dominance_factor(funding)
        
        contribution = relevance * dominance * type_weight
        pressure += contribution
        
        # Track dominant players
        if contribution >= 0.3:  # Significant contributor
            dominant_players.append(comp.get("name", "Unknown"))
    
    return pressure, dominant_players[:5], noise_count


def _determine_market_structure(
    scoring_competitors: List[Dict],
    dominant_players: List[str],
    total_funding_millions: float,
    pressure_score: float
) -> Tuple[str, List[str], float]:
    """
    Determine market structure based on DOMINANCE and SUBSTITUTABILITY, not counts.
    
    This function reasons about market POWER, not market SIZE.
    
    Returns: (structure_type, evidence_list, confidence)
    
    Structure Types:
    - fragmented: Many small/weak players, no dominant brand, low switching costs
    - emerging: Few early players, unclear category leader, evolving definitions
    - consolidated: Several strong incumbents, clear expectations, differentiation required
    - monopolized: One dominant provider, high switching costs, extremely hard to enter
    """
    evidence = []
    
    direct_count = sum(1 for c in scoring_competitors 
                       if c.get("type", c.get("competitor_type", "")) == CompetitorType.DIRECT_PRODUCT.value)
    adjacent_count = sum(1 for c in scoring_competitors 
                         if c.get("type", c.get("competitor_type", "")) == CompetitorType.ADJACENT_PRODUCT.value)
    
    # Count competitors with known funding (indicates established players)
    funded_competitors = [c for c in scoring_competitors 
                          if c.get("funding", "Unknown") != "Unknown"]
    
    # Check if any single competitor has dominant funding (> 50% of total)
    competitor_fundings = []
    for comp in scoring_competitors:
        funding = comp.get("funding", "Unknown")
        amount = _parse_funding_amount(funding)
        if amount > 0:
            competitor_fundings.append((comp.get("name", "Unknown"), amount))
    
    competitor_fundings.sort(key=lambda x: x[1], reverse=True)
    
    has_dominant_player = False
    dominant_player_name = None
    if competitor_fundings and total_funding_millions > 0:
        top_funding = competitor_fundings[0][1]
        if top_funding > 0.5 * total_funding_millions:
            has_dominant_player = True
            dominant_player_name = competitor_fundings[0][0]
    
    # =========================================================================
    # STRUCTURE CLASSIFICATION LOGIC (reason about dominance, not count)
    # =========================================================================
    
    # MONOPOLIZED: One dominant provider with high switching costs
    if has_dominant_player and top_funding >= 100:
        structure_type = "monopolized"
        evidence.append(f"Single dominant player '{dominant_player_name}' controls majority of market funding")
        evidence.append(f"Market leader has ${top_funding:.0f}M funding - extremely high barrier to entry")
        if len(dominant_players) == 1:
            evidence.append("No credible challengers observed")
        confidence = 0.85
    
    # CONSOLIDATED: Several strong incumbents with clear market positions
    elif len(funded_competitors) >= 2 and total_funding_millions >= 30:
        structure_type = "consolidated"
        evidence.append(f"Multiple funded incumbents ({len(funded_competitors)} competitors with known funding)")
        evidence.append(f"Combined market funding of ${total_funding_millions:.1f}M indicates established space")
        if dominant_players:
            evidence.append(f"Clear market leaders: {', '.join(dominant_players[:3])}")
        evidence.append("Differentiation required to compete - clear user expectations exist")
        confidence = 0.75
    
    # EMERGING: Few early players, unclear leader, evolving category
    elif direct_count >= 1 and direct_count <= 3 and total_funding_millions < 30:
        structure_type = "emerging"
        evidence.append(f"Small number of direct products ({direct_count}) suggests early-stage market")
        if total_funding_millions > 0:
            evidence.append(f"Low total market funding (${total_funding_millions:.1f}M) indicates opportunity")
        else:
            evidence.append("No known funding among competitors - category still forming")
        evidence.append("Unclear category leader - market definitions still evolving")
        evidence.append("Indicates timing sensitivity - early entry advantage possible")
        confidence = 0.70
    
    # FRAGMENTED: Many small players OR no clear winners
    elif direct_count >= 4 or (adjacent_count >= 3 and direct_count == 0):
        structure_type = "fragmented"
        if not has_dominant_player:
            evidence.append("No single product is the default choice for users")
        evidence.append("Multiple partial solutions exist without clear market leader")
        if len(funded_competitors) < 2:
            evidence.append("Most competitors lack significant funding - low barriers to entry")
        evidence.append("Users rely on ad-hoc discovery rather than a dominant platform")
        evidence.append("MANY WEAK PLAYERS ≠ SATURATED MARKET - indicates opportunity for consolidation")
        confidence = 0.65
    
    # DEFAULT: Emerging (limited data)
    else:
        structure_type = "emerging"
        if direct_count == 0:
            evidence.append("No direct product competitors found - may indicate nascent/untested market")
        if adjacent_count > 0:
            evidence.append(f"{adjacent_count} adjacent solutions found - problem space exists but not directly addressed")
        else:
            evidence.append("Limited competitive data - market may be nascent or search terms too narrow")
        confidence = 0.50
    
    return structure_type, evidence, confidence


# DELETED: _determine_market_saturation_weighted - concept removed
# DELETED: _determine_market_saturation - concept removed


async def _search_exa_async(
    client: httpx.AsyncClient,
    api_key: str,
    query: str,
    timeout: float = Timeouts.EXA
) -> List[Dict]:
    """
    Search Exa API asynchronously with timeout and retry.
    """
    url = EXA_API_URL
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "query": query,
        "type": "auto",
        "numResults": 15,
        "contents": {
            "text": True,
            "highlights": True
        }
    }
    
    for attempt in range(RetryConfig.MAX_RETRIES + 1):
        try:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
                timeout=timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
            
            # Non-retryable errors
            if response.status_code in RetryConfig.NON_RETRYABLE_CODES:
                log_timing("competitors", f"Exa non-retryable error: {response.status_code}")
                return []
            
            # Retryable errors
            if attempt < RetryConfig.MAX_RETRIES:
                backoff = min(
                    RetryConfig.INITIAL_BACKOFF * (2 ** attempt),
                    RetryConfig.MAX_BACKOFF
                )
                await asyncio.sleep(backoff)
                
        except httpx.TimeoutException:
            log_timing("competitors", f"Exa timeout on attempt {attempt + 1}")
            if attempt < RetryConfig.MAX_RETRIES:
                await asyncio.sleep(RetryConfig.INITIAL_BACKOFF)
        except Exception as e:
            log_timing("competitors", f"Exa error: {str(e)[:50]}")
            return []
    
    return []


async def _get_embeddings_batch(
    client: AsyncOpenAI,
    texts: List[str],
    timeout: float = Timeouts.OPENAI_EMBEDDING
) -> List[List[float]]:
    """
    Get embeddings for multiple texts in a single batch call.
    """
    if not texts:
        return []
    
    # Truncate texts to fit token limits
    truncated = [t[:8000] for t in texts]
    
    try:
        response = await asyncio.wait_for(
            client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=truncated
            ),
            timeout=timeout
        )
        return [item.embedding for item in response.data]
    except asyncio.TimeoutError:
        log_timing("competitors", "Embedding batch timeout")
        return [[] for _ in texts]
    except Exception as e:
        log_timing("competitors", f"Embedding batch error: {str(e)[:50]}")
        return [[] for _ in texts]


async def search_competitors(state: ValidationState) -> Dict[str, Any]:
    """
    Search for competitors using Exa AI.
    
    ASYNC OPTIMIZED:
    - Concurrent query execution
    - Batched embeddings
    - 10s timeout per request
    - Max 2 retries
    """
    timer = StepTimer("competitors")
    
    idea_input = state.get("idea_input", "")
    processing_errors = list(state.get("processing_errors", []))
    
    if not idea_input:
        return {
            "competitor_analysis": _insufficient_data_response(["no_idea_provided"]),
            "processing_errors": processing_errors + ["Competitors: No idea provided"]
        }
    
    try:
        exa_key, openai_key = _get_api_keys()
    except ValueError as e:
        return {
            "competitor_analysis": _insufficient_data_response([str(e)]),
            "processing_errors": processing_errors + [f"Competitors: {str(e)}"]
        }
    
    # Get global embedding and intent from state
    idea_embedding = state.get("idea_embedding", [])
    intent_keywords = state.get("intent_keywords", [])
    
    if not idea_embedding:
        return {
            "competitor_analysis": _insufficient_data_response(["missing_idea_embedding"]),
            "processing_errors": processing_errors + ["Competitors: Missing idea embedding"]
        }
        
    # Generate queries using intent keywords
    queries = _generate_competitor_queries(idea_input, intent_keywords)
    
    # Initialize OpenAI client
    openai_client = AsyncOpenAI(api_key=openai_key)
    
    # Search Exa CONCURRENTLY for all queries
    async with timer.async_step("exa_search"):
        async with httpx.AsyncClient() as http_client:
            search_tasks = [
                _search_exa_async(http_client, exa_key, query)
                for query in queries
            ]
            results_lists = await asyncio.gather(*search_tasks, return_exceptions=True)
    
    # Flatten results
    all_results = []
    for result_list in results_lists:
        if isinstance(result_list, list):
            all_results.extend(result_list)
    
    if not all_results:
        timer.summary()
        return {
            "competitor_analysis": _insufficient_data_response(["no_search_results"]),
            "processing_errors": processing_errors + ["Competitors: No results"]
        }
    
    # Deduplicate
    seen_urls = set()
    unique_results = []
    for result in all_results:
        url = result.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(result)
    
    # ========================================================================
    # PHASE 1: STRICT CLASSIFICATION GATE
    # Classify ALL results BEFORE any scoring or processing
    # ========================================================================
    async with timer.async_step("classification"):
        all_classified = []
        
        for result in unique_results:
            url = result.get("url", "")
            title = result.get("title", "")
            content = result.get("text", "")
            highlights = result.get("highlights", [])
            snippet = content[:500] if content else ""
            
            full_content = f"{title}\n{content}\n{' '.join(highlights) if highlights else ''}"
            
            # Check for parked/dead first
            is_parked, parked_reason = _is_parked_or_dead(full_content, title, url)
            if is_parked:
                continue
            
            # STRICT 6-TYPE CLASSIFICATION with justification
            comp_type, justification, class_confidence = classify_competitor_strict(
                url, title, snippet, intent_keywords
            )
            
            # Extract company name
            company_name = _extract_company_name(title, url)
            
            all_classified.append({
                "url": url,
                "title": title,
                "content": content,
                "full_content": full_content[:4000],
                "company_name": company_name,
                "type": comp_type,
                "justification": justification,
                "classification_confidence": class_confidence,
            })
        
        log_timing("competitors", f"Classified {len(all_classified)} results")
    
    if not all_classified:
        timer.summary()
        return {
            "competitor_analysis": _insufficient_data_response([
                "all_results_filtered_or_parked"
            ]),
            "processing_errors": processing_errors + ["Competitors: All results filtered"]
        }
    
    # ========================================================================
    # PHASE 2: SEPARATE SCORING vs NON-SCORING COMPETITORS
    # ONLY direct_product and adjacent_product affect verdicts
    # ========================================================================
    scoring_candidates = []
    non_scoring_candidates = []
    excluded_types = set()
    
    for item in all_classified:
        if is_scoring_competitor(item["type"]):
            scoring_candidates.append(item)
        else:
            non_scoring_candidates.append(item)
            excluded_types.add(item["type"].value)
    
    log_timing("competitors", 
        f"Scoring: {len(scoring_candidates)}, Non-scoring: {len(non_scoring_candidates)}")
    
    # ========================================================================
    # PHASE 3: COMPUTE RELEVANCE FOR SCORING COMPETITORS ONLY
    # Embeddings are only computed for scoring competitors (saves cost)
    # ========================================================================
    if scoring_candidates:
        async with timer.async_step("batch_embeddings"):
            texts_to_embed = [r["full_content"] for r in scoring_candidates]
            embeddings = await _get_embeddings_batch(openai_client, texts_to_embed)
        
        # Calculate relevance for each scoring competitor
        for i, result in enumerate(scoring_candidates):
            if i < len(embeddings) and embeddings[i]:
                base_relevance = _cosine_similarity(idea_embedding, embeddings[i])
            else:
                base_relevance = 0.3
            
            domain_boost = _has_domain_signals(result["full_content"], intent_keywords)
            final_relevance = min(1.0, base_relevance + domain_boost)
            result["relevance_score"] = round(final_relevance, 3)
            
            # Extract funding
            result["funding"] = _extract_and_validate_funding(result["full_content"])
    
    # ========================================================================
    # PHASE 4: BUILD FINAL COMPETITOR LISTS
    # ========================================================================
    
    # Build scoring competitors list
    scoring_competitors: List[CompetitorInfo] = []
    for comp in sorted(scoring_candidates, key=lambda x: x.get("relevance_score", 0), reverse=True)[:15]:
        clean_desc = _clean_description(comp["content"])
        info: CompetitorInfo = {
            "name": comp["company_name"],
            "url": comp["url"],
            "description": clean_desc,
            "funding": comp.get("funding", "Unknown"),
            "type": comp["type"].value,
            "justification": comp["justification"],
            "confidence": comp["classification_confidence"],
            "relevance_score": comp.get("relevance_score", 0.0),
        }
        scoring_competitors.append(info)
    
    # Build non-scoring competitors list (for context only)
    non_scoring_competitors: List[CompetitorInfo] = []
    for comp in non_scoring_candidates[:10]:
        clean_desc = _clean_description(comp["content"])
        info: CompetitorInfo = {
            "name": comp["company_name"],
            "url": comp["url"],
            "description": clean_desc,
            "funding": "Unknown",
            "type": comp["type"].value,
            "justification": comp["justification"],
            "confidence": comp["classification_confidence"],
            "relevance_score": 0.0,  # Non-scoring competitors have no relevance score
        }
        non_scoring_competitors.append(info)
    
    # ========================================================================
    # PHASE 5: COMPUTE MARKET STRUCTURE (ONLY FROM SCORING COMPETITORS)
    # Evidence-based classification: fragmented | emerging | consolidated | monopolized
    # ========================================================================
    
    # Calculate weighted pressure (only from scoring competitors)
    pressure_score = 0.0
    dominant_players = []
    
    for comp in scoring_competitors:
        comp_type_val = comp["type"]
        relevance = comp.get("relevance_score", 0.5)
        funding = comp.get("funding", "Unknown")
        dominance = _estimate_dominance_factor(funding)
        
        if comp_type_val == CompetitorType.DIRECT_PRODUCT.value:
            weight = COMPETITOR_WEIGHTS[CompetitorType.DIRECT_PRODUCT]
        elif comp_type_val == CompetitorType.ADJACENT_PRODUCT.value:
            weight = COMPETITOR_WEIGHTS[CompetitorType.ADJACENT_PRODUCT]
        else:
            weight = 0.0
        
        contribution = relevance * dominance * weight
        pressure_score += contribution
        
        if contribution >= 0.3:
            dominant_players.append(comp["name"])
    
    # Calculate total funding from scoring competitors only
    total_funding_millions = 0.0
    for comp in scoring_competitors:
        total_funding_millions += _parse_funding_amount(comp.get("funding", "Unknown"))
    
    # Determine market structure using evidence-based reasoning
    # This REPLACES the old market_saturation concept entirely
    market_type, evidence, structure_confidence = _determine_market_structure(
        scoring_competitors,
        dominant_players,
        total_funding_millions,
        pressure_score
    )
    
    market_structure: MarketStructure = {
        "type": market_type,
        "confidence": structure_confidence,
        "evidence": evidence,
    }
    
    # ========================================================================
    # PHASE 6: BUILD FINAL OUTPUT
    # NOTE: market_saturation has been REMOVED - use market_structure instead
    # ========================================================================
    
    # Map excluded types to human-readable names
    excluded_from_scoring = []
    for excluded_type in excluded_types:
        type_map = {
            "directory_or_list": "directories and aggregators",
            "content_or_media": "blogs, articles, and listicles",
            "platform_or_tool_non_substitutable": "non-substitutable platforms",
            "noise": "SEO noise and irrelevant results",
        }
        excluded_from_scoring.append(type_map.get(excluded_type, excluded_type))
    
    # Differentiation opportunities (based on scoring competitors)
    scoring_comp_dicts = [
        {"name": c["name"], "description": c["description"], "funding": c.get("funding", "Unknown")}
        for c in scoring_competitors
    ]
    differentiation_opportunities = _extract_differentiation_opportunities(idea_input, scoring_comp_dicts)
    
    # Total funding display string
    if total_funding_millions >= 1000:
        total_funding_str = f"${total_funding_millions/1000:.1f}B+"
    elif total_funding_millions >= 1:
        total_funding_str = f"${total_funding_millions:.1f}M+"
    elif total_funding_millions > 0:
        total_funding_str = f"${total_funding_millions*1000:.0f}K+"
    else:
        total_funding_str = "Unknown"
    
    # Quality metrics
    relevance_scores = [c.get("relevance_score", 0) for c in scoring_competitors]
    avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
    
    direct_count = sum(1 for c in scoring_competitors if c["type"] == CompetitorType.DIRECT_PRODUCT.value)
    
    confidence = min(0.95, (
        0.3 * min(len(scoring_competitors) / 5, 1) +
        0.4 * avg_relevance +
        0.3 * (0.8 if direct_count > 0 else 0.4)
    ))
    
    warnings = []
    if len(scoring_competitors) < 2:
        warnings.append("limited_scoring_competitor_data")
    if direct_count == 0:
        warnings.append("no_direct_product_competitors")
    if len(non_scoring_competitors) > len(scoring_competitors) * 2:
        warnings.append("high_noise_ratio")
    if len(excluded_from_scoring) > 0:
        warnings.append(f"excluded_{len(non_scoring_candidates)}_non_scoring_results")
    
    quality: QualityMetrics = {
        "data_volume": len(scoring_competitors),
        "relevance_mean": round(avg_relevance, 3),
        "confidence": round(confidence, 3),
        "warnings": warnings,
    }
    
    # Legacy field mapping for backward compatibility
    direct_competitors = [c for c in scoring_competitors if c["type"] == CompetitorType.DIRECT_PRODUCT.value]
    indirect_competitors = [c for c in scoring_competitors if c["type"] == CompetitorType.ADJACENT_PRODUCT.value]
    
    competitor_analysis: CompetitorAnalysis = {
        # Counts
        "competitors_found": len(all_classified),
        "scoring_competitors_count": len(scoring_competitors),
        "non_scoring_competitors_count": len(non_scoring_competitors),
        
        # Separated lists
        "scoring_competitors": scoring_competitors,
        "non_scoring_competitors": non_scoring_competitors,
        
        # Legacy (backward compatible)
        "direct_competitors": direct_competitors[:10],
        "indirect_competitors": indirect_competitors[:10],
        
        # Exclusion transparency
        "excluded_from_scoring": excluded_from_scoring,
        
        # Market analysis (ONLY from scoring competitors)
        # NOTE: market_saturation REMOVED - market_structure replaces it
        "market_structure": market_structure,
        "differentiation_opportunities": differentiation_opportunities,
        "total_funding_in_space": total_funding_str,
        
        # Quality
        "quality": quality,
    }
    
    timer.summary()
    return {"competitor_analysis": competitor_analysis}


def _insufficient_data_response(warnings: List[str]) -> CompetitorAnalysis:
    """Generate insufficient data response with new schema."""
    return {
        "competitors_found": 0,
        "scoring_competitors_count": 0,
        "non_scoring_competitors_count": 0,
        "scoring_competitors": [],
        "non_scoring_competitors": [],
        "direct_competitors": [],
        "indirect_competitors": [],
        "excluded_from_scoring": [],
        "market_structure": {
            "type": "emerging",  # Default to emerging when insufficient data
            "confidence": 0.0,
            "evidence": ["Insufficient data for market structure analysis"],
        },
        "differentiation_opportunities": ["Insufficient data for analysis"],
        "total_funding_in_space": "Unknown",
        "quality": {
            "data_volume": 0,
            "relevance_mean": 0.0,
            "confidence": 0.0,
            "warnings": warnings,
        },
    }
