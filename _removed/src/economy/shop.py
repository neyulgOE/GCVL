"""
Merchant and Village Seed Shop System for Green Valley Tales.
Offers seasonal seeds, livestock (chickens, cows), and farm supplies.
"""

from src.settings import CROPS_DATA, ANIMAL_DATA

class Shop:
    def __init__(self):
        self.is_open = False
        self.selected_index = 0

    def get_available_items(self, current_season_id):
        """Returns catalogue of items available for sale in current season."""
        items = []

        # 1. Seasonal Seeds
        for crop_id, data in CROPS_DATA.items():
            valid_seasons = [data["season"]]
            if crop_id in ["wild_corn", "corn"]:
                valid_seasons.append("fall")

            if current_season_id in valid_seasons:
                items.append({
                    "category": "seed",
                    "id": crop_id,
                    "name": f"Hạt giống {data['name'].split(' (')[0]}",
                    "price": data["seed_cost"],
                    "desc": f"Lớn trong {data['grow_days']} ngày. Đổi: {data['sell_price']} 🐚"
                })

        # 2. Livestock
        for anim_id, data in ANIMAL_DATA.items():
            items.append({
                "category": "animal",
                "id": anim_id,
                "name": data["name"],
                "price": data["cost"],
                "desc": f"Cho {data['product_name']}. Cần cho ăn & vuốt ve."
            })

        # 3. Supplies
        items.append({
            "category": "supply",
            "id": "hay",
            "name": "Bó rơm khô (Hay)",
            "price": 15,
            "desc": "Thức ăn chất lượng cho gia súc vào mùa đông hoặc ngày mưa."
        })

        return items

    def buy_item(self, item, inventory, animals_manager, farm_map):
        """Execute purchase."""
        price = item["price"]
        if inventory.gold < price:
            return False, "Không đủ tiền vàng (G)!"

        cat = item["category"]
        if cat == "seed":
            seed_dict = {
                "type": "seed",
                "id": item["id"],
                "name": item["name"],
                "qty": 5
            }
            if inventory.add_item(seed_dict, qty=5):
                inventory.gold -= price
                return True, f"Đã mua 5x {item['name']}!"
            else:
                return False, "Túi đồ đã đầy!"

        elif cat == "animal":
            anim_type = item["id"]
            inventory.gold -= price
            # Spawn animal in farm pasture near barn
            animals_manager.add_animal(anim_type)
            return True, f"Chúc mừng! Bạn đã mua 1 {item['name']}!"

        elif cat == "supply":
            supply_dict = {
                "type": "material",
                "id": item["id"],
                "name": item["name"],
                "price": 10,
                "qty": 10
            }
            if inventory.add_item(supply_dict, qty=10):
                inventory.gold -= price
                return True, f"Đã mua 10x {item['name']}!"
            else:
                return False, "Túi đồ đã đầy!"

        return False, "Lỗi giao dịch"
