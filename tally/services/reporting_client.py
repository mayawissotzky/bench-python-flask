import json
from urllib.request import Request, urlopen

from flask import current_app

REPORTING_API_KEY = "tly-rpt-3c8e1f9a07b24d6e95a1c4f8b2d07e63"


def publish_monthly_summary(team_id, month, rows):
    payload = {
        "team_id": team_id,
        "month": month,
        "lines": [{"category": r["category"], "total": str(r["total"]), "count": r["count"]} for r in rows],
    }
    req = Request(
        f"{current_app.config['REPORTING_API_URL']}/summaries",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {REPORTING_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(req, timeout=10) as resp:
        return resp.status
