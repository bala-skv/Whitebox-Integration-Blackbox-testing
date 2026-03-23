"""
test_reviews.py — Tests for product reviews.

Spec:
  - Rating: 1–5 (outside → 400).
  - Comment: 1–200 characters.
  - Average rating must be a decimal calculation (not floored integer).
  - No reviews → average = 0.
"""

import requests
import pytest

BASE_URL = "http://localhost:8080/api/v1"


def _post_review(uh, product_id, rating, comment="Good product"):
    return requests.post(
        f"{BASE_URL}/products/{product_id}/reviews",
        json={"rating": rating, "comment": comment},
        headers=uh,
    )


class TestReviewValidation:
    def test_rating_zero_returns_400(self, uh, first_product):
        """Justification: Rating 0 is below minimum (1) → 400."""
        r = _post_review(uh, first_product["product_id"], 0)
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_rating_six_returns_400(self, uh, first_product):
        """Justification: Rating 6 is above maximum (5) → 400."""
        r = _post_review(uh, first_product["product_id"], 6)
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_rating_negative_returns_400(self, uh, first_product):
        """Justification: Negative rating is clearly out of range → 400."""
        r = _post_review(uh, first_product["product_id"], -1)
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_rating_1_accepted(self, uh, first_product):
        """Justification: Boundary value — 1 is the minimum valid rating."""
        r = _post_review(uh, first_product["product_id"], 1)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    def test_rating_5_accepted(self, uh, first_product):
        """Justification: Boundary value — 5 is the maximum valid rating."""
        r = _post_review(uh, first_product["product_id"], 5)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    def test_comment_empty_returns_400(self, uh, first_product):
        """Justification: Comment must be ≥ 1 character → empty string invalid."""
        r = _post_review(uh, first_product["product_id"], 3, comment="")
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_comment_too_long_returns_400(self, uh, first_product):
        """Justification: Comment > 200 chars violates spec → 400."""
        r = _post_review(uh, first_product["product_id"], 3, comment="A" * 201)
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_comment_exactly_200_chars_accepted(self, uh, first_product):
        """Justification: Boundary value — 200 chars is maximum allowed."""
        r = _post_review(uh, first_product["product_id"], 3, comment="A" * 200)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"


class TestReviewAverage:
    def test_average_rating_is_decimal_not_floor(self, uh, first_product, second_user_id):
        """
        Justification: Average must be a proper decimal (e.g. 3.5), not an integer (floor 3).
        If server returns int when the true average is a fraction, it's a bug.
        """
        pid = first_product["product_id"]

        # Post two reviews with different ratings from two users
        uh2 = {"X-Roll-Number": "2025121002", "X-User-ID": str(second_user_id)}
        _post_review(uh, pid, 4)
        _post_review(uh2, pid, 3)

        r = requests.get(f"{BASE_URL}/products/{pid}/reviews", headers=uh)
        assert r.status_code == 200
        data = r.json()
        avg = data.get("average_rating", data.get("avg_rating", data.get("average", None)))
        if avg is None:
            pytest.skip("No average_rating field returned")

        # Average of 4 and 3 is 3.5 — verify it's not floor-divided to 3
        # We check the type: returning an int like 3 would be wrong
        reviews = data.get("reviews", [])
        if len(reviews) >= 2:
            computed_ratings = [float(rev.get("rating", 0)) for rev in reviews]
            true_avg = sum(computed_ratings) / len(computed_ratings)
            assert round(float(avg), 2) == round(true_avg, 2), \
                f"Average rating: expected {true_avg:.2f}, got {avg}"

    def test_no_reviews_average_is_zero(self, uh, admin_headers):
        """Justification: A product with no reviews must show average rating of 0."""
        r_admin = requests.get(f"{BASE_URL}/admin/products", headers=admin_headers)
        products = r_admin.json() if r_admin.status_code == 200 else []

        # Find a product with no reviews
        no_review_pid = None
        for p in products:
            if not p.get("is_active", True):
                continue
            r_rev = requests.get(f"{BASE_URL}/products/{p['product_id']}/reviews", headers=uh)
            if r_rev.status_code == 200:
                rev_data = r_rev.json()
                reviews = rev_data.get("reviews", [])
                if len(reviews) == 0:
                    no_review_pid = p["product_id"]
                    avg = rev_data.get("average_rating", rev_data.get("avg_rating", -1))
                    assert float(avg) == 0, f"Expected avg=0 for product with no reviews, got {avg}"
                    break

        if no_review_pid is None:
            pytest.skip("All products have at least one review")
