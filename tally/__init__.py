from flask import Flask, redirect, url_for

from .extensions import db, login_manager


def create_app(config_object="tally.config.Config"):
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)
    login_manager.init_app(app)

    from . import api, auth, expenses, profile, receipts
    from .cli import register_commands
    from .reports.routes import bp as reports_bp
    from .services.formatting import format_amount, team_badge
    from .teams import bp as teams_bp

    app.register_blueprint(auth.bp)
    app.register_blueprint(expenses.bp)
    app.register_blueprint(teams_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(profile.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(receipts.bp)

    app.jinja_env.globals["team_badge"] = team_badge
    app.jinja_env.filters["money"] = format_amount

    register_commands(app)

    @app.get("/")
    def index():
        return redirect(url_for("expenses.index"))

    return app
