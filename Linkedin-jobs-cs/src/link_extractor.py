"""Extract LinkedIn job ID from view URLs; used by job_cache and linkedin_search."""
from __future__ import annotations

import re
from urllib.parse import urlparse, parse_qs


def job_key_from_url(url: str) -> str | None:
    """Extract job ID from a LinkedIn job view URL or search URL with currentJobId."""
    if not url or "linkedin.com" not in url.lower():
        return None
    # Match /jobs/view/1234567890 or /jobs/view/1234567890/
    m = re.search(r"/jobs/view/(\d+)", url, re.IGNORECASE)
    if m:
        return m.group(1)
    # Search page often uses currentJobId=123 in query string
    parsed = urlparse(url)
    q = parse_qs(parsed.query)
    for key in ("currentJobId", "jobId", "currentJob"):
        if key in q and q[key]:
            val = q[key][0].strip()
            if val.isdigit():
                return val
    path = (parsed.path or "").strip("/")
    if path.startswith("jobs/view/"):
        parts = path.split("/")
        if len(parts) >= 3 and parts[2].isdigit():
            return parts[2]
    return None
