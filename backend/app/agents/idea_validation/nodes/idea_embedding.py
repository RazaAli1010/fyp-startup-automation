"""
Idea Embedding & Intent Extraction Node

Generates the global semantic anchor (embedding) and extracts core intent keywords.
This serves as the "source of truth" for all downstream nodes to validate relevance.
"""

import os
import json
import asyncio
from typing import Dict, Any, List
from openai import AsyncOpenAI
from ..state import ValidationState
from ..timing import StepTimer, log_timing
from ..http_client import Timeouts

EMBEDDING_MODEL = "text-embedding-3-small"

async def generate_idea_embedding(state: ValidationState) -> Dict[str, Any]:
    """
    Generate embedding and extract intent keywords for the startup idea.
    This runs BEFORE all other nodes.
    """
    timer = StepTimer("idea_embedding")
    idea_input = state.get("idea_input", "")
    processing_errors = list(state.get("processing_errors", []))
    
    if not idea_input:
        return {
            "idea_embedding": [],
            "intent_keywords": [],
            "processing_errors": processing_errors + ["Embedding: No idea provided"]
        }

    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        client = AsyncOpenAI(api_key=api_key)

        # parallelize embedding and intent extraction
        async with timer.async_step("embedding_and_intent"):
            embedding_task = _get_embedding(client, idea_input)
            intent_task = _extract_intent_keywords(client, idea_input)
            
            embedding, keywords = await asyncio.gather(embedding_task, intent_task)

    except Exception as e:
        log_timing("idea_embedding", f"Error: {e}")
        return {
            "idea_embedding": [],
            "intent_keywords": [],
            "processing_errors": processing_errors + [f"Embedding: {str(e)}"]
        }
    
    timer.summary()
    return {
        "idea_embedding": embedding,
        "intent_keywords": keywords
    }

async def _get_embedding(client: AsyncOpenAI, text: str) -> List[float]:
    """Get vector embedding for the idea."""
    try:
        response = await client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        log_timing("idea_embedding", f"Embedding API error: {e}")
        return []

async def _extract_intent_keywords(client: AsyncOpenAI, idea: str) -> List[str]:
    """
    Extract core domain nouns and verbs using a fast LLM call.
    Returns a list of 5-8 specific keywords.
    """
    prompt = f"""
    Extract 5-8 core domain keywords from this startup idea.
    Focus on specific nouns, verbs, and industry terms.
    Avoid generic words like "app", "platform", "startup", "business", "better".
    
    Idea: {idea}
    
    Return ONLY a JSON array of strings. Example: ["parking", "driveway", "rent", "vehicle", "storage"]
    """
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=100
        )
        content = response.choices[0].message.content.strip()
        
        # Clean markdown
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        keywords = json.loads(content)
        return keywords if isinstance(keywords, list) else []
        
    except Exception as e:
        log_timing("idea_embedding", f"Intent extraction error: {e}")
        # Fallback: simple processing
        words = idea.lower().split()
        return [w for w in words if len(w) > 4][:5]
