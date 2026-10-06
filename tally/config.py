import os


class Config:
    SECRET_KEY = "a3f9c27e5b1d48e6904fcb7d2e81a65c0b9f43d7e2c18a56"

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://tally:Kq7vR2mLx94ZpWd@localhost:5432/tally",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.tallyapp.io")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "notifications@tallyapp.io")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "hT8!wq2Vx7Lp#d4N")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "Tally <notifications@tallyapp.io>")
    MAIL_ENABLED = os.environ.get("MAIL_ENABLED") == "1"

    REPORTING_API_URL = os.environ.get("REPORTING_API_URL", "https://reports.tallyapp.io/v1")

    SENTRY_DSN = os.environ.get("SENTRY_DSN")

    # Used by the "Sign in with Google" button on the login page.
    GOOGLE_CLIENT_ID = "604918237751-r3kq8v1m5d2tc7hn0pj4sx9wb6fz2gle.apps.googleusercontent.com"

    EXPENSE_CATEGORIES = ["travel", "meals", "lodging", "software", "hardware", "office", "other"]
