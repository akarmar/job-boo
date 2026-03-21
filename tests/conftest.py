"""Shared fixtures for job-boo test suite."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Generator

import pytest

from job_boo.config import Config, LocationConfig, SalaryConfig, AIConfig, SourcesConfig, CompaniesConfig
from job_boo.models import Job, Resume, MatchResult, Application, JobState
from job_boo.storage.db import JobDB


@pytest.fixture
def sample_job() -> Job:
    """A typical job listing for testing."""
    return Job(
        title="Senior Software Engineer",
        company="Acme Corp",
        location="Remote",
        description="We need a senior engineer with Python, AWS, and Kubernetes experience.",
        url="https://acme.com/jobs/123",
        source="adzuna",
        salary_min=150000,
        salary_max=200000,
        remote=True,
        posted_date="2026-01-15",
        job_id="acme-123",
    )


@pytest.fixture
def sample_resume() -> Resume:
    """A typical parsed resume for testing."""
    return Resume(
        raw_text="Experienced software engineer with 8 years of experience in Python, AWS, Docker.",
        skills=["Python", "AWS", "Docker", "Kubernetes", "PostgreSQL", "Go"],
        experience_years=8,
        job_titles=["Senior Software Engineer", "Software Engineer"],
        education=["BS in Computer Science"],
        summary="Senior engineer with cloud infrastructure expertise.",
        source_path="/tmp/resume.pdf",
    )


@pytest.fixture
def sample_match(sample_job: Job) -> MatchResult:
    """A typical match result for testing."""
    return MatchResult(
        job=sample_job,
        keyword_score=75.0,
        ai_score=80.0,
        final_score=78.5,
        matched_skills=["Python", "AWS", "Kubernetes"],
        missing_skills=["Terraform"],
        reasoning="Strong match with relevant cloud experience.",
    )


@pytest.fixture
def sample_application(sample_job: Job, sample_match: MatchResult) -> Application:
    """A typical application for testing."""
    return Application(
        job=sample_job,
        match=sample_match,
        state=JobState.READY,
        db_id=1,
    )


@pytest.fixture
def tmp_db(tmp_path: Path) -> Generator[JobDB, None, None]:
    """Provide a temporary JobDB instance backed by a temp SQLite file."""
    db_path = tmp_path / "test_jobs.db"
    db = JobDB(db_path=db_path)
    yield db
    db.close()


@pytest.fixture
def config_with_profiles() -> Config:
    """Config with test profiles defined."""
    return Config(
        job_title="Software Engineer",
        keywords=["python", "backend"],
        profiles={
            "frontend": {
                "job_title": "Frontend Developer",
                "keywords": ["react", "typescript"],
                "resume_path": "/tmp/frontend_resume.pdf",
            },
            "data": {
                "job_title": "Data Engineer",
                "keywords": ["spark", "airflow"],
            },
        },
    )


@pytest.fixture
def minimal_config() -> Config:
    """Minimal config with defaults."""
    return Config()


@pytest.fixture
def config_with_blacklist() -> Config:
    """Config with company blacklist."""
    return Config(
        companies=CompaniesConfig(
            blacklist=["Evil Corp", "Spam Inc"],
        ),
    )
