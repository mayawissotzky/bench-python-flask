from markupsafe import Markup


def format_amount(amount, currency="USD"):
    return f"{currency} {amount:,.2f}"


def team_badge(team):
    if team is None:
        return ""
    return Markup(f'<span class="team-badge">{team.name}</span>')


def format_count(n, noun):
    return f"{n:,} {noun if n == 1 else noun + 's'}"
