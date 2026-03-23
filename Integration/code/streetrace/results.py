"""Results module for StreetRace Manager.

Records race outcomes, calculates prize distribution, and updates rankings.
Depends on Race Management and Inventory modules.
"""


class Results:
    """Records and manages race results and prize distribution."""

    PRIZE_SPLIT = {1: 0.50, 2: 0.30, 3: 0.20}

    def __init__(self, race_management, inventory):
        """Initialize with references to dependent modules."""
        self._race_mgmt = race_management
        self._inventory = inventory
        self._results = {}  # race_id -> list of {driver_id, position}

    def record_result(self, race_id, rankings):
        """Record results for a completed race.

        Args:
            race_id: The race ID.
            rankings: List of driver IDs in finishing order (1st, 2nd, ...).

        Raises:
            ValueError: If race not found, not completed, or invalid rankings.
        """
        race = self._race_mgmt.get_race(race_id)
        if race is None:
            raise ValueError(f"Race '{race_id}' not found.")
        if race["status"] != "completed":
            raise ValueError(
                f"Race '{race_id}' is not completed. "
                "Complete the race before recording results."
            )

        entry_driver_ids = {e["driver_id"] for e in race["entries"]}
        for driver_id in rankings:
            if driver_id not in entry_driver_ids:
                raise ValueError(
                    f"Driver '{driver_id}' was not entered in race '{race_id}'."
                )

        self._results[race_id] = [
            {"driver_id": driver_id, "position": pos + 1}
            for pos, driver_id in enumerate(rankings)
        ]

    def get_race_results(self, race_id):
        """Return results for a race, or None if not recorded."""
        return self._results.get(race_id)

    def calculate_prize(self, race_id):
        """Distribute prize money based on recorded results.

        Prize split: 1st gets 50%, 2nd gets 30%, 3rd gets 20%.
        Updates the Inventory cash balance.

        Returns:
            Dict of {driver_id: prize_amount}.

        Raises:
            ValueError: If results not yet recorded.
        """
        results = self._results.get(race_id)
        if results is None:
            raise ValueError(
                f"No results recorded for race '{race_id}'."
            )

        race = self._race_mgmt.get_race(race_id)
        total_prize = race["prize_money"]
        payouts = {}

        for result in results:
            position = result["position"]
            driver_id = result["driver_id"]
            if position in self.PRIZE_SPLIT:
                prize = int(total_prize * self.PRIZE_SPLIT[position])
                payouts[driver_id] = prize
                self._inventory.add_cash(prize)

        return payouts

    def get_all_results(self):
        """Return all recorded results."""
        return dict(self._results)
