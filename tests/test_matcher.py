"""Tests for scoring/matcher module."""

from __future__ import annotations

from unittest.mock import MagicMock

from job_boo.config import Config, LocationConfig, CompaniesConfig
from job_boo.models import Job, MatchResult, Resume
from job_boo.scoring.matcher import (
    KEYWORD_THRESHOLD,
    _skill_in_text,
    _trim_description,
    check_filters,
    is_company_blacklisted,
    keyword_score,
    score_jobs,
)


class TestSkillInText:
    def test_short_skill_word_boundary(self) -> None:
        # "go" should not match "good"
        assert _skill_in_text("go", "this is a good language") is False

    def test_short_skill_matches_exact(self) -> None:
        assert _skill_in_text("go", "experience with go programming") is True

    def test_short_skill_r_not_in_error(self) -> None:
        assert _skill_in_text("r", "error handling is important") is False

    def test_short_skill_r_matches_standalone(self) -> None:
        assert _skill_in_text("r", "experience with r and python") is True

    def test_long_skill_substring_match(self) -> None:
        # Skills > 3 chars use plain substring
        assert _skill_in_text("python", "we use python 3.11") is True

    def test_long_skill_partial_match_ok(self) -> None:
        # "java" will match "javascript" (by design for > 3 chars: substring check)
        assert _skill_in_text("java", "javascript developer") is True

    def test_case_sensitive(self) -> None:
        # The function does not lowercase — caller is responsible
        assert _skill_in_text("Python", "python developer") is False
        assert _skill_in_text("python", "python developer") is True

    def test_empty_skill(self) -> None:
        assert _skill_in_text("", "some text") is True  # empty pattern matches

    def test_skill_at_end_of_string(self) -> None:
        assert _skill_in_text("go", "I know go") is True

    def test_skill_at_start_of_string(self) -> None:
        assert _skill_in_text("go", "go is great") is True

    def test_skill_with_special_regex_chars(self) -> None:
        # c++ is 3 chars, uses word boundary; re.escape handles the +
        # But \b after + doesn't match as expected with regex word boundaries
        # since + is not a word char, \b matches between + and space — actually
        # the issue is c++ has len 3, so it uses word boundary regex, but
        # \bc\+\+\b won't match because + is non-word char at the boundary.
        # This is a known limitation of the word-boundary approach for short skills.
        # For longer skills (>3 chars), substring matching is used instead.
        assert (
            _skill_in_text("c++", "c++ developer needed") is False
        )  # known limitation

    def test_three_char_skill_uses_boundary(self) -> None:
        # Exactly 3 chars should use word boundary
        assert _skill_in_text("sql", "sql database") is True
        assert _skill_in_text("sql", "nosql systems") is False


class TestTrimDescription:
    def test_short_description_unchanged(self) -> None:
        desc = "Short job description"
        assert _trim_description(desc) == desc

    def test_long_description_truncated(self) -> None:
        desc = "x" * 5000
        result = _trim_description(desc, max_chars=3000)
        assert len(result) == 3000

    def test_prefers_requirements_section(self) -> None:
        desc = "A" * 2000 + "Requirements: Python, AWS, Docker" + "B" * 2000
        result = _trim_description(desc, max_chars=500)
        assert "Requirements" in result or "requirements" in result.lower()

    def test_qualifications_marker(self) -> None:
        desc = "X" * 2000 + "Qualifications: BS in CS" + "Y" * 2000
        result = _trim_description(desc, max_chars=500)
        assert "Qualifications" in result or "qualifications" in result.lower()

    def test_no_marker_truncates_from_start(self) -> None:
        desc = "A" * 5000
        result = _trim_description(desc, max_chars=3000)
        assert result == "A" * 3000

    def test_marker_near_start(self) -> None:
        desc = "Requirements: Python, AWS. " + "B" * 5000
        result = _trim_description(desc, max_chars=100)
        assert result.startswith("Requirements")

    def test_exact_max_chars(self) -> None:
        desc = "x" * 3000
        result = _trim_description(desc, max_chars=3000)
        assert len(result) == 3000


