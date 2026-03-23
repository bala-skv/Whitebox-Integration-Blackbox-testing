"""
test_loyalty.py — Tests for GET /api/v1/loyalty and POST /api/v1/loyalty/redeem.

Spec:
  - Redeem amount must be ≥ 1.
  - User must have enough points to redeem.
"""

import requests
import pytest

BASE_URL = "http://localhost:8080/api/v1"


class TestLoyalty:
    def test_get_loyalty_returns_200(self, uh):
        """Justification: Valid user must be able to view their loyalty points."""
        r = requests.get(f"{BASE_URL}/loyalty", headers=uh)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    def test_get_loyalty_returns_points_field(self, uh):
        """Justification: Response must contain the loyalty points value."""
        r = requests.get(f"{BASE_URL}/loyalty", headers=uh)
        data = r.json()
        has_points = "points" in data or "loyalty_points" in data
        assert has_points, f"Points field missing in response: {data}"

    def test_redeem_zero_returns_error(self, uh):
        """Justification: Minimum redemption is 1 point → 0 must be rejected."""
        r = requests.post(f"{BASE_URL}/loyalty/redeem", json={"points": 0}, headers=uh)
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_redeem_negative_returns_error(self, uh):
        """Justification: Negative redemption amount is invalid → must be rejected."""
        r = requests.post(f"{BASE_URL}/loyalty/redeem", json={"points": -10}, headers=uh)
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_redeem_more_than_balance_returns_error(self, uh):
        """Justification: Redeeming more points than the user has must be rejected."""
        r_bal = requests.get(f"{BASE_URL}/loyalty", headers=uh)
        data = r_bal.json()
        current = int(data.get("points", data.get("loyalty_points", 0)))
        r = requests.post(
            f"{BASE_URL}/loyalty/redeem",
            json={"points": current + 99999},
            headers=uh,
        )
        assert r.status_code == 400, f"Expected 400 for insufficient points, got {r.status_code}: {r.text}"
