"""
Wandering Rare Merchant System for Green Valley Tales (Thương Nhân Du Mục Thần Bí).
Periodically visits the player's farm (weekends or lucky days).
Sells ultra-rare commodities (Ancient Seeds, Magic Fertilizer, Legendary Rod, Energy Elixirs).
Buys rare excavated artifacts & gemstones at premium bonus prices (+50% to +80%).
"""

import random
from src.settings import TILE_SIZE

class WanderingMerchant:
    def __init__(self):
        self.is_present = False
        # World position on farm (near river bank & pasture: col 16, row 12)
        self.col = 16
        self.row = 12
        self.carpet_rect = (self.col * TILE_SIZE, self.row * TILE_SIZE, TILE_SIZE * 2, TILE_SIZE * 2)
        
        # Dialogue responses
        self.greetings = [
            "Chào bạn trẻ! Ta là Lão Hạc - thương nhân chu du vạn dặm. Nay ghé chân mang tới bảo vật hiếm thấy!",
            "Gió lành đưa ta tới nông trại trù phú này! Xem qua những món hàng độc bản chỉ ta mới có nhé.",
            "Nghe đồn đất này ẩn giấu nhiều cổ vật quý xưa kia. Ngươi có đào được món gì lạ mắt không?"
        ]

    def check_daily_appearance(self, day, season_id, year):
        """
        Determines if merchant visits today.
        Spawns on days 5, 7, 12, 14, 19, 21, 26, 28 (every Friday & Sunday),
        or on a 30% chance for other days.
        """
        day_of_week = day % 7
        if day_of_week in [5, 0]:  # Friday & Sunday
            self.is_present = True
        else:
            rng = random.Random(year * 1000 + hash(season_id) % 100 + day)
            self.is_present = rng.random() < 0.35

        return self.is_present

    def get_rare_stock(self):
        """Returns catalogue of rare and legendary items for sale."""
        return [
            {
                "id": "ancient_seed",
                "category": "seed",
                "name": "Hạt giống Cổ Đại (Ancient Seed)",
                "price": 500,
                "desc": "Hạt giống ngàn năm! Trồng được 4 mùa, cho quả Hoàng Kim bán 1,200G.",
                "qty_stock": 3
            },
            {
                "id": "magic_fertilizer",
                "category": "supply",
                "name": "Phân bón Thần Tốc (Magic Fertilizer)",
                "price": 150,
                "desc": "Thần dược cho đất! Rút ngắn 50% thời gian lớn của cây trồng.",
                "qty_stock": 5
            },
            {
                "id": "legendary_rod",
                "category": "special",
                "name": "Cần câu Ngọc Bích (Legendary Rod)",
                "price": 2000,
                "desc": "Cần câu gia truyền của thần sông! Mở rộng thanh hứng cá x1.5.",
                "qty_stock": 1
            },
            {
                "id": "energy_elixir",
                "category": "consumable",
                "name": "Tiên Dược Sinh Lực (Energy Elixir)",
                "price": 120,
                "desc": "Uống vào hồi phục ngay lập tức 100% Thể Lực (Stamina).",
                "qty_stock": 4
            },
            {
                "id": "bag_voucher",
                "category": "special",
                "name": "Phiếu Mở Rộng Túi (Storage Voucher)",
                "price": 850,
                "desc": "Dùng mở thêm 8 ô túi đồ ngay lập tức mà không cần vật liệu.",
                "qty_stock": 1
            }
        ]

    def get_premium_buy_rate(self, item):
        """
        Calculates buying price for rare artifacts.
        Offers +60% to +80% higher than regular shipping bin price!
        """
        base_price = item.get("price", 10)
        item_id = item.get("id", "")
        item_type = item.get("type", "")

        # Rare artifacts list
        rare_items = [
            "mystic_geode", "gold_nugget", "ancient_amber", 
            "fossil_wood", "ancient_coin", "clay_relic", "golden_trout"
        ]

        if item_id in rare_items or item_type == "rare" or item.get("is_rare", False):
            # 1.7x premium price
            return int(base_price * 1.7)
        
        # Standard items bought at normal price
        return base_price

    def is_player_near(self, player_x, player_y):
        """Check if player is near the merchant stall."""
        if not self.is_present:
            return False
        cx = (self.col + 1) * TILE_SIZE
        cy = (self.row + 1) * TILE_SIZE
        dist_sq = (player_x - cx) ** 2 + (player_y - cy) ** 2
        return dist_sq < (TILE_SIZE * 3.5) ** 2
