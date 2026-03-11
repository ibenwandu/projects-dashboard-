---
name: resume_tailor
domain: job_search
model: claude-haiku-4-5-20251001
agent: JobSearchAgent
version: 1.0
success_rate: 1.0
invocation_count: 0
---

## Purpose

Tailor resumes and generate cover letters for high-scoring job opportunities.

Only processes jobs with relevance score >= 0.75 (high quality matches).
Generates customized resume sections and cover letters matching job requirements.

## Inputs

- `min_score`: Minimum job relevance score to tailor for (default: 0.75)
- `max_tailors_per_day`: Limit tailoring volume (default: 10)
- `track`: Job search track (analyst, pm, ops, cs)

## Steps

1. **Filter** jobs scored >= min_score from daily search results
2. **Limit** to max_tailors_per_day to avoid overwhelming volume
3. **Tailor** resume sections matching job requirements
4. **Generate** customized cover letter
5. **Output** tailored documents to application tracking system
6. **Report** count of applications prepared

## Output Format

```json
{
  "timestamp": "2026-03-10T10:00:00Z",
  "jobs_tailored": 8,
  "by_track": {
    "analyst": 3,
    "pm": 2,
    "ops": 2,
    "cs": 1
  },
  "tailored_jobs": [
    {
      "id": "job_123",
      "company": "Acme Corp",
      "title": "Senior Business Analyst",
      "track": "analyst",
      "score": 0.87,
      "resume_file": "resumes/tailored_acme_senior_ba.pdf",
      "cover_letter_file": "cover_letters/acme_senior_ba.pdf"
    }
  ],
  "status": "complete"
}
```

## Self-Improvement Hooks

- If success_rate < 0.80 over 5 runs: check resume template availability
- If avg_tailoring_time > 30s: optimize resume matching algorithm
- If invocation_count > 500: implement caching layer for common tailoring patterns
