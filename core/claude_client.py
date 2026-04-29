"""
Shared Claude API client used by all Claude-powered modules.
Single point of contact with the Anthropic SDK — handles initialization,
prompt caching, JSON parsing, and graceful fallback when unavailable.
"""

import json
import os
import re

_client = None


def is_available() -> bool:
    """Return True if the Anthropic SDK is installed and an API key is set."""
    try:
        import anthropic  # noqa: F401
        return bool(os.getenv("ANTHROPIC_API_KEY", ""))
    except ImportError:
        return False


def get_client():
    """Lazily initialize and return the shared Anthropic client."""
    global _client
    if _client is None:
        from anthropic import Anthropic
        _client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    return _client


def cached_profile_system(profile_text: str, persona: str = "") -> list[dict]:
    """
    Build a system message list with the user profile marked for prompt caching.
    The profile block is marked with cache_control so repeated calls (query gen,
    rerank batches) hit the cache instead of re-sending the full profile text.
    """
    base_persona = persona or (
        "You are an expert career advisor and job market analyst. "
        "You have deep knowledge of hiring practices, career trajectories, "
        "and what makes candidates successful in different roles."
    )
    return [
        {
            "type": "text",
            "text": f"{base_persona}\n\n<candidate_profile>\n{profile_text}\n</candidate_profile>",
            "cache_control": {"type": "ephemeral"},
        }
    ]


def _extract_json(text: str) -> str:
    """Strip markdown code fences around JSON if present."""
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        return match.group(1).strip()
    return text.strip()


def call_claude_json(
    system: list[dict],
    user_message: str,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 4096,
) -> dict | list:
    """
    Send a request to Claude and return the parsed JSON response.
    Handles markdown code fences around JSON. Raises ValueError on parse failure.
    """
    client = get_client()
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    raw = response.content[0].text
    return json.loads(_extract_json(raw))
