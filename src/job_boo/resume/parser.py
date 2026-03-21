"""Resume PDF parsing and skill extraction."""

from __future__ import annotations

import json
from pathlib import Path
import click
import fitz  # pymupdf

from job_boo.ai.base import AIProvider
from job_boo.ai.fallback import FallbackProvider
from job_boo.models import Resume


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


def parse_resume(
    pdf_path: str | Path,
    ai: AIProvider | FallbackProvider,
) -> Resume:
    """Parse a PDF resume and extract structured data using AI (or fallback)."""
    if not pdf_path or str(pdf_path).strip() in ("", "."):
        raise click.ClickException(
            "No resume_path configured. Run 'job-boo init' to set it up."
        )

    raw_text = extract_text_from_pdf(pdf_path)
    if not raw_text.strip():
        raise ValueError(f"No text extracted from {pdf_path}. Is it a scanned image?")

    try:
        resume = ai.extract_skills(raw_text)
    except json.JSONDecodeError as e:
        import logging

        logging.warning(f"AI returned malformed JSON, using fallback: {e}")
        fallback = FallbackProvider()
        resume = fallback.extract_skills(raw_text)
    except Exception as e:
        import logging

        logging.warning(
            f"AI extraction failed ({type(e).__name__}: {e}), using fallback"
        )
        fallback = FallbackProvider()
        resume = fallback.extract_skills(raw_text)

    resume.source_path = str(pdf_path)
    resume.raw_text = raw_text
    return resume
