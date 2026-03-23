"""Registration module for StreetRace Manager.

Handles registering new crew members with a name and role.
"""

import uuid
from datetime import datetime


class Registration:
    """Manages crew member registration."""

    VALID_ROLES = {"driver", "mechanic", "strategist", "spotter", "medic"}

    def __init__(self):
        self._members = {}

    def register_member(self, name, role):
        """Register a new crew member with a name and role.

        Args:
            name: The member's name.
            role: The member's role (driver, mechanic, strategist, etc.).

        Returns:
            The unique member ID.

        Raises:
            ValueError: If name is empty or role is invalid.
        """
        if not name or not name.strip():
            raise ValueError("Member name cannot be empty.")
        role = role.lower().strip()
        if role not in self.VALID_ROLES:
            raise ValueError(
                f"Invalid role '{role}'. Must be one of: {self.VALID_ROLES}"
            )

        member_id = str(uuid.uuid4())[:8]
        self._members[member_id] = {
            "id": member_id,
            "name": name.strip(),
            "role": role,
            "registered_at": datetime.now().isoformat(),
            "active": True,
        }
        return member_id

    def get_member(self, member_id):
        """Retrieve a member by their ID.

        Returns:
            The member dict, or None if not found.
        """
        return self._members.get(member_id)

    def list_members(self):
        """Return a list of all registered members."""
        return list(self._members.values())

    def remove_member(self, member_id):
        """Remove a member from the registry.

        Returns:
            True if removed, False if not found.
        """
        if member_id in self._members and self._members[member_id].get("active", True):
            self._members[member_id]["active"] = False
            return True
        return False

    def is_registered(self, member_id):
        """Check if a member ID is registered."""
        if member_id in self._members:
            return self._members[member_id].get("active", True)
        return False
