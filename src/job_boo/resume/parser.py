"""Resume PDF parsing and skill extraction."""

from __future__ import annotations

from pathlib import Path

import fitz  # pymupdf

from job_boo.ai.base import AIProvider
from job_boo.models import Resume


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """Extract all text from a PDF file."""
    path = Path(pdf_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Resume not found: {path}")

    doc = fitz.open(str(path))
    text_parts: list[str] = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts)


def parse_resume(pdf_path: str | Path, ai: AIProvider) -> Resume:
    """Parse a PDF resume and extract structured data using AI."""
    raw_text = extract_text_from_pdf(pdf_path)
    if not raw_text.strip():
        raise ValueError(f"No text extracted from {pdf_path}. Is it a scanned image?")

    resume = ai.extract_skills(raw_text)
    resume.source_path = str(pdf_path)
    resume.raw_text = raw_text
    return resume
