"""
Matplotlib chart generators. Returns PNG bytes — no file I/O here.
Uses the Agg backend so it works headless (no display required).
"""

import io

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    _MPL_AVAILABLE = True
except ImportError:
    _MPL_AVAILABLE = False


def render_charts(stats: dict) -> dict[str, bytes]:
    """
    Build all four summary charts and return {name: PNG bytes}.
    Returns an empty dict if matplotlib is not installed.
    """
    if not _MPL_AVAILABLE:
        print("[charts] matplotlib not installed — skipping chart generation.")
        return {}

    return {
        "time_on_market": _chart_time_on_market(stats.get("time_on_market", {})),
        "top_skills":     _chart_top_skills(stats.get("top_skills", [])),
        "skill_gap":      _chart_skill_gap(stats.get("skill_gap", {})),
        "salary":         _chart_salary(stats.get("salary", {})),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save_fig(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _no_data_fig(title: str, msg: str = "No data available") -> bytes:
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.text(0.5, 0.5, msg, ha="center", va="center",
            transform=ax.transAxes, color="#6c757d", fontsize=12)
    ax.set_title(title, fontweight="bold")
    ax.axis("off")
    fig.tight_layout()
    return _save_fig(fig)


# ---------------------------------------------------------------------------
# Individual charts
# ---------------------------------------------------------------------------

def _chart_time_on_market(data: dict) -> bytes:
    buckets = data.get("histogram_buckets", {})
    if not buckets or sum(buckets.values()) == 0:
        return _no_data_fig("Time on Market", "No posting date data available")

    labels = list(buckets.keys())
    values = list(buckets.values())
    avg = data.get("avg_days")
    med = data.get("median_days")

    subtitle = f"avg {avg:.0f} days, median {med:.0f} days" if avg is not None else ""
    title = f"Time on Market\n{subtitle}" if subtitle else "Time on Market"

    fig, ax = plt.subplots(figsize=(6, 3.5))
    bars = ax.bar(labels, values, color="#0d6efd", alpha=0.85, edgecolor="white")
    ax.set_title(title, fontweight="bold", fontsize=10)
    ax.set_xlabel("Days Since Posted")
    ax.set_ylabel("Number of Jobs")
    for bar, v in zip(bars, values):
        if v > 0:
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.1, str(v), ha="center", va="bottom", fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _save_fig(fig)


def _chart_top_skills(data: list) -> bytes:
    top = data[:15]
    if not top:
        return _no_data_fig("Top Skills Demanded", "No skill data available")

    skills = [e["skill"] for e in reversed(top)]
    counts = [e["count"] for e in reversed(top)]

    fig, ax = plt.subplots(figsize=(6, max(3.5, len(top) * 0.38)))
    bars = ax.barh(skills, counts, color="#198754", alpha=0.85)
    ax.set_title("Top Skills in Job Descriptions", fontweight="bold", fontsize=10)
    ax.set_xlabel("Number of Jobs Mentioning Skill")
    for bar, v in zip(bars, counts):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                str(v), va="center", fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _save_fig(fig)


def _chart_skill_gap(data: dict) -> bytes:
    missing = data.get("missing", [])
    if not missing:
        return _no_data_fig("Skill Gap Analysis", "No skill gap detected\n(or no demanded skills found)")

    skills = [e["skill"] for e in reversed(missing)]
    counts = [e["demand_count"] for e in reversed(missing)]

    fig, ax = plt.subplots(figsize=(6, max(3.5, len(missing) * 0.42)))
    bars = ax.barh(skills, counts, color="#dc3545", alpha=0.85)
    ax.set_title("Skills to Add to Your Resume", fontweight="bold", fontsize=10)
    ax.set_xlabel("Number of Jobs Requiring Skill")
    for bar, v in zip(bars, counts):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                str(v), va="center", fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _save_fig(fig)


def _chart_salary(data: dict) -> bytes:
    if not data.get("n_with_salary"):
        return _no_data_fig("Salary Distribution", "No salary data reported\nin current listings")

    pairs = [
        ("Min",    data.get("min")),
        ("25th %", data.get("p25")),
        ("Median", data.get("median")),
        ("75th %", data.get("p75")),
        ("Max",    data.get("max")),
    ]
    pairs = [(lbl, v) for lbl, v in pairs if v is not None]
    if not pairs:
        return _no_data_fig("Salary Distribution", "No salary data reported")

    labels, values = zip(*pairs)
    values_k = [v / 1000 for v in values]

    fig, ax = plt.subplots(figsize=(6, 3.5))
    bars = ax.bar(labels, values_k, color="#fd7e14", alpha=0.85, edgecolor="white")
    n = data["n_with_salary"]
    currency = data.get("currency_assumption", "USD")
    ax.set_title(f"Salary Distribution (n={n} listings, {currency})", fontweight="bold", fontsize=10)
    ax.set_ylabel("Salary ($K)")
    for bar, v in zip(bars, values_k):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.5, f"${v:.0f}K", ha="center", va="bottom", fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _save_fig(fig)
