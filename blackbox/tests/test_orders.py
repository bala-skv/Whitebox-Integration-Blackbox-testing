"""
test_orders.py — Tests for order listing, detail, cancellation, and invoice.

Spec:
  - Delivered order cannot be cancelled → 400.
  - Non-existent order cancel → 404.
  - Order cancellation restores stock.
  - Invoice: subtotal + GST = total. Total must match actual order total.
"""

import requests
import pytest

BASE_URL = "http://localhost:8080/api/v1"


def _checkout_card(uh, pid, qty=1):
    """Helper: clear cart, add product, checkout with CARD. Returns response."""
    requests.delete(f"{BASE_URL}/cart/clear", headers=uh)
    requests.post(f"{BASE_URL}/cart/add", json={"product_id": pid, "quantity": qty}, headers=uh)
    return requests.post(f"{BASE_URL}/checkout", json={"payment_method": "CARD"}, headers=uh)


class TestOrdersList:
    def test_get_orders_returns_200(self, uh):
        """Justification: A valid user must be able to list their orders."""
        r = requests.get(f"{BASE_URL}/orders", headers=uh)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    def test_get_orders_returns_list(self, uh):
        """Justification: Response must be a JSON array (or dict with list)."""
        r = requests.get(f"{BASE_URL}/orders", headers=uh)
        data = r.json()
        orders = data if isinstance(data, list) else data.get("orders", [])
        assert isinstance(orders, list), f"Expected list, got: {type(orders)}"


class TestOrderDetail:
    def test_get_nonexistent_order_returns_404(self, uh):
        """Justification: order_id that doesn't exist must return 404."""
        r = requests.get(f"{BASE_URL}/orders/999999", headers=uh)
        assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"


class TestOrderCancel:
    def test_cancel_nonexistent_order_returns_404(self, uh):
        """Justification: Trying to cancel a non-existent order → 404."""
        r = requests.post(f"{BASE_URL}/orders/999999/cancel", headers=uh)
        assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"

    def test_cancel_delivered_order_returns_400(self, uh, admin_headers):
        """Justification: Delivered orders cannot be cancelled per spec → 400."""
        r_orders = requests.get(f"{BASE_URL}/admin/orders", headers=admin_headers)
        if r_orders.status_code != 200:
            pytest.skip("Cannot fetch orders from admin")
        all_orders = r_orders.json()
        if isinstance(all_orders, dict):
            all_orders = all_orders.get("orders", [])

        delivered = [o for o in all_orders if o.get("order_status") == "DELIVERED"]
        if not delivered:
            pytest.skip("No delivered orders in DB to test cancellation rejection")

        order_id = delivered[0].get("order_id")
        r = requests.post(f"{BASE_URL}/orders/{order_id}/cancel", headers=uh)
        assert r.status_code == 400, f"Expected 400 for delivered order, got {r.status_code}: {r.text}"

    def test_cancel_order_restores_stock(self, uh, first_product, admin_headers):
        """Justification: Cancelling an order must add all its items back to product stock."""
        pid = first_product["product_id"]
        stock_before = first_product.get("stock", 0)
        if stock_before < 1:
            pytest.skip("No stock to place order")

        r_checkout = _checkout_card(uh, pid, 1)
        if r_checkout.status_code != 200:
            pytest.skip(f"Checkout failed: {r_checkout.text}")

        data = r_checkout.json()
        order_id = data.get("order_id", data.get("order", {}).get("order_id"))
        if not order_id:
            pytest.skip("No order_id returned from checkout")

        # Get stock now (after order)
        r_prod = requests.get(f"{BASE_URL}/products/{pid}", headers=uh)
        stock_after_order = int(r_prod.json().get("stock", 0))

        # Cancel the order
        r_cancel = requests.post(f"{BASE_URL}/orders/{order_id}/cancel", headers=uh)
        assert r_cancel.status_code == 200, f"Cancel failed: {r_cancel.status_code}: {r_cancel.text}"

        # Stock should be restored
        r_prod_after = requests.get(f"{BASE_URL}/products/{pid}", headers=uh)
        stock_after_cancel = int(r_prod_after.json().get("stock", 0))
        assert stock_after_cancel == stock_after_order + 1, \
            f"Stock not restored: before_cancel={stock_after_order}, after_cancel={stock_after_cancel}"


class TestInvoice:
    def test_invoice_subtotal_plus_gst_equals_total(self, uh, first_product):
        """Justification: Invoice must show subtotal, GST amount, and total where subtotal + GST = total."""
        pid = first_product["product_id"]
        stock = first_product.get("stock", 0)
        if stock < 1:
            pytest.skip("No stock")

        r_checkout = _checkout_card(uh, pid, 1)
        if r_checkout.status_code != 200:
            pytest.skip(f"Checkout failed: {r_checkout.text}")

        data = r_checkout.json()
        order_id = data.get("order_id", data.get("order", {}).get("order_id"))
        if not order_id:
            pytest.skip("No order_id returned")

        r_inv = requests.get(f"{BASE_URL}/orders/{order_id}/invoice", headers=uh)
        assert r_inv.status_code == 200, f"Invoice fetch failed: {r_inv.status_code}: {r_inv.text}"

        inv = r_inv.json()
        subtotal = float(inv.get("subtotal", 0))
        gst = float(inv.get("gst", inv.get("gst_amount", 0)))
        total = float(inv.get("total", 0))

        assert round(subtotal + gst, 2) == round(total, 2), \
            f"Invoice mismatch: subtotal({subtotal}) + gst({gst}) ≠ total({total})"

    def test_invoice_gst_is_5_percent_of_subtotal(self, uh, first_product):
        """Justification: GST must be exactly 5% of the subtotal."""
        pid = first_product["product_id"]
        stock = first_product.get("stock", 0)
        if stock < 1:
            pytest.skip("No stock")

        r_checkout = _checkout_card(uh, pid, 1)
        if r_checkout.status_code != 200:
            pytest.skip(f"Checkout failed: {r_checkout.text}")

        data = r_checkout.json()
        order_id = data.get("order_id", data.get("order", {}).get("order_id"))
        if not order_id:
            pytest.skip("No order_id returned")

        r_inv = requests.get(f"{BASE_URL}/orders/{order_id}/invoice", headers=uh)
        inv = r_inv.json()
        subtotal = float(inv.get("subtotal", 0))
        gst = float(inv.get("gst", inv.get("gst_amount", 0)))

        expected_gst = round(subtotal * 0.05, 2)
        assert round(gst, 2) == expected_gst, \
            f"GST should be 5% of subtotal: expected {expected_gst}, got {gst}"
