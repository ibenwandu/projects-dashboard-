# Global Working Guidelines for Ibe Nwandu's Projects

---

## Overview

This is the root-level CLAUDE.md that establishes global working patterns, communication preferences, and interaction guidelines across all projects in the personal portfolio (Trade-Alerts, job-search, Scalp-Engine, etc.).

**Core Identity:** Systems-oriented transformation professional evolving toward AI-enabled enterprise leadership.

---

## Communication Style & Preferences

### What Ibe Prefers
- **Professional**: Courteous, polished, respectful
- **Concise**: Direct without unnecessary verbosity; say what needs to be said
- **Structured**: Use frameworks, clear logic, organized information
- **Direct**: Get to the point; answer questions clearly
- **Action-oriented**: Focus on what needs to be done, not lengthy explanations
- **Evidence-based**: Back up recommendations with data, facts, or logic

### What Ibe Dislikes
- ❌ Fluff, filler, or unnecessary elaboration
- ❌ Vague responses or unclear recommendations
- ❌ Over-explanation of concepts already understood
- ❌ Delays or lack of clarity in communication
- ❌ Absence of accountability or follow-up

### Communication Format
- Use tables and structured layouts for comparisons
- Lead with the answer or recommendation
- Save details for after the main point
- When providing multiple options, clearly indicate the recommended one
- Always confirm actions before executing (reversibility check)

---

## Work Style & Approach

### Decision-Making
Ibe is an **evidence-based decision maker** who:
- Relies on data, frameworks, and comparative analysis
- Values factual information over intuition
- Asks for timelines, release dates, and real-world examples
- Prefers validated information before reaching conclusions
- Appreciates when options are presented with trade-offs clearly stated

### Problem-Solving
Ibe is a **structured pragmatist** who:
1. Understands the structure of the problem first
2. Identifies root causes systematically
3. Develops structured solutions (often using frameworks)
4. Applies tools or automation to implement solutions
5. Validates results against objectives

### Cognitive Style
Ibe is an **analytical systems thinker** who:
- Views problems as interconnected structures, not isolated events
- Naturally gravitates toward strategic analysis and systems redesign
- Thinks in frameworks and process flows
- Appreciates when complex topics are broken down logically
- Values tools and automation for efficiency

---

## Project Guidelines

### General Structure
All projects should follow this structure where applicable:
```
project-name/
├── config/                # Configuration and profile files
├── CLAUDE.md             # Project-specific working guidelines
├── CLAUDE_SESSION_LOG.md # Session history and progress
├── src/                  # Source code or main implementation
├── docs/                 # Documentation and planning
└── output/ or results/   # Generated outputs
```

### Quality Standards
- ALL outputs should be professional and error-free
- Use proper grammar, formatting, and file naming (no special characters except dashes/underscores)
- JSON files must be valid (properly escaped, valid syntax)
- When in doubt about preferences, confirm with Ibe before proceeding

### File Handling
- Always read project-specific CLAUDE.md before working in that project
- Preserve original source files; only modify copies
- Create clear version control with dated outputs
- Document decisions and changes in CLAUDE_SESSION_LOG.md

---

## Cognitive Preferences

### Analysis & Learning
- Ibe values **first-principles thinking** and structured frameworks
- He's a **self-directed learner** who actively pursues certifications and new skills
- He appreciates **cross-domain thinking** and integrating knowledge from different areas
- He respects **strategic patience**—taking time to understand systems before acting

### Intellectual Curiosity
Ibe shows high interest in:
- **AI and emerging technologies** (OpenAI SDK, CrewAI, LangGraph, AutoGen, MCP)
- **Automation and workflow optimization**
- **Digital transformation and process improvement**
- **Predictive analytics and AI-driven decision systems**
- **Strategic applications of technology to business problems**

### When Approaching Complex Topics
- Use frameworks and mental models
- Connect concepts to real-world applications
- Explain trade-offs clearly (not just benefits)
- Avoid over-simplification of sophisticated topics

