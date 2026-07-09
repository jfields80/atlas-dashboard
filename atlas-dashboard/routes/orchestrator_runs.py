from flask import Blueprint, abort, render_template, request

from services.orchestrator_run_view_service import get_run_detail, list_runs


orchestrator_runs_bp = Blueprint("orchestrator_runs", __name__)


@orchestrator_runs_bp.route("/orchestrator/runs")
def runs():
    pipeline_filter = request.args.get("pipeline") or None
    run_records = list_runs(pipeline_name=pipeline_filter)

    return render_template(
        "orchestrator_runs.html",
        runs=run_records,
        pipeline_filter=pipeline_filter,
    )


@orchestrator_runs_bp.route("/orchestrator/runs/<run_id>")
def run_detail(run_id):
    detail = get_run_detail(run_id)

    if detail is None:
        abort(404)

    return render_template(
        "orchestrator_run_detail.html",
        run=detail["run"],
        stages=detail["stages"],
    )
