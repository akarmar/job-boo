"""Adzuna job search API."""

from __future__ import annotations

import httpx

from job_boo.config import Config
from job_boo.models import Job


def search_adzuna(config: Config) -> list[Job]:
    """Search jobs via Adzuna API (free tier: 1000 req/month)."""
    app_id = config.sources.adzuna.resolve_app_id()
    api_key = config.sources.adzuna.resolve_key()
    country = config.sources.adzuna.country
    if not app_id or not api_key:
        return []

    query = config.job_title
    if config.keywords:
        query += " " + " ".join(config.keywords)

    params: dict[str, str | int] = {
        "app_id": app_id,
        "app_key": api_key,
        "what": query,
        "results_per_page": 50,
        "content-type": "application/json",
    }

    if config.location.city:
        params["where"] = config.location.city

    if config.salary.min:
        params["salary_min"] = config.salary.min
    if config.salary.max:
        params["salary_max"] = config.salary.max

    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
    resp = httpx.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    jobs: list[Job] = []
    for item in data.get("results", []):
        location_name = item.get("location", {}).get("display_name", "")
        jobs.append(
            Job(
                title=item.get("title", ""),
                company=item.get("company", {}).get("display_name", ""),
                location=location_name,
                description=item.get("description", ""),
                url=item.get("redirect_url", ""),
                source="adzuna",
                salary_min=int(item.get("salary_min", 0) or 0),
                salary_max=int(item.get("salary_max", 0) or 0),
                remote="remote" in location_name.lower()
                or "remote" in item.get("title", "").lower(),
                posted_date=item.get("created", ""),
                job_id=item.get("id", ""),
                raw_data=item,
            )
        )

    return jobs
