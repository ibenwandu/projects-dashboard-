"""Cross-platform job deduplication."""
import hashlib
from datetime import datetime, timezone
from typing import Optional

from .job_model import JobDetails
from .cache import load_dedup_db, save_dedup_db


def compute_fingerprint(job: JobDetails) -> str:
    """
    Compute fingerprint hash for job deduplication.

    Same job on multiple platforms will have identical fingerprint.
    """
    key = (
        job.company.lower().strip() +
        "|" +
        job.title.lower().strip() +
        "|" +
        job.location.lower().strip() +
        "|" +
        (job.salary or "")
    )
    return hashlib.sha256(key.encode()).hexdigest()


def deduplicate_jobs(jobs: list[JobDetails]) -> tuple[list[JobDetails], dict]:
    """
    Deduplicate jobs across platforms.

    Returns:
        - list of deduplicated JobDetails (with platform info preserved)
        - dedup database dict
    """
    dedup_db = load_dedup_db()
    seen_fingerprints = {}
    deduplicated = []

    for job in jobs:
        fingerprint = compute_fingerprint(job)
        job.fingerprint = fingerprint

        if fingerprint in seen_fingerprints:
            # This job already scraped from another platform
            master_job = seen_fingerprints[fingerprint]

            # Update dedup_db with new platform URL
            if fingerprint in dedup_db:
                dedup_db[fingerprint]["platforms"].append(job.platform)
                dedup_db[fingerprint]["urls"][job.platform] = job.url
            else:
                dedup_db[fingerprint] = {
                    "platforms": [master_job.platform, job.platform],
                    "urls": {master_job.platform: master_job.url, job.platform: job.url},
                    "master_job_id": f"{master_job.platform}_{master_job.job_id}",
                    "created_date": datetime.now(timezone.utc).isoformat(),
                }

            # Skip adding duplicate (we already have the master)
            continue

        # First time seeing this job
        seen_fingerprints[fingerprint] = job

        # Initialize dedup_db entry if not exists
        if fingerprint not in dedup_db:
            dedup_db[fingerprint] = {
                "platforms": [job.platform],
                "urls": {job.platform: job.url},
                "master_job_id": f"{job.platform}_{job.job_id}",
                "created_date": datetime.now(timezone.utc).isoformat(),
            }

        deduplicated.append(job)

    # Save updated dedup_db
    save_dedup_db(dedup_db)

    return deduplicated, dedup_db


def get_all_platform_urls(job: JobDetails) -> dict[str, str]:
    """Get all platform URLs for a job (from dedup database)."""
    dedup_db = load_dedup_db()
    if job.fingerprint in dedup_db:
        return dedup_db[job.fingerprint]["urls"]
    return {job.platform: job.url}
