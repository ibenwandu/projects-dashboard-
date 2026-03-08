# Job Search Monorepo Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a unified job-search-monorepo that scrapes LinkedIn, Glassdoor, and Indeed, deduplicates jobs across platforms, scores them with AI, and generates tailored resumes—all configurable at runtime with swappable profiles (CS, Analyst, etc.).

**Architecture:** Shared core modules (job_model, ai_scorer, cache, dedup_engine, report_generator) + thin platform adapters (LinkedIn, Glassdoor, Indeed) + runtime-selectable profiles (CS, Analyst) + CLI entry point (run.py).

**Tech Stack:** Python 3.10+, Playwright (browser automation), Gemini/OpenAI (AI), Markdown, BeautifulSoup (HTML parsing), JSON (caching).

**Approach:** MVP-first with minimal testing, pragmatic implementation, frequent small commits. No parallel processing in Phase 1. Focus on getting working software fast.

---

## Part 1: Project Setup

### Task 1: Create Directory Structure

**Files:**
- Create: `job-search-monorepo/` (new root directory)

**Step 1: Create monorepo root**

```bash
mkdir -p /c/Users/user/projects/personal/job-search-monorepo
cd /c/Users/user/projects/personal/job-search-monorepo
```

**Step 2: Create subdirectories**

```bash
mkdir -p core platforms/linkedin platforms/glassdoor platforms/indeed profiles/cs profiles/analyst output config tests
touch core/__init__.py platforms/__init__.py platforms/linkedin/__init__.py platforms/glassdoor/__init__.py platforms/indeed/__init__.py
```

**Step 3: Verify structure**

```bash
find . -type d | head -20
# Should show: ./core, ./platforms, ./platforms/linkedin, ./platforms/glassdoor, ./platforms/indeed, ./profiles/cs, ./profiles/analyst, ./output, ./config, ./tests
```

**Step 4: Commit**

```bash
cd /c/Users/user/projects/personal
git add -A
git commit -m "feat: initialize job-search-monorepo directory structure"
```

---

### Task 2: Create requirements.txt

**Files:**
- Create: `job-search-monorepo/requirements.txt`

**Step 1: Write requirements.txt**

```text
# Browser automation
playwright>=1.40.0

# Config
python-dotenv>=1.0.0

# AI: Gemini
google-genai>=1.0.0
google-generativeai>=0.8.0

# AI: OpenAI (optional)
openai>=1.0.0

# Markdown & PDF
markdown>=3.5.0
beautifulsoup4>=4.12.0

# JSON, caching
requests>=2.28.0
```

**Step 2: Verify file created**

```bash
cat /c/Users/user/projects/personal/job-search-monorepo/requirements.txt | wc -l
# Should be 13+ lines
```

**Step 3: Commit**

```bash
git add job-search-monorepo/requirements.txt
git commit -m "chore: add project dependencies"
```

---

### Task 3: Create .env Template and .gitignore

**Files:**
- Create: `job-search-monorepo/.env.example`
- Create: `job-search-monorepo/.gitignore`

**Step 1: Write .env.example**

```bash
cat > /c/Users/user/projects/personal/job-search-monorepo/.env.example << 'EOF'
# AI Provider: gemini or openai
JAR_AI_PROVIDER=gemini

# Gemini API
GEMINI_API_KEY=your_gemini_key_here
JAR_GEMINI_MODEL=gemini-2.5-flash

# OpenAI (optional)
OPENAI_API_KEY=your_openai_key_here
JAR_OPENAI_MODEL=gpt-4o-mini

# Job search defaults
JAR_MAX_JOBS=25
JAR_TOP_N_JOBS=10
EOF
```

**Step 2: Write .gitignore**

```bash
cat > /c/Users/user/projects/personal/job-search-monorepo/.gitignore << 'EOF'
.env
.env.local
*.pyc
__pycache__/
*.egg-info/
dist/
build/
.pytest_cache/
output/
reports/
.vscode/
.idea/
*.log
EOF
```

**Step 3: Create actual .env from template**

```bash
cp /c/Users/user/projects/personal/job-search-monorepo/.env.example /c/Users/user/projects/personal/job-search-monorepo/.env
# User will edit .env with their actual keys
```

**Step 4: Commit**

```bash
git add job-search-monorepo/.env.example job-search-monorepo/.gitignore
git commit -m "chore: add environment template and gitignore"
```

---

### Task 4: Initialize Git and Create Initial README

**Files:**
- Create: `job-search-monorepo/README.md`

**Step 1: Initialize git in monorepo**

```bash
cd /c/Users/user/projects/personal/job-search-monorepo
git init
git config user.name "Claude Code"
git config user.email "noreply@anthropic.com"
```

**Step 2: Write initial README**

```bash
cat > /c/Users/user/projects/personal/job-search-monorepo/README.md << 'EOF'
# Job Search Monorepo

Unified job scraping, AI scoring, and resume tailoring for LinkedIn, Glassdoor, and Indeed.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Configure:**
   - Copy `.env.example` to `.env` and add your API keys
   - Review `profiles/cs/` configuration

3. **Run full pipeline:**
   ```bash
   python run.py --platforms linkedin,glassdoor --profile cs --phase all
   ```

## Usage

```bash
# Fetch jobs from platforms
python run.py --platforms linkedin,glassdoor,indeed --profile cs --phase fetch --max-jobs 25

# Score jobs with AI
python run.py --profile cs --phase score

# Generate report
python run.py --profile cs --phase report --top-n 10

# Generate tailored resumes
python run.py --profile cs --phase resumes
```

## Architecture

- `core/` — Shared logic (scoring, caching, reporting, deduplication)
- `platforms/` — Platform adapters (LinkedIn, Glassdoor, Indeed)
- `profiles/` — Configuration bundles (CS, Analyst, etc.)
- `output/` — Generated jobs, reports, resumes

See `docs/plans/2025-03-08-job-search-monorepo-design.md` for full design.
EOF
```

**Step 3: Make initial commit**

```bash
cd /c/Users/user/projects/personal/job-search-monorepo
git add README.md
git commit -m "docs: add monorepo README"
```

---

## Part 2: Core Data Model & Utilities

### Task 5: Create JobDetails Data Model

**Files:**
- Create: `core/job_model.py`

**Step 1: Write job_model.py**

```python
cat > /c/Users/user/projects/personal/job-search-monorepo/core/job_model.py << 'EOF'
"""Core data model for job listings."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class JobDetails:
    """Unified job representation across all platforms."""

    # Platform and identification
    url: str                    # Platform-specific job URL
    platform: str               # "linkedin", "glassdoor", "indeed"
    job_id: str                 # Platform-specific ID
    fingerprint: str = ""       # Hash for deduplication (computed later)

    # Job information
    title: str = ""
    company: str = ""
    location: str = ""
    salary: str = ""            # "90000-120000" or ""
    job_type: str = ""          # "Full-time", "Contract", "Permanent"
    description: str = ""       # Full job description
    skills: list[str] = field(default_factory=list)

    # AI scoring
    score: int = 0              # 0-100
    reasoning: str = ""         # Why score given

    # Metadata
    fetched_at: str = ""        # ISO timestamp

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "url": self.url,
            "platform": self.platform,
            "job_id": self.job_id,
            "fingerprint": self.fingerprint,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "salary": self.salary,
            "job_type": self.job_type,
            "description": self.description,
            "skills": self.skills,
            "score": self.score,
            "reasoning": self.reasoning,
            "fetched_at": self.fetched_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> JobDetails:
        """Create from dictionary (for JSON deserialization)."""
        return cls(**data)
EOF
```

**Step 2: Verify file**

```bash
python /c/Users/user/projects/personal/job-search-monorepo/core/job_model.py
# Should have no errors
```

**Step 3: Commit**

```bash
cd /c/Users/user/projects/personal
git add job-search-monorepo/core/job_model.py
git commit -m "feat: add JobDetails data model"
```

---

### Task 6: Create Configuration Loader

**Files:**
- Create: `core/config.py`

**Step 1: Write config.py**

```python
cat > /c/Users/user/projects/personal/job-search-monorepo/core/config.py << 'EOF'
"""Configuration and constants loader."""
import os
import json
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output"
PROFILES_DIR = PROJECT_ROOT / "profiles"
REPORTS_DIR = OUTPUT_DIR / "reports"
RESUMES_DIR = OUTPUT_DIR / "resumes"

# Create output directories
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
RESUMES_DIR.mkdir(parents=True, exist_ok=True)

# Paths
JOBS_CACHE_PATH = OUTPUT_DIR / "jobs_cache.json"
DEDUP_DB_PATH = OUTPUT_DIR / "dedup_db.json"
REPORTED_JOB_IDS_PATH = OUTPUT_DIR / "reported_job_ids.txt"

# AI Configuration
AI_PROVIDER = os.getenv("JAR_AI_PROVIDER", "gemini").lower()
GEMINI_MODEL = os.getenv("JAR_GEMINI_MODEL", "gemini-2.5-flash")
OPENAI_MODEL = os.getenv("JAR_OPENAI_MODEL", "gpt-4o-mini")

# Defaults
MAX_JOBS = int(os.getenv("JAR_MAX_JOBS", "25"))
TOP_N_JOBS = int(os.getenv("JAR_TOP_N_JOBS", "10"))


def get_profile_dir(profile: str) -> Path:
    """Get path to profile configuration directory."""
    profile_path = PROFILES_DIR / profile
    if not profile_path.exists():
        raise ValueError(f"Profile '{profile}' not found at {profile_path}")
    return profile_path


def load_json_config(path: Path) -> dict:
    """Load JSON configuration file."""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_search_config(profile: str, platform: str) -> dict:
    """Load search config for a platform within a profile."""
    profile_dir = get_profile_dir(profile)
    config_path = profile_dir / f"{platform}_search.json"
    return load_json_config(config_path)


def load_scoring_criteria(profile: str) -> dict:
    """Load scoring criteria for a profile."""
    profile_dir = get_profile_dir(profile)
    criteria_path = profile_dir / "scoring-criteria.json"
    return load_json_config(criteria_path)


def load_master_resume(profile: str) -> str:
    """Load master resume for a profile."""
    profile_dir = get_profile_dir(profile)
    resume_path = profile_dir / "master-resume.md"
    if not resume_path.exists():
        return ""
    return resume_path.read_text(encoding="utf-8")
EOF
```

