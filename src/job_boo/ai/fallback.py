"""Fallback provider when no AI API key is configured.

Uses keyword-only matching and basic text heuristics instead of LLM calls.
Search and export still work. Tailoring and cover letters are unavailable.
"""

from __future__ import annotations

import re

from job_boo.models import Job, MatchResult, Resume

# Common tech skills to recognize in resume text
KNOWN_SKILLS = {
    "python",
    "java",
    "javascript",
    "typescript",
    "go",
    "golang",
    "rust",
    "c++",
    "c#",
    "ruby",
    "php",
    "swift",
    "kotlin",
    "scala",
    "perl",
    "r",
    "matlab",
    "react",
    "angular",
    "vue",
    "svelte",
    "next.js",
    "nuxt",
    "django",
    "flask",
    "fastapi",
    "spring",
    "rails",
    "express",
    "node.js",
    "node",
    "aws",
    "azure",
    "gcp",
    "google cloud",
    "docker",
    "kubernetes",
    "k8s",
    "terraform",
    "ansible",
    "jenkins",
    "ci/cd",
    "github actions",
    "postgresql",
    "mysql",
    "mongodb",
    "redis",
    "elasticsearch",
    "dynamodb",
    "cassandra",
    "sqlite",
    "oracle",
    "sql server",
    "git",
    "linux",
    "bash",
    "rest",
    "graphql",
    "grpc",
    "kafka",
    "rabbitmq",
    "machine learning",
    "deep learning",
    "nlp",
    "computer vision",
    "pytorch",
    "tensorflow",
    "pandas",
    "numpy",
    "scikit-learn",
    "spark",
    "hadoop",
    "html",
    "css",
    "sass",
    "webpack",
    "vite",
    "tailwind",
    "agile",
    "scrum",
    "jira",
    "confluence",
    "figma",
    "microservices",
    "distributed systems",
    "system design",
}


class FallbackProvider:
    """Keyword-based fallback when no AI provider is available.

    Provides basic functionality:
    - extract_skills: regex + keyword matching from resume text
    - score_match: keyword overlap scoring (no semantic analysis)
    - tailor_resume: returns original resume (no tailoring without AI)
    - generate_cover_letter: returns a template (no generation without AI)
    """

    def extract_skills(self, resume_text: str) -> Resume:
        text_lower = resume_text.lower()
        found_skills: list[str] = []

        for skill in KNOWN_SKILLS:
            # Word boundary check to avoid partial matches
            pattern = r"\b" + re.escape(skill) + r"\b"
            if re.search(pattern, text_lower):
                found_skills.append(skill.title() if len(skill) > 2 else skill.upper())

        # Extract years of experience from patterns like "5+ years", "5 years"
        years = 0
        year_patterns = re.findall(
            r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience", text_lower
        )
        if year_patterns:
            years = max(int(y) for y in year_patterns)

        # Extract job titles from common patterns
        titles: list[str] = []
        title_patterns = [
            r"(?:senior|staff|lead|principal|junior)?\s*(?:software|backend|frontend|full[- ]?stack|data|devops|platform|site reliability|cloud|ml|machine learning)\s*(?:engineer|developer|architect|scientist|analyst)",
            r"(?:engineering|technical|product)\s*(?:manager|lead|director)",
        ]
        for pattern in title_patterns:
            matches = re.findall(pattern, text_lower)
            titles.extend(m.strip().title() for m in matches)

        # Extract education
        education: list[str] = []
        edu_patterns = [
            r"(?:bachelor|master|phd|doctorate|associate|b\.?s\.?|m\.?s\.?|m\.?b\.?a\.?|b\.?a\.?)\s+(?:of|in)\s+\w[\w\s,]+",
        ]
        for pattern in edu_patterns:
            matches = re.findall(pattern, text_lower)
            education.extend(m.strip().title() for m in matches)

        # Build summary from first ~200 chars that look like a summary
        summary = ""
        lines = resume_text.strip().split("\n")
        for line in lines[1:10]:
            stripped = line.strip()
            if len(stripped) > 50 and not stripped.startswith(
                ("http", "phone", "email", "+", "(", "@")
            ):
                summary = stripped[:200]
                break

        return Resume(
            raw_text=resume_text,
            skills=sorted(set(found_skills)),
            experience_years=years,
            job_titles=list(set(titles))[:5],
            education=list(set(education))[:3],
            summary=summary
            or "Professional with experience in " + ", ".join(found_skills[:5]),
        )

    def score_match(self, resume: Resume, job: Job) -> MatchResult:
        """Pure keyword matching — no AI semantic analysis."""
        resume_skills = {s.lower().strip() for s in resume.skills}
        job_text = (job.title + " " + job.description).lower()

        matched: list[str] = []
        for skill in resume_skills:
            if skill in job_text:
                matched.append(skill)
            elif len(skill) > 3:
                variants = [
                    skill.replace(" ", "-"),
                    skill.replace("-", " "),
                    skill.replace(".", ""),
                ]
                if any(v in job_text for v in variants):
                    matched.append(skill)

        # Extract skills from job description that candidate is missing
        missing: list[str] = []
        for skill in KNOWN_SKILLS:
            pattern = r"\b" + re.escape(skill) + r"\b"
            if re.search(pattern, job_text) and skill not in {
                s.lower() for s in matched
            }:
                missing.append(skill.title() if len(skill) > 2 else skill.upper())

        score = (
            (len(matched) / max(len(resume_skills), 1)) * 100 if resume_skills else 0
        )

        return MatchResult(
            job=job,
            keyword_score=score,
            ai_score=score,  # same as keyword score in fallback mode
            final_score=score,
            matched_skills=[s.title() for s in matched],
            missing_skills=missing[:10],
            reasoning=f"Keyword match: {len(matched)}/{len(resume_skills)} skills found in job description. "
            f"(Fallback mode — no AI scoring. Run 'job-boo setup-ai' for semantic analysis.)",
        )

    def tailor_resume(self, resume: Resume, job: Job, match: MatchResult) -> str:
        """Cannot tailor without AI — returns original with a note."""
        header = (
            f"[NOTE: This is your original resume. AI tailoring is unavailable.\n"
            f"Run 'job-boo setup-ai' to enable AI-powered resume customization.]\n"
            f"\nTarget: {job.title} at {job.company}\n"
            f"Matched skills: {', '.join(match.matched_skills)}\n"
            f"Missing skills: {', '.join(match.missing_skills)}\n"
            f"\n{'=' * 60}\n\n"
        )
        return header + resume.raw_text

    def generate_cover_letter(
        self, resume: Resume, job: Job, match: MatchResult
    ) -> str:
        """Cannot generate without AI — returns a template."""
        return (
            f"Dear Hiring Manager,\n\n"
            f"I am writing to express my interest in the {job.title} position at {job.company}.\n\n"
            f"With {resume.experience_years} years of experience and skills in "
            f"{', '.join(match.matched_skills[:5])}, I believe I would be a strong fit for this role.\n\n"
            f"[NOTE: This is a basic template. Run 'job-boo setup-ai' to generate "
            f"AI-powered personalized cover letters.]\n\n"
            f"Thank you for your consideration.\n\n"
            f"Sincerely,\n[Your Name]"
        )
