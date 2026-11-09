"""
Era Quest & Progression System for Stone Age: Dawn of Tribe.
Coordinates 12 major milestones across 3 prehistoric eras:
- Paleolithic (Thời Đồ Đá Cũ)
- Neolithic (Thời Đồ Đá Mới)
- Bronze Age (Thời Đồ Đồng & Hưng Thịnh Bộ Lạc)
Tracks progress, awards shells & blueprints, triggers era evolution celebrations.
"""

from src.settings import ERA_PALEOLITHIC, ERA_NEOLITHIC, ERA_BRONZE, ERAS_DATA

QUESTS = [
    # -------------------------------------------------------------
    # ERA 1: PALEOLITHIC (THỜI ĐỒ ĐÁ CŨ)
    # -------------------------------------------------------------
    {
        "id": "q1_forage",
        "era": ERA_PALEOLITHIC,
        "title": "1. Thu Lượm Sơ Khai",
        "desc": "Đi dạo quanh thung lũng, nhặt ít nhất 5 Cành Cây Khô và 3 Hòn Đá Cuội ven bờ suối.",
        "requirements": {"branch": 5, "pebble": 3},
        "reward_shells": 20,
        "reward_items": [{"id": "fiber", "type": "material", "name": "Sợi Cỏ Dại", "price": 4, "qty": 3}],
        "reward_desc": "+20 🐚 Vỏ Sò & 3x Sợi Cỏ Dại"
    },
    {
        "id": "q2_craft_axe",
        "era": ERA_PALEOLITHIC,
        "title": "2. Đẽo Đá Thành Rìu",
        "desc": "Mở Menu Chế Tác [Phím C] và chế tạo chiếc Rìu Đá Thô Sơ đầu tiên.",
        "requirement_type": "has_tool",
        "target_tool": "primitive_axe",
        "reward_shells": 30,
        "reward_items": [{"id": "flint", "type": "material", "name": "Đá Lửa", "price": 8, "qty": 2}],
        "reward_desc": "+30 🐚 Vỏ Sò & 2x Đá Lửa"
    },
    {
        "id": "q3_campfire",
        "era": ERA_PALEOLITHIC,
        "title": "3. Ngọn Lửa Sinh Tồn",
        "desc": "Đốn cây lấy gỗ và nhóm Đống Lửa Trại đầu tiên để sưởi ấm và nấu nướng.",
        "requirement_type": "structure_level",
        "target_structure": "campfire",
        "target_level": 1,
        "reward_shells": 40,
        "reward_items": [{"id": "primitive_spear", "tool_type": "fishing_rod", "type": "tool", "name": "Giáo Xiên Cá Thô Sơ", "power": 1}],
        "reward_desc": "+40 🐚 Vỏ Sò & 1x Giáo Xiên Cá Thô Sơ"
    },
    {
        "id": "q4_cook_food",
        "era": ERA_PALEOLITHIC,
        "title": "4. Bữa Ăn Nóng Đầu Tiên",
        "desc": "Bắt 1 con cá dưới suối (hoặc đào củ rừng), lại gần Đống Lửa Trại [Phím E] để nướng chín.",
        "requirement_type": "has_item_category",
        "target_category": "food",
        "reward_shells": 50,
        "reward_items": [{"id": "wild_roots", "type": "seed", "name": "Hạt Củ Dại Đầm Lầy", "qty": 5}],
        "reward_desc": "+50 🐚 Vỏ Sò & 5x Hạt Củ Dại"
    },
    {
        "id": "q5_shelter",
        "era": ERA_PALEOLITHIC,
        "title": "5. Mái Ấm Tiền Sử",
        "desc": "Thu thập cành lá và dựng Chòi Lá Trú Ẩn để ngủ qua đêm an toàn.",
        "requirement_type": "structure_level",
        "target_structure": "shelter",
        "target_level": 1,
        "reward_shells": 80,
        "unlocks_era": ERA_NEOLITHIC,
        "reward_desc": "+80 🐚 Vỏ Sò & 🌟 MỞ KHÓA THỜI ĐỒ ĐÁ MỚI!"
    },

    # -------------------------------------------------------------
    # ERA 2: NEOLITHIC (THỜI ĐỒ ĐÁ MỚI)
    # -------------------------------------------------------------
    {
        "id": "q6_agriculture",
        "era": ERA_NEOLITHIC,
        "title": "6. Khai Mở Nông Nghiệp",
        "desc": "Chế tạo Gậy bới đất hoặc Cuốc đá mài, xới đất và gieo luống hạt giống dại đầu tiên.",
        "requirement_type": "tilled_or_planted",
        "reward_shells": 60,
        "reward_items": [{"id": "wild_wheat", "type": "seed", "name": "Hạt Lúa Mì Nguyên Thủy", "qty": 5}],
        "reward_desc": "+60 🐚 Vỏ Sò & 5x Hạt Lúa Mì"
    },
    {
        "id": "q7_clay_kiln",
        "era": ERA_NEOLITHIC,
        "title": "7. Nghệ Thuật Đất Nung",
        "desc": "Đào đất sét bên bờ suối và xây dựng Lò Nung Đất Sét để nung gốm và luyện kim.",
        "requirement_type": "structure_level",
        "target_structure": "clay_kiln",
        "target_level": 1,
        "reward_shells": 90,
        "reward_items": [{"id": "clay_jug", "tool_type": "water_can", "type": "tool", "name": "Bình Gốm Nung Múc Nước", "water": 35, "max_water": 35, "power": 2}],
        "reward_desc": "+90 🐚 Vỏ Sò & 1x Bình Gốm Nung"
    },
    {
        "id": "q8_harvest",
        "era": ERA_NEOLITHIC,
        "title": "8. Vụ Mùa Đầu Tiên",
        "desc": "Tưới nước chăm sóc và thu hoạch mẻ nông sản đầu tiên từ cánh đồng tiền sử.",
        "requirement_type": "has_harvested",
        "reward_shells": 120,
        "reward_items": [{"id": "cord", "type": "material", "name": "Dây Bện Cỏ", "price": 10, "qty": 4}],
        "reward_desc": "+120 🐚 Vỏ Sò & 4x Dây Bện Cỏ"
    },
    {
        "id": "q9_fur_tent",
        "era": ERA_NEOLITHIC,
        "title": "9. Định Cư Vững Chắc",
        "desc": "Nâng cấp căn cứ lên Lều Da Thú (Cấp 2) bằng cọc gỗ và da thú ấm áp.",
        "requirement_type": "structure_level",
        "target_structure": "shelter",
        "target_level": 2,
        "reward_shells": 150,
        "unlocks_era": ERA_BRONZE,
        "reward_desc": "+150 🐚 Vỏ Sò & 🌟 MỞ KHÓA THỜI ĐỒ ĐỒNG!"
    },

    # -------------------------------------------------------------
    # ERA 3: BRONZE AGE (THỜI ĐỒ ĐỒNG & HƯNG THỊNH BỘ LẠC)
    # -------------------------------------------------------------
    {
        "id": "q10_copper_bar",
        "era": ERA_BRONZE,
        "title": "10. Khai Khoáng Kim Khí",
        "desc": "Đập đá tìm Quặng Đồng và nung đúc thành Thỏi Đồng nguyên chất tại Lò Nung.",
        "requirements": {"copper_bar": 1},
        "reward_shells": 180,
        "reward_items": [{"id": "copper_bar", "type": "material", "name": "Thỏi Đồng", "qty": 2}],
        "reward_desc": "+180 🐚 Vỏ Sò & 2x Thỏi Đồng Thưởng"
    },
    {
        "id": "q11_bronze_tools",
        "era": ERA_BRONZE,
        "title": "11. Công Cụ Đồng Sắc Bén",
        "desc": "Rèn Rìu Đồng hoặc Cuốc Đồng sắc bén để nâng cao năng suất khai hoang gấp bội.",
        "requirement_type": "has_bronze_tool",
        "reward_shells": 250,
        "reward_items": [{"id": "ancient_amber", "type": "rare", "name": "Hổ Phách Thần Bí", "price": 300, "qty": 1}],
        "reward_desc": "+250 🐚 Vỏ Sò & 1x Hổ Phách Thần Bí"
    },
    {
        "id": "q12_tribal_totem",
        "era": ERA_BRONZE,
        "title": "12. Trụ Totem & Đại Bộ Tộc",
        "desc": "Xây dựng Trụ Totem Tổ Tiên ở trung tâm căn cứ, quy tụ và đưa bộ lạc bước vào thời hoàng kim!",
        "requirement_type": "structure_level",
        "target_structure": "totem",
        "target_level": 1,
        "reward_shells": 500,
        "reward_desc": "+500 🐚 Vỏ Sò & 👑 DANH HIỆU THỦ LĨNH TỐI CAO!"
    }
]


