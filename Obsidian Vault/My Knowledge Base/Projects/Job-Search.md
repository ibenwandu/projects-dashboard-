# 💼 Job-Search Project

## Vision Alignment
Income stability while building autonomous systems. This project automates the discovery, analysis, and customization of job opportunities to streamline the job search process and identify roles that align with technical growth and compensation objectives.

## Current Status
**Production (Paused)** — Disabled intentionally

The Job-Search workflow is currently paused as of Feb 27, 2026 to preserve API credits while focusing on other priorities. The system is fully functional and can be re-enabled at any time once conditions warrant resumption.

## Key Metrics

### Workflow Description
- **Daily Execution**: `daily_workflow.py` orchestrates end-to-end job discovery
- **Job Sources**: LinkedIn and Glassdoor job listings
- **Analysis Pipeline**: Scoring, filtering, and relevance analysis
- **Customization**: Resume adaptation for matched opportunities
- **Output Format**: Markdown summaries with job links and application status

### Acceptance Criteria
- Job discovery runs without errors (when enabled)
- Scoring correctly filters to relevant opportunities
- Resume customization produces valid PDFs
- Application tracking remains up to date
- Configuration allows easy enable/disable cycles

## Current Blockers
**None** — Project is intentionally paused. No active blockers to workflow execution.

## Active Tasks
**None** — All development paused pending re-enablement decision.

## Related Learning & Decisions

### Intentional Pause (Feb 27, 2026)
Decision to pause the Job-Search workflow to:
- Preserve API credits (LinkedIn, Glassdoor APIs have rate limits and costs)
- Focus on priority projects (trading systems, indicator alerts)
- Maintain configuration and pipeline for rapid re-enablement
- Review and refine job matching criteria when resumed

### Key Configuration Files
- Workflow orchestration: `../../../job-search-monorepo/daily_workflow.py`
- Search configuration: `../../../job-search-monorepo/config/search_config.json`
- Session logs: Check dated folders in `../../../job-search-monorepo/reports/`

### Earlier Development
See [[../Projects/Trading-Systems]] and [[../Projects/Scalp-Engine]] for concurrent automation projects.

## Next Milestone

### Re-enablement Conditions
Workflow will be re-enabled when:
1. **API Budget Approved**: Credits available for LinkedIn/Glassdoor API calls
2. **Priority Shift**: Other autonomous system projects reach stable state
3. **Enhanced Filtering**: Review and update job matching criteria for better relevance
4. **Resume Updates**: Current resume/CV reflects latest skills and achievements

### Resumption Checklist
- [ ] Review and approve active job search criteria
- [ ] Validate API credentials and rate limits
- [ ] Run test workflow on 1-2 sample jobs
- [ ] Confirm resume templates are current
- [ ] Monitor first 24 hours of re-enabled workflow

## Progress Notes

### Feb 27, 2026 — Intentional Pause
- Paused daily_workflow execution
- Disabled scheduled job discovery runs
- Preserved all configuration and customized resumes
- Marked project as "Production (Paused)"
- Decision: Resume when API budget allows

### Earlier Phase — Production (Active)
- Built end-to-end job discovery pipeline
- Integrated LinkedIn and Glassdoor data sources
- Implemented multi-factor job scoring (relevance, salary, location)
- Created resume customization for matched jobs
- Developed application tracking system
- Generated ~50+ analyzed job opportunities
- Applied to 20+ positions across multiple roles

## Key Components

Core automation files handle:
- **Workflow orchestration** — Job discovery → analysis → customization → output
- **Configuration management** — Search criteria, API keys, scoring rules
- **Job extraction** — Raw job listings from LinkedIn and Glassdoor sources
- **Analysis tools** — Scoring, filtering, and relevance analysis
- **Resume customization** — Generated resume PDFs tailored per opportunity
- **Application tracking** — Status monitoring and job link consolidation

## Links

**Project Folder**: [Job-Search Monorepo](../../../job-search-monorepo/)

**Workflow Documentation**:
- [Daily Workflow Script](../../../job-search-monorepo/daily_workflow.py)
- [Search Configuration](../../../job-search-monorepo/config/search_config.json)

**Related Projects**:
- [[../Projects/Trade-Alerts]] — Complementary automation project
- [[../Projects/Scalp-Engine]] — Concurrent trading system focus

---

## Implementation Note

**Note**: This project has two implementations (`job-search` and `job-search-monorepo`). Currently tracking primary implementation at `job-search-monorepo`.

---

*Last Updated: Mar 9, 2026*
*Status: Paused (Intentional) · Next Review: Pending market assessment or urgent job opportunity*
