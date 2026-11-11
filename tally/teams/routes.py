import secrets

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import select

from ..extensions import db
from ..models import Expense, Team, TeamInvite
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


@bp.route("/<int:team_id>/invites", methods=["GET", "POST"])
def invites(team_id):
    team = db.get_or_404(Team, team_id)
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role", "member")
        if role not in ("member", "manager"):
            abort(400)
        if "@" not in email:
            flash("Enter the e-mail address to invite.", "error")
        else:
            invite = TeamInvite(
                team_id=team.id,
                email=email[:255],
                role=role,
                message=request.form.get("message", "")[:1000],
                token=secrets.token_urlsafe(24),
                invited_by_id=current_user.id,
            )
            db.session.add(invite)
            db.session.commit()
            flash(f"Invite link for {email}: {url_for('invites.show', token=invite.token, _external=True)}", "success")
        return redirect(url_for("teams.invites", team_id=team.id))
    pending = db.session.scalars(
        select(TeamInvite)
        .where(TeamInvite.team_id == team.id, TeamInvite.accepted_at.is_(None))
        .order_by(TeamInvite.created_at.desc())
    ).all()
    return render_template("teams/invites.html", team=team, invites=pending)


@bp.post("/<int:team_id>/invites/<int:invite_id>/revoke")
def revoke_invite(team_id, invite_id):
    if not current_user.is_manager:
        abort(403)
    invite = db.first_or_404(select(TeamInvite).filter_by(id=invite_id, team_id=team_id, accepted_at=None))
    db.session.delete(invite)
    db.session.commit()
    flash("Invite revoked.", "success")
    return redirect(url_for("teams.invites", team_id=team_id))
