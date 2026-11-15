from flask import Blueprint, redirect, url_for
from flask_login import current_user, login_required

bp = Blueprint("budgets", __name__, url_prefix="/budgets")


@bp.before_request
@login_required
def require_team():
    if not current_user.team_id:
        return redirect(url_for("teams.create"))


from . import routes  # noqa: E402,F401
