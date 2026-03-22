"""Resume PDF parsing and skill extraction."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import click
import fitz  # pymupdf

from job_boo.ai.base import AIProvider
from job_boo.ai.fallback import FallbackProvider
from job_boo.config import CONFIG_DIR
from job_boo.models import Resume

CACHE_DIR = CONFIG_DIR / "cache"

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """Extract all text from a PDF file."""
    path = Path(pdf_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Resume not found: {path}")

    try:
        doc = fitz.open(str(path))
    except Exception as e:
        raise ValueError(f"Cannot open PDF {path}: {e}") from e

    if doc.is_encrypted:
        doc.close()
        raise ValueError(
            f"PDF is encrypted/password-protected: {path}. "
            "Please provide an unprotected PDF."
        )

    text_parts: list[str] = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts)


def _resume_cache_path(pdf_path: str | Path) -> Path:
    """Get cache file path based on PDF content hash."""
    path = Path(pdf_path).expanduser()
    content_hash = hashlib.md5(path.read_bytes()).hexdigest()[:12]
    return CACHE_DIR / f"resume_{content_hash}.json"


def _load_cached_resume(cache_path: Path) -> Resume | None:
    """Load resume from cache if it exists."""
    if not cache_path.exists():
        return None
    try:
        data: dict[str, object] = json.loads(cache_path.read_text())
        return Resume(
            raw_text=str(data["raw_text"]),
            skills=list(data["skills"]),  # type: ignore[arg-type]
            experience_years=int(data["experience_years"]),  # type: ignore[arg-type]
            job_titles=list(data["job_titles"]),  # type: ignore[arg-type]
            education=list(data["education"]),  # type: ignore[arg-type]
            summary=str(data["summary"]),
            source_path=str(data["source_path"]),
        )
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.debug("Cache load failed, will re-parse: %s", e)
        return None


def _save_resume_cache(cache_path: Path, resume: Resume) -> None:
    """Save parsed resume to cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data: dict[str, object] = {
        "raw_text": resume.raw_text,
        "skills": resume.skills,
        "experience_years": resume.experience_years,
        "job_titles": resume.job_titles,
        "education": resume.education,
        "summary": resume.summary,
        "source_path": resume.source_path,
    }
    cache_path.write_text(json.dumps(data))


def parse_resume(
    pdf_path: str | Path,
    ai: AIProvider | FallbackProvider,
    *,
    use_cache: bool = True,
) -> Resume:
    """Parse a PDF resume and extract structured data using AI (or fallback).

    Results are cached based on the PDF content hash.  Pass ``use_cache=False``
    to force a fresh parse (e.g. ``--no-cache`` on the CLI).
    """
    if not pdf_path or str(pdf_path).strip() in ("", "."):
        raise click.ClickException(
            "No resume_path configured. Run 'job-boo init' to set it up."
        )

    # Check cache first (based on PDF content hash)
    if use_cache:
        try:
            cache_path = _resume_cache_path(pdf_path)
            cached = _load_cached_resume(cache_path)
            if cached:
                logger.info("Loaded resume from cache (hash-matched)")
                return cached
        except (OSError, ValueError) as e:
            logger.debug("Cache lookup failed, will parse fresh: %s", e)

    raw_text = extract_text_from_pdf(pdf_path)
    if not raw_text.strip():
        raise ValueError(f"No text extracted from {pdf_path}. Is it a scanned image?")

    try:
        resume = ai.extract_skills(raw_text)
    except json.JSONDecodeError as e:
        logger.warning("AI returned malformed JSON, using fallback: %s", e)
        fallback = FallbackProvider()
        resume = fallback.extract_skills(raw_text)
    except Exception as e:
        logger.warning(
            "AI extraction failed (%s: %s), using fallback",
            type(e).__name__,
            e,
        )
        fallback = FallbackProvider()
        resume = fallback.extract_skills(raw_text)

    resume.source_path = str(pdf_path)
    resume.raw_text = raw_text

    # Save to cache
    try:
        cache_path = _resume_cache_path(pdf_path)
        _save_resume_cache(cache_path, resume)
        logger.info("Saved resume to cache")
    except OSError as e:
        logger.debug("Failed to save resume cache: %s", e)

    return resume
