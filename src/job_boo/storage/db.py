"""SQLite storage for job tracking and application state."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from job_boo.config import DB_PATH
from job_boo.models import Job, JobState, MatchResult


SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    description TEXT,
    url TEXT,
    source TEXT,
    salary_min INTEGER DEFAULT 0,
    salary_max INTEGER DEFAULT 0,
    remote BOOLEAN DEFAULT 0,
    sponsorship_available INTEGER,  -- NULL = unknown
    posted_date TEXT,
    job_id TEXT,
    dedup_key TEXT UNIQUE,
    raw_data TEXT,
    -- scoring
    keyword_score REAL DEFAULT 0,
    ai_score REAL DEFAULT 0,
    final_score REAL DEFAULT 0,
    matched_skills TEXT,
    missing_skills TEXT,
    reasoning TEXT,
    location_fit BOOLEAN DEFAULT 1,
    sponsorship_fit BOOLEAN DEFAULT 1,
    -- state
    state TEXT DEFAULT 'found',
    tailored_resume_path TEXT,
    cover_letter_path TEXT,
    applied_at TEXT,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_jobs_state ON jobs(state);
CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(final_score DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_dedup ON jobs(dedup_key);
"""


class JobDB:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        if sys.platform != "win32":
            os.chmod(self.db_path, 0o600)
        self._in_batch: bool = False
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def __enter__(self) -> JobDB:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        self.close()

    def close(self) -> None:
        self.conn.close()

    @contextmanager
    def batch(self) -> Generator[None, None, None]:
        """Batch multiple operations into a single transaction."""
        self._in_batch = True
        try:
            yield
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            self._in_batch = False

    def upsert_job(self, job: Job) -> int:
        """Insert or update a job. Returns the row ID."""
        cursor = self.conn.execute(
            """INSERT INTO jobs (title, company, location, description, url, source,
                salary_min, salary_max, remote, sponsorship_available, posted_date,
                job_id, dedup_key, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(dedup_key) DO UPDATE SET
                description = excluded.description,
                url = excluded.url,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                job.title,
                job.company,
                job.location,
                job.description,
                job.url,
                job.source,
                job.salary_min,
                job.salary_max,
                job.remote,
                job.sponsorship_available,
                job.posted_date,
                job.job_id,
                job.dedup_key(),
                json.dumps(job.raw_data),
            ),
        )
        if not self._in_batch:
            self.conn.commit()
        return cursor.lastrowid or 0

    def update_score(self, dedup_key: str, match: MatchResult) -> None:
        self.conn.execute(
            """UPDATE jobs SET
                keyword_score = ?, ai_score = ?, final_score = ?,
                matched_skills = ?, missing_skills = ?, reasoning = ?,
                location_fit = ?, sponsorship_fit = ?,
                state = ?, updated_at = CURRENT_TIMESTAMP
            WHERE dedup_key = ?""",
            (
                match.keyword_score,
                match.ai_score,
                match.final_score,
                json.dumps(match.matched_skills),
                json.dumps(match.missing_skills),
                match.reasoning,
                match.location_fit,
                match.sponsorship_fit,
                JobState.SCORED.value,
                dedup_key,
            ),
        )
        if not self._in_batch:
            self.conn.commit()

    def update_state(self, db_id: int, state: JobState, **kwargs: str) -> None:
        self.conn.execute(
            """UPDATE jobs SET
                state = ?,
                tailored_resume_path = COALESCE(?, tailored_resume_path),
                cover_letter_path = COALESCE(?, cover_letter_path),
                applied_at = COALESCE(?, applied_at),
                notes = COALESCE(?, notes),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?""",
            (
                state.value,
                kwargs.get("tailored_resume_path"),
                kwargs.get("cover_letter_path"),
                kwargs.get("applied_at"),
                kwargs.get("notes"),
                db_id,
            ),
        )
        if not self._in_batch:
            self.conn.commit()

    def update_notes(self, db_id: int, notes: str) -> None:
        self.conn.execute(
            "UPDATE jobs SET notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (notes, db_id),
        )
        if not self._in_batch:
            self.conn.commit()

    def get_jobs(
        self,
        state: JobState | None = None,
        min_score: float = 0,
        limit: int = 100,
    ) -> list[dict]:
        query = "SELECT * FROM jobs WHERE final_score >= ?"
        params: list[float | str | int] = [min_score]
        if state:
            query += " AND state = ?"
            params.append(state.value)
        query += " ORDER BY final_score DESC LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get_job_by_id(self, db_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM jobs WHERE id = ?", (db_id,)).fetchone()
        return dict(row) if row else None

    def get_job_by_dedup_key(self, dedup_key: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM jobs WHERE dedup_key = ?", (dedup_key,)
        ).fetchone()
        return dict(row) if row else None

    def get_stats(self) -> dict[str, int]:
        rows = self.conn.execute(
            "SELECT state, COUNT(*) as cnt FROM jobs GROUP BY state"
        ).fetchall()
        return {row["state"]: row["cnt"] for row in rows}

    def get_all_dedup_keys(self) -> set[str]:
        """Return all dedup_key values in the database."""
        rows = self.conn.execute("SELECT dedup_key FROM jobs").fetchall()
        return {row["dedup_key"] for row in rows}

    def get_all_jobs(self, limit: int = 10000) -> list[dict]:
        """Return all jobs regardless of score."""
        rows = self.conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]

    def get_applied_per_day(self, days: int = 30) -> list[dict[str, str | int]]:
        """Return count of jobs applied per day for the last N days."""
        rows = self.conn.execute(
            """SELECT DATE(applied_at) as day, COUNT(*) as cnt
            FROM jobs
            WHERE state = 'applied' AND applied_at IS NOT NULL
                AND DATE(applied_at) >= DATE('now', ?)
            GROUP BY DATE(applied_at)
            ORDER BY day""",
            (f"-{days} days",),
        ).fetchall()
        return [{"day": row["day"], "count": row["cnt"]} for row in rows]

    def cleanup_expired(self, days: int = 90) -> int:
        """Delete jobs in 'found' or 'scored' state not updated in N days."""
        cursor = self.conn.execute(
            """DELETE FROM jobs
            WHERE state IN ('found', 'scored')
                AND DATE(updated_at) < DATE('now', ?)""",
            (f"-{days} days",),
        )
        self.conn.commit()
        return cursor.rowcount

    def get_company_history(self, company: str | None = None) -> list[dict]:
        """Get application history grouped by company."""
        query = """
            SELECT company,
                COUNT(*) as job_count,
                SUM(CASE WHEN state = 'applied' THEN 1 ELSE 0 END) as applied_count,
                ROUND(AVG(final_score), 2) as avg_score,
                MAX(CASE WHEN state = 'applied' THEN applied_at END) as latest_applied_at,
                GROUP_CONCAT(DISTINCT state) as states
            FROM jobs
        """
        params: list[str] = []
        if company:
            query += " WHERE LOWER(company) = LOWER(?)"
            params.append(company)
        query += " GROUP BY company ORDER BY job_count DESC"
        rows = self.conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get_jobs_by_date_range(
        self,
        start_date: str,
        end_date: str,
        state: str | None = None,
    ) -> list[dict]:
        """Get jobs created or applied within a date range (ISO format)."""
        query = """
            SELECT * FROM jobs
            WHERE (DATE(created_at) BETWEEN ? AND ?
                OR DATE(applied_at) BETWEEN ? AND ?)
        """
        params: list[str] = [start_date, end_date, start_date, end_date]
        if state:
            query += " AND state = ?"
            params.append(state)
        query += " ORDER BY created_at DESC"
        rows = self.conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get_source_stats(self) -> list[dict]:
        """Count of jobs per source."""
        rows = self.conn.execute(
            """SELECT source, COUNT(*) as count
            FROM jobs
            GROUP BY source
            ORDER BY count DESC"""
        ).fetchall()
        return [dict(row) for row in rows]

    def get_score_distribution(self) -> list[dict]:
        """Count of jobs in score buckets: 0-20, 20-40, 40-60, 60-80, 80-100."""
        rows = self.conn.execute(
            """SELECT
                CASE
                    WHEN final_score < 20 THEN '0-20'
                    WHEN final_score < 40 THEN '20-40'
                    WHEN final_score < 60 THEN '40-60'
                    WHEN final_score < 80 THEN '60-80'
                    ELSE '80-100'
                END as bucket,
                COUNT(*) as count
            FROM jobs
            GROUP BY bucket
            ORDER BY bucket"""
        ).fetchall()
        return [{"bucket": row["bucket"], "count": row["count"]} for row in rows]

    def get_company_applied_history(self) -> list[dict]:
        """Return applied jobs grouped by company with details."""
        rows = self.conn.execute(
            """SELECT company, title, applied_at, final_score
            FROM jobs
            WHERE state = 'applied' AND applied_at IS NOT NULL
            ORDER BY applied_at DESC"""
        ).fetchall()
        return [dict(row) for row in rows]

    def row_to_job(self, row: dict) -> Job:
        return Job(
            title=row["title"],
            company=row["company"],
            location=row["location"] or "",
            description=row["description"] or "",
            url=row["url"] or "",
            source=row["source"] or "",
            salary_min=row["salary_min"] or 0,
            salary_max=row["salary_max"] or 0,
            remote=bool(row["remote"]),
            sponsorship_available=row["sponsorship_available"],
            posted_date=row["posted_date"] or "",
            job_id=row["job_id"] or "",
            raw_data=json.loads(row["raw_data"]) if row["raw_data"] else {},
        )

    def row_to_match(self, row: dict) -> MatchResult:
        job = self.row_to_job(row)
        return MatchResult(
            job=job,
            keyword_score=row["keyword_score"] or 0,
            ai_score=row["ai_score"] or 0,
            final_score=row["final_score"] or 0,
            matched_skills=json.loads(row["matched_skills"])
            if row["matched_skills"]
            else [],
            missing_skills=json.loads(row["missing_skills"])
            if row["missing_skills"]
            else [],
            reasoning=row["reasoning"] or "",
            location_fit=bool(row["location_fit"]),
            sponsorship_fit=bool(row["sponsorship_fit"]),
        )
