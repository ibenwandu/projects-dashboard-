"""Load candidate profile and scoring criteria from config folder."""
from __future__ import annotations

import json
from pathlib import Path

from .config import (
    CANDIDATE_PROFILE_PATH,
    MASTER_RESUME_PATH,
    SCORING_CRITERIA_PATH,
)


def load_scoring_criteria(path: Path | None = None) -> dict:
    p = path or SCORING_CRITERIA_PATH
    if not Path(p).exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def load_candidate_profile_text(path: Path | None = None) -> str:
    p = path or CANDIDATE_PROFILE_PATH
    if not Path(p).exists():
        return ""
    return Path(p).read_text(encoding="utf-8")


def load_master_resume(path: Path | None = None) -> str:
    p = path or MASTER_RESUME_PATH
    p = Path(p)
    if p.exists():
        text = p.read_text(encoding="utf-8").strip()
        if len(text) > 300 and "profile.md" not in text.lower()[:200]:
            return text
    return load_candidate_profile_text(CANDIDATE_PROFILE_PATH)


def get_candidate_summary_for_scoring(criteria: dict) -> str:
    if not criteria:
        return ""
    profile = criteria.get("candidate_profile", {})
    name = profile.get("name", "")
    title = profile.get("title", "")
    creds = profile.get("credentials", [])
    years = profile.get("years_of_experience", "")
    loc = criteria.get("location", {})
    salary = criteria.get("salary", {})
    roles = criteria.get("role_types", {}).get("primary_targets", [])
    lines = [
        f"Candidate: {name}",
        f"Title: {title}",
        f"Credentials: {', '.join(creds)}",
        f"Years of experience: {years}",
        "Preferred location/work: " + str(loc.get("preferred", [])) + "; acceptable: " + str(loc.get("acceptable", [])),
        f"Salary: min {salary.get('minimum')} {salary.get('currency', 'CAD')}, target {salary.get('target')}",
        "Target roles: " + ", ".join(roles),
    ]
    return "\n".join(lines)