class EraQuestSystem:
    def __init__(self):
        self.quests = QUESTS
        self.active_index = 0
        self.completed_quest_ids = set()
        self.show_tracker = True
        self.has_harvested_any = False
        self.has_tilled_or_planted = False

    @property
    def current_quest(self):
        if 0 <= self.active_index < len(self.quests):
            return self.quests[self.active_index]
        return None

    def check_progress(self, inventory, crafting_sys, primitive_structures, dialog_mgr, assets):
        """
        Evaluates active quest requirements.
        If met, grants rewards, advances active quest, and triggers celebrations.
        """
        quest = self.current_quest
        if not quest:
            return False

        q_id = quest["id"]
        is_completed = False

        # 1. Standard inventory materials requirement
        if "requirements" in quest:
            reqs = quest["requirements"]
            all_met = True
            for item_id, req_qty in reqs.items():
                cur_qty = crafting_sys._count_item(inventory, item_id)
                if cur_qty < req_qty:
                    all_met = False
                    break
            if all_met:
                is_completed = True

        # 2. Specific requirement types
        req_type = quest.get("requirement_type")
        if req_type == "has_tool":
            target_tool = quest.get("target_tool")
            all_slots = inventory.hotbar + inventory.bag
            for item in all_slots:
                if item and item.get("id") == target_tool:
                    is_completed = True
                    break

        elif req_type == "structure_level":
            target_struct = quest.get("target_structure")
            target_lvl = quest.get("target_level", 1)
            cur_lvl = 0
            if target_struct == "campfire":
                cur_lvl = primitive_structures.campfire_level
            elif target_struct == "shelter":
                cur_lvl = primitive_structures.shelter_level
            elif target_struct == "clay_kiln":
                cur_lvl = primitive_structures.kiln_level
            elif target_struct == "totem":
                cur_lvl = primitive_structures.totem_level
            if cur_lvl >= target_lvl:
                is_completed = True

        elif req_type == "has_item_category":
            cat = quest.get("target_category")
            all_slots = inventory.hotbar + inventory.bag
            for item in all_slots:
                if item and (item.get("type") == cat or "nướng" in item.get("name", "").lower()):
                    is_completed = True
                    break

        elif req_type == "tilled_or_planted":
            if self.has_tilled_or_planted:
                is_completed = True

        elif req_type == "has_harvested":
            if self.has_harvested_any:
                is_completed = True

        elif req_type == "has_bronze_tool":
            all_slots = inventory.hotbar + inventory.bag
            for item in all_slots:
                if item and "bronze" in item.get("id", ""):
                    is_completed = True
                    break

        # If completed, claim and advance!
        if is_completed and q_id not in self.completed_quest_ids:
            self._claim_quest(quest, inventory, crafting_sys, dialog_mgr, assets)
            return True

        return False

    def _claim_quest(self, quest, inventory, crafting_sys, dialog_mgr, assets):
        """Grants rewards and progresses to next milestone."""
        self.completed_quest_ids.add(quest["id"])
        assets.play_sound("success")

        # 1. Shells Reward
        reward_shells = quest.get("reward_shells", 0)
        inventory.gold += reward_shells

        # 2. Items Reward
        for itm in quest.get("reward_items", []):
            inventory.add_item(dict(itm), itm.get("qty", 1))

        # 3. Era Unlock
        if "unlocks_era" in quest:
            next_era = quest["unlocks_era"]
            ok, era_msg = crafting_sys.unlock_era(next_era)
            if ok:
                dialog_mgr.add_toast(era_msg)

        # 4. Success Toast
        dialog_mgr.add_toast(f"🎉 Hoàn thành: {quest['title']}! ({quest.get('reward_desc', '')})")

        # Advance to next quest
        self.active_index += 1

    def get_progress_string(self, inventory, crafting_sys, primitive_structures):
        """Returns concise progress string (e.g. 'Cành cây: 3/5, Đá cuội: 2/3') for HUD."""
        quest = self.current_quest
        if not quest:
            return "Đã hoàn thành mọi mục tiêu Kỷ Nguyên!"

        if "requirements" in quest:
            parts = []
            for item_id, req_qty in quest["requirements"].items():
                cur = crafting_sys._count_item(inventory, item_id)
                name = "Cành" if item_id == "branch" else ("Đá" if item_id == "pebble" else item_id)
                parts.append(f"{name}: {min(cur, req_qty)}/{req_qty}")
            return ", ".join(parts)

        req_type = quest.get("requirement_type")
        if req_type == "has_tool":
            return "Mở [C] để chế tác Rìu Đá"
        elif req_type == "structure_level":
            t_name = quest.get("target_structure")
            name_vn = "Lửa Trại" if t_name == "campfire" else ("Chòi/Lều" if t_name == "shelter" else ("Lò Nung" if t_name == "clay_kiln" else "Trụ Totem"))
            return f"Xây dựng {name_vn} [C]"
        elif req_type == "has_item_category":
            return "Nướng cá/củ tại Lửa Trại [E]"
        elif req_type == "tilled_or_planted":
            return "Xới đất & gieo hạt giống"
        elif req_type == "has_harvested":
            return "Thu hoạch 1 mẻ nông sản"
        elif req_type == "has_bronze_tool":
            return "Rèn 1 công cụ Đồng [C]"

        return "Đang thực hiện"

    def to_dict(self):
        return {
            "active_index": self.active_index,
            "completed_quest_ids": list(self.completed_quest_ids),
            "has_harvested_any": self.has_harvested_any,
            "has_tilled_or_planted": self.has_tilled_or_planted
        }

    def from_dict(self, data):
        if not data:
            return
        self.active_index = data.get("active_index", 0)
        self.completed_quest_ids = set(data.get("completed_quest_ids", []))
        self.has_harvested_any = data.get("has_harvested_any", False)
        self.has_tilled_or_planted = data.get("has_tilled_or_planted", False)

