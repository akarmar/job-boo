"""JSearch (RapidAPI) — aggregates Google for Jobs data (LinkedIn, Indeed, Glassdoor, etc.)."""

from __future__ import annotations

import httpx

from job_boo.config import Config
from job_boo.models import Job

JSEARCH_URL = "https://jsearch.p.rapidapi.com/search"


def search_jsearch(config: Config) -> list[Job]:
    """Search JSearch API via RapidAPI."""
    api_key = config.sources.jsearch.resolve_key()
    if not api_key:
        raise RuntimeError("JSearch API key not configured")

    query = config.job_title
    if config.keywords:
        query += " " + " ".join(config.keywords)

    params: dict[str, str | int] = {
        "query": query,
        "page": "1",
        "num_pages": "1",
    }

    if config.location.city:
        params["query"] += f" in {config.location.city}"

    if config.location.preference == "remote":
        params["remote_jobs_only"] = "true"

    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }

    resp = httpx.get(JSEARCH_URL, params=params, headers=headers, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"JSearch API returned HTTP {resp.status_code}")
    content_type = resp.headers.get("content-type", "")
    if "application/json" not in content_type and "text/json" not in content_type:
        raise RuntimeError(f"JSearch returned unexpected content-type: {content_type}")
    data = resp.json()

    jobs: list[Job] = []
    for item in data.get("data", []):
        description = item.get("job_description", "") or ""
        salary_min = item.get("job_min_salary") or 0
        salary_max = item.get("job_max_salary") or 0

        location_parts = []
        if item.get("job_city"):
            location_parts.append(item["job_city"])
        if item.get("job_state"):
            location_parts.append(item["job_state"])
        if item.get("job_country"):
            location_parts.append(item["job_country"])
        location_str = ", ".join(location_parts) if location_parts else ""

        is_remote = bool(item.get("job_is_remote"))

        jobs.append(
            Job(
                title=item.get("job_title", ""),
                company=item.get("employer_name", ""),
                location=location_str,
                description=description,
                url=item.get("job_apply_link") or item.get("job_google_link", ""),
                source="jsearch",
                remote=is_remote,
                salary_min=int(salary_min) if salary_min else 0,
                salary_max=int(salary_max) if salary_max else 0,
                posted_date=item.get("job_posted_at_datetime_utc", ""),
                job_id=item.get("job_id", ""),
                raw_data=item,
            )
        )

    return jobs