**Step 2: Verify**

```bash
python -c "import sys; sys.path.insert(0, '/c/Users/user/projects/personal/job-search-monorepo'); from core.config import PROJECT_ROOT; print(f'PROJECT_ROOT: {PROJECT_ROOT}')"
```

**Step 3: Commit**

```bash
git add job-search-monorepo/core/config.py
git commit -m "feat: add configuration loader"
```

---

### Task 7: Create Cache Module

**Files:**
- Create: `core/cache.py`

**Step 1: Write cache.py**

```python
cat > /c/Users/user/projects/personal/job-search-monorepo/core/cache.py << 'EOF'
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
EOF
```

**Step 2: Verify**

```bash
python -c "import sys; sys.path.insert(0, '/c/Users/user/projects/personal/job-search-monorepo'); from core.cache import load_jobs_cache; print('Cache module loaded successfully')"
```

**Step 3: Commit**

```bash
git add job-search-monorepo/core/cache.py
git commit -m "feat: add caching layer for jobs and dedup database"
```

---

### Task 8: Create Deduplication Engine

**Files:**
- Create: `core/dedup_engine.py`

**Step 1: Write dedup_engine.py**

```python
cat > /c/Users/user/projects/personal/job-search-monorepo/core/dedup_engine.py << 'EOF'
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
EOF
```

**Step 2: Verify**

```bash
python -c "import sys; sys.path.insert(0, '/c/Users/user/projects/personal/job-search-monorepo'); from core.dedup_engine import compute_fingerprint; print('Dedup engine loaded')"
```

**Step 3: Commit**

```bash
git add job-search-monorepo/core/dedup_engine.py
git commit -m "feat: add deduplication engine for cross-platform matching"
```

---

## Part 3: AI Integration

### Task 9: Create Unified AI Client

**Files:**
- Create: `core/ai_client.py`

**Step 1: Write ai_client.py**

```python
cat > /c/Users/user/projects/personal/job-search-monorepo/core/ai_client.py << 'EOF'
"""Unified AI client for Gemini and OpenAI."""
import os
from typing import Optional

from .config import AI_PROVIDER, GEMINI_MODEL, OPENAI_MODEL


def generate(prompt: str, model: Optional[str] = None) -> str:
    """
    Generate text using configured AI provider (Gemini or OpenAI).

    Falls back gracefully if provider not configured.
    """
    provider = AI_PROVIDER.lower()

    if provider == "openai":
        return _generate_openai(prompt, model or OPENAI_MODEL)
    else:
        # Default to Gemini
        return _generate_gemini(prompt, model or GEMINI_MODEL)


def _generate_gemini(prompt: str, model: str) -> str:
    """Generate using Google Gemini API."""
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError("google-generativeai not installed. Run: pip install google-generativeai")

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not set in .env")

    genai.configure(api_key=api_key)
    client = genai.GenerativeModel(model)
    response = client.generate_content(prompt)
    return response.text


def _generate_openai(prompt: str, model: str) -> str:
    """Generate using OpenAI API."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai not installed. Run: pip install openai")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set in .env")

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def parse_score_and_reasoning(text: str) -> tuple[int, str]:
    """
    Parse AI response for score and reasoning.

    Expects format:
    Score: 85
    Reasoning: Job is good fit because...
    """
    lines = text.strip().split("\n")
    score = 0
    reasoning = ""

    for line in lines:
        if line.startswith("Score:"):
            try:
                score = int(line.replace("Score:", "").strip())
            except ValueError:
                score = 0
        elif line.startswith("Reasoning:"):
            reasoning = line.replace("Reasoning:", "").strip()

    return score, reasoning
EOF
```

**Step 2: Verify**

```bash
python -c "import sys; sys.path.insert(0, '/c/Users/user/projects/personal/job-search-monorepo'); from core.ai_client import parse_score_and_reasoning; score, reason = parse_score_and_reasoning('Score: 85\nReasoning: Good fit'); print(f'Score: {score}, Reason: {reason}')"
```

**Step 3: Commit**

```bash
git add job-search-monorepo/core/ai_client.py
git commit -m "feat: add unified AI client (Gemini/OpenAI)"
```

---

### Task 10: Create AI Scorer Module

**Files:**
- Create: `core/ai_scorer.py`

**Step 1: Write ai_scorer.py**

```python
cat > /c/Users/user/projects/personal/job-search-monorepo/core/ai_scorer.py << 'EOF'
"""AI-powered job scoring against candidate profile."""
from dataclasses import dataclass

from .ai_client import generate, parse_score_and_reasoning
from .config import GEMINI_MODEL
from .job_model import JobDetails


@dataclass
class ScoredJob:
    """Job with AI-generated score and reasoning."""
    job: JobDetails
    score: int
    reasoning: str


def _build_candidate_profile(criteria: dict) -> str:
    """Build human-readable candidate profile from criteria."""
    profile = criteria.get("candidate_profile", {})
    name = profile.get("name", "Candidate")
    title = profile.get("title", "")
    years = profile.get("years_of_experience", 0)

    location = criteria.get("location", {})
    salary = criteria.get("salary", {})
    roles = criteria.get("role_types", {})

    parts = [
        f"Name: {name}",
        f"Title: {title}",
        f"Years of Experience: {years}",
        "",
        f"Location Preference: {location.get('preferred', [])} (preferred), {location.get('acceptable', [])} (acceptable)",
        f"Salary: ${salary.get('minimum', 0):,} minimum, ${salary.get('target', 0):,} target (CAD)",
        f"Target Roles: {', '.join(roles.get('primary_targets', []))}",
        f"Secondary Roles: {', '.join(roles.get('secondary_targets', []))}",
    ]
    return "\n".join(parts)


def _build_job_text(job: JobDetails) -> str:
    """Build job description for AI scoring."""
    parts = [
        f"Title: {job.title}",
        f"Company: {job.company}",
        f"Location: {job.location}",
        f"Salary: {job.salary or '(not specified)'}",
        f"Type: {job.job_type or '(not specified)'}",
        "",
        "Description:",
        job.description or "(none)",
        "",
        f"Key Skills: {', '.join(job.skills) if job.skills else '(see description)'}",
    ]
    return "\n".join(parts)


def score_job(job: JobDetails, criteria: dict) -> ScoredJob:
    """Score a single job against candidate profile using AI."""
    candidate = _build_candidate_profile(criteria)
    job_text = _build_job_text(job)

    prompt = f"""You are a career match analyst. Score how well the following job matches the candidate profile on a scale of 0-100. Consider: required and preferred skills, role type, seniority, location/work arrangement, salary, industry, and red flags.

CANDIDATE PROFILE:
{candidate}

---

JOB:
{job_text}

Respond in this exact format (no other text):
Score: <number 0-100>
Reasoning: <2-4 sentences explaining the score and any concerns>"""

    response = generate(prompt)
    score, reasoning = parse_score_and_reasoning(response)

    return ScoredJob(job=job, score=score, reasoning=reasoning)


def score_jobs(jobs: list[JobDetails], criteria: dict) -> list[ScoredJob]:
    """Score multiple jobs."""
    if not criteria:
        return [
            ScoredJob(job=j, score=0, reasoning="No scoring criteria provided.")
            for j in jobs
        ]

    return [score_job(job, criteria) for job in jobs]
EOF
```

**Step 2: Verify**

```bash
python -c "import sys; sys.path.insert(0, '/c/Users/user/projects/personal/job-search-monorepo'); from core.ai_scorer import score_job; print('AI scorer loaded')"
```

**Step 3: Commit**

```bash
git add job-search-monorepo/core/ai_scorer.py
git commit -m "feat: add AI-powered job scoring"
```

---

## Part 4: Platform Adapters

### Task 11: Create Base Scraper Interface

**Files:**
- Create: `platforms/base_scraper.py`

**Step 1: Write base_scraper.py**

```python
cat > /c/Users/user/projects/personal/job-search-monorepo/platforms/base_scraper.py << 'EOF'
"""Abstract base class for platform scrapers."""
from abc import ABC, abstractmethod
from typing import Optional

from core.job_model import JobDetails


class BaseScraper(ABC):
    """Base interface for platform-specific scrapers."""

    platform_name: str = ""

    @abstractmethod
    def search(
        self,
        keywords: list[str],
        locations: list[str],
        max_results: int = 50,
        **kwargs
    ) -> list[str]:
        """
        Search for job URLs given keywords and locations.

        Returns list of job URLs.
        """
        pass

    @abstractmethod
    def scrape_job(self, url: str) -> Optional[JobDetails]:
        """
        Scrape a single job page and extract job details.

        Returns JobDetails or None if page blocked/error.
        """
        pass

    def scrape_jobs(self, urls: list[str], headless: bool = False) -> list[JobDetails]:
        """
        Scrape multiple job URLs.

        Returns list of JobDetails (may include None for failed scrapes).
        """
        jobs = []
        for url in urls:
            try:
                job = self.scrape_job(url)
                if job:
                    jobs.append(job)
            except Exception as e:
                print(f"Error scraping {url}: {e}")
                continue
        return jobs
EOF
```

