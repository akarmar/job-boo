"""Tests for search/__init__.py orchestration and helpers."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from job_boo.config import Config, CompaniesConfig, SourcesConfig
from job_boo.models import Job
from job_boo.search import filter_by_company, filter_by_recency, parse_posted_date, search_all_sources


class TestSearchAllSources:
    @patch("job_boo.search.search_remotive")
    @patch("job_boo.search.search_themuse")
    def test_deduplicates_across_sources(
        self, mock_muse: MagicMock, mock_remotive: MagicMock
    ) -> None:
        job1 = Job(title="Dev", company="Co", location="", description="", url="u1", source="themuse")
        job2 = Job(title="Dev", company="Co", location="", description="", url="u2", source="remotive")
        mock_muse.return_value = [job1]
        mock_remotive.return_value = [job2]

        config = Config(
            sources=SourcesConfig(themuse=True, remotive=True),
        )
        # Disable other sources
        config.sources.serpapi.enabled = False
        config.sources.adzuna.enabled = False
        config.sources.jobspy.enabled = False

        jobs = search_all_sources(config)
        # Same dedup key -> only one job
        assert len(jobs) == 1

    @patch("job_boo.search.search_remotive")
    @patch("job_boo.search.search_themuse")
    def test_handles_source_errors(
        self, mock_muse: MagicMock, mock_remotive: MagicMock
    ) -> None:
        mock_muse.side_effect = RuntimeError("API down")
        mock_remotive.return_value = [
            Job(title="Dev", company="Co", location="", description="", url="", source="remotive")
        ]

        config = Config(sources=SourcesConfig(themuse=True, remotive=True))
        config.sources.serpapi.enabled = False
        config.sources.adzuna.enabled = False
        config.sources.jobspy.enabled = False

        # Should not raise
        jobs = search_all_sources(config)
        assert len(jobs) == 1

    def test_no_sources_enabled(self) -> None:
        config = Config(
            sources=SourcesConfig(themuse=False, remotive=False),
        )
        config.sources.serpapi.enabled = False
        config.sources.adzuna.enabled = False
        config.sources.jobspy.enabled = False

        jobs = search_all_sources(config)
        assert jobs == []

    @patch("job_boo.search.search_themuse")
    def test_applies_recency_filter(self, mock_muse: MagicMock) -> None:
        old_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        recent_date = datetime.now().strftime("%Y-%m-%d")
        mock_muse.return_value = [
            Job(title="Old", company="Co1", location="", description="", url="", source="themuse", posted_date=old_date),
            Job(title="New", company="Co2", location="", description="", url="", source="themuse", posted_date=recent_date),
        ]

        config = Config(sources=SourcesConfig(themuse=True, remotive=False))
        config.sources.serpapi.enabled = False
        config.sources.adzuna.enabled = False
        config.sources.jobspy.enabled = False

        jobs = search_all_sources(config, max_days=30)
        assert len(jobs) == 1
        assert jobs[0].title == "New"

    @patch("job_boo.search.search_themuse")
    def test_applies_company_filter(self, mock_muse: MagicMock) -> None:
        mock_muse.return_value = [
            Job(title="E", company="Evil Corp", location="", description="", url="", source="themuse"),
            Job(title="E", company="Good Corp", location="", description="", url="", source="themuse"),
        ]

        config = Config(
            sources=SourcesConfig(themuse=True, remotive=False),
            companies=CompaniesConfig(blacklist=["Evil Corp"]),
        )
        config.sources.serpapi.enabled = False
        config.sources.adzuna.enabled = False
        config.sources.jobspy.enabled = False

        jobs = search_all_sources(config)
        assert len(jobs) == 1
        assert jobs[0].company == "Good Corp"
