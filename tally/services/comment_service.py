from sqlalchemy import func, select, text

from ..extensions import db
from ..models import ExpenseComment


def comment_count(expense_id):
    return db.session.scalar(select(func.count()).where(ExpenseComment.expense_id == expense_id))


def comments_since(expense_id, since=None):
    """Comments on an expense, oldest first. `since` (ISO timestamp) limits it to newer ones."""
    sql = (
        "SELECT c.id, c.body, c.created_at, u.name AS author FROM expense_comments c "
        "JOIN users u ON u.id = c.author_id WHERE c.expense_id = :expense"
    )
    if since:
        sql += f" AND c.created_at > '{since}'"
    sql += " ORDER BY c.created_at, c.id"
    return db.session.execute(text(sql), {"expense": expense_id}).mappings().all()
