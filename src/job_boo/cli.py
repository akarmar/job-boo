"""CLI entry point for job-boo."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.table import Table

from job_boo.config import (
    CONFIG_DIR,
    CONFIG_PATH,
    load_config,
    ensure_dirs,
    apply_profile,
)
from job_boo.models import JobState, MatchResult

console = Console()


@click.group()
@click.version_option(package_name="job-boo")
def main() -> None:
    """Job Boo — AI-powered job search, resume tailoring, and application automation."""


@main.command()
def init() -> None:
    """Interactive setup — creates config file."""
    if CONFIG_PATH.exists():
        if not click.confirm(f"Config already exists at {CONFIG_PATH}. Overwrite?"):
            return

    config: dict = {}
    console.print("\n[bold]Job Boo Setup[/bold]\n")

    config["resume_path"] = click.prompt("Path to your resume PDF", type=str)
    config["job_title"] = click.prompt(
        "Target job title (e.g., Senior Software Engineer)"
    )
    keywords = click.prompt(
        "Additional search keywords (comma-separated, or blank)", default=""
    )
    config["keywords"] = [k.strip() for k in keywords.split(",") if k.strip()]

    console.print("\n[bold]Location[/bold]")
    pref = click.prompt(
        "Preference",
        type=click.Choice(["remote", "hybrid", "onsite"]),
        default="remote",
    )
    city = ""
    if pref != "remote":
        city = click.prompt("City")
    config["location"] = {"preference": pref, "city": city}

    config["needs_sponsorship"] = click.confirm(
        "Do you need visa sponsorship?", default=False
    )

    console.print("\n[bold]Salary (USD, enter 0 to skip)[/bold]")
    config["salary"] = {
        "min": click.prompt("Minimum salary", type=int, default=0),
        "max": click.prompt("Maximum salary", type=int, default=0),
        "currency": "USD",
    }

    config["match_threshold"] = click.prompt(
        "Minimum match score (0-100)", type=int, default=60
    )

    console.print("\n[bold]AI Provider[/bold]")
    provider = click.prompt(
        "Provider", type=click.Choice(["claude", "openai"]), default="claude"
    )
    api_key = click.prompt(
        "API key (or set JOB_BOO_AI_KEY env var)", default="", hide_input=True
    )
    config["ai"] = {"provider": provider, "api_key": api_key, "model": ""}

    console.print("\n[bold]Job Sources[/bold]")
    config["sources"] = {
        "serpapi": {"enabled": False, "api_key": ""},
        "adzuna": {"enabled": False, "app_id": "", "api_key": "", "country": "us"},
        "themuse": {"enabled": True},
        "remotive": {"enabled": True},
    }

    if click.confirm("Enable SerpAPI (Google Jobs, paid)?", default=False):
        config["sources"]["serpapi"]["enabled"] = True
        config["sources"]["serpapi"]["api_key"] = click.prompt(
            "SerpAPI key", default=""
        )

    if click.confirm("Enable Adzuna (free tier, 1000 req/month)?", default=True):
        config["sources"]["adzuna"]["enabled"] = True
        config["sources"]["adzuna"]["app_id"] = click.prompt(
            "Adzuna App ID", default=""
        )
        config["sources"]["adzuna"]["api_key"] = click.prompt(
            "Adzuna API key", default=""
        )

    config["output_dir"] = str(CONFIG_DIR / "output")
    config["apply"] = {
        "confirm_before_submit": True,
        "include_cover_letter": True,
        "delay_between_applications": 5,
    }

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if sys.platform != "win32":
        os.chmod(
            CONFIG_DIR, 0o700
        )  # nosemgrep: insecure-file-permissions — owner-only dir for secrets
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    if sys.platform != "win32":
        os.chmod(CONFIG_PATH, 0o600)

    console.print(f"\n[green]Config saved to {CONFIG_PATH}[/green]")
    console.print("Run [bold]job-boo search[/bold] to find matching jobs.")

    from rich.panel import Panel

    warning = (
        "[bold yellow]IMPORTANT NOTICES[/bold yellow]\n\n"
        "1. [bold]PRIVACY:[/bold] Your resume will be sent to external AI services (Anthropic/OpenAI) "
        "for skill extraction and job matching. These providers may retain data for up to 30 days. "
        "Run without an AI key for keyword-only fallback mode.\n\n"
        "2. [bold]API KEYS:[/bold] Keys stored in ~/.job-boo/config.yaml are protected with restricted "
        "file permissions (owner-only). For extra security, use environment variables instead.\n\n"
        "3. [bold]TERMS OF SERVICE:[/bold] Some job sources may prohibit automated access. "
        "Scraping LinkedIn, Indeed, Glassdoor, or ZipRecruiter (via JobSpy) violates their ToS "
        "and may result in account suspension, IP blocks, or legal action. Use at your own risk.\n\n"
        "4. [bold]COSTS:[/bold] AI-powered features make API calls that cost money. "
        "A typical search-and-score run costs ~$0.50-$1.50 depending on job count."
    )
    console.print(
        Panel(
            warning, title="[bold red]Security & Privacy[/bold red]", border_style="red"
        )
    )


@main.command(name="setup-ai")
def setup_ai() -> None:
    """Configure and validate AI provider (Claude or OpenAI)."""
    config = load_config()
    console.print("\n[bold]AI Provider Setup[/bold]\n")

    # Show current state
    current_key = config.ai.resolve_key()
    has_key = bool(current_key)
    masked = (
        f"...{current_key[-6:]}"
        if len(current_key) > 6
        else ("(set)" if has_key else "(not set)")
    )

    console.print(f"  Current provider:  [cyan]{config.ai.provider}[/cyan]")
    console.print(f"  Current model:     [cyan]{config.ai.resolve_model()}[/cyan]")
    console.print(f"  API key:           [cyan]{masked}[/cyan]")
    env_key = os.environ.get("JOB_BOO_AI_KEY", "")
    if env_key:
        console.print("  Env JOB_BOO_AI_KEY: [green]set[/green]")
    console.print()

    # Choose provider
    provider = click.prompt(
        "AI provider",
        type=click.Choice(["claude", "openai"]),
        default=config.ai.provider,
    )

    # Provider-specific guidance
    if provider == "claude":
        console.print(
            "\n  [dim]Get your API key at: https://console.anthropic.com/settings/keys[/dim]"
        )
        console.print(
            "  [dim]Free tier: limited requests. Pay-as-you-go recommended.[/dim]"
        )
        models = [
            "claude-sonnet-4-20250514",
            "claude-haiku-4-5-20251001",
            "claude-opus-4-20250514",
        ]
        default_model = "claude-sonnet-4-20250514"
    else:
        console.print(
            "\n  [dim]Get your API key at: https://platform.openai.com/api-keys[/dim]"
        )
        console.print("  [dim]Free tier: $5 credit for new accounts.[/dim]")
        models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]
        default_model = "gpt-4o"

    # API key
    console.print()
    key_source = click.prompt(
        "How to provide API key",
        type=click.Choice(["enter_now", "env_var", "keep_current"]),
        default="keep_current" if has_key else "enter_now",
    )

    api_key = config.ai.api_key
    if key_source == "enter_now":
        api_key = click.prompt("API key", hide_input=True)
    elif key_source == "env_var":
        console.print("\n  Add this to your shell profile (~/.zshrc or ~/.bashrc):")
        console.print('  [bold]export JOB_BOO_AI_KEY="your-key-here"[/bold]')
        console.print(
            "  Then restart your terminal or run: [bold]source ~/.zshrc[/bold]"
        )
        api_key = ""  # clear from config, rely on env

    # Model selection
    console.print()
    model = click.prompt(
        "Model",
        type=click.Choice(models + ["custom"]),
        default=config.ai.model if config.ai.model in models else default_model,
    )
    if model == "custom":
        model = click.prompt("Custom model ID")

    # Test connection
    test_key = api_key or os.environ.get("JOB_BOO_AI_KEY", "")
    if test_key:
        console.print("\n[bold]Testing connection...[/bold]")
        try:
            if provider == "claude":
                import anthropic

                client = anthropic.Anthropic(api_key=test_key)
                resp = client.messages.create(
                    model=model,
                    max_tokens=50,
                    messages=[{"role": "user", "content": "Reply with only: OK"}],
                )
                reply = resp.content[0].text.strip()
                tokens_in = resp.usage.input_tokens
                tokens_out = resp.usage.output_tokens
            else:
                import openai as oai

                client = oai.OpenAI(api_key=test_key)
                resp = client.chat.completions.create(
                    model=model,
                    max_tokens=50,
                    messages=[{"role": "user", "content": "Reply with only: OK"}],
                )
                reply = (resp.choices[0].message.content or "").strip()
                tokens_in = resp.usage.prompt_tokens if resp.usage else 0
                tokens_out = resp.usage.completion_tokens if resp.usage else 0

            console.print(f"  Response: [green]{reply}[/green]")
            console.print(f"  Tokens used: {tokens_in} in / {tokens_out} out")
            console.print("  [bold green]Connection successful![/bold green]")
        except Exception as e:
            console.print(f"  [bold red]Connection failed: {e}[/bold red]")
            if not click.confirm("Save config anyway?", default=False):
                return
    else:
        console.print(
            "\n[yellow]No API key available to test. Set one via env var or re-run setup.[/yellow]"
        )

    # Save to config
    _update_config_section(
        "ai",
        {
            "provider": provider,
            "api_key": api_key,
            "model": model,
        },
    )
    console.print(f"\n[green]AI config saved to {CONFIG_PATH}[/green]")


@main.command()
def doctor() -> None:
    """Diagnose configuration and connectivity issues."""
    config = load_config()
    issues: list[str] = []
    warnings: list[str] = []

    console.print("\n[bold]Job Boo Doctor[/bold]\n")

    # Config file
    if CONFIG_PATH.exists():
        console.print(f"  Config file:       [green]OK[/green] ({CONFIG_PATH})")
    else:
        console.print("  Config file:       [red]MISSING[/red]")
        issues.append("Run 'job-boo init' to create config")

    # Resume
    if config.resume_path:
        resume_path = Path(config.resume_path).expanduser()
        if resume_path.exists():
            size_kb = resume_path.stat().st_size / 1024
            console.print(f"  Resume PDF:        [green]OK[/green] ({size_kb:.0f} KB)")
        else:
            console.print(
                f"  Resume PDF:        [red]NOT FOUND[/red] ({config.resume_path})"
            )
            issues.append(f"Resume file not found: {config.resume_path}")
    else:
        console.print("  Resume PDF:        [red]NOT SET[/red]")
        issues.append("Set resume_path in config")

    # AI provider
    ai_key = config.ai.resolve_key()
    if ai_key:
        console.print(
            f"  AI provider:       [green]{config.ai.provider}[/green] (model: {config.ai.resolve_model()})"
        )
        console.print(f"  AI key:            [green]...{ai_key[-6:]}[/green]")
    else:
        console.print("  AI provider:       [red]NO KEY[/red]")
        issues.append("Run 'job-boo setup-ai' to configure AI provider")

    # Job sources
    active_sources = []
    if config.sources.serpapi.enabled and config.sources.serpapi.resolve_key():
        active_sources.append("SerpAPI")
    if config.sources.adzuna.enabled and config.sources.adzuna.resolve_key():
        active_sources.append("Adzuna")
    if config.sources.themuse:
        active_sources.append("The Muse")
    if config.sources.remotive:
        active_sources.append("Remotive")

    if active_sources:
        console.print(
            f"  Job sources:       [green]{', '.join(active_sources)}[/green]"
        )
    else:
        console.print("  Job sources:       [red]NONE[/red]")
        issues.append("No job sources configured")

    # Free sources without keys
    if not config.sources.adzuna.resolve_key() and config.sources.adzuna.enabled:
        warnings.append(
            "Adzuna enabled but no API key — get a free key at developer.adzuna.com"
        )

    # Search criteria
    if config.job_title:
        console.print(f"  Job title:         [green]{config.job_title}[/green]")
    else:
        console.print("  Job title:         [yellow]NOT SET[/yellow]")
        warnings.append("Set job_title in config for better search results")

    console.print(
        f"  Location:          {config.location.preference}"
        + (f" ({config.location.city})" if config.location.city else "")
    )
    console.print(
        f"  Sponsorship:       {'needed' if config.needs_sponsorship else 'not needed'}"
    )
    console.print(f"  Match threshold:   {config.match_threshold}%")

    # Output dir
    out_dir = Path(config.output_dir).expanduser()
    if out_dir.exists():
        console.print(f"  Output dir:        [green]OK[/green] ({out_dir})")
    else:
        console.print(
            f"  Output dir:        [yellow]will be created[/yellow] ({out_dir})"
        )

    # DB
    from job_boo.config import DB_PATH

    if DB_PATH.exists():
        size_kb = DB_PATH.stat().st_size / 1024
        from job_boo.storage.db import JobDB

        with JobDB() as db:
            stats = db.get_stats()
        total = sum(stats.values())
        console.print(
            f"  Database:          [green]{total} jobs tracked[/green] ({size_kb:.0f} KB)"
        )
    else:
        console.print("  Database:          [dim]not yet created[/dim]")

    # Summary
    console.print()
    if issues:
        console.print("[bold red]Issues to fix:[/bold red]")
        for issue in issues:
            console.print(f"  [red]  {issue}[/red]")
    if warnings:
        console.print("[bold yellow]Warnings:[/bold yellow]")
        for warning in warnings:
            console.print(f"  [yellow]  {warning}[/yellow]")
    if not issues and not warnings:
        console.print(
            "[bold green]All good! Run 'job-boo search' to get started.[/bold green]"
        )
    elif not issues:
        console.print(
            "\n[green]No blocking issues. You can run 'job-boo search'.[/green]"
        )


@main.command(name="reset")
@click.option("--jobs", is_flag=True, help="Clear all tracked jobs from the database")
@click.option(
    "--config", "reset_config", is_flag=True, help="Delete config and start fresh"
)
@click.option(
    "--output", is_flag=True, help="Delete all tailored resumes and cover letters"
)
@click.option("--everything", is_flag=True, help="Wipe all job-boo data")
def reset(jobs: bool, reset_config: bool, output: bool, everything: bool) -> None:
    """Reset job-boo data (database, config, or output files)."""
    from job_boo.config import DB_PATH

    if not any([jobs, reset_config, output, everything]):
        console.print(
            "Specify what to reset: --jobs, --config, --output, or --everything"
        )
        console.print("Run 'job-boo reset --help' for details.")
        return

    # Load config once before any deletions (config file may be deleted below)
    config = load_config()

    if everything:
        jobs = reset_config = output = True

    if jobs or everything:
        if DB_PATH.exists():
            if click.confirm(f"Delete job database ({DB_PATH})?"):
                DB_PATH.unlink()
                console.print("[green]  Database deleted.[/green]")
        else:
            console.print("  [dim]No database to delete.[/dim]")

    if reset_config:
        if CONFIG_PATH.exists():
            if click.confirm(f"Delete config ({CONFIG_PATH})?"):
                CONFIG_PATH.unlink()
                console.print(
                    "[green]  Config deleted. Run 'job-boo init' to reconfigure.[/green]"
                )
        else:
            console.print("  [dim]No config to delete.[/dim]")

    if output:
        out_dir = Path(config.output_dir).expanduser()
        if out_dir.exists() and any(out_dir.iterdir()):
            count = len(list(out_dir.iterdir()))
            if click.confirm(f"Delete {count} files in {out_dir}?"):
                shutil.rmtree(out_dir)
                out_dir.mkdir(parents=True)
                console.print("[green]  Output directory cleared.[/green]")
        else:
            console.print("  [dim]Output directory is empty.[/dim]")


@main.command(name="export")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["csv", "json"]),
    default="csv",
    help="Export format",
)
@click.option("--min-score", type=float, default=0, help="Minimum score filter")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def export_jobs(fmt: str, min_score: float, output: str | None) -> None:
    """Export tracked jobs to CSV or JSON."""
    import csv
    import json
    from io import StringIO
    from job_boo.storage.db import JobDB

    with JobDB() as db:
        rows = db.get_jobs(min_score=min_score, limit=10000)

    if not rows:
        console.print("[yellow]No jobs to export.[/yellow]")
        return

    export_fields = [
        "id",
        "title",
        "company",
        "location",
        "url",
        "source",
        "final_score",
        "keyword_score",
        "ai_score",
        "matched_skills",
        "missing_skills",
        "reasoning",
        "state",
        "remote",
        "salary_min",
        "salary_max",
        "posted_date",
        "tailored_resume_path",
        "cover_letter_path",
    ]

    if fmt == "csv":
        buf = StringIO()
        writer = csv.DictWriter(buf, fieldnames=export_fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in export_fields})
        content = buf.getvalue()
        ext = ".csv"
    else:
        clean_rows = [{k: row.get(k, "") for k in export_fields} for row in rows]
        content = json.dumps(clean_rows, indent=2)
        ext = ".json"

    out_path = output or str(
        Path(load_config().output_dir).expanduser() / f"jobs_export{ext}"
    )
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(content)
    console.print(f"[green]Exported {len(rows)} jobs to {out_path}[/green]")


def _update_config_section(section: str, values: dict[str, str]) -> None:
    """Update a specific section of the YAML config without overwriting other sections."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}
    data[section] = values
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    if sys.platform != "win32":
        os.chmod(CONFIG_PATH, 0o600)


