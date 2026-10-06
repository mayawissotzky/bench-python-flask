from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user
from sqlalchemy import select

from .extensions import db
from .models import User
from .services.accounts import register_user

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = db.session.scalar(select(User).where(User.email == email))
        if user and user.check_password(request.form.get("password", "")):
            login_user(user, remember=bool(request.form.get("remember")))
            return redirect(url_for("expenses.index"))
        flash("Invalid email or password.", "error")
    return render_template("auth/login.html", google_client_id=current_app.config["GOOGLE_CLIENT_ID"])


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        if not email or len(password) < 8:
            flash("Email and a password of at least 8 characters are required.", "error")
        elif db.session.scalar(select(User).where(User.email == email.strip().lower())):
            flash("That email is already registered.", "error")
        else:
            user = register_user(email, request.form.get("name", "") or email, password)
            login_user(user)
            return redirect(url_for("teams.create"))
    return render_template("auth/register.html")


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
