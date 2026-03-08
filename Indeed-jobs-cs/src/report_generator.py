"""Generate actionable reports: top N matching jobs and full ranked list."""
from __future__ import annotations

from pathlib import Path

from .config import REPORTS_DIR, TOP_N_JOBS
from .gemini_scorer import ScoredJob


def _job_md(s: ScoredJob, rank: int) -> str:
    j = s.job
    return f"""### {rank}. {j.title} — {j.company}
- **Score:** {s.score}/100
- **Location:** {j.location or '—'}
- **Salary:** {j.salary or '—'}
- **URL:** {j.url}
- **Job ID (for approval):** `{s.jk}`

**Reasoning:** {s.reasoning}
"""


def generate_report(scored: list[ScoredJob], top_n: int | None = None, report_dir: Path | None = None, run_id: str | None = None) -> Path:
    report_dir = Path(report_dir or REPORTS_DIR)
    top_n = top_n or TOP_N_JOBS
    sorted_scores = sorted(scored, key=lambda x: x.score, reverse=True)
    top = sorted_scores[:top_n]
    run_dir = report_dir / (run_id or "latest")
    run_dir.mkdir(parents=True, exist_ok=True)
    lines = ["# Job Match Report", "", f"**Top {len(top)} matching jobs** (of {len(scored)} scored).", "", "---", ""]
    for i, s in enumerate(top, 1):
        lines.append(_job_md(s, i))
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Full ranked list (all jobs)")
    lines.append("")
    for i, s in enumerate(sorted_scores, 1):
        j = s.job
        lines.append(f"{i}. **{j.title}** — {j.company} — Score: {s.score}/100 — ID: `{s.jk}`")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## How to approve jobs")
    lines.append("")
    lines.append("Copy the Job IDs you want to generate resumes for into `config/approved_jobs.txt` (one ID per line).")
    lines.append("Then run: `python run_workflow.py --phase resumes`")
    lines.append("")
    for s in top[:3]:
        lines.append(f"  {s.jk}")
    lines.append("")
    report_path = run_dir / "report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    top_jobs_path = run_dir / "top_job_ids.txt"
    top_jobs_path.write_text("\n".join(s.jk for s in top), encoding="utf-8")
    return report_path
