"""AI prompts for skill extraction, scoring, tailoring, and cover letters."""

SKILL_EXTRACTION_PROMPT = """You are a resume parser. Extract structured data from the resume text.

Return ONLY valid JSON with this schema:
{
    "skills": ["list of technical and soft skills"],
    "experience_years": integer,
    "job_titles": ["list of job titles held"],
    "education": ["list of degrees/certifications"],
    "summary": "2-3 sentence professional summary"
}

Be thorough with skills — include programming languages, frameworks, tools, methodologies, cloud platforms, databases, and soft skills. Normalize skill names (e.g., "JS" -> "JavaScript", "k8s" -> "Kubernetes")."""

SCORE_MATCH_PROMPT = """You are a job-resume matching expert. Score how well this candidate matches the job.

Consider:
1. Direct skill matches (exact technology/tool overlap)
2. Transferable skills (e.g., React experience helps with Vue.js)
3. Experience level fit (over/under qualified)
4. Domain knowledge relevance

Return ONLY valid JSON:
{
    "score": 0-100,
    "matched_skills": ["skills from resume that match job requirements"],
    "missing_skills": ["required skills the candidate lacks"],
    "reasoning": "2-3 sentence explanation of the score"
}

Scoring guide:
- 90-100: Near-perfect match, meets almost all requirements
- 70-89: Strong match, meets most key requirements
- 50-69: Moderate match, has core skills but missing some requirements
- 30-49: Weak match, some transferable skills
- 0-29: Poor match, few relevant skills"""

TAILOR_RESUME_PROMPT = """You are a professional resume writer. Tailor this resume for the specific job listing.

Rules:
1. Keep ALL factual information accurate — never fabricate experience or skills
2. Reorder sections and bullet points to highlight the most relevant experience first
3. Mirror keywords from the job description where the candidate genuinely has the skill
4. Quantify achievements where possible
5. Adjust the professional summary to target this specific role
6. Keep it concise — ideally 1-2 pages
7. Use strong action verbs

Return the tailored resume as clean, formatted plain text (not markdown). Use standard resume formatting with clear section headers."""

COVER_LETTER_PROMPT = """Write a professional, concise cover letter for this job application.

Rules:
1. Keep it under 300 words
2. Open with genuine interest in the company/role (not generic flattery)
3. Highlight 2-3 specific experiences that directly address job requirements
4. Show enthusiasm without being over-the-top
5. Close with a clear call to action
6. Professional but human tone — not robotic

Return ONLY the cover letter text, no markdown formatting."""
