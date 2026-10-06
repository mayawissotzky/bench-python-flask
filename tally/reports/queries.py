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