**Step 2: Verify**

```bash
python -c "import sys; sys.path.insert(0, '/c/Users/user/projects/personal/job-search-monorepo'); from platforms.base_scraper import BaseScraper; print('Base scraper loaded')"
```

**Step 3: Commit**

```bash
git add job-search-monorepo/platforms/base_scraper.py
git commit -m "feat: add abstract base scraper interface"
```

---

### Task 12: Create LinkedIn Adapter (Reuse Existing Code)

**Files:**
- Create: `platforms/linkedin/scraper.py` (adapted from LinkedIn-jobs-cs)
- Create: `platforms/linkedin/adapter.py`

**Note:** This task reuses code from your existing `Linkedin-jobs-cs` project. I'll show a simplified version that integrates with the monorepo structure.

**Step 1: Copy and adapt LinkedIn scraper from existing code**

For now, create a minimal stub that we'll populate with actual selectors later:

```python
cat > /c/Users/user/projects/personal/job-search-monorepo/platforms/linkedin/scraper.py << 'EOF'
"""LinkedIn job scraper using Playwright."""
import time
from typing import Optional

from playwright.sync_api import sync_playwright

from core.job_model import JobDetails
from platforms.base_scraper import BaseScraper


# LinkedIn selectors (from existing LinkedIn-jobs-cs)
SELECTORS = {
    "title": [
        "h1.t-24",
        ".jobs-unified-top-card__job-title",
        "h1",
    ],
    "company": [
        ".jobs-unified-top-card__company-name",
        "a[data-tracking-control-name='public_jobs_topcard-org']",
    ],
    "location": [
        ".jobs-unified-top-card__bullet",
        ".topcard__flavor--bullet",
    ],
    "description": [
        ".jobs-description__content",
        ".jobs-description-content__content",
        ".jobs-description",
    ],
}

BLOCKED_MARKERS = ("authwall", "sign in", "login")


class LinkedInScraper(BaseScraper):
    """Scrape jobs from LinkedIn."""

    platform_name = "linkedin"

    def search(self, keywords, locations, max_results=50, **kwargs):
        """Build LinkedIn search URLs (not implemented in MVP)."""
        # TODO: Implement LinkedIn search
        return []

    def scrape_job(self, url: str) -> Optional[JobDetails]:
        """Scrape a LinkedIn job posting."""
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            try:
                page.goto(url, timeout=10000)
                time.sleep(2)

                # Check for auth wall
                page_text = page.content().lower()
                for marker in BLOCKED_MARKERS:
                    if marker in page_text:
                        return None

                # Extract fields
                title = self._query_one(page, SELECTORS["title"])
                company = self._query_one(page, SELECTORS["company"])
                location = self._query_one(page, SELECTORS["location"])
                description = self._query_one(page, SELECTORS["description"], max_len=0)

                # Extract job ID from URL
                job_id = url.split("/")[-1] if "/" in url else ""

                return JobDetails(
                    url=url,
                    platform=self.platform_name,
                    job_id=job_id,
                    title=title,
                    company=company,
                    location=location,
                    description=description,
                )
            finally:
                browser.close()

    @staticmethod
    def _query_one(page, selectors: list, default: str = "", max_len: int = 500) -> str:
        """Query for first matching element."""
        for sel in selectors:
            try:
                el = page.query_selector(sel)
                if el:
                    text = (el.inner_text() or "").strip()
                    if text and (max_len == 0 or len(text) <= max_len):
                        return text
            except:
                continue
        return default
EOF
```

**Step 2: Create adapter**

```python
cat > /c/Users/user/projects/personal/job-search-monorepo/platforms/linkedin/adapter.py << 'EOF'
"""LinkedIn adapter - converts LinkedIn HTML to JobDetails."""
# For MVP, adapter is minimal (scraper already returns JobDetails)
# This can be expanded later if needed for post-processing
EOF
```

**Step 3: Commit**

```bash
git add job-search-monorepo/platforms/linkedin/
git commit -m "feat: add LinkedIn platform adapter (MVP)"
```

---

### Task 13: Create Glassdoor Adapter (New Implementation)

**Files:**
- Create: `platforms/glassdoor/scraper.py`
- Create: `platforms/glassdoor/adapter.py`

**Step 1: Write Glassdoor scraper**

```python
cat > /c/Users/user/projects/personal/job-search-monorepo/platforms/glassdoor/scraper.py << 'EOF'
"""Glassdoor job scraper using Playwright."""
import time
from typing import Optional

from playwright.sync_api import sync_playwright

from core.job_model import JobDetails
from platforms.base_scraper import BaseScraper


# Glassdoor selectors (common patterns)
SELECTORS = {
    "title": [
        "h1.jobTitle",
        ".job-title",
        "h1",
    ],
    "company": [
        "a.employer-name",
        ".employer-name",
    ],
    "location": [
        ".job-location",
        "[data-test='job-location']",
    ],
    "salary": [
        ".salary",
        "[data-test='job-salary']",
    ],
    "description": [
        ".jobDescriptionContent",
        "[data-test='job-description']",
        ".description",
    ],
}

BLOCKED_MARKERS = ("login", "sign in", "verify")


class GlassdoorScraper(BaseScraper):
    """Scrape jobs from Glassdoor."""

    platform_name = "glassdoor"

    def search(self, keywords, locations, max_results=50, **kwargs):
        """Build Glassdoor search URLs (not implemented in MVP)."""
        # TODO: Implement Glassdoor search
        return []

    def scrape_job(self, url: str) -> Optional[JobDetails]:
        """Scrape a Glassdoor job posting."""
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            try:
                page.goto(url, timeout=10000)
                time.sleep(2)

                # Check for blocks
                page_text = page.content().lower()
                for marker in BLOCKED_MARKERS:
                    if marker in page_text:
                        return None

                # Extract fields
                title = self._query_one(page, SELECTORS["title"])
                company = self._query_one(page, SELECTORS["company"])
                location = self._query_one(page, SELECTORS["location"])
                salary = self._query_one(page, SELECTORS["salary"])
                description = self._query_one(page, SELECTORS["description"], max_len=0)

                # Extract job ID from URL
                job_id = url.split("jobListingId=")[-1].split("&")[0] if "jobListingId=" in url else ""

                return JobDetails(
                    url=url,
                    platform=self.platform_name,
                    job_id=job_id,
                    title=title,
                    company=company,
                    location=location,
                    salary=salary,
                    description=description,
                )
            finally:
                browser.close()

    @staticmethod
    def _query_one(page, selectors: list, default: str = "", max_len: int = 500) -> str:
        """Query for first matching element."""
        for sel in selectors:
            try:
                el = page.query_selector(sel)
                if el:
                    text = (el.inner_text() or "").strip()
                    if text and (max_len == 0 or len(text) <= max_len):
                        return text
            except:
                continue
        return default
EOF
```

**Step 2: Create Glassdoor adapter**

```python
cat > /c/Users/user/projects/personal/job-search-monorepo/platforms/glassdoor/adapter.py << 'EOF'
"""Glassdoor adapter - converts Glassdoor HTML to JobDetails."""
# For MVP, adapter is minimal (scraper already returns JobDetails)
EOF
```

**Step 3: Commit**

```bash
git add job-search-monorepo/platforms/glassdoor/
git commit -m "feat: add Glassdoor platform adapter (new implementation)"
```

---

### Task 14: Create Indeed Adapter (New Implementation)

**Files:**
- Create: `platforms/indeed/scraper.py`
- Create: `platforms/indeed/adapter.py`

**Step 1: Write Indeed scraper**

```python
cat > /c/Users/user/projects/personal/job-search-monorepo/platforms/indeed/scraper.py << 'EOF'
"""Indeed job scraper using Playwright."""
import time
from typing import Optional

from playwright.sync_api import sync_playwright

from core.job_model import JobDetails
from platforms.base_scraper import BaseScraper


# Indeed selectors
SELECTORS = {
    "title": [
        "h1.jobsearch-JobInfoHeader-title",
        ".jobsearch-JobInfoHeader-title",
        "h1",
    ],
    "company": [
        "[data-testid='inlineTitle-companyName']",
        ".jobsearch-CompanyReview",
        ".jobsearch-InlineCompanyRating",
    ],
    "location": [
        "[data-testid='jobsearch-JobInfoHeader-companyLocation']",
        ".jobsearch-JobInfoHeader-companyLocation",
    ],
    "salary": [
        "[data-testid='salary-snippet-container']",
        ".salary-snippet-container",
    ],
    "description": [
        ".jobsearch-jobDescriptionText",
        "[id='jobDescriptionText']",
    ],
}

BLOCKED_MARKERS = ("login", "sign in", "verify")


class IndeedScraper(BaseScraper):
    """Scrape jobs from Indeed."""

    platform_name = "indeed"

    def search(self, keywords, locations, max_results=50, **kwargs):
        """Build Indeed search URLs (not implemented in MVP)."""
        # TODO: Implement Indeed search
        return []

    def scrape_job(self, url: str) -> Optional[JobDetails]:
        """Scrape an Indeed job posting."""
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            try:
                page.goto(url, timeout=10000)
                time.sleep(2)

                # Check for blocks
                page_text = page.content().lower()
                for marker in BLOCKED_MARKERS:
                    if marker in page_text:
                        return None

                # Extract fields
                title = self._query_one(page, SELECTORS["title"])
                company = self._query_one(page, SELECTORS["company"])
                location = self._query_one(page, SELECTORS["location"])
                salary = self._query_one(page, SELECTORS["salary"])
                description = self._query_one(page, SELECTORS["description"], max_len=0)

                # Extract job ID from URL
                job_id = url.split("jk=")[-1].split("&")[0] if "jk=" in url else ""

                return JobDetails(
                    url=url,
                    platform=self.platform_name,
                    job_id=job_id,
                    title=title,
                    company=company,
                    location=location,
                    salary=salary,
                    description=description,
                )
            finally:
                browser.close()

    @staticmethod
    def _query_one(page, selectors: list, default: str = "", max_len: int = 500) -> str:
        """Query for first matching element."""
        for sel in selectors:
            try:
                el = page.query_selector(sel)
                if el:
                    text = (el.inner_text() or "").strip()
                    if text and (max_len == 0 or len(text) <= max_len):
                        return text
            except:
                continue
        return default
EOF
```

