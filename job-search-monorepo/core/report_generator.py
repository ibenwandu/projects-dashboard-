"""Generate ranked job reports and market insights."""
from datetime import datetime
from pathlib import Path
from typing import Optional

from .ai_scorer import ScoredJob
from .dedup_engine import get_all_platform_urls


def generate_market_insights(scored_jobs: list[ScoredJob]) -> dict:
    """Generate market insights from scored jobs."""
    if not scored_jobs:
        return {}

    salaries = []
    companies = {}
    remote_count = 0

    for scored in scored_jobs:
        job = scored.job

        if job.salary:
            try:
                if "-" in job.salary:
                    min_sal, max_sal = job.salary.split("-")
                    salaries.append(int(max_sal.replace(",", "")))
            except:
                pass

        companies[job.company] = companies.get(job.company, 0) + 1

        if "remote" in job.location.lower():
            remote_count += 1

    avg_salary = int(sum(salaries) / len(salaries)) if salaries else 0
    top_companies = sorted(companies.items(), key=lambda x: x[1], reverse=True)[:5]
    remote_pct = int((remote_count / len(scored_jobs)) * 100) if scored_jobs else 0

    return {
        "avg_salary": avg_salary,
        "top_companies": [{"company": c, "count": cnt} for c, cnt in top_companies],
        "remote_percentage": remote_pct,
        "total_jobs": len(scored_jobs),
    }


def generate_report_markdown(scored_jobs: list[ScoredJob], top_n: int = 10) -> str:
    """Generate markdown report of top jobs."""
    ranked = sorted(scored_jobs, key=lambda x: x.score, reverse=True)

    report = [
        "# Job Search Report",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Summary",
        f"- Total jobs scored: {len(ranked)}",
        f"- Top candidates below (top {top_n})",
        "",
        "## Top Matches",
        "",
    ]

    for i, scored in enumerate(ranked[:top_n], 1):
        job = scored.job
        all_urls = get_all_platform_urls(job)
        platforms_str = " + ".join(all_urls.keys()).upper()

        report.extend([
            f"### {i}. {job.title} at {job.company}",
            f"**Score:** {scored.score}/100 | **Location:** {job.location} | **Salary:** {job.salary or 'Not specified'}",
            f"**Platforms:** {platforms_str}",
            f"**Reasoning:** {scored.reasoning}",
            f"**Links:**",
        ])

        for platform, url in all_urls.items():
            report.append(f"- [{platform.upper()}]({url})")

        report.append("")

    report.extend(["", "## Full Ranking", ""])

    for i, scored in enumerate(ranked, 1):
        job = scored.job
        report.append(f"{i}. **{scored.score}** - {job.title} at {job.company} ({job.location})")

    return "\n".join(report)


def save_report(scored_jobs: list[ScoredJob], report_dir: Path, top_n: int = 10, run_id: Optional[str] = None) -> Path:
    """Generate and save report to file."""
    run_id = run_id or datetime.now().strftime("%Y-%m-%d_%H%M")
    output_dir = report_dir / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "report.md"
    markdown = generate_report_markdown(scored_jobs, top_n=top_n)
    report_path.write_text(markdown, encoding="utf-8")

    return report_path
