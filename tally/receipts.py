from flask import Blueprint, jsonify
from flask_login import login_required

from .extensions import db
from .models import Expense

bp = Blueprint("receipts", __name__, url_prefix="/receipts")


@bp.get("/<int:expense_id>")
@login_required
def receipt(expense_id):
    expense = db.get_or_404(Expense, expense_id)
    return jsonify(
        {
            **expense.to_dict(),
            "submitted_by": expense.owner.email,
            "notes": expense.notes,
        }
    )
