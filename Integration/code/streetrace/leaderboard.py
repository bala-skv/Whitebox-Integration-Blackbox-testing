"""Leaderboard module for StreetRace Manager (Custom Module 2).

Tracks season-wide driver standings, stats, and streaks.
Depends on Results and Registration modules.
"""


class Leaderboard:
    """Maintains season standings and driver statistics."""

    def __init__(self, registration):
        """Initialize with a reference to the Registration module."""
        self._registration = registration
        self._standings = {}  # driver_id -> {wins, podiums, races, points}

    def update_standings(self, race_results):
        """Update standings from a single race's results.

        Args:
            race_results: List of {driver_id, position} dicts.

        Points system: 1st=25, 2nd=18, 3rd=15, 4th=12, 5th=10, others=1.
        """
        points_table = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10}

        for result in race_results:
            driver_id = result["driver_id"]
            position = result["position"]

            if driver_id not in self._standings:
                self._standings[driver_id] = {
                    "wins": 0,
                    "podiums": 0,
                    "races": 0,
                    "points": 0,
                    "history": [],
                }

            stats = self._standings[driver_id]
            stats["races"] += 1
            stats["points"] += points_table.get(position, 1)
            stats["history"].append(position)

            if position == 1:
                stats["wins"] += 1
            if position <= 3:
                stats["podiums"] += 1

    def get_standings(self):
        """Return sorted standings (highest points first).

        Returns:
            List of (driver_id, stats_dict) sorted by points descending.
        """
        return sorted(
            self._standings.items(),
            key=lambda x: x[1]["points"],
            reverse=True,
        )

    def get_driver_stats(self, driver_id):
        """Return stats for a specific driver, or None if no races.

        Returns:
            Dict with wins, podiums, races, points, or None.
        """
        stats = self._standings.get(driver_id)
        if stats is None:
            return None

        member = self._registration.get_member(driver_id)
        name = member["name"] if member else "Unknown"
        return {
            "name": name,
            "wins": stats["wins"],
            "podiums": stats["podiums"],
            "races": stats["races"],
            "points": stats["points"],
        }

    def get_streak(self, driver_id):
        """Return the current streak info for a driver.

        Returns:
            Dict with streak_type ('win', 'podium', 'none') and count.
        """
        stats = self._standings.get(driver_id)
        if stats is None or not stats["history"]:
            return {"type": "none", "count": 0}

        history = stats["history"]
        # Check win streak from most recent
        win_streak = 0
        for pos in reversed(history):
            if pos == 1:
                win_streak += 1
            else:
                break

        if win_streak > 0:
            return {"type": "win", "count": win_streak}

        # Check podium streak
        podium_streak = 0
        for pos in reversed(history):
            if pos <= 3:
                podium_streak += 1
            else:
                break

        if podium_streak > 0:
            return {"type": "podium", "count": podium_streak}

        return {"type": "none", "count": 0}
