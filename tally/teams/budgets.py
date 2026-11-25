from datetime import date
from decimal import Decimal, InvalidOperation

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from markupsafe import Markup, escape
from sqlalchemy import select, text

from ..extensions import db
from ..models import Budget, Team
from . import bp

SORTABLE = ("category", "monthly_limit", "spent")


def _month_start(today=None):
    today = today or date.today()
    return today.replace(day=1)


def _spent_by_category(team_id, start):
    rows = db.session.execute(
        text(
            "SELECT category, COALESCE(SUM(amount), 0) AS spent FROM expenses "
            "WHERE team_id = :team AND spent_on >= :start AND status != 'rejected' "
            "GROUP BY category"
        ),
        {"team": team_id, "start": start},
    )
    return {row.category: row.spent for row in rows}


def _budget_rows(team_id, sort):
    sql = (
        "SELECT * FROM (SELECT b.id, b.category, b.monthly_limit, b.note, "
        "COALESCE(SUM(e.amount), 0) AS spent FROM budgets b "
        "LEFT JOIN expenses e ON e.team_id = b.team_id AND e.category = b.category "
        "AND e.spent_on >= :start AND e.status != 'rejected' "
        "WHERE b.team_id = :team GROUP BY b.id) AS budget_rows "
        f"ORDER BY {sort}"
    )
    return db.session.execute(text(sql), {"team": team_id, "start": _month_start()}).all()


def _over_budget_banner(team_id, rows):
    spent = _spent_by_category(team_id, _month_start())
    over = [r.category for r in rows if spent.get(r.category, 0) > r.monthly_limit]
    if not over:
        return None
    names = ", ".join(str(escape(c)) for c in over)
    return Markup(f"<strong>Over budget this month:</strong> {names}")


def _parse_limit(raw):
    try:
        value = Decimal(raw)
    except (InvalidOperation, TypeError):
        return None
    return value if value > 0 else None


@bp.get("/<int:team_id>/budgets")
def budgets(team_id):
    sort = request.args.get("sort", "category")
    rows = _budget_rows(team_id, sort)
    return render_template(
        "teams/budgets.html",
        team=db.session.get(Team, team_id),
        rows=rows,
        banner=_over_budget_banner(team_id, rows),
        sortable=SORTABLE,
        sort=sort,
    )


@bp.post("/<int:team_id>/budgets")
def create_budget(team_id):
    if not current_user.is_manager:
        abort(403)
    category = request.form.get("category", "").strip()[:40]
    limit = _parse_limit(request.form.get("monthly_limit"))
    if not category or limit is None:
        flash("Category and a positive monthly limit are required.", "error")
    else:
        db.session.add(Budget(team_id=team_id, category=category, monthly_limit=limit,
                              note=request.form.get("note", "")))
        db.session.commit()
        flash("Budget added.", "success")
    return redirect(url_for("teams.budgets", team_id=team_id))


@bp.post("/<int:team_id>/budgets/<int:budget_id>/edit")
def edit_budget(team_id, budget_id):
    if not current_user.is_manager:
        abort(403)
    budget = db.first_or_404(select(Budget).filter_by(id=budget_id, team_id=team_id))
    limit = _parse_limit(request.form.get("monthly_limit"))
    if limit is not None:
        budget.monthly_limit = limit
    budget.note = request.form.get("note", budget.note)
    db.session.commit()
    flash("Budget updated.", "success")
    return redirect(url_for("teams.budgets", team_id=team_id))


@bp.post("/<int:team_id>/budgets/<int:budget_id>/delete")
def delete_budget(team_id, budget_id):
    if not current_user.is_manager:
        abort(403)
    budget = db.get_or_404(Budget, budget_id)
    db.session.delete(budget)
    db.session.commit()
    flash("Budget removed.", "success")
    return redirect(url_for("teams.budgets", team_id=team_id))
