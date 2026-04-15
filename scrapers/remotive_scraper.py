"""
Scraper for the Remotive REST API — remote jobs only, no auth required.
API docs: https://remotive.com/remote-jobs/api

Free tier: No key needed. ~2,000 active listings. Rate limit: 2 req/min.
"""

import requests

from core.user_profile import UserProfile, Job
from scrapers.base import BaseScraper


REMOTIVE_API_URL = "https://remotive.com/api/remote-jobs"

# Map Remotive categories to common search terms
CATEGORY_MAP = {
    "data": "data",
    "science": "data-science",
    "analyst": "data",
    "engineer": "software-dev",
    "developer": "software-dev",
    "marketing": "marketing",
    "finance": "finance-legal",
    "design": "design",
    "product": "product",
    "management": "management-finance",
}


def _guess_category(profile: UserProfile) -> str:
    """Pick the best Remotive category based on profile job titles and skills."""
    text = " ".join(profile.job_titles + profile.skills).lower()
    for keyword, category in CATEGORY_MAP.items():
        if keyword in text:
            return category
    return ""  # empty = all categories


class RemotiveScraper(BaseScraper):
    """Fetches remote job listings from Remotive (no API key required)."""

    name = "remotive"

    def fetch(self, profile: UserProfile, max_results: int = 50) -> list[Job]:
        search_term = profile.to_search_query()
        category = _guess_category(profile)

        params = {"limit": min(max_results, 100)}
        if search_term:
            params["search"] = search_term
        if category:
            params["category"] = category

        print(f"[{self.name}] Searching: '{search_term}' | Category: '{category or 'all'}'")

        try:
            response = requests.get(REMOTIVE_API_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            print(f"[{self.name}] Request error: {e}")
            return []
        except ValueError as e:
            print(f"[{self.name}] JSON parse error: {e}")
            return []

        raw_jobs = data.get("jobs", [])
        jobs = []
        for item in raw_jobs[:max_results]:
            job = Job(
                title=item.get("title", ""),
                company=item.get("company_name", ""),
                location=item.get("candidate_required_location", "Remote"),
                description=item.get("description", ""),
                url=item.get("url", ""),
                salary_min=None,
                salary_max=None,
                job_type=item.get("job_type", "full_time"),
                source=self.name,
                posted_date=item.get("publication_date", ""),
            )
            # Parse salary if present in the salary field
            salary_str = item.get("salary", "")
            if salary_str:
                job = _parse_salary(job, salary_str)

            if job.title and job.company:
                jobs.append(job)

        print(f"[{self.name}] Found {len(jobs)} jobs.")
        return jobs


def _parse_salary(job: Job, salary_str: str) -> Job:
    """Best-effort salary range extraction from Remotive's free-text salary field."""
    import re
    numbers = re.findall(r'\$?([\d,]+)', salary_str.replace(",", ""))
    nums = [float(n.replace(",", "")) for n in numbers if n]
    if len(nums) >= 2:
        job.salary_min = min(nums)
        job.salary_max = max(nums)
    elif len(nums) == 1:
        job.salary_min = nums[0]
    return job
