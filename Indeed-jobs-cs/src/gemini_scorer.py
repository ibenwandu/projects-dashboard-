"""Score a job against the candidate profile using AI (Gemini or OpenAI)."""
from __future__ import annotations

from dataclasses import dataclass

from .config import GEMINI_MODEL
from .ai_client import generate, parse_score_and_reasoning
from .indeed_scraper import JobDetails
from .link_extractor import job_key_from_url
from .profile_loader import get_candidate_summary_for_scoring, load_scoring_criteria


@dataclass
class ScoredJob:
    job: JobDetails
    score: int
    reasoning: str
    jk: str = ""


def _job_text(job: JobDetails) -> str:
    parts = [
        f"Title: {job.title}",
        f"Company: {job.company}",
        f"Location: {job.location}",
        f"Salary: {job.salary}",
        f"Type: {job.job_type}",
        "",
        "Description:",
        job.description or "(none)",
        "",
        "Skills/keywords: " + ", ".join(job.skills) if job.skills else "",
    ]
    return "\n".join(parts)


def score_job_with_gemini(job: JobDetails, criteria: dict, model: str | None = None) -> ScoredJob:
    candidate = get_candidate_summary_for_scoring(criteria)
    job_txt = _job_text(job)
    model = model or GEMINI_MODEL
    prompt = f"""You are a career match analyst. Score how well the following job matches the candidate profile (0-100). Consider: required and preferred skills, role type, seniority, location/work arrangement, salary, industry, and red flags.

CANDIDATE PROFILE:
{candidate}

---
JOB:
{job_txt}

Respond in this exact format (no other text):
Score: <number 0-100>
Reasoning: <2-4 sentences on fit and any concerns>"""
    out = generate(prompt, model=model)
    score, reasoning = parse_score_and_reasoning(out)
    jk = job_key_from_url(job.url) or ""
    return ScoredJob(job=job, score=score, reasoning=reasoning, jk=jk)


def score_jobs(jobs: list[JobDetails], criteria: dict | None = None, model: str | None = None) -> list[ScoredJob]:
    criteria = criteria or load_scoring_criteria()
    if not criteria:
        return [ScoredJob(job=j, score=0, reasoning="No scoring criteria loaded.", jk=job_key_from_url(j.url) or "") for j in jobs]
    return [score_job_with_gemini(job, criteria, model=model) for job in jobs]