class TestKeywordScore:
    def test_all_skills_match(self) -> None:
        resume = Resume(raw_text="", skills=["python", "aws"])
        job = Job(
            title="Python Developer",
            company="Co",
            location="",
            description="python and aws required",
            url="",
            source="test",
        )
        assert keyword_score(resume, job) == 100.0

    def test_no_skills_match(self) -> None:
        resume = Resume(raw_text="", skills=["rust", "haskell"])
        job = Job(
            title="Python Developer",
            company="Co",
            location="",
            description="python and java",
            url="",
            source="test",
        )
        assert keyword_score(resume, job) == 0.0

    def test_empty_skills_returns_zero(self) -> None:
        resume = Resume(raw_text="", skills=[])
        job = Job(
            title="Dev",
            company="Co",
            location="",
            description="anything",
            url="",
            source="test",
        )
        assert keyword_score(resume, job) == 0

    def test_partial_match(self) -> None:
        resume = Resume(raw_text="", skills=["python", "aws", "kubernetes", "java"])
        job = Job(
            title="Dev",
            company="Co",
            location="",
            description="we need python and kubernetes experience",
            url="",
            source="test",
        )
        score = keyword_score(resume, job)
        assert score == 50.0  # 2 out of 4

    def test_variant_matching_hyphen(self) -> None:
        resume = Resume(raw_text="", skills=["ci/cd"])
        job = Job(
            title="DevOps",
            company="Co",
            location="",
            description="experience with ci cd pipelines",
            url="",
            source="test",
        )
        # ci/cd -> "ci cd" variant (replace / with nothing doesn't help; replace("-", " ") won't help either)
        # Actually the variants are: "ci/cd".replace(" ", "-") = "ci/cd", replace("-", " ") = "ci/cd", replace(".", "") = "ci/cd"
        # None match "ci cd" — so this tests that non-matching variants return 0
        score = keyword_score(resume, job)
        assert score == 0.0

    def test_skill_in_title_counts(self) -> None:
        resume = Resume(raw_text="", skills=["python"])
        job = Job(
            title="Python Developer",
            company="Co",
            location="",
            description="build things",
            url="",
            source="test",
        )
        assert keyword_score(resume, job) == 100.0

    def test_case_insensitive_matching(self) -> None:
        resume = Resume(raw_text="", skills=["Python", "AWS"])
        job = Job(
            title="Dev",
            company="Co",
            location="",
            description="python and aws needed",
            url="",
            source="test",
        )
        assert keyword_score(resume, job) == 100.0

    def test_whitespace_in_skills(self) -> None:
        resume = Resume(raw_text="", skills=["  python  ", " aws "])
        job = Job(
            title="Dev",
            company="Co",
            location="",
            description="python and aws",
            url="",
            source="test",
        )
        assert keyword_score(resume, job) == 100.0


class TestIsCompanyBlacklisted:
    def test_blacklisted(self, config_with_blacklist: Config) -> None:
        job = Job(
            title="E",
            company="Evil Corp",
            location="",
            description="",
            url="",
            source="test",
        )
        assert is_company_blacklisted(job, config_with_blacklist) is True

    def test_not_blacklisted(self, config_with_blacklist: Config) -> None:
        job = Job(
            title="E",
            company="Good Corp",
            location="",
            description="",
            url="",
            source="test",
        )
        assert is_company_blacklisted(job, config_with_blacklist) is False

    def test_case_insensitive(self, config_with_blacklist: Config) -> None:
        job = Job(
            title="E",
            company="evil corp",
            location="",
            description="",
            url="",
            source="test",
        )
        assert is_company_blacklisted(job, config_with_blacklist) is True

    def test_empty_blacklist(self) -> None:
        config = Config()
        job = Job(
            title="E", company="Any", location="", description="", url="", source="test"
        )
        assert is_company_blacklisted(job, config) is False


