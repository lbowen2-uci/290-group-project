"""
Job Scraper — Entry Point

Usage examples:
  # Q&A mode, export to CSV
  python main.py --mode qa --output csv

  # Resume mode, export to HTML report
  python main.py --mode resume --file resume.pdf --output html

  # Resume mode with location override, save to SQLite
  python main.py --mode resume --file resume.pdf --location "Chicago, IL" --output db

  # Resume mode, keyword matching (faster, no GPU needed)
  python main.py --mode resume --file resume.pdf --output csv --matching keyword

  # Remote jobs only
  python main.py --mode qa --remote --output html
"""

import argparse
import sys

from config import get_config
from core.user_profile import UserProfile
from scrapers.scraper_manager import run_scrapers
from matching.keyword_matcher import score_jobs_keyword
from matching.semantic_matcher import score_jobs_semantic
from output.csv_exporter import export_csv, export_excel
from output.html_report import export_html
from output.db_store import save_results


def parse_args():
    parser = argparse.ArgumentParser(
        description="Job scraper that matches postings to your resume or profile.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--mode",
        choices=["resume", "qa"],
        required=True,
        help="Input mode: 'resume' to parse a PDF, 'qa' for interactive Q&A.",
    )
    parser.add_argument(
        "--file",
        metavar="PATH",
        help="Path to your PDF resume (required when --mode resume).",
    )
    parser.add_argument(
        "--location",
        metavar="CITY",
        help="Override/set job search location, e.g. 'Chicago, IL'.",
    )
    parser.add_argument(
        "--remote",
        action="store_true",
        help="Include remote jobs (can combine with --location).",
    )
    parser.add_argument(
        "--output",
        choices=["csv", "excel", "html", "db", "all"],
        default="csv",
        help="Output format (default: csv).",
    )
    parser.add_argument(
        "--matching",
        choices=["semantic", "keyword"],
        default=None,
        help="Matching mode override (default: from .env or 'semantic').",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=50,
        metavar="N",
        help="Max results to fetch per scraper (default: 50).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=25,
        metavar="N",
        help="Number of top results to include in output (default: 25).",
    )
    return parser.parse_args()


def build_profile(args) -> UserProfile:
    """Load or collect the user profile based on --mode."""
    if args.mode == "resume":
        if not args.file:
            print("Error: --file is required when using --mode resume.")
            sys.exit(1)
        from core.resume_parser import parse_resume
        profile = parse_resume(args.file)
    else:
        from core.questionnaire import run_questionnaire
        profile = run_questionnaire()

    # Apply CLI overrides
    if args.location:
        profile.location = args.location
    if args.remote:
        profile.remote_ok = True

    return profile


def score_jobs(jobs, profile, mode: str):
    """Run the selected matching mode."""
    if not jobs:
        return []
    if mode == "keyword":
        print("\n[main] Scoring with keyword matcher (TF-IDF)...")
        return score_jobs_keyword(profile, jobs)
    else:
        print("\n[main] Scoring with semantic matcher (sentence-transformers)...")
        try:
            return score_jobs_semantic(profile, jobs)
        except ImportError as e:
            print(f"[main] Semantic matching unavailable: {e}")
            print("[main] Falling back to keyword matching.")
            return score_jobs_keyword(profile, jobs)


def write_output(jobs, profile, output_format: str, top_n: int):
    """Write results in the requested format(s)."""
    top_jobs = jobs[:top_n]

    if output_format in ("csv", "all"):
        export_csv(top_jobs)
    if output_format in ("excel", "all"):
        export_excel(top_jobs)
    if output_format in ("html", "all"):
        export_html(top_jobs, profile)
    if output_format in ("db", "all"):
        save_results(top_jobs, profile)


def main():
    args = parse_args()
    config = get_config()

    # Matching mode: CLI flag > .env > default semantic
    matching_mode = args.matching or config.get("matching_mode", "semantic")

    print("=" * 60)
    print("  Job Scraper")
    print("=" * 60)

    # 1. Build user profile
    profile = build_profile(args)

    # 2. Scrape jobs
    jobs = run_scrapers(
        profile=profile,
        config=config,
        max_results_per_scraper=args.max_results,
    )

    if not jobs:
        print("\nNo jobs found. Try broadening your search or checking your API keys.")
        sys.exit(0)

    # 3. Score / rank
    scored_jobs = score_jobs(jobs, profile, matching_mode)

    # 4. Print preview
    print(f"\n{'Rank':<5} {'Score':>6}  {'Title':<40} {'Company':<25} {'Location'}")
    print("-" * 110)
    for i, job in enumerate(scored_jobs[:10], 1):
        score_pct = f"{job.match_score * 100:.1f}%"
        print(f"{i:<5} {score_pct:>6}  {job.title[:38]:<40} {job.company[:23]:<25} {job.location}")

    # 5. Export
    print()
    write_output(scored_jobs, profile, args.output, args.top)
    print("\nDone.")


if __name__ == "__main__":
    main()
