"""Generate a standalone HTML dashboard from the job-boo SQLite database."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from job_boo.config import DB_PATH, OUTPUT_DIR


# ---------------------------------------------------------------------------
# Data queries
# ---------------------------------------------------------------------------


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _query_state_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Count jobs per state."""
    rows = conn.execute(
        "SELECT state, COUNT(*) as cnt FROM jobs GROUP BY state"
    ).fetchall()
    return {r["state"]: r["cnt"] for r in rows}


def _query_funnel(state_counts: dict[str, int]) -> list[dict[str, Any]]:
    """Build cumulative funnel stages."""
    ordered_states = ["found", "scored", "tailored", "applied", "closed"]
    # Cumulative: each stage includes all jobs that reached it or beyond
    progression = [
        "found",
        "scored",
        "tailored",
        "ready",
        "applied",
        "followed_up",
        "closed",
        "skipped",
    ]
    cumulative: list[dict[str, Any]] = []
    for stage in ordered_states:
        stage_idx = progression.index(stage) if stage in progression else 0
        total = sum(
            cnt
            for st, cnt in state_counts.items()
            if st in progression and progression.index(st) >= stage_idx
        )
        cumulative.append({"stage": stage.capitalize(), "count": total})
    return cumulative


def _query_daily_applications(
    conn: sqlite3.Connection, days: int = 30
) -> list[dict[str, Any]]:
    """Daily application counts for the last N days."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT DATE(applied_at) as day, COUNT(*) as cnt "
        "FROM jobs WHERE applied_at IS NOT NULL AND DATE(applied_at) >= ? "
        "GROUP BY DATE(applied_at) ORDER BY day",
        (cutoff,),
    ).fetchall()
    return [{"day": r["day"], "count": r["cnt"]} for r in rows]


def _query_score_distribution(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Bucket final_score into ranges."""
    rows = conn.execute(
        "SELECT final_score FROM jobs WHERE final_score IS NOT NULL"
    ).fetchall()
    buckets = {"0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}
    for r in rows:
        score = r["final_score"]
        if score < 20:
            buckets["0-20"] += 1
        elif score < 40:
            buckets["20-40"] += 1
        elif score < 60:
            buckets["40-60"] += 1
        elif score < 80:
            buckets["60-80"] += 1
        else:
            buckets["80-100"] += 1
    return [{"bucket": k, "count": v} for k, v in buckets.items()]


def _query_jobs_by_source(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT source, COUNT(*) as cnt FROM jobs GROUP BY source ORDER BY cnt DESC"
    ).fetchall()
    return [{"source": r["source"] or "unknown", "count": r["cnt"]} for r in rows]


def _query_top_companies(
    conn: sqlite3.Connection, limit: int = 10
) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT company, COUNT(*) as cnt FROM jobs GROUP BY company ORDER BY cnt DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [{"company": r["company"], "count": r["cnt"]} for r in rows]


def _query_skill_gaps(
    conn: sqlite3.Connection, limit: int = 10
) -> list[dict[str, Any]]:
    """Top missing skills across all scored jobs."""
    rows = conn.execute(
        "SELECT missing_skills FROM jobs WHERE missing_skills IS NOT NULL AND missing_skills != ''"
    ).fetchall()
    counter: Counter[str] = Counter()
    for r in rows:
        raw = r["missing_skills"]
        try:
            skills = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            skills = [s.strip() for s in raw.split(",") if s.strip()]
        for skill in skills:
            counter[skill] += 1
    top = counter.most_common(limit)
    return [{"skill": s, "count": c} for s, c in top]


def _query_company_history(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT company, title, final_score, applied_at, state "
        "FROM jobs WHERE state IN ('applied', 'followed_up', 'closed') "
        "ORDER BY company, applied_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def _query_recent_applications(
    conn: sqlite3.Connection, limit: int = 20
) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT applied_at, company, title, final_score, url "
        "FROM jobs WHERE applied_at IS NOT NULL "
        "ORDER BY applied_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def _query_stats(
    conn: sqlite3.Connection, state_counts: dict[str, int]
) -> dict[str, Any]:
    """Aggregate stats for the top cards."""
    total = sum(state_counts.values())
    applied = sum(state_counts.get(s, 0) for s in ("applied", "followed_up", "closed"))

    row = conn.execute(
        "SELECT AVG(final_score) as avg_score FROM jobs WHERE final_score IS NOT NULL"
    ).fetchone()
    avg_score = (
        round(row["avg_score"], 1) if row and row["avg_score"] is not None else 0
    )

    row = conn.execute("SELECT MIN(created_at) as earliest FROM jobs").fetchone()
    if row and row["earliest"]:
        try:
            earliest = datetime.fromisoformat(row["earliest"].replace("Z", "+00:00"))
            days_active = (datetime.now().astimezone() - earliest).days
        except (ValueError, TypeError):
            days_active = 0
    else:
        days_active = 0

    row = conn.execute(
        "SELECT source, COUNT(*) as cnt FROM jobs GROUP BY source ORDER BY cnt DESC LIMIT 1"
    ).fetchone()
    top_source = row["source"] if row else "N/A"

    return {
        "total_jobs": total,
        "total_applied": applied,
        "avg_score": avg_score,
        "days_active": days_active,
        "top_source": top_source,
    }


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

