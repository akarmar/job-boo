# Developer Notes

## Quick Reference

```bash
# Dev setup
python3 -m venv .venv && source .venv/bin/activate && pip install -e .

# Run
job-boo --help
job-boo doctor        # Check config health

# Quality checks
qlty fmt              # Auto-format
qlty check            # Lint
semgrep --config auto src/

# Test (no AI key needed)
job-boo search        # Falls back to keyword-only mode
```

## Project Layout

```text
src/job_boo/
├── cli.py              # All Click commands (entry point)
├── config.py           # YAML + env var config loading
├── models.py           # Dataclasses (Job, Resume, MatchResult, Application)
├── ai/                 # AI provider abstraction layer
│   ├── __init__.py     # get_provider() — factory with fallback
│   ├── base.py         # AIProvider protocol (interface)
│   ├── claude.py       # Anthropic Claude implementation
│   ├── openai_provider.py  # OpenAI implementation
│   ├── fallback.py     # Keyword-only fallback (no API key needed)
│   └── prompts.py      # System prompts for all AI operations
├── resume/parser.py    # PDF -> text -> structured Resume
├── search/             # Job source adapters
│   ├── __init__.py     # SearchOrchestrator (runs all sources, deduplicates)
│   ├── serpapi.py      # Google Jobs via SerpAPI ($50/mo)
│   ├── adzuna.py       # Adzuna (free 1K/mo)
│   ├── themuse.py      # The Muse (free, no key)
│   ├── remotive.py     # Remotive (free, remote jobs only)
│   └── url.py          # Parse any job URL (BeautifulSoup)
├── scoring/matcher.py  # Two-pass scoring: keyword -> AI
├── tailor/tailorer.py  # Resume + cover letter generation
├── apply/submitter.py  # Application submission (browser open)
└── storage/db.py       # SQLite state tracking
```

## Key Design Patterns

### AI Provider Abstraction

All AI operations go through the `AIProvider` protocol (`ai/base.py`). Three implementations:

| Provider | When used             | File                    |
| -------- | --------------------- | ----------------------- |
| Claude   | `ai.provider: claude` | `ai/claude.py`          |
| OpenAI   | `ai.provider: openai` | `ai/openai_provider.py` |
| Fallback | No API key configured | `ai/fallback.py`        |

`get_provider()` in `ai/__init__.py` selects automatically. **Fallback is the zero-config default.**

### Job Source Adapter Pattern

Each source in `search/` is a standalone function: `search_<source>(config: Config) -> list[Job]`

The orchestrator in `search/__init__.py`:

1. Checks which sources are enabled + have valid keys
2. Runs each sequentially (parallel planned)
3. Deduplicates by `(company, title)` — see `Job.dedup_key()`
4. Returns merged list

### State Machine

```text
FOUND → SCORED → TAILORED → READY → APPLIED → FOLLOWED_UP → CLOSED
                                  ↘ SKIPPED
```

States are stored in SQLite. Transitions via `db.update_state(id, new_state)`.

### Two-Pass Scoring

1. **Keyword pass** (free): Jaccard-like overlap of resume skills vs job description text. Threshold: 20%.
2. **AI pass** (costs tokens): Sends resume + job to LLM for semantic scoring. Only jobs that passed keyword filter.
3. **Final score**: `0.3 * keyword + 0.7 * AI`

In fallback mode, keyword score is used for both passes.

## Config Resolution Order

For API keys, checked in order:

1. Config file (`~/.job-boo/config.yaml`)
2. Environment variable (`JOB_BOO_AI_KEY`, `ADZUNA_API_KEY`, etc.)

The env var takes precedence if config value is empty.

## Adding New Features

### New CLI Command

Add to `cli.py`:

```python
@main.command()
@click.option("--flag", is_flag=True)
def mycommand(flag: bool) -> None:
    """Description shown in --help."""
    config = load_config()
    # ... implementation
```

### New Job Source

1. Create `search/newsite.py` with `search_newsite(config) -> list[Job]`
2. Add config dataclass in `config.py` if API keys needed
3. Register in `search/__init__.py`

### New AI Provider

1. Create `ai/newprovider.py` implementing all 4 protocol methods
2. Register in `ai/__init__.py:get_provider()`

## Database

SQLite at `~/.job-boo/jobs.db`. Schema is auto-created on first use. Schema definition is in `storage/db.py:SCHEMA`.

Key tables: `jobs` (single table with all fields — scoring, state, tailored paths).

To inspect manually:

```bash
sqlite3 ~/.job-boo/jobs.db
.schema
SELECT id, company, title, final_score, state FROM jobs ORDER BY final_score DESC LIMIT 10;
```

## Debugging

```bash
# Check what's configured
job-boo doctor

# See tracked jobs
job-boo jobs --min-score 0

# Export everything for inspection
job-boo export --format json -o /tmp/debug.json

# Reset and start fresh
job-boo reset --everything
```

## Security Notes

- API keys stored in plaintext in `~/.job-boo/config.yaml` — use env vars in production/CI
- Resume text is sent to AI provider APIs for parsing/scoring — understood and expected
- No telemetry, no analytics, no data collection
- Job search APIs receive your job title and location — standard search queries
- BeautifulSoup URL parsing uses a standard User-Agent header
- SQLite DB contains job descriptions (potentially large) — not encrypted
