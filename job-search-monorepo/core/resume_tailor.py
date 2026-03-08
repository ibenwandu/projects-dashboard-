"""AI-powered resume tailoring for specific jobs."""
from pathlib import Path

from .ai_client import generate
from .job_model import JobDetails


def tailor_resume(job: JobDetails, master_resume: str, model: str | None = None) -> str:
    """Tailor master resume for a specific job using AI."""
    job_ctx = f"""Title: {job.title}
Company: {job.company}
Location: {job.location}
Salary: {job.salary or '(not specified)'}

Description:
{job.description or '(none)'}

Key Skills: {', '.join(job.skills) if job.skills else 'See description'}
"""

    prompt = f"""You are an expert resume writer. Create a customized resume for the candidate that matches THIS SPECIFIC JOB. Use the master resume content below but:

1. Reorder and emphasize experiences, skills, and achievements that align with the job description.
2. Use keywords from the job posting (especially skills and requirements) naturally in the resume.
3. Keep the same factual content (dates, titles, companies) but tailor bullet points and summary to this role.
4. Keep the resume in Markdown format, professional and concise (no more than 2 pages when rendered).
5. Do not invent new jobs or dates—only reframe existing content.

JOB TO MATCH:
{job_ctx}

---

MASTER RESUME (candidate's full profile):
{master_resume}

---

Output ONLY the tailored resume in Markdown, no preamble or explanation."""

    return generate(prompt, model=model)


def write_tailored_resume(job: JobDetails, master_resume: str, output_path: Path) -> Path:
    """Generate and save tailored resume to file."""
    tailored = tailor_resume(job, master_resume)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(tailored, encoding="utf-8")
    return output_path
