"""
Orchestrates multiple scrapers, runs them concurrently,
and returns a deduplicated list of Job objects.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from core.user_profile import UserProfile, Job
from scrapers.base import BaseScraper
from scrapers.jobspy_scraper import JobSpyScraper
from scrapers.remotive_scraper import RemotiveScraper
from scrapers.adzuna_scraper import AdzunaScraper


def _build_scrapers(config: dict, enabled: list[str]) -> list[BaseScraper]:
    """Instantiate only the scrapers that are enabled."""
    registry = {
        "jobspy": JobSpyScraper,
        "remotive": RemotiveScraper,
        "adzuna": AdzunaScraper,
    }
    scrapers = []
    for name in enabled:
        cls = registry.get(name)
        if cls:
            scrapers.append(cls(config))
        else:
            print(f"[manager] Unknown scraper '{name}' — skipping.")
    return scrapers


def _deduplicate(jobs: list[Job]) -> list[Job]:
    """Remove duplicate postings across sources using (title, company, location) hash."""
    seen = set()
    unique = []
    for job in jobs:
        key = job.dedup_key()
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique


def run_scrapers(
    profile: UserProfile,
    config: dict,
    enabled_scrapers: list[str] | None = None,
    max_results_per_scraper: int = 50,
) -> list[Job]:
    """
    Run all enabled scrapers concurrently and return deduplicated results.

    Args:
        profile:                   The user's profile.
        config:                    API keys and settings dict.
        enabled_scrapers:          Names of scrapers to run. Defaults to all three.
        max_results_per_scraper:   Max results to request from each scraper.

    Returns:
        Deduplicated list of Job objects from all sources.
    """
    if enabled_scrapers is None:
        enabled_scrapers = config.get("enabled_scrapers", ["jobspy", "remotive", "adzuna"])

    scrapers = _build_scrapers(config, enabled_scrapers)

    if not scrapers:
        print("[manager] No scrapers configured.")
        return []

    all_jobs: list[Job] = []

    print(f"\n[manager] Running {len(scrapers)} scraper(s) in parallel...")

    with ThreadPoolExecutor(max_workers=len(scrapers)) as executor:
        future_to_scraper = {
            executor.submit(s.fetch, profile, max_results_per_scraper): s.name
            for s in scrapers
        }
        for future in as_completed(future_to_scraper):
            name = future_to_scraper[future]
            try:
                jobs = future.result()
                all_jobs.extend(jobs)
            except Exception as e:
                print(f"[manager] Scraper '{name}' raised an error: {e}")

    before = len(all_jobs)
    unique_jobs = _deduplicate(all_jobs)
    print(f"\n[manager] Total: {before} raw → {len(unique_jobs)} after deduplication.")
    return unique_jobs