@main.command()
@click.option("--url", help="Score a specific job listing URL")
@click.option("--threshold", type=int, help="Override match threshold")
@click.option(
    "--profile", type=str, default=None, help="Use a named profile from config"
)
@click.option(
    "--days", type=int, default=None, help="Only include jobs posted within N days"
)
def search(
    url: str | None,
    threshold: int | None,
    profile: str | None,
    days: int | None,
) -> None:
    """Search for jobs and score them against your resume."""
    config = load_config()
    if profile:
        apply_profile(config, profile)
    ensure_dirs(config)

    if threshold is not None:
        config.match_threshold = threshold

    from job_boo.ai import get_provider
    from job_boo.resume.parser import parse_resume
    from job_boo.scoring.matcher import score_jobs
    from job_boo.storage.db import JobDB

    ai = get_provider(config.ai)

    console.print("\n[bold]Parsing resume...[/bold]")
    resume = parse_resume(config.resume_path, ai)
    console.print(
        f"  Found [green]{len(resume.skills)}[/green] skills: {', '.join(resume.skills[:10])}..."
    )

    if url:
        from job_boo.search.url import parse_job_url

        console.print("\n[bold]Parsing job URL...[/bold]")
        job = parse_job_url(url)
        jobs = [job]
    else:
        from job_boo.search import search_all_sources

        console.print(f"\n[bold]Searching for '{config.job_title}'...[/bold]")
        jobs = search_all_sources(config, max_days=days)

    if not jobs:
        console.print("[red]No jobs found. Check your config and API keys.[/red]")
        return

    # Show cost estimate before AI scoring
    estimated_cost = len(jobs) * 0.003  # ~$0.003 per job for scoring
    console.print(
        f"[dim]Estimated AI scoring cost: ~${estimated_cost:.2f} for {len(jobs)} jobs[/dim]"
    )

    console.print(f"\n[bold]Scoring {len(jobs)} jobs...[/bold]")
    matches = score_jobs(resume, jobs, ai, config)

    with JobDB() as db:
        # Save raw jobs to DB
        for job in jobs:
            db.upsert_job(job)

        # Save scores to DB
        for match in matches:
            db.update_score(match.job.dedup_key(), match)

    # Filter by threshold
    above = [m for m in matches if m.final_score >= config.match_threshold]

    _display_results(above, config.match_threshold)


