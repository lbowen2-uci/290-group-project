"""
Aggregate statistics computed from a scored job list and user profile.
Pure Python — no I/O, no matplotlib. Easy to unit-test independently.
"""

import re
import collections
from datetime import datetime, timedelta

from core.user_profile import Job, UserProfile
from core.profile_builder import extract_skills_from_text, normalize_skills


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

def _parse_date(date_str: str) -> datetime | None:
    """Parse various posted-date formats to a datetime, or return None."""
    if not date_str:
        return None
    s = date_str.strip()
    sl = s.lower()

    # Relative strings
    m = re.search(r'(\d+)\s+day', sl)
    if m:
        return datetime.now() - timedelta(days=int(m.group(1)))
    m = re.search(r'(\d+)\s+week', sl)
    if m:
        return datetime.now() - timedelta(weeks=int(m.group(1)))
    m = re.search(r'(\d+)\s+month', sl)
    if m:
        return datetime.now() - timedelta(days=int(m.group(1)) * 30)
    if re.search(r'today|just\s+posted', sl):
        return datetime.now()
    if 'yesterday' in sl:
        return datetime.now() - timedelta(days=1)

    # Standard formats
    for fmt in (
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S+00:00",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%m-%d-%Y",
    ):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Internal metric computers
# ---------------------------------------------------------------------------

def _percentile(sorted_vals: list[float], pct: float) -> float | None:
    """Linear-interpolation percentile on a pre-sorted list."""
    if not sorted_vals:
        return None
    idx = (len(sorted_vals) - 1) * pct
    lo = int(idx)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (idx - lo)


def _time_on_market(jobs: list[Job]) -> dict:
    now = datetime.now()
    ages = []
    for job in jobs:
        dt = _parse_date(job.posted_date)
        if dt:
            age = (now - dt).days
            if 0 <= age <= 365:
                ages.append(age)

    buckets = {"0-7": 0, "8-14": 0, "15-30": 0, "31-60": 0, "60+": 0}
    if not ages:
        return {
            "n_with_date": 0,
            "avg_days": None,
            "median_days": None,
            "p25": None,
            "p75": None,
            "histogram_buckets": buckets,
        }

    for age in ages:
        if age <= 7:
            buckets["0-7"] += 1
        elif age <= 14:
            buckets["8-14"] += 1
        elif age <= 30:
            buckets["15-30"] += 1
        elif age <= 60:
            buckets["31-60"] += 1
        else:
            buckets["60+"] += 1

    sv = sorted(ages)
    return {
        "n_with_date": len(sv),
        "avg_days": round(sum(sv) / len(sv), 1),
        "median_days": round(_percentile(sv, 0.5), 1),
        "p25": round(_percentile(sv, 0.25), 1),
        "p75": round(_percentile(sv, 0.75), 1),
        "histogram_buckets": buckets,
    }


def _top_skills(jobs: list[Job], n: int = 20) -> list[dict]:
    counter: collections.Counter = collections.Counter()
    n_jobs = len(jobs)
    for job in jobs:
        if job.description:
            for skill in extract_skills_from_text(job.description):
                counter[skill] += 1

    return [
        {
            "skill": skill,
            "count": count,
            "pct_of_jobs": round(count / n_jobs * 100, 1) if n_jobs else 0.0,
        }
        for skill, count in counter.most_common(n)
    ]


def _skill_gap(profile: UserProfile, top_skills: list[dict], n: int = 10) -> dict:
    user_set = set(normalize_skills(profile.skills))
    missing = []
    for entry in top_skills[:20]:
        if entry["skill"] not in user_set and len(missing) < n:
            missing.append({"skill": entry["skill"], "demand_count": entry["count"]})
    return {
        "user_skills": sorted(user_set),
        "top_demanded": [e["skill"] for e in top_skills[:10]],
        "missing": missing,
    }


def _salary_distribution(jobs: list[Job]) -> dict:
    midpoints: list[float] = []
    for job in jobs:
        if job.salary_min is not None and job.salary_max is not None:
            midpoints.append((job.salary_min + job.salary_max) / 2)
        elif job.salary_min is not None:
            midpoints.append(job.salary_min)
        elif job.salary_max is not None:
            midpoints.append(job.salary_max)

    if not midpoints:
        return {
            "n_with_salary": 0,
            "min": None,
            "p25": None,
            "median": None,
            "p75": None,
            "max": None,
            "currency_assumption": "USD",
        }

    sv = sorted(midpoints)
    return {
        "n_with_salary": len(sv),
        "min": round(min(sv), 0),
        "p25": round(_percentile(sv, 0.25), 0),
        "median": round(_percentile(sv, 0.5), 0),
        "p75": round(_percentile(sv, 0.75), 0),
        "max": round(max(sv), 0),
        "currency_assumption": "USD",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_stats(jobs: list[Job], profile: UserProfile) -> dict:
    """
    Compute aggregate market statistics from a list of scored Job objects.

    Returns a dict with keys: meta, time_on_market, top_skills, skill_gap, salary.
    """
    sources = dict(collections.Counter(j.source for j in jobs))
    top_skills_data = _top_skills(jobs)

    return {
        "meta": {
            "total_jobs": len(jobs),
            "sources": sources,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        },
        "time_on_market": _time_on_market(jobs),
        "top_skills": top_skills_data,
        "skill_gap": _skill_gap(profile, top_skills_data),
        "salary": _salary_distribution(jobs),
    }
