"""JobSpy integration for scraping LinkedIn, Indeed, Glassdoor, ZipRecruiter."""

from __future__ import annotations

import logging
from typing import Any

from job_boo.config import Config
from job_boo.models import Job

logger = logging.getLogger(__name__)

try:
    from jobspy import scrape_jobs

    JOBSPY_AVAILABLE = True
except ImportError:
    JOBSPY_AVAILABLE = False


def search_jobspy(config: Config) -> list[Job]:
    """Search jobs via JobSpy scraper across multiple sites.

    Supports LinkedIn, Indeed, Glassdoor, and ZipRecruiter.
    Returns an empty list if the jobspy package is not installed.
    """
    if not JOBSPY_AVAILABLE:
        logger.warning("python-jobspy is not installed. Run: pip install python-jobspy")
        return []

    jobspy_cfg = config.sources.jobspy
    if not jobspy_cfg.enabled:
        return []

    logger.warning(
        "JobSpy scrapes LinkedIn, Indeed, Glassdoor, and ZipRecruiter. "
        "This may violate their Terms of Service and could result in IP blocks "
        "or account suspension. Use at your own risk."
    )

    search_term = config.job_title
    if config.keywords:
        search_term += " " + " ".join(config.keywords)

    kwargs: dict[str, Any] = {
        "site_name": jobspy_cfg.sites,
        "search_term": search_term,
        "results_wanted": jobspy_cfg.results_per_site,
    }

    if config.location.city:
        kwargs["location"] = config.location.city

    if config.salary.min:
        kwargs["salary_min"] = config.salary.min
    if config.salary.max:
        kwargs["salary_max"] = config.salary.max

    if jobspy_cfg.proxy:
        kwargs["proxy"] = jobspy_cfg.proxy

    df = scrape_jobs(**kwargs)

    return _dataframe_to_jobs(df)


def _dataframe_to_jobs(df: Any) -> list[Job]:
    """Convert a JobSpy pandas DataFrame to a list of Job models."""
    jobs: list[Job] = []

    for _, row in df.iterrows():
        title = str(row.get("title", "") or "")
        company = str(row.get("company_name", "") or "")
        location = str(row.get("location", "") or "")
        description = str(row.get("description", "") or "")
        job_url = str(row.get("job_url", "") or "")
        site = str(row.get("site", "") or "")

        salary_min = _safe_int(row.get("min_amount"))
        salary_max = _safe_int(row.get("max_amount"))

        is_remote = bool(row.get("is_remote", False))
        posted_date = str(row.get("date_posted", "") or "")
        job_id = str(row.get("id", "") or "")

        jobs.append(
            Job(
                title=title,
                company=company,
                location=location,
                description=description,
                url=job_url,
                source=f"jobspy:{site}",
                salary_min=salary_min,
                salary_max=salary_max,
                remote=is_remote or "remote" in location.lower(),
                posted_date=posted_date,
                job_id=job_id,
                raw_data=row.to_dict() if hasattr(row, "to_dict") else {},
            )
        )

    return jobs


def _safe_int(value: Any) -> int:
    """Safely convert a value to int, returning 0 for None/NaN/invalid."""
    if value is None:
        return 0
    try:
        import math

        if isinstance(value, float) and math.isnan(value):
            return 0
        return int(value)
    except (ValueError, TypeError):
        return 0
