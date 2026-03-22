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

- **Multi-source job search** — Adzuna, The Muse, Remotive (free, no keys needed), JobSpy (LinkedIn/Indeed/Glassdoor), SerpAPI/Google Jobs (paid, optional)
- **Paste any job URL** — Score a specific listing with `--url`
- **Two-pass scoring** — Fast keyword pre-filter, then AI semantic analysis (saves ~50% on API costs)
- **AI resume tailoring** — Rewrites your resume per job: reorders sections, mirrors keywords, adjusts summary
- **Cover letter generation** — Personalized per job, under 300 words, professional tone
- **Interview prep** — AI-generated questions, talking points, and company research per job
- **Application tracking** — SQLite state machine: FOUND -> SCORED -> TAILORED -> APPLIED -> CLOSED
- **Batch apply** — Open multiple application URLs with tailored materials ready
- **Watch mode** — Scheduled searches with webhook notifications for new matches
- **Analytics** — Conversion funnel, skill gap trends, daily application activity
- **HTML Dashboard** — Interactive charts (Chart.js) with score distribution, company breakdown, skill gaps
- **Application history** — Search history by company or date range
- **Auto-cleanup** — Remove stale found/scored jobs older than 90 days
- **Resume caching** — Parsed resumes are cached by content hash; re-runs cost zero AI credits
- **Quick config updates** — Change any setting with `job-boo config key value`

### Smart Filters

- **Sponsorship detection** — Auto-detects "unable to sponsor" / "no visa sponsorship" in job descriptions
- **Location matching** — Filter by remote/hybrid/onsite and specific cities
- **Salary range** — Skip jobs below your minimum
- **Configurable threshold** — Default 60% match score, adjustable per run with `--threshold`
- **Company blacklist/whitelist** — Skip or target specific companies
- **Recency filter** — Only show jobs posted within N days (`--days`)

### Multi-Profile

- **Multiple search profiles** — Different resumes, titles, and keywords per job target
- Switch profiles with `--profile backend` or `--profile frontend`

### AI Providers

- **Claude** (Anthropic) — Default, best quality-to-cost ratio
- **OpenAI** (GPT-4o) — Alternative, works identically
- **Fallback mode** — No API key? Keyword-only matching still works for search and scoring
- **Configurable model** — Use any model (Haiku for cheap, Opus for best quality)

### Developer Experience

- **Interactive setup** — `job-boo init` wizard configures everything
- **AI setup wizard** — `job-boo setup-ai` tests your API connection live
- **Health check** — `job-boo doctor` diagnoses config, keys, resume, sources
- **Job notes** — Add notes to tracked jobs for your own reference
- **Export** — CSV or JSON export for spreadsheet tracking
- **Reset** — Clean slate with `--jobs`, `--config`, `--output`, or `--everything`
- **Docker demo** — Try without installing anything

## System Requirements

### Minimum
| Requirement | Minimum                                              |
| ----------- | ---------------------------------------------------- |
| Python      | 3.11+                                                |
| OS          | macOS 12+, Ubuntu 20.04+, Windows 10+ (WSL2 recommended) |
| RAM         | 256 MB (CLI only), 512 MB (with AI scoring)          |
| CPU         | Any x86_64 or ARM64                                  |
| Disk        | 50 MB (install) + ~1 MB per 1000 tracked jobs        |
| Network     | Required for job search and AI scoring               |

### Docker
| Requirement    | Minimum                          |
| -------------- | -------------------------------- |
| Docker         | 20.10+                           |
| Docker Compose | 2.0+ (optional, for demo)        |
| RAM            | 512 MB container limit           |
| Disk           | ~500 MB (image with dependencies) |

### Supported Platforms
- **macOS**: Intel and Apple Silicon (M1/M2/M3/M4)
- **Linux**: Ubuntu 20.04+, Debian 11+, Fedora 36+, RHEL 8+, Arch (any x86_64 or ARM64)
- **Windows**: Windows 10+ via WSL2 (native Windows not tested)
- **Docker**: Any platform with Docker 20.10+

### Python Dependencies
All dependencies are installed automatically via `pip install -e .`. No system-level packages required beyond Python 3.11+. PyMuPDF (PDF parsing) includes pre-built wheels for all major platforms.

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

# Update a single setting without re-running init
job-boo config job_title "Data Engineer"
job-boo config ai.provider openai
job-boo config match_threshold 70
job-boo config keywords "python, sql, spark"

