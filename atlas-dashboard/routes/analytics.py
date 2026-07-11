from flask import Blueprint, render_template
import sqlite3

from config import DATABASE


analytics_bp = Blueprint("analytics", __name__)

# Fixed allowlist of table names this module is authorized to query.
# get_table_count/get_status_count interpolate table_name into SQL text
# because SQLite does not support parameter binding for identifiers
# (table/column names) — only for values. Every call site in this module
# passes a literal from this set; validating against it here closes the
# SQL-identifier-injection shape without changing query semantics for any
# currently authorized table (AES-REVIEW-001A #5).
_ALLOWED_TABLE_NAMES = frozenset(
    {"projects", "businesses", "categories", "jobs"}
)


def _validate_table_name(table_name):
    if table_name not in _ALLOWED_TABLE_NAMES:
        raise ValueError("unauthorized table name: %r" % (table_name,))


def get_table_count(cursor, table_name):
    try:
        _validate_table_name(table_name)
        cursor.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        )

        result = cursor.fetchone()

        if result:
            return result[0]

        return 0

    except (sqlite3.Error, ValueError):
        return 0


def get_status_count(cursor, table_name, status):
    try:
        _validate_table_name(table_name)
        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM {table_name}
            WHERE LOWER(status) = LOWER(?)
            """,
            (status,)
        )

        result = cursor.fetchone()

        if result:
            return result[0]

        return 0

    except (sqlite3.Error, ValueError):
        return 0


@analytics_bp.route("/analytics")
def analytics():
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    project_count = get_table_count(
        cursor,
        "projects"
    )

    business_count = get_table_count(
        cursor,
        "businesses"
    )

    category_count = get_table_count(
        cursor,
        "categories"
    )

    job_count = get_table_count(
        cursor,
        "jobs"
    )

    active_project_count = get_status_count(
        cursor,
        "projects",
        "active"
    )

    planning_project_count = get_status_count(
        cursor,
        "projects",
        "planning"
    )

    completed_job_count = get_status_count(
        cursor,
        "jobs",
        "complete"
    )

    running_job_count = get_status_count(
        cursor,
        "jobs",
        "running"
    )

    verified_business_count = get_status_count(
        cursor,
        "businesses",
        "verified"
    )

    found_business_count = get_status_count(
        cursor,
        "businesses",
        "found"
    )

    connection.close()

    analytics_data = {
        "projects": project_count,
        "businesses": business_count,
        "categories": category_count,
        "jobs": job_count,
        "active_projects": active_project_count,
        "planning_projects": planning_project_count,
        "completed_jobs": completed_job_count,
        "running_jobs": running_job_count,
        "verified_businesses": verified_business_count,
        "found_businesses": found_business_count,
        "ai_employees": 7
    }

    return render_template(
        "analytics.html",
        analytics=analytics_data
    )