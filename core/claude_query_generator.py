"""
Claude-powered search query generator. Instead of a single job title,
Claude produces multiple targeted queries that cover primary roles,
alternative titles, stretch roles, and industry variants.
"""

from core.user_profile import UserProfile
from core.claude_client import cached_profile_system, call_claude_json

_USER_PROMPT = """Based on this candidate's profile, generate {max_queries} job search queries.

Rules:
- Each query should be 2-5 words, suitable for a job board search field
- Cover different angles: their primary target role, alternative titles for the same role, one stretch/growth role, and one industry-specific variant if applicable
- Order from most to least relevant
- Do NOT include location in the queries
- Think about how recruiters title these roles — use real job board language

Return ONLY a JSON array of strings, e.g.:
["Senior Data Analyst", "Business Intelligence Analyst", "Analytics Engineer", "Data Scientist"]"""


def generate_search_queries(
    profile: UserProfile,
    max_queries: int = 4,
    model: str = "claude-sonnet-4-6",
) -> list[str]:
    """
    Use Claude to generate optimized job search queries from the candidate profile.
    Falls back to [profile.to_search_query()] if Claude fails.
    """
    system = cached_profile_system(profile.to_profile_text())
    try:
        result = call_claude_json(
            system=system,
            user_message=_USER_PROMPT.format(max_queries=max_queries),
            model=model,
            max_tokens=256,
        )
        if isinstance(result, list) and result:
            queries = [str(q) for q in result if q][:max_queries]
            return queries
    except Exception as e:
        print(f"[claude_queries] Failed to generate queries: {e}")

    fallback = profile.to_search_query()
    return [fallback] if fallback else []
