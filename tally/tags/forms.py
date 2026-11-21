"""Validation for tag forms. Pure functions so they are easy to test."""

import re

TAG_COLORS = ("slate", "blue", "green", "amber", "red", "purple")
NAME_MAX = 40
DESCRIPTION_MAX = 200

# Letters, digits, spaces and a few separators people use in labels
# ("Q3 offsite", "client:acme", "billable-2026").
_NAME_RE = re.compile(r"^[\w][\w .:/&+-]*$")
_SPACES_RE = re.compile(r"\s+")


class TagFormError(ValueError):
    pass


def clean_name(raw):
    name = _SPACES_RE.sub(" ", (raw or "").strip())
    if not name:
        raise TagFormError("Tag name is required.")
    if len(name) > NAME_MAX:
        raise TagFormError(f"Tag names can be at most {NAME_MAX} characters.")
    if not _NAME_RE.match(name):
        raise TagFormError("Tag names may contain letters, digits, spaces and . : / & + - only.")
    return name


def clean_color(raw):
    color = (raw or "").strip().lower()
    return color if color in TAG_COLORS else TAG_COLORS[0]


def clean_description(raw):
    return (raw or "").strip()[:DESCRIPTION_MAX]


def parse_tag_form(form):
    """Return a dict of cleaned tag fields or raise TagFormError."""
    return {
        "name": clean_name(form.get("name")),
        "color": clean_color(form.get("color")),
        "description": clean_description(form.get("description")),
    }


def parse_id_list(values, limit):
    """Turn a list of form values into unique positive ints, ignoring junk."""
    ids = []
    for value in values:
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if number > 0 and number not in ids:
            ids.append(number)
        if len(ids) >= limit:
            break
    return ids
