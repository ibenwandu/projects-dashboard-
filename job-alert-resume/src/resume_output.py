"""Format scraped job details for resume tailoring (export to files)."""
from __future__ import annotations

from pathlib import Path

from .indeed_scraper import JobDetails


def job_to_markdown(job: JobDetails) -> str:
    """Turn one job into a markdown document for resume tailoring."""
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


def write_job_files(jobs: list[JobDetails], out_dir: Path) -> list[Path]:
    """Write one markdown file per job; return list of written paths."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for i, job in enumerate(jobs):
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in (job.title or "job")[:60])
        safe_company = "".join(c if c.isalnum() or c in " -_" else "_" for c in (job.company or "company")[:40])
        fname = f"{i+1:02d}_{safe_title}_{safe_company}.md".replace(" ", "_")
        path = out_dir / fname
        path.write_text(job_to_markdown(job), encoding="utf-8")
        written.append(path)
    return written


def write_combined_markdown(jobs: list[JobDetails], path: Path) -> Path:
    """Write all jobs into one markdown file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    parts = [job_to_markdown(job) for job in jobs]
    path.write_text("\n\n---\n\n".join(parts), encoding="utf-8")
    return path
