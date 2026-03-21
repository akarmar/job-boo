# Job Boo — Talk Track

## One-liner

AI-powered CLI that searches jobs, scores them against your resume, tailors your resume per listing, and helps you apply — in one pipeline.

## 2-Minute Pitch

Job hunting is broken. You spend 15-30 minutes per application, and you need 100-200 applications to land an offer. That's 50-100 hours of copy-paste-tweak-submit.

Job Boo automates the repetitive parts:
- **Searches** multiple job boards (Adzuna, The Muse, Remotive, Google Jobs)
- **Scores** every job against your actual resume using AI (Claude or GPT)
- **Tailors** your resume for each job — reordering, keyword-matching, rewriting summaries
- **Tracks** everything in a local SQLite database with a pipeline dashboard
- **Helps you apply** by opening jobs in your browser with tailored materials ready

You stay in control. It confirms before every application. All data stays local.

## Demo Commands

```bash
# Non-interactive narrated demo (Docker)
./demo/run.sh --demo

# Interactive environment
./demo/run.sh --env ~/.job-boo.env

# Native (no Docker)
pip install -e .
job-boo init
job-boo search
```

## Key Features to Highlight

| Feature              | Command                  | What it shows                              |
| -------------------- | ------------------------ | ------------------------------------------ |
| AI setup wizard      | `job-boo setup-ai`    | Tests connection, validates key             |
| Search + score       | `job-boo search`      | Multi-source search, two-pass scoring       |
| Score specific URL   | `job-boo search --url` | Paste any job listing, get a match score   |
| Resume tailoring     | `job-boo tailor 1`    | AI rewrites resume for specific job         |
| Full pipeline        | `job-boo all`          | End-to-end: search -> score -> tailor -> apply |
| Health check         | `job-boo doctor`       | Validates config, keys, resume, sources    |
| Export               | `job-boo export`       | CSV/JSON for spreadsheet tracking          |

## Talking Points

### vs. AIHawk (29K stars)
- AIHawk is LinkedIn-only, uses Selenium (fragile, gets banned)
- Job Boo uses official APIs (reliable, no bans)
- AIHawk auto-submits blindly; Job Boo scores first, confirms before applying

### vs. Manual Process
- 15 min/application -> ~30 seconds
- Resume tailored per job, not generic
- Never miss a "no sponsorship" red flag
- Track every application in one place

### Two-Pass Scoring (token efficiency)
- Pass 1: Free keyword overlap filters out 50%+ of irrelevant jobs
- Pass 2: AI scores only viable candidates
- Saves ~50% on API costs vs. scoring everything

### Privacy & Control
- All data local (SQLite + flat files)
- No accounts, no cloud services, no data sharing
- Your API keys, your data

## Where to Get API Keys

| Service  | URL                                    | Cost        |
| -------- | -------------------------------------- | ----------- |
| Claude   | console.anthropic.com/settings/keys    | Pay-as-you-go |
| OpenAI   | platform.openai.com/api-keys           | Pay-as-you-go |
| Adzuna   | developer.adzuna.com                   | Free (1K/mo) |
| SerpAPI  | serpapi.com                            | $50/mo       |

## FAQ

**Q: Does it auto-submit applications?**
A: It opens the application URL in your browser with tailored resume/cover letter ready. You click submit. Confirmation is on by default.

**Q: Which AI provider is better?**
A: Claude Sonnet is the default (best quality/cost ratio for this use case). GPT-4o works too. Configurable.

**Q: Can it scrape LinkedIn/Indeed directly?**
A: Not currently — those sites aggressively block bots. We use official APIs and aggregators instead. You can paste any job URL for scoring with `--url`.

**Q: How much does AI scoring cost?**
A: Roughly $0.01-0.03 per job scored (using Sonnet). A full search of 50 jobs costs about $0.50-1.50.

**Q: Can I use it without Docker?**
A: Yes. `pip install -e .` and `job-boo init`. Docker is just for the demo.
