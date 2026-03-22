"""Two-pass job-resume matching: keyword pre-filter + AI semantic scoring."""

from __future__ import annotations

import re

from rich.console import Console
from rich.progress import track

from job_boo.ai.base import AIProvider
from job_boo.config import Config
from job_boo.models import Job, MatchResult, Resume

console = Console()

# Keyword pre-filter threshold — jobs below this skip the AI call
KEYWORD_THRESHOLD = 20


def _skill_in_text(skill: str, text: str) -> bool:
    """Check if skill appears in text, using word boundaries for short terms."""
    if len(skill) <= 3:
        return bool(re.search(r"\b" + re.escape(skill) + r"\b", text))
    return skill in text


def _trim_description(description: str, max_chars: int = 3000) -> str:
    """Truncate description, preferring requirements sections."""
    if len(description) <= max_chars:
        return description
    lower = description.lower()
    for marker in [
        "requirements",
        "qualifications",
        "what you'll need",
        "what we're looking for",
    ]:
        idx = lower.find(marker)
        if idx != -1:
            start = max(0, idx - 200)
            return description[start : start + max_chars]
    return description[:max_chars]


def keyword_score(resume: Resume, job: Job, config: Config | None = None) -> float:
    """Fast keyword overlap score (0-100) using Jaccard similarity."""
    resume_skills = {s.lower().strip() for s in resume.skills}
    if not resume_skills:
        return 0

    job_text = (job.title + " " + job.description).lower()

    matched = 0
    for skill in resume_skills:
        # Check for the skill or common variations
        if _skill_in_text(skill, job_text):
            matched += 1
        elif len(skill) > 3 and any(
            variant in job_text
            for variant in [
                skill.replace(" ", "-"),
                skill.replace("-", " "),
                skill.replace(".", ""),
            ]
        ):
            matched += 1

    base_score = (matched / len(resume_skills)) * 100

    # Title relevance boost: if job title contains the search terms, boost the score
    if config and config.job_title:
        title_lower = job.title.lower()
        search_terms = config.job_title.lower().split()
        # Also include keywords
        if config.keywords:
            for kw in config.keywords:
                search_terms.extend(kw.lower().split())
        # Remove common stop words
        stop_words = {
            "the",
            "a",
            "an",
            "of",
            "for",
            "and",
            "or",
            "in",
            "at",
            "with",
            "to",
            "senior",
            "junior",
            "lead",
            "staff",
            "principal",
            "sr",
            "jr",
        }
        search_terms = [t for t in search_terms if t not in stop_words]

        title_words = set(re.findall(r"\w+", title_lower))
        matching_terms = sum(1 for t in search_terms if t in title_words)

        if search_terms:
            title_relevance = matching_terms / len(set(search_terms))
            # Boost up to 15 points for perfect title match, penalize 10 for zero match
            if title_relevance > 0:
                base_score = min(100, base_score + title_relevance * 15)
            else:
                base_score = max(0, base_score - 10)

    return base_score


def is_company_blacklisted(job: Job, config: Config) -> bool:
    """Check if a job's company is on the blacklist."""
    blacklist = {c.lower() for c in config.companies.blacklist}
    return job.company.lower().strip() in blacklist


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
    """Score all jobs with two-pass approach: keyword filter then AI scoring.

    Returns ALL scored jobs (including below-threshold), sorted by score descending.
    Jobs that fail the keyword pre-filter get a keyword-only score with reasoning.
    """
    results: list[MatchResult] = []
    filtered_out: list[MatchResult] = []

    # Pass 1: keyword pre-filter
    candidates: list[tuple[Job, float]] = []
    for job in jobs:
        ks = keyword_score(resume, job, config)
        if ks >= KEYWORD_THRESHOLD:
            candidates.append((job, ks))
        else:
            # Track filtered jobs with reason
            location_fit, sponsorship_fit = check_filters(job, config)
            filtered_out.append(
                MatchResult(
                    job=job,
                    keyword_score=ks,
                    ai_score=0,
                    final_score=ks * 0.3,  # keyword-only weighted score
                    matched_skills=[],
                    missing_skills=[],
                    reasoning=f"Failed keyword filter ({ks:.0f}% < {KEYWORD_THRESHOLD}% threshold). "
                    "Resume skills not found in job description.",
                    location_fit=location_fit,
                    sponsorship_fit=sponsorship_fit,
                )
            )

    console.print(
        f"  Keyword filter: [green]{len(candidates)}[/green]/{len(jobs)} jobs "
        f"passed (>= {KEYWORD_THRESHOLD}% keyword match)"
    )

    if not candidates:
        console.print(
            "[yellow]  No jobs passed the keyword filter.[/yellow]\n"
            "  [dim]This means fewer than 20% of your resume skills appeared in any job description.\n"
            "  Try: change your job title, add more keywords, or add in-demand skills to your resume.[/dim]"
        )
        # Still return the filtered jobs so they can be saved to DB
        filtered_out.sort(key=lambda m: m.final_score, reverse=True)
        return filtered_out

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
            console.print(
                f"  [red]Error scoring {job.company} - {job.title}: {e}[/red]"
            )

    # Combine AI-scored results with keyword-filtered jobs
    all_results = results + filtered_out
    all_results.sort(key=lambda m: m.final_score, reverse=True)
    return all_results
