---
name: job_search_daily
domain: job_search
model: claude-haiku-4-5-20251001
agent: JobSearchAgent
version: 1.0
success_rate: 1.0
invocation_count: 0
---

## Purpose

Daily automated job search across 4 platforms (LinkedIn, Indeed, Glassdoor, ZipRecruiter) and 4 career tracks (Analyst, PM, Operations, Customer Success).

Scrapes new job listings, scores by relevance, deduplicates, and prepares for resume tailoring.

## Inputs

- `platforms`: List of job boards to scrape (default: linkedin, indeed, glassdoor, ziprecruiter)
- `tracks`: List of job search tracks (default: analyst, pm, ops, cs)
- `score_threshold`: Minimum relevance score (default: 0.70)

## Steps

1. **Scrape** job listings from each platform for each track
2. **Deduplicate** across platforms (same job posted in multiple places)
3. **Score** jobs by relevance using AI scorer (0.0-1.0)
4. **Filter** jobs scoring >= score_threshold
5. **Track** in application database
6. **Report** summary (jobs found, scored, deduplicated)

## Output Format

```json
{
  "timestamp": "2026-03-10T09:00:00Z",
  "jobs_found": 145,
  "jobs_scored": 142,
  "by_track": {
    "analyst": {"found": 45, "scored": 42},
    "pm": {"found": 38, "scored": 36},
    "ops": {"found": 35, "scored": 34},
    "cs": {"found": 27, "scored": 30}
  },
  "by_platform": {
    "linkedin": 50,
    "indeed": 45,
    "glassdoor": 35,
    "ziprecruiter": 15
  },
  "status": "complete"
}
```

## Self-Improvement Hooks

- If success_rate < 0.80 over 5 runs: debug scraper failures
- If jobs_scored / jobs_found < 0.90: improve deduplication logic
- If invocation_count > 100: implement incremental scraping (API polling) instead of full re-scrape
