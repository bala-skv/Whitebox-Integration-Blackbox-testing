"""White-box tests for the Bank class."""
import pytest
from moneypoly.bank import Bank
from moneypoly.player import Player
from moneypoly.config import BANK_STARTING_FUNDS


class TestBankCollect:
    def test_collect_positive(self):
        bank = Bank()
        bank.collect(200)
        assert bank.get_balance() == BANK_STARTING_FUNDS + 200

    def test_collect_zero(self):
        bank = Bank()
        bank.collect(0)
        assert bank.get_balance() == BANK_STARTING_FUNDS

    def test_collect_negative_ignored(self):
        """Docstring says negative amounts are silently ignored.
        BUG CHECK: implementation does not guard against this."""
        bank = Bank()
        initial = bank.get_balance()
        bank.collect(-500)
        # Negative should not reduce bank funds
        assert bank.get_balance() == initial


class TestBankPayOut:
    def test_pay_out_normal(self):
        bank = Bank()
        result = bank.pay_out(100)
        assert result == 100
        assert bank.get_balance() == BANK_STARTING_FUNDS - 100

    def test_pay_out_zero(self):
        bank = Bank()
        result = bank.pay_out(0)
        assert result == 0
        assert bank.get_balance() == BANK_STARTING_FUNDS

    def test_pay_out_negative(self):
        bank = Bank()
        result = bank.pay_out(-10)
        assert result == 0

    def test_pay_out_insufficient_funds(self):
        bank = Bank()
        with pytest.raises(ValueError):
            bank.pay_out(BANK_STARTING_FUNDS + 1)


class TestBankGiveLoan:
    def test_give_loan_normal(self):
        bank = Bank()
        player = Player("Alice", balance=0)
        bank.give_loan(player, 500)
        assert player.balance == 500
        assert bank.loan_count() == 1
        assert bank.total_loans_issued() == 500

    def test_give_loan_zero(self):
        bank = Bank()
        player = Player("Alice", balance=0)
        bank.give_loan(player, 0)
        assert player.balance == 0
        assert bank.loan_count() == 0

    def test_give_loan_negative(self):
        bank = Bank()
        player = Player("Alice", balance=0)
        bank.give_loan(player, -100)
        assert player.balance == 0
        assert bank.loan_count() == 0

    def test_multiple_loans(self):
        bank = Bank()
        p1 = Player("Alice", balance=0)
        p2 = Player("Bob", balance=0)
        bank.give_loan(p1, 300)
        bank.give_loan(p2, 700)
        assert bank.loan_count() == 2
        assert bank.total_loans_issued() == 1000
