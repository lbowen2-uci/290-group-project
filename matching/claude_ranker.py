"""
Claude-powered job re-ranker. After keyword/semantic pre-filtering,
Claude evaluates the top N jobs with nuanced reasoning about career fit,
growth potential, and skill alignment — beyond what cosine similarity captures.

Uses prompt caching: the candidate profile is cached in the system prompt,
so only the job batches are billed at full rate on repeated calls.
"""

from core.user_profile import UserProfile, Job
from core.claude_client import cached_profile_system, call_claude_json

_SYSTEM_PERSONA = (
    "You are an expert career advisor evaluating job postings for a specific candidate. "
    "You understand that good fit goes beyond keyword matching — consider career trajectory, "
    "growth potential, culture signals in job descriptions, and realistic skill gaps. "
    "Be honest about concerns without being unnecessarily harsh."
)

_BATCH_PROMPT = """Evaluate the following job postings for the candidate described in your system prompt.

For each job return a JSON object with:
- "job_index": integer (matches the index below)
- "adjusted_score": integer 0-100 representing overall fit
- "fit_reasoning": 3-5 word phrase summarizing fit (e.g. "good salary, skill gap in SQL")
- "growth_potential": "high", "medium", or "low" — does this role advance their career goals?
- "key_match": the single strongest alignment point between candidate and role
- "concern": 3-5 word phrase for the biggest gap or risk (e.g. "missing cloud exp"), or "none"

Return a JSON array of these objects, one per job.

<jobs>
{jobs_block}
</jobs>"""


def _format_jobs_block(jobs: list[Job], indices: list[int]) -> str:
    lines = []
    for idx, job in zip(indices, jobs):
        desc_snippet = job.description[:800].replace("\n", " ").strip() if job.description else ""
        lines.append(
            f"[Job {idx}]\n"
            f"Title: {job.title}\n"
            f"Company: {job.company}\n"
            f"Location: {job.location or 'Not specified'}\n"
            f"Type: {job.job_type or 'Not specified'}\n"
            f"Description: {desc_snippet}"
        )
    return "\n\n".join(lines)


def rerank_with_claude(
    profile: UserProfile,
    jobs: list[Job],
    top_n: int = 25,
    batch_size: int = 10,
    model: str = "claude-sonnet-4-6",
) -> list[Job]:
    """
    Re-rank the top N pre-scored jobs using Claude.

    The system prompt (with full profile) is cached after the first batch call,
    so subsequent batches hit the cache. Jobs outside top_n are appended unchanged.
    """
    if not jobs:
        return jobs

    to_rerank = jobs[:top_n]
    remainder = jobs[top_n:]

    system = cached_profile_system(profile.to_profile_text(), persona=_SYSTEM_PERSONA)

    # Process in batches
    results_map: dict[int, dict] = {}
    for batch_start in range(0, len(to_rerank), batch_size):
        batch = to_rerank[batch_start: batch_start + batch_size]
        indices = list(range(batch_start, batch_start + len(batch)))

        jobs_block = _format_jobs_block(batch, indices)
        try:
            raw = call_claude_json(
                system=system,
                user_message=_BATCH_PROMPT.format(jobs_block=jobs_block),
                model=model,
                max_tokens=2048,
            )
            if isinstance(raw, list):
                for entry in raw:
                    idx = entry.get("job_index")
                    if idx is not None:
                        results_map[idx] = entry
        except Exception as e:
            print(f"[claude_ranker] Batch {batch_start // batch_size + 1} failed: {e}")
            # Jobs in this batch keep their original match_score

    # Apply Claude scores back to job objects
    for i, job in enumerate(to_rerank):
        entry = results_map.get(i)
        if entry:
            raw_score = entry.get("adjusted_score")
            if raw_score is not None:
                job.claude_score = round(float(raw_score) / 100, 4)
            job.fit_reasoning = str(entry.get("fit_reasoning") or "")
            job.growth_potential = str(entry.get("growth_potential") or "")
            job.key_match = str(entry.get("key_match") or "")
            job.concern = str(entry.get("concern") or "")

    # Sort re-ranked jobs by claude_score (fallback to match_score)
    to_rerank.sort(
        key=lambda j: j.claude_score if j.claude_score is not None else j.match_score,
        reverse=True,
    )

    ranked_count = sum(1 for j in to_rerank if j.claude_score is not None)
    print(f"[claude_ranker] Re-ranked {ranked_count}/{len(to_rerank)} jobs with Claude.")

    return to_rerank + remainder
