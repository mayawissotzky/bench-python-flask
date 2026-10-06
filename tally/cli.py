from datetime import date, timedelta
from decimal import Decimal

import click

from .extensions import db
from .models import Expense, Team, User


def register_commands(app):
    @app.cli.command("init-db")
    def init_db():
        """Create all tables."""
        db.create_all()
        click.echo("Database initialised.")

    @app.cli.command("seed")
    def seed():
        """Load a demo team with a few expenses."""
        team = Team(name="Design Studio", description="Product design team")
        db.session.add(team)
        db.session.flush()

        manager = User(email="dana@example.com", name="Dana Levi", role="manager", team_id=team.id)
        manager.set_password("demo-password")
        member = User(email="omer@example.com", name="Omer Katz", team_id=team.id)
        member.set_password("demo-password")
        db.session.add_all([manager, member])
        db.session.flush()

        today = date.today()
        samples = [
            ("Train to client workshop", "travel", "48.20"),
            ("Team lunch", "meals", "126.00"),
            ("Figma seats (quarterly)", "software", "540.00"),
            ("USB-C dock", "hardware", "189.99"),
        ]
        for offset, (desc, cat, amount) in enumerate(samples):
            db.session.add(
                Expense(
                    owner_id=member.id if offset % 2 else manager.id,
                    team_id=team.id,
                    description=desc,
                    category=cat,
                    amount=Decimal(amount),
                    spent_on=today - timedelta(days=offset * 3),
                )
            )
        db.session.commit()
        click.echo("Seeded demo data.")
