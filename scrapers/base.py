"""
Abstract base class for all job scrapers.
Every scraper must implement fetch() and return a list of Job objects.
"""

from abc import ABC, abstractmethod
from core.user_profile import UserProfile, Job


class BaseScraper(ABC):
    """All scrapers inherit from this class."""

    name: str = "base"

    def __init__(self, config: dict):
        """
        Args:
            config: Dict of API keys and settings from config.py.
        """
        self.config = config

    @abstractmethod
    def fetch(self, profile: UserProfile, max_results: int = 50) -> list[Job]:
        """
        Fetch job postings relevant to the given UserProfile.

        Args:
            profile:     The user's profile (skills, location, titles, etc.)
            max_results: Maximum number of results to return.

        Returns:
            List of normalized Job objects.
        """

    def _safe_float(self, value) -> float | None:
        """Safely convert a value to float, returning None on failure."""
        try:
            return float(value) if value not in (None, "", "N/A") else None
        except (TypeError, ValueError):
            return None
