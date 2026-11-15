"""Team category budgets: validation, persistence and spend-vs-budget tracking."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from flask import abort
from sqlalchemy import case, func, select

from ..extensions import db
from ..models import Budget, Expense
from .expense_service import parse_amount

DEFAULT_WARN_PERCENT = 80
HISTORY_MONTHS = 6
ZERO = Decimal("0.00")


@dataclass
class BudgetLine:
    """One row of the monthly budget overview."""

    category: str
    currency: str
    budget: Budget | None
    approved: Decimal
    pending: Decimal
    expense_count: int

    @property
    def spent(self):
        return self.approved + self.pending

    @property
    def limit(self):
        return self.budget.limit_amount if self.budget else None

    @property
    def remaining(self):
        if self.budget is None:
            return None
        return self.budget.limit_amount - self.spent

    @property
    def percent_used(self):
        if self.budget is None:
            return None
        return percent_of(self.spent, self.budget.limit_amount)

    @property
    def state(self):
        if self.budget is None:
            return "unbudgeted"
        return utilization_state(self.spent, self.budget.limit_amount, self.budget.warn_at_percent)


# --- small pure helpers -----------------------------------------------------


def first_of_month(day):
    return day.replace(day=1)


def shift_month(month_start, delta):
    """Move a first-of-month date forward (or back) by ``delta`` months."""
    index = month_start.year * 12 + (month_start.month - 1) + delta
    return date(index // 12, index % 12 + 1, 1)


def month_bounds(month_start):
    return month_start, shift_month(month_start, 1)


def parse_month(raw):
    """Parse ``YYYY-MM`` into the first day of that month (current month when empty)."""
    if not raw:
        return first_of_month(date.today())
    try:
        return date.fromisoformat(f"{raw}-01")
    except ValueError:
        abort(400, "Use YYYY-MM for the month")


def percent_of(part, whole):
    if not whole:
        return 0
    return int((Decimal(part) * 100 / Decimal(whole)).to_integral_value())


def utilization_state(spent, limit, warn_at_percent=DEFAULT_WARN_PERCENT):
    used = percent_of(spent, limit)
    if used > 100:
        return "over"
    if used >= warn_at_percent:
        return "warning"
    return "ok"


def parse_warn_percent(raw):
    if raw in (None, ""):
        return DEFAULT_WARN_PERCENT
    try:
        value = int(raw)
    except (TypeError, ValueError):
        abort(400, "Warning threshold must be a whole number")
    if not 1 <= value <= 100:
        abort(400, "Warning threshold must be between 1 and 100")
    return value


def parse_currency(raw):
    currency = (raw or "USD").strip().upper()
    if len(currency) != 3 or not currency.isalpha():
        abort(400, "Currency must be a three-letter code")
    return currency


def validate_category(raw, categories):
    if raw not in categories:
        abort(400, "Unknown category")
    return raw


# --- persistence --------------------------------------------------------------


def list_budgets(team_id, month_start):
    stmt = (
        select(Budget)
        .where(Budget.team_id == team_id, Budget.month == month_start)
        .order_by(Budget.category)
    )
    return db.session.scalars(stmt).all()


def get_team_budget_or_404(team_id, budget_id):
    return db.first_or_404(select(Budget).filter_by(id=budget_id, team_id=team_id))


def find_budget(team_id, category, month_start):
    stmt = select(Budget).filter_by(team_id=team_id, category=category, month=month_start)
    return db.session.scalar(stmt)


def create_budget(team_id, user, form, categories):
    """Create a budget from a submitted form. Returns ``None`` if one already exists."""
    month_start = parse_month(form.get("month"))
    category = validate_category(form.get("category"), categories)
    if find_budget(team_id, category, month_start) is not None:
        return None
    budget = Budget(
        team_id=team_id,
        category=category,
        month=month_start,
        limit_amount=parse_amount(form.get("limit")),
        currency=parse_currency(form.get("currency")),
        warn_at_percent=parse_warn_percent(form.get("warn_at_percent")),
        note=form.get("note", "").strip()[:255],
        created_by_id=user.id,
    )
    db.session.add(budget)
    db.session.commit()
    return budget


def update_budget(budget, form):
    if form.get("limit"):
        budget.limit_amount = parse_amount(form["limit"])
    if form.get("currency"):
        budget.currency = parse_currency(form["currency"])
    budget.warn_at_percent = parse_warn_percent(form.get("warn_at_percent"))
    budget.note = form.get("note", budget.note).strip()[:255]
    db.session.commit()
    return budget


def delete_budget(budget):
    db.session.delete(budget)
    db.session.commit()


def copy_budgets(team_id, source_month, target_month, user):
    """Copy every budget of ``source_month`` into ``target_month``, keeping existing ones.

    Returns the number of budgets created.
    """
    existing = {b.category for b in list_budgets(team_id, target_month)}
    created = 0
    for source in list_budgets(team_id, source_month):
        if source.category in existing:
            continue
        db.session.add(
            Budget(
                team_id=team_id,
                category=source.category,
                month=target_month,
                limit_amount=source.limit_amount,
                currency=source.currency,
                warn_at_percent=source.warn_at_percent,
                note=source.note,
                created_by_id=user.id,
            )
        )
        created += 1
    db.session.commit()
    return created


# --- spend tracking -----------------------------------------------------------


def spending_by_category(team_id, start, end, category=None):
    """Approved and pending spend per (category, currency); rejected expenses are ignored."""
    approved = func.coalesce(func.sum(case((Expense.status == "approved", Expense.amount), else_=0)), 0)
    pending = func.coalesce(func.sum(case((Expense.status == "pending", Expense.amount), else_=0)), 0)
    stmt = (
        select(
            Expense.category,
            Expense.currency,
            approved.label("approved"),
            pending.label("pending"),
            func.count(Expense.id).label("expense_count"),
        )
        .where(
            Expense.team_id == team_id,
            Expense.spent_on >= start,
            Expense.spent_on < end,
            Expense.status != "rejected",
        )
        .group_by(Expense.category, Expense.currency)
    )
    if category is not None:
        stmt = stmt.where(Expense.category == category)
    return {
        (row.category, row.currency): (Decimal(row.approved), Decimal(row.pending), row.expense_count)
        for row in db.session.execute(stmt)
    }


def budget_overview(team_id, month_start):
    """Combine the month's budgets with the month's spend.

    Budgeted categories come first (in category order), followed by any
    category/currency pair that has spend but no matching budget.
    """
    start, end = month_bounds(month_start)
    spend = spending_by_category(team_id, start, end)
    lines = []
    for budget in list_budgets(team_id, month_start):
        approved, pending, count = spend.pop((budget.category, budget.currency), (ZERO, ZERO, 0))
        lines.append(BudgetLine(budget.category, budget.currency, budget, approved, pending, count))
    for (category, currency), (approved, pending, count) in sorted(spend.items()):
        lines.append(BudgetLine(category, currency, None, approved, pending, count))
    return lines


def overview_totals(lines):
    """Totals per currency across the budgeted lines of an overview."""
    totals = {}
    for line in lines:
        if line.budget is None:
            continue
        entry = totals.setdefault(line.currency, {"limit": ZERO, "spent": ZERO})
        entry["limit"] += line.budget.limit_amount
        entry["spent"] += line.spent
    for entry in totals.values():
        entry["remaining"] = entry["limit"] - entry["spent"]
        entry["percent_used"] = percent_of(entry["spent"], entry["limit"])
    return totals


def category_history(team_id, category, end_month, months=HISTORY_MONTHS):
    """Budget vs spend for one category over the ``months`` months ending at ``end_month``."""
    first = shift_month(end_month, -(months - 1))
    budgets = db.session.scalars(
        select(Budget).where(
            Budget.team_id == team_id,
            Budget.category == category,
            Budget.month >= first,
            Budget.month <= end_month,
        )
    ).all()
    by_month = {b.month: b for b in budgets}

    history = []
    for offset in range(months):
        month_start = shift_month(first, offset)
        start, end = month_bounds(month_start)
        budget = by_month.get(month_start)
        currency = budget.currency if budget else None
        approved = pending = ZERO
        count = 0
        for (_, cur), (a, p, c) in spending_by_category(team_id, start, end, category).items():
            if currency is None or cur == currency:
                approved += a
                pending += p
                count += c
        history.append(
            {
                "month": month_start,
                "line": BudgetLine(category, currency or "", budget, approved, pending, count),
            }
        )
    return history
