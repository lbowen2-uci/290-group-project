"""
Fast keyword-based matching using TF-IDF + cosine similarity (scikit-learn).
Used as a quick pre-filter before the more expensive semantic matcher.

Install: pip install scikit-learn
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from core.user_profile import UserProfile, Job


def score_jobs_keyword(profile: UserProfile, jobs: list[Job]) -> list[Job]:
    """
    Score each job against the user profile using TF-IDF cosine similarity.
    Also tags which profile skills appear in the job description.

    Args:
        profile: The user's profile.
        jobs:    List of Job objects to score.

    Returns:
        Jobs with match_score and matched_skills populated, sorted descending.
    """
    if not jobs:
        return []

    profile_text = profile.to_profile_text()
    job_texts = [f"{job.title} {job.company} {job.description}" for job in jobs]

    corpus = [profile_text] + job_texts

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=10_000,
        sublinear_tf=True,
    )
    try:
        tfidf_matrix = vectorizer.fit_transform(corpus)
    except ValueError:
        # Empty vocabulary edge case
        return jobs

    profile_vec = tfidf_matrix[0:1]
    job_vecs = tfidf_matrix[1:]

    scores = cosine_similarity(profile_vec, job_vecs)[0]

    for job, score in zip(jobs, scores):
        job.match_score = round(float(score), 4)
        job.matched_skills = _find_matched_skills(profile.skills, job.description)

    return sorted(jobs, key=lambda j: j.match_score, reverse=True)


def _find_matched_skills(profile_skills: list[str], job_description: str) -> list[str]:
    """Return the subset of profile skills that appear in the job description."""
    desc_lower = job_description.lower()
    return [skill for skill in profile_skills if skill.lower() in desc_lower]
