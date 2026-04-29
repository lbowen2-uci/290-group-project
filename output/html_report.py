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
  /* ---- Market Summary / Stats ---- */
  .stats-section { background: #fff; border-radius: 8px; padding: 24px; margin-bottom: 24px;
                   box-shadow: 0 1px 3px rgba(0,0,0,.1); }
  .stats-section h2 { margin-top: 0; color: #343a40; border-bottom: 2px solid #e9ecef; padding-bottom: 12px; }
  .stats-section h3 { font-size: 15px; color: #495057; margin: 20px 0 8px; }
  .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
                gap: 12px; margin-bottom: 20px; }
  .stat-card  { background: #f8f9fa; border-radius: 8px; padding: 16px; text-align: center; }
  .stat-value { font-size: 28px; font-weight: 700; color: #0d6efd; }
  .stat-label { font-size: 12px; color: #6c757d; margin-top: 4px; }
  .chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 16px 0; }
  .chart-img  { width: 100%; border-radius: 6px; border: 1px solid #e9ecef; }
  .stats-table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 8px; }
  .stats-table th { text-align: left; padding: 8px 12px; background: #f8f9fa;
                    border-bottom: 2px solid #dee2e6; color: #495057; }
  .stats-table td { padding: 7px 12px; border-bottom: 1px solid #f0f0f0; }
  .stats-table tr:last-child td { border-bottom: none; }
  .stats-subsection { margin-top: 20px; }
  .stats-note { font-size: 13px; color: #6c757d; margin: 4px 0 8px; }
  /* ---- Claude Analysis ---- */
  .claude-analysis { background: #f3f0ff; border-left: 3px solid #7c3aed;
                     border-radius: 0 6px 6px 0; padding: 10px 14px; margin-top: 12px; }
  .claude-analysis .fit-reasoning { margin: 0 0 6px; font-size: 13px; color: #3b1a8c; }
  .claude-meta { display: flex; gap: 12px; flex-wrap: wrap; font-size: 12px; color: #5b21b6; }
  .claude-meta span { background: #ede9fe; padding: 2px 8px; border-radius: 10px; }
  .claude-concern { color: #92400e; background: #fef3c7 !important; }
  @media (max-width: 600px) { .chart-grid { grid-template-columns: 1fr; } }
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

{% if stats %}
<div class="stats-section">
  <h2>Market Summary</h2>

  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-value">{{ stats.meta.total_jobs }}</div>
      <div class="stat-label">Jobs Analyzed</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{{ stats.meta.sources | length }}</div>
      <div class="stat-label">Data Sources</div>
    </div>
    {% if stats.time_on_market.avg_days is not none %}
    <div class="stat-card">
      <div class="stat-value">{{ stats.time_on_market.avg_days | int }}</div>
      <div class="stat-label">Avg Days Listed</div>
    </div>
    {% endif %}
    {% if stats.salary.n_with_salary %}
    <div class="stat-card">
      <div class="stat-value">${{ (stats.salary.median / 1000) | round | int }}K</div>
      <div class="stat-label">Median Salary</div>
    </div>
    {% endif %}
  </div>

  {% if b64_charts %}
  <div class="chart-grid">
    {% if b64_charts.time_on_market %}
    <img class="chart-img" src="{{ b64_charts.time_on_market }}" alt="Time on Market">
    {% endif %}
    {% if b64_charts.top_skills %}
    <img class="chart-img" src="{{ b64_charts.top_skills }}" alt="Top Skills Demanded">
    {% endif %}
    {% if b64_charts.skill_gap %}
    <img class="chart-img" src="{{ b64_charts.skill_gap }}" alt="Skill Gap Analysis">
    {% endif %}
    {% if b64_charts.salary %}
    <img class="chart-img" src="{{ b64_charts.salary }}" alt="Salary Distribution">
    {% endif %}
  </div>
  {% endif %}

  {% if stats.top_skills %}
  <div class="stats-subsection">
    <h3>Top Skills in Demand</h3>
    <table class="stats-table">
      <thead><tr><th>Skill</th><th>Jobs</th><th>% of Listings</th></tr></thead>
      <tbody>
        {% for s in stats.top_skills[:10] %}
        <tr><td>{{ s.skill }}</td><td>{{ s.count }}</td><td>{{ s.pct_of_jobs }}%</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% endif %}

  {% if stats.skill_gap.missing %}
  <div class="stats-subsection">
    <h3>Skills to Add to Your Resume</h3>
    <p class="stats-note">These in-demand skills weren't found in your profile:</p>
    <table class="stats-table">
      <thead><tr><th>Skill</th><th>Demand (# Jobs)</th></tr></thead>
      <tbody>
        {% for m in stats.skill_gap.missing %}
        <tr><td>{{ m.skill }}</td><td>{{ m.demand_count }}</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% endif %}

</div>
{% endif %}

{% for job in jobs %}
{% set display_score = job.claude_score if job.claude_score is not none else job.match_score %}
{% set pct = (display_score * 100) | round(1) %}
<div class="job">
  <div class="job-header">
    <div>
      <p class="title">{{ job.title }}</p>
      <p class="company">{{ job.company }}</p>
      <p class="location">{{ job.location }}{% if not job.location %} &mdash; Location not listed{% endif %}</p>
    </div>
    <span class="score-badge {% if pct >= 60 %}score-high{% elif pct >= 35 %}score-medium{% else %}score-low{% endif %}">
      {{ pct }}% match{% if job.claude_score is not none %} ✦{% endif %}
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

  {% if job.fit_reasoning %}
  <div class="claude-analysis">
    <p class="fit-reasoning">{{ job.fit_reasoning }}</p>
    <div class="claude-meta">
      {% if job.growth_potential %}<span>Growth: {{ job.growth_potential }}</span>{% endif %}
      {% if job.key_match %}<span>{{ job.key_match }}</span>{% endif %}
      {% if job.concern and job.concern != "none" %}<span class="claude-concern">⚠ {{ job.concern }}</span>{% endif %}
    </div>
  </div>
  {% endif %}

  {% if job.url %}
  <a class="apply-btn" href="{{ job.url }}" target="_blank" rel="noopener">View / Apply →</a>
  {% endif %}
</div>
{% endfor %}

</body>
</html>"""


def _b64_png(png_bytes: bytes) -> str:
    import base64
    return "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")


def _prepare_b64_charts(charts: dict | None) -> dict:
    if not charts:
        return {}
    return {k: _b64_png(v) for k, v in charts.items()}


def export_html(
    jobs: list[Job],
    profile: UserProfile,
    output_path: str = "report.html",
    top_n: int = 50,
    stats: dict | None = None,
    charts: dict | None = None,
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
        stats=stats,
        b64_charts=_prepare_b64_charts(charts),
    )

    path = Path(output_path)
    path.write_text(rendered, encoding="utf-8")
    print(f"[html] Report written ({min(len(jobs), top_n)} jobs) → {path.resolve()}")
    return str(path.resolve())
