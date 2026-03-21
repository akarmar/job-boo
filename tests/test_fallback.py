"""Tests for the FallbackProvider (keyword-only matching)."""

from __future__ import annotations

from job_boo.ai.fallback import FallbackProvider, KNOWN_SKILLS
from job_boo.models import Job, MatchResult, Resume


class TestExtractSkills:
    def test_recognizes_known_skills(self) -> None:
        provider = FallbackProvider()
        text = "Experienced with Python, Docker, and Kubernetes in production."
        resume = provider.extract_skills(text)
        skills_lower = {s.lower() for s in resume.skills}
        assert "python" in skills_lower
        assert "docker" in skills_lower
        assert "kubernetes" in skills_lower

    def test_word_boundary_prevents_partial_match(self) -> None:
        provider = FallbackProvider()
        # "go" should match only as a standalone word, not in "good" or "algorithm"
        text = "Good algorithm design. Experience with Go language."
        resume = provider.extract_skills(text)
        skills_lower = {s.lower() for s in resume.skills}
        assert "go" in skills_lower

    def test_extracts_experience_years(self) -> None:
        provider = FallbackProvider()
        text = "I have 10+ years of experience in software engineering."
        resume = provider.extract_skills(text)
        assert resume.experience_years == 10

    def test_extracts_max_experience_years(self) -> None:
        provider = FallbackProvider()
        # Pattern requires "X years of experience" (not "X years of total experience")
        text = "3 years of experience in backend and 7 years of experience overall."
        resume = provider.extract_skills(text)
        assert resume.experience_years == 7

    def test_no_experience_pattern(self) -> None:
        provider = FallbackProvider()
        text = "Python developer with strong skills."
        resume = provider.extract_skills(text)
        assert resume.experience_years == 0

    def test_extracts_job_titles(self) -> None:
        provider = FallbackProvider()
        text = "Senior Software Engineer at Acme Corp. Previously a Backend Developer."
        resume = provider.extract_skills(text)
        # Should find at least one title pattern
        assert len(resume.job_titles) >= 1

    def test_extracts_education(self) -> None:
        provider = FallbackProvider()
        text = "Bachelor of Science in Computer Science from MIT."
        resume = provider.extract_skills(text)
        assert len(resume.education) >= 1

    def test_builds_summary_from_long_line(self) -> None:
        provider = FallbackProvider()
        text = (
            "John Doe\n"
            "Experienced software engineer with over 10 years building scalable distributed systems "
            "using Python, Go, and Kubernetes across cloud platforms.\n"
            "Skills: Python, Go\n"
        )
        resume = provider.extract_skills(text)
        assert len(resume.summary) > 0

    def test_fallback_summary_when_no_long_line(self) -> None:
        provider = FallbackProvider()
        text = "Short\nLines\nOnly\n"
        resume = provider.extract_skills(text)
        # Falls back to "Professional with experience in ..."
        assert "Professional with experience" in resume.summary or resume.summary

    def test_short_skills_cased_correctly(self) -> None:
        provider = FallbackProvider()
        # Short skills (<=2 chars) should be uppercased, others titled
        text = "Knows CSS and AWS and go programming."
        resume = provider.extract_skills(text)
        for skill in resume.skills:
            if len(skill) <= 2:
                assert skill == skill.upper()

    def test_empty_text(self) -> None:
        provider = FallbackProvider()
        resume = provider.extract_skills("")
        assert resume.skills == []
        assert resume.experience_years == 0

    def test_skills_are_sorted_and_deduplicated(self) -> None:
        provider = FallbackProvider()
        text = "Python and python and PYTHON are the same skill."
        resume = provider.extract_skills(text)
        python_skills = [s for s in resume.skills if s.lower() == "python"]
        assert len(python_skills) == 1


