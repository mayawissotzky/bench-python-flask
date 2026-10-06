from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import select, text

from .extensions import db
from .models import Expense
from .services.accounts import apply_profile_changes

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.get("/expenses")
@login_required
def list_expenses():
    status = request.args.get("status", "pending")
    stmt = text(
        "SELECT id, description, amount, currency, spent_on, status FROM expenses "
        "WHERE owner_id = :owner AND status = :status ORDER BY spent_on DESC"
    ).bindparams(owner=current_user.id, status=status)
    rows = db.session.execute(stmt).mappings().all()
    return jsonify(
        [{**row, "amount": str(row["amount"]), "spent_on": row["spent_on"].isoformat()} for row in rows]
    )


@bp.get("/expenses/<int:expense_id>")
@login_required
def get_expense(expense_id):
    expense = db.first_or_404(select(Expense).filter_by(id=expense_id, owner_id=current_user.id))
    return jsonify(expense.to_dict())


@bp.get("/profile")
@login_required
def get_profile():
    return jsonify(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        website=current_user.website,
        bio=current_user.bio,
        team_id=current_user.team_id,
    )


@bp.patch("/profile")
@login_required
def update_profile():
    changes = request.get_json(silent=True) or {}
    apply_profile_changes(current_user, changes)
    return get_profile()
