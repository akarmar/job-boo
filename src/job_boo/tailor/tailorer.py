"""Resume tailoring and cover letter generation."""

from __future__ import annotations

import re
from pathlib import Path

from rich.console import Console

from job_boo.ai.base import AIProvider
from job_boo.models import MatchResult, Resume

console = Console()


def _safe_filename(text: str) -> str:
    """Convert text to a safe filename."""
    return re.sub(r"[^\w\-]", "_", text.lower())[:50]


def tailor_for_job(
    resume: Resume,
    match: MatchResult,
    ai: AIProvider,
    output_dir: str,
    include_cover_letter: bool = True,
) -> tuple[str, str]:
    """Generate tailored resume and optional cover letter.

    Returns (resume_path, cover_letter_path).
    """
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)

    job = match.job
    slug = _safe_filename(f"{job.company}_{job.title}")

    # Tailor resume
    console.print(f"  Tailoring resume for [cyan]{job.company} - {job.title}[/cyan]...")
    tailored_text = ai.tailor_resume(resume, job, match)
    resume_path = out / f"resume_{slug}.txt"
    resume_path.write_text(tailored_text)
    console.print(f"  Saved: [green]{resume_path}[/green]")

    # Generate cover letter
    cover_path_str = ""
    if include_cover_letter:
        console.print("  Generating cover letter...")
        cover_text = ai.generate_cover_letter(resume, job, match)
        cover_path = out / f"cover_{slug}.txt"
        cover_path.write_text(cover_text)
        cover_path_str = str(cover_path)
        console.print(f"  Saved: [green]{cover_path}[/green]")

    return str(resume_path), cover_path_str
