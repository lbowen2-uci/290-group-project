"""
Loads configuration from environment variables / .env file.
Copy .env.example to .env and fill in your API keys before running.
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # python-dotenv not installed — env vars must be set manually


def get_config() -> dict:
    """Return a config dict with all API keys and runtime settings."""
    return {
        # --- Adzuna (free tier: 250 req/day) ---
        # Register at: https://developer.adzuna.com/
        "adzuna_app_id": os.getenv("ADZUNA_APP_ID", ""),
        "adzuna_app_key": os.getenv("ADZUNA_APP_KEY", ""),
        "adzuna_country": os.getenv("ADZUNA_COUNTRY", "us"),

        # --- RapidAPI / JSearch (free tier: 1,000 req/month) ---
        # Register at: https://rapidapi.com/ then subscribe to JSearch
        "rapidapi_key": os.getenv("RAPIDAPI_KEY", ""),

        # --- Scrapers to enable ---
        # Options: "jobspy", "remotive", "adzuna"
        # jobspy and remotive need no API keys
        "enabled_scrapers": _parse_list(
            os.getenv("ENABLED_SCRAPERS", "jobspy,remotive,adzuna")
        ),

        # --- JobSpy sites ---
        # Options: linkedin, indeed, glassdoor, zip_recruiter, google
        "jobspy_sites": _parse_list(
            os.getenv("JOBSPY_SITES", "linkedin,indeed")
        ),

        # --- Matching mode ---
        # "semantic" (default, uses sentence-transformers)
        # "keyword"  (faster, uses TF-IDF, no GPU needed)
        "matching_mode": os.getenv("MATCHING_MODE", "semantic"),

        # --- Anthropic / Claude (optional — all features fall back without key) ---
        # Register at: https://console.anthropic.com/
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", ""),
        "claude_model": os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6"),
        "claude_rerank_top_n": int(os.getenv("CLAUDE_RERANK_TOP_N", "25")),
        "claude_batch_size": int(os.getenv("CLAUDE_BATCH_SIZE", "10")),
    }


def _parse_list(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]
