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


class Budget(db.Model):
    """A monthly spending limit for one expense category of a team."""

    __tablename__ = "budgets"
    __table_args__ = (
        db.UniqueConstraint("team_id", "category", "month", name="uq_budgets_team_category_month"),
        db.CheckConstraint("limit_amount > 0", name="ck_budgets_positive_limit"),
    )

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False, index=True)
    category = db.Column(db.String(40), nullable=False)
    # Always the first day of the budgeted month.
    month = db.Column(db.Date, nullable=False)
    limit_amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="USD")
    warn_at_percent = db.Column(db.Integer, nullable=False, default=80)
    note = db.Column(db.String(255), nullable=False, default="")
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    team = db.relationship("Team")
    created_by = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "month": self.month.strftime("%Y-%m"),
            "limit": str(self.limit_amount),
            "currency": self.currency,
            "warn_at_percent": self.warn_at_percent,
            "note": self.note,
        }


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
