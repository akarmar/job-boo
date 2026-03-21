# Notes

## Design Decisions

### Why keyword pre-filter before AI scoring?

AI scoring costs tokens ($0.01-0.03 per job). If you search 100 jobs, that's $1-3 per search. The keyword pre-filter eliminates ~50% of irrelevant jobs for free in milliseconds, cutting AI costs in half while barely affecting quality (a job with 0% keyword overlap is almost never a good match).

### Why not scrape LinkedIn/Indeed directly?

These sites aggressively block automated access — CAPTCHA, IP bans, account suspension. Selenium-based approaches (like AIHawk) work but are fragile and violate ToS. We use official APIs (Adzuna, The Muse, Remotive) and SerpAPI (which handles Google's anti-bot measures). Users can always paste a specific URL for scoring.

### Why fallback mode?

Not everyone wants to pay for AI API access. The fallback mode makes job-boo useful from the first install — search, keyword scoring, and export all work without any API key. Users can upgrade to AI scoring when ready.

### Why SQLite instead of flat files?

Application tracking needs deduplication, filtering, and state management. SQLite handles this natively with zero setup — no server, no migrations, just a file. The DB is at `~/.job-boo/jobs.db`.

### Why Click instead of Typer?

Click has fewer dependencies (no pydantic), is well-documented, and is the most battle-tested CLI framework in Python. Typer would work too, but doesn't add enough value to justify the extra dependency.

### Why not auto-submit applications?

We open the application URL in the browser instead of submitting forms because:

1. ATS form structures vary wildly and change frequently
2. Many applications require login, CAPTCHA, or multi-step flows
3. Auto-submit without review leads to embarrassing mistakes
4. Opening the browser with tailored resume/cover letter ready is 90% of the time savings

## Scoring Algorithm

### Two-Pass Architecture

```text
Pass 1: Keyword Score (free, instant)
  - Extract skills from resume
  - Check each skill against job description text
  - Handle variations: "Node.js" vs "NodeJS" vs "Node"
  - Score = (matched / total_resume_skills) * 100
  - Threshold: 20% (very generous, just filters total mismatches)

Pass 2: AI Score (costs tokens, semantic)
  - Sends resume skills + job description to AI
  - AI considers: direct matches, transferable skills, experience level, domain fit
  - Returns: score (0-100), matched skills, missing skills, reasoning
  - Only runs on jobs that passed Pass 1

Final Score = (30% * keyword_score) + (70% * ai_score)
```

### Why 30/70 split?

Keyword matching catches obvious fits but misses transferable skills (React -> Vue.js) and domain knowledge. AI scoring catches semantic matches but can sometimes hallucinate. The 30/70 split means keyword overlap still matters but AI drives the final ranking.

### Sponsorship Detection

Pattern-matches common phrases in job descriptions:

- "unable to sponsor" / "not able to sponsor"
- "no visa sponsorship"
- "must be authorized to work"
- "must be legally authorized"

If found and user `needs_sponsorship: true`, the job gets a VISA flag (not auto-rejected — just flagged).

## API Cost Estimates

| Operation               | Claude Sonnet | GPT-4o      |
| ----------------------- | ------------- | ----------- |
| Resume parsing          | ~$0.01        | ~$0.01      |
| Score 1 job             | ~$0.01-0.03   | ~$0.01-0.03 |
| Tailor resume           | ~$0.03-0.05   | ~$0.03-0.05 |
| Cover letter            | ~$0.01-0.02   | ~$0.01-0.02 |
| Full pipeline (50 jobs) | ~$0.50-1.50   | ~$0.50-1.50 |

Use `claude-haiku-4-5-20251001` or `gpt-4o-mini` for cheaper scoring at slightly lower quality.

## Known Limitations

1. **No LinkedIn/Indeed direct scraping** — Use SerpAPI or paste URLs
2. **Text-only resume output** — Tailored resumes are plain text, not formatted PDF (yet)
3. **No auto-form-filling** — Opens browser, you click submit
4. **Keyword fallback is basic** — Without AI, scoring misses transferable skills
5. **No multi-language support** — English job descriptions only for now
6. **Rate limiting is basic** — Sequential requests with configurable delay, not smart backoff
