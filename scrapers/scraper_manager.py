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
from scrapers.jsearch_scraper import JSearchScraper


def _build_scrapers(config: dict, enabled: list[str]) -> list[BaseScraper]:
    """Instantiate only the scrapers that are enabled."""
    registry = {
        "jobspy": JobSpyScraper,
        "remotive": RemotiveScraper,
        "adzuna": AdzunaScraper,
        "jsearch": JSearchScraper,
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
    search_queries: list[str] | None = None,
) -> list[Job]:
    """
    Run all enabled scrapers concurrently and return deduplicated results.
    When search_queries is provided (Claude-generated), each scraper is run
    once per query — max_results is divided across queries to keep volume stable.

    Args:
        profile:                   The user's profile.
        config:                    API keys and settings dict.
        enabled_scrapers:          Names of scrapers to run. Defaults to configured list.
        max_results_per_scraper:   Max results to request per (scraper, query) pair.
        search_queries:            Claude-generated queries; falls back to profile query if None.

    Returns:
        Deduplicated list of Job objects from all sources.
    """
    if enabled_scrapers is None:
        enabled_scrapers = config.get("enabled_scrapers", ["jobspy", "remotive", "adzuna"])

    scrapers = _build_scrapers(config, enabled_scrapers)

    if not scrapers:
        print("[manager] No scrapers configured.")
        return []

    queries = search_queries or [None]  # None = each scraper uses its default
    per_query_max = max(10, max_results_per_scraper // len(queries))

    total_tasks = len(scrapers) * len(queries)
    print(f"\n[manager] Running {len(scrapers)} scraper(s) × {len(queries)} query/queries = {total_tasks} task(s) in parallel...")
    if search_queries:
        print(f"[manager] Queries: {search_queries}")

    all_jobs: list[Job] = []

    with ThreadPoolExecutor(max_workers=min(total_tasks, 12)) as executor:
        future_to_label = {}
        for s in scrapers:
            for q in queries:
                future = executor.submit(s.fetch, profile, per_query_max, q)
                label = f"{s.name}:{q or 'default'}"
                future_to_label[future] = label

        for future in as_completed(future_to_label):
            label = future_to_label[future]
            try:
                jobs = future.result()
                all_jobs.extend(jobs)
            except Exception as e:
                print(f"[manager] '{label}' raised an error: {e}")

    before = len(all_jobs)
    unique_jobs = _deduplicate(all_jobs)
    print(f"\n[manager] Total: {before} raw → {len(unique_jobs)} after deduplication.")
    return unique_jobs
