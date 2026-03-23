"""White-box tests for Property and PropertyGroup classes."""
import pytest
from moneypoly.property import Property, PropertyGroup
from moneypoly.player import Player


def make_property(price=100, rent=10, group=None):
    """Helper: create a simple Property."""
    return Property("Test St", 1, {"price": price, "rent": rent}, group)


class TestPropertyGetRent:
    def test_get_rent_mortgaged_returns_zero(self):
        prop = make_property()
        prop.finance["is_mortgaged"] = True
        assert prop.get_rent() == 0

    def test_get_rent_no_group(self):
        prop = make_property(rent=10)
        prop.owner = Player("Alice")
        assert prop.get_rent() == 10

    def test_get_rent_partial_group_base_rent(self):
        group = PropertyGroup("TestGroup", "red")
        p1 = make_property(rent=10, group=group)
        p2 = make_property(rent=10, group=group)
        p2.position = 2
        p2.name = "Test St 2"
        alice = Player("Alice")
        p1.owner = alice  # only owns one of two
        assert p1.get_rent() == 10  # base rent only

    def test_get_rent_full_group_doubled(self):
        """Owner holds every property in group → doubled rent.
        BUG CHECK: all_owned_by uses any() instead of all()."""
        group = PropertyGroup("TestGroup", "red")
        p1 = Property("A", 1, {"price": 100, "rent": 10}, group)
        p2 = Property("B", 2, {"price": 100, "rent": 10}, group)
        alice = Player("Alice")
        p1.owner = alice
        p2.owner = alice
        # With correct code (all), doubled rent is returned
        assert p1.get_rent() == 20  # 10 * FULL_GROUP_MULTIPLIER


class TestPropertyMortgage:
    def test_mortgage_normal(self):
        prop = make_property(price=100)
        payout = prop.mortgage()
        assert payout == 50  # price // 2
        assert prop.finance["is_mortgaged"] is True

    def test_mortgage_already_mortgaged(self):
        prop = make_property(price=100)
        prop.finance["is_mortgaged"] = True
        payout = prop.mortgage()
        assert payout == 0

    def test_unmortgage_normal(self):
        prop = make_property(price=100)
        prop.finance["is_mortgaged"] = True
        cost = prop.unmortgage()
        assert cost == int(50 * 1.1)  # mortgage_value * 1.1
        assert prop.finance["is_mortgaged"] is False

    def test_unmortgage_not_mortgaged(self):
        prop = make_property(price=100)
        cost = prop.unmortgage()
        assert cost == 0


class TestPropertyAvailability:
    def test_is_available_unowned_unmortgaged(self):
        prop = make_property()
        assert prop.is_available() is True

    def test_is_available_owned(self):
        prop = make_property()
        prop.owner = Player("Alice")
        assert prop.is_available() is False

    def test_is_available_mortgaged(self):
        prop = make_property()
        prop.finance["is_mortgaged"] = True
        assert prop.is_available() is False


class TestPropertyGroupAllOwnedBy:
    def test_all_owned_by_none_player(self):
        group = PropertyGroup("G", "blue")
        p1 = Property("A", 1, {"price": 100, "rent": 10}, group)
        assert group.all_owned_by(None) is False

    def test_all_owned_by_partial_ownership(self):
        """Player owns only 1 of 2 properties — should NOT be considered full owner.
        BUG CHECK: any() returns True even for partial ownership."""
        group = PropertyGroup("G", "blue")
        p1 = Property("A", 1, {"price": 100, "rent": 10}, group)
        p2 = Property("B", 2, {"price": 100, "rent": 10}, group)
        alice = Player("Alice")
        p1.owner = alice
        # p2.owner is None
        assert group.all_owned_by(alice) is False  # FAILS with any()

    def test_all_owned_by_full_ownership(self):
        group = PropertyGroup("G", "blue")
        p1 = Property("A", 1, {"price": 100, "rent": 10}, group)
        p2 = Property("B", 2, {"price": 100, "rent": 10}, group)
        alice = Player("Alice")
        p1.owner = alice
        p2.owner = alice
        assert group.all_owned_by(alice) is True
