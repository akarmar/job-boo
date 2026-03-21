# Job Boo

**AI-powered job search, resume tailoring, and application automation.**\
Like a baby's toy — one button does everything.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

---

## What It Does

Job Boo automates the painful parts of job hunting:

| Step             | Manual                              | With Job Boo                                 |
| ---------------- | ----------------------------------- | -------------------------------------------- |
| **Find jobs**    | Open 5 tabs, scroll, search, repeat | `job-boo search` — queries 4+ sources        |
| **Evaluate**     | Read each JD, guess if you're a fit | AI scores every job against your resume      |
| **Tailor**       | Copy resume, tweak for each job     | `job-boo tailor 42` — AI rewrites it         |
| **Cover letter** | Stare at blank page for 20 min      | Auto-generated, personalized                 |
| **Apply**        | Fill forms, upload, repeat 200x     | `job-boo apply` — opens with materials ready |
| **Track**        | Spreadsheet you forget to update    | SQLite DB tracks every application           |

**Works without AI too.** No API key? Job Boo runs in fallback mode with keyword-only matching. Search, score, export — all work. AI just makes scoring and tailoring smarter.

## Features

### Core Pipeline

- **Multi-source job search** — Adzuna, The Muse, Remotive (free, no keys needed), SerpAPI/Google Jobs (paid, optional)
- **Paste any job URL** — Score a specific listing with `--url`
- **Two-pass scoring** — Fast keyword pre-filter, then AI semantic analysis (saves ~50% on API costs)
- **AI resume tailoring** — Rewrites your resume per job: reorders sections, mirrors keywords, adjusts summary
- **Cover letter generation** — Personalized per job, under 300 words, professional tone
- **Application tracking** — SQLite state machine: FOUND -> SCORED -> TAILORED -> APPLIED -> CLOSED
- **Batch apply** — Open multiple application URLs with tailored materials ready

### Smart Filters

- **Sponsorship detection** — Auto-detects "unable to sponsor" / "no visa sponsorship" in job descriptions
- **Location matching** — Filter by remote/hybrid/onsite and specific cities
- **Salary range** — Skip jobs below your minimum
- **Configurable threshold** — Default 60% match score, adjustable per run with `--threshold`
- **Company blacklist** — Skip companies you don't want to work for (coming soon)

### AI Providers

- **Claude** (Anthropic) — Default, best quality-to-cost ratio
- **OpenAI** (GPT-4o) — Alternative, works identically
- **Fallback mode** — No API key? Keyword-only matching still works for search and scoring
- **Configurable model** — Use any model (Haiku for cheap, Opus for best quality)

### Developer Experience

- **Interactive setup** — `job-boo init` wizard configures everything
- **AI setup wizard** — `job-boo setup-ai` tests your API connection live
- **Health check** — `job-boo doctor` diagnoses config, keys, resume, sources
- **Export** — CSV or JSON export for spreadsheet tracking
- **Reset** — Clean slate with `--jobs`, `--config`, `--output`, or `--everything`
- **Docker demo** — Try without installing anything

## Quick Start

### Install

```bash
git clone https://github.com/akarmar/job-boo.git
cd job-boo
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Configure

```bash
job-boo init          # Interactive setup wizard
job-boo setup-ai      # Configure + test AI provider
job-boo doctor        # Verify everything works
```

### Use

```bash
# Search for jobs and score them
job-boo search

# Score a specific job listing
job-boo search --url "https://boards.greenhouse.io/company/jobs/12345"

# Tailor your resume for a specific job (by ID from search results)
job-boo tailor 1

# Apply to a specific job
job-boo apply 1

# Full pipeline: search -> score -> tailor -> apply
job-boo all

# Lower the match threshold
job-boo all --threshold 50
```

### Track

```bash
job-boo jobs                  # List all tracked jobs with scores
job-boo jobs --min-score 80   # Filter by score
job-boo status                # Pipeline dashboard
job-boo export --format csv   # Export for spreadsheets
job-boo export --format json  # Export as JSON
```

## Configuration

Config lives at `~/.job-boo/config.yaml`. Created by `job-boo init`, or copy from [`config.example.yaml`](config.example.yaml).

```yaml
resume_path: ~/Documents/resume.pdf
job_title: "Senior Software Engineer"
keywords: ["python", "distributed systems"]

location:
  preference: remote # remote | hybrid | onsite
  city: "" # required if hybrid/onsite

needs_sponsorship: false

salary:
  min: 150000
  max: 250000
  currency: USD

match_threshold: 60 # 0-100, configurable per run

ai:
  provider: claude # claude | openai
  api_key: "" # or set JOB_BOO_AI_KEY env var
  model: "" # optional override

sources:
  serpapi:
    enabled: false # paid ($50/mo), optional
    api_key: ""
  adzuna:
    enabled: true # free tier (1000 req/month)
    app_id: "" # or set ADZUNA_APP_ID env var
    api_key: "" # or set ADZUNA_API_KEY env var
    country: us
  themuse:
    enabled: true # free, no key needed
  remotive:
    enabled: true # free, no key needed
