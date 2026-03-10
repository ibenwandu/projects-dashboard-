# Idea Backlog

A comprehensive system for tracking, evaluating, and managing project ideas aligned with my vision of building intelligent financial systems.

**Last Updated:** 2026-03-09
**Review Cadence:** Weekly (Monday 9 AM)

---

## Evaluation Criteria

Standardized scoring system (1-10 scale) for objective idea evaluation:

| Criterion | Description | Scoring Guide |
|-----------|-------------|----------------|
| **Vision Alignment** | How well does this align with my core mission: intelligent financial systems that reduce human bias and increase profitability? | 1=Unrelated, 5=Tangential, 10=Core mission enabler |
| **Effort** | Time/complexity to build and deploy | 1=Trivial (<2h), 5=Medium (1-2w), 10=Major (>1m) |
| **ROI** | Expected return on time/capital investment | 1=Minimal, 5=Moderate, 10=High impact/revenue |
| **Dependencies** | What must exist first? | Clear dependency tree required |
| **Status** | Current stage of development | New, Researched, In Progress, Blocked, Paused |

---

## Current Ideas

### 1. Currency Trend Tracker

**Summary:** Real-time visualization and analysis of currency pair trends with technical analysis overlays and deviation detection from normal market conditions.

| Criterion | Score | Notes |
|-----------|-------|-------|
| Vision Alignment | 8 | Core to forex trading system; feeds risk management |
| Effort | 5 | Medium - requires data pipeline, frontend dashboard |
| ROI | 7 | High - enables quicker market interpretation |
| Dependencies | Forex data source, Time-series database |
| Status | Researched |

**Key Features:**
- Real-time trend visualization (multiple timeframes)
- Technical analysis indicators (MA, RSI, MACD)
- Deviation alerts when trends break patterns
- Historical pattern matching

**Next Steps:**
- [ ] Prototype with Polygon.io Forex API
- [ ] Design dashboard layout (React + D3)
- [ ] Test with historical data (6-month backtest)

---

### 2. Recruiter Email Automation

**Summary:** Intelligent email workflow system to automate outreach to recruiters with personalized messages based on job market analysis and my profile strengths.

| Criterion | Score | Notes |
|-----------|-------|-------|
| Vision Alignment | 7 | Supports financial independence goal; enables scaling job applications |
| Effort | 5 | Medium - email templating, LinkedIn API integration, schedule management |
| ROI | 6 | Moderate - reduces manual effort; varies with market conditions |
| Dependencies | LinkedIn API access, Email service (SMTP or SendGrid), Job matching algorithm |
| Status | Researched |

**Key Features:**
- Template system with variable substitution
- LinkedIn job matching and recruiter identification
- Batch scheduling with rate limiting
- Response tracking and follow-up management
- A/B testing framework for subject lines/body copy

**Next Steps:**
- [ ] Document email templates (3-5 variations)
- [ ] Build job matching algorithm
- [ ] Set up email service with proper SPF/DKIM

---

### 3. Market Regime Detection

**Summary:** ML-based system to detect and classify current market regime (trending up/down, sideways, high volatility, regime shift) with probability scoring and alerts.

| Criterion | Score | Notes |
|-----------|-------|-------|
| Vision Alignment | 9 | **CRITICAL** - Foundational for trading strategy selection and risk management |
| Effort | 9 | High - requires ML pipeline, feature engineering, backtesting, monitoring |
| ROI | 9 | **HIGHEST** - Enables strategy adaptation; core risk mitigation tool |
| Dependencies | 1-5yr historical OHLCV data, ML pipeline infrastructure, Model monitoring |
| Status | New |

**Key Features:**
- Regime classification (Trending, Sideways, Volatile, Breakout, Consolidation)
- Probability scoring for each regime state
- Hidden Markov Model or similar probabilistic classifier
- Real-time detection with lookback windows (15m, 1h, 4h, daily)
- Alert system for regime transitions
- Performance analytics by regime

**Business Impact:**
- Enables dynamic strategy selection
- Reduces losses in wrong regimes
- Identifies optimal entry/exit conditions
- Feeds all other trading systems

**Next Steps:**
- [ ] Research existing ML approaches (academic papers)
- [ ] Collect and clean historical data (multiple asset classes)
- [ ] Design feature engineering pipeline
- [ ] Build and train baseline model
- [ ] Backtest regime detection accuracy
- [ ] Deploy with real-time monitoring

---

## Archive

*Ideas that were evaluated and rejected go here. This section is empty and ready to document decisions.*

**Format for archived ideas:**
```
### [Archived Idea Name]
- **Reason for rejection:** [Clear explanation]
- **Date archived:** YYYY-MM-DD
- **Score summary:** [Scores that led to rejection]
- **Potential revival conditions:** [What would make this viable again?]
```

---

## Decision Guidelines

### When to INITIATE an idea:

1. **Vision Alignment ≥ 7** - Moves needle on core mission
2. **(Effort + ROI) Score ≥ 14** - Feasible effort-to-value ratio
3. **Dependencies are clear** - No unknown blockers
4. **Current capacity available** - Not overloaded with in-progress work
5. **Can deliver MVP in ≤ 2 weeks** - Quick learning cycle

**Process:**
- Score idea using evaluation criteria
- Move to "In Progress" section
- Create project in Projects folder
- Schedule weekly review milestone

### When to DROP an idea:

1. **Vision Alignment < 5** - Doesn't serve core mission
2. **Effort > 5 AND ROI < 5** - Not worth time investment
3. **Key dependencies blocked indefinitely** - Can't move forward
4. **Better alternatives emerged** - Opportunity cost too high
5. **Market conditions changed** - Idea no longer relevant
6. **No progress in 2+ weeks** - Indicates hidden blockers

**Process:**
- Document rejection reason clearly
- Move to Archive with timestamp
- Note any learnings for future reference

---

## Review Schedule

### Weekly Review (Monday, 9:00 AM)
- **Duration:** 15 minutes
- **Process:**
  1. Review current idea scores
  2. Check status of "In Progress" ideas
  3. Evaluate any new ideas since last review
  4. Identify blockers or capacity changes
  5. Update this backlog

### Bi-Weekly Deep Dive (2nd & 4th Monday)
- **Duration:** 45 minutes
- **Process:**
  1. Analyze completed projects - extract learnings
  2. Research emerging market trends
  3. Reassess current idea priorities
  4. Plan next sprint of work

### Monthly Strategy Review (1st Monday)
- **Duration:** 90 minutes
- **Process:**
  1. Review quarter progress against goals
  2. Evaluate how ideas map to larger vision
  3. Consider strategic pivots or new directions
  4. Update this backlog with strategic changes

---

## Related Resources

- [[00-DASHBOARD]] - Overall system dashboard with active projects
- [[Trading-Journal/Trading Log]] - Market observations and trade analysis
- [[Research/Market Analysis]] - Ongoing market research and findings
- [[Projects]] - Project tracking and implementation details

---

## Statistics

| Metric | Count |
|--------|-------|
| Total Ideas | 3 |
| Status: New | 1 |
| Status: Researched | 2 |
| Status: In Progress | 0 |
| Average Vision Alignment | 8.0 |
| Average ROI | 7.3 |
| Ideas in Archive | 0 |

---

## Notes

- This backlog serves as the single source of truth for all personal projects and initiatives
- Ideas must pass objective evaluation before significant time investment
- Regular review ensures alignment with evolving goals and market conditions
- Archive provides historical record of decision-making and rejected ideas
