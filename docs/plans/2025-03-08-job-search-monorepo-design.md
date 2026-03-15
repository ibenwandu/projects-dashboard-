# Job Search Monorepo Design

**Date:** March 8, 2025
**Author:** Claude Code
**Status:** APPROVED

---

## Overview

Create a unified **job-search-monorepo** that consolidates job scraping, AI-powered matching, and resume tailoring across multiple platforms (LinkedIn, Glassdoor, Indeed). This replaces separate `Linkedin-jobs-cs`, `Indeed-jobs`, etc. with a single, configurable system.

**Core Innovation:** Runtime-selectable **profiles** (CS, Analyst, etc.) and **platforms** (any combination of LinkedIn/Glassdoor/Indeed) with shared core logic.

---

## Requirements

### Must-Have (Phase 1)
- [x] Cross-platform job scraping (LinkedIn, Glassdoor, Indeed)
- [x] Cross-platform deduplication (same job on multiple platforms recognized)
- [x] AI-powered job scoring (Gemini/OpenAI) against candidate profile
- [x] Tailored resume generation (Markdown + PDF)
- [x] Ranked job reports with cross-platform insights
- [x] Runtime profile switching (CS vs Analyst, etc.)
- [x] Smart filtering pipeline (reduce AI scoring costs)
- [x] Fast implementation (minimal testing, pragmatic MVP)

### Nice-to-Have (Phase 2+)
- [ ] Parallel processing (3x faster scraping)
- [ ] Company reviews/ratings integration
- [ ] Salary market analysis across platforms
- [ ] Advanced dedup matching (fuzzy matching for similar jobs)

---

## Architecture

### Directory Structure

```
job-search-monorepo/
│
├── core/                              # Shared logic
│   ├── __init__.py
│   ├── job_model.py                   # JobDetails dataclass
│   ├── ai_scorer.py                   # Gemini/OpenAI scoring
│   ├── ai_client.py                   # Unified AI interface
│   ├── resume_tailor.py               # AI-powered resume customization
│   ├── report_generator.py            # Ranking, filtering, reporting
│   ├── dedup_engine.py                # Cross-platform job matching
│   ├── cache.py                       # jobs_cache.json + dedup_db.json
│   └── profile_loader.py              # Load configs at runtime
│
├── platforms/                         # Platform adapters (thin layer)
│   ├── __init__.py
│   ├── base_scraper.py                # Abstract interface
│   ├── linkedin/
│   │   ├── __init__.py
│   │   ├── scraper.py                 # Playwright + LinkedIn selectors
│   │   └── adapter.py                 # LinkedIn HTML → JobDetails
│   ├── glassdoor/
│   │   ├── __init__.py
│   │   ├── scraper.py                 # Playwright + Glassdoor selectors
│   │   └── adapter.py                 # Glassdoor HTML → JobDetails
│   └── indeed/
│       ├── __init__.py
│       ├── scraper.py                 # Playwright + Indeed selectors (NEW)
│       └── adapter.py                 # Indeed HTML → JobDetails (NEW)
│
├── profiles/                          # Swappable configs
│   ├── cs/
│   │   ├── linkedin_search.json       # Keywords, locations, filters
│   │   ├── glassdoor_search.json
│   │   ├── indeed_search.json
│   │   ├── scoring-criteria.json      # Weights, salary targets, role types
│   │   ├── master-resume.md           # Master resume for tailoring
│   │   └── approved_jobs.txt          # User-approved job IDs
│   └── analyst/
│       ├── linkedin_search.json
│       ├── glassdoor_search.json
│       ├── indeed_search.json
│       ├── scoring-criteria.json
│       ├── master-resume.md
│       └── approved_jobs.txt
│
├── output/                            # All generated files
│   ├── jobs_cache.json                # All scraped/deduplicated jobs
│   ├── dedup_db.json                  # Job fingerprints + cross-platform mappings
│   ├── reported_job_ids.txt           # Already-processed job IDs
│   ├── <job_id>.md                    # Individual job markdown
│   ├── jobs_combined.md               # All jobs in one markdown
│   ├── resumes/
│   │   ├── <job_id>_tailored.md       # Tailored resume (markdown)
│   │   ├── <job_id>_tailored.pdf      # Tailored resume (PDF)
│   │   └── job_links.md               # Application URLs + job metadata
│   └── reports/
│       └── <YYYY-MM-DD_HHMM>/
│           ├── report.md              # Top-N + full ranking + cross-platform insights
│           ├── report_metadata.json   # Market analysis data
│           └── top_job_ids.txt        # Approved job IDs from this run
│
├── run.py                             # Main CLI entry point
├── requirements.txt                   # Dependencies
├── .env                               # API keys, config
├── .gitignore
└── README.md
```

