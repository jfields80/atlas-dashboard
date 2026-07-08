from flask import Blueprint, render_template

employees_bp = Blueprint("employees", __name__)


@employees_bp.route("/employees")
def employees():
    return render_template("employees.html")