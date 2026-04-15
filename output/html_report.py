"""
Generate a ranked HTML report of job matches.
Uses an inline Jinja2 template — no external template files needed.

Install: pip install jinja2
"""

from pathlib import Path
from datetime import datetime
from core.user_profile import UserProfile, Job

try:
    from jinja2 import Environment, BaseLoader
    _JINJA_AVAILABLE = True
except ImportError:
    _JINJA_AVAILABLE = False


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Job Match Report — {{ profile.name or "User" }}</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         max-width: 960px; margin: 0 auto; padding: 24px; background: #f8f9fa; color: #212529; }
  h1   { color: #343a40; margin-bottom: 4px; }
  .meta { color: #6c757d; font-size: 14px; margin-bottom: 32px; }
  .job  { background: #fff; border-radius: 8px; padding: 20px; margin-bottom: 16px;
          box-shadow: 0 1px 3px rgba(0,0,0,.1); }
  .job-header { display: flex; justify-content: space-between; align-items: flex-start; }
  .title  { font-size: 18px; font-weight: 600; margin: 0; }
  .company { font-size: 15px; color: #495057; margin: 4px 0; }
  .location { color: #6c757d; font-size: 13px; }
  .score-badge { font-size: 13px; font-weight: 700; padding: 4px 10px;
                 border-radius: 20px; white-space: nowrap; }
  .score-high   { background: #d4edda; color: #155724; }
  .score-medium { background: #fff3cd; color: #856404; }
  .score-low    { background: #f8d7da; color: #721c24; }
  .score-bar-wrap { margin: 10px 0 8px; background: #e9ecef; border-radius: 4px; height: 6px; }
  .score-bar { height: 6px; border-radius: 4px; background: #0d6efd; }
  .meta-row { display: flex; gap: 16px; flex-wrap: wrap; font-size: 13px;
              color: #495057; margin-top: 8px; }
  .skills { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; }
  .skill-tag { background: #e7f0ff; color: #0052cc; font-size: 12px;
               padding: 2px 8px; border-radius: 12px; }
  .apply-btn { display: inline-block; margin-top: 12px; padding: 7px 16px;
               background: #0d6efd; color: #fff; text-decoration: none;
               border-radius: 6px; font-size: 13px; }
  .apply-btn:hover { background: #0b5ed7; }
  .summary { background: #fff; border-radius: 8px; padding: 20px; margin-bottom: 24px;
             box-shadow: 0 1px 3px rgba(0,0,0,.1); }
  .summary h2 { margin-top: 0; font-size: 16px; }
  .summary p  { margin: 4px 0; font-size: 14px; color: #495057; }
</style>
</head>
<body>
<h1>Job Match Report</h1>
<p class="meta">Generated {{ generated_at }} &bull; {{ jobs|length }} results</p>

<div class="summary">
  <h2>Your Profile</h2>
  {% if profile.name %}<p><strong>Name:</strong> {{ profile.name }}</p>{% endif %}
  {% if profile.job_titles %}<p><strong>Targeting:</strong> {{ profile.job_titles | join(", ") }}</p>{% endif %}
  {% if profile.skills %}<p><strong>Skills:</strong> {{ profile.skills[:10] | join(", ") }}</p>{% endif %}
  {% if profile.location %}<p><strong>Location:</strong> {{ profile.location }}{% if profile.remote_ok %} (remote OK){% endif %}</p>{% endif %}
  {% if profile.experience_years %}<p><strong>Experience:</strong> {{ profile.experience_years }} years</p>{% endif %}
</div>

{% for job in jobs %}
{% set pct = (job.match_score * 100) | round(1) %}
<div class="job">
  <div class="job-header">
    <div>
      <p class="title">{{ job.title }}</p>
      <p class="company">{{ job.company }}</p>
      <p class="location">{{ job.location }}{% if not job.location %} &mdash; Location not listed{% endif %}</p>
    </div>
    <span class="score-badge {% if pct >= 60 %}score-high{% elif pct >= 35 %}score-medium{% else %}score-low{% endif %}">
      {{ pct }}% match
    </span>
  </div>

  <div class="score-bar-wrap">
    <div class="score-bar" style="width: {{ [pct, 100]|min }}%"></div>
  </div>

  <div class="meta-row">
    {% if job.salary_min or job.salary_max %}
    <span>💰 {{ job.salary_display() }}</span>
    {% endif %}
    {% if job.source %}<span>📌 {{ job.source }}</span>{% endif %}
    {% if job.posted_date %}<span>📅 {{ job.posted_date[:10] }}</span>{% endif %}
    {% if job.job_type %}<span>🕐 {{ job.job_type }}</span>{% endif %}
  </div>

  {% if job.matched_skills %}
  <div class="skills">
    {% for skill in job.matched_skills %}
    <span class="skill-tag">{{ skill }}</span>
    {% endfor %}
  </div>
  {% endif %}

  {% if job.url %}
  <a class="apply-btn" href="{{ job.url }}" target="_blank" rel="noopener">View / Apply →</a>
  {% endif %}
</div>
{% endfor %}

</body>
</html>"""


def export_html(
    jobs: list[Job],
    profile: UserProfile,
    output_path: str = "report.html",
    top_n: int = 50,
) -> str:
    """
    Render a ranked HTML report of the top N jobs.

    Args:
        jobs:        Scored and sorted Job list.
        profile:     The user's profile (shown in header summary).
        output_path: Destination HTML file path.
        top_n:       How many jobs to include in the report.

    Returns:
        Absolute path to the rendered HTML file.
    """
    if not _JINJA_AVAILABLE:
        raise ImportError(
            "jinja2 is required for HTML reports.\n"
            "Install it with: pip install jinja2"
        )

    env = Environment(loader=BaseLoader())
    template = env.from_string(TEMPLATE)

    rendered = template.render(
        jobs=jobs[:top_n],
        profile=profile,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )

    path = Path(output_path)
    path.write_text(rendered, encoding="utf-8")
    print(f"[html] Report written ({min(len(jobs), top_n)} jobs) → {path.resolve()}")
    return str(path.resolve())