@main.command()
@click.argument("job_id", type=int)
@click.option(
    "--profile", type=str, default=None, help="Use a named profile from config"
)
def tailor(job_id: int, profile: str | None) -> None:
    """Tailor your resume for a specific job (by DB ID)."""
    config = load_config()
    if profile:
        apply_profile(config, profile)
    ensure_dirs(config)

    from job_boo.ai import get_provider
    from job_boo.resume.parser import parse_resume
    from job_boo.storage.db import JobDB
    from job_boo.tailor.tailorer import tailor_for_job

    ai = get_provider(config.ai)

    with JobDB() as db:
        row = db.get_job_by_id(job_id)
        if not row:
            console.print(
                f"[red]Job ID {job_id} not found. Run 'job-boo jobs' to see available IDs.[/red]"
            )
            return

        resume = parse_resume(config.resume_path, ai)
        match = db.row_to_match(row)

        resume_path, cover_path = tailor_for_job(
            resume, match, ai, config.output_dir, config.apply.include_cover_letter
        )

        db.update_state(
            job_id,
            JobState.TAILORED,
            tailored_resume_path=resume_path,
            cover_letter_path=cover_path,
        )


@main.command()
@click.argument("job_id", type=int, required=False)
@click.option("--min-score", type=float, help="Apply to all jobs above this score")
@click.option("--no-confirm", is_flag=True, help="Skip confirmation prompts")
def apply(job_id: int | None, min_score: float | None, no_confirm: bool) -> None:
    """Apply to a specific job or batch-apply to scored jobs."""
    config = load_config()
    ensure_dirs(config)

    from job_boo.apply.submitter import batch_apply, submit_application
    from job_boo.models import Application
    from job_boo.storage.db import JobDB

    with JobDB() as db:
        confirm = config.apply.confirm_before_submit and not no_confirm

        if job_id:
            row = db.get_job_by_id(job_id)
            if not row:
                console.print(f"[red]Job ID {job_id} not found.[/red]")
                return
            match = db.row_to_match(row)
            app = Application(
                job=match.job,
                match=match,
                tailored_resume_path=row.get("tailored_resume_path", ""),
                cover_letter_path=row.get("cover_letter_path", ""),
                db_id=row["id"],
            )
            submit_application(
                app, db, confirm=confirm, delay=config.apply.delay_between_applications
            )
        elif min_score is not None:
            rows = db.get_jobs(min_score=min_score)
            matches = [db.row_to_match(r) for r in rows]
            batch_apply(
                matches,
                db,
                confirm=confirm,
                delay=config.apply.delay_between_applications,
            )
        else:
            # Default: apply to all scored jobs above threshold
            rows = db.get_jobs(
                state=JobState.TAILORED, min_score=config.match_threshold
            )
            if not rows:
                rows = db.get_jobs(
                    state=JobState.SCORED, min_score=config.match_threshold
                )
            if not rows:
                console.print(
                    "[yellow]No jobs ready to apply. Run 'job-boo search' first.[/yellow]"
                )
                return
            matches = [db.row_to_match(r) for r in rows]
            batch_apply(
                matches,
                db,
                confirm=confirm,
                delay=config.apply.delay_between_applications,
            )


