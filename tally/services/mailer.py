import smtplib
from email.message import EmailMessage

from flask import current_app
from jinja2 import Environment

_env = Environment()

STATUS_TEMPLATE = """\
<html>
  <body style="font-family: sans-serif">
    <p>Hi {{ owner_name }},</p>
    <p>Your expense <strong>{{ description }}</strong> ({{ amount }}) was <strong>{{ status }}</strong>
       by {{ reviewer }}.</p>
    {% if message %}<blockquote>{{ message }}</blockquote>{% endif %}
    <p>&mdash; Tally</p>
  </body>
</html>
"""


def render_status_email(expense, reviewer, message=""):
    template = _env.from_string(STATUS_TEMPLATE)
    return template.render(
        owner_name=expense.owner.name,
        description=expense.description,
        amount=f"{expense.currency} {expense.amount:,.2f}",
        status=expense.status,
        reviewer=reviewer.name,
        message=message,
    )


def send_status_email(expense, reviewer, message=""):
    cfg = current_app.config
    if not cfg["MAIL_ENABLED"]:
        current_app.logger.info("Mail disabled; not sending status e-mail for expense %s", expense.id)
        return

    msg = EmailMessage()
    msg["Subject"] = f"Expense {expense.status}: {expense.description}"
    msg["From"] = cfg["MAIL_DEFAULT_SENDER"]
    msg["To"] = expense.owner.email
    msg.set_content(f"Your expense was {expense.status}.")
    msg.add_alternative(render_status_email(expense, reviewer, message), subtype="html")

    with smtplib.SMTP(cfg["MAIL_SERVER"], cfg["MAIL_PORT"], timeout=10) as smtp:
        smtp.starttls()
        smtp.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
        smtp.send_message(msg)
