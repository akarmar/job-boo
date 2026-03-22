"""Job search orchestration across multiple sources."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from rich.console import Console

from job_boo.config import Config
from job_boo.models import Job
from job_boo.search.adzuna import search_adzuna
from job_boo.search.himalayas import search_himalayas
from job_boo.search.jobicy import search_jobicy
from job_boo.search.jobspy_source import search_jobspy
from job_boo.search.jsearch import search_jsearch
from job_boo.search.remotive import search_remotive
from job_boo.search.serpapi import search_serpapi
from job_boo.search.themuse import search_themuse
from job_boo.search.url import parse_job_url  # noqa: F401 — re-exported for CLI
from job_boo.search.usajobs import search_usajobs

console = Console()


def parse_posted_date(date_str: str) -> datetime | None:
    """Best-effort parse of posted_date strings (ISO dates and relative like '3 days ago')."""
    if not date_str:
        return None

    # Try ISO format variants
    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
    ):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue

    # Try relative date patterns like "3 days ago", "1 week ago", "2 months ago"
    relative = re.match(
        r"(\d+)\s+(day|week|month|hour|minute)s?\s+ago", date_str.strip().lower()
    )
    if relative:
        amount = int(relative.group(1))
        unit = relative.group(2)
        now = datetime.now()
        if unit == "day":
            return now - timedelta(days=amount)
        elif unit == "week":
            return now - timedelta(weeks=amount)
        elif unit == "month":
            return now - timedelta(days=amount * 30)
        elif unit == "hour":
            return now - timedelta(hours=amount)
        elif unit == "minute":
            return now - timedelta(minutes=amount)

    # "today" / "yesterday"
    lower = date_str.strip().lower()
    if lower == "today":
        return datetime.now()
    if lower == "yesterday":
        return datetime.now() - timedelta(days=1)

    return None


def filter_by_recency(jobs: list[Job], max_days: int) -> list[Job]:
    """Filter jobs to only include those posted within max_days. Jobs with unparseable dates are kept."""
    cutoff = datetime.now() - timedelta(days=max_days)
    filtered: list[Job] = []
    for job in jobs:
        posted = parse_posted_date(job.posted_date)
        if posted is None or posted >= cutoff:
            filtered.append(job)
    return filtered


def filter_by_company(jobs: list[Job], config: Config) -> list[Job]:
    """Filter jobs by company blacklist/whitelist. Case-insensitive matching."""
    blacklist = {c.lower() for c in config.companies.blacklist}
    whitelist = {c.lower() for c in config.companies.whitelist}

    filtered: list[Job] = []
    for job in jobs:
        company_lower = (job.company or "").lower().strip()
        if company_lower in blacklist:
            continue
        if whitelist and company_lower not in whitelist:
            continue
        filtered.append(job)

    removed = len(jobs) - len(filtered)
    if removed > 0:
        console.print(f"  Company filter: removed [yellow]{removed}[/yellow] jobs")

    return filtered


_STOP_WORDS = frozenset(
    {"the", "a", "an", "of", "for", "and", "or", "in", "at", "with", "to"}
)


def _tokenize(text: str) -> set[str]:
    """Split text into lowercase words, excluding stop words."""
    return {w for w in re.findall(r"[a-z]+", text.lower()) if w not in _STOP_WORDS}


def filter_by_title_relevance(jobs: list[Job], config: Config) -> list[Job]:
    """Remove jobs whose titles share zero meaningful terms with the search query."""
    relevant_terms: set[str] = _tokenize(config.job_title)
    for kw in config.keywords:
        relevant_terms |= _tokenize(kw)

    if not relevant_terms:
        return jobs

    filtered: list[Job] = []
    for job in jobs:
        title_terms = _tokenize(job.title or "")
        if title_terms & relevant_terms:
            filtered.append(job)

    removed = len(jobs) - len(filtered)
    if removed > 0:
        console.print(
            f"  Title relevance filter: removed [yellow]{removed}/{len(jobs)}[/yellow]"
            f" jobs (titles unrelated to [cyan]{config.job_title!r}[/cyan])"
        )

    return filtered


def search_all_sources(config: Config, max_days: int | None = None) -> list[Job]:
    """Search all enabled sources and return deduplicated, filtered jobs."""
    all_jobs: list[Job] = []
    seen: set[str] = set()

    sources = []
    if config.sources.serpapi.enabled and config.sources.serpapi.resolve_key():
        sources.append(("SerpAPI (Google Jobs)", lambda: search_serpapi(config)))
    if config.sources.adzuna.enabled and config.sources.adzuna.resolve_key():
        sources.append(("Adzuna", lambda: search_adzuna(config)))
    if config.sources.jobspy.enabled:
        sites_label = ", ".join(config.sources.jobspy.sites)
        sources.append((f"JobSpy ({sites_label})", lambda: search_jobspy(config)))
    if config.sources.jsearch.enabled and config.sources.jsearch.resolve_key():
        sources.append(("JSearch (Google Jobs)", lambda: search_jsearch(config)))
    if config.sources.usajobs.enabled and config.sources.usajobs.resolve_key():
        sources.append(("USAJobs (Federal)", lambda: search_usajobs(config)))
    if config.sources.themuse:
        sources.append(("The Muse", lambda: search_themuse(config)))
    if config.sources.remotive:
        sources.append(("Remotive", lambda: search_remotive(config)))
    if config.sources.himalayas:
        sources.append(("Himalayas", lambda: search_himalayas(config)))
    if config.sources.jobicy:
        sources.append(("Jobicy", lambda: search_jobicy(config)))

    if not sources:
        console.print(
            "[yellow]No job sources enabled or configured. Check your config.[/yellow]"
        )
        return []

    for name, search_fn in sources:
        try:
            console.print(f"  Searching [cyan]{name}[/cyan]...", end=" ")
            jobs = search_fn()
            new_count = 0
            for job in jobs:
                key = job.dedup_key()
                if key not in seen:
                    seen.add(key)
                    all_jobs.append(job)
                    new_count += 1
            console.print(f"[green]{new_count} new jobs[/green] ({len(jobs)} total)")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    # Apply company filters
    all_jobs = filter_by_company(all_jobs, config)

    # Apply recency filter
    if max_days is not None:
        before = len(all_jobs)
        all_jobs = filter_by_recency(all_jobs, max_days)
        removed = before - len(all_jobs)
        if removed > 0:
            console.print(
                f"  Recency filter ({max_days}d): removed [yellow]{removed}[/yellow] jobs"
            )

    # Apply title relevance filter
    all_jobs = filter_by_title_relevance(all_jobs, config)

    return all_jobs
