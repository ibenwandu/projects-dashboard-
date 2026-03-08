"""Load candidate profile and scoring criteria from config folder."""
from __future__ import annotations

import json
from pathlib import Path

from .config import (
    CANDIDATE_PROFILE_PATH,
    CONFIG_DIR,
    MASTER_RESUME_PATH,
    SCORING_CRITERIA_PATH,
)


def load_scoring_criteria(path: Path | None = None) -> dict:
    """Load scoring-criteria.json. Returns the full dict (candidate_profile, required_skills, location, etc.)."""
    p = path or SCORING_CRITERIA_PATH
    if not Path(p).exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def load_candidate_profile_text(path: Path | None = None) -> str:
    """Load profile.md as raw text (for display or context)."""
    p = path or CANDIDATE_PROFILE_PATH
    if not Path(p).exists():
        return ""
    return Path(p).read_text(encoding="utf-8")


def load_master_resume(path: Path | None = None) -> str:
    """Load master resume (master-resume.md or fallback to profile.md) for tailoring."""
    p = path or MASTER_RESUME_PATH
    p = Path(p)
    if p.exists():
        text = p.read_text(encoding="utf-8").strip()
        # Use profile.md if master-resume is just a placeholder (short or says to use profile)
        if len(text) > 300 and "profile.md" not in text.lower()[:200]:
            return text
    return load_candidate_profile_text(CANDIDATE_PROFILE_PATH)


def get_candidate_summary_for_scoring(criteria: dict) -> str:
    """Build a concise text summary of the candidate from scoring-criteria for Gemini prompt."""
    if not criteria:
        return ""
    profile = criteria.get("candidate_profile", {})
    name = profile.get("name", "")
    title = profile.get("title", "")
    creds = profile.get("credentials", [])
    years = profile.get("years_of_experience", "")
    diffs = profile.get("key_differentiators", [])
    must = criteria.get("required_skills", {}).get("must_have", [])
    pref = criteria.get("required_skills", {}).get("preferred", [])
    loc = criteria.get("location", {})
    salary = criteria.get("salary", {})
    roles = criteria.get("role_types", {}).get("primary_targets", [])
    seniority = criteria.get("seniority", {}).get("target", [])
    industries = criteria.get("industries", {}).get("preferred_industries", [])
    red_flags = criteria.get("red_flags_to_avoid", [])

    lines = [
        f"Candidate: {name}",
        f"Title: {title}",
        f"Credentials: {', '.join(creds)}",
        f"Years of experience: {years}",
        "Key differentiators: " + "; ".join(diffs),
        "Must-have skills: " + ", ".join(must),
        "Preferred skills: " + ", ".join(pref),
        "Preferred location/work: " + str(loc.get("preferred", [])) + "; acceptable: " + str(loc.get("acceptable", [])),
        f"Salary: min {salary.get('minimum')} {salary.get('currency', 'CAD')}, target {salary.get('target')}",
        "Target roles: " + ", ".join(roles),
        "Seniority: " + ", ".join(seniority),
        "Preferred industries: " + ", ".join(industries),
        "Red flags to avoid: " + "; ".join(red_flags),
    ]
    return "\n".join(lines)
