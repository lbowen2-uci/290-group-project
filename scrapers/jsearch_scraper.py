"""
Scraper for the JSearch API (via RapidAPI).
Free tier: 200 req/month. Paid plans available for higher volume.

Register at https://rapidapi.com/ and subscribe to the JSearch API.
Set in .env:
    RAPIDAPI_KEY=your_key
"""

import requests

from core.user_profile import UserProfile, Job
from scrapers.base import BaseScraper


JSEARCH_URL = "https://jsearch.p.rapidapi.com/search"
JSEARCH_HOST = "jsearch.p.rapidapi.com"


class JSearchScraper(BaseScraper):
    """
    Fetches job listings from JSearch via RapidAPI.
    Aggregates postings from LinkedIn, Indeed, Glassdoor, and more.
    """

    name = "jsearch"

    def fetch(self, profile: UserProfile, max_results: int = 50, query_override: str | None = None) -> list[Job]:
        api_key = self.config.get("rapidapi_key", "")

        if not api_key:
            print(f"[{self.name}] Skipping — RAPIDAPI_KEY not set in .env")
            return []

        # JSearch returns ~10 results per page; cap at 5 pages to stay within free tier
        num_pages = max(1, min(max_results // 10, 5))

        query = query_override or profile.to_search_query()
        if profile.location and not query_override:
            query = f"{query} in {profile.location}"

        params = {
            "query": query,
            "page": "1",
            "num_pages": str(num_pages),
            "date_posted": "week",
        }
        if profile.remote_ok:
            params["remote_jobs_only"] = "true"

        headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": JSEARCH_HOST,
        }

        print(f"[{self.name}] Searching: '{query}'")

        try:
            resp = requests.get(JSEARCH_URL, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"[{self.name}] Request error: {e}")
            return []
        except ValueError as e:
            print(f"[{self.name}] JSON parse error: {e}")
            return []

        jobs: list[Job] = []
        for item in data.get("data", []):
            city = item.get("job_city") or ""
            state = item.get("job_state") or ""
            location = ", ".join(p for p in [city, state] if p)

            emp_type = item.get("job_employment_type") or ""
            job = Job(
                title=item.get("job_title", ""),
                company=item.get("employer_name", ""),
                location=location,
                description=item.get("job_description", ""),
                url=item.get("job_apply_link") or item.get("job_google_link", ""),
                salary_min=self._safe_float(item.get("job_min_salary")),
                salary_max=self._safe_float(item.get("job_max_salary")),
                salary_currency=item.get("job_salary_currency") or "USD",
                job_type=emp_type.lower().replace("_", "-"),
                source=self.name,
                posted_date=item.get("job_posted_at_datetime_utc") or "",
            )
            if job.title and job.company:
                jobs.append(job)

        print(f"[{self.name}] Found {len(jobs)} jobs.")
        return jobs[:max_results]