_CSS = """
:root {
    --bg: #0f1117;
    --card: #1a1d27;
    --border: #2a2d3a;
    --text: #e1e4ed;
    --text-dim: #8b8fa3;
    --accent: #6c5ce7;
    --accent2: #00cec9;
    --accent3: #fd79a8;
    --accent4: #fdcb6e;
    --accent5: #55efc4;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    padding: 2rem;
    line-height: 1.6;
}
h1 { font-size: 1.8rem; margin-bottom: 0.5rem; }
h2 { font-size: 1.1rem; color: var(--text-dim); margin-bottom: 2rem; font-weight: 400; }
h3 { font-size: 1rem; margin-bottom: 1rem; color: var(--accent2); text-transform: uppercase; letter-spacing: 0.05em; }

.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
}
.stat-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    text-align: center;
}
.stat-card .value {
    font-size: 2rem;
    font-weight: 700;
    color: var(--accent);
}
.stat-card .label {
    font-size: 0.8rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 0.25rem;
}

.charts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2rem;
}
.chart-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
}
.chart-card canvas { max-height: 320px; }

.table-section {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    overflow-x: auto;
}
table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
}
th {
    text-align: left;
    padding: 0.6rem 0.8rem;
    border-bottom: 2px solid var(--border);
    color: var(--text-dim);
    text-transform: uppercase;
    font-size: 0.75rem;
    letter-spacing: 0.05em;
}
td {
    padding: 0.5rem 0.8rem;
    border-bottom: 1px solid var(--border);
}
tr:hover td { background: rgba(108, 92, 231, 0.05); }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

footer {
    text-align: center;
    color: var(--text-dim);
    font-size: 0.75rem;
    margin-top: 2rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border);
}
"""


def _chart_colors(count: int) -> list[str]:
    palette = [
        "#6c5ce7",
        "#00cec9",
        "#fd79a8",
        "#fdcb6e",
        "#55efc4",
        "#a29bfe",
        "#81ecec",
        "#fab1a0",
        "#ffeaa7",
        "#74b9ff",
    ]
    return [palette[i % len(palette)] for i in range(count)]


def _build_stat_cards_html(stats: dict[str, Any]) -> str:
    cards = [
        (str(stats["total_jobs"]), "Total Jobs Tracked"),
        (str(stats["total_applied"]), "Total Applied"),
        (str(stats["avg_score"]), "Avg Match Score"),
        (str(stats["days_active"]), "Days Active"),
        (stats["top_source"], "Top Source"),
    ]
    items = ""
    for value, label in cards:
        items += (
            f'<div class="stat-card">'
            f'<div class="value">{value}</div>'
            f'<div class="label">{label}</div>'
            f"</div>\n"
        )
    return f'<div class="stats-grid">{items}</div>'


def _build_table_html(title: str, headers: list[str], rows: list[list[str]]) -> str:
    header_cells = "".join(f"<th>{h}</th>" for h in headers)
    body_rows = ""
    for row in rows:
        cells = "".join(f"<td>{c}</td>" for c in row)
        body_rows += f"<tr>{cells}</tr>\n"
    return (
        f'<div class="table-section"><h3>{title}</h3>'
        f"<table><thead><tr>{header_cells}</tr></thead>"
        f"<tbody>{body_rows}</tbody></table></div>"
    )