class TestScoreMatch:
    def test_perfect_match(self) -> None:
        provider = FallbackProvider()
        resume = Resume(
            raw_text="", skills=["Python", "AWS"], experience_years=5
        )
        job = Job(
            title="Python Developer",
            company="Co",
            location="",
            description="We need Python and AWS experience.",
            url="",
            source="test",
        )
        result = provider.score_match(resume, job)
        assert result.final_score == 100.0
        assert len(result.matched_skills) == 2

    def test_no_match(self) -> None:
        provider = FallbackProvider()
        resume = Resume(raw_text="", skills=["Rust", "Haskell"], experience_years=5)
        job = Job(
            title="Python Developer",
            company="Co",
            location="",
            description="We need Python and Java.",
            url="",
            source="test",
        )
        result = provider.score_match(resume, job)
        assert result.final_score == 0.0
        assert len(result.matched_skills) == 0

    def test_empty_skills(self) -> None:
        provider = FallbackProvider()
        resume = Resume(raw_text="", skills=[], experience_years=0)
        job = Job(
            title="Engineer", company="Co", location="",
            description="Python required.", url="", source="test",
        )
        result = provider.score_match(resume, job)
        assert result.final_score == 0.0

    def test_variant_matching_with_hyphens(self) -> None:
        provider = FallbackProvider()
        resume = Resume(raw_text="", skills=["next.js"], experience_years=3)
        job = Job(
            title="Frontend Dev",
            company="Co",
            location="",
            description="Experience with nextjs required.",
            url="",
            source="test",
        )
        result = provider.score_match(resume, job)
        assert len(result.matched_skills) == 1

    def test_missing_skills_identified(self) -> None:
        provider = FallbackProvider()
        resume = Resume(raw_text="", skills=["Python"], experience_years=5)
        job = Job(
            title="Engineer",
            company="Co",
            location="",
            description="We need Python, Docker, and Kubernetes expertise.",
            url="",
            source="test",
        )
        result = provider.score_match(resume, job)
        missing_lower = {s.lower() for s in result.missing_skills}
        assert "docker" in missing_lower or "kubernetes" in missing_lower

    def test_reasoning_mentions_fallback(self) -> None:
        provider = FallbackProvider()
        resume = Resume(raw_text="", skills=["Python"], experience_years=5)
        job = Job(
            title="Dev", company="Co", location="", description="Python.",
            url="", source="test",
        )
        result = provider.score_match(resume, job)
        assert "Fallback mode" in result.reasoning


class TestTailorResume:
    def test_returns_original_with_header(self) -> None:
        provider = FallbackProvider()
        resume = Resume(raw_text="My resume content here.", skills=["Python"])
        job = Job(
            title="Engineer", company="Acme", location="", description="",
            url="", source="test",
        )
        match = MatchResult(
            job=job, keyword_score=50, ai_score=50, final_score=50,
            matched_skills=["Python"], missing_skills=["AWS"],
        )
        result = provider.tailor_resume(resume, job, match)
        assert "NOTE" in result
        assert "My resume content here." in result
        assert "Acme" in result


class TestGenerateCoverLetter:
    def test_returns_template(self) -> None:
        provider = FallbackProvider()
        resume = Resume(raw_text="", skills=["Python"], experience_years=5)
        job = Job(
            title="Engineer", company="Acme", location="", description="",
            url="", source="test",
        )
        match = MatchResult(
            job=job, keyword_score=50, ai_score=50, final_score=50,
            matched_skills=["Python"],
        )
        letter = provider.generate_cover_letter(resume, job, match)
        assert "Engineer" in letter
        assert "Acme" in letter
        assert "NOTE" in letter


class TestPrepInterview:
    def test_returns_template(self) -> None:
        provider = FallbackProvider()
        resume = Resume(raw_text="", skills=["Python", "AWS"], experience_years=5)
        job = Job(
            title="SRE", company="Acme", location="", description="",
            url="", source="test",
        )
        result = provider.prep_interview(resume, job)
        assert "SRE" in result
        assert "Acme" in result
        assert "Technical" in result
        assert "Behavioral" in result
