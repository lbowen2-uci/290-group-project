"""
High-quality semantic matching using sentence-transformers.
Understands meaning, not just keywords — e.g. "data wrangling" ≈ "ETL pipelines".

Install: pip install sentence-transformers
Model download happens automatically on first run (~90MB).
"""

from core.user_profile import UserProfile, Job

DEFAULT_MODEL = "all-MiniLM-L6-v2"  # Fast + accurate; 384-dim embeddings


def score_jobs_semantic(
    profile: UserProfile,
    jobs: list[Job],
    model_name: str = DEFAULT_MODEL,
    batch_size: int = 32,
) -> list[Job]:
    """
    Score each job against the user profile using sentence embeddings
    and cosine similarity.

    Args:
        profile:    The user's profile.
        jobs:       List of Job objects to score.
        model_name: Sentence-transformers model to use.
        batch_size: Encoding batch size.

    Returns:
        Jobs with match_score populated, sorted descending.
    """
    if not jobs:
        return []

    try:
        from sentence_transformers import SentenceTransformer, util
    except ImportError:
        raise ImportError(
            "sentence-transformers is required for semantic matching.\n"
            "Install it with: pip install sentence-transformers"
        )

    print(f"[semantic] Loading model '{model_name}'...")
    model = SentenceTransformer(model_name)

    profile_text = profile.to_profile_text()
    job_texts = [f"{job.title}\n{job.company}\n{job.description[:1000]}" for job in jobs]

    print(f"[semantic] Encoding {len(jobs)} job descriptions...")
    profile_embedding = model.encode(profile_text, convert_to_tensor=True)
    job_embeddings = model.encode(job_texts, batch_size=batch_size, convert_to_tensor=True, show_progress_bar=True)

    scores = util.pytorch_cos_sim(profile_embedding, job_embeddings)[0]

    for job, score in zip(jobs, scores):
        job.match_score = round(float(score), 4)
        if not job.matched_skills:
            job.matched_skills = _find_matched_skills(profile.skills, job.description)

    return sorted(jobs, key=lambda j: j.match_score, reverse=True)


def _find_matched_skills(profile_skills: list[str], job_description: str) -> list[str]:
    desc_lower = job_description.lower()
    return [skill for skill in profile_skills if skill.lower() in desc_lower]
