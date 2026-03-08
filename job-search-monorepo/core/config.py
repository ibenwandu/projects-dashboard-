"""Configuration and constants loader."""
import os
import json
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output"
PROFILES_DIR = PROJECT_ROOT / "profiles"
REPORTS_DIR = OUTPUT_DIR / "reports"
RESUMES_DIR = OUTPUT_DIR / "resumes"

# Create output directories
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
RESUMES_DIR.mkdir(parents=True, exist_ok=True)

# Paths
JOBS_CACHE_PATH = OUTPUT_DIR / "jobs_cache.json"
DEDUP_DB_PATH = OUTPUT_DIR / "dedup_db.json"
REPORTED_JOB_IDS_PATH = OUTPUT_DIR / "reported_job_ids.txt"

# AI Configuration
AI_PROVIDER = os.getenv("JAR_AI_PROVIDER", "gemini").lower()
GEMINI_MODEL = os.getenv("JAR_GEMINI_MODEL", "gemini-2.5-flash")
OPENAI_MODEL = os.getenv("JAR_OPENAI_MODEL", "gpt-4o-mini")

# Defaults
MAX_JOBS = int(os.getenv("JAR_MAX_JOBS", "25"))
TOP_N_JOBS = int(os.getenv("JAR_TOP_N_JOBS", "10"))


def get_profile_dir(profile: str) -> Path:
    """Get path to profile configuration directory."""
    profile_path = PROFILES_DIR / profile
    if not profile_path.exists():
        raise ValueError(f"Profile '{profile}' not found at {profile_path}")
    return profile_path


def load_json_config(path: Path) -> dict:
    """Load JSON configuration file."""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_search_config(profile: str, platform: str) -> dict:
    """Load search config for a platform within a profile."""
    profile_dir = get_profile_dir(profile)
    config_path = profile_dir / f"{platform}_search.json"
    return load_json_config(config_path)


def load_scoring_criteria(profile: str) -> dict:
    """Load scoring criteria for a profile."""
    profile_dir = get_profile_dir(profile)
    criteria_path = profile_dir / "scoring-criteria.json"
    return load_json_config(criteria_path)


def load_master_resume(profile: str) -> str:
    """Load master resume for a profile."""
    profile_dir = get_profile_dir(profile)
    resume_path = profile_dir / "master-resume.md"
    if not resume_path.exists():
        return ""
    return resume_path.read_text(encoding="utf-8")
