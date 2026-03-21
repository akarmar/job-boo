"""Application submission — opens job URLs and tracks state."""

from __future__ import annotations

import time
import webbrowser
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from job_boo.models import Application, JobState, MatchResult
from job_boo.storage.db import JobDB

console = Console()


def submit_application(
    app: Application,
    db: JobDB,
    confirm: bool = True,
    delay: int = 5,
) -> bool:
    """Submit an application for a job.

    Currently opens the application URL in the browser and tracks state.
    Future: auto-fill ATS forms (Greenhouse, Lever, etc.)
    """
    job = app.job

    console.print(
        Panel(
            f"[bold]{job.title}[/bold] at [cyan]{job.company}[/cyan]\n"
            f"Location: {job.location}\n"
            f"Score: {app.match.final_score:.0f}%\n"
            f"Matched: {', '.join(app.match.matched_skills[:5])}\n"
            f"URL: {job.url}\n"
            + (
                f"\nTailored resume: {app.tailored_resume_path}"
                if app.tailored_resume_path
                else ""
            )
            + (
                f"\nCover letter: {app.cover_letter_path}"
                if app.cover_letter_path
                else ""
            ),
            title="Application",
        )
    )

    if not job.url:
        console.print("[red]  No application URL available. Skipping.[/red]")
        return False

    if confirm:
        proceed = Confirm.ask("  Open in browser and mark as applied?")
        if not proceed:
            console.print("  [yellow]Skipped.[/yellow]")
            if app.db_id:
                db.update_state(app.db_id, JobState.SKIPPED)
            return False

    # Open the application URL
    webbrowser.open(job.url)
    console.print("  [green]Opened in browser.[/green]")
    console.print(
        "  Apply using the tailored resume and cover letter saved in your output directory."
    )

    if app.db_id:
        db.update_state(
            app.db_id, JobState.APPLIED, applied_at=datetime.now().isoformat()
        )

    if delay > 0:
        time.sleep(delay)

    return True


def batch_apply(
    matches: list[MatchResult],
    db: JobDB,
    confirm: bool = True,
    delay: int = 5,
) -> int:
    """Apply to multiple jobs. Returns count of applications submitted."""
    delay = max(delay, 10)  # Minimum 10 seconds to avoid anti-bot triggers
    applied = 0
    total = len(matches)

    console.print(
        "[yellow]WARNING: Batch applying rapidly may trigger anti-bot defenses on job sites, "
        "potentially blocking your IP or flagging your applications.[/yellow]\n"
    )

    for i, match in enumerate(matches, 1):
        console.print(f"\n[bold]--- Application {i}/{total} ---[/bold]")

        row = None
        rows = db.get_jobs(min_score=0, limit=1000)
        for r in rows:
            if r["dedup_key"] == match.job.dedup_key():
                row = r
                break

        app = Application(
            job=match.job,
            match=match,
            state=JobState.READY,
            tailored_resume_path=row.get("tailored_resume_path", "") if row else "",
            cover_letter_path=row.get("cover_letter_path", "") if row else "",
            db_id=row["id"] if row else None,
        )

        if submit_application(app, db, confirm=confirm, delay=delay):
            applied += 1

    console.print(f"\n[bold green]Applied to {applied}/{total} jobs.[/bold green]")
    return applied
