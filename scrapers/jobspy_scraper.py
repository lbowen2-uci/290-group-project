"""
Scraper using python-jobspy — aggregates LinkedIn, Indeed, Glassdoor, ZipRecruiter.
No API keys required.

Install: pip install python-jobspy
"""

from core.user_profile import UserProfile, Job
from scrapers.base import BaseScraper


class JobSpyScraper(BaseScraper):
    """
    Wraps python-jobspy to scrape multiple major job boards simultaneously.
    Sources: linkedin, indeed, glassdoor, zip_recruiter, google
    """

    name = "jobspy"

    # Subset of sites to scrape — can be overridden via config
    DEFAULT_SITES = ["linkedin", "indeed", "glassdoor", "zip_recruiter"]

    def fetch(self, profile: UserProfile, max_results: int = 50, query_override: str | None = None) -> list[Job]:
        try:
            from jobspy import scrape_jobs
        except ImportError:
            raise ImportError(
                "python-jobspy is required for JobSpyScraper.\n"
                "Install it with: pip install python-jobspy"
            )

        sites = self.config.get("jobspy_sites", self.DEFAULT_SITES)
        search_term = query_override or profile.to_search_query()
        location = profile.location or None

        remote_label = " | Remote: Yes" if profile.remote_ok else ""
        print(f"[{self.name}] Searching: '{search_term}' | Location: '{location or 'any'}'{remote_label} | Sites: {sites}")

        try:
            df = scrape_jobs(
                site_name=sites,
                search_term=search_term,
                location=location,
                is_remote=profile.remote_ok,
                results_wanted=max_results,
                hours_old=72,          # jobs posted in last 3 days
                country_indeed="USA",
            )
        except Exception as e:
            print(f"[{self.name}] Error during scrape: {e}")
            return []

        if df is None or df.empty:
            print(f"[{self.name}] No results returned.")
            return []

        jobs = []
        for _, row in df.iterrows():
            job = Job(
                title=str(row.get("title", "") or ""),
                company=str(row.get("company", "") or ""),
                location=str(row.get("location", "") or ""),
                description=str(row.get("description", "") or ""),
                url=str(row.get("job_url", "") or ""),
                salary_min=self._safe_float(row.get("min_amount")),
                salary_max=self._safe_float(row.get("max_amount")),
                salary_currency=str(row.get("currency", "USD") or "USD"),
                job_type=str(row.get("job_type", "") or ""),
                source=str(row.get("site", self.name) or self.name),
                posted_date=str(row.get("date_posted", "") or ""),
            )
            if job.title and job.company:
                jobs.append(job)

        print(f"[{self.name}] Found {len(jobs)} jobs.")
        return jobs
