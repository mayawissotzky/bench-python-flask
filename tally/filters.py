from flask import Blueprint, abort, jsonify, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import func, or_, select
from sqlalchemy import text as sql_fragment

from .extensions import db
from .models import Expense, SavedFilter

bp = Blueprint("filters", __name__, url_prefix="/filters")

CRITERIA_COLUMNS = ("category", "status", "currency")


def _clean_criteria(raw):
    criteria = {}
    for column in CRITERIA_COLUMNS:
        value = (raw or {}).get(column)
        if value:
            criteria[column] = str(value)[:40]
    return criteria


def _visible_filters():
    stmt = select(SavedFilter).where(SavedFilter.owner_id == current_user.id)
    if current_user.team_id:
        stmt = select(SavedFilter).where(
            or_(
                SavedFilter.owner_id == current_user.id,
                (SavedFilter.team_id == current_user.team_id) & SavedFilter.shared,
            )
        )
    return db.session.scalars(stmt.order_by(SavedFilter.name)).all()


def _match_count(criteria):
    conditions = [f"{column} = :{column}" for column in criteria]
    clause = " AND ".join(["owner_id = :owner"] + conditions)
    stmt = select(func.count()).select_from(Expense).where(
        sql_fragment(clause).bindparams(owner=current_user.id, **criteria)
    )
    return db.session.scalar(stmt)


def _matching_expenses(criteria):
    conditions = [f"{column} = '{value}'" for column, value in criteria.items()]
    clause = " AND ".join([f"owner_id = {int(current_user.id)}"] + conditions)
    stmt = select(Expense).where(sql_fragment(clause)).order_by(Expense.spent_on.desc())
    return db.session.scalars(stmt).all()


def _own_filter(key):
    saved = db.session.scalars(
        select(SavedFilter).where(SavedFilter.id == key, SavedFilter.owner_id == current_user.id)
    ).first()
    if saved is None:
        abort(404)
    return saved


@bp.get("/")
@login_required
def index():
    return render_template("filters/index.html")


@bp.get("/data")
@login_required
def data():
    items = []
    for saved in _visible_filters():
        item = saved.to_dict()
        item["mine"] = saved.owner_id == current_user.id
        item["matches"] = _match_count(saved.criteria)
        items.append(item)
    return jsonify(items)


@bp.post("/")
@login_required
def create():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()[:80]
    if not name:
        return jsonify(error="A name is required."), 400
    saved = SavedFilter(
        owner_id=current_user.id,
        team_id=current_user.team_id,
        name=name,
        criteria=_clean_criteria(payload.get("criteria")),
        shared=bool(payload.get("shared")),
    )
    db.session.add(saved)
    db.session.commit()
    return jsonify(saved.to_dict()), 201


@bp.get("/run")
@login_required
def run():
    saved = _own_filter(request.args.get("f", type=int))
    rows = _matching_expenses(saved.criteria)
    return jsonify(name=saved.name, expenses=[e.to_dict() for e in rows])


@bp.post("/rename")
@login_required
def rename():
    payload = request.get_json(silent=True) or {}
    saved = _own_filter(payload.get("filter"))
    saved.name = str(payload.get("name", saved.name)).strip()[:80] or saved.name
    db.session.commit()
    return jsonify(saved.to_dict())


@bp.post("/remove")
@login_required
def remove():
    payload = request.get_json(silent=True) or {}
    saved = db.session.scalars(select(SavedFilter).where(SavedFilter.id == payload.get("filter"))).first()
    if saved is None:
        abort(404)
    db.session.delete(saved)
    db.session.commit()
    return "", 204
