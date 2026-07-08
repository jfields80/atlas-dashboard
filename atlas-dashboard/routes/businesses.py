from flask import Blueprint, render_template, request

from services.database import Database

businesses_bp = Blueprint("businesses", __name__)


@businesses_bp.route("/businesses")
def businesses():
    database = Database()

    detailed_records = database.get_businesses_detailed()

    business_records = [
        (
            record["business_name"],
            record["category"],
            record["city"],
            record["state"],
            record["status"],
            record["id"]
        )
        for record in detailed_records
    ]

    duplicate_summary = database.get_duplicate_summary()

    deleted = request.args.get("deleted") == "1"

    return render_template(
        "businesses.html",
        businesses=business_records,
        duplicate_summary=duplicate_summary,
        deleted=deleted
    )