"""Configuration and constants. Job source is Glassdoor search."""
import os
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass
OUTPUT_DIR = PROJECT_ROOT / "output"
JOBS_CACHE_PATH = OUTPUT_DIR / "jobs_cache.json"
REPORTED_JOB_IDS_PATH = OUTPUT_DIR / "reported_job_ids.txt"
REPORTS_DIR = PROJECT_ROOT / "reports"
RESUMES_DIR = OUTPUT_DIR / "resumes"

CONFIG_DIR = PROJECT_ROOT / "config"
GLASSDOOR_SEARCH_CONFIG_PATH = CONFIG_DIR / "glassdoor_search.json"
RESUME_PDF_TEMPLATE_PATH = CONFIG_DIR / "resume-pdf-template.html"
COVER_LETTER_TEMPLATE_PATH = CONFIG_DIR / "cover-letter-template.html"
SCORING_CRITERIA_PATH = CONFIG_DIR / "scoring-criteria.json"
CANDIDATE_PROFILE_PATH = CONFIG_DIR / "profile.md"
MASTER_RESUME_PATH = CONFIG_DIR / "master-resume.md"
APPROVED_JOBS_PATH = CONFIG_DIR / "approved_jobs.txt"

JAR_AI_PROVIDER = os.getenv("JAR_AI_PROVIDER", "gemini").lower()
GEMINI_MODEL = os.getenv("JAR_GEMINI_MODEL") or os.getenv("GEMINI_MODEL") or "gemini-2.5-flash"
OPENAI_MODEL = os.getenv("JAR_OPENAI_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
TOP_N_JOBS = int(os.getenv("JAR_TOP_N_JOBS", "10"))


def load_glassdoor_search_config() -> dict:
    """Load Glassdoor search criteria from config/glassdoor_search.json."""
    path = GLASSDOOR_SEARCH_CONFIG_PATH
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)
