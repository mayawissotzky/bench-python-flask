from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from . import bp, service
from .forms import TAG_COLORS, TagFormError, parse_id_list, parse_tag_form


@bp.get("/")
def index():
    return render_template(
        "tags/index.html",
        rows=service.tag_overview(current_user.id),
        colors=TAG_COLORS,
        max_tags=service.MAX_TAGS_PER_USER,
    )


@bp.post("/")
def create():
    try:
        fields = parse_tag_form(request.form)
        if service.name_taken(current_user.id, fields["name"]):
            raise TagFormError("You already have a tag with that name.")
        tag = service.create_tag(current_user.id, fields)
    except (TagFormError, service.TagLimitError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("tags.index"))
    except IntegrityError:
        db.session.rollback()
        flash("You already have a tag with that name.", "error")
        return redirect(url_for("tags.index"))
    flash(f"Tag “{tag.name}” created.", "success")
    return redirect(url_for("tags.index"))


@bp.get("/<int:tag_id>")
def detail(tag_id):
    tag = service.get_user_tag_or_404(current_user.id, tag_id)
    status = request.args.get("status", "")
    if status not in service.STATUSES:
        status = ""
    expenses = service.tagged_expenses(current_user.id, tag, status or None)
    return render_template(
        "tags/detail.html",
        tag=tag,
        expenses=expenses,
        totals=service.totals_by_currency(expenses),
        status=status,
        statuses=service.STATUSES,
    )


@bp.route("/<int:tag_id>/edit", methods=["GET", "POST"])
def edit(tag_id):
    tag = service.get_user_tag_or_404(current_user.id, tag_id)
    if request.method == "POST":
        try:
            fields = parse_tag_form(request.form)
            if service.name_taken(current_user.id, fields["name"], exclude_id=tag.id):
                raise TagFormError("You already have a tag with that name.")
            service.update_tag(tag, fields)
        except TagFormError as exc:
            flash(str(exc), "error")
            return redirect(url_for("tags.edit", tag_id=tag.id))
        except IntegrityError:
            db.session.rollback()
            flash("You already have a tag with that name.", "error")
            return redirect(url_for("tags.edit", tag_id=tag.id))
        flash("Tag updated.", "success")
        return redirect(url_for("tags.detail", tag_id=tag.id))
    return render_template("tags/edit.html", tag=tag, colors=TAG_COLORS)


@bp.post("/<int:tag_id>/delete")
def delete(tag_id):
    tag = service.get_user_tag_or_404(current_user.id, tag_id)
    name = tag.name
    service.delete_tag(tag)
    flash(f"Tag “{name}” deleted. Your expenses were not changed.", "success")
    return redirect(url_for("tags.index"))


@bp.route("/expense/<int:expense_id>", methods=["GET", "POST"])
def expense_tags(expense_id):
    expense = service.get_user_expense_or_404(current_user.id, expense_id)
    if request.method == "POST":
        tag_ids = parse_id_list(request.form.getlist("tag_id"), service.MAX_TAGS_PER_EXPENSE + 1)
        try:
            service.set_expense_tags(current_user.id, expense, tag_ids)
        except service.TagLimitError as exc:
            flash(str(exc), "error")
            return redirect(url_for("tags.expense_tags", expense_id=expense.id))
        flash("Tags saved.", "success")
        return redirect(url_for("tags.expense_tags", expense_id=expense.id))
    selected = {tag.id for tag in expense.tags}
    return render_template(
        "tags/expense.html",
        expense=expense,
        tags=service.user_tags(current_user.id),
        selected=selected,
        max_per_expense=service.MAX_TAGS_PER_EXPENSE,
    )


@bp.route("/bulk", methods=["GET", "POST"])
def bulk():
    tags = service.user_tags(current_user.id)
    if request.method == "POST":
        tag_ids = parse_id_list([request.form.get("tag_id")], 1)
        if not tag_ids:
            flash("Pick a tag first.", "error")
            return redirect(url_for("tags.bulk"))
        tag = service.get_user_tag_or_404(current_user.id, tag_ids[0])
        expense_ids = parse_id_list(request.form.getlist("expense_id"), service.BULK_PAGE_SIZE)
        remove = request.form.get("action") == "remove"
        changed = service.bulk_apply(current_user.id, tag, expense_ids, remove=remove)
        verb = "removed from" if remove else "added to"
        flash(f"Tag “{tag.name}” {verb} {changed} expense(s).", "success")
        return redirect(url_for("tags.detail", tag_id=tag.id))
    return render_template(
        "tags/bulk.html",
        tags=tags,
        expenses=service.recent_expenses(current_user.id),
        page_size=service.BULK_PAGE_SIZE,
    )


@bp.get("/summary.json")
def summary_json():
    """Tag usage for the signed-in user, for the mobile companion app."""
    rows = service.tag_overview(current_user.id)
    return jsonify([{**row["tag"].to_dict(), "expense_count": row["count"]} for row in rows])
