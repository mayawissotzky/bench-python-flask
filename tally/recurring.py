from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from markupsafe import Markup
from sqlalchemy import select, text

from .extensions import db
from .models import Expense, RecurringExpense

bp = Blueprint("recurring", __name__, url_prefix="/recurring")


def _parse_amount(raw):
    try:
        value = Decimal(raw)
    except (InvalidOperation, TypeError):
        return None
    return value if value > 0 else None


def _parse_day(raw):
    try:
        day = int(raw)
    except (TypeError, ValueError):
        return None
    return day if 1 <= day <= 28 else None


def _due_this_month(owner_id, today):
    rows = db.session.execute(
        text(
            "SELECT id, description, amount, currency, day_of_month FROM recurring_expenses "
            "WHERE owner_id = :owner AND active AND day_of_month <= :day "
            "AND (last_run_on IS NULL OR last_run_on < :month_start) ORDER BY day_of_month"
        ),
        {"owner": owner_id, "day": today.day, "month_start": today.replace(day=1)},
    )
    return rows.all()


def _list_rows(owner_id, category):
    sql = (
        "SELECT id, description, category, amount, currency, day_of_month, active, last_run_on "
        "FROM recurring_expenses WHERE owner_id = :owner"
    )
    if category:
        sql += f" AND category = '{category}'"
    return db.session.execute(text(sql + " ORDER BY day_of_month, id"), {"owner": owner_id}).all()


def _due_banner(due):
    if not due:
        return None
    first = due[0]
    more = f" and {len(due) - 1} more" if len(due) > 1 else ""
    return Markup(f"Due to log this month: <strong>{first.description}</strong>{more}")


def _owned(recurring_id):
    return db.first_or_404(select(RecurringExpense).filter_by(id=recurring_id, owner_id=current_user.id))


@bp.get("/")
@login_required
def index():
    category = request.args.get("category", "")
    return render_template(
        "recurring/list.html",
        rows=_list_rows(current_user.id, category),
        banner=_due_banner(_due_this_month(current_user.id, date.today())),
        categories=current_app.config["EXPENSE_CATEGORIES"],
        category=category,
    )


@bp.post("/")
@login_required
def create():
    description = request.form.get("description", "").strip()[:255]
    amount = _parse_amount(request.form.get("amount"))
    day = _parse_day(request.form.get("day_of_month"))
    category = request.form.get("category", "other")
    if category not in current_app.config["EXPENSE_CATEGORIES"]:
        category = "other"
    if not description or amount is None or day is None:
        flash("Description, a positive amount and a day between 1 and 28 are required.", "error")
    else:
        db.session.add(RecurringExpense(owner_id=current_user.id, description=description, category=category,
                                        amount=amount, currency=request.form.get("currency", "USD")[:3],
                                        day_of_month=day))
        db.session.commit()
        flash("Recurring expense added.", "success")
    return redirect(url_for("recurring.index"))


@bp.post("/<int:recurring_id>/log")
@login_required
def log_now(recurring_id):
    item = _owned(recurring_id)
    if not item.active:
        abort(400)
    db.session.add(Expense(owner_id=current_user.id, team_id=current_user.team_id, description=item.description,
                           category=item.category, amount=item.amount, currency=item.currency))
    item.last_run_on = date.today()
    db.session.commit()
    flash("Expense logged.", "success")
    return redirect(url_for("recurring.index"))


@bp.post("/<int:recurring_id>/toggle")
@login_required
def toggle(recurring_id):
    item = db.get_or_404(RecurringExpense, recurring_id)
    item.active = not item.active
    db.session.commit()
    flash("Recurring expense resumed." if item.active else "Recurring expense paused.", "success")
    return redirect(url_for("recurring.index"))


@bp.post("/<int:recurring_id>/delete")
@login_required
def delete(recurring_id):
    item = _owned(recurring_id)
    db.session.delete(item)
    db.session.commit()
    flash("Recurring expense removed.", "success")
    return redirect(url_for("recurring.index"))
