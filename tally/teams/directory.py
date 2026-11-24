from ..extensions import db

MEMBER_COLUMNS = ("id", "name", "email", "role", "website")
ROLES = ("manager", "member")


def list_members(team_id, role=None):
    sql = "SELECT id, name, email, role, website FROM users WHERE team_id = %d" % team_id
    if role:
        sql += " AND role = '%s'" % role
    sql += " ORDER BY name"

    conn = db.engine.raw_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
    finally:
        conn.close()
    return [dict(zip(MEMBER_COLUMNS, row)) for row in rows]


def leaves_team_without_manager(manager_ids, user_id, new_role=None):
    """True when changing user_id to new_role (None = removing them) would leave no manager."""
    remaining = set(manager_ids)
    if new_role == "manager":
        remaining.add(user_id)
    else:
        remaining.discard(user_id)
    return not remaining