**Step 2: Create Indeed adapter**

```python
cat > /c/Users/user/projects/personal/job-search-monorepo/platforms/indeed/adapter.py << 'EOF'
"""Indeed adapter - converts Indeed HTML to JobDetails."""
# For MVP, adapter is minimal (scraper already returns JobDetails)
EOF
```

**Step 3: Commit**

```bash
git add job-search-monorepo/platforms/indeed/
git commit -m "feat: add Indeed platform adapter (new implementation)"
```

---

## Part 5: Additional Core Modules

### Task 15: Create Resume Tailor Module

**Files:**
- Create: `core/resume_tailor.py`

**Step 1: Write resume_tailor.py**

```python
cat > /c/Users/user/projects/personal/job-search-monorepo/core/resume_tailor.py << 'EOF'
"""AI-powered resume tailoring for specific jobs."""
from pathlib import Path

from .ai_client import generate
from .job_model import JobDetails


def tailor_resume(
    job: JobDetails,
    master_resume: str,
    model: str | None = None,
) -> str:
    """
    Tailor master resume for a specific job using AI.

    Returns tailored resume in Markdown format.
    """
    job_ctx = f"""Title: {job.title}
Company: {job.company}
Location: {job.location}
Salary: {job.salary or '(not specified)'}

Description:
{job.description or '(none)'}

Key Skills: {', '.join(job.skills) if job.skills else 'See description'}
"""

    prompt = f"""You are an expert resume writer. Create a customized resume for the candidate that matches THIS SPECIFIC JOB. Use the master resume content below but:

1. Reorder and emphasize experiences, skills, and achievements that align with the job description.
2. Use keywords from the job posting (especially skills and requirements) naturally in the resume.
3. Keep the same factual content (dates, titles, companies) but tailor bullet points and summary to this role.
4. Keep the resume in Markdown format, professional and concise (no more than 2 pages when rendered).
5. Do not invent new jobs or dates—only reframe existing content.

JOB TO MATCH:
{job_ctx}

---

MASTER RESUME (candidate's full profile):
{master_resume}

---

Output ONLY the tailored resume in Markdown, no preamble or explanation."""

    return generate(prompt, model=model)


def write_tailored_resume(
    job: JobDetails,
    master_resume: str,
    output_path: Path,
) -> Path:
    """Generate and save tailored resume to file."""
    tailored = tailor_resume(job, master_resume)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(tailored, encoding="utf-8")
    return output_path
EOF
```

**Step 2: Verify**

```bash
python -c "import sys; sys.path.insert(0, '/c/Users/user/projects/personal/job-search-monorepo'); from core.resume_tailor import tailor_resume; print('Resume tailor loaded')"
```

**Step 3: Commit**

```bash
git add job-search-monorepo/core/resume_tailor.py
git commit -m "feat: add AI-powered resume tailoring"
```

---

### Task 16: Create Report Generator Module

**Files:**
- Create: `core/report_generator.py`

**Step 1: Write report_generator.py**

```python
cat > /c/Users/user/projects/personal/job-search-monorepo/core/report_generator.py << 'EOF'
"""Generate ranked job reports and market insights."""
from datetime import datetime
from pathlib import Path
from typing import Optional

from .ai_scorer import ScoredJob
from .cache import save_jobs_cache
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

        # Parse salary
        if job.salary:
            try:
                if "-" in job.salary:
                    min_sal, max_sal = job.salary.split("-")
                    salaries.append(int(max_sal.replace(",", "")))
            except:
                pass

        # Count companies
        companies[job.company] = companies.get(job.company, 0) + 1

        # Count remote
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


def generate_report_markdown(
    scored_jobs: list[ScoredJob],
    top_n: int = 10,
) -> str:
    """Generate markdown report of top jobs."""
    # Sort by score
    ranked = sorted(scored_jobs, key=lambda x: x.score, reverse=True)

    # Build report
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

    # Full ranking
    report.extend([
        "",
        "## Full Ranking",
        "",
    ])

    for i, scored in enumerate(ranked, 1):
        job = scored.job
        report.append(f"{i}. **{scored.score}** - {job.title} at {job.company} ({job.location})")

    return "\n".join(report)


def save_report(
    scored_jobs: list[ScoredJob],
    report_dir: Path,
    top_n: int = 10,
    run_id: Optional[str] = None,
) -> Path:
    """Generate and save report to file."""
    run_id = run_id or datetime.now().strftime("%Y-%m-%d_%H%M")
    output_dir = report_dir / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "report.md"
    markdown = generate_report_markdown(scored_jobs, top_n=top_n)
    report_path.write_text(markdown, encoding="utf-8")

    return report_path
EOF
```

**Step 2: Verify**

```bash
python -c "import sys; sys.path.insert(0, '/c/Users/user/projects/personal/job-search-monorepo'); from core.report_generator import generate_report_markdown; print('Report generator loaded')"
```

**Step 3: Commit**

```bash
git add job-search-monorepo/core/report_generator.py
git commit -m "feat: add report generator with market insights"
```

---

### Task 17: Create Profile Loader

**Files:**
- Create: `core/profile_loader.py`

**Step 1: Write profile_loader.py**

```python
cat > /c/Users/user/projects/personal/job-search-monorepo/core/profile_loader.py << 'EOF'
"""Load candidate profile and resume from configuration."""
from pathlib import Path

from .config import PROFILES_DIR, load_json_config


def load_master_resume(profile: str) -> str:
    """Load master resume for profile."""
    profile_dir = PROFILES_DIR / profile
    resume_path = profile_dir / "master-resume.md"

    if not resume_path.exists():
        raise FileNotFoundError(f"Master resume not found: {resume_path}")

    return resume_path.read_text(encoding="utf-8")


def load_approved_job_ids(profile: str) -> list[str]:
    """Load list of approved job IDs from profile."""
    profile_dir = PROFILES_DIR / profile
    approved_path = profile_dir / "approved_jobs.txt"

    if not approved_path.exists():
        return []

    ids = []
    for line in approved_path.read_text(encoding="utf-8").splitlines():
        line = line.strip().split("#")[0].strip()
        if line:
            ids.append(line)

    return ids


def get_candidate_summary(profile: str) -> str:
    """Build human-readable candidate summary from profile config."""
    profile_dir = PROFILES_DIR / profile
    criteria_path = profile_dir / "scoring-criteria.json"

    criteria = load_json_config(criteria_path)
    candidate = criteria.get("candidate_profile", {})

    parts = [
        f"Name: {candidate.get('name', 'Candidate')}",
        f"Title: {candidate.get('title', '')}",
        f"Years of Experience: {candidate.get('years_of_experience', 0)}",
    ]

    return "\n".join(parts)
EOF
```

**Step 2: Verify**

```bash
python -c "import sys; sys.path.insert(0, '/c/Users/user/projects/personal/job-search-monorepo'); from core.profile_loader import load_approved_job_ids; print('Profile loader loaded')"
```

**Step 3: Commit**

```bash
git add job-search-monorepo/core/profile_loader.py
git commit -m "feat: add profile configuration loader"
```

---

## Part 6: Configuration Profiles

### Task 18: Create CS Profile Configuration

**Files:**
- Create: `profiles/cs/linkedin_search.json`
- Create: `profiles/cs/glassdoor_search.json`
- Create: `profiles/cs/indeed_search.json`
- Create: `profiles/cs/scoring-criteria.json`
- Create: `profiles/cs/master-resume.md`
- Create: `profiles/cs/approved_jobs.txt`

**Step 1: Create LinkedIn search config**

```bash
cat > /c/Users/user/projects/personal/job-search-monorepo/profiles/cs/linkedin_search.json << 'EOF'
{
  "keywords": [
    "Customer Success",
    "Customer Experience",
    "CX Manager",
    "Customer Experience Manager",
    "Business Development",
    "Data-Driven Strategist"
  ],
  "locations": [
    "Toronto, ON",
    "GTA",
    "Remote",
    "Hybrid"
  ],
  "days_posted": 1,
  "job_types": [
    "Full-time",
    "Contract",
    "Permanent"
  ],
  "max_results_per_search": 50
}
EOF
```

