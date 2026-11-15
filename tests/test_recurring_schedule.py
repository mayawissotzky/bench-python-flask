"""Unit tests for the recurring schedule date maths and form validation.

Run with: python -m unittest discover tests
"""

import unittest
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from tally.services.recurring import monthly_equivalent, occurrence, parse_form, upcoming

CATEGORIES = ["travel", "software", "office", "other"]


def _form(**overrides):
    values = {
        "description": "Design tool seats",
        "category": "software",
        "amount": "45.50",
        "currency": "usd",
        "frequency": "monthly",
        "start_date": "2026-01-31",
        "end_date": "",
        "notes": "",
    }
    values.update(overrides)
    return values


class OccurrenceTests(unittest.TestCase):
    def test_monthly_clamps_to_month_end_without_drifting(self):
        start = date(2026, 1, 31)
        self.assertEqual(occurrence(start, "monthly", 1), date(2026, 2, 28))
        self.assertEqual(occurrence(start, "monthly", 2), date(2026, 3, 31))
        self.assertEqual(occurrence(start, "monthly", 3), date(2026, 4, 30))

    def test_leap_years(self):
        self.assertEqual(occurrence(date(2028, 2, 29), "yearly", 1), date(2029, 2, 28))
        self.assertEqual(occurrence(date(2028, 2, 29), "yearly", 4), date(2032, 2, 29))
        self.assertEqual(occurrence(date(2027, 11, 30), "quarterly", 1), date(2028, 2, 29))

    def test_weekly_and_year_rollover(self):
        self.assertEqual(occurrence(date(2026, 12, 28), "weekly", 1), date(2027, 1, 4))
        self.assertEqual(occurrence(date(2026, 11, 15), "monthly", 2), date(2027, 1, 15))

    def test_rejects_unknown_frequency_and_negative_index(self):
        with self.assertRaises(ValueError):
            occurrence(date(2026, 1, 1), "daily", 1)
        with self.assertRaises(ValueError):
            occurrence(date(2026, 1, 1), "monthly", -1)

    def test_upcoming_stops_at_end_date(self):
        schedule = SimpleNamespace(
            start_date=date(2026, 1, 1), frequency="monthly", occurrences=1, end_date=date(2026, 4, 1)
        )
        self.assertEqual(upcoming(schedule), [date(2026, 2, 1), date(2026, 3, 1), date(2026, 4, 1)])

    def test_monthly_equivalent(self):
        weekly = SimpleNamespace(frequency="weekly", amount=Decimal("12.00"))
        yearly = SimpleNamespace(frequency="yearly", amount=Decimal("120.00"))
        self.assertEqual(monthly_equivalent(weekly), Decimal("52.00"))
        self.assertEqual(monthly_equivalent(yearly), Decimal("10.00"))


class ParseFormTests(unittest.TestCase):
    def test_valid_form(self):
        data = parse_form(_form(), CATEGORIES)
        self.assertTrue(data.ok, data.errors)
        self.assertEqual(data.amount, Decimal("45.50"))
        self.assertEqual(data.currency, "USD")
        self.assertEqual(data.start_date, date(2026, 1, 31))
        self.assertIsNone(data.end_date)

    def test_rejects_bad_values(self):
        cases = [
            {"description": "  "},
            {"category": "yachts"},
            {"amount": "abc"},
            {"amount": "-5"},
            {"amount": "NaN"},
            {"amount": "2000000"},
            {"currency": "US"},
            {"currency": "U$D"},
            {"frequency": "hourly"},
            {"start_date": ""},
            {"start_date": "31/01/2026"},
            {"end_date": "2025-12-31"},
            {"notes": "x" * 2001},
        ]
        for overrides in cases:
            with self.subTest(overrides=overrides):
                self.assertFalse(parse_form(_form(**overrides), CATEGORIES).ok)


if __name__ == "__main__":
    unittest.main()
