"""Personal expense tags.

Tags are private to the user who creates them: every tag, and every expense a
tag is applied to, is looked up through the signed-in user's id.
"""

import hmac
import secrets

from flask import Blueprint, abort, request, session
from flask_login import current_user

from ..extensions import login_manager

bp = Blueprint("tags", __name__, url_prefix="/tags")

_CSRF_SESSION_KEY = "tags_csrf"
_CSRF_FIELD = "csrf_token"


def csrf_token():
    token = session.get(_CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[_CSRF_SESSION_KEY] = token
    return token


@bp.before_request
def require_login_and_valid_form():
    if not current_user.is_authenticated:
        return login_manager.unauthorized()
    if request.method == "POST":
        expected = session.get(_CSRF_SESSION_KEY, "")
        submitted = request.form.get(_CSRF_FIELD, "")
        if not expected or not hmac.compare_digest(expected, submitted):
            abort(400, "The form expired, please reload the page and try again.")


@bp.context_processor
def inject_csrf():
    return {"csrf_token": csrf_token}


from . import routes  # noqa: E402,F401
