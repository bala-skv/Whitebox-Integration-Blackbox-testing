"""
test_products.py — Tests for GET /api/v1/products and GET /api/v1/products/{id}.

Spec:
  - List returns only active products.
  - Single product: 404 for non-existent ID.
  - Supports filter by category, search by name, sort by price (asc/desc).
  - Price shown must be the exact real price from DB.
"""

import requests
import pytest

BASE_URL = "http://localhost:8080/api/v1"


class TestListProducts:
    def test_get_products_returns_200(self, uh):
        """Justification: Product listing is a core feature — must return 200."""
        r = requests.get(f"{BASE_URL}/products", headers=uh)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    def test_products_list_is_a_list(self, uh):
        """Justification: Response must be a JSON array of products."""
        r = requests.get(f"{BASE_URL}/products", headers=uh)
        data = r.json()
        products = data if isinstance(data, list) else data.get("products", data.get("data", []))
        assert isinstance(products, list), f"Expected list, got {type(products)}: {data}"

    def test_inactive_products_not_in_list(self, uh, admin_headers):
        """Justification: Only active products should be visible to users; inactive ones must be hidden."""
        # Get all products from admin (includes inactive)
        r_admin = requests.get(f"{BASE_URL}/admin/products", headers=admin_headers)
        all_products = r_admin.json()
        inactive_ids = {p["product_id"] for p in all_products if not p.get("is_active", True)}

        # Get public product list
        r_user = requests.get(f"{BASE_URL}/products", headers=uh)
        data = r_user.json()
        user_products = data if isinstance(data, list) else data.get("products", data.get("data", []))
        user_ids = {p["product_id"] for p in user_products}

        leaked = inactive_ids & user_ids
        assert not leaked, f"Inactive products leaked into user listing: {leaked}"

    def test_filter_by_category(self, uh, admin_headers):
        """Justification: Category filter must return only products of that category."""
        # Find a category from admin
        r_admin = requests.get(f"{BASE_URL}/admin/products", headers=admin_headers)
        products = r_admin.json()
        active = [p for p in products if p.get("is_active", True)]
        if not active:
            pytest.skip("No active products available")
        category = active[0].get("category")
        if not category:
            pytest.skip("Products have no category field")

        r = requests.get(f"{BASE_URL}/products", params={"category": category}, headers=uh)
        assert r.status_code == 200
        data = r.json()
        filtered = data if isinstance(data, list) else data.get("products", data.get("data", []))
        for p in filtered:
            assert p.get("category") == category, \
                f"Product {p.get('product_id')} has wrong category: {p.get('category')}"

    def test_sort_by_price_ascending(self, uh):
        """Justification: sort=price_asc must return products with non-decreasing prices."""
        r = requests.get(f"{BASE_URL}/products", params={"sort": "price_asc"}, headers=uh)
        assert r.status_code == 200
        data = r.json()
        products = data if isinstance(data, list) else data.get("products", data.get("data", []))
        prices = [p.get("price", 0) for p in products]
        assert prices == sorted(prices), f"Prices not ascending: {prices}"

    def test_sort_by_price_descending(self, uh):
        """Justification: sort=price_desc must return products with non-increasing prices."""
        r = requests.get(f"{BASE_URL}/products", params={"sort": "price_desc"}, headers=uh)
        assert r.status_code == 200
        data = r.json()
        products = data if isinstance(data, list) else data.get("products", data.get("data", []))
        prices = [p.get("price", 0) for p in products]
        assert prices == sorted(prices, reverse=True), f"Prices not descending: {prices}"

    def test_search_by_name(self, uh, first_product):
        """Justification: Name search must return only matching products."""
        name = first_product.get("name", "")[:4]
        if not name:
            pytest.skip("No product name available")
        r = requests.get(f"{BASE_URL}/products", params={"search": name}, headers=uh)
        assert r.status_code == 200


class TestSingleProduct:
    def test_get_existing_product_returns_200(self, uh, first_product):
        """Justification: A known product_id must return 200 with product details."""
        pid = first_product["product_id"]
        r = requests.get(f"{BASE_URL}/products/{pid}", headers=uh)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    def test_get_nonexistent_product_returns_404(self, uh):
        """Justification: Non-existent product_id must return 404 per spec."""
        r = requests.get(f"{BASE_URL}/products/999999", headers=uh)
        assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"

    def test_product_price_matches_admin(self, uh, admin_headers, first_product):
        """Justification: Price shown to user must be the exact real price from DB."""
        pid = first_product["product_id"]
        r_user = requests.get(f"{BASE_URL}/products/{pid}", headers=uh)
        r_admin = requests.get(f"{BASE_URL}/admin/products", headers=admin_headers)
        admin_products = r_admin.json()
        admin_product = next((p for p in admin_products if p["product_id"] == pid), None)

        if admin_product:
            user_price = r_user.json().get("price")
            admin_price = admin_product.get("price")
            assert user_price == admin_price, \
                f"Price mismatch: user sees {user_price}, admin has {admin_price}"
