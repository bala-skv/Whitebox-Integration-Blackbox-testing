"""White-box tests for the Game class (logic methods only, no UI/input)."""
import pytest
from unittest.mock import patch, MagicMock
from moneypoly.game import Game
from moneypoly.player import Player
from moneypoly.property import Property, PropertyGroup
from moneypoly.bank import Bank
from moneypoly.config import STARTING_BALANCE


def make_game(names=("Alice", "Bob")):
    """Create a Game instance with the given player names."""
    return Game(list(names))


def make_prop(price=200, rent=20, owner=None):
    """Create a standalone Property (no group)."""
    prop = Property("Test Ave", 1, {"price": price, "rent": rent})
    prop.owner = owner
    return prop


class TestBuyProperty:
    def test_buy_success(self):
        g = make_game()
        alice = g.players[0]
        prop = make_prop(price=100)
        result = g.buy_property(alice, prop)
        assert result is True
        assert prop.owner == alice
        assert alice.balance == STARTING_BALANCE - 100

    def test_buy_exact_balance_should_succeed(self):
        """Player with exactly the asking price should be able to buy.
        BUG CHECK: code uses <= instead of <, blocking this case."""
        g = make_game()
        alice = g.players[0]
        alice.balance = 100
        prop = make_prop(price=100)
        result = g.buy_property(alice, prop)
        # With correct code (balance < price means CAN'T afford),
        # having exactly 100 should PASS (balance == price means they can just afford it)
        assert result is True  # FAILS with current <= bug

    def test_buy_insufficient_balance(self):
        g = make_game()
        alice = g.players[0]
        alice.balance = 50
        prop = make_prop(price=100)
        result = g.buy_property(alice, prop)
        assert result is False
        assert prop.owner is None


class TestPayRent:
    def test_pay_rent_mortgaged_no_charge(self):
        g = make_game()
        alice, bob = g.players
        prop = make_prop(price=100, rent=30, owner=bob)
        prop.finance["is_mortgaged"] = True
        before = alice.balance
        g.pay_rent(alice, prop)
        assert alice.balance == before  # no rent deducted

    def test_pay_rent_normal(self):
        g = make_game()
        alice, bob = g.players
        prop = make_prop(price=100, rent=30, owner=bob)
        before = alice.balance
        g.pay_rent(alice, prop)
        assert alice.balance == before - 30


class TestMortgageProperty:
    def test_mortgage_not_owner_returns_false(self):
        g = make_game()
        alice, bob = g.players
        prop = make_prop(owner=bob)
        assert g.mortgage_property(alice, prop) is False

    def test_mortgage_success(self):
        g = make_game()
        alice = g.players[0]
        prop = make_prop(price=200, owner=alice)
        before = alice.balance
        result = g.mortgage_property(alice, prop)
        assert result is True
        assert alice.balance == before + 100  # price // 2


class TestUnmortgageProperty:
    def test_unmortgage_not_owner_returns_false(self):
        g = make_game()
        alice, bob = g.players
        prop = make_prop(owner=bob)
        prop.finance["is_mortgaged"] = True
        assert g.unmortgage_property(alice, prop) is False

    def test_unmortgage_success(self):
        g = make_game()
        alice = g.players[0]
        prop = make_prop(price=200, owner=alice)
        prop.finance["is_mortgaged"] = True
        cost = int(100 * 1.1)  # mortgage_value * 1.1
        before = alice.balance
        result = g.unmortgage_property(alice, prop)
        assert result is True
        assert alice.balance == before - cost

    def test_unmortgage_insufficient_funds(self):
        g = make_game()
        alice = g.players[0]
        alice.balance = 1  # not enough to redeem
        prop = make_prop(price=200, owner=alice)
        prop.finance["is_mortgaged"] = True
        result = g.unmortgage_property(alice, prop)
        assert result is False


class TestTrade:
    def test_trade_success(self):
        g = make_game()
        alice, bob = g.players
        prop = make_prop(owner=alice)
        alice.properties.append(prop)
        result = g.trade(alice, bob, prop, 50)
        assert result is True
        assert prop.owner == bob

    def test_trade_wrong_owner(self):
        g = make_game()
        alice, bob = g.players
        prop = make_prop(owner=bob)  # bob owns it, alice tries to sell
        result = g.trade(alice, bob, prop, 50)
        assert result is False

    def test_trade_buyer_insufficient_funds(self):
        g = make_game()
        alice, bob = g.players
        prop = make_prop(owner=alice)
        bob.balance = 10
        result = g.trade(alice, bob, prop, 500)
        assert result is False


class TestCheckBankruptcy:
    def test_bankruptcy_removes_player(self):
        g = make_game()
        alice = g.players[0]
        alice.balance = -1
        prop = make_prop(owner=alice)
        alice.properties.append(prop)
        g._check_bankruptcy(alice)
        assert alice not in g.players
        assert prop.owner is None
        assert prop.finance["is_mortgaged"] is False

    def test_no_bankruptcy_when_solvent(self):
        g = make_game()
        alice = g.players[0]
        g._check_bankruptcy(alice)
        assert alice in g.players


