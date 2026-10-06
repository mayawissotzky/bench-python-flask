from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import select

from ..extensions import db
from ..models import Expense, Team
from . import bp
from .directory import list_members


@bp.route("/new", methods=["GET", "POST"])
def create():
    if current_user.team_id:
        return redirect(url_for("teams.expenses", team_id=current_user.team_id))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Team name is required.", "error")
        else:
            team = Team(name=name[:120], description=request.form.get("description", ""))
            db.session.add(team)
            db.session.flush()
            current_user.team_id = team.id
            current_user.role = "manager"
            db.session.commit()
            return redirect(url_for("teams.expenses", team_id=team.id))
    return render_template("teams/new.html")


@bp.get("/<int:team_id>/expenses")
def expenses(team_id):
    status = request.args.get("status")
    stmt = select(Expense).where(Expense.team_id == team_id).order_by(Expense.spent_on.desc())
    if status:
        stmt = stmt.where(Expense.status == status)
    items = db.session.scalars(stmt).all()
    return render_template("teams/expenses.html", team=db.session.get(Team, team_id), items=items)


@bp.get("/<int:team_id>/members")
def members(team_id):
    role = request.args.get("role", "")
    rows = list_members(team_id, role)
    return render_template("teams/members.html", team=db.session.get(Team, team_id), members=rows, role=role)


@bp.route("/<int:team_id>/settings", methods=["GET", "POST"])
def settings(team_id):
    if not current_user.is_manager:
        abort(403)
    team = db.get_or_404(Team, team_id)
    if request.method == "POST":
        team.name = request.form.get("name", team.name).strip()[:120] or team.name
        team.description = request.form.get("description", team.description)
        db.session.commit()
        flash("Team updated.", "success")
        return redirect(url_for("teams.settings", team_id=team.id))
    return render_template("teams/settings.html", team=team)
