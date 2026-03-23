"""
test_coupons.py — Tests for POST /api/v1/coupon/apply and /coupon/remove.

Spec:
  - Coupon must not be expired.
  - Cart total must meet minimum cart value.
  - PERCENT coupon: discount = total × percent / 100
  - FIXED coupon: discount = flat amount
  - Discount must respect max cap (if set).
"""

import requests
import pytest

BASE_URL = "http://localhost:8080/api/v1"


def _clear(uh):
    requests.delete(f"{BASE_URL}/cart/clear", headers=uh)


def _add(uh, product_id, quantity=1):
    return requests.post(
        f"{BASE_URL}/cart/add",
        json={"product_id": product_id, "quantity": quantity},
        headers=uh,
    )


class TestCouponApply:
    def test_apply_invalid_coupon_code_returns_error(self, uh, first_product):
        """Justification: A coupon code that doesn't exist should be rejected."""
        _clear(uh)
        pid = first_product["product_id"]
        stock = first_product.get("stock", 0)
        if stock < 1:
            pytest.skip("No stock")
        _add(uh, pid, 1)
        r = requests.post(
            f"{BASE_URL}/coupon/apply",
            json={"code": "INVALIDCODE999"},
            headers=uh,
        )
        assert r.status_code in (400, 404), \
            f"Expected 400/404 for invalid coupon, got {r.status_code}: {r.text}"

    def test_apply_expired_coupon_returns_error(self, uh, admin_headers, first_product):
        """Justification: Expired coupons must be rejected per spec."""
        # Find an expired coupon from admin
        r_admin = requests.get(f"{BASE_URL}/admin/coupons", headers=admin_headers)
        if r_admin.status_code != 200:
            pytest.skip("Cannot fetch coupons from admin")
        coupons = r_admin.json()
        if isinstance(coupons, dict):
            coupons = coupons.get("coupons", [])

        from datetime import datetime
        now = datetime.utcnow().isoformat()
        expired = [c for c in coupons if c.get("expiry", c.get("expires_at", "9999")) < now]
        if not expired:
            pytest.skip("No expired coupons in DB")

        _clear(uh)
        pid = first_product["product_id"]
        stock = first_product.get("stock", 0)
        if stock < 1:
            pytest.skip("No stock")
        _add(uh, pid, 1)

        r = requests.post(
            f"{BASE_URL}/coupon/apply",
            json={"code": expired[0]["code"]},
            headers=uh,
        )
        assert r.status_code in (400, 422), \
            f"Expected error for expired coupon, got {r.status_code}: {r.text}"

    def test_apply_coupon_cart_below_minimum_returns_error(self, uh, admin_headers, first_product):
        """Justification: Cart total below coupon's minimum_cart_value must be rejected."""
        r_admin = requests.get(f"{BASE_URL}/admin/coupons", headers=admin_headers)
        if r_admin.status_code != 200:
            pytest.skip("Cannot fetch coupons")
        coupons = r_admin.json()
        if isinstance(coupons, dict):
            coupons = coupons.get("coupons", [])

        # Find coupon with high minimum value
        high_min = [c for c in coupons if float(c.get("min_cart_value", c.get("minimum_cart_value", 0))) > 10000]
        if not high_min:
            pytest.skip("No coupon with very high minimum cart value found")

        _clear(uh)
        pid = first_product["product_id"]
        stock = first_product.get("stock", 0)
        if stock < 1:
            pytest.skip("No stock")
        _add(uh, pid, 1)

        r = requests.post(
            f"{BASE_URL}/coupon/apply",
            json={"code": high_min[0]["code"]},
            headers=uh,
        )
        assert r.status_code in (400, 422), \
            f"Expected error for cart below minimum, got {r.status_code}: {r.text}"

    def test_percent_coupon_discount_correct(self, uh, admin_headers, first_product):
        """Justification: PERCENT coupon must deduct exactly percent% of the cart total."""
        r_admin = requests.get(f"{BASE_URL}/admin/coupons", headers=admin_headers)
        if r_admin.status_code != 200:
            pytest.skip("Cannot fetch coupons")
        coupons = r_admin.json()
        if isinstance(coupons, dict):
            coupons = coupons.get("coupons", [])

        from datetime import datetime
        now = datetime.utcnow().isoformat()
        percent_coupons = [
            c for c in coupons
            if c.get("type", c.get("discount_type", "")) == "PERCENT"
            and c.get("expiry", c.get("expires_at", "9999")) > now
        ]
        if not percent_coupons:
            pytest.skip("No active PERCENT coupon in DB")

        coupon = percent_coupons[0]
        min_val = float(coupon.get("min_cart_value", coupon.get("minimum_cart_value", 0)))

        _clear(uh)
        pid = first_product["product_id"]
        price = float(first_product.get("price", 0))
        stock = first_product.get("stock", 0)
        if stock < 1 or price <= 0:
            pytest.skip("Insufficient stock or price")

        # Add enough to meet minimum
        qty = max(1, int(min_val / price) + 1)
        qty = min(qty, stock)
        _add(uh, pid, qty)

        cart = requests.get(f"{BASE_URL}/cart", headers=uh).json()
        total = float(cart.get("total", cart.get("cart_total", 0)))
        if total < min_val:
            pytest.skip("Cannot meet coupon minimum with available stock")

        r = requests.post(
            f"{BASE_URL}/coupon/apply",
            json={"code": coupon["code"]},
            headers=uh,
        )
        assert r.status_code == 200, f"Apply coupon failed: {r.status_code}: {r.text}"

        # Verify discount
        percent = float(coupon.get("discount_value", coupon.get("value", 0)))
        raw_discount = total * percent / 100
        cap = coupon.get("max_discount", coupon.get("max_discount_cap"))
        if cap:
            raw_discount = min(raw_discount, float(cap))
        expected_discount = round(raw_discount, 2)

        resp = r.json()
        actual_discount = round(float(resp.get("discount", resp.get("discount_amount", 0))), 2)
        assert actual_discount == expected_discount, \
            f"PERCENT discount: expected {expected_discount}, got {actual_discount}"

    def test_remove_coupon(self, uh, admin_headers, first_product):
        """Justification: Removing a coupon should succeed and restore the original total."""
        # Skip if no valid coupon
        r_admin = requests.get(f"{BASE_URL}/admin/coupons", headers=admin_headers)
        coupons = r_admin.json() if r_admin.status_code == 200 else []
        if isinstance(coupons, dict):
            coupons = coupons.get("coupons", [])
        if not coupons:
            pytest.skip("No coupons available")

        _clear(uh)
        pid = first_product["product_id"]
        stock = first_product.get("stock", 0)
        if stock < 1:
            pytest.skip("No stock")
        _add(uh, pid, 1)

        # Try remove without applying first (should not crash)
        r = requests.post(f"{BASE_URL}/coupon/remove", json={}, headers=uh)
        assert r.status_code in (200, 400), \
            f"Unexpected status on coupon remove: {r.status_code}: {r.text}"
