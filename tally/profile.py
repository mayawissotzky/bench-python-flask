import nh3
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .services.accounts import save_profile

bp = Blueprint("profile", __name__, url_prefix="/profile")


@bp.route("/", methods=["GET", "POST"])
@login_required
def edit():
    if request.method == "POST":
        save_profile(current_user, request.form)
        flash("Profile saved.", "success")
        return redirect(url_for("profile.edit"))
    bio_html = nh3.clean(current_user.bio or "")
    return render_template("profile/edit.html", user=current_user, bio_html=bio_html)
