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



class RecurringExpense(db.Model):
    """A schedule that turns into a regular expense every week, month, quarter or year."""

    __tablename__ = "recurring_expenses"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    description = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(40), nullable=False, default="other")
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="USD")
    frequency = db.Column(db.String(20), nullable=False, default="monthly")
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    end_date = db.Column(db.Date)
    next_due = db.Column(db.Date, nullable=False, default=date.today)
    occurrences = db.Column(db.Integer, nullable=False, default=0)
    active = db.Column(db.Boolean, nullable=False, default=True)
    notes = db.Column(db.Text, nullable=False, default="")
    last_generated_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_now)

    owner = db.relationship("User")
    runs = db.relationship(
        "RecurringRun",
        back_populates="schedule",
        cascade="all, delete-orphan",
        order_by="RecurringRun.due_on.desc()",
    )

    @property
    def finished(self):
        return self.end_date is not None and self.next_due > self.end_date

    @property
    def state(self):
        if self.finished:
            return "finished"
        return "active" if self.active else "paused"



class RecurringRun(db.Model):
    """One expense created from a recurring schedule."""

    __tablename__ = "recurring_runs"
    __table_args__ = (db.UniqueConstraint("schedule_id", "due_on", name="uq_recurring_run_due"),)

    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(
        db.Integer, db.ForeignKey("recurring_expenses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    expense_id = db.Column(db.Integer, db.ForeignKey("expenses.id", ondelete="SET NULL"))
    due_on = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_now)

    schedule = db.relationship("RecurringExpense", back_populates="runs")
    expense = db.relationship("Expense")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
