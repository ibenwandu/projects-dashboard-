"""Format scraped job details for resume tailoring (export to files)."""
from __future__ import annotations

from pathlib import Path

from .glassdoor_scraper import JobDetails


def job_to_markdown(job: JobDetails) -> str:
    lines = [
        f"# {job.title}",
        "",
        f"- **Company:** {job.company}",
        f"- **Location:** {job.location}",
        f"- **Salary:** {job.salary}",
        f"- **URL:** {job.url}",
        "",
        "## Skills / Keywords (prioritize these on your resume)",
        "",
    ]
    if job.skills:
        for s in job.skills:
            lines.append(f"- {s}")
        lines.append("")
    else:
        lines.append("*(none extracted)*")
        lines.append("")
    lines.append("## Full job description")
    lines.append("")
    lines.append(job.description if job.description else "*(description not extracted)*")
    return "\n".join(lines)


def _is_blocked(job: JobDetails) -> bool:
    """Skip writing files for blocked, Cloudflare, timeout, or non-job pages."""
    t = (job.title or "").strip().lower()
    if t.startswith("[blocked:") or "sign in" in t or "auth" in t:
        return True
    if "help us protect" in t or "cloudflare" in t or ("verify" in t and "real person" in t):
        return True
    # Skip if URL is a category/search page
    url = (job.url or "").lower()
    if "jobs-srch" in url or ("/job/" in url and "job-listing" not in url and "jv_" not in url and url.rstrip("/").endswith("jobs.htm")):
        return True
    return False


def write_job_files(jobs: list[JobDetails], out_dir: Path) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    index = 0
    for job in jobs:
        if _is_blocked(job):
            continue
        index += 1
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in (job.title or "job")[:60])
        safe_company = "".join(c if c.isalnum() or c in " -_" else "_" for c in (job.company or "company")[:40])
        fname = f"{index:02d}_{safe_title}_{safe_company}.md".replace(" ", "_")
        path = out_dir / fname
        path.write_text(job_to_markdown(job), encoding="utf-8")
        written.append(path)
    return written


def write_combined_markdown(jobs: list[JobDetails], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    parts = [job_to_markdown(job) for job in jobs if not _is_blocked(job)]
    path.write_text("\n\n---\n\n".join(parts), encoding="utf-8")
    return path