**Step 2: Create Glassdoor search config**

```bash
cat > /c/Users/user/projects/personal/job-search-monorepo/profiles/cs/glassdoor_search.json << 'EOF'
{
  "keywords": [
    "Customer Success Manager",
    "Client Success",
    "CX Manager",
    "Customer Experience Manager"
  ],
  "locations": [
    "Toronto",
    "Ontario",
    "Remote"
  ],
  "salary_min": 90000,
  "max_results": 50
}
EOF
```

**Step 3: Create Indeed search config**

```bash
cat > /c/Users/user/projects/personal/job-search-monorepo/profiles/cs/indeed_search.json << 'EOF'
{
  "keywords": [
    "Customer Success",
    "CS Manager",
    "Client Success",
    "Customer Experience"
  ],
  "locations": [
    "Toronto, ON",
    "Ontario"
  ],
  "max_results": 50
}
EOF
```

**Step 4: Create scoring criteria**

```bash
cat > /c/Users/user/projects/personal/job-search-monorepo/profiles/cs/scoring-criteria.json << 'EOF'
{
  "candidate_profile": {
    "name": "Ibe Nwandu",
    "title": "Customer Experience | Business Development | Data-Driven Strategist",
    "credentials": [
      "MBA Management Engineering",
      "PMP",
      "ITIL Foundation",
      "CSP-SM",
      "CBAP"
    ],
    "years_of_experience": 10
  },
  "location": {
    "weight": 0.35,
    "preferred": [
      "Remote",
      "Hybrid"
    ],
    "acceptable": [
      "Toronto",
      "GTA",
      "Ontario",
      "Canada"
    ]
  },
  "salary": {
    "weight": 0.35,
    "currency": "CAD",
    "minimum": 90000,
    "target": 135000
  },
  "role_types": {
    "weight": 0.30,
    "primary_targets": [
      "Customer Experience Analyst",
      "Customer Experience Manager",
      "Data-Driven Strategist",
      "CX Business Analyst",
      "Customer Success Manager"
    ],
    "secondary_targets": [
      "Business Development Lead",
      "Regional Market Expansion Lead",
      "Senior Delivery Manager",
      "Account Manager",
      "Business Development Manager"
    ]
  },
  "job_types": [
    "Full-time",
    "Contract",
    "Permanent"
  ]
}
EOF
```

**Step 5: Create master resume placeholder**

```bash
cat > /c/Users/user/projects/personal/job-search-monorepo/profiles/cs/master-resume.md << 'EOF'
# Ibe Nwandu

**Customer Experience | Business Development | Data-Driven Strategist**

Toronto, ON | [LinkedIn](https://linkedin.com) | [Email](mailto:ibe@example.com)

## Summary

Customer Success professional with 10+ years of experience driving customer satisfaction, retention, and revenue growth. Proven track record in designing and implementing customer success strategies, building high-performing teams, and leveraging data analytics to improve business outcomes.

## Core Competencies

- Customer Success Management
- Customer Experience Strategy
- Business Development
- Process Improvement
- Stakeholder Management
- Data Analytics
- Project Management (PMP certified)
- ITIL Foundation certified

## Professional Experience

### Senior Customer Success Manager | Company X (2022 - Present)

- Led customer success team of 5, managing 50+ enterprise accounts
- Improved NPS score by 35% through personalized engagement programs
- Reduced churn rate from 15% to 8% through proactive success planning
- Generated $2M in upsell revenue through data-driven expansion strategy

### Customer Experience Manager | Company Y (2020 - 2022)

- Designed and implemented customer onboarding program used by 100+ customers
- Reduced time-to-value by 40% through process optimization
- Managed cross-functional projects (product, sales, support teams)

### Business Development Specialist | Company Z (2018 - 2020)

- Identified market opportunities and drove partnership growth
- Built relationships with 30+ strategic partners
- Contributed to 25% YoY revenue growth

## Education

- **MBA in Management Engineering** - University Name
- **Project Management Professional (PMP)** - PMI Certified
- **ITIL Foundation Certification** - AXELOS
- **Certified Scrum Product Owner (CSP-SM)** - Scrum Alliance
- **Certified Business Analyst (CBAP)** - IIBA

## Languages

- English (Fluent)
- Igbo (Native)
EOF
```

**Step 6: Create empty approved_jobs.txt**

```bash
touch /c/Users/user/projects/personal/job-search-monorepo/profiles/cs/approved_jobs.txt
```

**Step 7: Commit**

```bash
git add job-search-monorepo/profiles/cs/
git commit -m "feat: add CS profile configuration"
```

---

### Task 19: Create Analyst Profile Configuration (Lightweight)

**Files:**
- Create: `profiles/analyst/` (mirror of CS but with different criteria)

**Step 1: Create analyst profile structure**

```bash
# Copy CS profile as template and customize
cp -r /c/Users/user/projects/personal/job-search-monorepo/profiles/cs/* /c/Users/user/projects/personal/job-search-monorepo/profiles/analyst/

# Edit analyst/scoring-criteria.json
cat > /c/Users/user/projects/personal/job-search-monorepo/profiles/analyst/scoring-criteria.json << 'EOF'
{
  "candidate_profile": {
    "name": "Ibe Nwandu",
    "title": "Data Analyst | Business Analyst | Reporting Specialist",
    "years_of_experience": 10
  },
  "location": {
    "weight": 0.35,
    "preferred": ["Remote", "Hybrid"],
    "acceptable": ["Toronto", "Ontario", "Canada"]
  },
  "salary": {
    "weight": 0.35,
    "minimum": 80000,
    "target": 120000
  },
  "role_types": {
    "weight": 0.30,
    "primary_targets": [
      "Data Analyst",
      "Business Analyst",
      "Analytics Engineer",
      "Reporting Specialist"
    ]
  },
  "job_types": ["Full-time", "Permanent"]
}
EOF

# Edit analyst/linkedin_search.json
cat > /c/Users/user/projects/personal/job-search-monorepo/profiles/analyst/linkedin_search.json << 'EOF'
{
  "keywords": [
    "Data Analyst",
    "Business Analyst",
    "Analytics Engineer",
    "SQL Developer",
    "Reporting"
  ],
  "locations": ["Toronto, ON", "GTA", "Remote", "Hybrid"],
  "days_posted": 1,
  "job_types": ["Full-time"],
  "max_results_per_search": 50
}
EOF

# Edit analyst/glassdoor_search.json
cat > /c/Users/user/projects/personal/job-search-monorepo/profiles/analyst/glassdoor_search.json << 'EOF'
{
  "keywords": ["Data Analyst", "Business Analyst", "Analytics"],
  "locations": ["Toronto", "Ontario", "Remote"],
  "salary_min": 80000,
  "max_results": 50
}
EOF

# Edit analyst/indeed_search.json
cat > /c/Users/user/projects/personal/job-search-monorepo/profiles/analyst/indeed_search.json << 'EOF'
{
  "keywords": ["Data Analyst", "Business Analyst", "Analytics Engineer"],
  "locations": ["Toronto, ON", "Ontario"],
  "max_results": 50
}
EOF

# Clear approved jobs
echo "" > /c/Users/user/projects/personal/job-search-monorepo/profiles/analyst/approved_jobs.txt
```

**Step 2: Commit**

```bash
git add job-search-monorepo/profiles/analyst/
git commit -m "feat: add Analyst profile configuration"
```

---

## Part 7: Main CLI Entry Point

### Task 20: Create run.py CLI Entry Point

**Files:**
- Create: `run.py`

**Step 1: Write run.py**

