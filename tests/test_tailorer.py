"""Tests for resume tailoring."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from job_boo.models import Job, MatchResult, Resume
from job_boo.tailor.tailorer import _safe_filename, tailor_for_job


class TestSafeFilename:
    def test_basic(self) -> None:
        assert _safe_filename("Acme Corp_Engineer") == "acme_corp_engineer"

    def test_special_chars_replaced(self) -> None:
        result = _safe_filename("O'Reilly & Co / Senior Dev!")
        assert "'" not in result
        assert "&" not in result
        assert "/" not in result

    def test_truncated_to_50(self) -> None:
        result = _safe_filename("a" * 100)
        assert len(result) == 50

    def test_empty_string(self) -> None:
        result = _safe_filename("")
        assert result == ""


class TestTailorForJob:
    def test_creates_resume_file(self, tmp_path: Path) -> None:
        ai = MagicMock()
        ai.tailor_resume.return_value = "Tailored resume content"
        ai.generate_cover_letter.return_value = "Cover letter content"

        resume = Resume(raw_text="Original resume", skills=["Python"])
        job = Job(
            title="Engineer", company="Acme", location="", description="",
            url="", source="test",
        )
        match = MatchResult(job=job, keyword_score=80, ai_score=85, final_score=82.5)

        resume_path, cover_path = tailor_for_job(
            resume, match, ai, str(tmp_path), include_cover_letter=True
        )
        assert Path(resume_path).exists()
        assert Path(cover_path).exists()
        assert Path(resume_path).read_text() == "Tailored resume content"
        assert Path(cover_path).read_text() == "Cover letter content"

    def test_no_cover_letter(self, tmp_path: Path) -> None:
        ai = MagicMock()
        ai.tailor_resume.return_value = "Tailored"

        resume = Resume(raw_text="Resume", skills=[])
        job = Job(title="Dev", company="Co", location="", description="", url="", source="test")
        match = MatchResult(job=job, keyword_score=50, ai_score=50, final_score=50)

        resume_path, cover_path = tailor_for_job(
            resume, match, ai, str(tmp_path), include_cover_letter=False
        )
        assert Path(resume_path).exists()
        assert cover_path == ""
        ai.generate_cover_letter.assert_not_called()

    def test_creates_output_dir(self, tmp_path: Path) -> None:
        ai = MagicMock()
        ai.tailor_resume.return_value = "Content"
        output_dir = tmp_path / "new" / "subdir"

        resume = Resume(raw_text="Resume", skills=[])
        job = Job(title="Dev", company="Co", location="", description="", url="", source="test")
        match = MatchResult(job=job, keyword_score=50, ai_score=50, final_score=50)

        tailor_for_job(resume, match, ai, str(output_dir), include_cover_letter=False)
        assert output_dir.exists()
