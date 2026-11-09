"""
Shipping Bin Economy System for Green Valley Tales.
Allows players to deposit harvested goods, fish, and materials.
Calculates overnight earnings broken down by category.
"""

class ShippingBin:
    def __init__(self):
        self.items = []

    def deposit(self, item_dict, qty=1):
        """Add item into the shipping bin."""
        if item_dict.get("type") == "tool":
            return False  # cannot sell tools

        # Stack if possible
        for it in self.items:
            if it["id"] == item_dict["id"]:
                it["qty"] += qty
                return True

        new_entry = dict(item_dict)
        new_entry["qty"] = qty
        self.items.append(new_entry)
        return True

    def calculate_overnight_earnings(self):
        """
        Process all shipped items and return detailed ledger breakdown.
        """
        breakdown = {
            "crops": 0,
            "fish": 0,
            "animals": 0,
            "materials": 0,
            "total": 0,
            "items_sold": []
        }

        for item in self.items:
            unit_price = item.get("price", 10)
            qty = item.get("qty", 1)
            revenue = unit_price * qty
            item_type = item.get("type", "material")

            if item_type == "crop":
                breakdown["crops"] += revenue
            elif item_type == "fish":
                breakdown["fish"] += revenue
            elif item_type == "animal_product":
                breakdown["animals"] += revenue
            else:
                breakdown["materials"] += revenue

            breakdown["total"] += revenue
            breakdown["items_sold"].append({
                "name": item.get("name", "Vật phẩm"),
                "qty": qty,
                "revenue": revenue
            })

        # Empty bin for the new day
        self.items.clear()
        return breakdown

    def to_dict(self):
        return {"items": self.items}

    def from_dict(self, data):
        self.items = data.get("items", [])
