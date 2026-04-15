"""
Interactive Q&A mode — ask the user a series of questions
and return a populated UserProfile without needing a resume.
"""

from core.user_profile import UserProfile
from core.profile_builder import normalize_skills


def _prompt(question: str, default: str = "") -> str:
    """Display a prompt and return stripped input. Returns default if blank."""
    suffix = f" [{default}]" if default else ""
    try:
        answer = input(f"\n{question}{suffix}\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    return answer if answer else default


def _prompt_list(question: str, hint: str = "comma-separated") -> list[str]:
    """Prompt for a comma-separated list and return cleaned items."""
    raw = _prompt(f"{question} ({hint})")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _prompt_int(question: str, default: int = 0) -> int:
    raw = _prompt(question, str(default))
    try:
        return int(raw)
    except ValueError:
        return default


def _prompt_bool(question: str, default: bool = False) -> bool:
    default_str = "y" if default else "n"
    raw = _prompt(f"{question} (y/n)", default_str).lower()
    return raw in ("y", "yes", "1", "true")


def run_questionnaire() -> UserProfile:
    """
    Walk the user through a series of prompts and build a UserProfile.

    Returns:
        A populated UserProfile ready for job searching and matching.
    """
    print("\n" + "=" * 60)
    print("  Job Search Profile Builder — Q&A Mode")
    print("  Press Enter to skip any question.")
    print("=" * 60)

    # --- Identity ---
    name = _prompt("1. What is your name?")
    email = _prompt("2. What is your email address?")

    # --- Role targeting ---
    raw_titles = _prompt_list(
        "3. What job titles are you targeting?",
        hint="e.g. Data Analyst, Business Analyst, Data Scientist",
    )
    job_titles = raw_titles if raw_titles else []

    # --- Skills ---
    raw_skills = _prompt_list(
        "4. List your top skills",
        hint="e.g. Python, SQL, Tableau, Machine Learning, Excel",
    )
    skills = normalize_skills(raw_skills)

    # --- Experience ---
    experience_years = _prompt_int(
        "5. How many years of professional experience do you have?", default=0
    )

    # --- Education ---
    print("\n6. What is your highest level of education?")
    print("   Options: High School, Associate's, Bachelor's, Master's, PhD, Other")
    education = _prompt("   Your answer", default="Bachelor's")

    # --- Location ---
    location = _prompt(
        "7. What city/metro are you targeting?",
        default="",
    )
    remote_ok = _prompt_bool(
        "8. Are you open to remote positions?", default=True
    )

    # --- Industry ---
    industry = _prompt(
        "9. What industry or domain are you targeting?",
        default="",
    )

    # --- Job type ---
    print("\n10. What type of employment are you looking for?")
    print("    Options: full-time, part-time, contract, internship")
    job_type = _prompt("    Your answer", default="full-time").lower()
    if job_type not in ("full-time", "part-time", "contract", "internship"):
        job_type = "full-time"

    # --- Goals ---
    goals = _prompt(
        "11. What matters most to you in your next role?",
        default="",
    )

    profile = UserProfile(
        name=name,
        email=email,
        skills=skills,
        job_titles=job_titles,
        location=location,
        remote_ok=remote_ok,
        experience_years=experience_years,
        education=education,
        industry=industry,
        job_type=job_type,
        goals=goals,
        raw_text="",
    )

    print("\n" + "=" * 60)
    print("  Profile Summary")
    print("=" * 60)
    print(f"  Name:        {profile.name or '(skipped)'}")
    print(f"  Targeting:   {', '.join(profile.job_titles) or '(skipped)'}")
    print(f"  Skills:      {', '.join(profile.skills[:8]) or '(skipped)'}")
    print(f"  Location:    {profile.location or 'Any'} | Remote: {'Yes' if profile.remote_ok else 'No'}")
    print(f"  Experience:  {profile.experience_years} years")
    print(f"  Education:   {profile.education or '(skipped)'}")
    print(f"  Industry:    {profile.industry or '(skipped)'}")
    print(f"  Job type:    {profile.job_type}")
    print(f"  Goals:       {profile.goals or '(skipped)'}")
    print("=" * 60)

    return profile
