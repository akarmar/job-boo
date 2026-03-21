"""Two-pass job-resume matching: keyword pre-filter + AI semantic scoring."""

from __future__ import annotations

from rich.console import Console
from rich.progress import track

from job_boo.ai.base import AIProvider
from job_boo.config import Config
from job_boo.models import Job, MatchResult, Resume

console = Console()

# Keyword pre-filter threshold — jobs below this skip the AI call
KEYWORD_THRESHOLD = 20


def keyword_score(resume: Resume, job: Job) -> float:
    """Fast keyword overlap score (0-100) using Jaccard similarity."""
    resume_skills = {s.lower().strip() for s in resume.skills}
    if not resume_skills:
        return 0

    job_text = (job.title + " " + job.description).lower()

    matched = 0
    for skill in resume_skills:
        # Check for the skill or common variations
        if skill in job_text:
            matched += 1
        elif len(skill) > 3 and any(
            variant in job_text
            for variant in [skill.replace(" ", "-"), skill.replace("-", " "), skill.replace(".", "")]
        ):
            matched += 1

    if not resume_skills:
        return 0
    return (matched / len(resume_skills)) * 100


def check_filters(job: Job, config: Config) -> tuple[bool, bool]:
    """Check location and sponsorship fit. Returns (location_fit, sponsorship_fit)."""
    # Location check
    location_fit = True
    if config.location.preference == "remote":
        location_fit = job.remote or "remote" in job.location.lower()
    elif config.location.city:
        location_fit = config.location.city.lower() in job.location.lower()

    # Sponsorship check
    sponsorship_fit = True
    if config.needs_sponsorship:
        desc_lower = job.description.lower()
        # If job explicitly says no sponsorship, it's not a fit
        no_sponsor_phrases = [
            "not able to sponsor",
            "unable to sponsor",
            "no sponsorship",
            "without sponsorship",
            "not sponsor",
            "must be authorized to work",
            "must be legally authorized",
            "no visa sponsorship",
        ]
        if any(phrase in desc_lower for phrase in no_sponsor_phrases):
            sponsorship_fit = False
        # If unknown, leave as True (benefit of doubt)
        if job.sponsorship_available is False:
            sponsorship_fit = False

    return location_fit, sponsorship_fit


def score_jobs(
    resume: Resume,
    jobs: list[Job],
    ai: AIProvider,
    config: Config,
) -> list[MatchResult]:
    """Score all jobs with two-pass approach: keyword filter then AI scoring."""
    results: list[MatchResult] = []

    # Pass 1: keyword pre-filter
    candidates: list[tuple[Job, float]] = []
    for job in jobs:
        ks = keyword_score(resume, job)
        if ks >= KEYWORD_THRESHOLD:
            candidates.append((job, ks))

    console.print(
        f"  Keyword filter: [green]{len(candidates)}[/green]/{len(jobs)} jobs "
        f"passed (>= {KEYWORD_THRESHOLD}% keyword match)"
    )

    if not candidates:
        console.print("[yellow]  No jobs passed the keyword filter. Try broader search terms.[/yellow]")
        return results

    # Pass 2: AI scoring
    console.print(f"  AI scoring {len(candidates)} candidates...")
    for job, ks in track(candidates, description="  Scoring"):
        try:
            match = ai.score_match(resume, job)
            match.keyword_score = ks
            # Weighted: 30% keyword, 70% AI
            match.final_score = (ks * 0.3) + (match.ai_score * 0.7)
            location_fit, sponsorship_fit = check_filters(job, config)
            match.location_fit = location_fit
            match.sponsorship_fit = sponsorship_fit
            results.append(match)
        except Exception as e:
            console.print(f"  [red]Error scoring {job.company} - {job.title}: {e}[/red]")

    # Sort by final score descending
    results.sort(key=lambda m: m.final_score, reverse=True)
    return results
