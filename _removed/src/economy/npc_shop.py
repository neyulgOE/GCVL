"""
Town NPC Shop and Dynamic Haggling (Bargaining / Trả Giá) Engine for Green Valley Tales.
Enables 'Thuận mua vừa bán' with dynamic price negotiations, NPC patience/mood gauges,
and specialized inventories for Town Merchants (Cô Mai, Bác Bảy, Cụ Ba Tri).
"""

import random
from src.settings import CROPS_DATA

class HagglingLevel:
    CAUTIOUS = "cautious"    # 10% discount / 10% bonus (82% base success)
    CLEVER = "clever"        # 20% discount / 20% bonus (58% base success)
    AGGRESSIVE = "aggressive"# 35% discount / 35% bonus (28% base success)

class TownShopManager:
    def __init__(self):
        pass

    def get_npc_stock(self, npc_id, current_season_id):
        """Returns items available for sale from the specific NPC."""
        items = []

        if npc_id in ["co_mai", "thay_mo_kraa"]:
            # 1. Seasonal Seeds
            for crop_id, data in CROPS_DATA.items():
                valid_seasons = [data["season"]]
                if crop_id in ["wild_corn", "corn"]:
                    valid_seasons.append("fall")

                if current_season_id in valid_seasons:
                    items.append({
                        "id": crop_id,
                        "type": "seed",
                        "name": f"Hạt giống {data['name'].split(' (')[0]}",
                        "price": data["seed_cost"],
                        "desc": f"Lớn trong {data['grow_days']} ngày. Đổi: {data['sell_price']} 🐚.",
                        "qty": 5
                    })

            # 2. Quality Fertilizer
            items.append({
                "id": "fertilizer",
                "type": "supply",
                "name": "Thảo mộc kích mầm (Fertilizer)",
                "price": 30,
                "desc": "Tăng chất lượng nông sản dại và kích thích rễ phát triển nhanh.",
                "qty": 5
            })

        elif npc_id in ["bac_bay", "tho_san_boomer"]:
            items.append({
                "id": "copper_ore",
                "type": "material",
                "name": "Quặng đồng thô (Copper Ore)",
                "price": 25,
                "desc": "Khoáng sản dùng đúc dụng cụ và rèn rìu kim loại.",
                "qty": 3
            })
            items.append({
                "id": "flint",
                "type": "material",
                "name": "Đá lửa tuyển chọn (Flint)",
                "price": 10,
                "desc": "Mảnh đá lửa sắc bén dùng nhóm bếp và chế tác vũ khí.",
                "qty": 5
            })
            items.append({
                "id": "pebble",
                "type": "material",
                "name": "Đá cuội lòng suối",
                "price": 4,
                "desc": "Nguyên liệu ghè đẽo công cụ sơ khai.",
                "qty": 10
            })

        elif npc_id in ["cu_ba_tri", "toc_truong_ogg"]:
            items.append({
                "id": "bait",
                "type": "supply",
                "name": "Mồi câu ấu trùng thơm",
                "price": 8,
                "desc": "Giúp cá suối cắn câu nhanh gấp đôi khi quăng cần/giáo.",
                "qty": 10
            })
            items.append({
                "id": "cord",
                "type": "material",
                "name": "Dây bện gân dẻo dai",
                "price": 15,
                "desc": "Vật liệu thắt buộc dựng nhà và chế tạo cung giáo.",
                "qty": 5
            })
            items.append({
                "id": "hay",
                "type": "material",
                "name": "Bó cỏ khô thảo mộc (Herb Hay)",
                "price": 15,
                "desc": "Thức ăn bổ dưỡng cho gà mái và bò sữa.",
                "qty": 10
            })

        return items

    def get_player_sellable_items(self, inventory, npc_id):
        """Filters player's backpack and hotbar to items that this NPC is interested in buying."""
        sellable = []
        all_slots = [s for s in inventory.bag[:inventory.bag_capacity] if s] + [s for s in inventory.hotbar if s and s.get("type") != "tool"]
        for slot in all_slots:
            item_type = slot.get("type", "")
            item_id = slot.get("id", "")

            # Filter by NPC specialization
            can_buy = False
            bonus_rate = 1.0

            if npc_id == "co_mai":
                # Buys produce, crops, forage, eggs, milk
                if item_type in ["produce", "fruit", "crop"] or item_id in ["egg", "milk", "large_egg", "large_milk"]:
                    can_buy = True
                    bonus_rate = 1.15  # Cô Mai pays +15% for farm fresh produce!

            elif npc_id == "bac_bay":
                # Buys ores, minerals, stones, geodes, gold
                if item_type in ["material", "rare"] and item_id in ["stone", "gold_nugget", "mystic_geode", "copper_ore", "iron_ore"]:
                    can_buy = True
                    bonus_rate = 1.20  # Blacksmith pays +20% for raw ores & minerals!

            elif npc_id == "cu_ba_tri":
                # Buys fish, antiques, relics, clay pottery, ancient coins, amber, fossils
                if item_type in ["fish", "rare"] or item_id in ["ancient_coin", "clay_relic", "ancient_amber", "fossil_wood"]:
                    can_buy = True
                    bonus_rate = 1.25  # Mayor pays +25% for rare historical relics & prime fish!

            if can_buy:
                item_copy = dict(slot)
                item_copy["unit_price"] = int(slot.get("price", 10) * bonus_rate)
                sellable.append(item_copy)

        return sellable

    def attempt_bargain(self, npc, item, is_buying, haggle_level):
        """
        Executes a bargaining round.
        Returns:
            success: bool
            final_price: int
            message: str (NPC response text)
        """
        base_price = item.get("unit_price", item.get("price", 10))
        qty = item.get("qty", 1)
        total_base = base_price * (1 if is_buying else qty)

        # If patience exhausted
        if npc.patience <= 0:
            return False, total_base, npc.angry_quote

        # Haggling configurations
        if haggle_level == HagglingLevel.CAUTIOUS:
            percent = 0.10
            base_chance = 82
            patience_cost = 20
        elif haggle_level == HagglingLevel.CLEVER:
            percent = 0.20
            base_chance = 58
            patience_cost = 32
        else:  # AGGRESSIVE
            percent = 0.35
            base_chance = 28
            patience_cost = 45

        # Personality modifier
        if npc.personality == "friendly":
            base_chance += 10
        elif npc.personality == "gruff":
            base_chance -= 8
        elif npc.personality == "wise":
            base_chance += 5

        # Patience modifier: Low patience makes them grumpy
        if npc.patience < 50:
            base_chance -= 15

        roll = random.randint(1, 100)
        success = roll <= base_chance

        if success:
            if is_buying:
                # Player gets a discount
                final_price = max(1, int(total_base * (1.0 - percent)))
            else:
                # Player gets a bonus selling price
                final_price = int(total_base * (1.0 + percent))

            npc.friendship = min(100, npc.friendship + 1)
            response = random.choice(npc.success_quotes)
            return True, final_price, response
        else:
            npc.patience = max(0, npc.patience - patience_cost)
            if npc.patience <= 0:
                response = npc.angry_quote
            else:
                response = random.choice(npc.fail_quotes)
            return False, total_base, response
