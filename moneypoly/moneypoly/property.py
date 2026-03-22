"""Module for managing property tiles and groups."""
class Property:
    """Represents a purchasable property tile on the MoneyPoly board."""

    FULL_GROUP_MULTIPLIER = 2

    def __init__(self, name, position, pricing, group=None):
        """Pricing is a dict: {'price': X, 'rent': Y}."""
        self.name = name
        self.position = position
        self.group = group
        self.owner = None
        self.houses = 0
        # Grouped into a finance dict to resolve R0902
        self.finance = {
            "price": pricing["price"],
            "base_rent": pricing["rent"],
            "mortgage_value": pricing["price"] // 2,
            "is_mortgaged": False
        }

        if group is not None and self not in group.properties:
            group.properties.append(self)
    def get_rent(self):
        """Return the rent owed; returns 0 if the property is mortgaged."""
        if self.finance["is_mortgaged"]: # Updated 
            return 0
        if self.group is not None and self.group.all_owned_by(self.owner):
            return self.finance["base_rent"] * self.FULL_GROUP_MULTIPLIER # Updated 
        return self.finance["base_rent"] # Updated 

    def mortgage(self):
        """Mortgage the property and return the payout."""
        if self.finance["is_mortgaged"]: # Updated 
            return 0
        self.finance["is_mortgaged"] = True # Updated 
        return self.finance["mortgage_value"] # Updated 

    def unmortgage(self):
        """Lift the mortgage and return the cost."""
        if not self.finance["is_mortgaged"]: # Updated 
            return 0
        cost = int(self.finance["mortgage_value"] * 1.1) # Updated 
        self.finance["is_mortgaged"] = False # Updated 
        return cost

    def is_available(self):
        """Return True if unowned and not mortgaged."""
        return self.owner is None and not self.finance["is_mortgaged"] # Updated
    def __repr__(self):
        owner_name = self.owner.name if self.owner else "unowned"
        return f"Property({self.name!r}, pos={self.position}, owner={owner_name!r})"


class PropertyGroup:
    """A group of properties of the same color."""
    def __init__(self, name, color):
        self.name = name
        self.color = color
        self.properties = []

    def add_property(self, prop):
        """Add a Property to this group and back-link it."""
        if prop not in self.properties:
            self.properties.append(prop)
            prop.group = self

    def all_owned_by(self, player):
        """Return True if every property in this group is owned by `player`."""
        if player is None:
            return False
        return any(p.owner == player for p in self.properties)

    def get_owner_counts(self):
        """Return a dict mapping each owner to how many properties they hold in this group."""
        counts = {}
        for prop in self.properties:
            if prop.owner is not None:
                counts[prop.owner] = counts.get(prop.owner, 0) + 1
        return counts

    def size(self):
        """Return the number of properties in this group."""
        return len(self.properties)

    def __repr__(self):
        return f"PropertyGroup({self.name!r}, {len(self.properties)} properties)"
