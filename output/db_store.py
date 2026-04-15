"""
SQLite storage for job results.
Handles deduplication across runs and tracks search history.

Uses Python stdlib sqlite3 — no extra dependencies needed.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from core.user_profile import UserProfile, Job

DEFAULT_DB_PATH = "jobs.db"


def _get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Create tables if they don't exist."""
    conn = _get_connection(db_path)
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS searches (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                run_at      TEXT NOT NULL,
                profile_name TEXT,
                query       TEXT,
                total_found INTEGER
            );

            CREATE TABLE IF NOT EXISTS jobs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                search_id       INTEGER,
                title           TEXT,
                company         TEXT,
                location        TEXT,
                salary_min      REAL,
                salary_max      REAL,
                job_type        TEXT,
                source          TEXT,
                posted_date     TEXT,
                url             TEXT UNIQUE,
                description     TEXT,
                match_score     REAL,
                matched_skills  TEXT,
                first_seen      TEXT,
                FOREIGN KEY (search_id) REFERENCES searches(id)
            );

            CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(match_score DESC);
            CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);
        """)
    conn.close()


def save_results(
    jobs: list[Job],
    profile: UserProfile,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    """
    Save a list of scored jobs to the database.
    Skips duplicates (by URL). Returns the search_id.
    """
    init_db(db_path)
    conn = _get_connection(db_path)
    now = datetime.utcnow().isoformat()

    with conn:
        cursor = conn.execute(
            "INSERT INTO searches (run_at, profile_name, query, total_found) VALUES (?, ?, ?, ?)",
            (now, profile.name, profile.to_search_query(), len(jobs)),
        )
        search_id = cursor.lastrowid

        inserted = 0
        for job in jobs:
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO jobs
                       (search_id, title, company, location, salary_min, salary_max,
                        job_type, source, posted_date, url, description,
                        match_score, matched_skills, first_seen)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        search_id,
                        job.title,
                        job.company,
                        job.location,
                        job.salary_min,
                        job.salary_max,
                        job.job_type,
                        job.source,
                        job.posted_date,
                        job.url,
                        job.description[:5000],  # cap description size
                        job.match_score,
                        json.dumps(job.matched_skills),
                        now,
                    ),
                )
                inserted += 1
            except sqlite3.Error:
                pass  # duplicate URL — skip silently

    conn.close()
    print(f"[db] Saved {inserted} new jobs (search_id={search_id}) → {Path(db_path).resolve()}")
    return search_id


def query_top_jobs(
    db_path: str = DEFAULT_DB_PATH,
    limit: int = 20,
    min_score: float = 0.0,
) -> list[dict]:
    """Return the top-scored jobs across all searches."""
    if not Path(db_path).exists():
        return []
    conn = _get_connection(db_path)
    rows = conn.execute(
        """SELECT title, company, location, match_score, salary_min, salary_max,
                  source, url, matched_skills
           FROM jobs
           WHERE match_score >= ?
           ORDER BY match_score DESC
           LIMIT ?""",
        (min_score, limit),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
