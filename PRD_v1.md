# PRD_v1.compact.md

## Status
- Version: 1.0
- Date: 2026-03-16
- Scope: v1
- Owner: Fatih Karahan
- Build mode: Python + `uv`, Codex-assisted development

## Product summary
Build a **personal student-job intake system** that:
- searches **LinkedIn public/guest jobs only**
- targets selected German cities
- focuses on student-compatible roles in a narrow role universe
- stores canonical data in **Supabase**
- syncs a **curated subset** into **Notion** for review and application workflow

This is not a Germany-wide, map-first, or multi-platform intelligence system.

## Problem
The earlier scraping project proved broad scraping was possible, but it became too complex for the actual need.

The real need is narrower:
- find student / working-student / internship-compatible jobs
- in fixed target cities
- for a small set of role families
- and review only the useful subset in Notion

v1 should optimize for:
- signal
- maintainability
- fast iteration
- usable review flow

## User
Primary user: **Fatih Karahan**

Relevant context:
- based in Germany
- MSc student
- already has working-student and internship experience
- wants roles aligned with data / analytics / ML
- wants Notion as the visual review layer

## Jobs-to-be-done
- Discover relevant student-compatible jobs.
- Separate jobs worth acting on from noisy keyword matches.
- Keep a canonical scraped dataset while pushing only selected jobs into a workable Notion layer.

## Goals
### Primary
1. Scrape targeted LinkedIn searches.
2. Identify likely student-compatible roles.
3. Classify jobs into the target role families.
4. Store raw + normalized data in Supabase.
5. Sync only selected jobs into Notion.
6. Keep the system easy to change.

### Secondary
1. Leave room for future StepStone/XING adapters.
2. Improve scoring later without rewriting the scraper.
3. Keep the project Codex-friendly.

### Non-goals
- StepStone support
- XING support
- company-site crawling
- Germany-wide expansion
- maps/geocoding
- broad analytics dashboards
- auto-application
- resume generation
- ML/LLM ranking as required runtime path

## v1 scope
### Platforms
- Included: LinkedIn guest/public jobs
- Excluded: StepStone, XING, company career sites

### Cities
- Oldenburg
- Bremen
- Hamburg
- Hanover
- Munich
- Stuttgart
- Berlin
- Frankfurt
- Dusseldorf
- Nuremberg
- Cologne
- Leipzig

### Included role families
- Data Engineering
- Analytics Engineering
- Analytics / BI
- ML / AI Engineering

### Excluded role families
- Frontend Engineering
- Backend Engineering
- Full-stack Engineering
- generic software engineering

### Job types
Primary target:
- working student / Werkstudent roles

Secondary target:
- internships
- student-assistant-like roles relevant to the included families

Rule: prefer **high precision over maximum recall**.

## Product principles
1. **Supabase is the source of truth.**
2. **Search and matching are separate concerns.**
3. **Student compatibility is a first-class signal.**
4. **Notion gets a subset, not everything.**
5. **Use deterministic rules before heavy AI.**
6. **Design for extension without paying the cost now.**

## Core assumptions
1. LinkedIn public jobs provide enough coverage for v1.
2. Student-job relevance can be approximated with deterministic signals.
3. Notion works well if the synced subset stays small.
4. City + role-family constraints produce useful volume.
5. Supabase + Notion is better than direct-to-Notion only.

## Success criteria
The system succeeds if:
- it regularly yields a small set of relevant jobs
- Notion stays usable and uncluttered
- role fit is better than raw keyword search
- updates do not require reworking the entire pipeline

Acceptance targets:
- LinkedIn search runs complete without crashing
- jobs upsert into Supabase with stable dedupe keys
- each job gets:
  - student-fit classification
  - role-family classification
  - shortlist decision
- only shortlisted jobs are eligible for Notion sync
- Notion sync is idempotent
- re-runs do not create duplicate Notion entries
- errors are logged clearly enough to debug changes

## Core workflows
### Workflow A: scrape and review
1. Run LinkedIn searches.
2. Store discovery and detail data in Supabase.
3. Run classification.
4. Compute shortlist status.
5. Sync shortlisted jobs to Notion.
6. Review/manage them in Notion.

### Workflow B: manage subsets in Notion
1. Keep one canonical job store in Supabase.
2. Create one main Notion review database.
3. Use linked views/pages for subsets like:
   - high priority
   - city groups
   - role-family groups
   - recent jobs
4. Avoid duplicating canonical job storage in Notion.

## Functional requirements
### FR-1 Search definitions
Support configurable LinkedIn searches built from:
- city
- role family
- keyword(s)
- optional stable filters
- German and English phrasing where useful