---

## Data Model

### JobDetails (Core Structure)

```python
@dataclass
class JobDetails:
    """Unified job representation across all platforms."""
    url: str                           # Platform-specific job URL
    platform: str                      # "linkedin", "glassdoor", "indeed"
    job_id: str                        # Platform-specific ID
    fingerprint: str                   # Hash for deduplication

    title: str
    company: str
    location: str
    salary: str                        # "90000-120000" or ""
    job_type: str                      # "Full-time", "Contract", etc.
    description: str                   # Full job description
    skills: list[str]                  # Extracted keywords

    score: int = 0                     # AI scoring (0-100)
    reasoning: str = ""                # Why score given
    fetched_at: str = ""               # ISO timestamp
```

---

## Workflow: Four Phases

### Phase 1: FETCH
```
Input: --platforms linkedin,glassdoor --profile cs --max-jobs 25

1. Load search config for each platform (linkedin_search.json, glassdoor_search.json, etc.)
2. For each platform:
   a. Build search URLs from keywords/locations/filters
   b. Scrape job listing pages → extract job URLs
   c. Scrape individual job pages → JobDetails
   d. Compute fingerprints for each job
3. Dedup: Check dedup_db.json for matches across platforms
4. Merge: Combine all jobs, mark multi-platform posting
5. Cache: Save to output/jobs_cache.json
6. Output: Individual .md files per job
```

**Output:**
- `output/jobs_cache.json` — all jobs (deduplicated)
- `output/dedup_db.json` — fingerprint mappings
- `output/*.md` — individual job files

---

### Phase 2: SCORE
```
Input: --profile cs (uses scoring-criteria.json from profile)

1. Load jobs_cache.json
2. Load scoring-criteria.json for selected profile
3. Filter: Exclude already-reported jobs (from reported_job_ids.txt)
4. Smart pre-filtering:
   - Location: Must match preferred/acceptable
   - Salary: Must meet minimum
   - Job type: Must be in approved types
5. For each remaining job:
   a. Build AI prompt: candidate profile + job details
   b. Call Gemini/OpenAI
   c. Extract score (0-100) + reasoning
   d. Save to jobs_cache.json
6. Output: jobs_cache.json with scores
```

**AI Prompt Template:**
```
You are a career match analyst. Score how well this job matches the candidate profile (0-100).

CANDIDATE PROFILE:
[name, title, credentials, years, salary range, location preference, role types]

JOB:
[title, company, location, salary, description, skills]

Respond:
Score: <0-100>
Reasoning: <2-4 sentences>
```

---

### Phase 3: REPORT
```
Input: --profile cs --top-n 10

1. Load jobs_cache.json (already scored)
2. Rank by score (highest first)
3. Extract top N jobs
4. Generate report.md:
   - Summary stats (total found, deduplicated, filtered, scored)
   - Market insights (avg salary, top companies, % remote, etc.)
   - Top 10 jobs with scores + reasoning
   - Full ranked list
   - Cross-platform indicators
5. Save reported job IDs → output/reported_job_ids.txt
6. Output: reports/<timestamp>/report.md
```