class TestApplyCard:
    def test_apply_card_none(self):
        g = make_game()
        alice = g.players[0]
        before = alice.balance
        g._apply_card(alice, None)  # should be a no-op
        assert alice.balance == before

    def test_apply_card_collect(self):
        g = make_game()
        alice = g.players[0]
        before = alice.balance
        card = {"description": "Collect $200", "action": "collect", "value": 200}
        g._apply_card(alice, card)
        assert alice.balance == before + 200

    def test_apply_card_pay(self):
        g = make_game()
        alice = g.players[0]
        before = alice.balance
        card = {"description": "Pay $150", "action": "pay", "value": 150}
        g._apply_card(alice, card)
        assert alice.balance == before - 150

    def test_apply_card_jail(self):
        g = make_game()
        alice = g.players[0]
        card = {"description": "Go to Jail", "action": "jail", "value": 0}
        g._apply_card(alice, card)
        assert alice.jail_status["in_jail"] is True

    def test_apply_card_jail_free(self):
        g = make_game()
        alice = g.players[0]
        card = {"description": "Get Out of Jail Free", "action": "jail_free", "value": 0}
        g._apply_card(alice, card)
        assert alice.jail_status["cards"] == 1

    def test_apply_card_birthday(self):
        g = make_game()
        alice, bob = g.players
        card = {"description": "Birthday", "action": "birthday", "value": 50}
        bob_before = bob.balance
        g._apply_card(alice, card)
        assert bob.balance == bob_before - 50


class TestFindWinner:
    def test_find_winner_no_players(self):
        g = make_game(names=[])
        g.players = []
        assert g.find_winner() is None

    def test_find_winner_picks_richest(self):
        """find_winner should return the player with the HIGHEST net worth.
        BUG CHECK: code uses min() instead of max()."""
        g = make_game()
        alice, bob = g.players
        alice.balance = 1000
        bob.balance = 500
        winner = g.find_winner()
        assert winner == alice  # FAILS with current min() bug


class TestAdvanceTurn:
    def test_advance_turn_increments(self):
        g = make_game()
        g.advance_turn()
        assert g.state["turn_number"] == 1
        assert g.state["current_index"] == 1

    def test_advance_turn_wraps(self):
        g = make_game()
        g.state["current_index"] = 1  # last player (0-indexed, 2 players)
        g.advance_turn()
        assert g.state["current_index"] == 0


class TestApplyCardMoveTo:
    def test_apply_card_move_to_forward(self):
        """move_to card: player moves forward (no Go salary expected)."""
        g = make_game()
        alice = g.players[0]
        alice.position = 5
        before = alice.balance
        card = {"description": "Advance to Go", "action": "move_to", "value": 10}
        g._apply_card(alice, card)
        assert alice.position == 10
        assert alice.balance == before  # no Go salary, moved forward

    def test_apply_card_move_to_backward_earns_go_salary(self):
        """move_to card: destination is behind old position → player passes Go."""
        g = make_game()
        alice = g.players[0]
        alice.position = 30
        before = alice.balance
        from moneypoly.config import GO_SALARY
        card = {"description": "Move back to Go", "action": "move_to", "value": 5}
        g._apply_card(alice, card)
        assert alice.position == 5
        assert alice.balance == before + GO_SALARY  # passed Go

    def test_apply_card_birthday_other_player_broke(self):
        """Birthday card: other player doesn't have enough — should NOT be charged."""
        g = make_game()
        alice, bob = g.players
        bob.balance = 10  # can't afford 50
        alice_before = alice.balance
        card = {"description": "Birthday", "action": "birthday", "value": 50}
        g._apply_card(alice, card)
        # Bob had only 10, so the condition other.balance >= value is False → no deduction
        assert bob.balance == 10  # untouched
        assert alice.balance == alice_before  # didn't collect either


class TestMortgageEdgeCases:
    def test_mortgage_already_mortgaged_returns_false(self):
        """Mortgaging a property that's already mortgaged should return False."""
        g = make_game()
        alice = g.players[0]
        prop = make_prop(price=200, owner=alice)
        prop.finance["is_mortgaged"] = True
        result = g.mortgage_property(alice, prop)
        assert result is False  # payout is 0, so returns False

    def test_trade_zero_cash(self):
        """A player can gift a property for free (cash_amount = 0)."""
        g = make_game()
        alice, bob = g.players
        prop = make_prop(owner=alice)
        alice.properties.append(prop)
        result = g.trade(alice, bob, prop, 0)
        assert result is True
        assert prop.owner == bob


class TestPlayerMoveEdgeCases:
    def test_move_zero_steps(self):
        """Moving 0 steps should leave position unchanged and award no Go salary."""
        from moneypoly.player import Player
        from moneypoly.config import STARTING_BALANCE
        p = Player("Alice")
        p.position = 10
        p.move(0)
        assert p.position == 10
        assert p.balance == STARTING_BALANCE  # no Go salary

    def test_move_exactly_board_size_steps(self):
        """Moving exactly BOARD_SIZE steps from non-zero position passes Go."""
        from moneypoly.player import Player
        from moneypoly.config import STARTING_BALANCE, GO_SALARY, BOARD_SIZE
        p = Player("Alice")
        p.position = 5
        p.move(BOARD_SIZE)  # 5 + 40 = 45 → wraps to 5, but passed Go
        assert p.position == 5
        # BUG CHECK: current fix uses position < old_position, which is False here
        # (new_pos == old_pos). Salary should still be awarded.
        assert p.balance == STARTING_BALANCE + GO_SALARY


class TestBankruptcyIndexWrap:
    def test_bankruptcy_current_index_wraps(self):
        """If the bankrupt player was last in the list, current_index wraps to 0."""
        g = make_game()
        alice, bob = g.players
        # Set current index to point at bob (index 1, the last player)
        g.state["current_index"] = 1
        bob.balance = -1
        g._check_bankruptcy(bob)
        # Bob removed → list has 1 player; index 1 >= len(1), so should wrap to 0
        assert g.state["current_index"] == 0
        assert bob not in g.players

