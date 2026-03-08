"""Configuration and constants."""
import os
from pathlib import Path

# Load .env from project root so scheduled task (which may have different cwd) always finds it
try:
    from dotenv import load_dotenv
    _project_root = Path(__file__).resolve().parents[1]
    load_dotenv(_project_root / ".env")
except ImportError:
    pass

# Default: search Gmail for Indeed (and common job alert senders) in Updates
GMAIL_QUERY = os.getenv("JAR_GMAIL_QUERY", "from:indeed OR from:linkedin in:updates")
GMAIL_MAX_MESSAGES = int(os.getenv("JAR_GMAIL_MAX_MESSAGES", "50"))

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CREDENTIALS_PATH = PROJECT_ROOT / "credentials.json"
TOKEN_PATH = PROJECT_ROOT / "token.json"
OUTPUT_DIR = PROJECT_ROOT / "output"
JOBS_CACHE_PATH = OUTPUT_DIR / "jobs_cache.json"
REPORTS_DIR = PROJECT_ROOT / "reports"
RESUMES_DIR = OUTPUT_DIR / "resumes"

# Config folder (candidate profile, scoring criteria, master resume)
CONFIG_DIR = PROJECT_ROOT / "config"
SCORING_CRITERIA_PATH = CONFIG_DIR / "scoring-criteria.json"
CANDIDATE_PROFILE_PATH = CONFIG_DIR / "profile.md"
MASTER_RESUME_PATH = CONFIG_DIR / "master-resume.md"  # fallback: profile.md
APPROVED_JOBS_PATH = CONFIG_DIR / "approved_jobs.txt"  # user lists job IDs (jk=...) here after review

# Gmail API scope (read-only)
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# AI provider: "gemini" or "openai". If OPENAI_API_KEY is set and JAR_AI_PROVIDER=openai, use ChatGPT.
JAR_AI_PROVIDER = os.getenv("JAR_AI_PROVIDER", "gemini").lower()
# Gemini (GEMINI_API_KEY or GOOGLE_API_KEY in .env)
GEMINI_MODEL = os.getenv("JAR_GEMINI_MODEL") or os.getenv("GEMINI_MODEL") or "gemini-1.5-flash"
# OpenAI (OPENAI_API_KEY in .env; model e.g. gpt-4o-mini, gpt-4o)
OPENAI_MODEL = os.getenv("JAR_OPENAI_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
TOP_N_JOBS = int(os.getenv("JAR_TOP_N_JOBS", "10"))
