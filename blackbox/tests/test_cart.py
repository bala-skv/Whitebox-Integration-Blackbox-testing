"""
test_cart.py — Tests for cart endpoints.

Spec:
  - Add: qty ≥ 1, product must exist, qty ≤ stock.
  - Duplicate add → quantities sum.
  - Subtotal = qty × unit price.
  - Cart total = sum of all subtotals.
  - Update: qty ≥ 1.
  - Remove: 404 if product not in cart.
  - Clear: empties cart.
"""

import requests
import pytest

BASE_URL = "http://localhost:8080/api/v1"


def _clear(uh):
    requests.delete(f"{BASE_URL}/cart/clear", headers=uh)


def _add(uh, product_id, quantity):
    return requests.post(
        f"{BASE_URL}/cart/add",
        json={"product_id": product_id, "quantity": quantity},
        headers=uh,
    )


def _get_cart(uh):
    return requests.get(f"{BASE_URL}/cart", headers=uh)


class TestCartAdd:
    def setup_method(self):
        pass  # each test clears manually

    def test_add_item_qty_zero_returns_400(self, uh, first_product):
        """Justification: Quantity 0 is below minimum (1) → 400."""
        _clear(uh)
        r = _add(uh, first_product["product_id"], 0)
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_add_item_negative_qty_returns_400(self, uh, first_product):
        """Justification: Negative quantity is invalid → 400."""
        _clear(uh)
        r = _add(uh, first_product["product_id"], -1)
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_add_nonexistent_product_returns_404(self, uh):
        """Justification: Product that doesn't exist → 404."""
        _clear(uh)
        r = _add(uh, 999999, 1)
        assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"

    def test_add_item_exceeds_stock_returns_400(self, uh, first_product):
        """Justification: Requesting more than stock → 400."""
        _clear(uh)
        stock = first_product.get("stock", 0)
        if stock <= 0:
            pytest.skip("Product is out of stock")
        r = _add(uh, first_product["product_id"], stock + 100)
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_add_valid_item_returns_success(self, uh, first_product):
        """Justification: Valid product with qty=1 must be accepted."""
        _clear(uh)
        stock = first_product.get("stock", 0)
        if stock <= 0:
            pytest.skip("Product is out of stock")
        r = _add(uh, first_product["product_id"], 1)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    def test_duplicate_add_sums_quantities(self, uh, first_product):
        """Justification: Adding same product twice must sum quantities, not replace."""
        _clear(uh)
        pid = first_product["product_id"]
        stock = first_product.get("stock", 0)
        if stock < 2:
            pytest.skip("Need at least 2 stock for duplicate add test")
        _add(uh, pid, 1)
        _add(uh, pid, 1)

        cart = _get_cart(uh).json()
        items = cart if isinstance(cart, list) else cart.get("items", cart.get("cart_items", []))
        item = next((i for i in items if i.get("product_id") == pid), None)
        assert item is not None, "Product not found in cart"
        assert item.get("quantity") == 2, \
            f"Expected quantity 2 after two adds, got {item.get('quantity')}"


class TestCartSubtotals:
    def test_item_subtotal_equals_qty_times_price(self, uh, first_product):
        """Justification: Each item subtotal must equal quantity × unit price (spec requirement)."""
        _clear(uh)
        pid = first_product["product_id"]
        price = first_product.get("price", 0)
        stock = first_product.get("stock", 0)
        if stock < 2:
            pytest.skip("Need at least 2 in stock")
        _add(uh, pid, 2)

        cart = _get_cart(uh).json()
        items = cart if isinstance(cart, list) else cart.get("items", cart.get("cart_items", []))
        item = next((i for i in items if i.get("product_id") == pid), None)
        assert item is not None
        expected_subtotal = round(2 * price, 2)
        actual_subtotal = round(float(item.get("subtotal", 0)), 2)
        assert actual_subtotal == expected_subtotal, \
            f"Subtotal mismatch: expected {expected_subtotal}, got {actual_subtotal}"

    def test_cart_total_equals_sum_of_subtotals(self, uh, first_product):
        """Justification: Cart total must equal the sum of all item subtotals per spec."""
        _clear(uh)
        pid = first_product["product_id"]
        stock = first_product.get("stock", 0)
        if stock < 1:
            pytest.skip("No stock available")
        _add(uh, pid, 1)

        cart = _get_cart(uh).json()
        items = cart.get("items", cart.get("cart_items", [])) if not isinstance(cart, list) else cart
        total_from_items = round(sum(float(i.get("subtotal", 0)) for i in items), 2)
        cart_total = round(float(cart.get("total", cart.get("cart_total", 0))), 2)
        assert cart_total == total_from_items, \
            f"Cart total {cart_total} ≠ sum of subtotals {total_from_items}"


class TestCartUpdate:
    def test_update_qty_to_zero_returns_400(self, uh, first_product):
        """Justification: Update quantity to 0 is below minimum → 400."""
        _clear(uh)
        pid = first_product["product_id"]
        stock = first_product.get("stock", 0)
        if stock < 1:
            pytest.skip("No stock")
        _add(uh, pid, 1)
        r = requests.post(
            f"{BASE_URL}/cart/update",
            json={"product_id": pid, "quantity": 0},
            headers=uh,
        )
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"


class TestCartRemove:
    def test_remove_item_not_in_cart_returns_404(self, uh):
        """Justification: Removing a product not in cart must return 404 per spec."""
        _clear(uh)
        r = requests.post(
            f"{BASE_URL}/cart/remove",
            json={"product_id": 999999},
            headers=uh,
        )
        assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"

    def test_clear_cart_empties_it(self, uh, first_product):
        """Justification: After DELETE /cart/clear, cart must be empty."""
        pid = first_product["product_id"]
        stock = first_product.get("stock", 0)
        if stock < 1:
            pytest.skip("No stock")
        _add(uh, pid, 1)
        _clear(uh)
        cart = _get_cart(uh).json()
        items = cart if isinstance(cart, list) else cart.get("items", cart.get("cart_items", []))
        assert items == [], f"Cart not empty after clear: {items}"
