# Contributing to Job Boo

Thanks for your interest in improving Job Boo! This guide covers development setup, code style, and how to add new features.

## Development Setup

```bash
# Clone and install in dev mode
git clone https://github.com/akarmar/job-boo.git
cd job-boo
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Verify
job-boo --help
```

### Running without AI (for development)

You don't need an API key to develop. The fallback provider (`ai/fallback.py`) handles all operations with keyword matching:

```bash
job-boo search    # Works in fallback mode
job-boo doctor    # Shows "no AI key" warning but no error
```

## Code Style

- **Type hints** on all function signatures
- **No redundant docblocks** — don't add `@return Type` when the return type hint is already there
- **No `declare(strict_types=1)`** equivalent patterns — trust the type system
- **Markdown tables** — align vertical bars for readability

### Linting and Formatting

```bash
# If you have qlty installed
qlty fmt    # Auto-format
qlty check  # Lint

# Semgrep (security scanning)
semgrep --config auto src/
```

## Architecture

### Adding a New Job Source

1. Create `src/job_boo/search/yoursite.py`
2. Implement a function matching the pattern:

```python
from job_boo.config import Config
from job_boo.models import Job

def search_yoursite(config: Config) -> list[Job]:
    """Search YourSite for jobs."""
    # Make HTTP requests, parse response, return Job objects
    return jobs
```

3. Add config to `config.py` (if it needs API keys)
4. Register it in `search/__init__.py`:

```python
if config.sources.yoursite.enabled:
    sources.append(("YourSite", lambda: search_yoursite(config)))
```

### Adding a New AI Provider

1. Create `src/job_boo/ai/yourprovider.py`
2. Implement all methods from `AIProvider` protocol in `ai/base.py`:
   - `extract_skills(resume_text) -> Resume`
   - `score_match(resume, job) -> MatchResult`
   - `tailor_resume(resume, job, match) -> str`
   - `generate_cover_letter(resume, job, match) -> str`
3. Register it in `ai/__init__.py`

### Database Schema

The SQLite schema is in `storage/db.py`. To add columns:

1. Add the column to the `SCHEMA` string
2. Add corresponding fields to the relevant dataclass in `models.py`
3. Update `upsert_job`, `get_jobs`, `row_to_job`, `row_to_match` methods

### State Machine

Jobs flow through states:

```text
FOUND -> SCORED -> TAILORED -> READY -> APPLIED -> FOLLOWED_UP -> CLOSED
                                    \-> SKIPPED
```

State transitions happen in `storage/db.py:update_state()`.

## Testing

```bash
# Run tests (when added)
python -m pytest tests/ -v

# Test a specific module
python -m pytest tests/test_scoring.py -v
```

### Testing Tips

- Use the fallback AI provider for tests — no API key needed
- Mock HTTP responses for job source tests
- The SQLite DB can use `:memory:` for test isolation

## Pull Request Guidelines

1. Keep PRs focused — one feature or fix per PR
1. Add type hints to all new functions
1. Test your changes (at minimum, verify `job-boo doctor` still passes)
1. Update the README if you add new commands or features
1. Don't break fallback mode — all core features should work without AI

## Ideas for Contribution

- [ ] Add JobSpy integration (LinkedIn, Indeed, Glassdoor scraping)
- [ ] ATS-optimized PDF resume output (currently text only)
- [ ] Auto-answer common application questions
- [ ] Company blacklist/whitelist
- [ ] Daily email digest of new matching jobs
- [ ] Interview prep question generator
- [ ] Salary normalization (hourly/monthly to annual)
- [ ] Job recency filter (posted in last N days)
- [ ] Browser extension for one-click scoring
