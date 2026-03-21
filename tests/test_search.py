"""Tests for search sources with mocked HTTP responses."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import httpx
import pytest

from job_boo.config import (
    AdzunaConfig,
    Config,
    LocationConfig,
    SalaryConfig,
    SerpApiConfig,
    SourcesConfig,
)
from job_boo.models import Job
from job_boo.search import (
    filter_by_company,
    filter_by_recency,
    parse_posted_date,
    search_all_sources,
)
from job_boo.search.adzuna import search_adzuna
from job_boo.search.remotive import search_remotive
from job_boo.search.serpapi import _parse_salary, search_serpapi
from job_boo.search.themuse import search_themuse
from job_boo.search.url import parse_job_url


def _mock_response(
    status_code: int = 200,
    json_data: dict | None = None,
    content_type: str = "application/json",
    text: str = "",
) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.headers = {"content-type": content_type}
    resp.json.return_value = json_data or {}
    resp.text = text or json.dumps(json_data or {})
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


class TestSearchAdzuna:
    @patch("job_boo.search.adzuna.httpx.get")
    def test_returns_jobs(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(
            json_data={
                "results": [
                    {
                        "title": "Python Developer",
                        "company": {"display_name": "Acme"},
                        "location": {"display_name": "Remote"},
                        "description": "Build stuff with Python",
                        "redirect_url": "https://acme.com/job/1",
                        "salary_min": 100000,
                        "salary_max": 150000,
                        "created": "2026-01-01",
                        "id": "123",
                    }
                ]
            }
        )
        config = Config(
            job_title="Python Developer",
            sources=SourcesConfig(
                adzuna=AdzunaConfig(enabled=True, app_id="aid", api_key="akey")
            ),
        )
        jobs = search_adzuna(config)
        assert len(jobs) == 1
        assert jobs[0].title == "Python Developer"
        assert jobs[0].company == "Acme"
        assert jobs[0].source == "adzuna"

    @patch("job_boo.search.adzuna.httpx.get")
    def test_empty_credentials_returns_empty(self, mock_get: MagicMock) -> None:
        config = Config(
            sources=SourcesConfig(adzuna=AdzunaConfig(enabled=True, app_id="", api_key=""))
        )
        jobs = search_adzuna(config)
        assert jobs == []
        mock_get.assert_not_called()

    @patch("job_boo.search.adzuna.httpx.get")
    def test_http_error_raises(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(status_code=500)
        config = Config(
            job_title="Dev",
            sources=SourcesConfig(
                adzuna=AdzunaConfig(enabled=True, app_id="aid", api_key="akey")
            ),
        )
        with pytest.raises(RuntimeError, match="HTTP 500"):
            search_adzuna(config)

    @patch("job_boo.search.adzuna.httpx.get")
    def test_unexpected_content_type_raises(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(
            json_data={"results": []}, content_type="text/html"
        )
        config = Config(
            job_title="Dev",
            sources=SourcesConfig(
                adzuna=AdzunaConfig(enabled=True, app_id="aid", api_key="akey")
            ),
        )
        with pytest.raises(RuntimeError, match="content-type"):
            search_adzuna(config)

    @patch("job_boo.search.adzuna.httpx.get")
    def test_empty_results(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(json_data={"results": []})
        config = Config(
            job_title="Dev",
            sources=SourcesConfig(
                adzuna=AdzunaConfig(enabled=True, app_id="aid", api_key="akey")
            ),
        )
        jobs = search_adzuna(config)
        assert jobs == []

    @patch("job_boo.search.adzuna.httpx.get")
    def test_remote_detection_from_location(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(
            json_data={
                "results": [
                    {
                        "title": "Dev",
                        "company": {"display_name": "Co"},
                        "location": {"display_name": "Remote, USA"},
                        "description": "",
                        "redirect_url": "",
                    }
                ]
            }
        )
        config = Config(
            job_title="Dev",
            sources=SourcesConfig(
                adzuna=AdzunaConfig(enabled=True, app_id="aid", api_key="akey")
            ),
        )
        jobs = search_adzuna(config)
        assert jobs[0].remote is True


class TestSearchRemotive:
    @patch("job_boo.search.remotive.httpx.get")
    def test_returns_jobs(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(
            json_data={
                "jobs": [
                    {
                        "title": "Backend Engineer",
                        "company_name": "RemoteCo",
                        "candidate_required_location": "Worldwide",
                        "description": "<p>Build APIs</p>",
                        "url": "https://remotive.com/job/1",
                        "salary": "$120,000 - $160,000",
                        "publication_date": "2026-01-01",
                        "id": 456,
                    }
                ]
            }
        )
        config = Config(job_title="software engineer")
        jobs = search_remotive(config)
        assert len(jobs) == 1
        assert jobs[0].remote is True
        assert jobs[0].salary_min == 120000
        assert jobs[0].salary_max == 160000
        # HTML should be stripped
        assert "<p>" not in jobs[0].description

    @patch("job_boo.search.remotive.httpx.get")
    def test_category_detection(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(json_data={"jobs": []})
        # "data" title maps to "data" category, but "engineer" keyword
        # is checked first in REMOTIVE_CATEGORIES and maps to "software-dev"
        # Use a title that only matches "data" category
        config = Config(job_title="data analyst")
        search_remotive(config)
        call_args = mock_get.call_args
        assert call_args[1]["params"]["category"] == "data"

    @patch("job_boo.search.remotive.httpx.get")
    def test_http_error(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(status_code=429)
        config = Config(job_title="dev")
        with pytest.raises(RuntimeError, match="HTTP 429"):
            search_remotive(config)


class TestSearchTheMuse:
    @patch("job_boo.search.themuse.httpx.get")
    def test_returns_jobs(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(
            json_data={
                "results": [
                    {
                        "name": "Product Manager",
                        "company": {"name": "MuseCo"},
                        "locations": [{"name": "New York"}],
                        "contents": "<b>Great role</b>",
                        "refs": {"landing_page": "https://muse.com/job/1"},
                        "publication_date": "2026-01-01",
                        "id": 789,
                    }
                ]
            }
        )
        config = Config(job_title="product manager")
        jobs = search_themuse(config)
        assert len(jobs) == 1
        assert jobs[0].title == "Product Manager"
        assert jobs[0].company == "MuseCo"
        assert "<b>" not in jobs[0].description

    @patch("job_boo.search.themuse.httpx.get")
    def test_remote_detection(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(
            json_data={
                "results": [
                    {
                        "name": "Dev",
                        "company": {"name": "Co"},
                        "locations": [{"name": "Remote"}],
                        "contents": "",
                        "refs": {"landing_page": ""},
                        "id": 1,
                    }
                ]
            }
        )
        config = Config(job_title="dev")
        jobs = search_themuse(config)
        assert jobs[0].remote is True

    @patch("job_boo.search.themuse.httpx.get")
    def test_flexible_location_is_remote(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(
            json_data={
                "results": [
                    {
                        "name": "Dev",
                        "company": {"name": "Co"},
                        "locations": [{"name": "Flexible / Remote"}],
                        "contents": "",
                        "refs": {"landing_page": ""},
                        "id": 1,
                    }
                ]
            }
        )
        config = Config(job_title="dev")
        jobs = search_themuse(config)
        assert jobs[0].remote is True


class TestSearchSerpapi:
    @patch("job_boo.search.serpapi.httpx.get")
    def test_returns_jobs(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(
            json_data={
                "jobs_results": [
                    {
                        "title": "ML Engineer",
                        "company_name": "AI Corp",
                        "location": "Remote",
                        "description": "Build ML models",
                        "apply_options": [{"link": "https://apply.com/1"}],
                        "detected_extensions": {
                            "salary": "$150K-$200K",
                            "posted_at": "3 days ago",
                        },
                        "job_id": "serp-1",
                    }
                ]
            }
        )
        config = Config(
            job_title="ML Engineer",
            sources=SourcesConfig(serpapi=SerpApiConfig(enabled=True, api_key="key")),
        )
        jobs = search_serpapi(config)
        assert len(jobs) == 1
        assert jobs[0].title == "ML Engineer"
        assert jobs[0].salary_min == 150000

    @patch("job_boo.search.serpapi.httpx.get")
    def test_no_api_key_returns_empty(self, mock_get: MagicMock) -> None:
        config = Config(
            sources=SourcesConfig(serpapi=SerpApiConfig(enabled=True, api_key=""))
        )
        jobs = search_serpapi(config)
        assert jobs == []

    @patch("job_boo.search.serpapi.httpx.get")
    def test_no_apply_options(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(
            json_data={
                "jobs_results": [
                    {
                        "title": "Dev",
                        "company_name": "Co",
                        "location": "NYC",
                        "description": "stuff",
                        "detected_extensions": {},
                        "job_id": "1",
                    }
                ]
            }
        )
        config = Config(
            job_title="Dev",
            sources=SourcesConfig(serpapi=SerpApiConfig(enabled=True, api_key="key")),
        )
        jobs = search_serpapi(config)
        assert jobs[0].url == ""


class TestParseSalary:
    def test_k_salary(self) -> None:
        assert _parse_salary("$150K-$200K") == 150000

    def test_comma_salary(self) -> None:
        assert _parse_salary("$120,000") == 120000

    def test_empty_string(self) -> None:
        assert _parse_salary("") == 0

    def test_no_numbers(self) -> None:
        assert _parse_salary("Competitive") == 0

    def test_lowercase_k(self) -> None:
        assert _parse_salary("120k") == 120000


class TestParseJobUrl:
    @patch("job_boo.search.url.httpx.get")
    def test_parses_html(self, mock_get: MagicMock) -> None:
        html = """
        <html>
        <head><title>Job at Acme</title></head>
        <body>
            <h1>Senior Engineer</h1>
            <div class="company-name">Acme Corp</div>
            <div class="location">Remote</div>
            <div class="job-description">Build great things with Python.</div>
        </body>
        </html>
        """
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.text = html
        resp.raise_for_status = MagicMock()
        mock_get.return_value = resp

        job = parse_job_url("https://acme.com/jobs/123")
        assert job.title == "Senior Engineer"
        assert job.company == "Acme Corp"
        assert job.source == "url"

    def test_invalid_scheme_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            parse_job_url("ftp://example.com")

    def test_no_hostname_raises(self) -> None:
        with pytest.raises(ValueError, match="no hostname"):
            parse_job_url("http://")

    @patch("job_boo.search.url.httpx.get")
    def test_remote_detection_in_content(self, mock_get: MagicMock) -> None:
        html = """
        <html><body>
            <h1>Remote Developer</h1>
            <article>Work from anywhere, remote position.</article>
        </body></html>
        """
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.text = html
        resp.raise_for_status = MagicMock()
        mock_get.return_value = resp
        job = parse_job_url("https://example.com/job")
        assert job.remote is True


class TestParsePostedDate:
    def test_iso_date(self) -> None:
        result = parse_posted_date("2026-01-15")
        assert result is not None
        assert result.year == 2026

    def test_iso_datetime(self) -> None:
        result = parse_posted_date("2026-01-15T10:30:00")
        assert result is not None

    def test_relative_days(self) -> None:
        result = parse_posted_date("3 days ago")
        assert result is not None
        assert (datetime.now() - result).days <= 4

    def test_relative_weeks(self) -> None:
        result = parse_posted_date("2 weeks ago")
        assert result is not None

    def test_relative_months(self) -> None:
        result = parse_posted_date("1 month ago")
        assert result is not None

    def test_today(self) -> None:
        result = parse_posted_date("today")
        assert result is not None
        assert result.date() == datetime.now().date()

    def test_yesterday(self) -> None:
        result = parse_posted_date("yesterday")
        assert result is not None
        assert result.date() == (datetime.now() - timedelta(days=1)).date()

    def test_empty_string(self) -> None:
        assert parse_posted_date("") is None

    def test_unparseable(self) -> None:
        assert parse_posted_date("not a date") is None

    def test_relative_hours(self) -> None:
        result = parse_posted_date("5 hours ago")
        assert result is not None

    def test_relative_minutes(self) -> None:
        result = parse_posted_date("30 minutes ago")
        assert result is not None


class TestFilterByRecency:
    def test_keeps_recent_jobs(self) -> None:
        job = Job(
            title="Dev", company="Co", location="", description="", url="", source="test",
            posted_date=datetime.now().strftime("%Y-%m-%d"),
        )
        result = filter_by_recency([job], max_days=7)
        assert len(result) == 1

    def test_filters_old_jobs(self) -> None:
        old_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        job = Job(
            title="Dev", company="Co", location="", description="", url="", source="test",
            posted_date=old_date,
        )
        result = filter_by_recency([job], max_days=30)
        assert len(result) == 0

    def test_keeps_jobs_with_unparseable_dates(self) -> None:
        job = Job(
            title="Dev", company="Co", location="", description="", url="", source="test",
            posted_date="unknown date",
        )
        result = filter_by_recency([job], max_days=7)
        assert len(result) == 1


class TestFilterByCompany:
    def test_blacklist_filters(self) -> None:
        config = Config(companies=MagicMock(blacklist=["Evil Corp"], whitelist=[]))
        jobs = [
            Job(title="E", company="Evil Corp", location="", description="", url="", source="test"),
            Job(title="E", company="Good Corp", location="", description="", url="", source="test"),
        ]
        result = filter_by_company(jobs, config)
        assert len(result) == 1
        assert result[0].company == "Good Corp"

    def test_whitelist_filters(self) -> None:
        config = Config(companies=MagicMock(blacklist=[], whitelist=["Good Corp"]))
        jobs = [
            Job(title="E", company="Good Corp", location="", description="", url="", source="test"),
            Job(title="E", company="Other Corp", location="", description="", url="", source="test"),
        ]
        result = filter_by_company(jobs, config)
        assert len(result) == 1
        assert result[0].company == "Good Corp"
