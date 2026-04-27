# Job Market Analyzer

A command-line tool that takes your career profile (via interactive Q&A or a PDF resume upload), searches live job postings across multiple sources, ranks them by relevance, and generates a market statistics report showing salary ranges, in-demand skills, skill gaps, and how long postings have been listed.

Built for BANA 290 group assignment.

---

## What It Does

1. **Profile input** — answer 11 questions about your target role, skills, and location *or* upload a PDF resume and let the tool extract the information automatically.
2. **Job search** — scrapes multiple job sources in parallel (LinkedIn, Indeed, Glassdoor, ZipRecruiter, Remotive, Adzuna, and optionally JSearch via RapidAPI).
3. **Relevance matching** — ranks every posting against your profile using either semantic embeddings (more accurate) or TF-IDF keyword matching (faster).
4. **Output** — writes a ranked job list in your choice of CSV, Excel, HTML, or SQLite, *plus* a market statistics summary (JSON, Markdown, and four PNG charts) every run.

---

## Quick Start

### 1. Clone and install

```bash
git clone <repo-url>
cd group-assignment
pip install -r requirements.txt
```

> **spaCy model** (needed for PDF resume parsing — skip if using Q&A mode only):
> ```bash
> python -m spacy download en_core_web_sm
> ```
>
> **First semantic-match run** downloads a ~90 MB sentence-transformer model automatically. Use `--matching keyword` to skip this.

### 2. Configure API keys

```bash
cp .env.example .env
# Open .env and fill in any keys you have (see API Keys section below)
```

JobSpy and Remotive work with **no API keys**. The `.env` file is gitignored — never commit it.

### 3. Run

```bash
# Interactive Q&A mode, HTML report
python main.py --mode qa --output html

# Resume PDF mode, all output formats
python main.py --mode resume --file resume.pdf --output all

# Faster (keyword matching), specific location
python main.py --mode qa --matching keyword --location "Chicago, IL" --output csv
```

---

## Usage

```
python main.py --mode {resume|qa} [options]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--mode resume` | — | Parse a PDF resume. Requires `--file`. |
| `--mode qa` | — | Walk through an 11-question interactive prompt. |
| `--file PATH` | — | Path to PDF resume (resume mode only). |
| `--location CITY` | from profile | Override or set job search location, e.g. `"Austin, TX"`. |
| `--remote` | false | Filter for remote-friendly postings. |
| `--output {csv,excel,html,db,all}` | `csv` | Output format(s). `all` writes every format. |
| `--matching {semantic,keyword}` | from `.env` | Matching algorithm. `semantic` is more accurate; `keyword` is faster. |
| `--max-results N` | 50 | Max postings to fetch per scraper. |
| `--top N` | 25 | Number of top matches to include in the job list outputs. |

### Examples

```bash
# Quick test with no API keys (uses JobSpy + Remotive, keyword matching)
python main.py --mode qa --matching keyword --output html

# Full run with all outputs, semantic matching
python main.py --mode resume --file my_resume.pdf --output all

# Remote jobs only, save to database for later comparison
python main.py --mode qa --remote --output db

# Location override, top 50 results in Excel
python main.py --mode qa --location "New York, NY" --top 50 --output excel
```

---

## Output Files

Every run produces these files in the working directory:

| File | Description |
|------|-------------|
| `stats.json` | Machine-readable market statistics (always written) |
| `stats.md` | Human-readable market statistics with tables (always written) |
| `charts/time_on_market.png` | Histogram of days since posted |
| `charts/top_skills.png` | Most-mentioned skills across all job descriptions |
| `charts/skill_gap.png` | In-demand skills missing from your profile |
| `charts/salary.png` | Salary distribution (min / quartiles / max) |
| `report.html` | Ranked job cards with embedded charts and stats (`--output html` or `all`) |
| `jobs_output.csv` | Ranked job list as CSV (`--output csv` or `all`) |
| `jobs_output.xlsx` | Same as CSV but Excel (`--output excel` or `all`) |
| `jobs.db` | SQLite database — deduplicates across runs (`--output db` or `all`) |

---

## API Keys

All scrapers degrade gracefully — if a key is missing the scraper is skipped and the rest still run.

