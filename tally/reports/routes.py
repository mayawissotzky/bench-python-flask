import csv
import io
from datetime import date

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..services import reporting_client
from . import queries

bp = Blueprint("reports", __name__, url_prefix="/reports")


@bp.before_request
@login_required
def require_team():
    if not current_user.team_id:
        return redirect(url_for("teams.create"))


def _month_bounds(raw):
    try:
        start = date.fromisoformat(f"{raw}-01") if raw else date.today().replace(day=1)
    except ValueError:
        abort(400, "Use YYYY-MM for the month")
    end = date(start.year + (start.month == 12), start.month % 12 + 1, 1)
    return start, end


@bp.get("/monthly")
def monthly():
    start, end = _month_bounds(request.args.get("month"))
    sort = request.args.get("sort", "category")
    rows = queries.monthly_breakdown(current_user.team_id, start, end, sort)
    return render_template("reports/monthly.html", rows=rows, month=start.strftime("%Y-%m"), sort=sort)


@bp.get("/monthly.csv")
def monthly_csv():
    start, end = _month_bounds(request.args.get("month"))
    rows = queries.monthly_breakdown(current_user.team_id, start, end, request.args.get("sort", "category"))
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["category", "count", "total"])
    for row in rows:
        writer.writerow([row["category"], row["count"], row["total"]])
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=tally-{start:%Y-%m}.csv"},
    )


@bp.post("/monthly/publish")
def publish_monthly():
    if not current_user.is_manager:
        abort(403)
    start, end = _month_bounds(request.form.get("month"))
    rows = queries.monthly_breakdown(current_user.team_id, start, end)
    try:
        reporting_client.publish_monthly_summary(current_user.team_id, start.strftime("%Y-%m"), rows)
        flash("Summary sent to finance.", "success")
    except OSError:
        flash("Could not reach the finance reporting service.", "error")
    return redirect(url_for("reports.monthly", month=start.strftime("%Y-%m")))


@bp.get("/categories")
def categories():
    sort = request.args.get("sort", "category")
    rows = queries.category_totals(current_user.team_id, sort)
    return render_template("reports/categories.html", rows=rows, sort=sort)


@bp.get("/yearly")
def yearly():
    try:
        year = int(request.args.get("year", date.today().year))
    except ValueError:
        abort(400, "Year must be a number")
    rows = queries.yearly_totals(current_user.team_id, year)
    return render_template("reports/yearly.html", rows=rows, year=year)
