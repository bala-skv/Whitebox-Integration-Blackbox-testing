"""
conftest.py — Shared fixtures for QuickCart black-box tests.

Headers required by every request:
  X-Roll-Number : 2025121002   (must be a valid integer)
  X-User-ID     : <positive int matching an existing user>

The server is assumed to be running at http://localhost:8080 before the
test-suite is executed:

    docker run -p 8080:8080 quickcart
"""

import pytest
import requests

BASE_URL = "http://localhost:8080/api/v1"
ROLL_NUMBER = "2025121002"

# ── helpers ──────────────────────────────────────────────────────────────────

def base_headers():
    """Headers needed by every request (no user scope)."""
    return {"X-Roll-Number": ROLL_NUMBER}


def user_headers(user_id: int):
    """Headers needed by user-scoped requests."""
    return {"X-Roll-Number": ROLL_NUMBER, "X-User-ID": str(user_id)}


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def admin_headers():
    return base_headers()


@pytest.fixture(scope="session")
def first_user_id(admin_headers):
    """Return the ID of the first user in the system (for reuse)."""
    r = requests.get(f"{BASE_URL}/admin/users", headers=admin_headers)
    assert r.status_code == 200, f"Could not list users: {r.text}"
    users = r.json()
    assert len(users) > 0, "No users found in DB – cannot run user-scoped tests."
    return users[0]["user_id"]


@pytest.fixture(scope="session")
def uh(first_user_id):
    """Shorthand: user-scoped headers for the first user."""
    return user_headers(first_user_id)


@pytest.fixture(scope="session")
def second_user_id(admin_headers):
    """Return the ID of the second user (for isolation in some tests)."""
    r = requests.get(f"{BASE_URL}/admin/users", headers=admin_headers)
    users = r.json()
    if len(users) > 1:
        return users[1]["user_id"]
    return users[0]["user_id"]


@pytest.fixture(scope="session")
def first_product(admin_headers):
    """Return the first active product (for cart / review tests)."""
    r = requests.get(f"{BASE_URL}/admin/products", headers=admin_headers)
    assert r.status_code == 200
    products = r.json()
    active = [p for p in products if p.get("is_active", True)]
    assert active, "No active products found."
    return active[0]


@pytest.fixture(autouse=False)
def clear_cart(uh):
    """Clear the cart before (and after) a test that needs a fresh cart."""
    requests.delete(f"{BASE_URL}/cart/clear", headers=uh)
    yield
    requests.delete(f"{BASE_URL}/cart/clear", headers=uh)
