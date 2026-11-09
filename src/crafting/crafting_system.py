"""
Crafting and Building System for Stone Age: Dawn of Tribe.
Handles primitive recipe definitions, material consumption, tool smithing,
building construction/upgrades, primitive campfire cooking, and Era progression.
"""

from src.settings import (
    ERA_PALEOLITHIC, ERA_NEOLITHIC, ERA_BRONZE, ERAS_DATA,
    TOOL_AXE, TOOL_HOE, TOOL_PICKAXE, TOOL_WATER_CAN, TOOL_SCYTHE, TOOL_FISHING_ROD
)

RECIPES = [
    # =========================================================================
    # 1. PALEOLITHIC ERA RECIPES (THỜI ĐỒ ĐÁ CŨ - SƠ KHAI)
    # =========================================================================
    {
        "id": "craft_sharp_flint",
        "name": "Mảnh Đá Lửa Sắc",
        "category": "materials",
        "era": ERA_PALEOLITHIC,
        "desc": "Đập hai hòn đá cuội vào nhau để tạo ra mảnh cạnh sắc bén.",
        "ingredients": {"pebble": 2},
        "output": {"id": "flint", "type": "material", "name": "Đá Lửa (Flint)", "price": 8, "qty": 1}
    },
    {
        "id": "craft_plant_cord",
        "name": "Dây Bện Cỏ Khô",
        "category": "materials",
        "era": ERA_PALEOLITHIC,
        "desc": "Bện các sợi cỏ dại thành sợi dây leo thô chắc chắn.",
        "ingredients": {"fiber": 3},
        "output": {"id": "cord", "type": "material", "name": "Dây Bện Cỏ (Cord)", "price": 10, "qty": 1}
    },
    {
        "id": "craft_primitive_axe",
        "name": "Rìu Đá Thô Sơ",
        "category": "tools",
        "era": ERA_PALEOLITHIC,
        "desc": "Cột đá sắc vào cành cây bằng dây cỏ. Dùng để đốn cây lấy gỗ nguyên sinh.",
        "ingredients": {"branch": 3, "pebble": 2, "fiber": 2},
        "output": {"id": "primitive_axe", "tool_type": TOOL_AXE, "type": "tool", "name": "Rìu Đá Thô Sơ", "power": 1}
    },
    {
        "id": "craft_digging_stick",
        "name": "Gậy Bới Đất Nhọn",
        "category": "tools",
        "era": ERA_PALEOLITHIC,
        "desc": "Cành cây vót nhọn bằng đá lửa. Dùng bới đất tơi xốp để gieo hạt giống dại.",
        "ingredients": {"branch": 2, "flint": 1},
        "output": {"id": "digging_stick", "tool_type": TOOL_HOE, "type": "tool", "name": "Gậy Bới Đất Nhọn", "power": 1}
    },
    {
        "id": "craft_primitive_spear",
        "name": "Giáo Xiên Cá Thô Sơ",
        "category": "tools",
        "era": ERA_PALEOLITHIC,
        "desc": "Gậy gỗ gắn đầu đá nhọn. Dùng để xiên bắt cá dưới dòng suối nguyên sinh.",
        "ingredients": {"branch": 3, "pebble": 1, "fiber": 2},
        "output": {"id": "primitive_spear", "tool_type": TOOL_FISHING_ROD, "type": "tool", "name": "Giáo Xiên Cá Thô Sơ", "power": 1}
    },
    {
        "id": "craft_stone_pick",
        "name": "Búa Đá Sơ Khai",
        "category": "tools",
        "era": ERA_PALEOLITHIC,
        "desc": "Đá nặng buộc chắc vào cán gỗ. Dùng đập vỡ đá cuội lớn và tảng đá mỏ khoáng.",
        "ingredients": {"branch": 3, "pebble": 3, "fiber": 2},
        "output": {"id": "stone_pick", "tool_type": TOOL_PICKAXE, "type": "tool", "name": "Búa Đá Sơ Khai", "power": 1}
    },
    {
        "id": "craft_flint_striker",
        "name": "Bộ Đánh Lửa Đá Lửa",
        "category": "tools",
        "era": ERA_PALEOLITHIC,
        "desc": "Hai hòn đá lửa cùng bùi nhùi cỏ khô để nhóm lửa trại sinh tồn.",
        "ingredients": {"flint": 2, "fiber": 2},
        "output": {"id": "flint_striker", "type": "tool", "name": "Bộ Đá Lửa Đánh Lửa", "power": 1}
    },
    {
        "id": "build_campfire",
        "name": "Đống Lửa Trại Sơ Khai",
        "category": "structures",
        "era": ERA_PALEOLITHIC,
        "desc": "Trái tim của căn cứ tiền sử! Sưởi ấm ban đêm, xua đuổi dã thú và nướng chín thức ăn.",
        "ingredients": {"branch": 5, "pebble": 4, "flint": 1},
        "building_target": "campfire",
        "level": 1
    },
    {
        "id": "build_leaf_shelter",
        "name": "Chòi Lá Trú Ẩn (Căn cứ Cấp 1)",
        "category": "structures",
        "era": ERA_PALEOLITHIC,
        "desc": "Mái che đan từ cành cây và lá cỏ khô. Cho phép người chơi ngủ qua đêm an toàn.",
        "ingredients": {"branch": 12, "fiber": 15},
        "building_target": "shelter",
        "level": 1
    },
    {
        "id": "build_woven_basket",
        "name": "Giỏ Đan Chứa Đồ",
        "category": "structures",
        "era": ERA_PALEOLITHIC,
        "desc": "Giỏ mây lau sậy đan dày dặn, dùng chứa các vật phẩm nhặt nhạnh được.",
        "ingredients": {"fiber": 8, "branch": 6},
        "building_target": "storage",
        "level": 1
    },
    {
        "id": "build_grass_tent",
        "name": "Lều Cỏ Đan Nhánh Cây (+2 Chỗ Ở)",
        "category": "structures",
        "era": ERA_PALEOLITHIC,
        "desc": "Dựng thêm lều cỏ đan cành khô cho bộ tộc. Tăng thêm 2 chỗ ở an toàn.",
        "ingredients": {"branch": 8, "fiber": 10},
        "building_target": "grass_tent",
        "level": 1
    },

    # =========================================================================
    # 2. NEOLITHIC ERA RECIPES (THỜI ĐỒ ĐÁ MỚI - NÔNG NGHIỆP & GỐM NUNG)
    # =========================================================================
    {
        "id": "craft_clay_brick",
        "name": "Gạch Bùn Đất Sét Nung",
        "category": "materials",
        "era": ERA_NEOLITHIC,
        "desc": "Đất sét nhào nặn phơi khô rồi nung lửa thành gạch rắn rỏi.",
        "ingredients": {"clay": 3, "wood": 1},
        "output": {"id": "clay_brick", "type": "material", "name": "Gạch Đất Nung", "price": 18, "qty": 1}
    },
    {
        "id": "craft_polished_axe",
        "name": "Rìu Đá Mài Bóng",
        "category": "tools",
        "era": ERA_NEOLITHIC,
        "desc": "Đá được mài nhẵn thia sắc lẹm, cán gỗ cứng buộc gân. Chặt cây tốn ít thể lực gấp đôi.",
        "ingredients": {"wood": 8, "pebble": 5, "cord": 2},
        "output": {"id": "polished_axe", "tool_type": TOOL_AXE, "type": "tool", "name": "Rìu Đá Mài Bóng", "power": 2}
    },
    {
        "id": "craft_stone_hoe",
        "name": "Cuốc Đá Xới Đất",
        "category": "tools",
        "era": ERA_NEOLITHIC,
        "desc": "Lưỡi đá mài nhẵn gắn cán chữ L chắc khỏe. Dùng xới luống đất nông nghiệp màu mỡ.",
        "ingredients": {"wood": 6, "pebble": 4, "cord": 2},
        "output": {"id": "stone_hoe", "tool_type": TOOL_HOE, "type": "tool", "name": "Cuốc Đá Xới Đất", "power": 2}
    },
    {
        "id": "craft_clay_jug",
        "name": "Bình Gốm Nung Múc Nước",
        "category": "tools",
        "era": ERA_NEOLITHIC,
        "desc": "Bình nặn bằng đất sét nung không thấm nước. Dùng múc nước sông tưới ẩm các luống cây.",
        "ingredients": {"clay": 4, "wood": 2},
        "output": {"id": "clay_jug", "tool_type": TOOL_WATER_CAN, "type": "tool", "name": "Bình Gốm Nung Múc Nước", "water": 35, "max_water": 35, "power": 2}
    },
    {
        "id": "craft_bone_rod",
        "name": "Cần Câu Móc Xương Cá",
        "category": "tools",
        "era": ERA_NEOLITHIC,
        "desc": "Cần câu uốn từ cành dẻo gắn lưỡi câu đẽo bằng xương cá lớn. Bắt cá sông cực nhạy.",
        "ingredients": {"wood": 5, "cord": 2, "bone": 2},
        "output": {"id": "bone_rod", "tool_type": TOOL_FISHING_ROD, "type": "tool", "name": "Cần Câu Móc Xương Cá", "power": 2}
    },
    {
        "id": "craft_bone_scythe",
        "name": "Liềm Răng Xương Cắt Cỏ",
        "category": "tools",
        "era": ERA_NEOLITHIC,
        "desc": "Lưỡi liềm gắn mảnh đá lửa sắc bén hoặc răng động vật. Cắt cỏ dại và dọn dẹp ruộng cực nhanh.",
        "ingredients": {"wood": 4, "flint": 3, "cord": 1},
        "output": {"id": "bone_scythe", "tool_type": TOOL_SCYTHE, "type": "tool", "name": "Liềm Răng Xương Cắt Cỏ", "power": 2}
    },
    {
        "id": "build_clay_kiln",
        "name": "Lò Nung Đất Sét Tiền Sử",
        "category": "structures",
        "era": ERA_NEOLITHIC,
        "desc": "Lò vòm đất sét giữ nhiệt độ cao, dùng nung đồ gốm và nung quặng đồng sơ khai.",
        "ingredients": {"clay": 12, "pebble": 8, "wood": 6},
        "building_target": "clay_kiln",
        "level": 1
    },
    {
        "id": "build_animal_pen",
        "name": "Bãi Quây Thuần Hóa Thú Nuôi",
        "category": "structures",
        "era": ERA_NEOLITHIC,
        "desc": "Hàng rào cọc gỗ vững chắc để giữ và chăm sóc gà rừng, bò rừng aurochs.",
        "ingredients": {"wood": 18, "cord": 4, "fiber": 10},
        "building_target": "animal_pen",
        "level": 1
    },
    {
        "id": "upgrade_fur_tent",
        "name": "Lều Da Thú Vững Chắc (Căn cứ Cấp 2)",
        "category": "structures",
        "era": ERA_NEOLITHIC,
        "desc": "Nâng cấp từ chòi lá sơ khai. Khung gỗ vững chãi phủ da thú ấm áp chống mưa gió.",
        "ingredients": {"wood": 20, "cord": 6, "branch": 15},
        "building_target": "shelter",
        "level": 2
    },
    {
        "id": "build_pelt_tipi",
        "name": "Đại Trướng Da Thú Khung Ngà (+4 Chỗ Ở)",
        "category": "structures",
        "era": ERA_NEOLITHIC,
        "desc": "Dựng thêm lều chóp nón lớn bọc da thú dày. Mở rộng thêm 4 chỗ ở ấm áp.",
        "ingredients": {"wood": 16, "pelt": 3, "cord": 4},
        "building_target": "pelt_tipi",
        "level": 1
    },
    {
        "id": "upgrade_stone_firepit",
        "name": "Bếp Lửa Đá Kè (Lửa Trại Cấp 2)",
        "category": "structures",
        "era": ERA_NEOLITHIC,
        "desc": "Lửa trại được kè đá tròn và dựng giá treo nướng thịt cá tiện lợi.",
        "ingredients": {"pebble": 12, "wood": 6, "clay": 4},
        "building_target": "campfire",
        "level": 2
    },

    # =========================================================================
    # 3. BRONZE ERA RECIPES (THỜI ĐỒ ĐỒNG - BỘ LẠC & KIM KHÍ)
    # =========================================================================
    {
        "id": "smelt_copper_bar",
        "name": "Nung Đúc Thỏi Đồng",
        "category": "materials",
        "era": ERA_BRONZE,
        "desc": "Nung quặng đồng nguyên chất trong lò nung ở nhiệt độ cao thành thỏi đồng sáng bóng.",
        "ingredients": {"copper_ore": 3, "wood": 2},
        "output": {"id": "copper_bar", "type": "material", "name": "Thỏi Đồng Nguyên Chất", "price": 85, "qty": 1}
    },
    {
        "id": "craft_bronze_axe",
        "name": "Rìu Đồng Sắc Bén",
        "category": "tools",
        "era": ERA_BRONZE,
        "desc": "Lưỡi rìu đúc bằng đồng tôi luyện sắc ngọt. Đốn gục cây cổ thụ chỉ trong vài nhát chém.",
        "ingredients": {"wood": 8, "copper_bar": 3, "cord": 2},
        "output": {"id": "bronze_axe", "tool_type": TOOL_AXE, "type": "tool", "name": "Rìu Đồng Sắc Bén", "power": 3}
    },
    {
        "id": "craft_bronze_hoe",
        "name": "Cuốc Đồng Khai Hoang",
        "category": "tools",
        "era": ERA_BRONZE,
        "desc": "Lưỡi đồng bóng loáng xới tơi xốp cả đất khô cằn sỏi đá, tiết kiệm tối đa sức lực.",
        "ingredients": {"wood": 6, "copper_bar": 3, "cord": 2},
        "output": {"id": "bronze_hoe", "tool_type": TOOL_HOE, "type": "tool", "name": "Cuốc Đồng Khai Hoang", "power": 3}
    },
    {
        "id": "craft_bronze_pick",
        "name": "Cuốc Chim Đồng Luyện",
        "category": "tools",
        "era": ERA_BRONZE,
        "desc": "Mũi cuốc chim bằng đồng nhọn hoắt đập vỡ mọi tảng đá hoa cương và mạch quặng lớn.",
        "ingredients": {"wood": 8, "copper_bar": 4, "cord": 2},
        "output": {"id": "bronze_pick", "tool_type": TOOL_PICKAXE, "type": "tool", "name": "Cuốc Chim Đồng Luyện", "power": 3}
    },
    {
        "id": "craft_tribal_harpoon",
        "name": "Lao Săn Cá Bộ Lạc",
        "category": "tools",
        "era": ERA_BRONZE,
        "desc": "Ngọn lao mũi đồng có ngạnh sắc lẹm, bắt gọn những loài cá lớn và cá hoàng kim quý giá.",
        "ingredients": {"wood": 10, "copper_bar": 2, "cord": 3},
        "output": {"id": "tribal_harpoon", "tool_type": TOOL_FISHING_ROD, "type": "tool", "name": "Lao Săn Cá Bộ Lạc", "power": 3}
    },
    {
        "id": "build_tribal_totem",
        "name": "Trụ Totem Tổ Tiên Thần Bí",
        "category": "structures",
        "era": ERA_BRONZE,
        "desc": "Trụ gỗ đá tạc hình thần linh tổ tiên. Lan tỏa linh khí giúp cây cối lớn nhanh và ban phước cho bộ lạc.",
        "ingredients": {"wood": 25, "pebble": 20, "copper_bar": 2},
        "building_target": "totem",
        "level": 1
    },
    {
        "id": "upgrade_mud_hut",
        "name": "Nhà Vách Đất Mái Tranh (Căn cứ Cấp 3)",
        "category": "structures",
        "era": ERA_BRONZE,
        "desc": "Căn nhà kiên cố xây từ cọc gỗ và đất sét nung, mát mẻ mùa hạ và ấm áp mùa đông.",
        "ingredients": {"wood": 35, "clay": 25, "pebble": 15},
        "building_target": "shelter",
        "level": 3
    },

    # =========================================================================
    # 4. CAMPFIRE COOKING & FORAGED ROASTS (ẨM THỰC SINH TỒN)
    # =========================================================================
    {
        "id": "cook_roasted_fish",
        "name": "Cá Suối Nướng Lửa Hồng",
        "category": "cooking",
        "era": ERA_PALEOLITHIC,
        "desc": "Cá tươi xiên cành nướng trên than hồng thơm ngậy. Hồi phục 35 Thể Lực.",
        "ingredients": {"raw_fish": 1},
        "output": {"id": "roasted_fish", "type": "food", "name": "Cá Suối Nướng Lửa Hồng", "price": 55, "stamina_restore": 35, "qty": 1}
    },
    {
        "id": "cook_roasted_roots",
        "name": "Củ Rừng Nướng Tro Ấm",
        "category": "cooking",
        "era": ERA_PALEOLITHIC,
        "desc": "Củ dại lùi tro nóng dẻo bùi ngọt ngào. Hồi phục 25 Thể Lực.",
        "ingredients": {"wild_roots": 1},
        "output": {"id": "roasted_roots", "type": "food", "name": "Củ Rừng Nướng Tro Ấm", "price": 38, "stamina_restore": 25, "qty": 1}
    },
    {
        "id": "cook_smoked_meat",
        "name": "Thịt Rừng Hun Khói Tiền Sử",
        "category": "cooking",
        "era": ERA_PALEOLITHIC,
        "desc": "Thịt thú rừng tươi hun khói củi thơm lừng. Hồi phục 55 Thể Lực.",
        "ingredients": {"raw_meat": 1},
        "output": {"id": "smoked_meat", "type": "food", "name": "Thịt Rừng Hun Khói", "price": 95, "stamina_restore": 55, "qty": 1}
    },
    {
        "id": "cook_roasted_corn",
        "name": "Bắp Rừng Nướng Than Rực",
        "category": "cooking",
        "era": ERA_NEOLITHIC,
        "desc": "Bắp ngô hoang dã nướng bắp vàng thơm ngát. Hồi phục 40 Thể Lực.",
        "ingredients": {"wild_corn": 1},
        "output": {"id": "roasted_corn", "type": "food", "name": "Bắp Rừng Nướng Than Rực", "price": 75, "stamina_restore": 40, "qty": 1}
    }
]


