"""Parse a single job listing from a URL."""

from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from job_boo.models import Job


def parse_job_url(url: str) -> Job:
    """Fetch a job listing URL and extract job details."""
    resp = httpx.get(
        url,
        follow_redirects=True,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Extract title from common patterns
    title = ""
    for selector in [
        "h1",
        '[data-testid="jobTitle"]',
        ".job-title",
        ".posting-headline h2",
    ]:
        el = soup.select_one(selector)
        if el:
            title = el.get_text(strip=True)
            break
    if not title:
        title = soup.title.string if soup.title else ""

    # Extract company
    company = ""
    for selector in [
        ".company-name",
        '[data-testid="companyName"]',
        ".posting-categories .sort-by-team",
    ]:
        el = soup.select_one(selector)
        if el:
            company = el.get_text(strip=True)
            break

    # Extract description
    description = ""
    for selector in [
        ".job-description",
        ".posting-description",
        '[data-testid="jobDescription"]',
        "article",
        ".content",
    ]:
        el = soup.select_one(selector)
        if el:
            description = el.get_text(separator=" ", strip=True)
            break
    if not description:
        # Fallback: get main content text
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        description = soup.get_text(separator=" ", strip=True)[:5000]

    # Extract location
    location = ""
    for selector in [
        ".location",
        '[data-testid="location"]',
        ".posting-categories .sort-by-location",
    ]:
        el = soup.select_one(selector)
        if el:
            location = el.get_text(strip=True)
            break

    return Job(
        title=title,
        company=company,
        location=location,
        description=description[:5000],
        url=url,
        source="url",
        remote="remote" in (location + " " + title + " " + description[:500]).lower(),
    )
