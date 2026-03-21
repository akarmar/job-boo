"""Tests for core data models."""

from __future__ import annotations

from datetime import datetime

from job_boo.models import Job, Resume, MatchResult, Application, JobState, LocationPref


class TestJobState:
    def test_values(self) -> None:
        assert JobState.FOUND.value == "found"
        assert JobState.APPLIED.value == "applied"
        assert JobState.SKIPPED.value == "skipped"

    def test_is_str_enum(self) -> None:
        assert isinstance(JobState.FOUND, str)
        assert JobState.FOUND == "found"


class TestLocationPref:
    def test_values(self) -> None:
        assert LocationPref.REMOTE.value == "remote"
        assert LocationPref.HYBRID.value == "hybrid"
        assert LocationPref.ONSITE.value == "onsite"


class TestJob:
    def test_basic_creation(self, sample_job: Job) -> None:
        assert sample_job.title == "Senior Software Engineer"
        assert sample_job.company == "Acme Corp"
        assert sample_job.remote is True

    def test_description_truncation_at_5000(self) -> None:
        long_desc = "x" * 6000
        job = Job(
            title="Test",
            company="Co",
            location="NYC",
            description=long_desc,
            url="https://example.com",
            source="test",
        )
        assert len(job.description) == 5000

    def test_description_under_5000_unchanged(self) -> None:
        desc = "Short description"
        job = Job(
            title="Test",
            company="Co",
            location="NYC",
            description=desc,
            url="https://example.com",
            source="test",
        )
        assert job.description == desc

    def test_description_exactly_5000(self) -> None:
        desc = "a" * 5000
        job = Job(
            title="Test",
            company="Co",
            location="NYC",
            description=desc,
            url="https://example.com",
            source="test",
        )
        assert len(job.description) == 5000

    def test_dedup_key_normalization(self) -> None:
        job = Job(
            title="  Senior Engineer  ",
            company="  ACME Corp  ",
            location="",
            description="",
            url="",
            source="test",
        )
        assert job.dedup_key() == "acme corp|senior engineer"

    def test_dedup_key_special_characters(self) -> None:
        job = Job(
            title="C++ Developer",
            company="O'Reilly & Associates",
            location="",
            description="",
            url="",
            source="test",
        )
        key = job.dedup_key()
        assert "o'reilly & associates" in key
        assert "c++ developer" in key

    def test_dedup_key_case_insensitive(self) -> None:
        job1 = Job(title="Engineer", company="GOOGLE", location="", description="", url="", source="test")
        job2 = Job(title="engineer", company="google", location="", description="", url="", source="test")
        assert job1.dedup_key() == job2.dedup_key()

    def test_default_values(self) -> None:
        job = Job(title="T", company="C", location="L", description="D", url="U", source="S")
        assert job.salary_min == 0
        assert job.salary_max == 0
        assert job.remote is False
        assert job.sponsorship_available is None
        assert job.posted_date == ""
        assert job.job_id == ""
        assert job.raw_data == {}


class TestResume:
    def test_default_values(self) -> None:
        resume = Resume(raw_text="some text")
        assert resume.skills == []
        assert resume.experience_years == 0
        assert resume.job_titles == []
        assert resume.education == []
        assert resume.summary == ""
        assert resume.source_path == ""


class TestMatchResult:
    def test_default_values(self, sample_job: Job) -> None:
        match = MatchResult(job=sample_job, keyword_score=50, ai_score=60, final_score=55)
        assert match.matched_skills == []
        assert match.missing_skills == []
        assert match.reasoning == ""
        assert match.location_fit is True
        assert match.sponsorship_fit is True


class TestApplication:
    def test_default_state(self, sample_job: Job, sample_match: MatchResult) -> None:
        app = Application(job=sample_job, match=sample_match)
        assert app.state == JobState.FOUND
        assert app.tailored_resume_path == ""
        assert app.cover_letter_path == ""
        assert app.applied_at is None
        assert app.notes == ""
        assert app.db_id is None
