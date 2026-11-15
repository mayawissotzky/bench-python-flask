# Tally

Tally is a lightweight expense tracker for small teams. Members log expenses and
receipt notes, managers approve them, and everyone gets monthly, category and
yearly reports for their team (with a CSV export for the bookkeeper).

## Features

- Accounts with email + password sign-in
- Teams with a manager and members
- Expenses with categories, receipt notes and an approval workflow
- Status e-mails to the expense owner when an expense is approved or rejected
- Recurring expenses (subscriptions, rent, phone plans) that turn into pending expenses when due
- Monthly / category / yearly team reports and CSV export
- Profile page (display name, website, short bio)
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

## Recurring expenses

Costs that come back on a fixed schedule can be set up once under **Recurring**
instead of being re-entered every month.

- A schedule has a description, category, amount, currency, a frequency
  (weekly, monthly, quarterly or yearly), a first occurrence and an optional
  last occurrence.
- Monthly, quarterly and yearly schedules keep the day of the first occurrence:
  a schedule starting on the 31st lands on the last day of shorter months and
  returns to the 31st afterwards.
- **Create due expenses** on the Recurring page adds a pending expense to
  *My expenses* for every occurrence that is due, which then goes through the
  normal approval flow. At most 24 occurrences are created per schedule in one
  run.
- Schedules can be paused, resumed, edited, or told to skip their next
  occurrence. Deleting a schedule keeps the expenses it already created.
- Managers get a read-only overview of the recurring expenses of everyone on
  their team at `/recurring/team`.

To create due expenses for every user, for example from a daily cron job:

```bash
flask --app wsgi generate-recurring
flask --app wsgi generate-recurring --date 2026-12-01   # treat that day as today
```

The new tables are created by `flask --app wsgi init-db`.

### Tests

```bash
python -m unittest discover tests
```