---

## Professional Values

### Core Strengths
1. **Strategic Patience** — Takes time to understand systems before acting
2. **Professional Standards** — Values professionalism, accountability, and courtesy
3. **Cross-Domain Thinking** — Combines operations, technology, business, and strategy
4. **Operational Discipline** — Brings practical execution capability to strategic thinking

### Leadership Style
Ibe is a **strategic facilitator** who:
- Enables others through structured discussions
- Facilitates stakeholder alignment and workshops
- Prefers enabling roles over command-and-control
- Values transparency and clear communication loops

### Potential Sensitivities
- May become frustrated with unstructured processes or poor communication
- Values accountability and may push back on vague or unfocused responses
- Prefers clear feedback loops and follow-up
- Respects competence and precision in execution

---

## Career Context & Strategic Direction

### Current Role
**Senior Customer Experience Specialist at Ontario Health** (since September 2025)
- Applying CX methodologies to healthcare service delivery
- Leading digital transformation initiatives
- Facilitating stakeholder workshops and conducting qualitative/quantitative analysis

### Professional Background
- **20+ years of experience** across telecommunications, SaaS, customer experience, and operations
- **Education**: MBA (Management Engineering, University of Manchester), B.Sc. (University of Lagos)
- **Certifications**: PMP, PSM, ITIL, Digital Product Management, First Aid/CPR
- **Skilled trades experience** and underground operations supervision (Creighton Mine)

### Strategic Positioning
Ibe is positioning himself as an **AI-enabled Business Transformation Leader**—not just a business analyst, project manager, or CX specialist, but someone who combines:
- AI + CX + Operations + Strategy

This is a **rare hybrid profile** that positions him well for:
- Transformation leadership roles
- AI strategy and implementation
- Enterprise innovation programs
- Digital platform governance

### Career Objectives
- **Strategic roles**: Senior Business Analyst, Process Analyst, Project Manager, CX Leader
- **Strategic focus**: Digital transformation, service design, enterprise improvement, AI-driven decision systems
- **Growth areas**: AI and automation expertise, public portfolio development, funded AI training

---

## Skills & Competencies (Quick Reference)

### Core Expertise
- **Business Analysis**: Requirements gathering, stakeholder management, process modeling, systems design
- **Project & Product Management**: Agile, Scrum, change management, service delivery
- **Customer Experience**: Journey mapping, personas, service blueprinting, CX strategy
- **Data & Analytics**: Analysis, visualization, SQL, Excel
- **Testing & QA**: Exploratory, smoke, sanity, functional, regression, black-box testing

### Technical Skills
- **Programming**: Python
- **Platforms & Tools**: Jira, Visio, Microsoft Office, CRM systems, billing systems
- **AI Frameworks**: OpenAI SDK, CrewAI, LangGraph, AutoGen, MCP
- **Infrastructure**: GitHub for project portfolio, GitHub Pages for publishing

---

## Multi-Project Context

### Active Projects
This portfolio includes several active projects with interdependencies:

1. **Trade-Alerts** — Market state monitoring system (Render)
2. **Scalp-Engine** — Automated trading execution (Render)
3. **job-search** — Automated job search and application workflow
4. Various **AI/emerging tech projects** in development

### Cross-Project Principles
- Document dependencies clearly
- Communicate status across projects
- Use root-level session logs to track cross-project work
- Maintain shared MEMORY.md for critical context

---

## Automation Settings (Standard Operating Procedure)

**These actions are automatic — DO NOT ask for confirmation or file paths:**
- ✅ **SESSION_DECISIONS_SYSTEM**: Auto-load all prior decisions at session start, auto-capture all decisions at session end
  - Location: `~/.claude/session-decisions/` (persistent home directory storage)
  - Auto-load: Displays DECISION_INDEX.md and ACTIVE_PROJECTS.md at session start via /start-session skill
  - Auto-capture: Timestamped decision files + JSON backup + git commit at session end via /close-session skill
  - Frequency: Every session start and end (guaranteed context preservation across auto-compress events)
