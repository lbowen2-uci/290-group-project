"""
Claude-powered resume parser. Replaces regex/spaCy extraction with a Claude
API call that understands career trajectory, infers goals, and reads context
that heuristic parsers miss entirely.

Requires: ANTHROPIC_API_KEY set in .env
Falls back to: core/resume_parser.py (regex/spaCy) if Claude is unavailable.
"""

from core.user_profile import UserProfile
from core.resume_parser import extract_text_from_pdf
from core.claude_client import call_claude_json

_SYSTEM = [
    {
        "type": "text",
        "text": (
            "You are an expert resume analyst and career advisor. "
            "When given a resume, extract a structured profile that goes beyond "
            "surface-level facts — infer career trajectory, identify what the person "
            "is genuinely good at, and determine what they likely want next based on "
            "how their career has evolved. Return ONLY valid JSON, no commentary."
        ),
    }
]

_USER_TEMPLATE = """Analyze this resume and return a JSON object with exactly these fields:

{{
  "name": "full name or empty string",
  "email": "email address or empty string",
  "skills": ["list of technical and professional skills, normalized to lowercase"],
  "job_titles": ["list of target/held job titles, most relevant first"],
  "location": "city/metro they are in or targeting, or empty string",
  "remote_ok": true or false,
  "experience_years": integer number of professional years,
  "education": "highest degree level: PhD, Master's, Bachelor's, Associate's, or empty",
  "industry": "primary industry or domain",
  "job_type": "full-time, part-time, contract, or internship",
  "goals": "what this person states they want next",
  "career_narrative": "2-3 sentences describing their career trajectory and direction — not just a summary of what they did, but where they are heading and why",
  "inferred_goals": "based on career trajectory, what does this person likely want in their next role even if they didn't explicitly state it",
  "strengths": ["3-6 genuine strengths inferred from their experience pattern, not just listed skills"],
  "career_level": "entry, mid, senior, lead, or executive"
}}

<resume>
{resume_text}
</resume>"""


def parse_resume_with_claude(pdf_path: str, model: str = "claude-sonnet-4-6") -> UserProfile:
    """
    Extract a rich UserProfile from a PDF resume using Claude.
    Reuses pdfminer text extraction from the existing resume_parser module.
    """
    from pathlib import Path
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"Resume file not found: {pdf_path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got: {path.suffix}")

    print(f"Parsing resume with Claude: {path.name}")
    raw_text = extract_text_from_pdf(pdf_path)

    if not raw_text.strip():
        raise ValueError("Could not extract text from PDF. The file may be scanned/image-based.")

    data = call_claude_json(
        system=_SYSTEM,
        user_message=_USER_TEMPLATE.format(resume_text=raw_text[:15000]),
        model=model,
        max_tokens=2048,
    )

    profile = UserProfile(
        name=str(data.get("name") or ""),
        email=str(data.get("email") or ""),
        skills=[str(s) for s in data.get("skills") or []],
        job_titles=[str(t) for t in data.get("job_titles") or []],
        location=str(data.get("location") or ""),
        remote_ok=bool(data.get("remote_ok", False)),
        experience_years=int(data.get("experience_years") or 0),
        education=str(data.get("education") or ""),
        industry=str(data.get("industry") or ""),
        job_type=str(data.get("job_type") or "full-time"),
        goals=str(data.get("goals") or ""),
        raw_text=raw_text,
        career_narrative=str(data.get("career_narrative") or ""),
        inferred_goals=str(data.get("inferred_goals") or ""),
        strengths=[str(s) for s in data.get("strengths") or []],
        career_level=str(data.get("career_level") or ""),
    )

    print(f"  Name:       {profile.name or '(not detected)'}")
    print(f"  Email:      {profile.email or '(not detected)'}")
    print(f"  Skills:     {', '.join(profile.skills[:8])}{'...' if len(profile.skills) > 8 else ''}")
    print(f"  Titles:     {', '.join(profile.job_titles) or '(not detected)'}")
    print(f"  Experience: {profile.experience_years} years ({profile.career_level})")
    print(f"  Education:  {profile.education or '(not detected)'}")
    print(f"  Location:   {profile.location or '(use --location to set)'}")
    print(f"  Narrative:  {profile.career_narrative[:120]}..." if len(profile.career_narrative) > 120 else f"  Narrative:  {profile.career_narrative}")

    return profile
