"""Extract Indeed job key (jk) from URLs."""
from urllib.parse import urlparse

def job_key_from_url(url):
    parsed = urlparse(url)
    for part in (parsed.query or "").split("&"):
        if part.lower().startswith("jk="):
            return part.split("=", 1)[1].strip()
    return None
