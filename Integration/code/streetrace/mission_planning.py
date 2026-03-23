"""Mission Planning module for StreetRace Manager.

Assigns missions and verifies required crew roles are available.
Depends on Registration and Crew Management modules.
"""

import uuid


class MissionPlanning:
    """Creates and manages missions with role-based crew requirements."""

    MISSION_TYPES = {"delivery", "rescue", "escort", "sabotage", "recon"}

    def __init__(self, registration, crew_management):
        """Initialize with references to dependent modules."""
        self._registration = registration
        self._crew = crew_management
        self._missions = {}

    def create_mission(self, name, mission_type, required_roles):
        """Create a new mission with required crew roles.

        Args:
            name: Mission name.
            mission_type: Type of mission (delivery, rescue, etc.).
            required_roles: List of role strings needed for the mission.

        Returns:
            The unique mission ID.

        Raises:
            ValueError: If mission type is invalid or no roles specified.
        """
        mission_type = mission_type.lower().strip()
        if mission_type not in self.MISSION_TYPES:
            raise ValueError(
                f"Invalid mission type '{mission_type}'. "
                f"Must be one of: {self.MISSION_TYPES}"
            )
        if not required_roles:
            raise ValueError("At least one required role must be specified.")

        mission_id = str(uuid.uuid4())[:8]
        self._missions[mission_id] = {
            "id": mission_id,
            "name": name,
            "type": mission_type,
            "required_roles": [r.lower() for r in required_roles],
            "assigned_members": [],
            "status": "pending",  # pending, active, completed
        }
        return mission_id

    def assign_mission(self, mission_id, member_ids):
        """Assign crew members to a mission.

        Validates that:
            - All members are registered.
            - The assigned members collectively cover all required roles.

        Args:
            mission_id: The mission to assign to.
            member_ids: List of member IDs to assign.

        Raises:
            ValueError: If mission not found, already active, or roles not met.
        """
        mission = self._get_mission_or_error(mission_id)
        if mission["status"] != "pending":
            raise ValueError(
                f"Mission '{mission_id}' is not in pending status."
            )

        # Validate all members are registered
        for mid in member_ids:
            if not self._registration.is_registered(mid):
                raise ValueError(f"Member '{mid}' is not registered.")

        # Check that required roles are covered (accounting for quantities)
        required_roles = mission["required_roles"].copy()
        
        for mid in member_ids:
            member = self._registration.get_member(mid)
            role = member["role"]
            if role in required_roles:
                required_roles.remove(role)

        if required_roles:
            raise ValueError(
                f"Mission requires roles not covered: {required_roles}. "
                "Cannot start mission without all required roles."
            )

        mission["assigned_members"] = list(member_ids)
        mission["status"] = "active"

    def complete_mission(self, mission_id):
        """Mark a mission as completed.

        Raises:
            ValueError: If mission not found or not active.
        """
        mission = self._get_mission_or_error(mission_id)
        if mission["status"] != "active":
            raise ValueError(
                f"Mission '{mission_id}' is not active."
            )
        mission["status"] = "completed"

    def get_mission(self, mission_id):
        """Retrieve mission details, or None if not found."""
        return self._missions.get(mission_id)

    def list_missions(self):
        """Return all missions."""
        return list(self._missions.values())

    def _get_mission_or_error(self, mission_id):
        """Return mission dict or raise ValueError."""
        mission = self._missions.get(mission_id)
        if mission is None:
            raise ValueError(f"Mission '{mission_id}' not found.")
        return mission
