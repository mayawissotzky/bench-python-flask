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