def _escape(text: str | None) -> str:
    if text is None:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _build_html(
    stats: dict[str, Any],
    funnel: list[dict[str, Any]],
    daily_apps: list[dict[str, Any]],
    score_dist: list[dict[str, Any]],
    by_source: list[dict[str, Any]],
    top_companies: list[dict[str, Any]],
    skill_gaps: list[dict[str, Any]],
    company_history: list[dict[str, Any]],
    recent_apps: list[dict[str, Any]],
    state_counts: dict[str, int],
) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    stat_cards = _build_stat_cards_html(stats)

    # State summary table
    state_rows = [[_escape(s), str(c)] for s, c in sorted(state_counts.items())]
    state_table = _build_table_html("State Summary", ["State", "Count"], state_rows)

    # Company history table
    history_rows = [
        [
            _escape(r.get("company")),
            _escape(r.get("title")),
            str(r.get("final_score") or ""),
            _escape(r.get("applied_at") or ""),
            _escape(r.get("state")),
        ]
        for r in company_history
    ]
    history_table = _build_table_html(
        "Company Application History",
        ["Company", "Title", "Score", "Applied At", "State"],
        history_rows,
    )

    # Recent applications table
    recent_rows = [
        [
            _escape(r.get("applied_at") or ""),
            _escape(r.get("company")),
            _escape(r.get("title")),
            str(r.get("final_score") or ""),
            f'<a href="{_escape(r.get("url") or "")}" target="_blank">Link</a>'
            if r.get("url")
            else "",
        ]
        for r in recent_apps
    ]
    recent_table = _build_table_html(
        "Recent Applications",
        ["Date", "Company", "Title", "Score", "URL"],
        recent_rows,
    )

    # Chart data as JSON
    funnel_labels = json.dumps([f["stage"] for f in funnel])
    funnel_data = json.dumps([f["count"] for f in funnel])
    funnel_colors = json.dumps(_chart_colors(len(funnel)))

    daily_labels = json.dumps([d["day"] for d in daily_apps])
    daily_data = json.dumps([d["count"] for d in daily_apps])

    score_labels = json.dumps([s["bucket"] for s in score_dist])
    score_data = json.dumps([s["count"] for s in score_dist])
    score_colors = json.dumps(_chart_colors(len(score_dist)))

    source_labels = json.dumps([s["source"] for s in by_source])
    source_data = json.dumps([s["count"] for s in by_source])
    source_colors = json.dumps(_chart_colors(len(by_source)))

    company_labels = json.dumps([c["company"] for c in top_companies])
    company_data = json.dumps([c["count"] for c in top_companies])
    company_colors = json.dumps(_chart_colors(len(top_companies)))

    skill_labels = json.dumps([s["skill"] for s in skill_gaps])
    skill_data = json.dumps([s["count"] for s in skill_gaps])
    skill_colors = json.dumps(_chart_colors(len(skill_gaps)))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Job Boo — Application Dashboard</title>
<style>{_CSS}</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
<h1>Job Boo — Application Dashboard</h1>
<h2>Generated {timestamp}</h2>

{stat_cards}

<div class="charts-grid">

<div class="chart-card">
<h3>Application Funnel</h3>
<canvas id="funnelChart"></canvas>
</div>

<div class="chart-card">
<h3>Applications Over Time (30d)</h3>
<canvas id="dailyChart"></canvas>
</div>

<div class="chart-card">
<h3>Score Distribution</h3>
<canvas id="scoreChart"></canvas>
</div>

<div class="chart-card">
<h3>Jobs by Source</h3>
<canvas id="sourceChart"></canvas>
</div>

<div class="chart-card">
<h3>Top Companies</h3>
<canvas id="companyChart"></canvas>
</div>

<div class="chart-card">
<h3>Skill Gaps</h3>
<canvas id="skillChart"></canvas>
</div>

</div>

{state_table}
{history_table}
{recent_table}

<footer>Job Boo Dashboard &middot; Generated {timestamp}</footer>

<script>
const chartDefaults = {{
    color: '#8b8fa3',
    borderColor: '#2a2d3a',
}};
Chart.defaults.color = chartDefaults.color;
Chart.defaults.borderColor = chartDefaults.borderColor;

// Funnel
new Chart(document.getElementById('funnelChart'), {{
    type: 'bar',
    data: {{
        labels: {funnel_labels},
        datasets: [{{
            data: {funnel_data},
            backgroundColor: {funnel_colors},
            borderRadius: 6,
        }}]
    }},
    options: {{
        indexAxis: 'y',
        plugins: {{ legend: {{ display: false }} }},
        scales: {{ x: {{ grid: {{ color: '#2a2d3a' }} }}, y: {{ grid: {{ display: false }} }} }}
    }}
}});

