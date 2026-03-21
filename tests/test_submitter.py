"""Tests for application submission."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from job_boo.apply.submitter import batch_apply, submit_application
from job_boo.models import Application, Job, JobState, MatchResult
from job_boo.storage.db import JobDB


@pytest.fixture
def mock_db(tmp_path: Path) -> JobDB:
    db = JobDB(db_path=tmp_path / "test.db")
    return db


class TestSubmitApplication:
    @patch("job_boo.apply.submitter.webbrowser.open")
    @patch("job_boo.apply.submitter.time.sleep")
    def test_successful_submit_no_confirm(
        self, mock_sleep: MagicMock, mock_browser: MagicMock, mock_db: JobDB
    ) -> None:
        job = Job(
            title="Dev", company="Co", location="Remote", description="",
            url="https://example.com/apply", source="test",
        )
        row_id = mock_db.upsert_job(job)
        match = MatchResult(job=job, keyword_score=80, ai_score=85, final_score=82.5)
        app = Application(job=job, match=match, state=JobState.READY, db_id=row_id)

        result = submit_application(app, mock_db, confirm=False, delay=0)
        assert result is True
        mock_browser.assert_called_once_with("https://example.com/apply")
        # Check state updated
        row = mock_db.get_job_by_id(row_id)
        assert row is not None
        assert row["state"] == "applied"

    @patch("job_boo.apply.submitter.webbrowser.open")
    def test_no_url_returns_false(self, mock_browser: MagicMock, mock_db: JobDB) -> None:
        job = Job(
            title="Dev", company="Co", location="", description="",
            url="", source="test",
        )
        match = MatchResult(job=job, keyword_score=80, ai_score=85, final_score=82.5)
        app = Application(job=job, match=match)

        result = submit_application(app, mock_db, confirm=False)
        assert result is False
        mock_browser.assert_not_called()

    @patch("job_boo.apply.submitter.Confirm.ask", return_value=False)
    @patch("job_boo.apply.submitter.webbrowser.open")
    def test_user_declines(
        self, mock_browser: MagicMock, mock_confirm: MagicMock, mock_db: JobDB
    ) -> None:
        job = Job(
            title="Dev", company="Co", location="", description="",
            url="https://example.com", source="test",
        )
        row_id = mock_db.upsert_job(job)
        match = MatchResult(job=job, keyword_score=80, ai_score=85, final_score=82.5)
        app = Application(job=job, match=match, state=JobState.READY, db_id=row_id)

        result = submit_application(app, mock_db, confirm=True)
        assert result is False
        mock_browser.assert_not_called()
        # Should be marked as skipped
        row = mock_db.get_job_by_id(row_id)
        assert row is not None
        assert row["state"] == "skipped"

    @patch("job_boo.apply.submitter.webbrowser.open")
    @patch("job_boo.apply.submitter.time.sleep")
    def test_delay_applied(
        self, mock_sleep: MagicMock, mock_browser: MagicMock, mock_db: JobDB
    ) -> None:
        job = Job(
            title="Dev", company="Co", location="", description="",
            url="https://example.com", source="test",
        )
        match = MatchResult(job=job, keyword_score=80, ai_score=85, final_score=82.5)
        app = Application(job=job, match=match)

        submit_application(app, mock_db, confirm=False, delay=3)
        mock_sleep.assert_called_once_with(3)

    @patch("job_boo.apply.submitter.webbrowser.open")
    @patch("job_boo.apply.submitter.time.sleep")
    def test_no_db_id_still_opens_browser(
        self, mock_sleep: MagicMock, mock_browser: MagicMock, mock_db: JobDB
    ) -> None:
        job = Job(
            title="Dev", company="Co", location="", description="",
            url="https://example.com", source="test",
        )
        match = MatchResult(job=job, keyword_score=80, ai_score=85, final_score=82.5)
        app = Application(job=job, match=match, db_id=None)

        result = submit_application(app, mock_db, confirm=False, delay=0)
        assert result is True
        mock_browser.assert_called_once()


class TestBatchApply:
    @patch("job_boo.apply.submitter.submit_application")
    def test_batch_apply_minimum_delay(
        self, mock_submit: MagicMock, mock_db: JobDB
    ) -> None:
        mock_submit.return_value = True
        job = Job(
            title="Dev", company="Co", location="", description="",
            url="https://example.com", source="test",
        )
        mock_db.upsert_job(job)
        match = MatchResult(job=job, keyword_score=80, ai_score=85, final_score=82.5)
        matches = [match]

        applied = batch_apply(matches, mock_db, confirm=False, delay=1)
        assert applied == 1
        # Delay should be at least 10
        call_kwargs = mock_submit.call_args
        assert call_kwargs[1]["delay"] >= 10 or call_kwargs.kwargs.get("delay", 0) >= 10

    @patch("job_boo.apply.submitter.submit_application")
    def test_batch_apply_counts_submissions(
        self, mock_submit: MagicMock, mock_db: JobDB
    ) -> None:
        # First returns True, second returns False
        mock_submit.side_effect = [True, False, True]
        jobs_and_matches = []
        for i in range(3):
            job = Job(
                title=f"Dev {i}", company=f"Co {i}", location="", description="",
                url=f"https://example.com/{i}", source="test",
            )
            mock_db.upsert_job(job)
            match = MatchResult(job=job, keyword_score=80, ai_score=85, final_score=82.5)
            jobs_and_matches.append(match)

        applied = batch_apply(jobs_and_matches, mock_db, confirm=False)
        assert applied == 2

    @patch("job_boo.apply.submitter.submit_application")
    def test_batch_apply_empty_list(self, mock_submit: MagicMock, mock_db: JobDB) -> None:
        applied = batch_apply([], mock_db)
        assert applied == 0
        mock_submit.assert_not_called()
