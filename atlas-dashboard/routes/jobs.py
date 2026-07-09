from flask import Blueprint, abort, jsonify, render_template

from services.operations_monitor_service import get_job_monitor_view


jobs_bp = Blueprint("jobs", __name__)


@jobs_bp.route("/jobs/<job_id>")
def job_status(job_id):
    view = get_job_monitor_view(job_id)

    if view is None:
        abort(404)

    return render_template(
        "job_status.html",
        job=view["job"],
        run=view["run"],
        stages=view["stages"],
    )


@jobs_bp.route("/jobs/<job_id>/status.json")
def job_status_json(job_id):
    view = get_job_monitor_view(job_id)

    if view is None:
        abort(404)

    job = view["job"]

    return jsonify(
        {
            "job_id": job.job_id,
            "state": job.state.value,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "error": job.error,
            "result": job.result,
            "run": view["run"],
            "stages": view["stages"],
        }
    )
