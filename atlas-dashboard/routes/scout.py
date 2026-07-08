import sqlite3

from flask import (
    Blueprint,
    redirect,
    render_template,
    request,
    url_for
)

from config import DATABASE
from services.ai.scout import ScoutAI
from services.connectors import CONNECTORS


scout_bp = Blueprint(
    "scout",
    __name__
)


DEFAULT_MAX_RESULTS = 20
MIN_MAX_RESULTS = 1
MAX_MAX_RESULTS = 100


def get_registered_connectors():
    return {
        connector_name.lower()
        for connector_name in CONNECTORS
    }


def get_scout_page_data():
    connection = sqlite3.connect(
        DATABASE
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            name,
            status
        FROM projects
        ORDER BY name
        """
    )

    projects = cursor.fetchall()

    cursor.execute(
        """
        SELECT
            id,
            name,
            connector,
            enabled
        FROM research_sources
        ORDER BY name
        """
    )

    source_records = cursor.fetchall()

    connection.close()

    registered_connectors = (
        get_registered_connectors()
    )

    sources = [
        source
        for source in source_records
        if (
            str(source[2]).lower()
            in registered_connectors
            and int(source[3]) == 1
        )
    ]

    return projects, sources


def get_project(
    project_id
):
    connection = sqlite3.connect(
        DATABASE
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            name,
            status
        FROM projects
        WHERE id = ?
        """,
        (project_id,)
    )

    project = cursor.fetchone()

    connection.close()

    return project


def normalize_search_value(
    value
):
    return " ".join(
        str(value or "")
        .strip()
        .split()
    )


def normalize_location(
    value
):
    return normalize_search_value(
        value
    )


def parse_max_results(
    value
):
    try:
        max_results = int(value)

    except (
        TypeError,
        ValueError
    ):
        max_results = (
            DEFAULT_MAX_RESULTS
        )

    return max(
        MIN_MAX_RESULTS,
        min(
            max_results,
            MAX_MAX_RESULTS
        )
    )


def scout_redirect(
    error,
    project_id="",
    search_term="",
    location="",
    max_results=DEFAULT_MAX_RESULTS
):
    return redirect(
        url_for(
            "scout.scout",
            error=error,
            project_id=project_id,
            search_term=search_term,
            location=location,
            max_results=max_results
        )
    )


@scout_bp.route("/scout")
def scout():
    projects, sources = (
        get_scout_page_data()
    )

    selected_project_id = (
        request.args.get(
            "project_id",
            ""
        )
    )

    previous_search_term = (
        request.args.get(
            "search_term",
            ""
        )
    )

    previous_location = (
        request.args.get(
            "location",
            ""
        )
    )

    previous_max_results = (
        parse_max_results(
            request.args.get(
                "max_results",
                DEFAULT_MAX_RESULTS
            )
        )
    )

    error = request.args.get(
        "error",
        ""
    )

    error_messages = {
        "missing_project": (
            "Choose an Atlas project."
        ),
        "missing_search": (
            "Enter a business category "
            "or search phrase."
        ),
        "missing_location": (
            "Enter a city, state, or "
            "search area."
        ),
        "missing_source": (
            "Choose at least one "
            "research source."
        ),
        "invalid_project": (
            "The selected project no "
            "longer exists."
        ),
        "invalid_source": (
            "The selected research "
            "source is unavailable."
        )
    }

    return render_template(
        "scout.html",
        projects=projects,
        sources=sources,
        selected_project_id=(
            selected_project_id
        ),
        previous_search_term=(
            previous_search_term
        ),
        previous_location=(
            previous_location
        ),
        previous_max_results=(
            previous_max_results
        ),
        error_message=(
            error_messages.get(
                error,
                ""
            )
        )
    )


@scout_bp.route(
    "/start-research",
    methods=["POST"]
)
def start_research():
    submitted_project_id = (
        request.form.get(
            "project_id",
            ""
        )
    )

    search_term = normalize_search_value(
        request.form.get(
            "search_term",
            ""
        )
    )

    location = normalize_location(
        request.form.get(
            "location",
            ""
        )
    )

    submitted_sources = [
        source.lower().strip()
        for source
        in request.form.getlist(
            "sources"
        )
        if source.strip()
    ]

    max_results = parse_max_results(
        request.form.get(
            "max_results",
            DEFAULT_MAX_RESULTS
        )
    )

    try:
        project_id = int(
            submitted_project_id
        )

    except (
        TypeError,
        ValueError
    ):
        return scout_redirect(
            error="missing_project",
            search_term=search_term,
            location=location,
            max_results=max_results
        )

    if not search_term:
        return scout_redirect(
            error="missing_search",
            project_id=project_id,
            location=location,
            max_results=max_results
        )

    if not location:
        return scout_redirect(
            error="missing_location",
            project_id=project_id,
            search_term=search_term,
            max_results=max_results
        )

    if not submitted_sources:
        return scout_redirect(
            error="missing_source",
            project_id=project_id,
            search_term=search_term,
            location=location,
            max_results=max_results
        )

    project_record = get_project(
        project_id
    )

    if project_record is None:
        return scout_redirect(
            error="invalid_project",
            search_term=search_term,
            location=location,
            max_results=max_results
        )

    valid_sources = (
        get_registered_connectors()
    )

    sources = list(
        dict.fromkeys(
            source
            for source
            in submitted_sources
            if source in valid_sources
        )
    )

    if not sources:
        return scout_redirect(
            error="invalid_source",
            project_id=project_id,
            search_term=search_term,
            location=location,
            max_results=max_results
        )

    project_name = project_record[1]

    try:
        scout_ai = ScoutAI()

        results = scout_ai.run(
            project_id=project_id,
            search_term=search_term,
            location=location,
            sources=sources,
            max_results=max_results
        )

        if not isinstance(
            results,
            dict
        ):
            results = {}

        normalized_results = {
            "found": int(
                results.get(
                    "found",
                    0
                )
                or 0
            ),
            "inserted": int(
                results.get(
                    "inserted",
                    0
                )
                or 0
            ),
            "updated": int(
                results.get(
                    "updated",
                    0
                )
                or 0
            ),
            "skipped": int(
                results.get(
                    "skipped",
                    0
                )
                or 0
            ),
            "run_duplicates": int(
                results.get(
                    "run_duplicates",
                    0
                )
                or 0
            ),
            "invalid": int(
                results.get(
                    "invalid",
                    0
                )
                or 0
            )
        }

        return render_template(
            "scout_results.html",
            success=True,
            project_name=project_name,
            search_term=search_term,
            location=location,
            sources=sources,
            max_results=max_results,
            results=normalized_results,
            error_message=""
        )

    except Exception as error:
        print(
            "[SCOUT ERROR] "
            f"{type(error).__name__}: "
            f"{error}"
        )

        return render_template(
            "scout_results.html",
            success=False,
            project_name=project_name,
            search_term=search_term,
            location=location,
            sources=sources,
            max_results=max_results,
            results={
                "found": 0,
                "inserted": 0,
                "updated": 0,
                "skipped": 0,
                "run_duplicates": 0,
                "invalid": 0
            },
            error_message=str(error)
        ), 500