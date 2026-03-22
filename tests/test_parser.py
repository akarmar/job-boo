"""Tests for resume PDF parsing."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import click
import pytest

from job_boo.models import Resume
from job_boo.resume.parser import (
    _load_cached_resume,
    _resume_cache_path,
    _save_resume_cache,
    extract_text_from_pdf,
    parse_resume,
)


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


class TestResumeCache:
    def test_cache_path_deterministic(self, tmp_path: Path) -> None:
        """Same file content produces same cache path."""
        pdf = tmp_path / "resume.pdf"
        pdf.write_bytes(b"fake pdf content")
        path1 = _resume_cache_path(str(pdf))
        path2 = _resume_cache_path(str(pdf))
        assert path1 == path2

    def test_cache_path_changes_with_content(self, tmp_path: Path) -> None:
        """Different file content produces different cache path."""
        pdf = tmp_path / "resume.pdf"
        pdf.write_bytes(b"version 1")
        path1 = _resume_cache_path(str(pdf))
        pdf.write_bytes(b"version 2")
        path2 = _resume_cache_path(str(pdf))
        assert path1 != path2

    def test_load_cached_resume_missing_file(self, tmp_path: Path) -> None:
        """Returns None when cache file doesn't exist."""
        result = _load_cached_resume(tmp_path / "nonexistent.json")
        assert result is None

    def test_load_cached_resume_invalid_json(self, tmp_path: Path) -> None:
        """Returns None when cache file contains invalid JSON."""
        bad_cache = tmp_path / "bad.json"
        bad_cache.write_text("not json")
        result = _load_cached_resume(bad_cache)
        assert result is None

    def test_load_cached_resume_missing_key(self, tmp_path: Path) -> None:
        """Returns None when cache file is missing required keys."""
        bad_cache = tmp_path / "incomplete.json"
        bad_cache.write_text(json.dumps({"skills": ["Python"]}))
        result = _load_cached_resume(bad_cache)
        assert result is None

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        """Saving then loading a resume produces equivalent data."""
        resume = Resume(
            raw_text="John Doe\nPython developer",
            skills=["Python", "AWS"],
            experience_years=10,
            job_titles=["Senior Developer"],
            education=["BS Computer Science"],
            summary="Experienced developer",
            source_path="/home/user/resume.pdf",
        )
        cache_path = tmp_path / "cache" / "resume_abc123.json"
        with patch("job_boo.resume.parser.CACHE_DIR", tmp_path / "cache"):
            _save_resume_cache(cache_path, resume)

        loaded = _load_cached_resume(cache_path)
        assert loaded is not None
        assert loaded.skills == ["Python", "AWS"]
        assert loaded.experience_years == 10
        assert loaded.job_titles == ["Senior Developer"]
        assert loaded.education == ["BS Computer Science"]
        assert loaded.summary == "Experienced developer"
        assert loaded.source_path == "/home/user/resume.pdf"
        assert loaded.raw_text == "John Doe\nPython developer"

    @patch("job_boo.resume.parser.extract_text_from_pdf")
    def test_parse_resume_uses_cache(self, mock_extract: MagicMock, tmp_path: Path) -> None:
        """parse_resume returns cached resume without calling AI."""
        pdf = tmp_path / "resume.pdf"
        pdf.write_bytes(b"fake pdf bytes")

        cached_resume = Resume(
            raw_text="cached text",
            skills=["Python"],
            experience_years=5,
            source_path=str(pdf),
        )
        cache_path = _resume_cache_path(str(pdf))

        with patch("job_boo.resume.parser.CACHE_DIR", tmp_path / "cache"):
            cache_dir = tmp_path / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            # Compute the real cache path using the tmp cache dir
            import hashlib

            content_hash = hashlib.md5(pdf.read_bytes()).hexdigest()[:12]
            real_cache_path = cache_dir / f"resume_{content_hash}.json"
            _save_resume_cache(real_cache_path, cached_resume)

            ai = MagicMock()
            resume = parse_resume(str(pdf), ai)

        # AI should NOT have been called
        ai.extract_skills.assert_not_called()
        # extract_text_from_pdf should NOT have been called
        mock_extract.assert_not_called()
        assert resume.skills == ["Python"]

    @patch("job_boo.resume.parser.extract_text_from_pdf")
    def test_parse_resume_no_cache_flag(self, mock_extract: MagicMock, tmp_path: Path) -> None:
        """parse_resume with use_cache=False skips cache."""
        pdf = tmp_path / "resume.pdf"
        pdf.write_bytes(b"fake pdf bytes")

        mock_extract.return_value = "Fresh text from PDF"
        ai = MagicMock()
        ai.extract_skills.return_value = Resume(
            raw_text="",
            skills=["Docker"],
            experience_years=3,
        )

        resume = parse_resume(str(pdf), ai, use_cache=False)
        ai.extract_skills.assert_called_once()
        assert resume.skills == ["Docker"]
