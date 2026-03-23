"""
test_admin.py — Tests for Admin / Data Inspection endpoints.

Spec:
  - GET /admin/users, /admin/carts, /admin/orders, /admin/products,
    /admin/coupons, /admin/tickets, /admin/addresses
  - All require X-Roll-Number. Admin endpoints do NOT require X-User-ID.
  - /admin/users/{user_id} returns one specific user.
"""

import requests
import pytest

BASE_URL = "http://localhost:8080/api/v1"


class TestAdminEndpoints:
    ENDPOINTS = [
        "users", "carts", "orders", "products", "coupons", "tickets", "addresses"
    ]

    def test_all_admin_endpoints_return_200(self, admin_headers):
        """Justification: All admin endpoints must be reachable with only X-Roll-Number."""
        for ep in self.ENDPOINTS:
            r = requests.get(f"{BASE_URL}/admin/{ep}", headers=admin_headers)
            assert r.status_code == 200, \
                f"Admin endpoint /admin/{ep} returned {r.status_code}: {r.text}"

    def test_admin_endpoints_require_roll_number(self):
        """Justification: All admin endpoints must reject requests missing X-Roll-Number → 401."""
        for ep in self.ENDPOINTS:
            r = requests.get(f"{BASE_URL}/admin/{ep}")
            assert r.status_code == 401, \
                f"/admin/{ep} returned {r.status_code} instead of 401 when header missing"

    def test_admin_users_returns_list(self, admin_headers):
        """Justification: /admin/users must return all users including wallet balance and loyalty points."""
        r = requests.get(f"{BASE_URL}/admin/users", headers=admin_headers)
        data = r.json()
        users = data if isinstance(data, list) else data.get("users", [])
        assert isinstance(users, list), f"Expected list of users, got {type(users)}"
        assert len(users) > 0, "No users found — server DB appears empty"

    def test_admin_get_specific_user(self, admin_headers, first_user_id):
        """Justification: /admin/users/{user_id} must return exactly the specified user."""
        r = requests.get(f"{BASE_URL}/admin/users/{first_user_id}", headers=admin_headers)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        # Response should include the user_id matching what was requested
        uid = data.get("user_id")
        assert uid == first_user_id, f"Expected user_id={first_user_id}, got {uid}"

    def test_admin_get_nonexistent_user_returns_404(self, admin_headers):
        """Justification: A non-existent user_id must return 404 from the admin endpoint."""
        r = requests.get(f"{BASE_URL}/admin/users/999999", headers=admin_headers)
        assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"

    def test_admin_products_includes_inactive(self, admin_headers, uh):
        """Justification: Admin product list must include inactive products unlike the user-facing list."""
        r_admin = requests.get(f"{BASE_URL}/admin/products", headers=admin_headers)
        r_user = requests.get(f"{BASE_URL}/products", headers=uh)
        admin_count = len(r_admin.json() if isinstance(r_admin.json(), list) else r_admin.json().get("products", []))
        user_data = r_user.json()
        user_count = len(user_data if isinstance(user_data, list) else user_data.get("products", []))
        # Admin should see >= user products (includes inactive)
        assert admin_count >= user_count, \
            f"Admin sees {admin_count} products, user sees {user_count} — admin should see more or equal"
