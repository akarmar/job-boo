"""Tests for analytics dashboard generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from job_boo.analytics.dashboard import (
    _build_stat_cards_html,
    _build_table_html,
    _chart_colors,
    _escape,
    _query_funnel,
    _query_score_distribution,
    _query_state_counts,
    generate_dashboard,
)
from job_boo.models import Job, JobState, MatchResult
from job_boo.storage.db import JobDB


class TestEscape:
    def test_ampersand(self) -> None:
        assert _escape("A & B") == "A &amp; B"

    def test_angle_brackets(self) -> None:
        assert _escape("<script>") == "&lt;script&gt;"

    def test_double_quotes(self) -> None:
        assert _escape('"hello"') == "&quot;hello&quot;"

    def test_single_quotes(self) -> None:
        assert _escape("it's") == "it&#x27;s"

    def test_none_returns_empty(self) -> None:
        assert _escape(None) == ""

    def test_empty_string(self) -> None:
        assert _escape("") == ""

    def test_normal_text_unchanged(self) -> None:
        assert _escape("Hello World") == "Hello World"

    def test_combined_special_chars(self) -> None:
        result = _escape('<a href="test">&')
        assert "&lt;" in result
        assert "&gt;" in result
        assert "&quot;" in result
        assert "&amp;" in result

    def test_numeric_input(self) -> None:
        assert _escape(str(42)) == "42"


class TestChartColors:
    def test_returns_correct_count(self) -> None:
        colors = _chart_colors(5)
        assert len(colors) == 5

    def test_wraps_around_palette(self) -> None:
        colors = _chart_colors(15)
        assert len(colors) == 15
        # Should cycle
        assert colors[0] == colors[10]

    def test_zero_count(self) -> None:
        assert _chart_colors(0) == []


class TestQueryFunnel:
    def test_empty_state_counts(self) -> None:
        funnel = _query_funnel({})
        assert len(funnel) == 5
        assert all(f["count"] == 0 for f in funnel)

    def test_cumulative_counts(self) -> None:
        state_counts = {"found": 100, "scored": 50, "tailored": 20, "applied": 10, "closed": 2}
        funnel = _query_funnel(state_counts)
        # "found" stage should include all that reached found or beyond
        found_stage = next(f for f in funnel if f["stage"] == "Found")
        assert found_stage["count"] >= 10  # at minimum the applied ones

    def test_with_skipped_state(self) -> None:
        state_counts = {"found": 5, "skipped": 3}
        funnel = _query_funnel(state_counts)
        # Should still work without error
        assert len(funnel) == 5


class TestBuildStatCardsHtml:
    def test_contains_all_stats(self) -> None:
        stats = {
            "total_jobs": 100,
            "total_applied": 25,
            "avg_score": 72.5,
            "days_active": 30,
            "top_source": "adzuna",
        }
        html = _build_stat_cards_html(stats)
        assert "100" in html
        assert "25" in html
        assert "72.5" in html
        assert "adzuna" in html


class TestBuildTableHtml:
    def test_basic_table(self) -> None:
        html = _build_table_html("Test Table", ["Col1", "Col2"], [["A", "B"], ["C", "D"]])
        assert "Test Table" in html
        assert "<th>Col1</th>" in html
        assert "<td>A</td>" in html

    def test_empty_rows(self) -> None:
        html = _build_table_html("Empty", ["H1"], [])
        assert "Empty" in html
        assert "<tbody></tbody>" in html


class TestGenerateDashboard:
    def test_empty_db_generates_html(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        output_path = tmp_path / "dashboard.html"
        # Create an empty DB with schema
        db = JobDB(db_path=db_path)
        db.close()

        result = generate_dashboard(db_path=db_path, output_path=output_path)
        assert result == output_path
        assert output_path.exists()
        content = output_path.read_text()
        assert "<!DOCTYPE html>" in content
        assert "Job Boo" in content

    def test_db_with_jobs(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        output_path = tmp_path / "dashboard.html"
        db = JobDB(db_path=db_path)
        for i in range(5):
            job = Job(
                title=f"Engineer {i}", company=f"Co {i}", location="Remote",
                description="Build stuff", url=f"https://example.com/{i}",
                source="adzuna",
            )
            db.upsert_job(job)
            match = MatchResult(
                job=job, keyword_score=float(i * 20), ai_score=float(i * 20),
                final_score=float(i * 20),
                matched_skills=["Python"], missing_skills=["AWS"],
            )
            db.update_score(job.dedup_key(), match)
        db.close()

        result = generate_dashboard(db_path=db_path, output_path=output_path)
        content = output_path.read_text()
        assert "chart.js" in content
        assert "funnelChart" in content

    def test_creates_output_dir(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        output_path = tmp_path / "subdir" / "dashboard.html"
        db = JobDB(db_path=db_path)
        db.close()

        generate_dashboard(db_path=db_path, output_path=output_path)
        assert output_path.exists()

    def test_with_missing_skills_in_db(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        output_path = tmp_path / "dashboard.html"
        db = JobDB(db_path=db_path)
        job = Job(
            title="Dev", company="Co", location="", description="",
            url="", source="test",
        )
        db.upsert_job(job)
        match = MatchResult(
            job=job, keyword_score=50, ai_score=50, final_score=50,
            missing_skills=["Docker", "K8s"],
        )
        db.update_score(job.dedup_key(), match)
        db.close()

        generate_dashboard(db_path=db_path, output_path=output_path)
        content = output_path.read_text()
        assert "Docker" in content or "skillChart" in content