// Daily applications
new Chart(document.getElementById('dailyChart'), {{
    type: 'line',
    data: {{
        labels: {daily_labels},
        datasets: [{{
            label: 'Applications',
            data: {daily_data},
            borderColor: '#6c5ce7',
            backgroundColor: 'rgba(108,92,231,0.1)',
            fill: true,
            tension: 0.3,
            pointRadius: 4,
            pointBackgroundColor: '#6c5ce7',
        }}]
    }},
    options: {{
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
            x: {{ grid: {{ color: '#2a2d3a' }} }},
            y: {{ beginAtZero: true, grid: {{ color: '#2a2d3a' }} }}
        }}
    }}
}});

// Score distribution
new Chart(document.getElementById('scoreChart'), {{
    type: 'bar',
    data: {{
        labels: {score_labels},
        datasets: [{{
            data: {score_data},
            backgroundColor: {score_colors},
            borderRadius: 6,
        }}]
    }},
    options: {{
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
            x: {{ grid: {{ display: false }} }},
            y: {{ beginAtZero: true, grid: {{ color: '#2a2d3a' }} }}
        }}
    }}
}});

// Jobs by source
new Chart(document.getElementById('sourceChart'), {{
    type: 'doughnut',
    data: {{
        labels: {source_labels},
        datasets: [{{
            data: {source_data},
            backgroundColor: {source_colors},
            borderWidth: 0,
        }}]
    }},
    options: {{
        plugins: {{ legend: {{ position: 'right', labels: {{ padding: 16 }} }} }},
        cutout: '55%',
    }}
}});

// Top companies
new Chart(document.getElementById('companyChart'), {{
    type: 'bar',
    data: {{
        labels: {company_labels},
        datasets: [{{
            data: {company_data},
            backgroundColor: {company_colors},
            borderRadius: 6,
        }}]
    }},
    options: {{
        indexAxis: 'y',
        plugins: {{ legend: {{ display: false }} }},
        scales: {{ x: {{ grid: {{ color: '#2a2d3a' }} }}, y: {{ grid: {{ display: false }} }} }}
    }}
}});

// Skill gaps
new Chart(document.getElementById('skillChart'), {{
    type: 'bar',
    data: {{
        labels: {skill_labels},
        datasets: [{{
            data: {skill_data},
            backgroundColor: {skill_colors},
            borderRadius: 6,
        }}]
    }},
    options: {{
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
            x: {{ grid: {{ display: false }} }},
            y: {{ beginAtZero: true, grid: {{ color: '#2a2d3a' }} }}
        }}
    }}
}});
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_dashboard(
    db_path: Path | None = None,
    output_path: Path | None = None,
) -> Path:
    """Generate a standalone HTML dashboard from the job-boo SQLite database.

    Args:
        db_path: Path to the SQLite database. Defaults to config.DB_PATH.
        output_path: Path for the output HTML file. Defaults to OUTPUT_DIR/dashboard.html.

    Returns:
        Path to the generated HTML file.
    """
    resolved_db = db_path or DB_PATH
    resolved_output = output_path or (OUTPUT_DIR / "dashboard.html")
    resolved_output.parent.mkdir(parents=True, exist_ok=True)

    conn = _connect(resolved_db)
    try:
        state_counts = _query_state_counts(conn)
        funnel = _query_funnel(state_counts)
        daily_apps = _query_daily_applications(conn)
        score_dist = _query_score_distribution(conn)
        by_source = _query_jobs_by_source(conn)
        top_companies = _query_top_companies(conn)
        skill_gaps = _query_skill_gaps(conn)
        company_history = _query_company_history(conn)
        recent_apps = _query_recent_applications(conn)
        stats = _query_stats(conn, state_counts)
    finally:
        conn.close()

    html = _build_html(
        stats=stats,
        funnel=funnel,
        daily_apps=daily_apps,
        score_dist=score_dist,
        by_source=by_source,
        top_companies=top_companies,
        skill_gaps=skill_gaps,
        company_history=company_history,
        recent_apps=recent_apps,
        state_counts=state_counts,
    )

    resolved_output.write_text(html, encoding="utf-8")
    return resolved_output
