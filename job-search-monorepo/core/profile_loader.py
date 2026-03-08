"""Load candidate profile and resume from configuration."""
from pathlib import Path

from .config import PROFILES_DIR, load_json_config


def load_master_resume(profile: str) -> str:
    """Load master resume for profile."""
    profile_dir = PROFILES_DIR / profile
    resume_path = profile_dir / "master-resume.md"

    if not resume_path.exists():
        raise FileNotFoundError(f"Master resume not found: {resume_path}")

    return resume_path.read_text(encoding="utf-8")


def load_approved_job_ids(profile: str) -> list[str]:
    """Load list of approved job IDs from profile."""
    profile_dir = PROFILES_DIR / profile
    approved_path = profile_dir / "approved_jobs.txt"

    if not approved_path.exists():
        return []

    ids = []
    for line in approved_path.read_text(encoding="utf-8").splitlines():
        line = line.strip().split("#")[0].strip()
        if line:
            ids.append(line)

    return ids


def get_candidate_summary(profile: str) -> str:
    """Build human-readable candidate summary from profile config."""
    profile_dir = PROFILES_DIR / profile
    criteria_path = profile_dir / "scoring-criteria.json"

    criteria = load_json_config(criteria_path)
    candidate = criteria.get("candidate_profile", {})

    parts = [
        f"Name: {candidate.get('name', 'Candidate')}",
        f"Title: {candidate.get('title', '')}",
        f"Years of Experience: {candidate.get('years_of_experience', 0)}",
    ]

    return "\n".join(parts)
