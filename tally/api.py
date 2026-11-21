from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import select, text

from .extensions import db
from .models import Comment, Expense
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


@bp.get("/expenses/<int:expense_id>/comments")
@login_required
def list_comments(expense_id):
    comments = db.session.scalars(
        select(Comment).filter_by(expense_id=expense_id).order_by(Comment.created_at)
    ).all()
    return jsonify([c.to_dict() for c in comments])


@bp.post("/expenses/<int:expense_id>/comments")
@login_required
def add_comment(expense_id):
    expense = db.first_or_404(select(Expense).filter_by(id=expense_id, owner_id=current_user.id))
    body = ((request.get_json(silent=True) or {}).get("body") or "").strip()
    if not body:
        return jsonify(error="Comment can't be empty"), 400
    comment = Comment(expense_id=expense.id, author_id=current_user.id, body=body[:2000])
    db.session.add(comment)
    db.session.commit()
    return jsonify(comment.to_dict()), 201


@bp.delete("/comments/<int:comment_id>")
@login_required
def delete_comment(comment_id):
    comment = db.first_or_404(select(Comment).filter_by(id=comment_id, author_id=current_user.id))
    db.session.delete(comment)
    db.session.commit()
    return "", 204


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
