from flask import Blueprint, abort, render_template

from services.background_job_service import get_job


jobs_bp = Blueprint("jobs", __name__)


@jobs_bp.route("/jobs/<job_id>")
def job_status(job_id):
    job = get_job(job_id)

    if job is None:
        abort(404)

    return render_template("job_status.html", job=job)
