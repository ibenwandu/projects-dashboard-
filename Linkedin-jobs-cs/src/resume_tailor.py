"""Generate customized resumes for approved jobs using AI and master resume."""
from __future__ import annotations

from pathlib import Path

from .config import APPROVED_JOBS_PATH, JOBS_CACHE_PATH, MASTER_RESUME_PATH, RESUMES_DIR
from .ai_client import generate
from .linkedin_scraper import JobDetails
from .job_cache import jobs_by_jk, load_jobs_cache
from .profile_loader import load_master_resume


def load_approved_job_ids(path: Path | None = None) -> list[str]:
    p = path or APPROVED_JOBS_PATH
    if not Path(p).exists():
        return []
    ids = []
    for line in Path(p).read_text(encoding="utf-8").splitlines():
        line = line.strip().split("#")[0].strip()
        if line:
            ids.append(line)
    return ids


def _job_context(job: JobDetails) -> str:
    return f"""Title: {job.title}
Company: {job.company}
Location: {job.location}
Salary: {job.salary}

Description:
{job.description or '(none)'}

Skills/keywords to emphasize: {', '.join(job.skills) if job.skills else 'See description'}
"""


def generate_tailored_resume(job: JobDetails, master_resume: str, model: str | None = None) -> str:
    job_ctx = _job_context(job)
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


def write_tailored_resumes(
    jobs_cache_path: Path | None = None,
    approved_path: Path | None = None,
    master_resume_path: Path | None = None,
    out_dir: Path | None = None,
    model: str | None = None,
) -> list[Path]:
    jobs_cache_path = jobs_cache_path or JOBS_CACHE_PATH
    approved_path = approved_path or APPROVED_JOBS_PATH
    master_resume_path = master_resume_path or MASTER_RESUME_PATH
    out_dir = Path(out_dir or RESUMES_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    approved = load_approved_job_ids(approved_path)
    if not approved:
        return []
    jobs = load_jobs_cache(jobs_cache_path)
    by_jk = jobs_by_jk(jobs)
    master = load_master_resume(master_resume_path)
    if not master:
        return []
    written = []
    approved_jobs_with_links = []
    for jk in approved:
        job = by_jk.get(jk)
        if not job:
            continue
        content = generate_tailored_resume(job, master, model=model)
        if not content or content.startswith("[Gemini error") or content.startswith("[OpenAI error"):
            continue
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in (job.title or "job")[:50])
        safe_company = "".join(c if c.isalnum() or c in " -_" else "_" for c in (job.company or "company")[:35])
        fname = f"{safe_title}_{safe_company}.md".replace(" ", "_")
        path = out_dir / fname
        path.write_text(content, encoding="utf-8")
        written.append(path)
        approved_jobs_with_links.append((job, fname))
    if approved_jobs_with_links:
        _write_job_links_file(out_dir, approved_jobs_with_links)
        from .md_to_pdf import convert_resume_mds_to_pdfs
        pdf_created = convert_resume_mds_to_pdfs(resumes_dir=out_dir)
        if pdf_created:
            for p in pdf_created:
                written.append(p)
    return written


def _write_job_links_file(out_dir: Path, jobs_with_names: list) -> Path:
    lines = [
        "# Job application links",
        "",
        "| # | Job title | Company | Apply link |",
        "|---|-----------|---------|------------|",
    ]
    for i, (job, resume_fname) in enumerate(jobs_with_names, 1):
        title = (job.title or "-").replace("|", "\\|")
        company = (job.company or "-").replace("|", "\\|")
        url = job.url or ""
        lines.append(f"| {i} | {title} | {company} | [Apply]({url}) |")
    lines.extend(["", "---", "", "**Plain URLs** (copy-paste):", ""])
    for job, _ in jobs_with_names:
        if job.url:
            lines.append(job.url)
    path = out_dir / "job_links.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
