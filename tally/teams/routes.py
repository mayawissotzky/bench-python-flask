from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import select

from ..extensions import db
from ..models import Expense, Team, User
from . import bp
from .directory import ROLES, leaves_team_without_manager, list_members


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
    return render_template(
        "teams/members.html", team=db.session.get(Team, team_id), members=rows, role=role, roles=ROLES
    )


def _manager_ids(team_id):
    return db.session.scalars(select(User.id).where(User.team_id == team_id, User.role == "manager")).all()


def _managed_member(team_id, user_id):
    if not current_user.is_manager:
        abort(403)
    return db.get_or_404(User, user_id)


@bp.post("/<int:team_id>/members/<int:user_id>/role")
def change_role(team_id, user_id):
    member = _managed_member(team_id, user_id)
    new_role = request.form.get("role")
    if new_role not in ROLES:
        abort(400)
    if leaves_team_without_manager(_manager_ids(team_id), member.id, new_role):
        flash("A team needs at least one manager.", "error")
    else:
        member.role = new_role
        db.session.commit()
        flash(f"{member.name} is now a {new_role}.", "success")
    return redirect(url_for("teams.members", team_id=team_id))


@bp.post("/<int:team_id>/members/<int:user_id>/remove")
def remove_member(team_id, user_id):
    member = _managed_member(team_id, user_id)
    if member.id == current_user.id:
        flash("You can't remove yourself from the team.", "error")
    elif leaves_team_without_manager(_manager_ids(team_id), member.id):
        flash("A team needs at least one manager.", "error")
    else:
        member.team_id = None
        member.role = "member"
        db.session.commit()
        flash(f"{member.name} was removed from the team.", "success")
    return redirect(url_for("teams.members", team_id=team_id))


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
