"""Tests for SQLite storage layer."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from job_boo.models import Job, JobState, MatchResult
from job_boo.storage.db import JobDB


class TestJobDBInit:
    def test_creates_db_file(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        db = JobDB(db_path=db_path)
        assert db_path.exists()
        db.close()

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        db_path = tmp_path / "sub" / "dir" / "test.db"
        db = JobDB(db_path=db_path)
        assert db_path.exists()
        db.close()

    def test_schema_created(self, tmp_db: JobDB) -> None:
        # Check that the jobs table exists
        row = tmp_db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'"
        ).fetchone()
        assert row is not None


class TestJobDBContextManager:
    def test_context_manager_opens_and_closes(self, tmp_path: Path) -> None:
        db_path = tmp_path / "ctx.db"
        with JobDB(db_path=db_path) as db:
            assert db.conn is not None
            db.upsert_job(
                Job(title="T", company="C", location="L", description="D", url="U", source="S")
            )
        # After context exit, connection should be closed
        # Attempting to use it should raise
        with pytest.raises(Exception):
            db.conn.execute("SELECT 1")


class TestUpsertJob:
    def test_insert_new_job(self, tmp_db: JobDB, sample_job: Job) -> None:
        row_id = tmp_db.upsert_job(sample_job)
        assert row_id > 0

    def test_upsert_same_dedup_key_updates(self, tmp_db: JobDB) -> None:
        job1 = Job(
            title="Engineer", company="Google", location="NYC",
            description="Old desc", url="https://old.com", source="test",
        )
        job2 = Job(
            title="Engineer", company="Google", location="NYC",
            description="New desc", url="https://new.com", source="test",
        )
        id1 = tmp_db.upsert_job(job1)
        id2 = tmp_db.upsert_job(job2)
        # Same dedup key -> same row updated
        row = tmp_db.get_job_by_dedup_key(job1.dedup_key())
        assert row is not None
        assert row["description"] == "New desc"
        assert row["url"] == "https://new.com"

    def test_different_dedup_keys_create_separate_rows(self, tmp_db: JobDB) -> None:
        job1 = Job(title="Engineer", company="Google", location="", description="", url="", source="test")
        job2 = Job(title="Manager", company="Google", location="", description="", url="", source="test")
        id1 = tmp_db.upsert_job(job1)
        id2 = tmp_db.upsert_job(job2)
        assert id1 != id2

    def test_raw_data_serialized(self, tmp_db: JobDB) -> None:
        job = Job(
            title="T", company="C", location="L", description="D",
            url="U", source="S", raw_data={"key": "value", "nested": [1, 2]},
        )
        tmp_db.upsert_job(job)
        row = tmp_db.get_job_by_dedup_key(job.dedup_key())
        assert row is not None
        parsed = json.loads(row["raw_data"])
        assert parsed["key"] == "value"


class TestBatch:
    def test_batch_commits_on_success(self, tmp_db: JobDB) -> None:
        with tmp_db.batch():
            for i in range(5):
                tmp_db.upsert_job(
                    Job(title=f"Job {i}", company=f"Co {i}", location="", description="", url="", source="test")
                )
        jobs = tmp_db.get_all_jobs()
        assert len(jobs) == 5

    def test_batch_rollback_on_error(self, tmp_db: JobDB) -> None:
        try:
            with tmp_db.batch():
                tmp_db.upsert_job(
                    Job(title="OK", company="Co", location="", description="", url="", source="test")
                )
                raise ValueError("Simulated error")
        except ValueError:
            pass
        jobs = tmp_db.get_all_jobs()
        assert len(jobs) == 0

    def test_batch_flag_reset_after_error(self, tmp_db: JobDB) -> None:
        try:
            with tmp_db.batch():
                raise ValueError("err")
        except ValueError:
            pass
        assert tmp_db._in_batch is False


class TestUpdateScore:
    def test_update_score(self, tmp_db: JobDB, sample_job: Job, sample_match: MatchResult) -> None:
        tmp_db.upsert_job(sample_job)
        tmp_db.update_score(sample_job.dedup_key(), sample_match)
        row = tmp_db.get_job_by_dedup_key(sample_job.dedup_key())
        assert row is not None
        assert row["keyword_score"] == 75.0
        assert row["ai_score"] == 80.0
        assert row["final_score"] == 78.5
        assert row["state"] == "scored"
        assert json.loads(row["matched_skills"]) == ["Python", "AWS", "Kubernetes"]


class TestUpdateState:
    def test_update_state_to_applied(self, tmp_db: JobDB, sample_job: Job) -> None:
        row_id = tmp_db.upsert_job(sample_job)
        now = datetime.now().isoformat()
        tmp_db.update_state(row_id, JobState.APPLIED, applied_at=now)
        row = tmp_db.get_job_by_id(row_id)
        assert row is not None
        assert row["state"] == "applied"
        assert row["applied_at"] == now

    def test_update_state_preserves_existing_fields(self, tmp_db: JobDB, sample_job: Job) -> None:
        row_id = tmp_db.upsert_job(sample_job)
        tmp_db.update_state(row_id, JobState.TAILORED, tailored_resume_path="/tmp/resume.txt")
        tmp_db.update_state(row_id, JobState.APPLIED, applied_at="2026-01-01T00:00:00")
        row = tmp_db.get_job_by_id(row_id)
        assert row is not None
        assert row["tailored_resume_path"] == "/tmp/resume.txt"


class TestUpdateNotes:
    def test_update_notes(self, tmp_db: JobDB, sample_job: Job) -> None:
        row_id = tmp_db.upsert_job(sample_job)
        tmp_db.update_notes(row_id, "Had a good phone screen")
        row = tmp_db.get_job_by_id(row_id)
        assert row is not None
        assert row["notes"] == "Had a good phone screen"


class TestGetJobs:
    def test_get_jobs_by_state(self, tmp_db: JobDB, sample_job: Job, sample_match: MatchResult) -> None:
        tmp_db.upsert_job(sample_job)
        tmp_db.update_score(sample_job.dedup_key(), sample_match)
        jobs = tmp_db.get_jobs(state=JobState.SCORED)
        assert len(jobs) == 1

    def test_get_jobs_by_min_score(self, tmp_db: JobDB, sample_job: Job, sample_match: MatchResult) -> None:
        tmp_db.upsert_job(sample_job)
        tmp_db.update_score(sample_job.dedup_key(), sample_match)
        # Score is 78.5 — should be found with min_score=70
        jobs = tmp_db.get_jobs(min_score=70)
        assert len(jobs) == 1
        # Should not be found with min_score=80
        jobs = tmp_db.get_jobs(min_score=80)
        assert len(jobs) == 0

    def test_get_jobs_limit(self, tmp_db: JobDB) -> None:
        for i in range(10):
            tmp_db.upsert_job(
                Job(title=f"Job {i}", company=f"Co {i}", location="", description="", url="", source="test")
            )
        jobs = tmp_db.get_jobs(limit=3)
        assert len(jobs) == 3

    def test_get_jobs_empty_db(self, tmp_db: JobDB) -> None:
        jobs = tmp_db.get_jobs()
        assert jobs == []


class TestGetJobByDedupKey:
    def test_found(self, tmp_db: JobDB, sample_job: Job) -> None:
        tmp_db.upsert_job(sample_job)
        row = tmp_db.get_job_by_dedup_key(sample_job.dedup_key())
        assert row is not None
        assert row["title"] == "Senior Software Engineer"

    def test_not_found(self, tmp_db: JobDB) -> None:
        row = tmp_db.get_job_by_dedup_key("nonexistent|key")
        assert row is None


class TestGetStats:
    def test_empty_db(self, tmp_db: JobDB) -> None:
        stats = tmp_db.get_stats()
        assert stats == {}

    def test_stats_counts(self, tmp_db: JobDB) -> None:
        for i in range(3):
            tmp_db.upsert_job(
                Job(title=f"Job {i}", company=f"Co {i}", location="", description="", url="", source="test")
            )
        stats = tmp_db.get_stats()
        assert stats["found"] == 3


class TestGetAllDedupKeys:
    def test_returns_all_keys(self, tmp_db: JobDB) -> None:
        for i in range(3):
            tmp_db.upsert_job(
                Job(title=f"Job {i}", company=f"Co {i}", location="", description="", url="", source="test")
            )
        keys = tmp_db.get_all_dedup_keys()
        assert len(keys) == 3


class TestCleanupExpired:
    def test_cleanup_does_not_delete_recent(self, tmp_db: JobDB) -> None:
        tmp_db.upsert_job(
            Job(title="Recent", company="Co", location="", description="", url="", source="test")
        )
        deleted = tmp_db.cleanup_expired(days=90)
        assert deleted == 0

    def test_cleanup_deletes_old_found_jobs(self, tmp_db: JobDB) -> None:
        tmp_db.upsert_job(
            Job(title="Old", company="Co", location="", description="", url="", source="test")
        )
        # Manually backdate the updated_at
        tmp_db.conn.execute(
            "UPDATE jobs SET updated_at = datetime('now', '-100 days') WHERE title = 'Old'"
        )
        tmp_db.conn.commit()
        deleted = tmp_db.cleanup_expired(days=90)
        assert deleted == 1

    def test_cleanup_does_not_delete_applied_jobs(self, tmp_db: JobDB) -> None:
        row_id = tmp_db.upsert_job(
            Job(title="Applied", company="Co", location="", description="", url="", source="test")
        )
        tmp_db.update_state(row_id, JobState.APPLIED)
        tmp_db.conn.execute(
            "UPDATE jobs SET updated_at = datetime('now', '-100 days') WHERE title = 'Applied'"
        )
        tmp_db.conn.commit()
        deleted = tmp_db.cleanup_expired(days=90)
        assert deleted == 0


class TestRowToJob:
    def test_converts_row_to_job(self, tmp_db: JobDB, sample_job: Job) -> None:
        tmp_db.upsert_job(sample_job)
        row = tmp_db.get_job_by_dedup_key(sample_job.dedup_key())
        assert row is not None
        job = tmp_db.row_to_job(row)
        assert job.title == "Senior Software Engineer"
        assert job.company == "Acme Corp"
        assert job.remote is True

    def test_handles_none_fields(self, tmp_db: JobDB) -> None:
        tmp_db.upsert_job(
            Job(title="T", company="C", location="", description="", url="", source="")
        )
        row = tmp_db.get_job_by_dedup_key("c|t")
        assert row is not None
        job = tmp_db.row_to_job(row)
        assert job.location == ""
        assert job.raw_data == {}


class TestRowToMatch:
    def test_converts_row_to_match(self, tmp_db: JobDB, sample_job: Job, sample_match: MatchResult) -> None:
        tmp_db.upsert_job(sample_job)
        tmp_db.update_score(sample_job.dedup_key(), sample_match)
        row = tmp_db.get_job_by_dedup_key(sample_job.dedup_key())
        assert row is not None
        match = tmp_db.row_to_match(row)
        assert match.keyword_score == 75.0
        assert match.matched_skills == ["Python", "AWS", "Kubernetes"]


class TestGetCompanyHistory:
    def test_empty_db(self, tmp_db: JobDB) -> None:
        history = tmp_db.get_company_history()
        assert history == []

    def test_with_data(self, tmp_db: JobDB, sample_job: Job) -> None:
        tmp_db.upsert_job(sample_job)
        history = tmp_db.get_company_history()
        assert len(history) == 1
        assert history[0]["company"] == "Acme Corp"

    def test_filter_by_company(self, tmp_db: JobDB) -> None:
        tmp_db.upsert_job(
            Job(title="E1", company="Google", location="", description="", url="", source="test")
        )
        tmp_db.upsert_job(
            Job(title="E2", company="Meta", location="", description="", url="", source="test")
        )
        history = tmp_db.get_company_history(company="Google")
        assert len(history) == 1


class TestGetSourceStats:
    def test_source_stats(self, tmp_db: JobDB) -> None:
        for i in range(3):
            tmp_db.upsert_job(
                Job(title=f"J{i}", company=f"C{i}", location="", description="", url="", source="adzuna")
            )
        tmp_db.upsert_job(
            Job(title="J3", company="C3", location="", description="", url="", source="remotive")
        )
        stats = tmp_db.get_source_stats()
        assert len(stats) == 2
        assert stats[0]["source"] == "adzuna"
        assert stats[0]["count"] == 3


class TestGetScoreDistribution:
    def test_score_distribution(self, tmp_db: JobDB) -> None:
        for i, score in enumerate([10, 30, 50, 70, 90]):
            job = Job(title=f"J{i}", company=f"C{i}", location="", description="", url="", source="test")
            tmp_db.upsert_job(job)
            match = MatchResult(
                job=job, keyword_score=score, ai_score=score, final_score=float(score)
            )
            tmp_db.update_score(job.dedup_key(), match)
        dist = tmp_db.get_score_distribution()
        assert len(dist) == 5
