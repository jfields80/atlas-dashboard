from flask import Blueprint, redirect, render_template, request, url_for

from services.database import Database


projects_bp = Blueprint("projects", __name__)


@projects_bp.route("/projects")
def projects():
    db = Database()
    project_records = db.get_projects()

    return render_template(
        "projects.html",
        projects=project_records
    )


@projects_bp.route("/new-project", methods=["GET", "POST"])
def new_project():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        status = request.form.get("status", "Planning").strip()

        allowed_statuses = {
            "Planning",
            "Active",
            "Paused",
            "Complete"
        }

        if status not in allowed_statuses:
            status = "Planning"

        if not name:
            return render_template(
                "new_project.html",
                error="Project name is required.",
                name=name,
                status=status
            )

        db = Database()
        connection = db.connect()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO projects (
                name,
                status
            )
            VALUES (?, ?)
            """,
            (name, status)
        )

        connection.commit()
        connection.close()

        return redirect(url_for("projects.projects"))

    return render_template(
        "new_project.html",
        error=None,
        name="",
        status="Planning"
    )


@projects_bp.route("/delete/<int:project_id>")
def delete_project(project_id):
    db = Database()
    connection = db.connect()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM projects
        WHERE id = ?
        """,
        (project_id,)
    )

    connection.commit()
    connection.close()

    return redirect(url_for("projects.projects"))