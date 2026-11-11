from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, text, update

from .extensions import db
from .models import TeamInvite

bp = Blueprint("invites", __name__, url_prefix="/invites")


def _pending_invite(token):
    invite = db.session.execute(
        text(
            "SELECT i.id, i.team_id, i.email, i.role, i.message, t.name AS team_name, u.name AS inviter "
            "FROM team_invites i JOIN teams t ON t.id = i.team_id JOIN users u ON u.id = i.invited_by_id "
            f"WHERE i.token = '{token}' AND i.accepted_at IS NULL"
        )
    ).mappings().first()
    if invite is None:
        abort(404)
    return invite


@bp.get("/<token>")
@login_required
def show(token):
    return render_template("invites/show.html", invite=_pending_invite(token), token=token)


@bp.post("/<token>/accept")
@login_required
def accept(token):
    invite = _pending_invite(token)
    if invite["email"] != current_user.email:
        abort(403)
    if current_user.team_id:
        flash("Leave your current team before joining another one.", "error")
        return redirect(url_for("invites.show", token=token))
    current_user.team_id = invite["team_id"]
    current_user.role = invite["role"]
    db.session.execute(update(TeamInvite).where(TeamInvite.id == invite["id"]).values(accepted_at=func.now()))
    db.session.commit()
    flash(f"Welcome to {invite['team_name']}!", "success")
    return redirect(url_for("teams.expenses", team_id=invite["team_id"]))
