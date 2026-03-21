"""Tests for CLI commands using Click test runner."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from job_boo.cli import main


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestMainGroup:
    def test_help(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Job Boo" in result.output

    def test_version(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0


class TestInitCommand:
    @patch("job_boo.cli.CONFIG_PATH")
    def test_init_shows_prompts(self, mock_path: MagicMock, runner: CliRunner) -> None:
        mock_path.exists.return_value = False
        result = runner.invoke(
            main, ["init"],
            input="~/resume.pdf\nSenior Engineer\npython,aws\nremote\n\nclaude\n\n"
        )
        # Should prompt for resume path
        assert "resume" in result.output.lower() or result.exit_code == 0


class TestStatusCommand:
    @patch("job_boo.cli.load_config")
    @patch("job_boo.storage.db.JobDB")
    def test_status_empty_db(
        self, mock_db_cls: MagicMock, mock_load: MagicMock, runner: CliRunner
    ) -> None:
        mock_load.return_value = MagicMock()
        mock_db = MagicMock()
        mock_db.get_stats.return_value = {}
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db_cls.return_value = mock_db

        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0


class TestSearchCommand:
    def test_search_help(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["search", "--help"])
        assert result.exit_code == 0
        assert "search" in result.output.lower() or "Search" in result.output


class TestExportCommand:
    @patch("job_boo.cli.load_config")
    @patch("job_boo.storage.db.JobDB")
    def test_export_csv(
        self, mock_db_cls: MagicMock, mock_load: MagicMock, runner: CliRunner, tmp_path: Path
    ) -> None:
        mock_load.return_value = MagicMock(output_dir=str(tmp_path))
        mock_db = MagicMock()
        mock_db.get_jobs.return_value = [
            {
                "title": "Dev",
                "company": "Co",
                "location": "Remote",
                "final_score": 85.0,
                "state": "scored",
                "url": "https://example.com",
                "matched_skills": '["Python"]',
                "missing_skills": '["AWS"]',
                "applied_at": None,
            }
        ]
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db_cls.return_value = mock_db

        result = runner.invoke(main, ["export", "--format", "csv"])
        assert result.exit_code == 0


class TestCleanupCommand:
    @patch("job_boo.storage.db.JobDB")
    def test_cleanup(self, mock_db_cls: MagicMock, runner: CliRunner) -> None:
        mock_db = MagicMock()
        mock_db.cleanup_expired.return_value = 5
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db_cls.return_value = mock_db

        result = runner.invoke(main, ["cleanup", "--days", "30"])
        assert result.exit_code == 0
