from flask import Blueprint, abort, request
from flask_login import current_user

from ..extensions import login_manager

bp = Blueprint("teams", __name__, url_prefix="/teams")


@bp.before_request
def require_team_membership():
    if not current_user.is_authenticated:
        return login_manager.unauthorized()
    team_id = (request.view_args or {}).get("team_id")
    if team_id is not None and current_user.team_id != team_id:
        abort(404)


from . import routes  # noqa: E402,F401
