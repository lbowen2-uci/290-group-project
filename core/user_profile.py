from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UserProfile:
    """Unified user profile produced by either resume parsing or Q&A mode."""
    name: str = ""
    email: str = ""
    skills: list[str] = field(default_factory=list)
    job_titles: list[str] = field(default_factory=list)
    location: str = ""
    remote_ok: bool = False
    experience_years: int = 0
    education: str = ""
    industry: str = ""
    job_type: str = "full-time"  # full-time, part-time, contract, internship
    goals: str = ""
    raw_text: str = ""  # full text blob used for semantic matching

    def to_search_query(self) -> str:
        """Build a concise search string for job API queries."""
        parts = []
        if self.job_titles:
            parts.append(self.job_titles[0])
        if self.skills:
            parts.extend(self.skills[:5])
        return " ".join(parts)

    def to_profile_text(self) -> str:
        """Combine all profile fields into a single text blob for embedding."""
        sections = [
            f"Target roles: {', '.join(self.job_titles)}" if self.job_titles else "",
            f"Skills: {', '.join(self.skills)}" if self.skills else "",
            f"Experience: {self.experience_years} years",
            f"Education: {self.education}" if self.education else "",
            f"Industry: {self.industry}" if self.industry else "",
            f"Goals: {self.goals}" if self.goals else "",
            self.raw_text,
        ]
        return "\n".join(s for s in sections if s)


@dataclass
class Job:
    """Normalized job posting from any scraper source."""
    title: str = ""
    company: str = ""
    location: str = ""
    description: str = ""
    url: str = ""
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: str = "USD"
    job_type: str = ""
    source: str = ""
    posted_date: str = ""
    match_score: float = 0.0
    matched_skills: list[str] = field(default_factory=list)

    def dedup_key(self) -> str:
        """Unique key for deduplication across scrapers."""
        return f"{self.title.lower()}|{self.company.lower()}|{self.location.lower()}"

    def salary_display(self) -> str:
        if self.salary_min and self.salary_max:
            return f"${self.salary_min:,.0f} – ${self.salary_max:,.0f}"
        if self.salary_min:
            return f"${self.salary_min:,.0f}+"
        if self.salary_max:
            return f"Up to ${self.salary_max:,.0f}"
        return "Not listed"