# Pre-parse resumes to save AI credits on future runs
job-boo parse-resume                    # Parse resume from config
job-boo parse-resume ~/resumes/*.pdf    # Parse all your resume variants
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

## Installation

### From source (recommended)
```bash
git clone https://github.com/akarmar/job-boo.git
cd job-boo
python3 -m venv .venv
source .venv/bin/activate  # On Windows WSL: source .venv/bin/activate
pip install -e .
job-boo --version  # Verify installation
```

### Windows (WSL2)

Native Windows is not supported — use WSL2 (Windows Subsystem for Linux):

```powershell
# Step 1: Install WSL2 (run PowerShell as Administrator)
wsl --install

# Step 2: Restart your PC, then open "Ubuntu" from the Start menu

# Step 3: Inside the Ubuntu terminal, install Python
sudo apt update && sudo apt install -y python3 python3-pip python3-venv git

# Step 4: Clone and install job-boo
git clone https://github.com/akarmar/job-boo.git
cd job-boo
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Step 5: Verify
job-boo --version
```

**Common Windows issues:**
- **`python3: command not found`** — Run `sudo apt install python3` inside WSL
- **`pip install` fails with SSL errors** — Run `sudo apt install ca-certificates` first
- **Can't find your resume PDF** — Windows files are at `/mnt/c/Users/YourName/Documents/` inside WSL
- **`webbrowser.open` doesn't work** — Install `wslu`: `sudo apt install wslu` (enables `wslview` for opening URLs)
- **Permission denied on `~/.job-boo/`** — WSL home directory is separate from Windows home; use `~/` (e.g., `~/Documents/resume.pdf`)

### Docker (no Python required)
```bash
git clone https://github.com/akarmar/job-boo.git
cd job-boo
./demo/run.sh --demo        # Narrated demo (no API keys needed)
./demo/run.sh --env ~/.job-boo.env  # Interactive with your keys
```

### Verify installation
```bash
job-boo --version   # Should print: job-boo, version 0.1.0
job-boo doctor      # Diagnose configuration
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

### Getting Your AI API Key

Job Boo works without an AI key (fallback mode), but AI scoring and tailoring require one. Here's how to get a key:

#### Claude (Anthropic) — Recommended
1. Go to [console.anthropic.com](https://console.anthropic.com/)
2. Sign up or log in
3. Navigate to **Settings** → **API Keys** (or go directly to [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys))
4. Click **Create Key**, give it a name (e.g., "job-boo")
5. Copy the key — it starts with `sk-ant-...`
6. **Billing**: Add a payment method at **Settings** → **Billing**. New accounts get $5 free credit. A typical job search costs $0.50-$1.50.

#### OpenAI (GPT-4o) — Alternative
1. Go to [platform.openai.com](https://platform.openai.com/)
2. Sign up or log in
3. Navigate to **API Keys** at [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
4. Click **Create new secret key**
5. Copy the key — it starts with `sk-...`
6. **Billing**: Add a payment method at **Settings** → **Billing**. Pay-as-you-go, ~$0.003/job for scoring.

#### Configure the key
```bash
# Option 1: Interactive wizard (recommended)
job-boo setup-ai

# Option 2: Environment variable (more secure — key stays out of config file)
export JOB_BOO_AI_KEY="sk-ant-your-key-here"

# Option 3: Config file (less secure — key stored in plaintext)
# Edit ~/.job-boo/config.yaml:
#   ai:
#     provider: claude
#     api_key: "sk-ant-your-key-here"
```

**Security tip:** Use the environment variable method. Add `export JOB_BOO_AI_KEY="..."` to your `~/.bashrc` or `~/.zshrc` so it persists across sessions without being stored in the config file.

## Job Sources

| Source    | Type    | Cost         | What it searches                            |
| --------- | ------- | ------------ | ------------------------------------------- |
| JobSpy    | Scraper | Free         | LinkedIn, Indeed, Glassdoor, ZipRecruiter   |
| Adzuna    | API     | Free (1K/mo) | Aggregates Indeed, Monster, etc.            |
| The Muse  | API     | Free, no key | Curated tech/startup jobs                   |
| Remotive  | API     | Free, no key | Remote-only jobs                            |
| SerpAPI   | API     | $50/mo       | Google Jobs (all sources)                   |
| URL paste | Direct  | Free         | Any job listing URL                         |

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

| Command               | Description                                         |
| --------------------- | --------------------------------------------------- |
| `job-boo init`        | Interactive configuration wizard                    |
| `job-boo config`      | View or update a single config setting              |
| `job-boo setup-ai`    | Configure and test AI provider                      |
| `job-boo parse-resume` | Pre-parse and cache resumes to save AI credits     |
| `job-boo doctor`      | Diagnose configuration issues                       |
| `job-boo search`      | Search and score jobs against your resume           |
| `job-boo show ID`     | View full job details, scores, and AI reasoning     |
| `job-boo tailor ID`   | Tailor resume + cover letter for a specific job     |
| `job-boo prep ID`     | Generate AI interview prep questions + talking pts  |
| `job-boo apply ID`    | Open application URL with tailored materials        |
| `job-boo all`         | Full pipeline: search -> score -> tailor -> apply   |
| `job-boo jobs`        | List tracked jobs with scores and state             |
| `job-boo note ID`     | Add or view notes for a tracked job                 |
| `job-boo status`      | Pipeline dashboard with counts per state            |
| `job-boo analytics`   | Conversion funnel, skill trends, daily activity     |
| `job-boo dashboard`   | Generate HTML analytics dashboard with charts       |
| `job-boo history`     | Application history by company or date range        |
| `job-boo cleanup`     | Remove expired jobs (found/scored older than 90d)   |
| `job-boo watch`       | Scheduled search — find new jobs at an interval     |
| `job-boo export`      | Export jobs to CSV or JSON                          |
| `job-boo reset`       | Clear database, config, or output files             |

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
│   ├── jobspy_source.py # JobSpy: LinkedIn, Indeed, Glassdoor, ZipRecruiter
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
├── analytics/
│   └── dashboard.py     # HTML dashboard with Chart.js visualizations
└── storage/
    └── db.py            # SQLite job tracking + state machine + cleanup
```

## Privacy & Security

- All data stored locally (`~/.job-boo/`) with restricted file permissions (`0600`/`0700`)
- No accounts, no cloud services, no telemetry
- API calls go only to your configured AI provider and job source APIs
- Your resume text **is sent** to Claude/OpenAI APIs for scoring and tailoring (these providers may retain data up to 30 days per their API terms)
- Use fallback mode (no AI key) if you don't want resume data leaving your machine
- API keys can be stored via environment variables instead of config file for added security

### Terms of Service Notices

| Source                         | ToS Status      |
| ------------------------------ | --------------- |
| SerpAPI, Adzuna               | Compliant       |
| The Muse, Remotive            | Gray area       |
| JobSpy (LinkedIn/Indeed/etc.) | **Violates ToS** |

**JobSpy scrapes LinkedIn, Indeed, Glassdoor, and ZipRecruiter**, which all prohibit automated access. Using JobSpy may result in IP blocks, account suspension, or legal action. It is disabled by default and requires explicit opt-in. **Use at your own risk.**

### Rate Limiting & Costs

- AI scoring costs ~$0.003/job (~$0.50-$1.50 per search of 50 jobs)
- Watch mode consumes API quotas per cycle — intervals under 4 hours are warned
- Batch apply enforces a minimum 10-second delay between applications to avoid anti-bot triggers
- Free API tier limits: SerpAPI = 100/month, Adzuna = 1,000/month

### Token Cost Optimizations

Job Boo minimizes AI API spend with these strategies:

| Optimization                  | Savings       | How                                                    |
| ----------------------------- | ------------- | ------------------------------------------------------ |
| Two-pass scoring              | ~50% tokens   | Free keyword filter eliminates irrelevant jobs first   |
| Description trimming          | ~30% tokens   | Prioritizes requirements section, caps at 3000 chars   |
| Skills cap                    | ~10% tokens   | Sends top 30 skills instead of full list               |
| Resume text cap               | ~15% tokens   | Caps raw resume at 8000 chars for tailoring            |
| Word-boundary skill matching  | Better scores | Prevents false positives ("go" in "good"), fewer retries |

Cost estimates are shown before AI scoring runs. Use `--threshold` to raise the bar and score fewer jobs.

## Development

### Run Tests

```bash
pip install -e ".[test]"
pytest tests/                     # Run all 256 tests
pytest tests/ --cov=job_boo      # With coverage report
pytest tests/test_db.py -v       # Run a specific test file
```

### Code Quality

```bash
qlty check src/                   # Lint
qlty fmt src/                     # Format
semgrep scan --config auto src/   # Security scan
```

## License

[MIT](LICENSE) — Use it, fork it, modify it, sell it. Just keep the copyright notice.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and how to add new job sources or AI providers.

## Acknowledgments

Inspired by [AIHawk](https://github.com/feder-cr/Jobs_Applier_AI_Agent_AIHawk), [JobSpy](https://github.com/speedyapply/JobSpy), and [Open Resume](https://github.com/xitanggg/open-resume).
