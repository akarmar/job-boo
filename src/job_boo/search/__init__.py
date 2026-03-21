"""Job search orchestration across multiple sources."""

from __future__ import annotations

from rich.console import Console

from job_boo.config import Config
from job_boo.models import Job
from job_boo.search.adzuna import search_adzuna
from job_boo.search.remotive import search_remotive
from job_boo.search.serpapi import search_serpapi
from job_boo.search.themuse import search_themuse
from job_boo.search.url import parse_job_url

console = Console()


def search_all_sources(config: Config) -> list[Job]:
    """Search all enabled sources and return deduplicated jobs."""
    all_jobs: list[Job] = []
    seen: set[str] = set()

    sources = []
    if config.sources.serpapi.enabled and config.sources.serpapi.resolve_key():
        sources.append(("SerpAPI (Google Jobs)", lambda: search_serpapi(config)))
    if config.sources.adzuna.enabled and config.sources.adzuna.resolve_key():
        sources.append(("Adzuna", lambda: search_adzuna(config)))
    if config.sources.themuse:
        sources.append(("The Muse", lambda: search_themuse(config)))
    if config.sources.remotive:
        sources.append(("Remotive", lambda: search_remotive(config)))

    if not sources:
        console.print("[yellow]No job sources enabled or configured. Check your config.[/yellow]")
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

    return all_jobs
