"""Tests for personal expense tags. Run with: python -m unittest tests.test_tags"""

import re
import secrets
import unittest
from decimal import Decimal

from tally import create_app
from tally.extensions import db
from tally.models import Expense, Tag, User
from tally.tags.forms import TagFormError, clean_color, clean_name, parse_id_list


class TestConfig:
    TESTING = True
    SECRET_KEY = secrets.token_hex(16)
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    EXPENSE_CATEGORIES = ["travel", "meals", "other"]
    GOOGLE_CLIENT_ID = ""


class FormTests(unittest.TestCase):
    def test_clean_name(self):
        self.assertEqual(clean_name("  client:acme  "), "client:acme")
        self.assertEqual(clean_name("Q3   offsite"), "Q3 offsite")
        for bad in ("", "   ", "x" * 41, "<b>", "-leading"):
            with self.assertRaises(TagFormError):
                clean_name(bad)

    def test_clean_color_falls_back(self):
        self.assertEqual(clean_color("Blue"), "blue")
        self.assertEqual(clean_color("hotpink"), "slate")

    def test_parse_id_list(self):
        self.assertEqual(parse_id_list(["3", "x", "3", "-1", "7", "9"], 2), [3, 7])


class TagRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.alice = self._user("alice@example.com")
        self.bob = self._user("bob@example.com")
        self.alice_expense = self._expense(self.alice, "Taxi", "12.50")
        self.bob_expense = self._expense(self.bob, "Hotel", "220.00")
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _user(self, email):
        user = User(email=email, name=email.split("@")[0])
        user.set_password("correct horse battery")
        db.session.add(user)
        db.session.commit()
        return user

    def _expense(self, owner, description, amount):
        expense = Expense(owner_id=owner.id, description=description, amount=Decimal(amount))
        db.session.add(expense)
        db.session.commit()
        return expense

    def _login(self, email):
        self.client.post("/login", data={"email": email, "password": "correct horse battery"})

    def _token(self):
        page = self.client.get("/tags/").get_data(as_text=True)
        return re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)

    def test_requires_login(self):
        self.assertEqual(self.client.get("/tags/").status_code, 302)

    def test_post_without_token_is_rejected(self):
        self._login("alice@example.com")
        self.assertEqual(self.client.post("/tags/", data={"name": "trip"}).status_code, 400)
        self.assertEqual(db.session.query(Tag).count(), 0)

    def test_create_assign_and_view(self):
        self._login("alice@example.com")
        token = self._token()
        self.client.post("/tags/", data={"name": "trip", "color": "green", "csrf_token": token})
        tag = db.session.query(Tag).one()
        self.assertEqual((tag.owner_id, tag.color), (self.alice.id, "green"))

        resp = self.client.post(
            f"/tags/expense/{self.alice_expense.id}", data={"tag_id": [str(tag.id)], "csrf_token": token}
        )
        self.assertEqual(resp.status_code, 302)
        page = self.client.get(f"/tags/{tag.id}").get_data(as_text=True)
        self.assertIn("Taxi", page)
        self.assertIn("12.50 USD", page)

        summary = self.client.get("/tags/summary.json").get_json()
        self.assertEqual(summary[0]["expense_count"], 1)

    def test_duplicate_name_is_rejected(self):
        self._login("alice@example.com")
        token = self._token()
        self.client.post("/tags/", data={"name": "Trip", "csrf_token": token})
        self.client.post("/tags/", data={"name": "trip", "csrf_token": token})
        self.assertEqual(db.session.query(Tag).count(), 1)

    def test_other_users_records_are_not_reachable(self):
        bob_tag = Tag(owner_id=self.bob.id, name="secret-project")
        db.session.add(bob_tag)
        db.session.commit()
        self._login("alice@example.com")
        token = self._token()

        self.assertEqual(self.client.get(f"/tags/{bob_tag.id}").status_code, 404)
        self.assertEqual(self.client.get(f"/tags/{bob_tag.id}/edit").status_code, 404)
        self.assertEqual(self.client.post(f"/tags/{bob_tag.id}/delete", data={"csrf_token": token}).status_code, 404)
        self.assertEqual(self.client.get(f"/tags/expense/{self.bob_expense.id}").status_code, 404)

        # Someone else's tag id is ignored when tagging your own expense.
        self.client.post(
            f"/tags/expense/{self.alice_expense.id}", data={"tag_id": [str(bob_tag.id)], "csrf_token": token}
        )
        self.assertEqual(db.session.get(Expense, self.alice_expense.id).tags, [])

        # Bulk tagging only touches your own expenses.
        alice_tag = Tag(owner_id=self.alice.id, name="mine")
        db.session.add(alice_tag)
        db.session.commit()
        self.client.post(
            "/tags/bulk",
            data={
                "tag_id": str(alice_tag.id),
                "expense_id": [str(self.alice_expense.id), str(self.bob_expense.id)],
                "action": "add",
                "csrf_token": token,
            },
        )
        db.session.expire_all()
        self.assertEqual([t.name for t in db.session.get(Expense, self.alice_expense.id).tags], ["mine"])
        self.assertEqual(db.session.get(Expense, self.bob_expense.id).tags, [])

    def test_pages_render(self):
        tag = Tag(owner_id=self.alice.id, name="trip", color="amber", description="Berlin <offsite>")
        db.session.add(tag)
        db.session.commit()
        self._login("alice@example.com")
        for url in ("/tags/", f"/tags/{tag.id}?status=pending", f"/tags/{tag.id}/edit",
                    f"/tags/expense/{self.alice_expense.id}", "/tags/bulk"):
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, url)
            self.assertNotIn("<offsite>", resp.get_data(as_text=True))

    def test_delete_keeps_expenses(self):
        self._login("alice@example.com")
        token = self._token()
        self.client.post("/tags/", data={"name": "trip", "csrf_token": token})
        tag = db.session.query(Tag).one()
        self.client.post("/tags/bulk", data={"tag_id": str(tag.id), "expense_id": [str(self.alice_expense.id)], "csrf_token": token})
        self.client.post(f"/tags/{tag.id}/delete", data={"csrf_token": token})
        self.assertEqual(db.session.query(Tag).count(), 0)
        self.assertIsNotNone(db.session.get(Expense, self.alice_expense.id))


if __name__ == "__main__":
    unittest.main()
