"""CLI entry point for job-boo."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.table import Table

from job_boo.config import CONFIG_DIR, CONFIG_PATH, load_config, ensure_dirs
from job_boo.models import JobState

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
    config["job_title"] = click.prompt("Target job title (e.g., Senior Software Engineer)")
    keywords = click.prompt("Additional search keywords (comma-separated, or blank)", default="")
    config["keywords"] = [k.strip() for k in keywords.split(",") if k.strip()]

    console.print("\n[bold]Location[/bold]")
    pref = click.prompt("Preference", type=click.Choice(["remote", "hybrid", "onsite"]), default="remote")
    city = ""
    if pref != "remote":
        city = click.prompt("City")
    config["location"] = {"preference": pref, "city": city}

    config["needs_sponsorship"] = click.confirm("Do you need visa sponsorship?", default=False)

    console.print("\n[bold]Salary (USD, enter 0 to skip)[/bold]")
    config["salary"] = {
        "min": click.prompt("Minimum salary", type=int, default=0),
        "max": click.prompt("Maximum salary", type=int, default=0),
        "currency": "USD",
    }

    config["match_threshold"] = click.prompt("Minimum match score (0-100)", type=int, default=60)

    console.print("\n[bold]AI Provider[/bold]")
    provider = click.prompt("Provider", type=click.Choice(["claude", "openai"]), default="claude")
    api_key = click.prompt("API key (or set JOB_BOO_AI_KEY env var)", default="", hide_input=True)
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
        config["sources"]["serpapi"]["api_key"] = click.prompt("SerpAPI key", default="")

    if click.confirm("Enable Adzuna (free tier, 1000 req/month)?", default=True):
        config["sources"]["adzuna"]["enabled"] = True
        config["sources"]["adzuna"]["app_id"] = click.prompt("Adzuna App ID", default="")
        config["sources"]["adzuna"]["api_key"] = click.prompt("Adzuna API key", default="")

    config["output_dir"] = str(CONFIG_DIR / "output")
    config["apply"] = {
        "confirm_before_submit": True,
        "include_cover_letter": True,
        "delay_between_applications": 5,
    }

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    console.print(f"\n[green]Config saved to {CONFIG_PATH}[/green]")
    console.print("Run [bold]job-boo search[/bold] to find matching jobs.")


@main.command(name="setup-ai")
def setup_ai() -> None:
    """Configure and validate AI provider (Claude or OpenAI)."""
    config = load_config()
    console.print("\n[bold]AI Provider Setup[/bold]\n")

    # Show current state
    current_key = config.ai.resolve_key()
    has_key = bool(current_key)
    masked = f"...{current_key[-6:]}" if len(current_key) > 6 else ("(set)" if has_key else "(not set)")

    console.print(f"  Current provider:  [cyan]{config.ai.provider}[/cyan]")
    console.print(f"  Current model:     [cyan]{config.ai.resolve_model()}[/cyan]")
    console.print(f"  API key:           [cyan]{masked}[/cyan]")
    env_key = os.environ.get("JOB_BOO_AI_KEY", "")
    if env_key:
        console.print(f"  Env JOB_BOO_AI_KEY: [green]set[/green]")
    console.print()

    # Choose provider
    provider = click.prompt(
        "AI provider",
        type=click.Choice(["claude", "openai"]),
        default=config.ai.provider,
    )

    # Provider-specific guidance
    if provider == "claude":
        console.print("\n  [dim]Get your API key at: https://console.anthropic.com/settings/keys[/dim]")
        console.print("  [dim]Free tier: limited requests. Pay-as-you-go recommended.[/dim]")
        models = ["claude-sonnet-4-20250514", "claude-haiku-4-5-20251001", "claude-opus-4-20250514"]
        default_model = "claude-sonnet-4-20250514"
    else:
        console.print("\n  [dim]Get your API key at: https://platform.openai.com/api-keys[/dim]")
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
        console.print(f'  [bold]export JOB_BOO_AI_KEY="your-key-here"[/bold]')
        console.print("  Then restart your terminal or run: [bold]source ~/.zshrc[/bold]")
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
            console.print(f"  [bold green]Connection successful![/bold green]")
        except Exception as e:
            console.print(f"  [bold red]Connection failed: {e}[/bold red]")
            if not click.confirm("Save config anyway?", default=False):
                return
    else:
        console.print("\n[yellow]No API key available to test. Set one via env var or re-run setup.[/yellow]")

    # Save to config
    _update_config_section("ai", {
        "provider": provider,
        "api_key": api_key,
        "model": model,
    })
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
        console.print(f"  Config file:       [red]MISSING[/red]")
        issues.append("Run 'job-boo init' to create config")

    # Resume
    if config.resume_path:
        resume_path = Path(config.resume_path).expanduser()
        if resume_path.exists():
            size_kb = resume_path.stat().st_size / 1024
            console.print(f"  Resume PDF:        [green]OK[/green] ({size_kb:.0f} KB)")
        else:
            console.print(f"  Resume PDF:        [red]NOT FOUND[/red] ({config.resume_path})")
            issues.append(f"Resume file not found: {config.resume_path}")
    else:
        console.print(f"  Resume PDF:        [red]NOT SET[/red]")
        issues.append("Set resume_path in config")

    # AI provider
    ai_key = config.ai.resolve_key()
    if ai_key:
        console.print(f"  AI provider:       [green]{config.ai.provider}[/green] (model: {config.ai.resolve_model()})")
        console.print(f"  AI key:            [green]...{ai_key[-6:]}[/green]")
    else:
        console.print(f"  AI provider:       [red]NO KEY[/red]")
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
        console.print(f"  Job sources:       [green]{', '.join(active_sources)}[/green]")
    else:
        console.print(f"  Job sources:       [red]NONE[/red]")
        issues.append("No job sources configured")

    # Free sources without keys
    if not config.sources.adzuna.resolve_key() and config.sources.adzuna.enabled:
        warnings.append("Adzuna enabled but no API key — get a free key at developer.adzuna.com")

    # Search criteria
    if config.job_title:
        console.print(f"  Job title:         [green]{config.job_title}[/green]")
    else:
        console.print(f"  Job title:         [yellow]NOT SET[/yellow]")
        warnings.append("Set job_title in config for better search results")

    console.print(f"  Location:          {config.location.preference}" +
                  (f" ({config.location.city})" if config.location.city else ""))
    console.print(f"  Sponsorship:       {'needed' if config.needs_sponsorship else 'not needed'}")
    console.print(f"  Match threshold:   {config.match_threshold}%")

    # Output dir
    out_dir = Path(config.output_dir).expanduser()
    if out_dir.exists():
        console.print(f"  Output dir:        [green]OK[/green] ({out_dir})")
    else:
        console.print(f"  Output dir:        [yellow]will be created[/yellow] ({out_dir})")

    # DB
    from job_boo.config import DB_PATH
    if DB_PATH.exists():
        size_kb = DB_PATH.stat().st_size / 1024
        from job_boo.storage.db import JobDB
        db = JobDB()
        stats = db.get_stats()
        total = sum(stats.values())
        db.close()
        console.print(f"  Database:          [green]{total} jobs tracked[/green] ({size_kb:.0f} KB)")
    else:
        console.print(f"  Database:          [dim]not yet created[/dim]")

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
        console.print("[bold green]All good! Run 'job-boo search' to get started.[/bold green]")
    elif not issues:
        console.print("\n[green]No blocking issues. You can run 'job-boo search'.[/green]")


@main.command(name="reset")
@click.option("--jobs", is_flag=True, help="Clear all tracked jobs from the database")
@click.option("--config", "reset_config", is_flag=True, help="Delete config and start fresh")
@click.option("--output", is_flag=True, help="Delete all tailored resumes and cover letters")
@click.option("--everything", is_flag=True, help="Wipe all job-boo data")
def reset(jobs: bool, reset_config: bool, output: bool, everything: bool) -> None:
    """Reset job-boo data (database, config, or output files)."""
    from job_boo.config import DB_PATH

    if not any([jobs, reset_config, output, everything]):
        console.print("Specify what to reset: --jobs, --config, --output, or --everything")
        console.print("Run 'job-boo reset --help' for details.")
        return

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
                console.print("[green]  Config deleted. Run 'job-boo init' to reconfigure.[/green]")
        else:
            console.print("  [dim]No config to delete.[/dim]")

    if output:
        out_dir = Path(load_config().output_dir).expanduser()
        if out_dir.exists() and any(out_dir.iterdir()):
            count = len(list(out_dir.iterdir()))
            if click.confirm(f"Delete {count} files in {out_dir}?"):
                shutil.rmtree(out_dir)
                out_dir.mkdir(parents=True)
                console.print("[green]  Output directory cleared.[/green]")
        else:
            console.print("  [dim]Output directory is empty.[/dim]")


@main.command(name="export")
@click.option("--format", "fmt", type=click.Choice(["csv", "json"]), default="csv", help="Export format")
@click.option("--min-score", type=float, default=0, help="Minimum score filter")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def export_jobs(fmt: str, min_score: float, output: str | None) -> None:
    """Export tracked jobs to CSV or JSON."""
    import csv
    import json
    from io import StringIO
    from job_boo.storage.db import JobDB

    db = JobDB()
    rows = db.get_jobs(min_score=min_score, limit=10000)
    db.close()

    if not rows:
        console.print("[yellow]No jobs to export.[/yellow]")
        return

    export_fields = [
        "id", "title", "company", "location", "url", "source",
        "final_score", "keyword_score", "ai_score",
        "matched_skills", "missing_skills", "reasoning",
        "state", "remote", "salary_min", "salary_max",
        "posted_date", "tailored_resume_path", "cover_letter_path",
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

    out_path = output or str(Path(load_config().output_dir).expanduser() / f"jobs_export{ext}")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(content)
    console.print(f"[green]Exported {len(rows)} jobs to {out_path}[/green]")


def _update_config_section(section: str, values: dict) -> None:
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


@main.command()
@click.option("--url", help="Score a specific job listing URL")
@click.option("--threshold", type=int, help="Override match threshold")
@click.option("--limit", type=int, default=50, help="Max jobs to return per source")
def search(url: str | None, threshold: int | None, limit: int) -> None:
    """Search for jobs and score them against your resume."""
    config = load_config()
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
    console.print(f"  Found [green]{len(resume.skills)}[/green] skills: {', '.join(resume.skills[:10])}...")

    db = JobDB()

    if url:
        from job_boo.search.url import parse_job_url
        console.print(f"\n[bold]Parsing job URL...[/bold]")
        job = parse_job_url(url)
        jobs = [job]
    else:
        from job_boo.search import search_all_sources
        console.print(f"\n[bold]Searching for '{config.job_title}'...[/bold]")
        jobs = search_all_sources(config)

    if not jobs:
        console.print("[red]No jobs found. Check your config and API keys.[/red]")
        return

    # Save raw jobs to DB
    for job in jobs:
        db.upsert_job(job)

    console.print(f"\n[bold]Scoring {len(jobs)} jobs...[/bold]")
    matches = score_jobs(resume, jobs, ai, config)

    # Save scores to DB
    for match in matches:
        db.update_score(match.job.dedup_key(), match)

    # Filter by threshold
    above = [m for m in matches if m.final_score >= config.match_threshold]

    _display_results(above, config.match_threshold)
    db.close()


@main.command()
@click.argument("job_id", type=int)
def tailor(job_id: int) -> None:
    """Tailor your resume for a specific job (by DB ID)."""
    config = load_config()
    ensure_dirs(config)

    from job_boo.ai import get_provider
    from job_boo.resume.parser import parse_resume
    from job_boo.storage.db import JobDB
    from job_boo.tailor.tailorer import tailor_for_job

    ai = get_provider(config.ai)
    db = JobDB()

    row = db.get_job_by_id(job_id)
    if not row:
        console.print(f"[red]Job ID {job_id} not found. Run 'job-boo jobs' to see available IDs.[/red]")
        return

    resume = parse_resume(config.resume_path, ai)
    match = db.row_to_match(row)

    resume_path, cover_path = tailor_for_job(
        resume, match, ai, config.output_dir, config.apply.include_cover_letter
    )

    db.update_state(job_id, JobState.TAILORED,
                    tailored_resume_path=resume_path,
                    cover_letter_path=cover_path)
    db.close()


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

    db = JobDB()
    confirm = config.apply.confirm_before_submit and not no_confirm

    if job_id:
        row = db.get_job_by_id(job_id)
        if not row:
            console.print(f"[red]Job ID {job_id} not found.[/red]")
            return
        match = db.row_to_match(row)
        app = Application(
            job=match.job, match=match,
            tailored_resume_path=row.get("tailored_resume_path", ""),
            cover_letter_path=row.get("cover_letter_path", ""),
            db_id=row["id"],
        )
        submit_application(app, db, confirm=confirm, delay=config.apply.delay_between_applications)
    elif min_score is not None:
        rows = db.get_jobs(min_score=min_score)
        matches = [db.row_to_match(r) for r in rows]
        batch_apply(matches, db, confirm=confirm, delay=config.apply.delay_between_applications)
    else:
        # Default: apply to all scored jobs above threshold
        rows = db.get_jobs(state=JobState.TAILORED, min_score=config.match_threshold)
        if not rows:
            rows = db.get_jobs(state=JobState.SCORED, min_score=config.match_threshold)
        if not rows:
            console.print("[yellow]No jobs ready to apply. Run 'job-boo search' first.[/yellow]")
            return
        matches = [db.row_to_match(r) for r in rows]
        batch_apply(matches, db, confirm=confirm, delay=config.apply.delay_between_applications)

    db.close()


@main.command(name="all")
@click.option("--threshold", type=int, help="Override match threshold")
@click.option("--no-confirm", is_flag=True, help="Skip confirmation for applications")
def run_all(threshold: int | None, no_confirm: bool) -> None:
    """Full pipeline: search -> score -> tailor -> apply."""
    config = load_config()
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
    db = JobDB()

    # Step 1: Parse resume
    console.print("\n[bold]Step 1/4: Parsing resume...[/bold]")
    resume = parse_resume(config.resume_path, ai)
    console.print(f"  Found [green]{len(resume.skills)}[/green] skills")

    # Step 2: Search
    console.print(f"\n[bold]Step 2/4: Searching for '{config.job_title}'...[/bold]")
    jobs = search_all_sources(config)
    for job in jobs:
        db.upsert_job(job)

    if not jobs:
        console.print("[red]No jobs found.[/red]")
        return

    # Step 3: Score
    console.print(f"\n[bold]Step 3/4: Scoring {len(jobs)} jobs...[/bold]")
    matches = score_jobs(resume, jobs, ai, config)
    for match in matches:
        db.update_score(match.job.dedup_key(), match)

    above = [m for m in matches if m.final_score >= config.match_threshold]
    _display_results(above, config.match_threshold)

    if not above:
        console.print("[yellow]No jobs above threshold. Try lowering match_threshold.[/yellow]")
        return

    # Step 4: Tailor top matches
    console.print(f"\n[bold]Step 4/4: Tailoring resumes for top {min(len(above), 10)} matches...[/bold]")
    for match in above[:10]:
        try:
            resume_path, cover_path = tailor_for_job(
                resume, match, ai, config.output_dir, config.apply.include_cover_letter
            )
            # Update DB
            rows = db.get_jobs(min_score=0, limit=1000)
            for r in rows:
                if r["dedup_key"] == match.job.dedup_key():
                    db.update_state(r["id"], JobState.TAILORED,
                                    tailored_resume_path=resume_path,
                                    cover_letter_path=cover_path)
                    break
        except Exception as e:
            console.print(f"  [red]Error tailoring for {match.job.company}: {e}[/red]")

    # Apply
    confirm = config.apply.confirm_before_submit and not no_confirm
    if click.confirm(f"\nReady to apply to {len(above)} jobs?", default=True):
        batch_apply(above, db, confirm=confirm, delay=config.apply.delay_between_applications)

    db.close()


@main.command()
@click.option("--state", type=click.Choice([s.value for s in JobState]), help="Filter by state")
@click.option("--min-score", type=float, default=0, help="Minimum score filter")
@click.option("--limit", type=int, default=50, help="Max results")
def jobs(state: str | None, min_score: float, limit: int) -> None:
    """List tracked jobs with scores."""
    from job_boo.storage.db import JobDB

    db = JobDB()
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
    db.close()


@main.command()
def status() -> None:
    """Show pipeline dashboard with stats."""
    from job_boo.storage.db import JobDB

    db = JobDB()
    stats = db.get_stats()

    if not stats:
        console.print("[yellow]No data yet. Run 'job-boo search' to get started.[/yellow]")
        return

    console.print("\n[bold]Pipeline Dashboard[/bold]\n")
    table = Table()
    table.add_column("State")
    table.add_column("Count", justify="right")

    total = 0
    for state_val in [s.value for s in JobState]:
        count = stats.get(state_val, 0)
        if count > 0:
            table.add_row(state_val.upper(), str(count))
            total += count

    table.add_row("[bold]TOTAL[/bold]", f"[bold]{total}[/bold]")
    console.print(table)
    db.close()


def _display_results(matches: list, threshold: int) -> None:
    """Display scored results in a rich table."""
    from job_boo.models import MatchResult

    if not matches:
        console.print(f"\n[yellow]No jobs scored above {threshold}%.[/yellow]")
        return

    console.print(f"\n[bold green]{len(matches)} jobs above {threshold}% threshold:[/bold green]\n")

    table = Table()
    table.add_column("#", style="dim")
    table.add_column("Score", justify="right")
    table.add_column("Company")
    table.add_column("Title")
    table.add_column("Location")
    table.add_column("Top Matched Skills")
    table.add_column("Flags")

    for i, match in enumerate(matches, 1):
        score_color = "green" if match.final_score >= 70 else "yellow" if match.final_score >= 50 else "red"
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
