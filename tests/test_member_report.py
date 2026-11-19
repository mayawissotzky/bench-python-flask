from decimal import Decimal

from tally.reports.queries import with_shares


def test_shares_split_approved_spend():
    rows = [
        {"name": "Ana", "approved": Decimal("75.00"), "pending": Decimal("0")},
        {"name": "Ben", "approved": Decimal("25.00"), "pending": Decimal("10.00")},
    ]
    shares = [row["share"] for row in with_shares(rows)]
    assert shares == [Decimal("75.0"), Decimal("25.0")]


def test_shares_are_zero_without_approved_spend():
    rows = [{"name": "Ana", "approved": Decimal("0"), "pending": Decimal("40.00")}]
    assert with_shares(rows)[0]["share"] == Decimal("0")


def test_rows_keep_their_fields():
    rows = [{"user_id": 3, "name": "Ana", "approved": Decimal("12.50"), "pending": Decimal("0")}]
    result = with_shares(rows)[0]
    assert result["user_id"] == 3
    assert result["name"] == "Ana"
    assert result["share"] == Decimal("100.0")
