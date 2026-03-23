"""
test_wallet.py — Tests for GET /api/v1/wallet, POST /api/v1/wallet/add, POST /api/v1/wallet/pay.

Spec:
  - Add: amount > 0, at most 100000.
  - Pay: amount > 0; if balance < amount → 400.
  - Pay deducts the exact requested amount (no extras).
"""

import requests
import pytest

BASE_URL = "http://localhost:8080/api/v1"


class TestWalletAdd:
    def test_add_zero_returns_error(self, uh):
        """Justification: Amount 0 is not > 0 per spec → must be rejected."""
        r = requests.post(f"{BASE_URL}/wallet/add", json={"amount": 0}, headers=uh)
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_add_negative_returns_error(self, uh):
        """Justification: Negative amount is invalid → must be rejected."""
        r = requests.post(f"{BASE_URL}/wallet/add", json={"amount": -100}, headers=uh)
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_add_above_100000_returns_error(self, uh):
        """Justification: Amount > 100000 exceeds maximum allowed → 400."""
        r = requests.post(f"{BASE_URL}/wallet/add", json={"amount": 100001}, headers=uh)
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_add_exactly_100000_accepted(self, uh):
        """Justification: Boundary value — 100000 is the maximum allowed amount."""
        r = requests.post(f"{BASE_URL}/wallet/add", json={"amount": 100000}, headers=uh)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    def test_add_valid_amount_increases_balance(self, uh):
        """Justification: After adding money, balance must increase by that exact amount."""
        r_before = requests.get(f"{BASE_URL}/wallet", headers=uh)
        before_balance = float(r_before.json().get("balance", r_before.json().get("wallet_balance", 0)))

        amount = 500
        r = requests.post(f"{BASE_URL}/wallet/add", json={"amount": amount}, headers=uh)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

        r_after = requests.get(f"{BASE_URL}/wallet", headers=uh)
        after_balance = float(r_after.json().get("balance", r_after.json().get("wallet_balance", 0)))
        assert round(after_balance - before_balance, 2) == amount, \
            f"Balance should increase by {amount}, before={before_balance}, after={after_balance}"


class TestWalletPay:
    def test_pay_zero_returns_error(self, uh):
        """Justification: Payment amount must be > 0 → 0 is invalid."""
        r = requests.post(f"{BASE_URL}/wallet/pay", json={"amount": 0}, headers=uh)
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_pay_more_than_balance_returns_400(self, uh):
        """Justification: Insufficient wallet balance must be rejected → 400."""
        # Get current balance
        r_bal = requests.get(f"{BASE_URL}/wallet", headers=uh)
        balance = float(r_bal.json().get("balance", r_bal.json().get("wallet_balance", 0)))

        r = requests.post(
            f"{BASE_URL}/wallet/pay",
            json={"amount": balance + 10000},
            headers=uh,
        )
        assert r.status_code == 400, f"Expected 400 for insufficient balance, got {r.status_code}: {r.text}"

    def test_pay_deducts_exact_amount(self, uh):
        """Justification: Only the exact requested amount must be deducted — no extras."""
        # Add known amount first
        requests.post(f"{BASE_URL}/wallet/add", json={"amount": 1000}, headers=uh)

        r_before = requests.get(f"{BASE_URL}/wallet", headers=uh)
        before_balance = float(r_before.json().get("balance", r_before.json().get("wallet_balance", 0)))

        amount = 100
        r = requests.post(f"{BASE_URL}/wallet/pay", json={"amount": amount}, headers=uh)
        assert r.status_code == 200, f"Pay failed: {r.status_code}: {r.text}"

        r_after = requests.get(f"{BASE_URL}/wallet", headers=uh)
        after_balance = float(r_after.json().get("balance", r_after.json().get("wallet_balance", 0)))
        assert round(before_balance - after_balance, 2) == amount, \
            f"Deduction mismatch: before={before_balance}, after={after_balance}, expected deduction={amount}"
