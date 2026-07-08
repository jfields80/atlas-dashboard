from flask import Blueprint, render_template, request, redirect, abort

from services.repositories.category_repository import CategoryRepository


categories_bp = Blueprint("categories", __name__)

repository = CategoryRepository()


@categories_bp.route("/categories")
def categories():
    categories = repository.get_all()

    return render_template(
        "categories.html",
        categories=categories
    )


@categories_bp.route("/categories/new")
def new_category():
    return render_template("new_category.html")


@categories_bp.route("/categories/create", methods=["POST"])
def create_category():
    repository.create(
        name=request.form["name"].strip(),
        slug=request.form["slug"].strip(),
        description=request.form.get(
            "description",
            ""
        ).strip(),
        industry=request.form.get(
            "industry",
            ""
        ).strip()
    )

    return redirect("/categories")


@categories_bp.route("/categories/edit/<int:category_id>")
def edit_category(category_id):
    category = repository.get(category_id)

    if category is None:
        abort(404)

    return render_template(
        "edit_category.html",
        category=category
    )


@categories_bp.route(
    "/categories/update/<int:category_id>",
    methods=["POST"]
)
def update_category(category_id):
    category = repository.get(category_id)

    if category is None:
        abort(404)

    active_value = request.form.get("active", "0")
    active = 1 if active_value == "1" else 0

    repository.update(
        category_id=category_id,
        name=request.form["name"].strip(),
        slug=request.form["slug"].strip(),
        description=request.form.get(
            "description",
            ""
        ).strip(),
        parent_id=category[4],
        industry=request.form.get(
            "industry",
            ""
        ).strip(),
        icon=category[6] or "",
        active=active
    )

    return redirect("/categories")


@categories_bp.route(
    "/categories/delete/<int:category_id>",
    methods=["POST"]
)
def delete_category(category_id):
    category = repository.get(category_id)

    if category is None:
        abort(404)

    repository.delete(category_id)

    return redirect("/categories")