"""Extract Glassdoor job ID from job listing URLs; used by job_cache and glassdoor_search."""
from __future__ import annotations

import re
from urllib.parse import urlparse, unquote


def job_key_from_url(url: str) -> str | None:
    """Extract a stable job key from a Glassdoor job listing URL."""
    if not url or "glassdoor" not in url.lower():
        return None
    url = unquote(url)
    # job-listing slug: .../job-listing/...-JV_IC123_KO0,21_KE22,31.htm
    m = re.search(r"JV_[A-Z0-9_,]+", url, re.IGNORECASE)
    if m:
        return m.group(0)
    parsed = urlparse(url)
    path = (parsed.path or "").strip("/")
    # For job-listing URLs, use last segment or full path as key so we always have a key
    if "job-listing" in path or "/Job/" in path:
        if ".htm" in path:
            segment = path.split("/")[-1].replace(".htm", "").replace(".html", "")
            if segment:
                return segment
        if path:
            return path
    if ".htm" in path:
        segment = path.split("/")[-1].replace(".htm", "").replace(".html", "")
        if segment and len(segment) > 5:
            return segment
    return None
