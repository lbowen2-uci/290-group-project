"""
Parse a PDF resume and produce a UserProfile.

Dependencies: pdfminer.six, spacy (en_core_web_sm)
Install:
    pip install pdfminer.six spacy
    python -m spacy download en_core_web_sm
"""

import re
from io import StringIO
from pathlib import Path

from core.user_profile import UserProfile
from core.profile_builder import (
    normalize_skills,
    extract_skills_from_text,
    extract_experience_years,
    extract_education,
)


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract raw text from a PDF file using pdfminer.six."""
    try:
        from pdfminer.high_level import extract_text
        return extract_text(pdf_path)
    except ImportError:
        raise ImportError(
            "pdfminer.six is required for PDF parsing.\n"
            "Install it with: pip install pdfminer.six"
        )


def extract_email(text: str) -> str:
    match = re.search(r'[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}', text)
    return match.group(0) if match else ""


def extract_name_spacy(text: str) -> str:
    """Use spaCy NER to find the first PERSON entity (likely the candidate name)."""
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text[:500])  # name is almost always near the top
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                return ent.text.strip()
    except Exception:
        pass
    return ""


def extract_job_titles_spacy(text: str) -> list[str]:
    """
    Heuristic: look for common title patterns and spaCy noun chunks
    near section headers like 'Experience' or 'Work History'.
    """
    title_patterns = [
        r'(?:^|\n)([A-Z][a-zA-Z\s/]+(?:Analyst|Engineer|Scientist|Developer|Manager|'
        r'Consultant|Specialist|Director|Associate|Intern|Lead|Architect|Designer|'
        r'Coordinator|Officer|Executive|Advisor|Researcher))',
    ]
    titles = []
    seen = set()
    for pattern in title_patterns:
        for match in re.finditer(pattern, text, re.MULTILINE):
            title = match.group(1).strip()
            if title.lower() not in seen and len(title) < 60:
                seen.add(title.lower())
                titles.append(title)
    return titles[:5]


def parse_resume(pdf_path: str) -> UserProfile:
    """
    Parse a PDF resume and return a populated UserProfile.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        UserProfile with extracted fields.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"Resume file not found: {pdf_path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got: {path.suffix}")

    print(f"Parsing resume: {path.name}")
    raw_text = extract_text_from_pdf(pdf_path)

    if not raw_text.strip():
        raise ValueError("Could not extract text from PDF. The file may be scanned/image-based.")

    name = extract_name_spacy(raw_text)
    email = extract_email(raw_text)
    skills = normalize_skills(extract_skills_from_text(raw_text))
    job_titles = extract_job_titles_spacy(raw_text)
    experience_years = extract_experience_years(raw_text)
    education = extract_education(raw_text)

    profile = UserProfile(
        name=name,
        email=email,
        skills=skills,
        job_titles=job_titles,
        experience_years=experience_years,
        education=education,
        raw_text=raw_text,
    )

    print(f"  Name:       {profile.name or '(not detected)'}")
    print(f"  Email:      {profile.email or '(not detected)'}")
    print(f"  Skills:     {', '.join(profile.skills[:8])}{'...' if len(profile.skills) > 8 else ''}")
    print(f"  Titles:     {', '.join(profile.job_titles) or '(not detected)'}")
    print(f"  Experience: {profile.experience_years} years")
    print(f"  Education:  {profile.education or '(not detected)'}")
    print(f"  Location:   {profile.location or '(use --location to set)'}")

    return profile
