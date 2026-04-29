"""
Export job results to CSV or Excel using pandas.

Install: pip install pandas openpyxl
"""

import pandas as pd
from pathlib import Path
from core.user_profile import Job


def export_csv(jobs: list[Job], output_path: str = "jobs_output.csv") -> str:
    """
    Write jobs to a CSV file.

    Args:
        jobs:        List of scored Job objects.
        output_path: Destination file path.

    Returns:
        Absolute path to the written file.
    """
    rows = _jobs_to_rows(jobs)
    df = pd.DataFrame(rows)
    path = Path(output_path)
    df.to_csv(path, index=False)
    print(f"[csv] Exported {len(jobs)} jobs → {path.resolve()}")
    return str(path.resolve())


def export_excel(jobs: list[Job], output_path: str = "jobs_output.xlsx") -> str:
    """
    Write jobs to an Excel file with basic formatting.

    Args:
        jobs:        List of scored Job objects.
        output_path: Destination file path.

    Returns:
        Absolute path to the written file.
    """
    rows = _jobs_to_rows(jobs)
    df = pd.DataFrame(rows)
    path = Path(output_path)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Job Results")
        ws = writer.sheets["Job Results"]
        # Auto-size columns
        for col in ws.columns:
            max_len = max((len(str(cell.value or "")) for cell in col), default=10)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 60)

    print(f"[excel] Exported {len(jobs)} jobs → {path.resolve()}")
    return str(path.resolve())


def _jobs_to_rows(jobs: list[Job]) -> list[dict]:
    return [
        {
            "match_score": round(job.match_score * 100, 1),
            "claude_score": round(job.claude_score * 100, 1) if job.claude_score is not None else "",
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "salary": job.salary_display(),
            "source": job.source,
            "posted_date": job.posted_date,
            "matched_skills": ", ".join(job.matched_skills),
            "growth_potential": job.growth_potential,
            "fit_reasoning": job.fit_reasoning,
            "concern": job.concern,
            "url": job.url,
        }
        for job in jobs
    ]
