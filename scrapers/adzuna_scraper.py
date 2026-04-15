"""
Scraper for the Adzuna Jobs API.
Free tier: ~250 API calls/day, salary data included, 12 countries.

Register for a free API key at: https://developer.adzuna.com/
Set in .env:
    ADZUNA_APP_ID=your_app_id
    ADZUNA_APP_KEY=your_app_key
"""

import requests

from core.user_profile import UserProfile, Job
from scrapers.base import BaseScraper


ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"
DEFAULT_COUNTRY = "us"


class AdzunaScraper(BaseScraper):
    """
    Fetches job listings from the Adzuna API.
    Provides salary data (min/max annual) and covers 12 countries.
    """

    name = "adzuna"

    def fetch(self, profile: UserProfile, max_results: int = 50) -> list[Job]:
        app_id = self.config.get("adzuna_app_id", "")
        app_key = self.config.get("adzuna_app_key", "")

        if not app_id or not app_key:
            print(f"[{self.name}] Skipping — ADZUNA_APP_ID / ADZUNA_APP_KEY not set in .env")
            return []

        country = self.config.get("adzuna_country", DEFAULT_COUNTRY)
        search_term = profile.to_search_query()
        location = profile.location or ""

        # Adzuna paginates at 50 results/page
        pages_needed = max(1, -(-max_results // 50))  # ceiling division
        jobs = []

        print(f"[{self.name}] Searching: '{search_term}' | Location: '{location or 'any'}'")

        for page in range(1, pages_needed + 1):
            params = {
                "app_id": app_id,
                "app_key": app_key,
                "results_per_page": min(50, max_results - len(jobs)),
                "page": page,
                "what": search_term,
                "content-type": "application/json",
            }
            if location:
                params["where"] = location
            if profile.remote_ok:
                params["what_and"] = "remote"

            url = f"{ADZUNA_BASE_URL}/{country}/search/{page}"

            try:
                response = requests.get(url, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
            except requests.RequestException as e:
                print(f"[{self.name}] Request error (page {page}): {e}")
                break
            except ValueError as e:
                print(f"[{self.name}] JSON parse error: {e}")
                break

            results = data.get("results", [])
            if not results:
                break

            for item in results:
                location_str = ""
                loc = item.get("location", {})
                area = loc.get("area", [])
                if area:
                    location_str = ", ".join(str(a) for a in area[-2:])  # city, state

                job = Job(
                    title=item.get("title", ""),
                    company=item.get("company", {}).get("display_name", ""),
                    location=location_str,
                    description=item.get("description", ""),
                    url=item.get("redirect_url", ""),
                    salary_min=self._safe_float(item.get("salary_min")),
                    salary_max=self._safe_float(item.get("salary_max")),
                    salary_currency="USD" if country == "us" else "",
                    job_type="full-time",
                    source=self.name,
                    posted_date=item.get("created", ""),
                )
                if job.title and job.company:
                    jobs.append(job)

            if len(jobs) >= max_results:
                break

        print(f"[{self.name}] Found {len(jobs)} jobs.")
        return jobs
