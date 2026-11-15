import csv
import io

from flask import Response, abort, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from ..services import budget_service
from . import bp


def _require_manager():
    if not current_user.is_manager:
        abort(403)


def _categories():
    return current_app.config["EXPENSE_CATEGORIES"]


def _overview_url(month_start):
    return url_for("budgets.index", month=month_start.strftime("%Y-%m"))


@bp.get("/")
def index():
    month_start = budget_service.parse_month(request.args.get("month"))
    lines = budget_service.budget_overview(current_user.team_id, month_start)
    return render_template(
        "budgets/index.html",
        lines=lines,
        totals=budget_service.overview_totals(lines),
        month=month_start.strftime("%Y-%m"),
        previous_month=budget_service.shift_month(month_start, -1).strftime("%Y-%m"),
        next_month=budget_service.shift_month(month_start, 1).strftime("%Y-%m"),
    )


@bp.route("/new", methods=["GET", "POST"])
def create():
    _require_manager()
    if request.method == "POST":
        budget = budget_service.create_budget(current_user.team_id, current_user, request.form, _categories())
        if budget is None:
            flash("That category already has a budget for this month.", "error")
        else:
            flash(f"Budget for {budget.category} added.", "success")
            return redirect(_overview_url(budget.month))
    month_start = budget_service.parse_month(request.values.get("month"))
    return render_template(
        "budgets/form.html",
        budget=None,
        categories=_categories(),
        month=month_start.strftime("%Y-%m"),
        selected_category=request.values.get("category", ""),
    )


@bp.route("/<int:budget_id>/edit", methods=["GET", "POST"])
def edit(budget_id):
    _require_manager()
    budget = budget_service.get_team_budget_or_404(current_user.team_id, budget_id)
    if request.method == "POST":
        budget_service.update_budget(budget, request.form)
        flash("Budget updated.", "success")
        return redirect(_overview_url(budget.month))
    return render_template(
        "budgets/form.html",
        budget=budget,
        categories=_categories(),
        month=budget.month.strftime("%Y-%m"),
        selected_category=budget.category,
    )


@bp.post("/<int:budget_id>/delete")
def delete(budget_id):
    _require_manager()
    budget = budget_service.get_team_budget_or_404(current_user.team_id, budget_id)
    month_start = budget.month
    budget_service.delete_budget(budget)
    flash("Budget removed.", "success")
    return redirect(_overview_url(month_start))


@bp.post("/copy")
def copy_previous():
    _require_manager()
    target = budget_service.parse_month(request.form.get("month"))
    source = budget_service.shift_month(target, -1)
    created = budget_service.copy_budgets(current_user.team_id, source, target, current_user)
    if created:
        flash(f"Copied {created} budget(s) from {source:%Y-%m}.", "success")
    else:
        flash(f"Nothing to copy from {source:%Y-%m}.", "error")
    return redirect(_overview_url(target))


@bp.get("/history")
def history():
    category = request.args.get("category", "")
    if category not in _categories():
        abort(404)
    end_month = budget_service.parse_month(request.args.get("month"))
    rows = budget_service.category_history(current_user.team_id, category, end_month)
    return render_template(
        "budgets/history.html",
        category=category,
        rows=rows,
        month=end_month.strftime("%Y-%m"),
    )


@bp.get("/export.csv")
def export_csv():
    month_start = budget_service.parse_month(request.args.get("month"))
    lines = budget_service.budget_overview(current_user.team_id, month_start)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["category", "currency", "limit", "approved", "pending", "spent", "remaining", "percent_used"])
    for line in lines:
        writer.writerow(
            [
                line.category,
                line.currency,
                line.limit if line.limit is not None else "",
                line.approved,
                line.pending,
                line.spent,
                line.remaining if line.remaining is not None else "",
                line.percent_used if line.percent_used is not None else "",
            ]
        )
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=tally-budgets-{month_start:%Y-%m}.csv"},
    )


@bp.get("/summary.json")
def summary_json():
    month_start = budget_service.parse_month(request.args.get("month"))
    lines = budget_service.budget_overview(current_user.team_id, month_start)
    return jsonify(
        month=month_start.strftime("%Y-%m"),
        lines=[
            {
                "category": line.category,
                "currency": line.currency,
                "budget": line.budget.to_dict() if line.budget else None,
                "approved": str(line.approved),
                "pending": str(line.pending),
                "spent": str(line.spent),
                "remaining": str(line.remaining) if line.remaining is not None else None,
                "percent_used": line.percent_used,
                "state": line.state,
            }
            for line in lines
        ],
        totals={
            currency: {key: str(value) if key != "percent_used" else value for key, value in entry.items()}
            for currency, entry in budget_service.overview_totals(lines).items()
        },
    )
