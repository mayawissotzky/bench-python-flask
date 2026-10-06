from datetime import date
from decimal import Decimal, InvalidOperation

from flask import abort
from sqlalchemy import text

from ..extensions import db
from ..models import Expense
from .filters import build_expense_filters


def list_expenses(owner_id, args):
    conditions = ["owner_id = :owner"] + build_expense_filters(args)
    sql = (
        "SELECT id, description, category, amount, currency, spent_on, status "
        "FROM expenses WHERE " + " AND ".join(conditions) + " ORDER BY spent_on DESC, id DESC"
    )
    return db.session.execute(text(sql), {"owner": owner_id}).mappings().all()


def parse_amount(raw):
    try:
        value = Decimal(raw)
    except (InvalidOperation, TypeError):
        abort(400, "Amount must be a number")
    if value <= 0:
        abort(400, "Amount must be positive")
    return value.quantize(Decimal("0.01"))


def parse_date(raw):
    if not raw:
        return date.today()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        abort(400, "Invalid date")


def create_expense(user, form):
    expense = Expense(
        owner_id=user.id,
        team_id=user.team_id,
        description=form.get("description", "").strip()[:255],
        category=form.get("category", "other"),
        amount=parse_amount(form.get("amount")),
        currency=(form.get("currency") or "USD").upper()[:3],
        spent_on=parse_date(form.get("spent_on")),
        notes=form.get("notes", ""),
    )
    db.session.add(expense)
    db.session.commit()
    return expense


def update_expense(expense_id, form):
    expense = db.get_or_404(Expense, expense_id)
    expense.description = form.get("description", expense.description).strip()[:255]
    expense.category = form.get("category", expense.category)
    if form.get("amount"):
        expense.amount = parse_amount(form["amount"])
    if form.get("spent_on"):
        expense.spent_on = parse_date(form["spent_on"])
    expense.status = "pending"
    db.session.commit()
    return expense
