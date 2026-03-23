"""
test_profile.py — Tests for GET /api/v1/profile and PUT /api/v1/profile.

Spec:
  - Name must be 2–50 characters.
  - Phone must be exactly 10 digits.
  - Invalid values → 400.
"""

import requests
import pytest

BASE_URL = "http://localhost:8080/api/v1"


class TestGetProfile:
    def test_get_profile_returns_200(self, uh):
        """Justification: Valid user must be able to retrieve their profile."""
        r = requests.get(f"{BASE_URL}/profile", headers=uh)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    def test_get_profile_returns_json(self, uh):
        """Justification: Profile response must be JSON with user fields."""
        r = requests.get(f"{BASE_URL}/profile", headers=uh)
        data = r.json()
        assert "user_id" in data or "name" in data, f"Unexpected response: {data}"


class TestUpdateProfile:
    def test_valid_name_and_phone(self, uh):
        """Justification: Valid 2–50 char name and 10-digit phone must succeed."""
        r = requests.put(
            f"{BASE_URL}/profile",
            json={"name": "Test User", "phone": "9876543210"},
            headers=uh,
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    def test_name_too_short_returns_400(self, uh):
        """Justification: Name < 2 chars violates spec → 400."""
        r = requests.put(
            f"{BASE_URL}/profile",
            json={"name": "A", "phone": "9876543210"},
            headers=uh,
        )
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_name_too_long_returns_400(self, uh):
        """Justification: Name > 50 chars violates spec → 400."""
        long_name = "A" * 51
        r = requests.put(
            f"{BASE_URL}/profile",
            json={"name": long_name, "phone": "9876543210"},
            headers=uh,
        )
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_name_exactly_2_chars_accepted(self, uh):
        """Justification: Boundary value — 2 chars is the minimum allowed."""
        r = requests.put(
            f"{BASE_URL}/profile",
            json={"name": "AB", "phone": "9876543210"},
            headers=uh,
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    def test_name_exactly_50_chars_accepted(self, uh):
        """Justification: Boundary value — 50 chars is the maximum allowed."""
        r = requests.put(
            f"{BASE_URL}/profile",
            json={"name": "A" * 50, "phone": "9876543210"},
            headers=uh,
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    def test_phone_less_than_10_digits_returns_400(self, uh):
        """Justification: Phone must be exactly 10 digits → 9 digits invalid."""
        r = requests.put(
            f"{BASE_URL}/profile",
            json={"name": "Test User", "phone": "123456789"},
            headers=uh,
        )
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_phone_more_than_10_digits_returns_400(self, uh):
        """Justification: Phone must be exactly 10 digits → 11 digits invalid."""
        r = requests.put(
            f"{BASE_URL}/profile",
            json={"name": "Test User", "phone": "12345678901"},
            headers=uh,
        )
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_phone_with_letters_returns_400(self, uh):
        """Justification: Phone must be digits only → alphabetic chars invalid."""
        r = requests.put(
            f"{BASE_URL}/profile",
            json={"name": "Test User", "phone": "98765abcde"},
            headers=uh,
        )
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_phone_exactly_10_digits_accepted(self, uh):
        """Justification: Boundary value — 10 digits is exactly the required length."""
        r = requests.put(
            f"{BASE_URL}/profile",
            json={"name": "Test User", "phone": "1234567890"},
            headers=uh,
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
