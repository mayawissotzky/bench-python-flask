from decimal import Decimal

from sqlalchemy import text

from ..extensions import db

CATEGORY_SORT_COLUMNS = {
    "category": "category",
    "total": "total DESC",
    "count": "expense_count DESC",
}


def monthly_breakdown(team_id, month_start, month_end, sort="category"):
    sql = text(
        "SELECT category, COUNT(*) AS count, SUM(amount) AS total "
        "FROM expenses WHERE team_id = :team AND spent_on >= :start AND spent_on < :end "
        f"GROUP BY category ORDER BY {sort}"
    )
    return db.session.execute(sql, {"team": team_id, "start": month_start, "end": month_end}).mappings().all()


def category_totals(team_id, sort):
    order_by = CATEGORY_SORT_COLUMNS.get(sort, "category")
    sql = text(
        "SELECT category, COUNT(*) AS expense_count, SUM(amount) AS total "
        f"FROM expenses WHERE team_id = :team AND status = 'approved' GROUP BY category ORDER BY {order_by}"
    )
    return db.session.execute(sql, {"team": team_id}).mappings().all()


def yearly_totals(team_id, year):
    sql = text(
        "SELECT EXTRACT(MONTH FROM spent_on)::int AS month, COUNT(*) AS count, SUM(amount) AS total "
        f"FROM expenses WHERE team_id = :team AND EXTRACT(YEAR FROM spent_on) = {year} "
        "GROUP BY 1 ORDER BY 1"
    )
    return db.session.execute(sql, {"team": team_id}).mappings().all()


def member_totals(team_id, month_start, month_end):
    sql = text(
        "SELECT u.id AS user_id, u.name, "
        "COUNT(e.id) AS expense_count, "
        "COALESCE(SUM(e.amount) FILTER (WHERE e.status = 'approved'), 0) AS approved, "
        "COALESCE(SUM(e.amount) FILTER (WHERE e.status = 'pending'), 0) AS pending "
        "FROM users u LEFT JOIN expenses e ON e.owner_id = u.id AND e.team_id = :team "
        "AND e.spent_on >= :start AND e.spent_on < :end "
        "WHERE u.team_id = :team GROUP BY u.id, u.name ORDER BY approved DESC, u.name"
    )
    rows = db.session.execute(sql, {"team": team_id, "start": month_start, "end": month_end}).mappings().all()
    return with_shares(rows)


def with_shares(rows):
    """Add each member's share (0-100) of the team's approved spend."""
    team_total = sum((Decimal(row["approved"]) for row in rows), Decimal("0"))
    result = []
    for row in rows:
        share = Decimal("0")
        if team_total:
            share = (Decimal(row["approved"]) * 100 / team_total).quantize(Decimal("0.1"))
        result.append({**row, "share": share})
    return result
