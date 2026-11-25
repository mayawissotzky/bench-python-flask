import secrets

import nh3
from flask import Blueprint, abort, flash, jsonify, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from markupsafe import Markup
from sqlalchemy import select

from .extensions import db
from .models import ShareLink

bp = Blueprint("share", __name__, url_prefix="/share")


def _heading(link):
    return Markup('<span class="share-title">{}</span>').format(link.title)


def _by_token(token):
    return db.session.execute(select(ShareLink).filter_by(token=token)).scalar_one_or_none()


@bp.get("/")
@login_required
def index():
    links = db.session.execute(
        select(ShareLink).filter_by(owner_id=current_user.id).order_by(ShareLink.created_at.desc())
    ).scalars().all()
    return render_template("share/index.html", links=links)


@bp.post("/")
@login_required
def create():
    title = request.form.get("title", "").strip()[:120]
    if not title:
        flash("A title is required.", "error")
        return redirect(url_for("share.index"))
    db.session.add(ShareLink(token=secrets.token_urlsafe(24), owner_id=current_user.id, title=title,
                             message=request.form.get("message", ""), note=request.form.get("note", ""),
                             link_url=request.form.get("link_url", "").strip()[:500]))
    db.session.commit()
    flash("Share link created.", "success")
    return redirect(url_for("share.index"))


@bp.post("/<int:link_id>/delete")
@login_required
def delete(link_id):
    link = db.first_or_404(select(ShareLink).filter_by(id=link_id, owner_id=current_user.id))
    db.session.delete(link)
    db.session.commit()
    return redirect(url_for("share.index"))


@bp.get("/s/<token>")
def view(token):
    link = _by_token(token)
    if link is None:
        return make_response(f"<p class='muted'>No shared page called <b>{token}</b>.</p>", 404)
    return render_template("share/view.html", link=link, heading=_heading(link),
                           note_html=nh3.clean(link.note or ""))


@bp.get("/s/<token>.json")
def view_json(token):
    link = _by_token(token)
    if link is None:
        abort(404)
    return jsonify(title=link.title, owner=link.owner.name, created=link.created_at.isoformat())
