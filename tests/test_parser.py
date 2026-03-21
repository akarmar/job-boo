"""Tests for resume PDF parsing."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import click
import pytest

from job_boo.models import Resume
from job_boo.resume.parser import extract_text_from_pdf, parse_resume


class TestExtractTextFromPdf:
    def test_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError, match="Resume not found"):
            extract_text_from_pdf("/nonexistent/resume.pdf")

    @patch("job_boo.resume.parser.fitz.open")
    def test_encrypted_pdf_raises(self, mock_fitz_open: MagicMock, tmp_path: Path) -> None:
        pdf_path = tmp_path / "encrypted.pdf"
        pdf_path.write_bytes(b"fake pdf")

        mock_doc = MagicMock()
        mock_doc.is_encrypted = True
        mock_fitz_open.return_value = mock_doc

        with pytest.raises(ValueError, match="encrypted"):
            extract_text_from_pdf(str(pdf_path))
        mock_doc.close.assert_called_once()

    @patch("job_boo.resume.parser.fitz.open")
    def test_successful_extraction(self, mock_fitz_open: MagicMock, tmp_path: Path) -> None:
        pdf_path = tmp_path / "resume.pdf"
        pdf_path.write_bytes(b"fake pdf")

        mock_page1 = MagicMock()
        mock_page1.get_text.return_value = "Page 1 content"
        mock_page2 = MagicMock()
        mock_page2.get_text.return_value = "Page 2 content"

        mock_doc = MagicMock()
        mock_doc.is_encrypted = False
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page1, mock_page2]))
        mock_fitz_open.return_value = mock_doc

        text = extract_text_from_pdf(str(pdf_path))
        assert "Page 1 content" in text
        assert "Page 2 content" in text
        mock_doc.close.assert_called_once()

    @patch("job_boo.resume.parser.fitz.open")
    def test_fitz_open_exception(self, mock_fitz_open: MagicMock, tmp_path: Path) -> None:
        pdf_path = tmp_path / "bad.pdf"
        pdf_path.write_bytes(b"not a pdf")
        mock_fitz_open.side_effect = RuntimeError("Cannot parse")

        with pytest.raises(ValueError, match="Cannot open PDF"):
            extract_text_from_pdf(str(pdf_path))


class TestParseResume:
    def test_empty_path_raises(self) -> None:
        ai = MagicMock()
        with pytest.raises(click.ClickException, match="No resume_path"):
            parse_resume("", ai)

    def test_dot_path_raises(self) -> None:
        ai = MagicMock()
        with pytest.raises(click.ClickException, match="No resume_path"):
            parse_resume(".", ai)

    def test_whitespace_path_raises(self) -> None:
        ai = MagicMock()
        with pytest.raises(click.ClickException, match="No resume_path"):
            parse_resume("   ", ai)

    @patch("job_boo.resume.parser.extract_text_from_pdf")
    def test_no_text_extracted_raises(self, mock_extract: MagicMock) -> None:
        mock_extract.return_value = "   \n   "
        ai = MagicMock()
        with pytest.raises(ValueError, match="No text extracted"):
            parse_resume("/tmp/resume.pdf", ai)

    @patch("job_boo.resume.parser.extract_text_from_pdf")
    def test_successful_parse(self, mock_extract: MagicMock) -> None:
        mock_extract.return_value = "John Doe\nSenior Python developer with 10 years experience."
        ai = MagicMock()
        ai.extract_skills.return_value = Resume(
            raw_text="",
            skills=["Python"],
            experience_years=10,
        )
        resume = parse_resume("/tmp/resume.pdf", ai)
        assert resume.skills == ["Python"]
        assert resume.source_path == "/tmp/resume.pdf"
        # raw_text should be overwritten with extracted text
        assert "John Doe" in resume.raw_text

    @patch("job_boo.resume.parser.extract_text_from_pdf")
    def test_json_decode_error_uses_fallback(self, mock_extract: MagicMock) -> None:
        mock_extract.return_value = "Python developer with AWS and Docker experience"
        ai = MagicMock()
        ai.extract_skills.side_effect = json.JSONDecodeError("err", "doc", 0)

        resume = parse_resume("/tmp/resume.pdf", ai)
        # Fallback should still produce a resume
        assert isinstance(resume, Resume)
        assert resume.source_path == "/tmp/resume.pdf"

    @patch("job_boo.resume.parser.extract_text_from_pdf")
    def test_generic_ai_error_uses_fallback(self, mock_extract: MagicMock) -> None:
        mock_extract.return_value = "Python developer experienced with Kubernetes"
        ai = MagicMock()
        ai.extract_skills.side_effect = RuntimeError("API timeout")

        resume = parse_resume("/tmp/resume.pdf", ai)
        assert isinstance(resume, Resume)
        assert resume.source_path == "/tmp/resume.pdf"
