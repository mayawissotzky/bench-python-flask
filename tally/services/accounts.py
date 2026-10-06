from ..extensions import db
from ..models import User


def register_user(email, name, password):
    user = User(email=email.strip().lower(), name=name.strip())
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def save_profile(user, form):
    user.name = form.get("name", user.name).strip()[:120] or user.name
    user.website = form.get("website", "").strip()[:255]
    user.bio = form.get("bio", "")
    db.session.commit()


def apply_profile_changes(user, changes):
    for field, value in changes.items():
        if hasattr(user, field):
            setattr(user, field, value)
    db.session.commit()