class CraftingSystem:
    def __init__(self):
        self.current_era = ERA_PALEOLITHIC
        self.recipes = RECIPES
        self.crafted_history = set()

    def get_recipes_by_category(self, category=None):
        """Returns recipes filtered by category and unlocked eras."""
        era_levels = {ERA_PALEOLITHIC: 1, ERA_NEOLITHIC: 2, ERA_BRONZE: 3}
        current_lvl = era_levels.get(self.current_era, 1)

        result = []
        for r in self.recipes:
            r_era = r.get("era", ERA_PALEOLITHIC)
            r_lvl = era_levels.get(r_era, 1)
            # Only show recipes up to current era
            if r_lvl <= current_lvl:
                if category is None or r.get("category") == category:
                    result.append(r)
        return result

    def can_craft(self, recipe, inventory):
        """Checks whether player has all required ingredients in bag or hotbar."""
        ingredients = recipe.get("ingredients", {})
        for item_id, required_qty in ingredients.items():
            current_qty = self._count_item(inventory, item_id)
            if current_qty < required_qty:
                return False, f"Thiếu {item_id} ({current_qty}/{required_qty})"
        return True, "Đủ nguyên liệu"

    def _count_item(self, inventory, item_id):
        """Counts total quantity of item in hotbar and bag."""
        count = 0
        all_slots = inventory.hotbar + inventory.bag
        for item in all_slots:
            if not item:
                continue
            iid = item.get("id")
            # Special aliases for prehistoric crafting
            if item_id in ["branch", "wood"]:
                if iid in ["branch", "wood"]:
                    count += item.get("qty", 1)
            elif item_id in ["pebble", "stone"]:
                if iid in ["pebble", "stone"]:
                    count += item.get("qty", 1)
            elif item_id == "raw_fish":
                if item.get("type") == "fish" or "cá" in item.get("name", "").lower() or "tôm" in item.get("name", "").lower() or iid in ["paleo_carp", "mud_catfish", "river_crayfish", "river_sturgeon", "carp", "bass"] or (isinstance(iid, str) and iid.startswith("fish_")):
                    count += item.get("qty", 1)
            elif item_id == "raw_meat":
                if iid in ["raw_meat", "meat"] or "thịt" in item.get("name", "").lower():
                    count += item.get("qty", 1)
            elif iid == item_id:
                count += item.get("qty", 1)
        return count

    def craft_recipe(self, recipe_id_or_dict, inventory, primitive_structures=None):
        """Helper to craft by recipe ID string or recipe dict."""
        if isinstance(recipe_id_or_dict, str):
            recipe = next((r for r in RECIPES if r["id"] == recipe_id_or_dict), None)
            if not recipe:
                return False, f"Không tìm thấy công thức: {recipe_id_or_dict}", None
        else:
            recipe = recipe_id_or_dict
        return self.craft(recipe, inventory, primitive_structures)

    def craft(self, recipe, inventory, primitive_structures=None):
        """
        Executes crafting or building. Consumes materials and adds output or upgrades base.
        Returns: (success: bool, message: str, sfx: str)
        """
        can, reason = self.can_craft(recipe, inventory)
        if not can:
            return False, reason, None

        # 1. Consume materials
        ingredients = recipe.get("ingredients", {})
        for item_id, required_qty in ingredients.items():
            self._consume_item(inventory, item_id, required_qty)

        # 2. Grant Output
        self.crafted_history.add(recipe["id"])

        # Case A: Building construction or base upgrade
        if "building_target" in recipe:
            b_target = recipe["building_target"]
            b_level = recipe.get("level", 1)
            if primitive_structures:
                primitive_structures.upgrade_structure(b_target, b_level)
            return True, f"Xây dựng thành công: {recipe['name']}!", "success"

        # Case B: Item or Tool output
        output_template = recipe.get("output")
        if output_template:
            out_item = dict(output_template)
            qty = out_item.get("qty", 1)
            inventory.add_item(out_item, qty)
            sfx = "chop" if out_item.get("tool_type") == TOOL_AXE else "clink"
            if recipe.get("category") == "cooking":
                sfx = "success"
            return True, f"Chế tác thành công: {out_item['name']}!", sfx

        return True, f"Hoàn thành {recipe['name']}!", "success"

    def _consume_item(self, inventory, item_id, qty_to_consume):
        """Removes requested quantity of item from bag/hotbar."""
        remaining = qty_to_consume
        all_slots = inventory.bag + inventory.hotbar  # Prefer consuming from bag first

        for item in all_slots:
            if not item:
                continue
            iid = item.get("id")
            is_match = False
            if item_id in ["branch", "wood"] and iid in ["branch", "wood"]:
                is_match = True
            elif item_id in ["pebble", "stone"] and iid in ["pebble", "stone"]:
                is_match = True
            elif item_id == "raw_fish":
                if item.get("type") == "fish" or "cá" in item.get("name", "").lower() or "tôm" in item.get("name", "").lower() or iid in ["paleo_carp", "mud_catfish", "river_crayfish", "river_sturgeon", "carp", "bass"] or (isinstance(iid, str) and iid.startswith("fish_")):
                    is_match = True
            elif item_id == "raw_meat":
                if iid in ["raw_meat", "meat"] or "thịt" in item.get("name", "").lower():
                    is_match = True
            elif iid == item_id:
                is_match = True

            if is_match:
                item_qty = item.get("qty", 1)
                take = min(remaining, item_qty)
                item["qty"] = item_qty - take
                remaining -= take
                if item["qty"] <= 0:
                    # Remove empty item from inventory
                    if item in inventory.bag:
                        inventory.bag[inventory.bag.index(item)] = None
                    elif item in inventory.hotbar:
                        inventory.hotbar[inventory.hotbar.index(item)] = None
                if remaining <= 0:
                    break

    def unlock_era(self, era_id):
        """Advances tribe evolution to the next era."""
        if era_id in ERAS_DATA and era_id != self.current_era:
            self.current_era = era_id
            return True, f"🌟 Chúc mừng! Bộ lạc đã tiến hóa lên: {ERAS_DATA[era_id]['name']}!"
        return False, ""

    def to_dict(self):
        return {
            "current_era": self.current_era,
            "crafted_history": list(self.crafted_history)
        }

    def from_dict(self, data):
        if not data:
            return
        self.current_era = data.get("current_era", ERA_PALEOLITHIC)
        self.crafted_history = set(data.get("crafted_history", []))
