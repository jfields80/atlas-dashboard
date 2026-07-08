from flask import Blueprint, render_template
import sqlite3

from config import DATABASE


analytics_bp = Blueprint("analytics", __name__)


def get_table_count(cursor, table_name):
    try:
        cursor.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        )

        result = cursor.fetchone()

        if result:
            return result[0]

        return 0

    except sqlite3.Error:
        return 0


def get_status_count(cursor, table_name, status):
    try:
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

    except sqlite3.Error:
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