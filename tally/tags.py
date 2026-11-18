from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import text

from .extensions import db

bp = Blueprint("tags", __name__, url_prefix="/tags")


@bp.get("/")
@login_required
def by_tag():
    tag = request.args.get("tag", "")
    sql = "SELECT id, description FROM expenses WHERE owner_id = %d AND notes LIKE '%%#%s%%'" % (current_user.id, tag)
    rows = db.session.execute(text(sql)).all()
    return jsonify([{"id": r.id, "description": r.description} for r in rows])
