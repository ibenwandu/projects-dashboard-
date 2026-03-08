"""Caching layer for jobs and deduplication database."""
import json
from pathlib import Path
from typing import Optional

from .config import JOBS_CACHE_PATH, DEDUP_DB_PATH, REPORTED_JOB_IDS_PATH
from .job_model import JobDetails


def save_jobs_cache(jobs: list[JobDetails], path: Path = JOBS_CACHE_PATH) -> None:
    """Save jobs to JSON cache."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [j.to_dict() for j in jobs]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_jobs_cache(path: Path = JOBS_CACHE_PATH) -> list[JobDetails]:
    """Load jobs from JSON cache."""
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [JobDetails.from_dict(item) for item in data]


def save_dedup_db(dedup_data: dict, path: Path = DEDUP_DB_PATH) -> None:
    """Save deduplication database."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dedup_data, f, indent=2)


def load_dedup_db(path: Path = DEDUP_DB_PATH) -> dict:
    """Load deduplication database."""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_reported_job_ids(path: Path = REPORTED_JOB_IDS_PATH) -> set[str]:
    """Load set of already-reported job IDs."""
    if not path.exists():
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def append_reported_job_ids(job_ids: list[str], path: Path = REPORTED_JOB_IDS_PATH) -> None:
    """Append job IDs to reported list."""
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_reported_job_ids(path)
    with open(path, "a", encoding="utf-8") as f:
        for job_id in job_ids:
            if job_id not in existing:
                f.write(job_id + "\n")
