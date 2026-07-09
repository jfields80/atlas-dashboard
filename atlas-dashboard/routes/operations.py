from flask import Blueprint, redirect, render_template, request, url_for

from services.background_job_service import submit_job
from services.operations_registry import list_operations
from services.pipeline_execution_service import start_directory_launch_run


operations_bp = Blueprint("operations", __name__)


@operations_bp.route("/operations")
def operations_center():
    return render_template(
        "operations_center.html",
        operations=list_operations(),
    )


@operations_bp.route("/operations/directory-launch/run", methods=["POST"])
def run_directory_launch():
    form_values = {
        "committee_run_id": request.form.get("committee_run_id", ""),
        "project_slug": request.form.get("project_slug", ""),
        "description": request.form.get("description", ""),
        "target_customer": request.form.get("target_customer", ""),
        "competition_level": request.form.get("competition_level", ""),
        "monetization_signals": request.form.get("monetization_signals", ""),
    }

    job_id = submit_job(lambda: start_directory_launch_run(**form_values))

    return redirect(url_for("jobs.job_status", job_id=job_id))
