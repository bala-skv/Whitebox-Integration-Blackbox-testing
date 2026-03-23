"""Crew Management module for StreetRace Manager.

Manages crew member roles and skill levels.
Depends on Registration module for member validation.
"""


class CrewManagement:
    """Manages roles and skill levels for registered crew members."""

    def __init__(self, registration):
        """Initialize with a reference to the Registration module.

        Args:
            registration: A Registration instance.
        """
        self._registration = registration
        self._skills = {}  # member_id -> skill_level (1-10)

    def _validate_member(self, member_id):
        """Ensure member is registered. Raises ValueError if not."""
        if not self._registration.is_registered(member_id):
            raise ValueError(
                f"Member '{member_id}' is not registered. "
                "Register them first before assigning roles."
            )

    def assign_role(self, member_id, role):
        """Update a registered member's role.

        Args:
            member_id: The member's unique ID.
            role: The new role to assign.

        Raises:
            ValueError: If member not registered or role invalid.
        """
        self._validate_member(member_id)
        role = role.lower().strip()
        if role not in self._registration.VALID_ROLES:
            raise ValueError(
                f"Invalid role '{role}'. "
                f"Must be one of: {self._registration.VALID_ROLES}"
            )
        member = self._registration.get_member(member_id)
        member["role"] = role

    def set_skill_level(self, member_id, skill_level):
        """Set a crew member's skill level (1 to 10).

        Args:
            member_id: The member's unique ID.
            skill_level: Integer from 1 to 10.

        Raises:
            ValueError: If member not registered or skill out of range.
        """
        self._validate_member(member_id)
        if not isinstance(skill_level, int) or not 1 <= skill_level <= 10:
            raise ValueError("Skill level must be an integer between 1 and 10.")
        self._skills[member_id] = skill_level

    def get_skill_level(self, member_id):
        """Return the skill level of a member, or 1 if not set."""
        self._validate_member(member_id)
        return self._skills.get(member_id, 1)

    def get_drivers(self):
        """Return all members with the 'driver' role."""
        return self.get_by_role("driver")

    def get_mechanics(self):
        """Return all members with the 'mechanic' role."""
        return self.get_by_role("mechanic")

    def get_by_role(self, role):
        """Return all registered members matching the given role."""
        return [
            m for m in self._registration.list_members()
            if m["role"] == role.lower()
        ]

    def is_role(self, member_id, role):
        """Check if a specific member has the given role."""
        self._validate_member(member_id)
        member = self._registration.get_member(member_id)
        return member["role"] == role.lower()