---

### Phase 4: RESUMES
```
Input: --profile cs (reads approved_jobs.txt)

1. Load profiles/cs/approved_jobs.txt (user-approved job IDs)
2. Load profiles/cs/master-resume.md
3. For each approved job:
   a. Fetch job details from jobs_cache.json
   b. Call AI: "Tailor this resume for this job"
   c. Save tailored resume → output/resumes/<job_id>_tailored.md
   d. Convert .md → .pdf
   e. Track platform URL for job_links.md
4. Generate output/resumes/job_links.md (table + plain URLs)
5. Output: .md + .pdf files in output/resumes/
```

---

## Deduplication Strategy

### Problem
Same job posted on LinkedIn, Glassdoor, AND Indeed = unnecessary duplicate work.

### Solution: Fingerprint Matching

**Fingerprint Hash:**
```python
def compute_fingerprint(job: JobDetails) -> str:
    key = (
        job.company.lower().strip() +
        job.title.lower().strip() +
        job.location.lower().strip() +
        (job.salary or "")  # e.g., "90000-120000"
    )
    return hashlib.sha256(key.encode()).hexdigest()
```

**Dedup Database (output/dedup_db.json):**
```json
{
  "fingerprint_abc123": {
    "platforms": ["linkedin", "glassdoor", "indeed"],
    "urls": {
      "linkedin": "https://linkedin.com/jobs/view/123456",
      "glassdoor": "https://glassdoor.com/job/789012",
      "indeed": "https://indeed.com/jobs/view/345678"
    },
    "master_job_id": "linkedin_123456",
    "created_date": "2025-03-08T10:30:00Z"
  }
}
```

**Workflow:**
1. Scrape all platforms
2. Compute fingerprints for all jobs
3. Check dedup_db.json for matches
4. If match found: merge URLs, use `master_job_id` for reporting
5. Report shows: "Customer Success Manager at Company X | LinkedIn + Glassdoor + Indeed"
6. When user approves job, all URLs available for applications

---

## Efficiency Improvements (Phase 1)

### A) Smart Filtering Pipeline
```
Scrape → Location Filter → Job Type Filter → Salary Filter → Dedup Filter → Score (AI)
```

Only jobs passing all pre-filters reach AI scoring:
- **Location:** Must match preferred/acceptable list
- **Salary:** Must meet minimum threshold
- **Job type:** Must be in approved types
- **Dedup:** Don't re-score existing versions of same job

**Expected savings:** 40-60% reduction in AI calls

### B) Pre-Filtering Logic

```python
# In score phase, before calling AI:
def should_score(job: JobDetails, criteria: dict) -> bool:
    # Location check
    if not location_matches(job.location, criteria['location']):
        return False

    # Salary check
    if criteria['salary'].get('minimum'):
        if not meets_salary_minimum(job.salary, criteria['salary']['minimum']):
            return False

    # Job type check
    if criteria.get('job_types'):
        if job.job_type not in criteria['job_types']:
            return False

    return True
```

### C) Caching
- **Job cache:** Don't re-scrape same platform URLs
- **Score cache:** If report re-run, use cached scores unless cache is stale
- **Dedup cache:** Persistent dedup_db.json prevents duplicate matching

---

## Configuration: Runtime Profile Selection

### Example: CS Profile

**profiles/cs/linkedin_search.json:**
```json
{
  "keywords": ["Customer Success", "Customer Experience Manager", "CX Manager"],
  "locations": ["Toronto, ON", "GTA", "Remote", "Hybrid"],
  "days_posted": 1,
  "job_types": ["Full-time", "Contract", "Permanent"],
  "max_results_per_search": 50
}
```

**profiles/cs/glassdoor_search.json:**
```json
{
  "keywords": ["Customer Success Manager", "Client Success", "CX Manager"],
  "locations": ["Toronto", "Ontario", "Remote"],
  "salary_min": 90000,
  "max_results": 50
}
```

