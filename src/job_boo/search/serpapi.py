"""Google Jobs search via SerpAPI."""

from __future__ import annotations

import httpx

from job_boo.config import Config
from job_boo.models import Job


def search_serpapi(config: Config) -> list[Job]:
    """Search Google Jobs via SerpAPI."""
    api_key = config.sources.serpapi.resolve_key()
    if not api_key:
        return []

    query = config.job_title
    if config.keywords:
        query += " " + " ".join(config.keywords)

    params: dict[str, str | int] = {
        "engine": "google_jobs",
        "q": query,
        "api_key": api_key,
        "num": 40,
    }

    if config.location.city:
        params["location"] = config.location.city
    if config.location.preference == "remote":
        params["ltype"] = "1"  # remote filter

    resp = httpx.get("https://serpapi.com/search", params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    jobs: list[Job] = []
    for item in data.get("jobs_results", []):
        detected_exts = item.get("detected_extensions", {})
        jobs.append(Job(
            title=item.get("title", ""),
            company=item.get("company_name", ""),
            location=item.get("location", ""),
            description=item.get("description", ""),
            url=item.get("apply_options", [{}])[0].get("link", "") if item.get("apply_options") else "",
            source="serpapi",
            remote="remote" in item.get("location", "").lower(),
            salary_min=_parse_salary(detected_exts.get("salary", "")),
            posted_date=detected_exts.get("posted_at", ""),
            job_id=item.get("job_id", ""),
            raw_data=item,
        ))

    return jobs


def _parse_salary(salary_str: str) -> int:
    """Extract approximate salary from string like '$120K-$160K'."""
    if not salary_str:
        return 0
    import re
    numbers = re.findall(r"[\d,]+", salary_str.replace("K", "000").replace("k", "000"))
    if numbers:
        return int(numbers[0].replace(",", ""))
    return 0
