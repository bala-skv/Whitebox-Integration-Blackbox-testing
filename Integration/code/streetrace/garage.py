"""Garage module for StreetRace Manager (Custom Module 1).

Handles car repair, maintenance, and upgrades.
Depends on Inventory and Crew Management modules.
"""


class Garage:
    """Manages car repairs and upgrades using crew mechanics and parts."""

    REPAIR_COST = 500

    def __init__(self, inventory, crew_management):
        """Initialize with references to dependent modules."""
        self._inventory = inventory
        self._crew = crew_management
        self._repair_queue = {}  # car_id -> mechanic_id

    def schedule_repair(self, car_id, mechanic_id):
        """Schedule a car repair with a mechanic.

        Business rules:
            - Car must exist and be damaged.
            - Assigned member must have the 'mechanic' role.

        Args:
            car_id: The car to repair.
            mechanic_id: The mechanic performing the repair.

        Raises:
            ValueError: If car not damaged or member is not a mechanic.
        """
        car = self._inventory.get_car(car_id)
        if car is None:
            raise ValueError(f"Car '{car_id}' not found.")
        if not car["is_damaged"]:
            raise ValueError(f"Car '{car_id}' is not damaged.")

        if not self._crew.is_role(mechanic_id, "mechanic"):
            raise ValueError(
                f"Member '{mechanic_id}' is not a mechanic. "
                "Only mechanics can perform repairs."
            )

        self._repair_queue[car_id] = mechanic_id

    def complete_repair(self, car_id):
        """Complete a scheduled repair.

        Repairs the car, charges the repair cost from inventory cash.

        Raises:
            ValueError: If no repair is scheduled or insufficient funds.
        """
        if car_id not in self._repair_queue:
            raise ValueError(
                f"No repair scheduled for car '{car_id}'."
            )

        self._inventory.deduct_cash(self.REPAIR_COST)
        self._inventory.repair_car(car_id)
        del self._repair_queue[car_id]

    def upgrade_car(self, car_id, part_name, speed_boost=10):
        """Upgrade a car using a spare part from inventory.

        Args:
            car_id: The car to upgrade.
            part_name: The part to use from inventory.
            speed_boost: How much to increase top_speed.

        Raises:
            ValueError: If car not found, part not in stock, or car is damaged.
        """
        car = self._inventory.get_car(car_id)
        if car is None:
            raise ValueError(f"Car '{car_id}' not found.")
        if car["is_damaged"]:
            raise ValueError(
                f"Car '{car_id}' is damaged. Repair it before upgrading."
            )

        self._inventory.use_part(part_name, 1)
        car["top_speed"] += speed_boost

    def get_repair_status(self, car_id):
        """Check if a car has a repair scheduled.

        Returns:
            The mechanic ID if scheduled, None otherwise.
        """
        return self._repair_queue.get(car_id)