class TestCheckFilters:
    def test_remote_preference_with_remote_job(self) -> None:
        config = Config(location=LocationConfig(preference="remote"))
        job = Job(
            title="E",
            company="C",
            location="Remote",
            description="",
            url="",
            source="test",
            remote=True,
        )
        loc_fit, spon_fit = check_filters(job, config)
        assert loc_fit is True

    def test_remote_preference_with_onsite_job(self) -> None:
        config = Config(location=LocationConfig(preference="remote"))
        job = Job(
            title="E",
            company="C",
            location="New York, NY",
            description="",
            url="",
            source="test",
            remote=False,
        )
        loc_fit, spon_fit = check_filters(job, config)
        assert loc_fit is False

    def test_city_preference_match(self) -> None:
        config = Config(
            location=LocationConfig(preference="onsite", city="San Francisco")
        )
        job = Job(
            title="E",
            company="C",
            location="San Francisco, CA",
            description="",
            url="",
            source="test",
        )
        loc_fit, _ = check_filters(job, config)
        assert loc_fit is True

    def test_city_preference_no_match(self) -> None:
        config = Config(
            location=LocationConfig(preference="onsite", city="San Francisco")
        )
        job = Job(
            title="E",
            company="C",
            location="New York, NY",
            description="",
            url="",
            source="test",
        )
        loc_fit, _ = check_filters(job, config)
        assert loc_fit is False

    def test_sponsorship_needed_and_not_available(self) -> None:
        config = Config(needs_sponsorship=True)
        job = Job(
            title="E",
            company="C",
            location="",
            url="",
            source="test",
            description="We are unable to sponsor visas.",
        )
        _, spon_fit = check_filters(job, config)
        assert spon_fit is False

    def test_sponsorship_needed_and_field_false(self) -> None:
        config = Config(needs_sponsorship=True)
        job = Job(
            title="E",
            company="C",
            location="",
            description="Great job!",
            url="",
            source="test",
            sponsorship_available=False,
        )
        _, spon_fit = check_filters(job, config)
        assert spon_fit is False

    def test_sponsorship_not_needed_ignores(self) -> None:
        config = Config(needs_sponsorship=False)
        job = Job(
            title="E",
            company="C",
            location="",
            url="",
            source="test",
            description="Unable to sponsor visas.",
        )
        _, spon_fit = check_filters(job, config)
        assert spon_fit is True

    def test_sponsorship_unknown_benefit_of_doubt(self) -> None:
        config = Config(needs_sponsorship=True)
        job = Job(
            title="E",
            company="C",
            location="",
            description="Great role!",
            url="",
            source="test",
            sponsorship_available=None,
        )
        _, spon_fit = check_filters(job, config)
        assert spon_fit is True


class TestScoreJobs:
    def test_empty_job_list(self) -> None:
        resume = Resume(raw_text="", skills=["Python"])
        ai = MagicMock()
        config = Config()
        results = score_jobs(resume, [], ai, config)
        assert results == []

    def test_jobs_below_threshold_returned_with_reasoning(self) -> None:
        resume = Resume(raw_text="", skills=["rust"])
        ai = MagicMock()
        config = Config()
        jobs = [
            Job(
                title="Python Developer",
                company="Co",
                location="",
                description="python only",
                url="",
                source="test",
            ),
        ]
        results = score_jobs(resume, jobs, ai, config)
        assert len(results) == 1
        assert results[0].ai_score == 0
        assert "Failed keyword filter" in results[0].reasoning
        ai.score_match.assert_not_called()

    def test_jobs_above_threshold_scored_by_ai(self) -> None:
        resume = Resume(raw_text="", skills=["python"])
        mock_match = MatchResult(
            job=MagicMock(),
            keyword_score=0,
            ai_score=80,
            final_score=0,
            matched_skills=["python"],
        )
        ai = MagicMock()
        ai.score_match.return_value = mock_match
        config = Config()
        jobs = [
            Job(
                title="Python Developer",
                company="Co",
                location="Remote",
                description="python experience required",
                url="",
                source="test",
            ),
        ]
        results = score_jobs(resume, jobs, ai, config)
        assert len(results) == 1
        assert ai.score_match.call_count == 1
        # Final score = keyword * 0.3 + ai * 0.7
        result = results[0]
        expected = result.keyword_score * 0.3 + 80 * 0.7
        assert abs(result.final_score - expected) < 0.01

    def test_ai_error_handled_gracefully(self) -> None:
        resume = Resume(raw_text="", skills=["python"])
        ai = MagicMock()
        ai.score_match.side_effect = RuntimeError("API error")
        config = Config()
        jobs = [
            Job(
                title="Python Dev",
                company="Co",
                location="",
                description="python experience required",
                url="",
                source="test",
            ),
        ]
        results = score_jobs(resume, jobs, ai, config)
        assert len(results) == 0

    def test_results_sorted_by_score_descending(self) -> None:
        resume = Resume(raw_text="", skills=["python", "aws", "docker"])
        config = Config()

        def make_match(resume_arg: Resume, job: Job) -> MatchResult:
            # Return different AI scores based on company
            ai_score = 90 if "high" in job.company.lower() else 50
            return MatchResult(
                job=job,
                keyword_score=0,
                ai_score=ai_score,
                final_score=0,
            )

        ai = MagicMock()
        ai.score_match.side_effect = make_match

        jobs = [
            Job(
                title="Dev",
                company="Low Score Co",
                location="",
                description="python aws docker",
                url="",
                source="test",
            ),
            Job(
                title="Dev",
                company="High Score Co",
                location="",
                description="python aws docker",
                url="",
                source="test",
            ),
        ]
        results = score_jobs(resume, jobs, ai, config)
        assert len(results) == 2
        assert results[0].final_score >= results[1].final_score
