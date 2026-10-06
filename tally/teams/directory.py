from ..extensions import db

MEMBER_COLUMNS = ("id", "name", "email", "role", "website")


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
