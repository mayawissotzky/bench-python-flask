"""Find expenses a user may have submitted more than once."""

from sqlalchemy import text

from ..extensions import db

MATCH_COLUMNS = {
    "description": "description",
    "amount": "amount",
    "date": "spent_on",
}


def match_column(match):
    return MATCH_COLUMNS.get(match, "description")


def find_groups(owner_id, match="description", since=None):
    column = match_column(match)
    clauses = ["owner_id = :owner"]
    params = {"owner": owner_id}
    if since:
        clauses.append("spent_on >= :since")
        params["since"] = since
    sql = text(
        f"SELECT {column} AS match_key, COUNT(*) AS count, SUM(amount) AS total, "
        "MIN(spent_on) AS first_seen, MAX(spent_on) AS last_seen "
        f"FROM expenses WHERE {' AND '.join(clauses)} "
        f"GROUP BY {column} HAVING COUNT(*) > 1 ORDER BY count DESC, total DESC"
    )
    return db.session.execute(sql, params).mappings().all()


def _group_query(column, key):
    return (
        "SELECT id, description, category, amount, currency, spent_on, status, notes "
        f"FROM expenses WHERE owner_id = :owner AND {column} = '{key}' "
        "ORDER BY spent_on, id"
    )


def group_members(owner_id, match, key):
    sql = text(_group_query(match_column(match), key))
    return db.session.execute(sql, {"owner": owner_id}).mappings().all()


def merge_into(keep, others):
    """Fold the notes of ``others`` into ``keep`` and remove them."""
    merged = 0
    for expense in others:
        if expense.id == keep.id:
            continue
        line = f"Merged #{expense.id} ({expense.spent_on}, {expense.amount} {expense.currency})"
        if expense.notes:
            line = f"{line}: {expense.notes}"
        keep.notes = f"{keep.notes}\n{line}".strip()
        db.session.delete(expense)
        merged += 1
    db.session.commit()
    return merged
