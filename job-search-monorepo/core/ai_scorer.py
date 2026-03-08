"""AI-powered job scoring against candidate profile."""
from dataclasses import dataclass

from .ai_client import generate, parse_score_and_reasoning
from .config import GEMINI_MODEL
from .job_model import JobDetails


@dataclass
class ScoredJob:
    """Job with AI-generated score and reasoning."""
    job: JobDetails
    score: int
    reasoning: str


def _build_candidate_profile(criteria: dict) -> str:
    """Build human-readable candidate profile from criteria."""
    profile = criteria.get("candidate_profile", {})
    name = profile.get("name", "Candidate")
    title = profile.get("title", "")
    years = profile.get("years_of_experience", 0)

    location = criteria.get("location", {})
    salary = criteria.get("salary", {})
    roles = criteria.get("role_types", {})

    parts = [
        f"Name: {name}",
        f"Title: {title}",
        f"Years of Experience: {years}",
        "",
        f"Location Preference: {location.get('preferred', [])} (preferred), {location.get('acceptable', [])} (acceptable)",
        f"Salary: ${salary.get('minimum', 0):,} minimum, ${salary.get('target', 0):,} target (CAD)",
        f"Target Roles: {', '.join(roles.get('primary_targets', []))}",
        f"Secondary Roles: {', '.join(roles.get('secondary_targets', []))}",
    ]
    return "\n".join(parts)


def _build_job_text(job: JobDetails) -> str:
    """Build job description for AI scoring."""
    parts = [
        f"Title: {job.title}",
        f"Company: {job.company}",
        f"Location: {job.location}",
        f"Salary: {job.salary or '(not specified)'}",
        f"Type: {job.job_type or '(not specified)'}",
        "",
        "Description:",
        job.description or "(none)",
        "",
        f"Key Skills: {', '.join(job.skills) if job.skills else '(see description)'}",
    ]
    return "\n".join(parts)


def score_job(job: JobDetails, criteria: dict) -> ScoredJob:
    """Score a single job against candidate profile using AI."""
    candidate = _build_candidate_profile(criteria)
    job_text = _build_job_text(job)

    prompt = f"""You are a career match analyst. Score how well the following job matches the candidate profile on a scale of 0-100. Consider: required and preferred skills, role type, seniority, location/work arrangement, salary, industry, and red flags.

CANDIDATE PROFILE:
{candidate}

---

JOB:
{job_text}

Respond in this exact format (no other text):
Score: <number 0-100>
Reasoning: <2-4 sentences explaining the score and any concerns>"""

    response = generate(prompt)
    score, reasoning = parse_score_and_reasoning(response)

    return ScoredJob(job=job, score=score, reasoning=reasoning)


def score_jobs(jobs: list[JobDetails], criteria: dict) -> list[ScoredJob]:
    """Score multiple jobs."""
    if not criteria:
        return [
            ScoredJob(job=j, score=0, reasoning="No scoring criteria provided.")
            for j in jobs
        ]

    return [score_job(job, criteria) for job in jobs]
