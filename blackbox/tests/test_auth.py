"""
test_auth.py — Tests for X-Roll-Number and X-User-ID header validation.

Spec (QuickCart System.md):
  - Every request must include X-Roll-Number (valid integer) → else 401 / 400.
  - User-scoped endpoints also require X-User-ID (positive int of existing user) → else 400.
"""

import requests
import pytest

BASE_URL = "http://localhost:8080/api/v1"
ROLL_NUMBER = "2025121002"


class TestRollNumberHeader:
    """X-Roll-Number must be present and a valid integer."""

    def test_missing_roll_number_returns_401(self):
        """Justification: Missing X-Roll-Number should always be rejected with 401."""
        r = requests.get(f"{BASE_URL}/admin/users")
        assert r.status_code == 401, f"Expected 401, got {r.status_code}: {r.text}"

    def test_non_integer_roll_number_returns_400(self):
        """Justification: X-Roll-Number must be parsable as an integer; letters must fail with 400."""
        r = requests.get(f"{BASE_URL}/admin/users", headers={"X-Roll-Number": "abc"})
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_symbolic_roll_number_returns_400(self):
        """Justification: Symbols are not valid integers; expect 400."""
        r = requests.get(f"{BASE_URL}/admin/users", headers={"X-Roll-Number": "!@#"})
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_valid_roll_number_accepted(self):
        """Justification: A correct roll number must be accepted (not 401/400)."""
        r = requests.get(f"{BASE_URL}/admin/users", headers={"X-Roll-Number": ROLL_NUMBER})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"


class TestUserIDHeader:
    """User-scoped endpoints require a valid X-User-ID."""

    def test_missing_user_id_returns_400(self):
        """Justification: X-User-ID is mandatory for user-scoped endpoints; absence should return 400."""
        r = requests.get(f"{BASE_URL}/profile", headers={"X-Roll-Number": ROLL_NUMBER})
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_zero_user_id_returns_400(self):
        """Justification: X-User-ID must be a positive integer; 0 is invalid → 400."""
        r = requests.get(
            f"{BASE_URL}/profile",
            headers={"X-Roll-Number": ROLL_NUMBER, "X-User-ID": "0"},
        )
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_nonexistent_user_id_returns_400(self):
        """Justification: A user_id that does not match any DB user must be rejected → 400."""
        r = requests.get(
            f"{BASE_URL}/profile",
            headers={"X-Roll-Number": ROLL_NUMBER, "X-User-ID": "999999"},
        )
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_string_user_id_returns_400(self):
        """Justification: Non-integer user IDs are invalid format → 400."""
        r = requests.get(
            f"{BASE_URL}/profile",
            headers={"X-Roll-Number": ROLL_NUMBER, "X-User-ID": "abc"},
        )
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_admin_endpoint_does_not_require_user_id(self):
        """Justification: Admin endpoints must NOT require X-User-ID per spec."""
        r = requests.get(f"{BASE_URL}/admin/users", headers={"X-Roll-Number": ROLL_NUMBER})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