```

### Environment Variables

All API keys can be set via env vars instead of config:

| Variable         | Purpose                  |
| ---------------- | ------------------------ |
| `JOB_BOO_AI_KEY` | Claude or OpenAI API key |
| `ADZUNA_APP_ID`  | Adzuna application ID    |
| `ADZUNA_API_KEY` | Adzuna API key           |
| `SERPAPI_KEY`    | SerpAPI key (optional)   |

## Job Sources

| Source    | Type   | Cost         | What it searches                 |
| --------- | ------ | ------------ | -------------------------------- |
| Adzuna    | API    | Free (1K/mo) | Aggregates Indeed, Monster, etc. |
| The Muse  | API    | Free, no key | Curated tech/startup jobs        |
| Remotive  | API    | Free, no key | Remote-only jobs                 |
| SerpAPI   | API    | $50/mo       | Google Jobs (all sources)        |
| URL paste | Direct | Free         | Any job listing URL              |

## How Scoring Works

```text
71 jobs found
    |
    v
[Pass 1: Keyword overlap — FREE, instant]
    |
    34 candidates (>= 20% keyword match)
    |
    v
[Pass 2: AI semantic scoring — costs tokens, accurate]
    |
    18 matches (>= 60% AI score)
    |
    v
Final score = (30% keyword) + (70% AI)
```

**Why two passes?** The keyword filter eliminates ~50% of irrelevant jobs before spending AI tokens. A full search of 50 jobs costs about $0.50-1.50 in API costs.

**Fallback mode:** Without an AI key, scoring uses keyword overlap only. Still useful — just less nuanced.

## Fallback Mode (No AI)

Job Boo works without any AI API key. Here's what changes:

| Feature              | With AI                          | Fallback (no key)             |
| -------------------- | -------------------------------- | ----------------------------- |
| Resume parsing       | AI extracts skills semantically  | Keyword regex matching        |
| Job scoring          | Semantic match (0-100)           | Keyword overlap (0-100)       |
| Resume tailoring     | AI rewrites per job              | Original resume + match notes |
| Cover letter         | AI generates personalized letter | Basic template                |
| Search               | Full functionality               | Full functionality            |
| Export               | Full functionality               | Full functionality            |
| Application tracking | Full functionality               | Full functionality            |

To upgrade from fallback to AI mode at any time:

```bash
job-boo setup-ai
```

## Docker

### Narrated Demo (no API keys needed)

```bash
./demo/run.sh --demo
```

### Interactive Environment

```bash
# With API keys
./demo/run.sh --env ~/.job-boo.env

# Mount your project directory
./demo/run.sh --env ~/.job-boo.env --mount ~/Documents
```

## All Commands

| Command             | Description                                       |
| ------------------- | ------------------------------------------------- |
| `job-boo init`      | Interactive configuration wizard                  |
| `job-boo setup-ai`  | Configure and test AI provider                    |
| `job-boo doctor`    | Diagnose configuration issues                     |
| `job-boo search`    | Search and score jobs against your resume         |
| `job-boo tailor ID` | Tailor resume + cover letter for a specific job   |
| `job-boo apply ID`  | Open application URL with tailored materials      |
| `job-boo all`       | Full pipeline: search -> score -> tailor -> apply |
| `job-boo jobs`      | List tracked jobs with scores and state           |
| `job-boo status`    | Pipeline dashboard with counts per state          |
| `job-boo export`    | Export jobs to CSV or JSON                        |
| `job-boo reset`     | Clear database, config, or output files           |

## Tech Stack

| Component     | Technology                |
| ------------- | ------------------------- |
| Language      | Python 3.11+              |
| CLI framework | Click                     |
| AI providers  | Anthropic SDK, OpenAI SDK |
| PDF parsing   | PyMuPDF (fitz)            |
| HTTP client   | httpx                     |
| Database      | SQLite (stdlib)           |
| Terminal UI   | Rich                      |
| HTML parsing  | BeautifulSoup4            |
| RSS parsing   | feedparser                |
| Config        | YAML (PyYAML)             |

## Project Structure

```text
src/job_boo/
├── cli.py              # Click CLI — all commands
├── config.py           # YAML config loading + env var fallbacks
├── models.py           # Dataclasses: Job, Resume, MatchResult, Application
├── ai/
│   ├── base.py         # AIProvider protocol
│   ├── claude.py       # Claude (Anthropic) implementation
│   ├── openai_provider.py  # OpenAI implementation
│   ├── fallback.py     # Keyword-only fallback (no API key needed)
│   └── prompts.py      # AI prompts for extraction, scoring, tailoring
├── resume/
│   └── parser.py       # PDF text extraction + AI skill parsing
├── search/
│   ├── serpapi.py       # Google Jobs via SerpAPI
│   ├── adzuna.py        # Adzuna job search API
│   ├── themuse.py       # The Muse API (free)
│   ├── remotive.py      # Remotive API (free, remote only)
│   └── url.py           # Parse any job listing URL
├── scoring/
│   └── matcher.py       # Two-pass scoring: keyword + AI
├── tailor/
│   └── tailorer.py      # Resume tailoring + cover letter generation
├── apply/
│   └── submitter.py     # Application submission + browser launch
└── storage/
    └── db.py            # SQLite job tracking + state machine
```

## Privacy

- All data stored locally (`~/.job-boo/`)
- No accounts, no cloud services, no telemetry
- API calls go only to your configured AI provider and job source APIs
- Your resume and API keys never leave your machine (except to APIs you explicitly configured)

## License

[MIT](LICENSE) — Use it, fork it, modify it, sell it. Just keep the copyright notice.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and how to add new job sources or AI providers.

## Acknowledgments

Inspired by [AIHawk](https://github.com/feder-cr/Jobs_Applier_AI_Agent_AIHawk), [JobSpy](https://github.com/speedyapply/JobSpy), and [Open Resume](https://github.com/xitanggg/open-resume).