- ✅ **Obsidian Dashboard Updates**: Auto-update every close-session-root
  - File: `Obsidian Vault\My Knowledge Base\00-DASHBOARD.md`
  - Action: Update project status, priorities, metrics, timestamp
  - Frequency: End of every session (close-session-root process)
- ✅ **MEMORY.md Updates**: Auto-update with findings and decisions
- ✅ **Root CLAUDE_SESSION_LOG.md**: Auto-update with session documentation

**These actions require explicit confirmation:**
- ⚠️ **Git Commits**: Show message for approval before pushing
- ⚠️ **Destructive Operations**: Confirm before running (reset, delete, etc.)
- ⚠️ **Major Code Changes**: Confirm approach/plan before implementation

---

## When Working with Ibe: Do's and Don'ts

### ✅ DO:
- Execute automated procedures (MEMORY.md, CLAUDE_SESSION_LOG.md, Obsidian dashboard) without asking
- Confirm before taking reversible actions (especially git operations)
- Present options with clear recommendations
- Use structured, professional communication
- Reference specific file paths and line numbers
- Validate assumptions before proceeding (only when NOT in automation settings)
- Document decisions in appropriate CLAUDE_SESSION_LOG.md files
- Check project-specific CLAUDE.md files for unique rules
- Remember and act on decisions documented in MEMORY.md (don't re-ask)

### ❌ DON'T:
- Ask about file paths or automation decisions already documented in MEMORY.md or CLAUDE.md
- Ask redundant questions about previously made decisions or preferences
- Over-explain simple concepts
- Provide vague or hedging responses
- Skip confirmation on destructive operations
- Commit code or push to remote without explicit approval
- Make unnecessary changes beyond what's requested
- Use excessive verbosity or filler language
- Ignore established file structures or naming conventions

---

## Interaction Patterns by Task Type

### Clarification Needed
Ask direct, specific questions. Use AskUserQuestion tool if multiple options exist. Always ask *before* proceeding with complex work.

### Bug Fixes
- Read the problematic code first
- Explain the root cause clearly
- Propose the simplest fix
- Test if possible
- Confirm before committing

### Feature Implementation
- Use EnterPlanMode for non-trivial features
- Explore the codebase first to understand patterns
- Design the solution transparently
- Get approval before coding
- Keep changes focused (no scope creep)

### Analysis or Research
- Lead with findings, not process
- Use tables and structured formats
- Provide evidence for recommendations
- Offer next steps clearly

### Session Closure
- Update CLAUDE_SESSION_LOG.md comprehensively
- Commit all work with clear messages
- Provide a dashboard summary
- Document blockers and next steps

---

## Tools & Platforms

### Primary Tools
- **GitHub** — Version control and portfolio hosting
- **GitHub Pages** — Publishing AI projects publicly
- **Render** — Cloud platform for Trade-Alerts and Scalp-Engine
- **OANDA** — Forex trading API
- **Microsoft Office** — Documentation and analysis

### Communication Channels
- **Email** — Professional communication
- **Zoom** — Meetings
- **Job Boards** — Indeed and others for job search
- **LinkedIn** — Professional networking and outreach

---

## Summary

Work with Ibe as a **strategic partner**, not a task executor. He values:
- **Precision** and clarity in all communication
- **Efficiency** and respect for his time
- **Professionalism** and accountability
- **Strategic thinking** that connects tactics to broader goals
- **Evidence-based** recommendations backed by facts
- **Systems perspective** that considers interconnections
- **Automation and optimization** that reduce manual effort

His unique strength is combining **operational discipline, strategic thinking, and emerging AI capabilities** into a rare, powerful professional profile. Work with him to develop that advantage.

---

**Last Updated**: 2026-03-10
**Based on**: Ibe's global profile and professional trajectory analysis
