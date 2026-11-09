"""
Inventory, Hotbar, Backpack, and Storage System for Stone Age: Dawn of Tribe.
- 8-slot active hotbar (on-screen)
- Upgradeable primitive pouch / backpack (Tab to open)
- Upgradeable woven basket / tribal storage cache (interact to open)
- Drag-and-drop between backpack and hotbar
- Currency: Vỏ Sò Cổ (Shells 🐚)
"""

from src.settings import (
    TOOL_HOE, TOOL_WATER_CAN, TOOL_AXE, TOOL_PICKAXE, 
    TOOL_SCYTHE, TOOL_FISHING_ROD, CURRENCY_ICON
)

# Upgrade tiers for Stone Age backpack: (required_gold/shells, required_materials, new_capacity)
BACKPACK_UPGRADES = [
    # Tier 0: 12 slots (starter)
    # Tier 1: 20 slots
    {"gold": 30, "materials": {"fiber": 10, "branch": 8}, "capacity": 20,
     "name": "Túi Da Thú Tiền Sử (Cấp 1)"},
    # Tier 2: 36 slots
    {"gold": 80, "materials": {"wood": 15, "cord": 6}, "capacity": 36,
     "name": "Gùi Mây Bộ Lạc (Cấp 2)"},
    # Tier 3: 48 slots
    {"gold": 160, "materials": {"wood": 30, "cord": 12}, "capacity": 48,
     "name": "Bao Da Thú Khổng Lồ (Cấp 3)"},
    # Tier 4: 64 slots (max)
    {"gold": 300, "materials": {"wood": 50, "pebble": 30}, "capacity": 64,
     "name": "Rương Chứa Đại Tộc (Cấp 4 Max)"},
]

# Upgrade tiers for storage cache
STORAGE_UPGRADES = [
    # Tier 0: 16 slots (starter woven basket)
    # Tier 1: 32 slots
    {"gold": 40, "materials": {"branch": 15, "fiber": 12}, "capacity": 32,
     "name": "Giỏ Mây Đan Kép (Cấp 1)"},
    # Tier 2: 50 slots
    {"gold": 100, "materials": {"wood": 25, "pebble": 15}, "capacity": 50,
     "name": "Hòm Đá Đẽo Đựng Đồ (Cấp 2)"},
    # Tier 3: 75 slots
    {"gold": 200, "materials": {"wood": 50, "clay": 20}, "capacity": 75,
     "name": "Kho Lương Vách Đất (Cấp 3)"},
    # Tier 4: 100 slots (max)
    {"gold": 400, "materials": {"wood": 80, "copper_bar": 5}, "capacity": 100,
     "name": "Đại Kho Trữ Lương Bộ Lạc (Cấp 4 Max)"},
]


