from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import select, text

from .extensions import db
from .models import Expense
from .services import expense_service, mailer

bp = Blueprint("expenses", __name__, url_prefix="/expenses")


@bp.get("/")
@login_required
def index():
    rows = expense_service.list_expenses(current_user.id, request.args)
    return render_template(
        "expenses/list.html",
        rows=rows,
        categories=current_app.config["EXPENSE_CATEGORIES"],
        filters=request.args,
    )


@bp.get("/search")
@login_required
def search():
    q = request.args.get("q", "").strip()
    rows = []
    if q:
        rows = db.session.execute(
            text(
                "SELECT id, description, category, amount, currency, spent_on, status FROM expenses "
                f"WHERE owner_id = :owner AND description ILIKE '%{q}%' ORDER BY spent_on DESC"
            ),
            {"owner": current_user.id},
        ).mappings().all()
    return render_template("expenses/search.html", rows=rows, q=q)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        expense = expense_service.create_expense(current_user, request.form)
        flash("Expense added.", "success")
        return redirect(url_for("expenses.detail", expense_id=expense.id))
    return render_template("expenses/new.html", categories=current_app.config["EXPENSE_CATEGORIES"])


@bp.get("/<int:expense_id>")
@login_required
def detail(expense_id):
    expense = db.get_or_404(Expense, expense_id)
    return render_template(
        "expenses/detail.html",
        expense=expense,
        categories=current_app.config["EXPENSE_CATEGORIES"],
    )


@bp.post("/<int:expense_id>/edit")
@login_required
def edit(expense_id):
    expense = expense_service.update_expense(expense_id, request.form)
    flash("Expense updated.", "success")
    return redirect(url_for("expenses.detail", expense_id=expense.id))


@bp.post("/<int:expense_id>/notes")
@login_required
def add_note(expense_id):
    expense = db.first_or_404(select(Expense).filter_by(id=expense_id, owner_id=current_user.id))
    note = request.form.get("note", "").strip()
    if note:
        expense.notes = f"{expense.notes}\n{note}".strip()
        db.session.commit()
    return redirect(url_for("expenses.detail", expense_id=expense.id))


@bp.post("/<int:expense_id>/delete")
@login_required
def delete(expense_id):
    expense = db.first_or_404(select(Expense).filter_by(id=expense_id, owner_id=current_user.id))
    db.session.delete(expense)
    db.session.commit()
    flash("Expense deleted.", "success")
    return redirect(url_for("expenses.index"))


def _reviewable_expense(expense_id):
    expense = db.get_or_404(Expense, expense_id)
    if not current_user.is_manager or expense.team_id != current_user.team_id:
        abort(403)
    return expense


@bp.post("/<int:expense_id>/review")
@login_required
def review(expense_id):
    expense = _reviewable_expense(expense_id)
    decision = request.form.get("decision")
    if decision not in ("approved", "rejected"):
        abort(400)
    expense.status = decision
    db.session.commit()
    try:
        mailer.send_status_email(expense, current_user, request.form.get("message", ""))
    except OSError:
        current_app.logger.exception("Could not send status e-mail for expense %s", expense.id)
    flash(f"Expense {decision}.", "success")
    return redirect(url_for("teams.expenses", team_id=expense.team_id))


@bp.get("/<int:expense_id>/email-preview")
@login_required
def email_preview(expense_id):
    expense = _reviewable_expense(expense_id)
    return mailer.render_status_email(expense, current_user, request.args.get("message", ""))