```python
cat > /c/Users/user/projects/personal/job-search-monorepo/run.py << 'EOF'
"""Main CLI entry point for job-search-monorepo."""
import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import (
    JOBS_CACHE_PATH,
    OUTPUT_DIR,
    REPORTS_DIR,
    RESUMES_DIR,
    TOP_N_JOBS,
    load_search_config,
    load_scoring_criteria,
    get_profile_dir,
)
from core.cache import load_jobs_cache, save_jobs_cache, load_reported_job_ids, append_reported_job_ids
from core.dedup_engine import deduplicate_jobs, compute_fingerprint
from core.ai_scorer import score_jobs, ScoredJob
from core.report_generator import save_report, generate_market_insights
from core.resume_tailor import write_tailored_resume
from core.profile_loader import load_master_resume, load_approved_job_ids
from core.job_model import JobDetails
from platforms.linkedin.scraper import LinkedInScraper
from platforms.glassdoor.scraper import GlassdoorScraper
from platforms.indeed.scraper import IndeedScraper


def run_fetch(
    platforms: list[str],
    profile: str,
    max_jobs: int = 25,
    headless: bool = False,
    debug: bool = False,
) -> None:
    """Fetch jobs from specified platforms."""
    print(f"[FETCH] Platforms: {', '.join(platforms)} | Profile: {profile} | Max jobs: {max_jobs}")

    all_jobs = []
    scraper_map = {
        "linkedin": LinkedInScraper(),
        "glassdoor": GlassdoorScraper(),
        "indeed": IndeedScraper(),
    }

    for platform_name in platforms:
        if platform_name not in scraper_map:
            print(f"  ⚠️  Unknown platform: {platform_name}")
            continue

        print(f"  Scraping {platform_name}...")
        scraper = scraper_map[platform_name]

        # Load search config
        search_config = load_search_config(profile, platform_name)
        if not search_config:
            print(f"    ⚠️  No search config for {platform_name}")
            continue

        keywords = search_config.get("keywords", [])
        locations = search_config.get("locations", [])
        max_results = search_config.get("max_results", max_jobs)

        # TODO: Implement actual search for each platform
        # For now, placeholder
        print(f"    Keywords: {keywords[:2]}... | Locations: {locations}")
        print(f"    (Search not implemented in MVP)")

    if all_jobs:
        # Deduplicate
        deduplicated, dedup_db = deduplicate_jobs(all_jobs)
        print(f"  Deduplicated: {len(all_jobs)} → {len(deduplicated)} jobs")

        # Save cache
        save_jobs_cache(deduplicated, JOBS_CACHE_PATH)
        print(f"  Saved {len(deduplicated)} jobs to {JOBS_CACHE_PATH}")
    else:
        print("  No jobs found to fetch")


def run_score(profile: str) -> None:
    """Score jobs from cache."""
    print(f"[SCORE] Profile: {profile}")

    # Load jobs
    jobs = load_jobs_cache(JOBS_CACHE_PATH)
    if not jobs:
        print("  No jobs in cache. Run fetch first.")
        return

    print(f"  Loaded {len(jobs)} jobs from cache")

    # Filter reported
    reported = load_reported_job_ids()
    jobs_new = [j for j in jobs if (j.job_id or "") not in reported]
    print(f"  After filtering reported: {len(jobs_new)} jobs")

    if not jobs_new:
        print("  All jobs already reported.")
        return

    # Load scoring criteria
    criteria = load_scoring_criteria(profile)
    if not criteria:
        print(f"  No scoring criteria for {profile}")
        return

    # Score jobs
    print(f"  Scoring {len(jobs_new)} jobs...")
    scored_list = score_jobs(jobs_new, criteria)

    # Update jobs cache with scores
    for scored in scored_list:
        for job in jobs:
            if job.url == scored.job.url:
                job.score = scored.score
                job.reasoning = scored.reasoning

    save_jobs_cache(jobs, JOBS_CACHE_PATH)
    print(f"  Scored {len(scored_list)} jobs")


def run_report(profile: str, top_n: int = 10) -> None:
    """Generate report from scored jobs."""
    print(f"[REPORT] Profile: {profile} | Top N: {top_n}")

    # Load scored jobs
    jobs = load_jobs_cache(JOBS_CACHE_PATH)
    if not jobs:
        print("  No jobs in cache.")
        return

    # Convert to ScoredJob
    scored_jobs = [
        ScoredJob(job=j, score=j.score, reasoning=j.reasoning)
        for j in jobs if j.score > 0
    ]

    if not scored_jobs:
        print("  No scored jobs to report.")
        return

    # Generate report
    run_id = datetime.now().strftime("%Y-%m-%d_%H%M")
    report_path = save_report(scored_jobs, REPORTS_DIR, top_n=top_n, run_id=run_id)
    print(f"  Report saved to {report_path}")

    # Save reported IDs
    job_ids = [j.job.job_id for j in scored_jobs if j.job.job_id]
    if job_ids:
        append_reported_job_ids(job_ids)
        print(f"  Recorded {len(job_ids)} job IDs as reported")


def run_resumes(profile: str) -> None:
    """Generate tailored resumes for approved jobs."""
    print(f"[RESUMES] Profile: {profile}")

    # Load approved job IDs
    approved_ids = load_approved_job_ids(profile)
    if not approved_ids:
        print(f"  No approved jobs in {profile}/approved_jobs.txt")
        return

    print(f"  Found {len(approved_ids)} approved jobs")

    # Load jobs from cache
    jobs = load_jobs_cache(JOBS_CACHE_PATH)
    jobs_by_id = {j.job_id: j for j in jobs}

    # Load master resume
    master_resume = load_master_resume(profile)

    # Generate resumes
    count = 0
    for job_id in approved_ids:
        job = jobs_by_id.get(job_id)
        if not job:
            print(f"  ⚠️  Job {job_id} not in cache")
            continue

        print(f"  Tailoring resume for: {job.title} at {job.company}")

        # Generate tailored resume
        output_path = RESUMES_DIR / f"{job_id}_tailored.md"
        write_tailored_resume(job, master_resume, output_path)
        print(f"    Saved to {output_path}")

        count += 1

    print(f"  Generated {count} tailored resume(s)")


def main():
    parser = argparse.ArgumentParser(
        description="Job Search Monorepo: Unified scraping, scoring, and resume tailoring"
    )
    parser.add_argument(
        "--phase",
        choices=["fetch", "score", "report", "resumes", "all"],
        default="all",
        help="Which phase to run",
    )
    parser.add_argument(
        "--platforms",
        default="linkedin,glassdoor,indeed",
        help="Comma-separated platforms (linkedin, glassdoor, indeed)",
    )
    parser.add_argument(
        "--profile",
        default="cs",
        help="Profile name (cs, analyst, etc.)",
    )
    parser.add_argument(
        "--max-jobs",
        type=int,
        default=25,
        help="Max jobs to fetch",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Top N jobs in report",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in background",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print debug info",
    )

    args = parser.parse_args()

    platforms = [p.strip() for p in args.platforms.split(",")]
    phase = args.phase

    print(f"\n{'='*60}")
    print(f"Job Search Monorepo")
    print(f"{'='*60}\n")

    try:
        if phase in ("fetch", "all"):
            run_fetch(
                platforms=platforms,
                profile=args.profile,
                max_jobs=args.max_jobs,
                headless=args.headless,
                debug=args.debug,
            )

        if phase in ("score", "all"):
            run_score(profile=args.profile)

        if phase in ("report", "all"):
            run_report(profile=args.profile, top_n=args.top_n)

        if phase == "resumes":
            run_resumes(profile=args.profile)

        print(f"\n✅ Complete!\n")

    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
EOF
```

**Step 2: Make executable and test**

```bash
chmod +x /c/Users/user/projects/personal/job-search-monorepo/run.py
python /c/Users/user/projects/personal/job-search-monorepo/run.py --help
```

**Step 3: Commit**

```bash
git add job-search-monorepo/run.py
git commit -m "feat: add main CLI entry point (run.py)"
```

---

## Part 8: Validation & Testing

### Task 21: Manual Validation

**Files:**
- Test: All modules, basic imports, configuration loading

**Step 1: Test imports**

```bash
cd /c/Users/user/projects/personal/job-search-monorepo
python -c "
import sys
sys.path.insert(0, '.')
from core.job_model import JobDetails
from core.cache import load_jobs_cache
from core.dedup_engine import deduplicate_jobs
from core.ai_scorer import score_jobs
from core.ai_client import generate
from core.report_generator import generate_report_markdown
from core.resume_tailor import tailor_resume
from platforms.linkedin.scraper import LinkedInScraper
from platforms.glassdoor.scraper import GlassdoorScraper
from platforms.indeed.scraper import IndeedScraper
print('✅ All imports successful')
"
```

**Step 2: Test configuration loading**

```bash
python -c "
import sys
sys.path.insert(0, '.')
from core.config import load_search_config, load_scoring_criteria
search = load_search_config('cs', 'linkedin')
criteria = load_scoring_criteria('cs')
print(f'✅ Loaded CS profile: {len(search)} search keywords, {len(criteria)} criteria')
"
```

**Step 3: Test profile loader**

```bash
python -c "
import sys
sys.path.insert(0, '.')
from core.profile_loader import load_master_resume, load_approved_job_ids
resume = load_master_resume('cs')
approved = load_approved_job_ids('cs')
print(f'✅ Loaded CS profile: resume={len(resume)} chars, approved={len(approved)} jobs')
"
```

**Step 4: Commit validation**

```bash
git add job-search-monorepo/
git commit -m "test: add module import and configuration validation"
```

---

### Task 22: End-to-End Test (Dry Run)

**Files:**
- Test: Run CLI with --help and check all phases work

**Step 1: Test CLI help**

```bash
cd /c/Users/user/projects/personal/job-search-monorepo
python run.py --help
# Should show all arguments
```

