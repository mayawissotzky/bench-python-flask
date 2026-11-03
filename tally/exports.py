import csv
import io

from flask import Blueprint, Response, jsonify, request
from flask_login import current_user, login_required

from .services import expense_service

bp = Blueprint("exports", __name__, url_prefix="/exports")

COLUMNS = ["id", "description", "category", "amount", "currency", "spent_on", "status"]


@bp.get("/expenses")
@login_required
def expenses():
    fmt = request.args.get("format", "csv")
    if fmt not in ("csv", "json"):
        return f"<p>Unsupported export format: {fmt}</p>", 400
    rows = expense_service.list_expenses(current_user.id, {})
    if fmt == "json":
        return jsonify([{**row, "amount": str(row["amount"]), "spent_on": row["spent_on"].isoformat()} for row in rows])
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    return Response(
        out.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=expenses.csv"},
    )
