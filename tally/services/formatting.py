from markupsafe import Markup

from .currency import category_icon, currency_name, format_amount  # noqa: F401


def team_badge(team):
    if team is None:
        return ""
    return Markup(f'<span class="team-badge">{team.name}</span>')