| Scraper | Key needed | Free tier | Sign up |
|---------|-----------|-----------|---------|
| **JobSpy** (LinkedIn, Indeed, Glassdoor, ZipRecruiter) | None | Unlimited | — |
| **Remotive** (remote jobs) | None | 2,000 listings | — |
| **Adzuna** | `ADZUNA_APP_ID` + `ADZUNA_APP_KEY` | 250 req/day | [developer.adzuna.com](https://developer.adzuna.com/) |
| **JSearch** (via RapidAPI) | `RAPIDAPI_KEY` | 200 req/month | [rapidapi.com](https://rapidapi.com/) → subscribe to JSearch |

To enable JSearch, add `jsearch` to `ENABLED_SCRAPERS` in your `.env`:
```
ENABLED_SCRAPERS=jobspy,remotive,adzuna,jsearch
```

---

## Configuration (`.env`)

```bash
# Adzuna
ADZUNA_APP_ID=your_app_id
ADZUNA_APP_KEY=your_app_key
ADZUNA_COUNTRY=us           # us, gb, au, ca, de, fr, ...

# JSearch / RapidAPI
RAPIDAPI_KEY=your_key

# Scrapers to run (comma-separated)
ENABLED_SCRAPERS=jobspy,remotive,adzuna

# JobSpy sites (comma-separated)
JOBSPY_SITES=linkedin,indeed,glassdoor,zip_recruiter

# Matching algorithm: semantic (default) or keyword
MATCHING_MODE=semantic
```

---

## Project Structure

```
group-assignment/
├── main.py                    # CLI entry point — orchestrates the full pipeline
├── config.py                  # Loads .env into a config dict
├── requirements.txt
├── .env.example               # Copy to .env and fill in keys
│
├── core/
│   ├── user_profile.py        # UserProfile and Job dataclasses
│   ├── questionnaire.py       # Interactive Q&A input mode
│   ├── resume_parser.py       # PDF text extraction + spaCy NER parsing
│   └── profile_builder.py     # Shared skill/education/experience utilities + KNOWN_SKILLS list
│
├── scrapers/
│   ├── base.py                # BaseScraper abstract class
│   ├── scraper_manager.py     # Runs scrapers in parallel, deduplicates results
│   ├── jobspy_scraper.py      # LinkedIn, Indeed, Glassdoor, ZipRecruiter (no key needed)
│   ├── remotive_scraper.py    # Remotive remote jobs API (no key needed)
│   ├── adzuna_scraper.py      # Adzuna jobs API (key required)
│   └── jsearch_scraper.py     # JSearch via RapidAPI (key required, paid fallback)
│
├── matching/
│   ├── keyword_matcher.py     # TF-IDF cosine similarity (fast, no GPU)
│   └── semantic_matcher.py    # Sentence-transformers embeddings (accurate, ~90MB model)
│
├── analytics/
│   ├── stats_generator.py     # compute_stats() — time on market, skills, salary, gap
│   └── charts.py              # render_charts() — returns matplotlib PNG bytes
│
└── output/
    ├── csv_exporter.py        # CSV and Excel export
    ├── html_report.py         # Jinja2 HTML report with embedded charts and stats
    ├── stats_exporter.py      # Writes stats.json, stats.md, charts/*.png
    └── db_store.py            # SQLite persistence (deduplicates across runs)
```

---

## Adding a New Scraper

1. Create `scrapers/your_scraper.py` — subclass `BaseScraper`, implement `fetch(profile, max_results) -> list[Job]`.
2. Register it in `scrapers/scraper_manager.py` inside `_build_scrapers()`:
   ```python
   "yourname": YourScraper,
   ```
3. Add the key (if any) to `config.py` and `.env.example`.
4. Enable it: `ENABLED_SCRAPERS=jobspy,remotive,yourname`

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'spacy'`** — Run `pip install -r requirements.txt`. Then `python -m spacy download en_core_web_sm` if using resume mode.

**Semantic matching is slow** — Use `--matching keyword` or set `MATCHING_MODE=keyword` in `.env`. A GPU is not required but speeds it up significantly.

**JobSpy returns 0 results** — LinkedIn and Indeed occasionally block scrapers. Try adding `--matching keyword` and reducing `--max-results`. Adzuna and JSearch APIs are more reliable for consistent results.

**Charts are missing from the HTML report** — Make sure `matplotlib` is installed (`pip install matplotlib`). Charts are generated regardless of `--output` format.

**PDF resume parsing misses skills or job title** — The parser matches against a known-skills list (`core/profile_builder.py → KNOWN_SKILLS`). Add any domain-specific skills there. For image-based (scanned) PDFs, text extraction will not work — use `--mode qa` instead.
