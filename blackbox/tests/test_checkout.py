"""
test_checkout.py — Tests for POST /api/v1/checkout.

Spec (field name: "payment_method"):
  - Payment must be COD | WALLET | CARD. Others → 400.
  - Empty cart → 400.
  - COD when total > 5000 → 400.
  - COD/WALLET → payment status PENDING.
  - CARD → payment status PAID.
  - GST = 5%, added exactly once.
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


def _checkout(uh, payment_method):
    return requests.post(
        f"{BASE_URL}/checkout",
        json={"payment_method": payment_method},
        headers=uh,
    )


class TestCheckoutValidation:
    def test_checkout_empty_cart_returns_400(self, uh):
        """Justification: Checking out with an empty cart must be rejected → 400."""
        _clear(uh)
        r = _checkout(uh, "COD")
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_invalid_payment_method_returns_400(self, uh, first_product):
        """Justification: Only COD/WALLET/CARD are valid; any other string must return 400."""
        _clear(uh)
        stock = first_product.get("stock", 0)
        if stock < 1:
            pytest.skip("No stock")
        _add(uh, first_product["product_id"], 1)
        r = _checkout(uh, "BITCOIN")
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
        _clear(uh)

    def test_cod_above_5000_returns_400(self, uh, admin_headers):
        """Justification: COD is not allowed when total > 5000 → 400."""
        _clear(uh)
        # Find an expensive product or add many units
        r_admin = requests.get(f"{BASE_URL}/admin/products", headers=admin_headers)
        products = r_admin.json() if r_admin.status_code == 200 else []
        active = [p for p in products if p.get("is_active", True) and p.get("stock", 0) > 0]
        if not active:
            pytest.skip("No active products with stock")

        # Sort by price desc, pick most expensive
        active.sort(key=lambda p: float(p.get("price", 0)), reverse=True)
        product = active[0]
        price = float(product.get("price", 0))
        stock = product.get("stock", 100)

        # Calculate qty needed to exceed 5000 / 1.05 (before GST) ≈ 4762
        threshold = 4762
        qty = int(threshold / price) + 1 if price > 0 else 1
        qty = min(qty, stock)

        if price * qty <= 4762:
            pytest.skip("Cannot reach > 5000 total with available stock/prices")

        _add(uh, product["product_id"], qty)
        r = _checkout(uh, "COD")
        assert r.status_code == 400, f"Expected 400 for COD > 5000, got {r.status_code}: {r.text}"
        _clear(uh)


class TestCheckoutPaymentStatus:
    def test_card_payment_status_is_paid(self, uh, admin_headers, first_product):
        """Justification: CARD checkout must result in payment status PAID per spec."""
        _clear(uh)
        pid = first_product["product_id"]
        stock = first_product.get("stock", 0)
        if stock < 1:
            pytest.skip("No stock")

        # Ensure wallet has enough (or use CARD which doesn't need balance)
        _add(uh, pid, 1)
        r = _checkout(uh, "CARD")
        assert r.status_code == 200, f"Checkout failed: {r.status_code}: {r.text}"
        data = r.json()
        order = data.get("order", data)
        payment_status = order.get("payment_status", "")
        assert payment_status == "PAID", f"Expected PAID, got '{payment_status}'"

    def test_cod_payment_status_is_pending(self, uh, admin_headers, first_product):
        """Justification: COD checkout must result in payment status PENDING per spec."""
        _clear(uh)
        pid = first_product["product_id"]
        price = float(first_product.get("price", 0))
        stock = first_product.get("stock", 0)
        if stock < 1 or price <= 0:
            pytest.skip("No stock or price")

        # Make sure total <= 5000 for COD
        max_qty = min(stock, max(1, int(4762 / price)))
        _add(uh, pid, max_qty)

        cart = requests.get(f"{BASE_URL}/cart", headers=uh).json()
        total_with_gst = float(cart.get("total", 0)) * 1.05
        if total_with_gst > 5000:
            _clear(uh)
            pytest.skip("Cannot fit within COD 5000 limit")

        r = _checkout(uh, "COD")
        assert r.status_code == 200, f"COD checkout failed: {r.status_code}: {r.text}"
        data = r.json()
        order = data.get("order", data)
        payment_status = order.get("payment_status", "")
        assert payment_status == "PENDING", f"Expected PENDING, got '{payment_status}'"


class TestCheckoutGST:
    def test_gst_is_5_percent(self, uh, admin_headers, first_product):
        """Justification: GST must be exactly 5% and added only once per spec."""
        _clear(uh)
        pid = first_product["product_id"]
        price = float(first_product.get("price", 0))
        stock = first_product.get("stock", 0)
        if stock < 1 or price <= 0:
            pytest.skip("No stock or price")

        _add(uh, pid, 1)
        cart = requests.get(f"{BASE_URL}/cart", headers=uh).json()
        cart_total = float(cart.get("total", cart.get("cart_total", price)))

        r = _checkout(uh, "CARD")
        assert r.status_code == 200, f"Checkout failed: {r.status_code}: {r.text}"
        data = r.json()
        order = data.get("order", data)

        # Get invoice to check subtotal and total
        order_id = order.get("order_id")
        if order_id:
            inv = requests.get(f"{BASE_URL}/orders/{order_id}/invoice", headers=uh)
            if inv.status_code == 200:
                inv_data = inv.json()
                subtotal = float(inv_data.get("subtotal", cart_total))
                gst_amount = float(inv_data.get("gst", inv_data.get("gst_amount", 0)))
                total = float(inv_data.get("total", 0))
                expected_gst = round(subtotal * 0.05, 2)
                assert round(gst_amount, 2) == expected_gst, \
                    f"GST mismatch: expected {expected_gst}, got {gst_amount}"
                assert round(total, 2) == round(subtotal + gst_amount, 2), \
                    f"Total mismatch: {total} ≠ {subtotal} + {gst_amount}"