@main.command(name="all")
@click.option("--threshold", type=int, help="Override match threshold")
@click.option("--no-confirm", is_flag=True, help="Skip confirmation for applications")
@click.option(
    "--profile", type=str, default=None, help="Use a named profile from config"
)
@click.option(
    "--days", type=int, default=None, help="Only include jobs posted within N days"
)
def run_all(
    threshold: int | None, no_confirm: bool, profile: str | None, days: int | None
) -> None:
    """Full pipeline: search -> score -> tailor -> apply."""
    config = load_config()
    if profile:
        apply_profile(config, profile)
    ensure_dirs(config)

    if threshold is not None:
        config.match_threshold = threshold

    from job_boo.ai import get_provider
    from job_boo.apply.submitter import batch_apply
    from job_boo.resume.parser import parse_resume
    from job_boo.scoring.matcher import score_jobs
    from job_boo.search import search_all_sources
    from job_boo.storage.db import JobDB
    from job_boo.tailor.tailorer import tailor_for_job

    ai = get_provider(config.ai)

    # Step 1: Parse resume
    console.print("\n[bold]Step 1/4: Parsing resume...[/bold]")
    resume = parse_resume(config.resume_path, ai)
    console.print(f"  Found [green]{len(resume.skills)}[/green] skills")

    # Step 2: Search
    console.print(f"\n[bold]Step 2/4: Searching for '{config.job_title}'...[/bold]")
    jobs = search_all_sources(config, max_days=days)

    if not jobs:
        console.print("[red]No jobs found.[/red]")
        return

    # Step 3: Score
    # Show cost estimate before AI scoring
    estimated_cost = len(jobs) * 0.003  # ~$0.003 per job for scoring
    console.print(
        f"[dim]Estimated AI scoring cost: ~${estimated_cost:.2f} for {len(jobs)} jobs[/dim]"
    )

    console.print(f"\n[bold]Step 3/4: Scoring {len(jobs)} jobs...[/bold]")
    matches = score_jobs(resume, jobs, ai, config)

    with JobDB() as db:
        for job in jobs:
            db.upsert_job(job)
        for match in matches:
            db.update_score(match.job.dedup_key(), match)

        above = [m for m in matches if m.final_score >= config.match_threshold]
        _display_results(above, config.match_threshold)

        if not above:
            console.print(
                "[yellow]No jobs above threshold. Try lowering match_threshold.[/yellow]"
            )
            return

        # Step 4: Tailor top matches
        console.print(
            f"\n[bold]Step 4/4: Tailoring resumes for top {min(len(above), 10)} matches...[/bold]"
        )
        # Build lookup dict to avoid O(n*m) per-match DB query
        rows = db.get_jobs(min_score=0, limit=10000)
        row_by_dedup = {r["dedup_key"]: r for r in rows}

        for match in above[:10]:
            try:
                resume_path, cover_path = tailor_for_job(
                    resume,
                    match,
                    ai,
                    config.output_dir,
                    config.apply.include_cover_letter,
                )
                # Update DB
                row = row_by_dedup.get(match.job.dedup_key())
                if row:
                    db.update_state(
                        row["id"],
                        JobState.TAILORED,
                        tailored_resume_path=resume_path,
                        cover_letter_path=cover_path,
                    )
            except Exception as e:
                console.print(
                    f"  [red]Error tailoring for {match.job.company}: {e}[/red]"
                )

        # Apply
        confirm = config.apply.confirm_before_submit and not no_confirm
        if click.confirm(f"\nReady to apply to {len(above)} jobs?", default=True):
            batch_apply(
                above,
                db,
                confirm=confirm,
                delay=config.apply.delay_between_applications,
            )


