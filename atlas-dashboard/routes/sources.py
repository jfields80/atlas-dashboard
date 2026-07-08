from flask import Blueprint, redirect, render_template, url_for
import sqlite3

from config import DATABASE


sources_bp = Blueprint("sources", __name__)


@sources_bp.route("/sources")
def sources():
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            name,
            website,
            connector,
            enabled
        FROM research_sources
        ORDER BY name
        """
    )

    source_records = cursor.fetchall()

    connection.close()

    return render_template(
        "sources.html",
        sources=source_records
    )


@sources_bp.route(
    "/sources/<int:source_id>/toggle",
    methods=["POST"]
)
def toggle_source(source_id):
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE research_sources
        SET enabled = CASE
            WHEN enabled = 1 THEN 0
            ELSE 1
        END
        WHERE id = ?
        """,
        (source_id,)
    )

    connection.commit()
    connection.close()

    return redirect(url_for("sources.sources"))