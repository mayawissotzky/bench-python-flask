"""Recurring expense schedules: form validation, date maths and expense generation.

A schedule remembers its anchor ``start_date`` and how many occurrences have been
generated so far. The next due date is always computed from the anchor, so a
monthly schedule that starts on the 31st lands on the last day of shorter months
and goes back to the 31st afterwards instead of drifting to the 28th.
"""

import calendar
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import select

from ..extensions import db
from ..models import Expense, RecurringExpense, RecurringRun, User

FREQUENCIES = {
    "weekly": "Every week",
    "monthly": "Every month",
    "quarterly": "Every quarter",
    "yearly": "Every year",
}

MAX_AMOUNT = Decimal("1000000")
MAX_NOTES = 2000
# Upper bound of expenses created for one schedule in a single run, so a schedule
# that was left untouched for years does not flood the expense list in one go.
MAX_CATCH_UP = 24


def _add_months(anchor, months):
    month_index = anchor.month - 1 + months
    year = anchor.year + month_index // 12
    month = month_index % 12 + 1
    day = min(anchor.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def occurrence(start, frequency, index):
    """Return the date of occurrence number ``index`` (0-based) of a schedule."""
    if index < 0:
        raise ValueError("index must not be negative")
    if frequency == "weekly":
        return start + timedelta(weeks=index)
    if frequency == "monthly":
        return _add_months(start, index)
    if frequency == "quarterly":
        return _add_months(start, index * 3)
    if frequency == "yearly":
        return _add_months(start, index * 12)
    raise ValueError(f"unknown frequency: {frequency}")


def upcoming(schedule, count=5):
    """The next ``count`` due dates of a schedule, respecting its end date."""
    dates = []
    index = schedule.occurrences
    while len(dates) < count:
        due = occurrence(schedule.start_date, schedule.frequency, index)
        if schedule.end_date is not None and due > schedule.end_date:
            break
        dates.append(due)
        index += 1
    return dates


def monthly_equivalent(schedule):
    """Rough monthly cost of a schedule, used for the totals on the list page."""
    factor = {
        "weekly": Decimal("52") / Decimal("12"),
        "monthly": Decimal("1"),
        "quarterly": Decimal("1") / Decimal("3"),
        "yearly": Decimal("1") / Decimal("12"),
    }[schedule.frequency]
    return (schedule.amount * factor).quantize(Decimal("0.01"))


@dataclass
class ScheduleForm:
    description: str = ""
    category: str = "other"
    amount: Decimal | None = None
    currency: str = "USD"
    frequency: str = "monthly"
    start_date: date | None = None
    end_date: date | None = None
    notes: str = ""
    errors: list = field(default_factory=list)

    @property
    def ok(self):
        return not self.errors


def _parse_date(raw, label, errors, required):
    raw = (raw or "").strip()
    if not raw:
        if required:
            errors.append(f"{label} is required.")
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        errors.append(f"{label} must be a date (YYYY-MM-DD).")
        return None


def parse_form(form, categories):
    """Validate a submitted schedule form. Never raises; problems end up in ``errors``."""
    errors = []
    data = ScheduleForm(errors=errors)

    data.description = (form.get("description") or "").strip()
    if not data.description:
        errors.append("Description is required.")
    elif len(data.description) > 255:
        errors.append("Description must be at most 255 characters.")

    data.category = form.get("category") or "other"
    if data.category not in categories:
        errors.append("Pick one of the listed categories.")

    raw_amount = (form.get("amount") or "").strip().replace(",", "")
    try:
        amount = Decimal(raw_amount)
    except InvalidOperation:
        amount = None
    if amount is None or not amount.is_finite():
        errors.append("Amount must be a number.")
    elif amount <= 0 or amount >= MAX_AMOUNT:
        errors.append("Amount must be greater than 0 and below 1,000,000.")
    else:
        data.amount = amount.quantize(Decimal("0.01"))

    data.currency = (form.get("currency") or "USD").strip().upper()
    if len(data.currency) != 3 or not data.currency.isascii() or not data.currency.isalpha():
        errors.append("Currency must be a three-letter code such as USD.")

    data.frequency = form.get("frequency") or "monthly"
    if data.frequency not in FREQUENCIES:
        errors.append("Pick one of the listed frequencies.")

    data.start_date = _parse_date(form.get("start_date"), "Start date", errors, required=True)
    data.end_date = _parse_date(form.get("end_date"), "End date", errors, required=False)
    if data.start_date and data.end_date and data.end_date < data.start_date:
        errors.append("End date must be on or after the start date.")

    data.notes = (form.get("notes") or "").strip()
    if len(data.notes) > MAX_NOTES:
        errors.append(f"Notes must be at most {MAX_NOTES} characters.")

    return data


def _apply(schedule, data):
    schedule.description = data.description
    schedule.category = data.category
    schedule.amount = data.amount
    schedule.currency = data.currency
    schedule.notes = data.notes
    schedule.end_date = data.end_date


def create_schedule(owner, data):
    schedule = RecurringExpense(
        owner_id=owner.id,
        frequency=data.frequency,
        start_date=data.start_date,
        next_due=data.start_date,
        occurrences=0,
        active=True,
    )
    _apply(schedule, data)
    db.session.add(schedule)
    db.session.commit()
    return schedule


def update_schedule(schedule, data):
    """Update a schedule. Changing frequency or start date restarts the count."""
    _apply(schedule, data)
    if data.frequency != schedule.frequency or data.start_date != schedule.start_date:
        schedule.frequency = data.frequency
        schedule.start_date = data.start_date
        schedule.occurrences = 0
        schedule.next_due = data.start_date
    db.session.commit()
    return schedule


def owned_schedules(owner_id):
    return db.session.scalars(
        select(RecurringExpense)
        .where(RecurringExpense.owner_id == owner_id)
        .order_by(RecurringExpense.active.desc(), RecurringExpense.next_due, RecurringExpense.id)
    ).all()


def get_owned_schedule(owner_id, schedule_id):
    return db.first_or_404(select(RecurringExpense).filter_by(id=schedule_id, owner_id=owner_id))


def team_schedules(team_id):
    return db.session.scalars(
        select(RecurringExpense)
        .join(User, RecurringExpense.owner_id == User.id)
        .where(User.team_id == team_id)
        .order_by(User.name, RecurringExpense.next_due)
    ).all()


def _generate_for(schedule, today):
    created = 0
    owner = schedule.owner
    while created < MAX_CATCH_UP and schedule.active and not schedule.finished and schedule.next_due <= today:
        due = schedule.next_due
        expense = Expense(
            owner_id=schedule.owner_id,
            team_id=owner.team_id,
            description=schedule.description,
            category=schedule.category,
            amount=schedule.amount,
            currency=schedule.currency,
            spent_on=due,
            status="pending",
            notes=schedule.notes,
        )
        db.session.add(expense)
        db.session.flush()
        db.session.add(RecurringRun(schedule_id=schedule.id, expense_id=expense.id, due_on=due))
        schedule.occurrences += 1
        schedule.next_due = occurrence(schedule.start_date, schedule.frequency, schedule.occurrences)
        created += 1
    if created:
        schedule.last_generated_at = datetime.now(timezone.utc)
    return created


def generate_due(schedules, today=None):
    """Create pending expenses for every due occurrence. Returns the number created."""
    today = today or date.today()
    created = sum(_generate_for(schedule, today) for schedule in schedules)
    db.session.commit()
    return created


def generate_due_for_owner(owner_id, today=None):
    return generate_due(owned_schedules(owner_id), today)


def generate_due_for_all(today=None):
    today = today or date.today()
    schedules = db.session.scalars(
        select(RecurringExpense).where(RecurringExpense.active.is_(True), RecurringExpense.next_due <= today)
    ).all()
    return generate_due(schedules, today)


def skip_next(schedule):
    """Move past the next occurrence without creating an expense for it."""
    if schedule.finished:
        return False
    schedule.occurrences += 1
    schedule.next_due = occurrence(schedule.start_date, schedule.frequency, schedule.occurrences)
    db.session.commit()
    return True


def set_active(schedule, active):
    schedule.active = active
    db.session.commit()


def delete_schedule(schedule):
    db.session.delete(schedule)
    db.session.commit()