@main.command()
@click.option(
    "--state", type=click.Choice([s.value for s in JobState]), help="Filter by state"
)
@click.option("--min-score", type=float, default=0, help="Minimum score filter")
@click.option("--limit", type=int, default=50, help="Max results")
def jobs(state: str | None, min_score: float, limit: int) -> None:
    """List tracked jobs with scores."""
    from job_boo.storage.db import JobDB

    with JobDB() as db:
        job_state = JobState(state) if state else None
        rows = db.get_jobs(state=job_state, min_score=min_score, limit=limit)

    if not rows:
        console.print("[yellow]No jobs found. Run 'job-boo search' first.[/yellow]")
        return

    table = Table(title="Tracked Jobs")
    table.add_column("ID", style="dim")
    table.add_column("Score", justify="right")
    table.add_column("Company")
    table.add_column("Title")
    table.add_column("Location")
    table.add_column("State")
    table.add_column("Source")

    for row in rows:
        score = row["final_score"] or 0
        score_color = "green" if score >= 70 else "yellow" if score >= 50 else "red"
        state_val = row["state"] or "found"
        table.add_row(
            str(row["id"]),
            f"[{score_color}]{score:.0f}%[/{score_color}]",
            row["company"][:25],
            row["title"][:35],
            (row["location"] or "")[:20],
            state_val,
            row["source"] or "",
        )

    console.print(table)


@main.command()
def status() -> None:
    """Show pipeline dashboard with stats."""
    from job_boo.storage.db import JobDB

    with JobDB() as db:
        stats = db.get_stats()

    total = sum(stats.values()) if stats else 0
    if total == 0:
        console.print(
            "[yellow]No data yet. Run 'job-boo search' to get started.[/yellow]"
        )
        return

    console.print("\n[bold]Pipeline Dashboard[/bold]\n")
    table = Table()
    table.add_column("State")
    table.add_column("Count", justify="right")

    for state_val in [s.value for s in JobState]:
        count = stats.get(state_val, 0)
        if count > 0:
            table.add_row(state_val.upper(), str(count))

    table.add_row("[bold]TOTAL[/bold]", f"[bold]{total}[/bold]")
    console.print(table)


