"""
Write aggregate market statistics to standalone files:
  - stats.json   (machine-readable)
  - stats.md     (human-readable markdown with tables)
  - charts/*.png (one PNG per chart)
"""

import json
from pathlib import Path


def export_stats_json(stats: dict, path: str = "stats.json") -> None:
    p = Path(path)
    p.write_text(json.dumps(stats, indent=2, default=str), encoding="utf-8")
    print(f"[stats] JSON  → {p.resolve()}")


def export_stats_markdown(stats: dict, path: str = "stats.md") -> None:
    p = Path(path)
    p.write_text("\n".join(_render_markdown(stats)), encoding="utf-8")
    print(f"[stats] MD    → {p.resolve()}")


def export_stats_charts(charts: dict[str, bytes], output_dir: str = "charts") -> None:
    if not charts:
        return
    d = Path(output_dir)
    d.mkdir(exist_ok=True)
    for name, png_bytes in charts.items():
        (d / f"{name}.png").write_bytes(png_bytes)
    print(f"[stats] Charts → {d.resolve()}/")


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------

def _fmt_salary(val) -> str:
    return f"${val:,.0f}" if val is not None else "N/A"


def _render_markdown(stats: dict) -> list[str]:
    lines: list[str] = ["# Job Market Summary Statistics", ""]

    meta = stats.get("meta", {})
    lines += [
        f"**Generated:** {meta.get('generated_at', 'N/A')}  ",
        f"**Total Jobs Analyzed:** {meta.get('total_jobs', 0)}  ",
    ]
    sources = meta.get("sources", {})
    if sources:
        lines.append("**Sources:** " + ", ".join(f"{k}: {v}" for k, v in sources.items()) + "  ")
    lines.append("")

    # ---- Time on market ----
    tom = stats.get("time_on_market", {})
    lines += ["## Time on Market", ""]
    if tom.get("n_with_date"):
        lines += [
            "| Metric | Value |",
            "|--------|-------|",
            f"| Jobs with date | {tom['n_with_date']} |",
            f"| Average (days) | {tom.get('avg_days', 'N/A')} |",
            f"| Median (days) | {tom.get('median_days', 'N/A')} |",
            f"| 25th percentile | {tom.get('p25', 'N/A')} |",
            f"| 75th percentile | {tom.get('p75', 'N/A')} |",
            "",
        ]
        buckets = tom.get("histogram_buckets", {})
        if buckets:
            lines += ["**Distribution:**", "", "| Range | Jobs |", "|-------|------|"]
            for label, count in buckets.items():
                lines.append(f"| {label} days | {count} |")
            lines.append("")
    else:
        lines += ["*No posting date data available.*", ""]

    # ---- Top skills ----
    top_skills = stats.get("top_skills", [])
    lines += ["## Top Skills Demanded", ""]
    if top_skills:
        lines += ["| Skill | # Jobs | % of Listings |", "|-------|--------|----------------|"]
        for s in top_skills[:15]:
            lines.append(f"| {s['skill']} | {s['count']} | {s['pct_of_jobs']}% |")
        lines.append("")
    else:
        lines += ["*No skill data available.*", ""]

    # ---- Skill gap ----
    gap = stats.get("skill_gap", {})
    missing = gap.get("missing", [])
    lines += ["## Skill Gap Analysis", ""]
    if missing:
        lines += [
            "Skills in demand **not on your profile:**",
            "",
            "| Skill | Jobs Requiring It |",
            "|-------|------------------|",
        ]
        for m in missing:
            lines.append(f"| {m['skill']} | {m['demand_count']} |")
        lines.append("")
    else:
        lines += ["*No skill gap detected (or no demanded skills found).*", ""]

    # ---- Salary ----
    salary = stats.get("salary", {})
    lines += ["## Salary Distribution", ""]
    if salary.get("n_with_salary"):
        currency = salary.get("currency_assumption", "USD")
        lines += [
            f"Based on **{salary['n_with_salary']}** listings reporting salary ({currency}):  ",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Minimum | {_fmt_salary(salary.get('min'))} |",
            f"| 25th percentile | {_fmt_salary(salary.get('p25'))} |",
            f"| Median | {_fmt_salary(salary.get('median'))} |",
            f"| 75th percentile | {_fmt_salary(salary.get('p75'))} |",
            f"| Maximum | {_fmt_salary(salary.get('max'))} |",
            "",
        ]
    else:
        lines += ["*No salary data reported in current listings.*", ""]

    return lines