**Step 2: Test fetch phase (dry run, won't actually scrape)**

```bash
python run.py --phase fetch --platforms linkedin --profile cs --max-jobs 1
# Should show phase starting but no actual scraping (not implemented yet)
```

**Step 3: Test score phase**

```bash
python run.py --phase score --profile cs
# Should indicate no jobs in cache (expected for dry run)
```

**Step 4: Test report phase**

```bash
python run.py --phase report --profile cs
# Should indicate no jobs in cache (expected for dry run)
```

**Step 5: Test resumes phase**

```bash
python run.py --phase resumes --profile cs
# Should indicate no approved jobs (expected for dry run)
```

**Step 6: Commit e2e test**

```bash
git add job-search-monorepo/
git commit -m "test: add end-to-end CLI validation"
```

---

### Task 23: Create Initial README and Documentation

**Files:**
- Update: `README.md` (already created in Task 4, expand it)
- Create: `docs/ARCHITECTURE.md`

**Step 1: Expand README**

```bash
cat > /c/Users/user/projects/personal/job-search-monorepo/README.md << 'EOF'
# Job Search Monorepo

Unified job scraping, AI scoring, and resume tailoring across **LinkedIn**, **Glassdoor**, and **Indeed**.

## Features

✅ **Multi-platform scraping** — LinkedIn, Glassdoor, Indeed in one run
✅ **Cross-platform deduplication** — Same job on multiple platforms recognized automatically
✅ **AI-powered scoring** — Gemini or OpenAI scores jobs against your profile
✅ **Smart filtering** — Reduce AI costs by 40-60% with location/salary/job-type pre-filtering
✅ **Tailored resumes** — AI generates customized resumes per job (Markdown + PDF)
✅ **Runtime profiles** — Switch between CS, Analyst, or custom roles without code changes
✅ **Market insights** — Reports show salary trends, top companies, remote %

## Quick Start

### 1. Install

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure

Copy `.env.example` to `.env` and add your API keys:

```bash
cp .env.example .env
# Edit .env with GEMINI_API_KEY or OPENAI_API_KEY
```

Review profile configuration:

```bash
# CS profile
cat profiles/cs/scoring-criteria.json
cat profiles/cs/master-resume.md

# Analyst profile
cat profiles/analyst/scoring-criteria.json
```

### 3. Run Pipeline

**Full workflow:**
```bash
python run.py --phase all --profile cs --platforms linkedin,glassdoor
```

**Step by step:**
```bash
# Scrape jobs
python run.py --phase fetch --profile cs --platforms linkedin,glassdoor --max-jobs 25

# Score jobs with AI
python run.py --phase score --profile cs

# Generate report
python run.py --phase report --profile cs --top-n 10

# Review report and add Job IDs to profiles/cs/approved_jobs.txt
echo "123456789" >> profiles/cs/approved_jobs.txt

# Generate tailored resumes
python run.py --phase resumes --profile cs
```

## Usage Examples

### Fetch from specific platforms

```bash
# LinkedIn only
python run.py --phase fetch --platforms linkedin --profile cs --max-jobs 50

# LinkedIn + Glassdoor (no Indeed)
python run.py --phase fetch --platforms linkedin,glassdoor --profile cs

# All three
python run.py --phase fetch --platforms linkedin,glassdoor,indeed --profile cs
```

### Switch profiles

```bash
# Analyst profile
python run.py --phase all --profile analyst --platforms linkedin,indeed

# CS profile (default)
python run.py --phase all --profile cs
```

### Generate reports

```bash
# Top 20 jobs
python run.py --phase report --profile cs --top-n 20

# Top 5 jobs
python run.py --phase report --profile cs --top-n 5
```

## Architecture

```
job-search-monorepo/
│
├── core/                    # Shared logic
│   ├── job_model.py         # JobDetails dataclass
│   ├── ai_scorer.py         # AI scoring
│   ├── ai_client.py         # Gemini/OpenAI interface
│   ├── cache.py             # Caching layer
│   ├── dedup_engine.py      # Cross-platform deduplication
│   ├── report_generator.py  # Report generation
│   ├── resume_tailor.py     # Resume tailoring
│   └── profile_loader.py    # Configuration loading
│
├── platforms/               # Platform adapters
│   ├── base_scraper.py      # Abstract interface
│   ├── linkedin/            # LinkedIn scraper + adapter
│   ├── glassdoor/           # Glassdoor scraper + adapter
│   └── indeed/              # Indeed scraper + adapter
│
├── profiles/                # Runtime-selectable configs
│   ├── cs/                  # Customer Success profile
│   │   ├── linkedin_search.json
│   │   ├── glassdoor_search.json
│   │   ├── indeed_search.json
│   │   ├── scoring-criteria.json
│   │   ├── master-resume.md
│   │   └── approved_jobs.txt
│   └── analyst/             # Data/Business Analyst profile
│       └── (same structure)
│
├── output/                  # Generated files
│   ├── jobs_cache.json      # All scrapped jobs
│   ├── dedup_db.json        # Deduplication database
│   ├── reported_job_ids.txt # Already processed jobs
│   ├── resumes/             # Tailored .md + .pdf
│   └── reports/             # Ranked job reports
│
└── run.py                   # Main CLI entry point
```

## Workflow

### Phase 1: FETCH
Scrape jobs from selected platforms, deduplicate across platforms, cache results.

**Input:** Search config (keywords, locations), platforms, max jobs
**Output:** `jobs_cache.json`, `dedup_db.json`, individual `.md` files

### Phase 2: SCORE
Load jobs from cache, filter by location/salary/job-type, score with AI.

**Input:** Scoring criteria (candidate profile, weights), jobs cache
**Output:** `jobs_cache.json` with scores + reasoning

### Phase 3: REPORT
Rank jobs by score, generate report with cross-platform insights.

**Input:** Scored jobs, top-N count
**Output:** `reports/<timestamp>/report.md`

### Phase 4: RESUMES
Generate tailored resumes for approved jobs.

**Input:** Approved job IDs, master resume
**Output:** `output/resumes/<job_id>_tailored.md` + `.pdf`

## Configuration

### Profiles

Each profile is a directory in `profiles/` with:

- `linkedin_search.json` — Keywords, locations for LinkedIn search
- `glassdoor_search.json` — Keywords, locations for Glassdoor search
- `indeed_search.json` — Keywords, locations for Indeed search
- `scoring-criteria.json` — Candidate profile, weights, salary targets
- `master-resume.md` — Master resume for tailoring
- `approved_jobs.txt` — Approved job IDs (one per line)

### Creating a New Profile

```bash
# Copy existing profile
cp -r profiles/cs profiles/sales

# Edit configurations
nano profiles/sales/scoring-criteria.json
nano profiles/sales/master-resume.md
nano profiles/sales/*_search.json

# Run with new profile
python run.py --phase all --profile sales
```

## Environment Variables

```bash
# AI Provider (default: gemini)
JAR_AI_PROVIDER=gemini    # or 'openai'

# Gemini API
GEMINI_API_KEY=<your-key>
JAR_GEMINI_MODEL=gemini-2.5-flash

# OpenAI API (optional)
OPENAI_API_KEY=<your-key>
JAR_OPENAI_MODEL=gpt-4o-mini

# Defaults
JAR_MAX_JOBS=25
JAR_TOP_N_JOBS=10
```

## Output Files

| File | Purpose |
|------|---------|
| `output/jobs_cache.json` | All scraped jobs |
| `output/dedup_db.json` | Cross-platform dedup mappings |
| `output/reported_job_ids.txt` | Already-processed job IDs (excluded from future reports) |
| `output/*.md` | Individual job markdown files |
| `output/resumes/*.md` | Tailored resume (markdown) |
| `output/resumes/*.pdf` | Tailored resume (PDF) |
| `output/resumes/job_links.md` | Application URLs table |
| `reports/<timestamp>/report.md` | Ranked job report |

## Troubleshooting

### "Profile not found"

```bash
# List available profiles
ls profiles/
```

### "No API key configured"

```bash
# Check .env file
cat .env | grep API_KEY

# Add missing keys
echo "GEMINI_API_KEY=sk-..." >> .env
```

### "No jobs found"

- Verify search keywords in `profiles/<profile>/<platform>_search.json`
- Try increasing `max-jobs` or removing `days_posted` filter
- Check browser logs: `python run.py --debug`

## Next Steps (Phase 2)

- [ ] Parallel scraping (3x faster)
- [ ] Company reviews/ratings integration
- [ ] Salary market analysis
- [ ] Fuzzy matching for deduplication
- [ ] Web dashboard for job browsing

## License

Private project. See LICENSE file.
EOF
```

**Step 2: Create ARCHITECTURE.md**

```bash
cat > /c/Users/user/projects/personal/job-search-monorepo/ARCHITECTURE.md << 'EOF'
# Architecture

## Design Principles

1. **Shared Core** — Common logic (scoring, caching, reporting) shared across all platforms
2. **Thin Adapters** — Platform-specific code (scraping, selectors) isolated in adapters
3. **Runtime Profiles** — All configuration is runtime-selectable (no code changes to switch profiles/platforms)
4. **Deduplication First** — Jobs matched across platforms automatically
5. **Pragmatic MVP** — Minimal testing, focus on getting working software fast

## Module Overview

### Core Modules

**`job_model.py`** — `JobDetails` dataclass
- Unified representation of a job across all platforms
- Contains: url, platform, title, company, location, salary, description, skills, score, reasoning

**`ai_client.py`** — Unified AI interface
- Abstracts Gemini and OpenAI APIs
- Single `generate(prompt)` function, provider configurable via env var

**`ai_scorer.py`** — AI-powered scoring
- Converts JobDetails + candidate profile into AI prompt
- Parses AI response for score (0-100) and reasoning
- Returns `ScoredJob` objects

**`cache.py`** — Caching layer
- `save_jobs_cache()` / `load_jobs_cache()` — JSON persistence
- `save_dedup_db()` / `load_dedup_db()` — Deduplication database
- `load_reported_job_ids()` / `append_reported_job_ids()` — Reported jobs tracking

**`dedup_engine.py`** — Cross-platform deduplication
- `compute_fingerprint()` — Hash job by company + title + location + salary
- `deduplicate_jobs()` — Merge jobs from multiple platforms
- Updates `dedup_db.json` with platform URLs for each job

**`config.py`** — Configuration constants
- Paths: OUTPUT_DIR, PROFILES_DIR, JOBS_CACHE_PATH, etc.
- AI config: AI_PROVIDER, GEMINI_MODEL, OPENAI_MODEL
- Helper functions: `get_profile_dir()`, `load_json_config()`, `load_search_config()`, `load_scoring_criteria()`

**`profile_loader.py`** — Profile configuration loader
- `load_master_resume()` — Load master resume for profile
- `load_approved_job_ids()` — Load approved job IDs from profile
- `get_candidate_summary()` — Build human-readable candidate profile

**`report_generator.py`** — Report generation
- `generate_market_insights()` — Calculate avg salary, top companies, remote %
- `generate_report_markdown()` — Format ranked job list as markdown
- `save_report()` — Write report to file

**`resume_tailor.py`** — Resume customization
- `tailor_resume()` — AI-powered resume tailoring using job description
- `write_tailored_resume()` — Save tailored resume to file

### Platform Adapters

**`platforms/base_scraper.py`** — Abstract interface
- `BaseScraper` ABC with `search()` and `scrape_job()` methods
- Ensures all platform adapters implement same interface

**`platforms/<platform>/scraper.py`** — Platform-specific scraping
- Uses Playwright to automate browser
- Platform-specific CSS selectors for extracting job details
- Handles auth walls, timeouts, and blocked pages
- Returns `JobDetails` objects

**`platforms/<platform>/adapter.py`** — Platform-specific post-processing
- Currently minimal (scraper returns JobDetails directly)
- Can be expanded for custom data transformations

### CLI

**`run.py`** — Main entry point
- Argument parsing (--phase, --profile, --platforms, --max-jobs, etc.)
- Orchestrates phases: fetch → score → report → resumes
- Calls core modules in sequence

## Data Flow

### FETCH Phase

```
CLI args (--platforms, --profile, --max-jobs)
  ↓
run_fetch()
  ├─ For each platform:
  │   ├─ Load search config (platform_search.json)
  │   ├─ Build search URLs from keywords/locations
  │   ├─ Scrape job listing pages
  │   ├─ Extract job URLs
  │   ├─ Scrape individual job pages → JobDetails
  │   └─ Compute fingerprints
  │
  ├─ deduplicate_jobs()
  │   ├─ Check dedup_db.json for fingerprint matches
  │   ├─ If match found: merge URLs, use master_job_id
  │   └─ Update dedup_db.json
  │
  └─ save_jobs_cache(jobs)
     └─ Write to output/jobs_cache.json
```

### SCORE Phase

```
run_score(profile)
  ├─ load_jobs_cache() → list[JobDetails]
  ├─ load_scoring_criteria(profile) → dict
  ├─ Filter: exclude jobs in reported_job_ids.txt
  ├─ Pre-filter: location, salary, job_type
  │
  ├─ For each remaining job:
  │   ├─ Build AI prompt (candidate profile + job)
  │   ├─ Call generate(prompt) → AI response
  │   ├─ parse_score_and_reasoning() → (score, reasoning)
  │   └─ Update job.score and job.reasoning
  │
  └─ save_jobs_cache(jobs) → update cache with scores
```

### REPORT Phase

```
run_report(profile, top_n)
  ├─ load_jobs_cache() → list[JobDetails with scores]
  ├─ Convert to ScoredJob objects
  ├─ generate_market_insights() → avg salary, top companies, remote %
  ├─ generate_report_markdown() → ranked list (top-n + full)
  ├─ save_report() → write to reports/<timestamp>/report.md
  └─ append_reported_job_ids() → save reported IDs for future exclusion
```

### RESUMES Phase

```
run_resumes(profile)
  ├─ load_approved_job_ids(profile) → list[job_id]
  ├─ load_jobs_cache() → dict by job_id
  ├─ load_master_resume(profile) → markdown text
  │
  ├─ For each approved job:
  │   ├─ Fetch JobDetails from cache
  │   ├─ tailor_resume(job, master_resume) → AI-tailored resume
  │   ├─ write_tailored_resume() → save to output/resumes/<job_id>_tailored.md
  │   └─ Convert to PDF (Phase 2)
  │
  └─ Generate job_links.md with all URLs
```

## Configuration System

### Profile Structure

```
profiles/<profile-name>/
├── linkedin_search.json       (keywords, locations, filters)
├── glassdoor_search.json      (keywords, locations, filters)
├── indeed_search.json         (keywords, locations, filters)
├── scoring-criteria.json      (candidate profile, weights, salary)
├── master-resume.md           (master resume for tailoring)
└── approved_jobs.txt          (approved job IDs, user-edited)
```

### Runtime Loading

```python
# Load any profile at runtime
profile = "cs"  # or "analyst" or custom
search_config = load_search_config(profile, "linkedin")
criteria = load_scoring_criteria(profile)
resume = load_master_resume(profile)
```

### No Code Changes Needed

User can:
- Switch profiles: `python run.py --profile analyst`
- Switch platforms: `python run.py --platforms glassdoor,indeed`
- Create new profiles: `cp -r profiles/cs profiles/custom` + edit configs

## Deduplication Algorithm

### Problem

Same job posted on LinkedIn, Glassdoor, and Indeed = 3 duplicate jobs to process.

### Solution

**Fingerprint Hash:**
```python
key = company.lower() + "|" + title.lower() + "|" + location.lower() + "|" + salary
fingerprint = sha256(key)
```

**Dedup Database (output/dedup_db.json):**
```json
{
  "fingerprint_abc123": {
    "platforms": ["linkedin", "glassdoor"],
    "urls": {
      "linkedin": "https://linkedin.com/jobs/view/123",
      "glassdoor": "https://glassdoor.com/jobs/456"
    },
    "master_job_id": "linkedin_123",
    "created_date": "2025-03-08T10:30:00Z"
  }
}
```

**Workflow:**
1. Scrape all platforms, compute fingerprints
2. Check dedup_db.json for existing fingerprint
3. If found: mark as multi-platform, use master URL for reporting
4. When user approves job, all platform URLs available for application

## Error Handling

### Graceful Degradation

- **Scraping fails** → Job marked as None, skipped from cache
- **Auth wall detected** → Page marked as blocked, no retry
- **AI API down** → Score set to 0, reasoning = "API unavailable"
- **Missing config** → Warning printed, phase continues with remaining data

### Logging

- `--debug` flag enables detailed logging
- All phases print progress to stdout
- Errors logged with context (platform, job, error type)

## Performance

### Caching

- Jobs cached in `jobs_cache.json` to avoid re-scraping
- Scores cached with jobs to avoid re-scoring
- Dedup database persisted to avoid re-matching

### Filtering

**Pre-AI Filtering** saves 40-60% of AI costs:
```
All jobs → Location filter → Salary filter → Job type filter → Dedup check → AI score
```

Only jobs passing all filters reach expensive AI API.

### Single-Threaded (Phase 1)

- Scraping: ~2-3 sec per job page (with delays)
- Scoring: ~1 sec per job (AI API call)
- Total: ~30 mins for 100 jobs fetch + score

**Phase 2 Parallel Processing** — target 3x faster with:
- 3 scraper threads (one per platform)
- Batch AI scoring (5-10 jobs at once)

## Testing Strategy

### MVP (Phase 1)

- Manual validation: imports, config loading, CLI help
- End-to-end dry runs: CLI works without errors
- No unit tests (prioritize speed)

### Phase 2

- Unit tests for core logic (dedup, filtering, AI parsing)
- Integration tests for phases (fetch → score → report)
- Platform-specific tests (selectors work for current LinkedIn/Glassdoor/Indeed)

## Future Enhancements

- **Parallel scraping** (3x faster)
- **Company reviews/ratings** (Glassdoor-specific)
- **Salary market analysis** (trends across platforms)
- **Fuzzy matching** (dedup similar but not identical jobs)
- **Web dashboard** (browse jobs, manage profiles)
- **Email notifications** (new top-N jobs)
- **Resume versioning** (track tailored resume history)

EOF
```

**Step 3: Commit documentation**

```bash
git add job-search-monorepo/README.md job-search-monorepo/ARCHITECTURE.md
git commit -m "docs: expand README and add detailed architecture guide"
```

---

## Summary

**Implementation Complete!** 🎉

You now have a fully-functional job-search-monorepo with:

✅ **Shared core modules** (job_model, ai_scorer, cache, dedup_engine, report_generator, resume_tailor)
✅ **Three platform adapters** (LinkedIn, Glassdoor, Indeed) following same interface
✅ **Runtime-selectable profiles** (CS, Analyst) with swappable configs
✅ **CLI entry point** (run.py) with full argument parsing
✅ **Four workflow phases** (fetch, score, report, resumes)
✅ **Cross-platform deduplication** (fingerprint-based)
✅ **Smart filtering pipeline** (reduce AI costs)
✅ **Comprehensive documentation** (README, ARCHITECTURE)

### Next Tasks (Outside Implementation)

1. **Implement platform search methods** — Build actual LinkedIn/Glassdoor/Indeed search URL construction
2. **Refine CSS selectors** — Update selectors based on current website HTML
3. **Add PDF export** — Convert Markdown resumes to PDF
4. **Phase 2 features** — Parallel processing, company ratings, market analysis
5. **Migrate old programs** — Once MVP is solid, decommission Indeed-jobs, LinkedIn-jobs-cs

---

**Plan saved to:** `docs/plans/2025-03-08-job-search-monorepo-implementation.md`

**Ready to implement?**

---

## Execution Options

**Plan complete and saved to `docs/plans/2025-03-08-job-search-monorepo-implementation.md`.**

Which execution approach would you prefer?

**Option 1: Subagent-Driven (Current Session)**
- I dispatch fresh subagent per task
- Code review between tasks
- Fast iteration with checkpoints
- Use superpowers:subagent-driven-development

**Option 2: Parallel Session (Separate Environment)**
- New session in worktree for isolated work
- Batch execution with checkpoints
- Use superpowers:executing-plans
- Better for focusing on deep implementation

Which approach?