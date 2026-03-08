"""Extract Indeed job key (jk) from URLs; used by job_cache and indeed_search."""
from __future__ import annotations

from urllib.parse import urlparse


def job_key_from_url(url: str) -> str | None:
    """Extract job key (jk) from any Indeed URL for use in reports/approval."""
    parsed = urlparse(url)
    q = parsed.query
    for part in q.split("&"):
        if part.lower().startswith("jk="):
            return part.split("=", 1)[1].strip()
    return None