**profiles/cs/indeed_search.json:**
```json
{
  "keywords": ["Customer Success", "CS Manager", "Client Success"],
  "locations": ["Toronto", "Ontario"],
  "max_results": 50
}
```

**profiles/cs/scoring-criteria.json:**
```json
{
  "candidate_profile": {
    "name": "Ibe Nwandu",
    "title": "Customer Success | CX | Business Development | Data-Driven Strategist",
    "years_of_experience": 10
  },
  "location": {
    "weight": 0.35,
    "preferred": ["Remote", "Hybrid"],
    "acceptable": ["Toronto", "GTA", "Ontario"]
  },
  "salary": {
    "weight": 0.35,
    "minimum": 90000,
    "target": 135000
  },
  "role_types": {
    "weight": 0.30,
    "primary_targets": ["Customer Success Manager", "CX Analyst", "Data-Driven Strategist"]
  }
}
```

---

## CLI Usage

```bash
# Full pipeline (fetch + score + report, resumes optional)
python run.py --platforms linkedin,glassdoor,indeed --profile cs --phase all

# Step by step
python run.py --platforms linkedin,glassdoor --profile cs --phase fetch --max-jobs 25
python run.py --profile cs --phase score
python run.py --profile cs --phase report --top-n 10

# User edits profiles/cs/approved_jobs.txt with approved job IDs
python run.py --profile cs --phase resumes

# Switch profiles/platforms easily
python run.py --platforms indeed --profile analyst --phase fetch
python run.py --profile analyst --phase score --phase report

# Options
--platforms PLATFORMS            Comma-separated: linkedin,glassdoor,indeed (default: all)
--profile PROFILE                cs or analyst (default: cs)
--phase PHASE                    fetch, score, report, resumes, all (default: all)
--max-jobs N                     Limit jobs to scrape (default: 25)
--top-n N                        Top N jobs in report (default: 10)
--headless                       Run browser in background
--debug                          Print debug info
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Shared core + thin adapters** | Reduces duplication, easy to add platforms |
| **Runtime profiles** | No code changes to switch between CS/Analyst roles |
| **Dedup by fingerprint** | Fast, accurate, handles multi-platform jobs |
| **Smart pre-filtering** | Saves 40-60% on AI costs before scoring |
| **Single-threaded Phase 1** | Fast to ship; parallel processing in Phase 2 |
| **Separate from old programs** | No risk to existing LinkedIn/Indeed code |
| **Phase 1 = MVP, Phase 2 = enhancements** | Iterate based on real usage |

---

## Next Steps

1. ✅ **Design approved** (this document)
2. → **Implementation plan** (invoke writing-plans skill)
3. → **Set up monorepo structure** (directories, git)
4. → **Build shared core modules** (job_model, ai_scorer, report_generator, dedup_engine)
5. → **Build platform adapters** (LinkedIn, Glassdoor, Indeed scrapers)
6. → **Build profiles** (CS, Analyst configurations)
7. → **CLI entry point** (run.py)
8. → **Testing & validation**
9. → **Decommission old programs** once stable

---

## Success Criteria

- ✅ Can scrape jobs from 3 platforms in one run
- ✅ Jobs are deduplicated across platforms
- ✅ AI scores jobs in under 10 minutes (for 25 jobs)
- ✅ Report shows top 10 with cross-platform insights
- ✅ Can generate tailored resumes for approved jobs
- ✅ Can switch profiles (CS ↔ Analyst) without code changes
- ✅ Can switch platforms (any combo of LinkedIn/Glassdoor/Indeed) without code changes
- ✅ Old programs (Indeed-jobs, Indeed-jobs-cs, etc.) can be retired once MVP is stable

---

**Design Document:** COMPLETE ✅
**Ready for Implementation Plan:** YES
