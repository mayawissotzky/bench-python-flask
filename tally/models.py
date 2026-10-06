from datetime import date, datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


def _now():
    return datetime.now(timezone.utc)


class Team(db.Model):
    __tablename__ = "teams"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_now)

    members = db.relationship("User", back_populates="team")


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="member")
    website = db.Column(db.String(255), nullable=False, default="")
    bio = db.Column(db.Text, nullable=False, default="")
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_now)

    team = db.relationship("Team", back_populates="members")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_manager(self):
        return self.role == "manager"


class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"))
    description = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(40), nullable=False, default="other")
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="USD")
    spent_on = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(20), nullable=False, default="pending")
    notes = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_now)

    owner = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "category": self.category,
            "amount": str(self.amount),
            "currency": self.currency,
            "spent_on": self.spent_on.isoformat(),
            "status": self.status,
            "notes": self.notes,
        }


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
