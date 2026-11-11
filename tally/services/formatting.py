import re

from markupsafe import Markup

_URL = re.compile(r"(https?://[^\s<]+)")


def format_amount(amount, currency="USD"):
    return f"{currency} {amount:,.2f}"


def team_badge(team):
    if team is None:
        return ""
    return Markup(f'<span class="team-badge">{team.name}</span>')


def render_comment(body):
    """Comment body as HTML: links become clickable and line breaks are kept."""
    html = _URL.sub(r'<a href="\1" rel="nofollow noopener" target="_blank">\1</a>', body)
    return Markup(html.replace("\n", "<br>"))
