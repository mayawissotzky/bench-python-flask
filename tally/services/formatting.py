from markupsafe import Markup


def format_amount(amount, currency="USD"):
    return f"{currency} {amount:,.2f}"


def team_badge(team):
    if team is None:
        return ""
    return Markup(f'<span class="team-badge">{team.name}</span>')


def format_percent(value: float, digits: int = 1) -> str:
    """Render a 0-1 ratio as a percentage string, e.g. 0.257 -> '25.7%'."""
    return f"{value * 100:.{digits}f}%"
