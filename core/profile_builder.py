"""
Shared utilities for normalizing and enriching a UserProfile,
used by both resume_parser.py and questionnaire.py.
"""

import re

# Common abbreviation expansions for skills
SKILL_ALIASES = {
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "nlp": "natural language processing",
    "dl": "deep learning",
    "cv": "computer vision",
    "bi": "business intelligence",
    "etl": "etl pipelines",
    "oop": "object oriented programming",
    "ds": "data science",
    "da": "data analysis",
    "sql": "sql",
    "nosql": "nosql",
    "js": "javascript",
    "ts": "typescript",
    "k8s": "kubernetes",
    "aws": "amazon web services",
    "gcp": "google cloud platform",
    "qa": "quality assurance",
}

# Tech/domain skill keyword list for extraction from free text
KNOWN_SKILLS = {
    # Languages
    "python", "r", "sql", "java", "scala", "javascript", "typescript",
    "c++", "c#", "go", "rust", "bash", "matlab",
    # Data / ML
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "keras",
    "xgboost", "lightgbm", "spark", "hadoop", "dbt", "airflow",
    "machine learning", "deep learning", "natural language processing",
    "computer vision", "time series", "forecasting", "regression",
    "classification", "clustering", "neural networks", "transformers",
    # Data platforms
    "snowflake", "databricks", "redshift", "bigquery", "postgresql",
    "mysql", "mongodb", "elasticsearch", "kafka", "redis",
    # BI / Viz
    "tableau", "power bi", "looker", "matplotlib", "seaborn", "plotly",
    "excel", "google sheets",
    # Cloud / DevOps
    "aws", "gcp", "azure", "docker", "kubernetes", "terraform",
    "ci/cd", "git", "github", "linux",
    # Business / Analytics
    "statistics", "a/b testing", "hypothesis testing", "data visualization",
    "business intelligence", "financial modeling", "supply chain",
    "marketing analytics", "product analytics",
    # More languages & tools
    "php", "ruby", "swift", "kotlin", "html", "css", "perl", "julia",
    "r studio", "sas", "spss", "vba",
    # More ML / AI
    "huggingface", "langchain", "openai api", "generative ai", "bert",
    "opencv", "nltk", "statsmodels", "scipy", "mlflow", "wandb",
    "dask", "polars", "pyspark", "feature engineering", "model deployment",
    "data pipeline", "llm", "prompt engineering", "rag",
    # More data platforms
    "hive", "cassandra", "dynamodb", "oracle", "clickhouse", "neo4j",
    "pinecone", "apache flink", "mariadb", "sqlite", "sql server",
    "azure synapse", "data warehouse", "data lake", "data lakehouse",
    # More BI / viz
    "d3.js", "ggplot2", "shiny", "grafana", "kibana", "qlik",
    "alteryx", "google data studio", "power automate",
    # More cloud / DevOps / engineering
    "jenkins", "github actions", "gitlab ci", "ansible", "helm",
    "prefect", "dagster", "serverless", "aws lambda", "aws s3",
    "rest api", "graphql", "microservices", "fastapi", "flask", "django",
    "api development", "azure devops", "cloud computing",
    "object oriented programming", "functional programming",
    "unit testing", "test driven development",
    # Process / Business
    "agile", "scrum", "jira", "confluence", "saas",
    "data engineering", "data governance", "data quality", "data modeling",
    "etl", "cohort analysis", "funnel analysis", "churn prediction",
    "recommendation systems", "risk modeling", "sentiment analysis",
    "text mining", "web scraping", "google analytics", "mixpanel",
    "amplitude", "segment", "pricing analysis", "competitive analysis",
    "product management", "stakeholder management", "data storytelling",
    "nosql", "t-sql", "pl/sql", "spark streaming", "real-time analytics",
}


def normalize_skills(skills: list[str]) -> list[str]:
    """Lowercase, deduplicate, and expand common abbreviations."""
    normalized = []
    seen = set()
    for skill in skills:
        s = skill.strip().lower()
        s = SKILL_ALIASES.get(s, s)
        if s and s not in seen:
            seen.add(s)
            normalized.append(s)
    return normalized


def extract_skills_from_text(text: str) -> list[str]:
    """Scan free text for known skill keywords."""
    text_lower = text.lower()
    found = []
    seen = set()
    for skill in sorted(KNOWN_SKILLS, key=len, reverse=True):  # longest first
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower) and skill not in seen:
            seen.add(skill)
            found.append(skill)
    return found


def extract_experience_years(text: str) -> int:
    """Try to pull years of experience from free text."""
    patterns = [
        r'(\d+)\+?\s+years? of experience',
        r'(\d+)\+?\s+years? experience',
        r'(\d+)\+?\s+yrs?\.?\s+exp',
        r'experience[:\s]+(\d+)\+?\s+years?',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return 0


def extract_education(text: str) -> str:
    """Pull highest education level mentioned in text."""
    degrees = [
        (r'\bph\.?d\.?\b', "PhD"),
        (r'\bdoctor(ate|al)?\b', "Doctorate"),
        (r'\bmaster[\'s]?\b|\bm\.s\.?\b|\bm\.b\.a\.?\b|\bmsba\b', "Master's"),
        (r'\bbachelor[\'s]?\b|\bb\.s\.?\b|\bb\.a\.?\b', "Bachelor's"),
        (r'\bassociate[\'s]?\b', "Associate's"),
    ]
    text_lower = text.lower()
    for pattern, label in degrees:
        if re.search(pattern, text_lower):
            return label
    return ""


def build_profile_text(profile) -> str:
    """Combine all fields into a single text blob for embedding/matching."""
    return profile.to_profile_text()