### FR-2 Discovery scraping
Collect at minimum:
- platform
- external job ID
- title
- company
- location
- job URL
- posted text/time if available
- rank in results
- source search definition

### FR-3 Detail scraping
Collect at minimum:
- canonical title
- company
- location
- description
- employment type
- seniority
- job function
- industries
- retrieval timestamp

### FR-4 Canonical persistence
Store:
- raw discovery records
- normalized job records
- search-definition metadata
- classifications
- Notion sync state

### FR-5 Deduplication
Use a stable canonical key:
- preferred: platform + external job ID
- fallback: normalized URL-derived identifier

### FR-6 Student-fit classification
Each job gets one of:
- `target_student_job`
- `possible_student_job`
- `not_student_job`

Use rule-based signals from:
- title
- description
- employment type
- seniority clues
- German and English student-related terms

### FR-7 Role-family classification
Each job gets one primary label:
- `data_engineering`
- `analytics_engineering`
- `analytics_bi`
- `ml_ai_engineering`
- `out_of_scope`

### FR-8 Shortlist decision
Shortlist depends on:
- student fit
- role-family fit
- location fit
- minimum metadata completeness

### FR-9 Notion sync
The system must:
- create new Notion items for new shortlisted jobs
- update existing ones
- avoid duplicates
- preserve manual workflow fields where appropriate

### FR-10 Observability
Log:
- search execution
- discovery counts
- detail counts
- classification counts
- shortlist counts
- Notion sync create/update/skip/error counts

## Recommended v1 matching logic
### Student-fit positive signals
- `werkstudent`
- `working student`
- `student assistant`
- `intern`
- `internship`
- `praktikum`
- `studentische hilfskraft`
- enrolled-student requirement
- university-study requirement

### Student-fit negative signals
- `senior`
- `lead`
- `principal`
- clearly full-time experienced roles without student terms

### Role-family signals
- Data Engineering: ETL/ELT, pipelines, Airflow, Spark, Kafka, warehouse, data platform
- Analytics Engineering: dbt, semantic layer, data modeling, quality tests, lineage
- Analytics / BI: dashboards, reporting, KPI, SQL analysis, Power BI, Tableau, Looker
- ML / AI Engineering: ML pipelines, training, evaluation, deployment, MLOps, GenAI, LLM

### Default shortlist rule
Eligible if:
- location is in target city set
- role family is in scope
- student fit is `target_student_job` or `possible_student_job`
- required title/description fields exist

Recommended stricter default:
- sync only `target_student_job`
- keep `possible_student_job` in Supabase only

## Data ownership
### Supabase owns
- canonical jobs
- raw platform data
- search definitions
- match results
- sync state
- run metadata

### Notion owns
- review workflow
- application status
- notes
- prioritization
- manual tags
- linked filtered views/pages

## Recommended Notion structure
One main shortlist database with fields such as:
- Job Title
- Company
- City
- Platform
- Role Family
- Student Fit
- Posted Text
- Job URL
- Shortlist Reason
- Priority
- Review Status
- Application Status
- Notes
- Source Search Name
- Synced At
- Canonical Job Key

Prefer **one database + linked views** over many databases.

## Constraints
### Technical
- Python-based
- `uv`
- reuse proven ideas from old repo:
  - Scrapy
  - Playwright / `scrapy-playwright`
  - config-driven searches
  - parser separation
- testable without every downstream service live all the time

### Product
- stay narrow
- avoid second-source integration in v1
- avoid over-engineering lifecycle logic before relevance quality is proven

## Risks and mitigations
- **Student-fit too noisy** → start strict; keep borderline jobs unsynced
- **LinkedIn coverage weak** → validate manually; add one more source later if needed
- **Notion clutter** → sync only shortlisted jobs; use one database + linked views
- **Scraper breakage** → keep parsing separate from classification; add smoke tests
- **Scope creep** → hold the v1 exclusions firmly

## Recommended stack
- Python 3.12+
- `uv`
- Scrapy
- Playwright
- `scrapy-playwright`
- Pydantic
- `python-dotenv`
- `httpx` or `requests`
- Supabase/Postgres client
- Notion SDK
- PyYAML
- pytest

Avoid in v1:
- Airflow
- Dagster
- Celery
- queues
- embeddings
- required LLM classification

## Milestones
1. search definitions + LinkedIn scraping
2. Supabase schema + dedupe
3. classification + shortlist
4. Notion sync
5. logging, smoke tests, runbook

## Final recommendation
Build the smallest useful version:
- LinkedIn only
- one canonical Supabase pipeline
- one curated Notion review database
- four role families
- strict student-fit rules
- no maps
- no multi-platform orchestration
- no auto-apply