@main.command()
@click.argument("job_id", type=int)
def show(job_id: int) -> None:
    """Show detailed information for a specific job (by DB ID)."""
    from rich.panel import Panel
    from job_boo.storage.db import JobDB

    with JobDB() as db:
        row = db.get_job_by_id(job_id)

    if not row:
        console.print(
            f"[red]Job ID {job_id} not found. Run 'job-boo jobs' to see available IDs.[/red]"
        )
        return

    import json

    title = row["title"] or ""
    company = row["company"] or ""
    location = row["location"] or "N/A"
    remote = "Yes" if row["remote"] else "No"
    state = row["state"] or "found"
    url = row["url"] or "N/A"
    posted_date = row["posted_date"] or "N/A"
    applied_at = row["applied_at"] or "N/A"
    notes = row["notes"] or ""

    keyword_score = row["keyword_score"] or 0
    ai_score = row["ai_score"] or 0
    final_score = row["final_score"] or 0
    reasoning = row["reasoning"] or "N/A"

    matched_skills = json.loads(row["matched_skills"]) if row["matched_skills"] else []
    missing_skills = json.loads(row["missing_skills"]) if row["missing_skills"] else []

    description = row["description"] or ""
    desc_preview = description[:500] + ("..." if len(description) > 500 else "")

    score_color = (
        "green" if final_score >= 70 else "yellow" if final_score >= 50 else "red"
    )

    lines = [
        f"[bold]{title}[/bold] at [bold]{company}[/bold]",
        "",
        f"[dim]Location:[/dim]    {location}",
        f"[dim]Remote:[/dim]      {remote}",
        f"[dim]State:[/dim]       {state}",
        f"[dim]URL:[/dim]         {url}",
        f"[dim]Posted:[/dim]      {posted_date}",
        f"[dim]Applied:[/dim]     {applied_at}",
        "",
        "[bold]Score Breakdown[/bold]",
        f"  Keyword:  {keyword_score:.0f}%",
        f"  AI:       {ai_score:.0f}%",
        f"  Final:    [{score_color}]{final_score:.0f}%[/{score_color}]",
        "",
        f"[bold]Matched Skills[/bold]: {', '.join(matched_skills) if matched_skills else 'N/A'}",
        f"[bold]Missing Skills[/bold]: {', '.join(missing_skills) if missing_skills else 'N/A'}",
        "",
        "[bold]AI Reasoning[/bold]",
        f"  {reasoning}",
    ]

    if notes:
        lines.extend(["", "[bold]Notes[/bold]", f"  {notes}"])

    lines.extend(
        ["", "[bold]Description (first 500 chars)[/bold]", f"  {desc_preview}"]
    )

    panel = Panel("\n".join(lines), title=f"Job #{job_id}", border_style="cyan")
    console.print(panel)


@main.command()
@click.argument("job_id", type=int)
@click.argument("text", required=False, default=None)
def note(job_id: int, text: str | None) -> None:
    """Add or view notes for a job. If no text is provided, shows current notes."""
    from job_boo.storage.db import JobDB

    with JobDB() as db:
        row = db.get_job_by_id(job_id)
        if not row:
            console.print(
                f"[red]Job ID {job_id} not found. Run 'job-boo jobs' to see available IDs.[/red]"
            )
            return

        if text is None:
            current_notes = row.get("notes") or ""
            if current_notes:
                console.print(
                    f"[bold]Notes for Job #{job_id}[/bold] ({row['company']} - {row['title']}):"
                )
                console.print(f"  {current_notes}")
            else:
                console.print(
                    f"[yellow]No notes for Job #{job_id}. Use 'job-boo note {job_id} \"your note\"' to add one.[/yellow]"
                )
        else:
            db.update_notes(job_id, text)
            console.print(
                f"[green]Note saved for Job #{job_id} ({row['company']} - {row['title']}).[/green]"
            )


