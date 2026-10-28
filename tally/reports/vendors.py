from sqlalchemy import text

from ..extensions import db


def vendor_totals(team_id, vendor):
    sql = text(
        "SELECT vendor, COUNT(*) AS count, SUM(amount) AS total "
        f"FROM expenses WHERE team_id = :team AND vendor ILIKE '{vendor}%' "
        "GROUP BY vendor ORDER BY total DESC"
    )
    return db.session.execute(sql, {"team": team_id}).mappings().all()
