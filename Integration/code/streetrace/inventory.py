"""Inventory module for StreetRace Manager.

Tracks cars, spare parts, tools, and the crew's cash balance.
"""

import uuid


class Inventory:
    """Manages the crew's inventory: cars, parts, tools, and cash."""

    def __init__(self, starting_cash=10000):
        self._cars = {}
        self._parts = {}  # part_name -> quantity
        self._tools = {}  # tool_name -> quantity
        self._cash = starting_cash

    # ---- Cash management ----

    def get_cash(self):
        """Return the current cash balance."""
        return self._cash

    def add_cash(self, amount):
        """Add cash to the balance.

        Raises:
            ValueError: If amount is not positive.
        """
        if amount <= 0:
            raise ValueError("Amount must be positive.")
        self._cash += amount

    def deduct_cash(self, amount):
        """Deduct cash from the balance.

        Raises:
            ValueError: If amount is not positive or exceeds balance.
        """
        if amount <= 0:
            raise ValueError("Amount must be positive.")
        if amount > self._cash:
            raise ValueError(
                f"Insufficient funds: need ${amount}, have ${self._cash}."
            )
        self._cash -= amount

    # ---- Car management ----

    def add_car(self, name, top_speed=200, condition=100):
        """Add a new car to the inventory.

        Args:
            name: Car name/model.
            top_speed: Maximum speed.
            condition: 0-100 condition rating.

        Returns:
            The unique car ID.
        """
        car_id = str(uuid.uuid4())[:8]
        self._cars[car_id] = {
            "id": car_id,
            "name": name,
            "top_speed": top_speed,
            "condition": condition,
            "is_damaged": False,
        }
        return car_id

    def get_car(self, car_id):
        """Retrieve a car by ID, or None if not found."""
        return self._cars.get(car_id)

    def list_cars(self):
        """Return all cars."""
        return list(self._cars.values())

    def list_available_cars(self):
        """Return only undamaged cars."""
        return [c for c in self._cars.values() if not c["is_damaged"]]

    def damage_car(self, car_id):
        """Mark a car as damaged.

        Raises:
            ValueError: If car not found.
        """
        car = self.get_car(car_id)
        if car is None:
            raise ValueError(f"Car '{car_id}' not found.")
        car["is_damaged"] = True
        car["condition"] = max(0, car["condition"] - 30)

    def repair_car(self, car_id):
        """Mark a car as repaired (undamaged).

        Raises:
            ValueError: If car not found.
        """
        car = self.get_car(car_id)
        if car is None:
            raise ValueError(f"Car '{car_id}' not found.")
        car["is_damaged"] = False
        car["condition"] = 100

    def is_car_available(self, car_id):
        """Check if a car exists and is not damaged."""
        car = self.get_car(car_id)
        return car is not None and not car["is_damaged"]

    # ---- Parts management ----

    def add_part(self, name, quantity=1):
        """Add spare parts to inventory.

        Raises:
            ValueError: If quantity is not positive.
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")
        self._parts[name] = self._parts.get(name, 0) + quantity

    def use_part(self, name, quantity=1):
        """Consume spare parts from inventory.

        Raises:
            ValueError: If not enough parts available.
        """
        available = self._parts.get(name, 0)
        if available < quantity:
            raise ValueError(
                f"Not enough '{name}': need {quantity}, have {available}."
            )
        self._parts[name] -= quantity

    def get_part_count(self, name):
        """Return how many of the named part are in stock."""
        return self._parts.get(name, 0)

    # ---- Tools management ----

    def add_tool(self, name, quantity=1):
        """Add tools to inventory.

        Raises:
            ValueError: If quantity is not positive.
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")
        self._tools[name] = self._tools.get(name, 0) + quantity

    def get_tool_count(self, name):
        """Return how many of the named tool are in stock."""
        return self._tools.get(name, 0)