@main.command()
@click.argument("job_id", type=int)
def prep(job_id: int) -> None:
    """Generate interview preparation material for a job (by DB ID)."""
    import re

    from rich.markdown import Markdown
    from rich.panel import Panel

    config = load_config()
    ensure_dirs(config)

    from job_boo.ai import get_provider
    from job_boo.resume.parser import parse_resume
    from job_boo.storage.db import JobDB

    with JobDB() as db:
        row = db.get_job_by_id(job_id)
        if not row:
            console.print(
                f"[red]Job ID {job_id} not found. Run 'job-boo jobs' to see available IDs.[/red]"
            )
            return
        job = db.row_to_job(row)

    ai = get_provider(config.ai)

    console.print("\n[bold]Parsing resume...[/bold]")
    resume = parse_resume(config.resume_path, ai)

    console.print(
        f"[bold]Generating interview prep for {job.title} at {job.company}...[/bold]\n"
    )
    prep_text = ai.prep_interview(resume, job)

    # Display with rich Markdown panel
    md = Markdown(prep_text)
    panel = Panel(
        md, title=f"Interview Prep: {job.title} @ {job.company}", border_style="green"
    )
    console.print(panel)

    # Save to file
    out_dir = Path(config.output_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_company = re.sub(r"[^\w\-]", "_", job.company.lower().strip())
    safe_title = re.sub(r"[^\w\-]", "_", job.title.lower().strip())
    out_path = out_dir / f"prep_{safe_company}_{safe_title}.txt"
    out_path.write_text(prep_text)
    console.print(f"\n[green]Saved to {out_path}[/green]")


@main.command()
@click.option(
    "--interval", type=int, default=24, help="Hours between searches (default: 24)"
)
@click.option("--once", is_flag=True, help="Run once and exit (for cron jobs)")
@click.option(
    "--webhook", type=str, default=None, help="POST new matches as JSON to this URL"
)
@click.option("--threshold", type=int, help="Override match threshold")
def watch(
    interval: int, once: bool, webhook: str | None, threshold: int | None
) -> None:
    """Watch for new jobs at a configurable interval."""
    import time

    import httpx

    config = load_config()
    ensure_dirs(config)

    if threshold is not None:
        config.match_threshold = threshold

    from job_boo.ai import get_provider
    from job_boo.resume.parser import parse_resume
    from job_boo.scoring.matcher import score_jobs
    from job_boo.search import search_all_sources
    from job_boo.storage.db import JobDB

    ai = get_provider(config.ai)
    resume = parse_resume(config.resume_path, ai)

    console.print(
        "[yellow]WARNING: Watch mode makes repeated API calls that consume your AI quota. "
        "Each cycle searches all sources and scores new jobs. "
        f"At {interval}-hour intervals, expect ~$1-3/day in AI costs.[/yellow]\n"
    )

    if interval < 4 and not once:
        console.print(
            "[yellow]WARNING: Intervals under 4 hours may exhaust free API quotas quickly. "
            f"At {interval}h intervals, you'll use ~{720 // interval} API calls/month per source.[/yellow]"
        )

    def run_once() -> None:
        with JobDB() as db:
            existing_keys = db.get_all_dedup_keys()

            console.print(f"\n[bold]Searching for '{config.job_title}'...[/bold]")
            jobs = search_all_sources(config)

            # Filter to only new jobs
            new_jobs = [j for j in jobs if j.dedup_key() not in existing_keys]

            if not new_jobs:
                console.print("[dim]No new jobs found since last run.[/dim]")
                return

            console.print(
                f"[green]{len(new_jobs)} new jobs found[/green] (out of {len(jobs)} total)"
            )

            # Save all jobs to DB
            for job in jobs:
                db.upsert_job(job)

            # Score only the new ones
            # Show cost estimate before AI scoring
            estimated_cost = len(new_jobs) * 0.003  # ~$0.003 per job for scoring
            console.print(
                f"[dim]Estimated AI scoring cost: ~${estimated_cost:.2f} for {len(new_jobs)} jobs[/dim]"
            )

            console.print(f"[bold]Scoring {len(new_jobs)} new jobs...[/bold]")
            matches = score_jobs(resume, new_jobs, ai, config)
            for match in matches:
                db.update_score(match.job.dedup_key(), match)

        above = [m for m in matches if m.final_score >= config.match_threshold]

        if above:
            _display_results(above, config.match_threshold)
        else:
            console.print(
                f"[yellow]No new jobs above {config.match_threshold}% threshold.[/yellow]"
            )

        # Webhook notification
        if webhook and not webhook.startswith("https://"):
            console.print(
                "[yellow]WARNING: Webhook URL is not HTTPS. Data will be sent unencrypted.[/yellow]"
            )
        if webhook and above:
            payload = [
                {
                    "title": m.job.title,
                    "company": m.job.company,
                    "location": m.job.location,
                    "url": m.job.url,
                    "score": m.final_score,
                    "matched_skills": m.matched_skills,
                    "missing_skills": m.missing_skills,
                }
                for m in above
            ]
            try:
                resp = httpx.post(webhook, json=payload, timeout=30)
                console.print(f"[green]Webhook sent ({resp.status_code})[/green]")
            except Exception as e:
                console.print(f"[red]Webhook failed: {e}[/red]")

    if once:
        run_once()
        return

    console.print(
        f"[bold]Watch mode: checking every {interval} hours. Press Ctrl+C to stop.[/bold]"
    )
    while True:
        try:
            run_once()
            console.print(f"\n[dim]Next check in {interval} hours...[/dim]")
            time.sleep(interval * 3600)
        except KeyboardInterrupt:
            console.print("\n[bold]Watch stopped.[/bold]")
            break


@main.command()
def analytics() -> None:
    """Show application analytics and conversion rates."""
    import json

    from rich.table import Table as RichTable

    from job_boo.storage.db import JobDB

    with JobDB() as db:
        stats = db.get_stats()
        all_jobs = db.get_all_jobs()
        daily = db.get_applied_per_day(days=30)

    if not all_jobs:
        console.print(
            "[yellow]No data yet. Run 'job-boo search' to get started.[/yellow]"
        )
        return

    # Counts by state
    scored = stats.get("scored", 0)
    tailored = stats.get("tailored", 0)
    applied = stats.get("applied", 0)
    closed = stats.get("closed", 0)
    total = sum(stats.values())

    # Pipeline overview
    console.print("\n[bold]Application Analytics[/bold]\n")

    pipeline_table = RichTable(title="Pipeline Overview")
    pipeline_table.add_column("Metric", style="bold")
    pipeline_table.add_column("Value", justify="right")
    pipeline_table.add_row("Total Jobs Found", str(total))
    pipeline_table.add_row("Scored", str(scored + tailored + applied + closed))
    pipeline_table.add_row("Tailored", str(tailored + applied))
    pipeline_table.add_row("Applied", str(applied))
    pipeline_table.add_row("Closed", str(closed))
    console.print(pipeline_table)

    # Conversion rates
    scored_total = scored + tailored + applied + closed
    applied_total = applied
    console.print()
    conv_table = RichTable(title="Conversion Rates")
    conv_table.add_column("Conversion", style="bold")
    conv_table.add_column("Rate", justify="right")

    if total > 0:
        conv_table.add_row("Scored / Found", f"{scored_total / total * 100:.1f}%")
    if scored_total > 0:
        conv_table.add_row(
            "Applied / Scored", f"{applied_total / scored_total * 100:.1f}%"
        )
    if total > 0:
        conv_table.add_row("Applied / Found", f"{applied_total / total * 100:.1f}%")
    console.print(conv_table)

    # Average match score of applied jobs
    applied_rows = [r for r in all_jobs if r["state"] == "applied" and r["final_score"]]
    if applied_rows:
        avg_score = sum(r["final_score"] for r in applied_rows) / len(applied_rows)
        console.print(
            f"\n[bold]Average match score of applied jobs:[/bold] {avg_score:.1f}%"
        )

    # Top 5 matched skills and missing skills across all jobs
    matched_counts: dict[str, int] = {}
    missing_counts: dict[str, int] = {}
    for row in all_jobs:
        if row.get("matched_skills"):
            try:
                for skill in json.loads(row["matched_skills"]):
                    matched_counts[skill] = matched_counts.get(skill, 0) + 1
            except (json.JSONDecodeError, TypeError):
                pass
        if row.get("missing_skills"):
            try:
                for skill in json.loads(row["missing_skills"]):
                    missing_counts[skill] = missing_counts.get(skill, 0) + 1
            except (json.JSONDecodeError, TypeError):
                pass

    if matched_counts:
        console.print()
        top_matched = sorted(matched_counts.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]
        skill_table = RichTable(title="Top 5 Matched Skills")
        skill_table.add_column("Skill", style="green")
        skill_table.add_column("Jobs", justify="right")
        for skill, count in top_matched:
            skill_table.add_row(skill, str(count))
        console.print(skill_table)

    if missing_counts:
        console.print()
        top_missing = sorted(missing_counts.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]
        gap_table = RichTable(title="Top 5 Missing Skills (Skill Gaps)")
        gap_table.add_column("Skill", style="red")
        gap_table.add_column("Jobs", justify="right")
        for skill, count in top_missing:
            gap_table.add_row(skill, str(count))
        console.print(gap_table)

    # Jobs applied per day (last 30 days)
    if daily:
        console.print()
        daily_table = RichTable(title="Applications Per Day (Last 30 Days)")
        daily_table.add_column("Date", style="bold")
        daily_table.add_column("Applications", justify="right")
        for entry in daily:
            daily_table.add_row(str(entry["day"]), str(entry["count"]))
        console.print(daily_table)

    console.print()


@main.command()
@click.option("--output", type=str, default=None, help="Output HTML file path")
def dashboard(output: str | None) -> None:
    """Generate an HTML analytics dashboard with charts and tables."""
    from pathlib import Path

    from job_boo.analytics.dashboard import generate_dashboard

    output_path = Path(output) if output else None
    path = generate_dashboard(output_path=output_path)
    console.print(f"[green]Dashboard generated: {path}[/green]")

    import webbrowser

    if click.confirm("Open in browser?", default=True):
        webbrowser.open(f"file://{path.resolve()}")


@main.command()
@click.option(
    "--days", type=int, default=90, help="Delete jobs older than N days (default: 90)"
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be deleted without deleting"
)
def cleanup(days: int, dry_run: bool) -> None:
    """Remove expired jobs (found/scored only, not applied/tailored)."""
    from job_boo.storage.db import JobDB

    with JobDB() as db:
        if dry_run:
            rows = db.conn.execute(
                """SELECT COUNT(*) as cnt FROM jobs
                WHERE state IN ('found', 'scored')
                    AND DATE(updated_at) < DATE('now', ?)""",
                (f"-{days} days",),
            ).fetchone()
            count = rows["cnt"] if rows else 0
            console.print(
                f"[yellow]Dry run: {count} jobs in found/scored state older than {days} days would be deleted.[/yellow]"
            )
        else:
            deleted = db.cleanup_expired(days=days)
            console.print(
                f"[green]Cleaned up {deleted} expired jobs (older than {days} days).[/green]"
            )


@main.command()
@click.argument("company", required=False, default=None)
@click.option(
    "--days", type=int, default=None, help="Show applications from last N days"
)
def history(company: str | None, days: int | None) -> None:
    """Show application history — optionally filter by company or date range."""
    from rich.table import Table as RichTable

    from job_boo.storage.db import JobDB

    with JobDB() as db:
        if company:
            rows = db.get_company_history(company=company)
            if not rows:
                console.print(
                    f"[yellow]No jobs found for company '{company}'.[/yellow]"
                )
                return
            table = RichTable(title=f"History for '{company}'")
            table.add_column("Company", style="bold")
            table.add_column("Jobs", justify="right")
            table.add_column("Applied", justify="right")
            table.add_column("Avg Score", justify="right")
            table.add_column("Last Applied")
            table.add_column("States")
            for r in rows:
                table.add_row(
                    r["company"],
                    str(r["job_count"]),
                    str(r["applied_count"]),
                    f"{r['avg_score']:.1f}" if r["avg_score"] else "N/A",
                    r["latest_applied_at"] or "N/A",
                    r["states"] or "",
                )
            console.print(table)
        elif days:
            from datetime import datetime, timedelta

            end = datetime.now().strftime("%Y-%m-%d")
            start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            rows = db.get_jobs_by_date_range(start, end, state="applied")
            console.print(
                f"\n[bold]Applications in last {days} days ({start} to {end}):[/bold] {len(rows)}\n"
            )
            if rows:
                table = RichTable()
                table.add_column("Date")
                table.add_column("Company", style="bold")
                table.add_column("Title")
                table.add_column("Score", justify="right")
                for r in rows:
                    score = r.get("final_score") or 0
                    table.add_row(
                        (r.get("applied_at") or r.get("created_at") or "")[:10],
                        r["company"],
                        r["title"],
                        f"{score:.0f}%",
                    )
                console.print(table)
        else:
            # Default: show all companies summary
            rows = db.get_company_history()
            if not rows:
                console.print(
                    "[yellow]No data yet. Run 'job-boo search' first.[/yellow]"
                )
                return
            table = RichTable(title="Company Summary")
            table.add_column("Company", style="bold")
            table.add_column("Jobs", justify="right")
            table.add_column("Applied", justify="right")
            table.add_column("Avg Score", justify="right")
            table.add_column("Last Applied")
            for r in rows[:30]:
                table.add_row(
                    r["company"][:35],
                    str(r["job_count"]),
                    str(r["applied_count"]),
                    f"{r['avg_score']:.1f}" if r["avg_score"] else "N/A",
                    r["latest_applied_at"] or "---",
                )
            console.print(table)


def _display_results(matches: list[MatchResult], threshold: int) -> None:
    """Display scored results in a rich table."""
    if not matches:
        console.print(f"\n[yellow]No jobs scored above {threshold}%.[/yellow]")
        return

    console.print(
        f"\n[bold green]{len(matches)} jobs above {threshold}% threshold:[/bold green]\n"
    )

    table = Table()
    table.add_column("#", style="dim")
    table.add_column("Score", justify="right")
    table.add_column("Company")
    table.add_column("Title")
    table.add_column("Location")
    table.add_column("Top Matched Skills")
    table.add_column("Flags")

    for i, match in enumerate(matches, 1):
        score_color = (
            "green"
            if match.final_score >= 70
            else "yellow"
            if match.final_score >= 50
            else "red"
        )
        flags = []
        if not match.location_fit:
            flags.append("[red]LOC[/red]")
        if not match.sponsorship_fit:
            flags.append("[red]VISA[/red]")

        table.add_row(
            str(i),
            f"[{score_color}]{match.final_score:.0f}%[/{score_color}]",
            match.job.company[:25],
            match.job.title[:35],
            match.job.location[:20],
            ", ".join(match.matched_skills[:4]),
            " ".join(flags) if flags else "[green]OK[/green]",
        )

    console.print(table)


if __name__ == "__main__":
    main()
