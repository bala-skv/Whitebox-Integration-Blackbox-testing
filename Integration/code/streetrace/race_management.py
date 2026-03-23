"""Race Management module for StreetRace Manager.

Creates races and validates driver/car entries.
Depends on Registration, Crew Management, and Inventory modules.
"""

import uuid
import random


class RaceManagement:
    """Manages race creation and entry validation."""

    def __init__(self, registration, crew_management, inventory):
        """Initialize with references to dependent modules."""
        self._registration = registration
        self._crew = crew_management
        self._inventory = inventory
        self._races = {}

    def create_race(self, name, prize_money=1000):
        """Create a new race.

        Args:
            name: Race name.
            prize_money: Total prize pool.

        Returns:
            The unique race ID.
        """
        if prize_money < 0:
            raise ValueError("Prize money cannot be negative.")

        race_id = str(uuid.uuid4())[:8]
        self._races[race_id] = {
            "id": race_id,
            "name": name,
            "prize_money": prize_money,
            "entries": [],  # list of {driver_id, car_id}
            "status": "open",  # open, in_progress, completed
        }
        return race_id

    def enter_race(self, race_id, driver_id, car_id):
        """Enter a driver and car into a race.

        Business rules:
            - Race must exist and be open.
            - Driver must be registered.
            - Driver must have the 'driver' role.
            - Car must exist and not be damaged.

        Raises:
            ValueError: If any validation fails.
        """
        race = self._get_race_or_error(race_id)
        if race["status"] != "open":
            raise ValueError(f"Race '{race_id}' is not open for entries.")

        # Validate driver
        if not self._registration.is_registered(driver_id):
            raise ValueError(
                f"Driver '{driver_id}' is not registered."
            )
        if not self._crew.is_role(driver_id, "driver"):
            raise ValueError(
                f"Member '{driver_id}' does not have the 'driver' role."
            )

        # Validate car
        if not self._inventory.is_car_available(car_id):
            raise ValueError(
                f"Car '{car_id}' is not available (damaged or not found)."
            )

        # Check for duplicate entries across all active races
        for r_id, other_race in self._races.items():
            if other_race["status"] in ("open", "in_progress"):
                for entry in other_race["entries"]:
                    if entry["driver_id"] == driver_id:
                        raise ValueError(
                            f"Driver '{driver_id}' is already entered in an active race."
                        )
                    if entry["car_id"] == car_id:
                        raise ValueError(
                            f"Car '{car_id}' is already entered in an active race."
                        )

        race["entries"].append({
            "driver_id": driver_id,
            "car_id": car_id,
        })

    def start_race(self, race_id):
        """Start a race (mark as in_progress).

        Raises:
            ValueError: If race not found, not open, or has no entries.
        """
        race = self._get_race_or_error(race_id)
        if race["status"] != "open":
            raise ValueError(f"Race '{race_id}' is not open.")
        if len(race["entries"]) < 1:
            raise ValueError(f"Race '{race_id}' has no entries.")
        race["status"] = "in_progress"

    def complete_race(self, race_id):
        """Mark a race as completed.

        Each car has a 50% chance of getting damaged during the race.

        Returns:
            List of car IDs that were damaged during the race.

        Raises:
            ValueError: If race not found or not in progress.
        """
        race = self._get_race_or_error(race_id)
        if race["status"] != "in_progress":
            raise ValueError(f"Race '{race_id}' is not in progress.")
        race["status"] = "completed"

        # 50% damage probability for each car
        damaged_cars = []
        for entry in race["entries"]:
            if random.random() < 0.5:
                car_id = entry["car_id"]
                self._inventory.damage_car(car_id)
                damaged_cars.append(car_id)

        return damaged_cars

    def get_race(self, race_id):
        """Retrieve race details, or None if not found."""
        return self._races.get(race_id)

    def list_races(self):
        """Return all races."""
        return list(self._races.values())

    def _get_race_or_error(self, race_id):
        """Return the race dict or raise ValueError."""
        race = self._races.get(race_id)
        if race is None:
            raise ValueError(f"Race '{race_id}' not found.")
        return race
