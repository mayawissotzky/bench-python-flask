"""Data access for tags. Every query is scoped to the owning user."""

from decimal import Decimal

from sqlalchemy import func, select

from ..extensions import db
from ..models import Expense, Tag, expense_tags

MAX_TAGS_PER_USER = 50
MAX_TAGS_PER_EXPENSE = 10
BULK_PAGE_SIZE = 100
STATUSES = ("pending", "approved", "rejected")


class TagLimitError(ValueError):
    pass


def user_tags(user_id):
    return db.session.scalars(select(Tag).where(Tag.owner_id == user_id).order_by(Tag.name)).all()


def tag_overview(user_id):
    """Tags with how many expenses use each one, alphabetically."""
    stmt = (
        select(Tag, func.count(expense_tags.c.expense_id))
        .outerjoin(expense_tags, expense_tags.c.tag_id == Tag.id)
        .where(Tag.owner_id == user_id)
        .group_by(Tag.id)
        .order_by(Tag.name)
    )
    return [{"tag": tag, "count": count} for tag, count in db.session.execute(stmt)]


def get_user_tag_or_404(user_id, tag_id):
    return db.first_or_404(select(Tag).where(Tag.id == tag_id, Tag.owner_id == user_id))


def get_user_expense_or_404(user_id, expense_id):
    return db.first_or_404(select(Expense).where(Expense.id == expense_id, Expense.owner_id == user_id))


def name_taken(user_id, name, exclude_id=None):
    stmt = select(Tag.id).where(Tag.owner_id == user_id, func.lower(Tag.name) == name.lower())
    if exclude_id is not None:
        stmt = stmt.where(Tag.id != exclude_id)
    return db.session.scalar(stmt) is not None


def create_tag(user_id, fields):
    count = db.session.scalar(select(func.count(Tag.id)).where(Tag.owner_id == user_id))
    if count >= MAX_TAGS_PER_USER:
        raise TagLimitError(f"You can have at most {MAX_TAGS_PER_USER} tags.")
    tag = Tag(owner_id=user_id, **fields)
    db.session.add(tag)
    db.session.commit()
    return tag


def update_tag(tag, fields):
    for key, value in fields.items():
        setattr(tag, key, value)
    db.session.commit()
    return tag


def delete_tag(tag):
    tag.expenses.clear()
    db.session.delete(tag)
    db.session.commit()


def tagged_expenses(user_id, tag, status=None):
    stmt = (
        select(Expense)
        .join(expense_tags, expense_tags.c.expense_id == Expense.id)
        .where(expense_tags.c.tag_id == tag.id, Expense.owner_id == user_id)
        .order_by(Expense.spent_on.desc(), Expense.id.desc())
    )
    if status in STATUSES:
        stmt = stmt.where(Expense.status == status)
    return db.session.scalars(stmt).all()


def totals_by_currency(expenses):
    """Sum amounts per currency; mixing currencies in one number would be wrong."""
    totals = {}
    for expense in expenses:
        entry = totals.setdefault(expense.currency, {"currency": expense.currency, "count": 0, "total": Decimal("0")})
        entry["count"] += 1
        entry["total"] += Decimal(expense.amount)
    return sorted(totals.values(), key=lambda row: row["currency"])


def set_expense_tags(user_id, expense, tag_ids):
    """Replace the tags on one of the user's expenses with the given (owned) tags."""
    if len(tag_ids) > MAX_TAGS_PER_EXPENSE:
        raise TagLimitError(f"An expense can have at most {MAX_TAGS_PER_EXPENSE} tags.")
    tags = []
    if tag_ids:
        tags = db.session.scalars(select(Tag).where(Tag.owner_id == user_id, Tag.id.in_(tag_ids))).all()
    expense.tags = sorted(tags, key=lambda t: t.name.lower())
    db.session.commit()
    return expense.tags


def recent_expenses(user_id, limit=BULK_PAGE_SIZE):
    stmt = (
        select(Expense)
        .where(Expense.owner_id == user_id)
        .order_by(Expense.spent_on.desc(), Expense.id.desc())
        .limit(limit)
    )
    return db.session.scalars(stmt).all()


def bulk_apply(user_id, tag, expense_ids, remove=False):
    """Add (or remove) a tag on several of the user's expenses. Returns how many changed."""
    if not expense_ids:
        return 0
    expenses = db.session.scalars(
        select(Expense).where(Expense.owner_id == user_id, Expense.id.in_(expense_ids))
    ).all()
    changed = 0
    for expense in expenses:
        has_tag = tag in expense.tags
        if remove and has_tag:
            expense.tags.remove(tag)
            changed += 1
        elif not remove and not has_tag and len(expense.tags) < MAX_TAGS_PER_EXPENSE:
            expense.tags.append(tag)
            changed += 1
    db.session.commit()
    return changed