class Inventory:
    HOTBAR_SLOTS = 8
    INITIAL_BAG_CAPACITY = 12
    MAX_BAG_CAPACITY = 64

    def __init__(self):
        # Hotbar: 8 slots for active use
        self.hotbar = [None] * self.HOTBAR_SLOTS
        # Backpack: starts at 12 slots, upgradeable to 64
        self.bag_capacity = self.INITIAL_BAG_CAPACITY
        self.bag_tier = 0  # 0..4
        self.bag = [None] * self.MAX_BAG_CAPACITY
        
        self.selected_index = 0  # Active hotbar slot (0..7)
        self.gold = 0  # Starts with 0 Shells

        self._init_starter_tools()

    def _init_starter_tools(self):
        """Place primitive starting items into inventory."""
        # Player starts in the wild with a sharp flint shard and wild berries
        self.hotbar[0] = {"type": "material", "id": "flint", "name": "Mảnh Đá Lửa Sắc (Flint)", "price": 8, "qty": 1}
        self.bag[0] = {"type": "food", "id": "berries", "name": "Quả Dâu Rừng (Wild Berries)", "price": 8, "stamina_restore": 15, "qty": 3}

    @property
    def slots(self):
        """Legacy accessor: returns hotbar slots for HUD compatibility."""
        return self.hotbar

    @property
    def active_item(self):
        return self.hotbar[self.selected_index]

    def set_active_slot(self, index):
        if 0 <= index < self.HOTBAR_SLOTS:
            self.selected_index = index

    def add_item(self, item_dict, qty=1):
        """Add item to inventory. Tries bag first, then hotbar."""
        item_id = item_dict["id"]
        is_tool = item_dict.get("type") == "tool"

        # 1. Try to stack with existing in hotbar
        if not is_tool:
            for slot in self.hotbar:
                if slot and slot["id"] == item_id:
                    slot["qty"] = slot.get("qty", 1) + qty
                    return True

            # 2. Try to stack with existing in bag
            for i in range(self.bag_capacity):
                slot = self.bag[i]
                if slot and slot["id"] == item_id:
                    slot["qty"] = slot.get("qty", 1) + qty
                    return True

        # 3. Find empty slot in bag first
        for i in range(self.bag_capacity):
            if self.bag[i] is None:
                new_item = dict(item_dict)
                if not is_tool:
                    new_item["qty"] = qty
                self.bag[i] = new_item
                return True

        # 4. Overflow to empty slot in hotbar
        for i in range(self.HOTBAR_SLOTS):
            if self.hotbar[i] is None:
                new_item = dict(item_dict)
                if not is_tool:
                    new_item["qty"] = qty
                self.hotbar[i] = new_item
                return True

        return False  # Inventory full!

    def remove_active_item(self, qty=1):
        """Removes quantity from active hotbar slot."""
        item = self.active_item
        if not item:
            return False

        if item.get("type") == "tool":
            self.hotbar[self.selected_index] = None
            return True

        cur_qty = item.get("qty", 1)
        if cur_qty <= qty:
            self.hotbar[self.selected_index] = None
        else:
            item["qty"] = cur_qty - qty
        return True

    def remove_item_by_id(self, item_id, qty=1):
        """Removes specified quantity of item across bag and hotbar."""
        remaining = qty
        # Search bag first
        for i in range(self.bag_capacity):
            slot = self.bag[i]
            if slot and slot["id"] == item_id:
                slot_qty = slot.get("qty", 1)
                take = min(remaining, slot_qty)
                slot["qty"] = slot_qty - take
                remaining -= take
                if slot["qty"] <= 0:
                    self.bag[i] = None
                if remaining <= 0:
                    return True

        # Then search hotbar
        for i in range(self.HOTBAR_SLOTS):
            slot = self.hotbar[i]
            if slot and slot["id"] == item_id:
                slot_qty = slot.get("qty", 1)
                take = min(remaining, slot_qty)
                slot["qty"] = slot_qty - take
                remaining -= take
                if slot["qty"] <= 0:
                    self.hotbar[i] = None
                if remaining <= 0:
                    return True

        return remaining <= 0

    def get_bag_upgrade_info(self):
        if self.bag_tier < len(BACKPACK_UPGRADES):
            return BACKPACK_UPGRADES[self.bag_tier]
        return None

    def can_upgrade_bag(self):
        if self.bag_tier >= len(BACKPACK_UPGRADES):
            return False, "Đã nâng cấp túi tối đa!"
        tier_data = BACKPACK_UPGRADES[self.bag_tier]
        if self.gold < tier_data["gold"]:
            return False, f"Thiếu vỏ sò ({self.gold}/{tier_data['gold']} {CURRENCY_ICON})"
        for mat_id, req_qty in tier_data["materials"].items():
            cur = self.count_item(mat_id)
            if cur < req_qty:
                return False, f"Thiếu {mat_id} ({cur}/{req_qty})"
        return True, "Có thể nâng cấp"

    def upgrade_bag(self):
        can, reason = self.can_upgrade_bag()
        if not can:
            return False, reason
        tier_data = BACKPACK_UPGRADES[self.bag_tier]
        self.gold -= tier_data["gold"]
        for mat_id, req_qty in tier_data["materials"].items():
            self.remove_item_by_id(mat_id, req_qty)
        self.bag_capacity = tier_data["capacity"]
        self.bag_tier += 1
        return True, f"Đã nâng cấp lên {tier_data['name']} ({tier_data['capacity']} ô)!"

    def count_item(self, item_id):
        count = 0
        for slot in self.hotbar:
            if slot and slot["id"] == item_id:
                count += slot.get("qty", 1)
        for i in range(self.bag_capacity):
            slot = self.bag[i]
            if slot and slot["id"] == item_id:
                count += slot.get("qty", 1)
        return count

    get_item_count = count_item

    def to_dict(self):
        return {
            "hotbar": self.hotbar,
            "bag": self.bag[:self.bag_capacity],
            "bag_capacity": self.bag_capacity,
            "bag_tier": self.bag_tier,
            "gold": self.gold,
            "selected_index": self.selected_index
        }

    def from_dict(self, data):
        if not data:
            return
        self.hotbar = data.get("hotbar", [None] * self.HOTBAR_SLOTS)
        loaded_bag = data.get("bag", [])
        self.bag = [None] * self.MAX_BAG_CAPACITY
        for i, item in enumerate(loaded_bag):
            if i < self.MAX_BAG_CAPACITY:
                self.bag[i] = item
        self.bag_capacity = data.get("bag_capacity", self.INITIAL_BAG_CAPACITY)
        self.bag_tier = data.get("bag_tier", 0)
        self.gold = data.get("gold", 0)
        self.selected_index = data.get("selected_index", 0)


