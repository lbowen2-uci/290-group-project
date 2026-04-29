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
from output.stats_exporter import export_stats_json, export_stats_markdown, export_stats_charts
from analytics.stats_generator import compute_stats
from analytics.charts import render_charts


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
        "--no-claude",
        action="store_true",
        help="Disable all Claude AI features for this run (uses regex parser, single query, original scoring).",
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
    use_claude = not getattr(args, "no_claude", False)

    if args.mode == "resume":
        if not args.file:
            print("Error: --file is required when using --mode resume.")
            sys.exit(1)

        if use_claude:
            from core.claude_client import is_available
            if is_available():
                try:
                    from core.claude_resume_parser import parse_resume_with_claude
                    profile = parse_resume_with_claude(args.file)
                except Exception as e:
                    print(f"[main] Claude resume parsing failed ({e}), falling back to regex/spaCy.")
                    from core.resume_parser import parse_resume
                    profile = parse_resume(args.file)
            else:
                print("[main] ANTHROPIC_API_KEY not set — using regex/spaCy parser.")
                from core.resume_parser import parse_resume
                profile = parse_resume(args.file)
        else:
            from core.resume_parser import parse_resume
            profile = parse_resume(args.file)
    else:
        from core.questionnaire import run_questionnaire
        profile = run_questionnaire()

        # Enhance QA profile with Claude narrative/strengths if available
        if use_claude:
            from core.claude_client import is_available
            if is_available():
                _enhance_qa_profile(profile)

    # Apply CLI overrides
    if args.location:
        profile.location = args.location
    if args.remote:
        profile.remote_ok = True

    return profile


def _enhance_qa_profile(profile: UserProfile) -> None:
    """Add Claude-inferred narrative, goals, and strengths to a QA-built profile."""
    from core.claude_client import cached_profile_system, call_claude_json
    system = [
        {
            "type": "text",
            "text": (
                "You are an expert career advisor. Given a candidate's self-reported profile, "
                "generate insightful career analysis they may not have articulated themselves. "
                "Return ONLY valid JSON."
            ),
        }
    ]
    user_msg = f"""Based on this candidate's self-reported profile, generate career insights.

Profile:
{profile.to_profile_text()}

Return a JSON object with:
{{
  "career_narrative": "2-3 sentences describing their career trajectory and direction",
  "inferred_goals": "what they likely want in their next role based on their background",
  "strengths": ["3-5 key strengths inferred from their experience and skills"],
  "career_level": "entry, mid, senior, lead, or executive"
}}"""
    try:
        data = call_claude_json(system=system, user_message=user_msg, max_tokens=512)
        profile.career_narrative = str(data.get("career_narrative") or "")
        profile.inferred_goals = str(data.get("inferred_goals") or "")
        profile.strengths = [str(s) for s in data.get("strengths") or []]
        profile.career_level = str(data.get("career_level") or "")
        print(f"[main] Claude enhanced profile: {profile.career_level} level, {len(profile.strengths)} strengths identified.")
    except Exception as e:
        print(f"[main] Claude profile enhancement failed: {e}")


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


def write_output(
    jobs,
    profile,
    output_format: str,
    top_n: int,
    stats: dict | None = None,
    charts: dict | None = None,
):
    """Write results in the requested format(s) and always emit summary stats."""
    top_jobs = jobs[:top_n]

    if output_format in ("csv", "all"):
        export_csv(top_jobs)
    if output_format in ("excel", "all"):
        export_excel(top_jobs)
    if output_format in ("html", "all"):
        export_html(top_jobs, profile, stats=stats, charts=charts)
    if output_format in ("db", "all"):
        save_results(top_jobs, profile)

    # Always write standalone stats files (cheap, always useful)
    if stats:
        export_stats_json(stats)
        export_stats_markdown(stats)
        export_stats_charts(charts or {})


def main():
    args = parse_args()
    config = get_config()

    use_claude = not getattr(args, "no_claude", False)

    # Matching mode: CLI flag > .env > default semantic
    matching_mode = args.matching or config.get("matching_mode", "semantic")

    print("=" * 60)
    print("  Job Scraper")
    print("=" * 60)

    # 1. Build user profile
    profile = build_profile(args)

    # 2. Generate smart search queries (Claude-powered if available)
    search_queries = None
    if use_claude:
        from core.claude_client import is_available
        if is_available():
            try:
                from core.claude_query_generator import generate_search_queries
                search_queries = generate_search_queries(
                    profile,
                    model=config.get("claude_model", "claude-sonnet-4-6"),
                )
                profile.search_queries = search_queries
                print(f"[main] Claude queries: {search_queries}")
            except Exception as e:
                print(f"[main] Claude query generation failed ({e}), using default query.")

    # 3. Scrape jobs
    jobs = run_scrapers(
        profile=profile,
        config=config,
        max_results_per_scraper=args.max_results,
        search_queries=search_queries,
    )

    if not jobs:
        print("\nNo jobs found. Try broadening your search or checking your API keys.")
        sys.exit(0)

    # 4. Pre-score / rank with keyword or semantic matching
    scored_jobs = score_jobs(jobs, profile, matching_mode)

    # 5. Claude re-ranking on top results (enhances pre-scoring)
    if use_claude:
        from core.claude_client import is_available
        if is_available() and scored_jobs:
            try:
                from matching.claude_ranker import rerank_with_claude
                print("\n[main] Re-ranking top results with Claude...")
                scored_jobs = rerank_with_claude(
                    profile,
                    scored_jobs,
                    top_n=config.get("claude_rerank_top_n", 25),
                    batch_size=config.get("claude_batch_size", 10),
                    model=config.get("claude_model", "claude-sonnet-4-6"),
                )
            except Exception as e:
                print(f"[main] Claude re-ranking failed ({e}), using original scoring.")

    # 6. Aggregate statistics (computed on all scored jobs, not just top-N)
    print("\n[main] Computing market statistics...")
    stats = compute_stats(scored_jobs, profile)
    charts = render_charts(stats)

    # 7. Print preview (shows Claude score when available)
    print(f"\n{'Rank':<5} {'Score':>6}  {'Title':<40} {'Company':<25} {'Location'}")
    print("-" * 110)
    for i, job in enumerate(scored_jobs[:10], 1):
        display_score = job.claude_score if job.claude_score is not None else job.match_score
        score_pct = f"{display_score * 100:.1f}%"
        print(f"{i:<5} {score_pct:>6}  {job.title[:38]:<40} {job.company[:23]:<25} {job.location}")

    # 8. Export
    print()
    write_output(scored_jobs, profile, args.output, args.top, stats=stats, charts=charts)
    print("\nDone.")


if __name__ == "__main__":
    main()
