"""Extract Indeed (and similar) job URLs from email HTML."""
from __future__ import annotations

import re
from urllib.parse import parse_qs, unquote, urljoin, urlparse

from bs4 import BeautifulSoup


# Match Indeed job view URLs (ca.indeed.com, www.indeed.com, indeed.com)
INDEED_VIEWJOB_PATTERN = re.compile(
    r"https?://(?:ca\.|www\.)?indeed\.com/viewjob\?[^>\s\"']+",
    re.IGNORECASE,
)

# From href we can also get relative links
INDEED_VIEWJOB_RELATIVE = re.compile(r"/viewjob\?[^\s\"']+", re.IGNORECASE)

# Indeed often uses redirect/tracking links in emails (e.g. /rc/clk?jk=...); match any indeed URL with jk=
INDEED_ANY_JK_PATTERN = re.compile(
    r"https?://[^\"'\s<>]*indeed\.com[^\"'\s<>]*[?&]jk=([a-zA-Z0-9]+)",
    re.IGNORECASE,
)


def _normalize_indeed_url(url: str, base: str = "https://ca.indeed.com") -> str:
    """Ensure URL is absolute and optionally strip tracking params for deduplication."""
    if url.startswith("/"):
        url = urljoin(base, url)
    parsed = urlparse(url)
    if not parsed.netloc:
        url = urljoin(base, url)
    return url


def _job_key_from_url(url: str) -> str | None:
    """Extract jk (job key) from Indeed viewjob URL for deduplication."""
    parsed = urlparse(url)
    if "viewjob" not in parsed.path and "viewjob" not in url:
        return None
    q = parsed.query
    for part in q.split("&"):
        if part.startswith("jk="):
            return part.split("=", 1)[1].strip()
    return None


def _job_key_from_any_url(url: str) -> str | None:
    """Extract jk= value from any Indeed URL (viewjob, rc/clk, etc.)."""
    parsed = urlparse(url)
    q = parsed.query
    for part in q.split("&"):
        if part.lower().startswith("jk="):
            return part.split("=", 1)[1].strip()
    return None


def job_key_from_url(url: str) -> str | None:
    """Public: extract job key (jk) from any Indeed URL for use in reports/approval."""
    return _job_key_from_any_url(url)


def _canonical_viewjob_url(jk: str, base: str = "https://ca.indeed.com") -> str:
    """Build canonical viewjob URL from job key."""
    return f"{base.rstrip('/')}/viewjob?jk={jk}"


def _unwrap_redirect_href(href: str) -> list[str]:
    """If href is a Gmail/Google redirect (e.g. google.com/url?q=...), return the inner URL(s)."""
    parsed = urlparse(href)
    if "google.com" not in parsed.netloc.lower() and "google." not in parsed.netloc.lower():
        return [href]
    q = parse_qs(parsed.query)
    inner = q.get("q", q.get("url", []))
    if not inner:
        return [href]
    return [unquote(u) for u in inner]


def extract_indeed_urls_from_html(html: str, base_url: str = "https://ca.indeed.com") -> list[str]:
    """
    Parse HTML and return a deduplicated list of Indeed viewjob URLs.
    Handles direct viewjob links and Indeed tracking/redirect links (e.g. /rc/clk?jk=...).
    """
    seen_jks: set[str] = set()
    urls: list[str] = []

    def add_by_jk(jk: str) -> None:
        if jk and jk not in seen_jks:
            seen_jks.add(jk)
            urls.append(_canonical_viewjob_url(jk, base_url))

    def add_url(raw: str) -> None:
        if not raw:
            return
        raw_lower = raw.lower()
        if "indeed.com" not in raw_lower and not raw.strip().startswith("/"):
            return
        if raw.startswith("/"):
            raw = urljoin(base_url, raw)
        # Direct viewjob
        if "viewjob" in raw_lower:
            normalized = _normalize_indeed_url(raw, base_url)
            jk = _job_key_from_url(normalized)
            if jk:
                add_by_jk(jk)
            return
        # Any Indeed URL with jk= (redirect/tracking)
        jk = _job_key_from_any_url(raw)
        if jk:
            add_by_jk(jk)

    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        # Gmail often wraps links in google.com/url?q=...; unwrap and check inner URL
        for link in _unwrap_redirect_href(href):
            if "indeed.com" in link or "jk=" in link or link.startswith("/viewjob"):
                add_url(link)

    # Regex: direct viewjob
    for match in INDEED_VIEWJOB_PATTERN.findall(html):
        add_url(match)
    for match in INDEED_VIEWJOB_RELATIVE.findall(html):
        add_url(match)
    # Regex: any Indeed URL with jk= (e.g. /rc/clk?jk=...)
    for match in INDEED_ANY_JK_PATTERN.findall(html):
        add_by_jk(match)

    return urls


def extract_indeed_urls_from_plain_text(text: str) -> list[str]:
    """Extract Indeed viewjob URLs from plain text (e.g. plain-text email)."""
    seen_jks: set[str] = set()
    urls = []

    def add_by_jk(jk: str) -> None:
        if jk and jk not in seen_jks:
            seen_jks.add(jk)
            urls.append(_canonical_viewjob_url(jk))

    for match in INDEED_VIEWJOB_PATTERN.findall(text):
        url = _normalize_indeed_url(match)
        jk = _job_key_from_url(url)
        if jk:
            add_by_jk(jk)
    for jk in INDEED_ANY_JK_PATTERN.findall(text):
        add_by_jk(jk)
    return urls