class StorageChest:
    INITIAL_CAPACITY = 16
    MAX_CAPACITY = 100

    def __init__(self):
        self.capacity = self.INITIAL_CAPACITY
        self.tier = 0
        self.slots = [None] * self.MAX_CAPACITY

    def get_upgrade_info(self):
        if self.tier < len(STORAGE_UPGRADES):
            return STORAGE_UPGRADES[self.tier]
        return None

    def can_upgrade(self, inventory):
        if self.tier >= len(STORAGE_UPGRADES):
            return False, "Đã nâng cấp tối đa!"
        tier_data = STORAGE_UPGRADES[self.tier]
        if inventory.gold < tier_data["gold"]:
            return False, f"Thiếu vỏ sò ({inventory.gold}/{tier_data['gold']})"
        for mat_id, req_qty in tier_data["materials"].items():
            cur = inventory.count_item(mat_id)
            if cur < req_qty:
                return False, f"Thiếu {mat_id} ({cur}/{req_qty})"
        return True, "Có thể nâng cấp"

    def upgrade(self, inventory):
        can, reason = self.can_upgrade(inventory)
        if not can:
            return False, reason
        tier_data = STORAGE_UPGRADES[self.tier]
        inventory.gold -= tier_data["gold"]
        for mat_id, req_qty in tier_data["materials"].items():
            inventory.remove_item_by_id(mat_id, req_qty)
        self.capacity = tier_data["capacity"]
        self.tier += 1
        return True, f"Đã nâng cấp lên {tier_data['name']} ({tier_data['capacity']} ô)!"

    def to_dict(self):
        return {
            "capacity": self.capacity,
            "tier": self.tier,
            "slots": self.slots[:self.capacity]
        }

    def from_dict(self, data):
        if not data:
            return
        self.capacity = data.get("capacity", self.INITIAL_CAPACITY)
        self.tier = data.get("tier", 0)
        loaded_slots = data.get("slots", [])
        self.slots = [None] * self.MAX_CAPACITY
        for i, item in enumerate(loaded_slots):
            if i < self.MAX_CAPACITY:
                self.slots[i] = item
