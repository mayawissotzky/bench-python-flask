# Tally

Tally is a lightweight expense tracker for small teams. Members log expenses and
receipt notes, managers approve them, and everyone gets monthly, category and
yearly reports for their team (with a CSV export for the bookkeeper).

## Features

- Accounts with email + password sign-in
- Teams with a manager and members
- Expenses with categories, receipt notes and an approval workflow
- Status e-mails to the expense owner when an expense is approved or rejected
- Monthly / category / yearly team reports and CSV export
- Profile page (display name, website, short bio)
- Monthly per-category team budgets with usage tracking
- Small JSON API for the mobile companion app

## Local setup

Requirements: Python 3.12+ and PostgreSQL 15+.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL=postgresql+psycopg://tally:<password>@localhost:5432/tally
flask --app wsgi init-db
flask --app wsgi seed          # optional demo data
flask --app wsgi run --debug
```

### Docker

```bash
cp .env.example .env   # then edit the values
docker compose up --build
docker compose exec web flask --app wsgi init-db
```

The app listens on http://localhost:8000.

## Configuration

All settings are read from environment variables (see `.env.example`):

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLAlchemy URL for Postgres |
| `MAIL_SERVER`, `MAIL_USERNAME`, `MAIL_PASSWORD` | SMTP account for status e-mails |
| `MAIL_ENABLED` | Set to `1` to actually send e-mails |
| `REPORTING_API_URL` | Finance reporting service that receives published monthly summaries |
| `SENTRY_DSN` | Optional error reporting |

## Budgets

Teams can set a monthly spending limit per expense category under **Budgets**
(`/budgets`). The overview compares each budget with the month's approved and
pending expenses (rejected ones are ignored), flags categories that pass their
warning threshold or go over the limit, and lists categories that have spend
but no budget yet.

- Everyone on the team can view budgets, the per-category history
  (`/budgets/history?category=travel`) and download the month as CSV
  (`/budgets/export.csv?month=YYYY-MM`).
- Managers can add, edit and remove budgets, and copy last month's budgets
  into the current month with one click (budgets that already exist are kept).
- `GET /budgets/summary.json?month=YYYY-MM` returns the same overview as JSON
  for the mobile companion app.

Budgets are stored in a new `budgets` table. Existing installs need to run
`flask --app wsgi init-db` once after upgrading; it only creates missing tables.

| Field | Meaning |
|---|---|
| Category | One of the configured expense categories |
| Month | The calendar month the limit applies to |
| Monthly limit / currency | Only expenses in the same currency count toward the budget |
| Warn at | Percentage of the limit at which the category is flagged (default 80%) |
| Note | Optional context shown under the category name |
