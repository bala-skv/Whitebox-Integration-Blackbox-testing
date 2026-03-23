"""White-box tests for the Player class."""
import pytest
from moneypoly.player import Player
from moneypoly.config import STARTING_BALANCE, BOARD_SIZE, GO_SALARY, JAIL_POSITION


class TestAddMoney:
    def test_add_money_positive(self):
        p = Player("Alice")
        p.add_money(100)
        assert p.balance == STARTING_BALANCE + 100

    def test_add_money_zero(self):
        p = Player("Alice")
        p.add_money(0)
        assert p.balance == STARTING_BALANCE

    def test_add_money_negative_raises(self):
        p = Player("Alice")
        with pytest.raises(ValueError):
            p.add_money(-50)


class TestDeductMoney:
    def test_deduct_money_positive(self):
        p = Player("Alice")
        p.deduct_money(100)
        assert p.balance == STARTING_BALANCE - 100

    def test_deduct_money_zero(self):
        p = Player("Alice")
        p.deduct_money(0)
        assert p.balance == STARTING_BALANCE

    def test_deduct_money_negative_raises(self):
        p = Player("Alice")
        with pytest.raises(ValueError):
            p.deduct_money(-50)


class TestIsBankrupt:
    def test_is_bankrupt_positive_balance(self):
        p = Player("Alice")
        assert p.is_bankrupt() is False

    def test_is_bankrupt_zero_balance(self):
        p = Player("Alice", balance=0)
        assert p.is_bankrupt() is True

    def test_is_bankrupt_negative_balance(self):
        p = Player("Alice", balance=-100)
        assert p.is_bankrupt() is True


class TestMove:
    def test_move_normal(self):
        p = Player("Alice")
        p.position = 5
        new_pos = p.move(6)
        assert new_pos == 11
        assert p.balance == STARTING_BALANCE  # no Go bonus

    def test_move_lands_on_go(self):
        """Moving exactly to position 0 should award Go salary."""
        p = Player("Alice")
        p.position = BOARD_SIZE - 3
        p.move(3)
        assert p.position == 0
        assert p.balance == STARTING_BALANCE + GO_SALARY

    def test_move_passes_go_awards_salary(self):
        """Passing Go (wrapping but landing elsewhere) should also award Go salary."""
        p = Player("Alice")
        p.position = BOARD_SIZE - 2  # 2 steps from end
        p.move(5)   # wraps around, lands at 3 — should pass Go
        assert p.position == 3
        # BUG CHECK: salary should be awarded for passing Go, not just landing on it
        assert p.balance == STARTING_BALANCE + GO_SALARY


class TestGoToJail:
    def test_go_to_jail(self):
        p = Player("Alice")
        p.position = 10
        p.go_to_jail()
        assert p.position == JAIL_POSITION
        assert p.jail_status["in_jail"] is True
        assert p.jail_status["turns"] == 0


class TestProperties:
    def test_add_property(self):
        p = Player("Alice")
        prop = object()  # dummy object
        p.properties.append(prop)
        assert prop in p.properties

    def test_add_property_dedup(self):
        p = Player("Alice")
        prop = object()
        p.add_property(prop)
        p.add_property(prop)  # add same property again
        assert p.properties.count(prop) == 1

    def test_remove_property_present(self):
        p = Player("Alice")
        prop = object()
        p.properties.append(prop)
        p.remove_property(prop)
        assert prop not in p.properties

    def test_remove_property_absent(self):
        p = Player("Alice")
        prop = object()
        p.remove_property(prop)  # should not raise
        assert prop not in p.properties


class TestStatusLine:
    def test_status_line_not_jailed(self):
        p = Player("Alice")
        line = p.status_line()
        assert "[JAILED]" not in line

    def test_status_line_jailed(self):
        p = Player("Alice")
        p.go_to_jail()
        line = p.status_line()
        assert "[JAILED]" in line
