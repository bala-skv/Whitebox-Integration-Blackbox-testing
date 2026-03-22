"""Main game loop and logic for MoneyPoly."""

from moneypoly.config import (
    JAIL_FINE,
    AUCTION_MIN_INCREMENT,
    INCOME_TAX_AMOUNT,
    LUXURY_TAX_AMOUNT,
    MAX_TURNS,
    GO_SALARY,
)
from moneypoly.player import Player
from moneypoly.board import Board
from moneypoly.bank import Bank
from moneypoly.dice import Dice
from moneypoly.cards import CardDeck, CHANCE_CARDS, COMMUNITY_CHEST_CARDS
from moneypoly import ui


class Game:
    """Manages the full state and flow of a MoneyPoly game session."""

    def __init__(self, player_names):
        """Initialize the game state with consolidated attributes for R0902."""
        self.board = Board()
        self.bank = Bank()
        self.dice = Dice()
        self.players = [Player(name) for name in player_names]
        self.running = True
        # Consolidate turn tracking into a 'state' dict (Attributes: 6/7)
        self.state = {
            "current_index": 0,
            "turn_number": 0
        }
        # Consolidate decks into a 'decks' dict (Attributes: 7/7)
        self.decks = {
            "chance": CardDeck(CHANCE_CARDS),
            "community": CardDeck(COMMUNITY_CHEST_CARDS)
        }

    def current_player(self):
        """Return the Player whose turn it currently is."""
        return self.players[self.state["current_index"]]

    def advance_turn(self):
        """Move to the next player in the rotation."""
        self.state["current_index"] = (self.state["current_index"] + 1) % len(self.players)
        self.state["turn_number"] += 1

    def play_turn(self):
        """Execute one complete turn for the current player."""
        player = self.current_player()
        ui.print_banner(
            f"Turn {self.state['turn_number'] + 1}  |  {player.name}  |  ${player.balance}"
        )

        if player.jail_status["in_jail"]:
            self._handle_jail_turn(player)
            self.advance_turn()
            return

        roll = self.dice.roll()
        print(f"  {player.name} rolled: {self.dice.describe()}")

        if self.dice.doubles_streak >= 3:
            print(f"  {player.name} rolled doubles 3 times in a row — go to jail!")
            player.go_to_jail()
            self.advance_turn()
            return

        self._move_and_resolve(player, roll)

        if self.dice.is_doubles():
            print(f"  Doubles! {player.name} rolls again.")
            return

        self.advance_turn()

    def _move_and_resolve(self, player, steps):
        """Move player and trigger tile logic using a dispatch dictionary."""
        player.move(steps)
        tile = self.board.get_tile_type(player.position)
        print(f"  {player.name} moved to position {player.position}  [{tile}]")

        # Dispatch table resolves R0912 (Branch complexity)
        handlers = {
            "go_to_jail": player.go_to_jail,
            "income_tax": lambda: self._pay_tax(player, INCOME_TAX_AMOUNT),
            "luxury_tax": lambda: self._pay_tax(player, LUXURY_TAX_AMOUNT),
            "chance": lambda: self._apply_card(player, self.decks["chance"].draw()),
            "community_chest": lambda: self._apply_card(player, self.decks["community"].draw()),
            "free_parking": lambda: print(f"  {player.name} rests on Free Parking."),
        }

        if tile in handlers:
            handlers[tile]()
        elif tile in ("property", "railroad"):
            prop = self.board.get_property_at(player.position)
            if prop:
                self._handle_property_tile(player, prop)

        self._check_bankruptcy(player)

    def _pay_tax(self, player, amount):
        """Helper to handle tax logic."""
        player.deduct_money(amount)
        self.bank.collect(amount)
        print(f"  {player.name} paid tax: ${amount}.")

    def _handle_property_tile(self, player, prop):
        """Resolve property landing using finance dict."""
        if prop.owner is None:
            price = prop.finance['price']
            print(f"  {prop.name} is unowned — asking price ${price}.")
            choice = input("  Buy (b), Auction (a), or Skip (s)? ").strip().lower()
            if choice == "b":
                self.buy_property(player, prop)
            elif choice == "a":
                self.auction_property(prop)
            else:
                print(f"  {player.name} passes on {prop.name}.")
        elif prop.owner == player:
            print(f"  {player.name} owns {prop.name}. No rent due.")
        else:
            self.pay_rent(player, prop)

    def buy_property(self, player, prop):
        """Purchase prop using finance dict."""
        price = prop.finance['price']
        if player.balance < price:
            print(f"  {player.name} cannot afford {prop.name} (${price}).")
            return False
        player.deduct_money(price)
        prop.owner = player
        player.add_property(prop)
        self.bank.collect(price)
        print(f"  {player.name} purchased {prop.name} for ${price}.")
        return True

    def pay_rent(self, player, prop):
        """Pay rent if property is not mortgaged."""
        if prop.finance['is_mortgaged']:
            print(f"  {prop.name} is mortgaged — no rent collected.")
            return
        if prop.owner:
            rent = prop.get_rent()
            player.deduct_money(rent)
            print(f"  {player.name} paid ${rent} rent on {prop.name} to {prop.owner.name}.")

    def mortgage_property(self, player, prop):
        """Mortgage logic using finance dict."""
        if prop.owner != player:
            return False
        payout = prop.mortgage()
        if payout > 0:
            player.add_money(payout)
            self.bank.collect(-payout)
            print(f"  {player.name} mortgaged {prop.name} for ${payout}.")
            return True
        return False

    def unmortgage_property(self, player, prop):
        """Redeem mortgaged property."""
        if prop.owner != player:
            return False
        cost = prop.unmortgage()
        if 0 < cost <= player.balance:
            player.deduct_money(cost)
            self.bank.collect(cost)
            print(f"  {player.name} unmortgaged {prop.name} for ${cost}.")
            return True
        return False

    def trade(self, seller, buyer, prop, cash_amount):
        """Execute property-for-cash trade."""
        if prop.owner == seller and buyer.balance >= cash_amount:
            buyer.deduct_money(cash_amount)
            prop.owner = buyer
            seller.remove_property(prop)
            buyer.add_property(prop)
            print(f"  {seller.name} sold {prop.name} to {buyer.name} for ${cash_amount}.")
            return True
        return False

    def auction_property(self, prop):
        """Auction unowned property."""
        price = prop.finance['price']
        print(f"\n  [Auction] Bidding on {prop.name} (Value: ${price})")
        highest_bid, highest_bidder = 0, None

        for player in self.players:
            print(f"  {player.name} (Bal: ${player.balance}, High: ${highest_bid})")
            bid = ui.safe_int_input("  Bid (0 to pass): ", default=0)
            if highest_bid + AUCTION_MIN_INCREMENT <= bid <= player.balance:
                highest_bid, highest_bidder = bid, player

        if highest_bidder:
            highest_bidder.deduct_money(highest_bid)
            prop.owner = highest_bidder
            highest_bidder.add_property(prop)
            self.bank.collect(highest_bid)
            print(f"  {highest_bidder.name} won {prop.name} for ${highest_bid}.")

    def _handle_jail_turn(self, player):
        """Process jail turn using jail_status dict."""
        print(f"  {player.name} in jail (turn {player.jail_status['turns'] + 1}/3).")

        if player.jail_status['cards'] > 0:
            if ui.confirm("  Use Get Out of Jail Free card? "):
                player.jail_status['cards'] -= 1
                player.jail_status['in_jail'] = False
                player.jail_status['turns'] = 0
                self._move_and_resolve(player, self.dice.roll())
                return

        if ui.confirm(f"  Pay ${JAIL_FINE} fine? "):
            self.bank.collect(JAIL_FINE)
            player.jail_status['in_jail'] = False
            player.jail_status['turns'] = 0
            self._move_and_resolve(player, self.dice.roll())
            return

        player.jail_status['turns'] += 1
        if player.jail_status['turns'] >= 3:
            player.deduct_money(JAIL_FINE)
            self.bank.collect(JAIL_FINE)
            player.jail_status['in_jail'] = False
            player.jail_status['turns'] = 0
            self._move_and_resolve(player, self.dice.roll())

    def _apply_card(self, player, card):
        """Apply drawn card effects."""
        if not card:
            return
        print(f"  Card: {card['description']}")
        action, value = card["action"], card["value"]

        if action == "collect":
            player.add_money(self.bank.pay_out(value))
        elif action == "pay":
            player.deduct_money(value)
            self.bank.collect(value)
        elif action == "jail":
            player.go_to_jail()
        elif action == "jail_free":
            player.jail_status['cards'] += 1
        elif action == "move_to":
            old_pos = player.position
            player.position = value
            if value < old_pos:
                player.add_money(GO_SALARY)
            tile = self.board.get_tile_type(value)
            if tile == "property":
                prop = self.board.get_property_at(value)
                if prop:
                    self._handle_property_tile(player, prop)
        elif action in ("birthday", "collect_from_all"):
            for other in self.players:
                if other != player and other.balance >= value:
                    other.deduct_money(value)
                    player.add_money(value)

    def _check_bankruptcy(self, player):
        """Handle player elimination."""
        if player.is_bankrupt():
            print(f"\n  *** {player.name} is bankrupt! ***")
            player.is_eliminated = True
            for prop in list(player.properties):
                prop.owner = None
                prop.finance["is_mortgaged"] = False
            player.properties.clear()
            self.players.remove(player)
            if self.state["current_index"] >= len(self.players):
                self.state["current_index"] = 0

    def find_winner(self):
        """Return wealthiest player."""
        return min(self.players, key=lambda p: p.net_worth()) if self.players else None

    def run(self):
        """Main loop."""
        ui.print_banner("Welcome to MoneyPoly!")
        while self.running and self.state["turn_number"] < MAX_TURNS:
            if len(self.players) <= 1:
                break
            self.play_turn()
            ui.print_standings(self.players)

        winner = self.find_winner()
        if winner:
            ui.print_banner(f"GAME OVER: {winner.name} WINS!")

    def interactive_menu(self, player):
        """Handle pre-roll choices."""
        while True:
            print("\n  1. Standings 2. Board 3. Mortgage 4. Unmortgage 5. Trade 0. Roll")
            choice = ui.safe_int_input("  Choice: ", default=0)
            if choice == 0:
                break
            menu_actions = {
                1: lambda: ui.print_standings(self.players),
                2: lambda: ui.print_board_ownership(self.board),
                3: lambda: self._menu_mortgage(player),
                4: lambda: self._menu_unmortgage(player),
                5: lambda: self._menu_trade(player),
            }
            if choice in menu_actions:
                menu_actions[choice]()

    def _menu_mortgage(self, player):
        """Select property to mortgage."""
        mortgageable = [p for p in player.properties if not p.finance["is_mortgaged"]]
        for i, prop in enumerate(mortgageable):
            print(f"  {i+1}. {prop.name} (${prop.finance['mortgage_value']})")
        idx = ui.safe_int_input("  Select: ", default=0) - 1
        if 0 <= idx < len(mortgageable):
            self.mortgage_property(player, mortgageable[idx])

    def _menu_unmortgage(self, player):
        """Select property to redeem."""
        mortgaged = [p for p in player.properties if p.finance["is_mortgaged"]]
        for i, prop in enumerate(mortgaged):
            print(f"  {i+1}. {prop.name}")
        idx = ui.safe_int_input("  Select: ", default=0) - 1
        if 0 <= idx < len(mortgaged):
            self.unmortgage_property(player, mortgaged[idx])

    def _menu_trade(self, player):
        """Handle trading logic with direct chained comparisons for R1716."""
        others = [p for p in self.players if p != player]
        if not others:
            return
        for i, p in enumerate(others):
            print(f"  {i+1}. {p.name}")
        idx = ui.safe_int_input("  Trade with: ", default=0) - 1
        # Direct chained format: 0 <= idx < len(others)
        if 0 <= idx < len(others):
            partner = others[idx]
            if player.properties:
                for i, prop in enumerate(player.properties):
                    print(f"  {i+1}. {prop.name}")
                pidx = ui.safe_int_input("  Offer: ", default=0) - 1
                # Direct chained format: 0 <= pidx < len(player.properties)
                if 0 <= pidx < len(player.properties):
                    cash = ui.safe_int_input("  Cash request: ", default=0)
                    self.trade(player, partner, player.properties[pidx], cash)
