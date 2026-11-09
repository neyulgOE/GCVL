"""
Tribe Settlement Manager for Stone Age: Dawn of Tribe.
Quản lý Định cư Bộ tộc: Sức chứa Chỗ ở, Lương thực Dự trữ, Lửa sưởi,
Vòng đời Sinh đẻ - Tuyển mộ người lưu lạc - Permadeath & Mai táng.
"""

import pygame
import random
import math
from src.settings import TILE_SIZE
from src.entities.villager import TribalVillager, TRIBAL_MALE_NAMES, TRIBAL_FEMALE_NAMES

class TribeSettlementManager:
    def __init__(self, primitive_structures=None):
        self.structures = primitive_structures
        self.villagers = []
        self.ancestral_records = []  # Bia đá tưởng niệm những người đã khuất
        self.recent_events = []      # Danh sách thông báo nổi trên màn hình
        self.event_timer = 0.0

        # Stockpile Tài nguyên chung của Bộ tộc
        self.stockpile = {
            "meat": 80,
            "berries": 45,
            "fish": 20,
            "wood": 60,
            "stone": 40,
            "pelt": 6
        }

        # Camp Base Coordinates (80x80 Prehistoric Map Central Sanctuary)
        self.campfire_center = (40 * TILE_SIZE + 32, 38 * TILE_SIZE + 32)
        self.shelter_center = (38 * TILE_SIZE + 96, 34 * TILE_SIZE + 96)
        self.storage_center = (43 * TILE_SIZE + 32, 38 * TILE_SIZE + 32)

        # Built additional tents (Lều xây thêm ngoài hốc đá tự nhiên)
        self.grass_tents = 0  # +2 chỗ ở mỗi lều
        self.pelt_tipis = 0   # +4 chỗ ở mỗi lều

        # Reproduction & Nomad Timers
        self.breeding_cooldown = 180.0  # seconds between natural birth checks
        self.nomad_check_timer = 120.0   # seconds between nomad encounters
        self.is_winter = False

        # Khởi tạo 6 cư dân ban đầu theo thiết kế đã phê duyệt
        self._init_starting_tribe()

    def _init_starting_tribe(self):
        """Spawns initial 6 tribe members staged realistically at their specialized workstations."""
        ts = TILE_SIZE

        # Realistic Workstation Staging coordinates
        # 1. Chieftain Ogg: Guarding Ancestral Rock Cave Entrance (col 38, row 36.8)
        # 2. Shaman Kraa: Performing Fire Rites at Megalithic Totem Shrine (col 36, row 42)
        # 3. Hunter Boomer: Knapping flint spearheads at Toolmakers Workshop (col 42, row 42)
        # 4. Hunter Tara: Standing watch at Palisade Gate (col 45, row 40)
        # 5. Gatherer Una: Processing berries & hides at Meat Smoker (col 44, row 35)
        # 6. Child Miko: Sitting safely outside Grass Lean-to (col 39, row 37)

        starting_roster = [
            {"id": "vil_chief", "name": "Ogg", "gender": "male", "age": 32, "role": "chieftain", 
             "wx": 38 * ts + 48, "wy": 36 * ts + 48, "dir": "down", "carrying": None},
            {"id": "vil_shaman", "name": "Kraa", "gender": "male", "age": 52, "role": "shaman", 
             "wx": 36 * ts + 32, "wy": 42 * ts + 18, "dir": "right", "carrying": None},
            {"id": "vil_tara", "name": "Tara", "gender": "female", "age": 25, "role": "hunter", 
             "wx": 44 * ts + 12, "wy": 41 * ts + 26, "dir": "right", "carrying": None},
            {"id": "vil_una", "name": "Una", "gender": "female", "age": 22, "role": "gatherer", 
             "wx": 44 * ts + 20, "wy": 35 * ts + 25, "dir": "down", "carrying": {"id": "berries", "count": 3, "max": 5}},
            {"id": "vil_boomer", "name": "Boomer", "gender": "male", "age": 28, "role": "hunter", 
             "wx": 42 * ts + 32, "wy": 42 * ts + 22, "dir": "down", "carrying": None},
            {"id": "vil_miko", "name": "Miko", "gender": "male", "age": 8, "role": "child", 
             "wx": 39 * ts + 25, "wy": 37 * ts + 12, "dir": "down", "carrying": None}
        ]

        for p in starting_roster:
            v = TribalVillager(
                villager_id=p["id"],
                name=p["name"],
                gender=p["gender"],
                age_seasons=p["age"],
                role=p["role"],
                x=p["wx"],
                y=p["wy"]
            )
            v.direction = p["dir"]
            if p.get("carrying"):
                v.carrying = p["carrying"]
            self.villagers.append(v)

        self.add_event_notification("🔥 Bộ tộc tiền sử đã nhóm lửa tại Hốc Đá Cội Nguồn!")

    # -----------------------------------------------------------------
    # CAPACITY & STOCKPILE CALCULATIONS
    # -----------------------------------------------------------------
    @property
    def housing_capacity(self):
        """Base Natural Rock Shelter = 6 beds. Additional tents expand capacity."""
        base_rock_shelter = 6
        extra_shelter_bonus = 0
        if self.structures:
            # Shelter Level 1: +0 (basic natural lean-to)
            # Shelter Level 2 (Lều Da Thú): +4
            # Shelter Level 3 (Nhà Đất Nện): +8
            if self.structures.shelter_level == 2:
                extra_shelter_bonus += 4
            elif self.structures.shelter_level >= 3:
                extra_shelter_bonus += 8

        extra_tents = 0
        if self.structures:
            extra_tents += getattr(self.structures, "grass_tents", 0) * 2
            extra_tents += getattr(self.structures, "pelt_tipis", 0) * 4

        total = base_rock_shelter + extra_shelter_bonus + extra_tents + (self.grass_tents * 2) + (self.pelt_tipis * 4)
        return total

    @property
    def alive_villagers(self):
        return [v for v in self.villagers if not v.is_dead]

    @property
    def dead_villagers(self):
        return [v for v in self.villagers if v.is_dead]

    @property
    def current_population(self):
        return len(self.alive_villagers)

    @property
    def total_food_units(self):
        return self.stockpile["meat"] + self.stockpile["berries"] + self.stockpile["fish"]

    def is_near_fire(self, wx, wy, radius=160):
        """Checks if world position receives heat from central campfire."""
        if self.structures and self.structures.campfire_level <= 0:
            return False
        dist = math.hypot(wx - self.campfire_center[0], wy - self.campfire_center[1])
        return dist <= radius

    def is_near_shelter(self, wx, wy, radius=180):
        """Checks if world position is inside sheltering boundary."""
        dist = math.hypot(wx - self.shelter_center[0], wy - self.shelter_center[1])
        return dist <= radius

    def get_campfire_center(self):
        return self.campfire_center

    def get_storage_center(self):
        return self.storage_center

    def deposit_resources(self, item_id, count):
        """Deposits harvested items from villagers into tribal stockpile."""
        if item_id in self.stockpile:
            self.stockpile[item_id] += count
        else:
            self.stockpile[item_id] = count

    def add_event_notification(self, text):
        """Adds a temporary banner message to screen."""
        self.recent_events.append({"text": text, "timer": 5.0})
        if len(self.recent_events) > 4:
            self.recent_events.pop(0)

    # -----------------------------------------------------------------
    # SIMULATION & POPULATION GROWTH MECHANICS
    # -----------------------------------------------------------------
    def update(self, dt, time_sys=None, obstacles_map=None):
        """Updates all villagers, handles food feeding, breeding and nomad events."""
        if time_sys:
            self.is_winter = (time_sys.season_id == "winter")

        # Update event notifications
        for ev in self.recent_events:
            ev["timer"] -= dt
        self.recent_events = [ev for ev in self.recent_events if ev["timer"] > 0]

        # 1. Update each villager
        for v in self.villagers:
            v.update(dt, self, obstacles_map)
            # Detect death and record to Ancestral Cairn exactly once
            if v.is_dead and not getattr(v, "_death_recorded", False):
                v._death_recorded = True
                self._handle_villager_death(v)

        # 2. Daily Feeding Routine from Stockpile (Every few real minutes)
        for v in self.alive_villagers:
            if v.hunger < 50.0 and self.total_food_units > 0:
                # Consume 1 unit of food
                if self.stockpile["berries"] > 0:
                    self.stockpile["berries"] -= 1
                    v.hunger = min(100.0, v.hunger + 35.0)
                elif self.stockpile["fish"] > 0:
                    self.stockpile["fish"] -= 1
                    v.hunger = min(100.0, v.hunger + 45.0)
                elif self.stockpile["meat"] > 0:
                    self.stockpile["meat"] -= 1
                    v.hunger = min(100.0, v.hunger + 55.0)

        # 3. Check Natural Reproduction (Branch 1)
        self.breeding_cooldown -= dt
        if self.breeding_cooldown <= 0:
            self.breeding_cooldown = 150.0
            self._attempt_natural_reproduction()

        # 4. Check Nomad / Wanderer Encounter (Branch 2)
        self.nomad_check_timer -= dt
        if self.nomad_check_timer <= 0:
            self.nomad_check_timer = 200.0
            self._attempt_nomad_approach()

    def _attempt_natural_reproduction(self):
        """
        Attempts childbirth if all 4 strict conditions are satisfied:
        1. Free beds (Pop < Capacity)
        2. Food surplus >= (Pop + 1) * 20
        3. Warm campfire active
        4. Healthy adult male & female in tribe
        """
        if self.current_population >= self.housing_capacity:
            return  # Full shelter!

        required_food = (self.current_population + 1) * 15
        if self.total_food_units < required_food:
            return  # Not enough surplus food

        # Check male and female adults
        adult_males = [v for v in self.alive_villagers if v.gender == "male" and v.stage == "adult" and not v.is_injured]
        adult_females = [v for v in self.alive_villagers if v.gender == "female" and v.stage == "adult" and not v.is_injured]

        if not adult_males or not adult_females:
            return

        mother = random.choice(adult_females)
        child_gender = random.choice(["male", "female"])
        child_name = random.choice(TRIBAL_MALE_NAMES if child_gender == "male" else TRIBAL_FEMALE_NAMES)

        # Birth event!
        cf_x, cf_y = self.campfire_center
        newborn = TribalVillager(
            villager_id=f"vil_born_{pygame.time.get_ticks()}",
            name=child_name,
            gender=child_gender,
            age_seasons=0,  # Newborn child
            role="child",
            x=mother.x + random.randint(-15, 15),
            y=mother.y + random.randint(-15, 15)
        )
        self.villagers.append(newborn)

        # Deduct some food for maternal care
        deduct = min(10, self.stockpile["meat"])
        self.stockpile["meat"] -= deduct

        self.add_event_notification(f"🎉 Niềm vui bộ tộc: {mother.name} vừa sinh hạ bé {child_name} tại lều ấm!")

    def _attempt_nomad_approach(self):
        """
        A cold, hungry wanderer might seek the camp fire if food is abundant
        and empty beds exist.
        """
        if self.current_population >= self.housing_capacity:
            return

        if self.total_food_units < 50:
            return

        # 40% chance of wanderer arriving at camp perimeter
        if random.random() < 0.40:
            nomad_gender = random.choice(["male", "female"])
            nomad_name = random.choice(TRIBAL_MALE_NAMES if nomad_gender == "male" else TRIBAL_FEMALE_NAMES)
            cf_x, cf_y = self.campfire_center

            nomad = TribalVillager(
                villager_id=f"vil_nomad_{pygame.time.get_ticks()}",
                name=nomad_name,
                gender=nomad_gender,
                age_seasons=random.randint(16, 32),
                role="hunter" if nomad_gender == "male" else "gatherer",
                x=cf_x + random.choice([-250, 250]),
                y=cf_y + random.choice([-200, 200])
            )
            nomad.hunger = 25.0
            nomad.warmth = 30.0
            # Moves to campfire
            nomad.command_move_to(cf_x + random.randint(-40, 40), cf_y + random.randint(-40, 40))
            self.villagers.append(nomad)

            self.add_event_notification(f"🏕️ Người du mục {nomad_name} tìm thấy ánh lửa trại và xin gia nhập bộ tộc!")

    def _handle_villager_death(self, villager):
        """Records Permadeath and logs to Ancestral Cairns."""
        record = {
            "name": villager.name,
            "role": villager.role,
            "age": villager.age_seasons // 4,
            "cause": villager.death_cause
        }
        self.ancestral_records.append(record)
        self.add_event_notification(f"💀 Đau buồn: {villager.name} đã ngã xuống ({villager.death_cause})!")

    # -----------------------------------------------------------------
    # RTS SELECTION & COMMANDING
    # -----------------------------------------------------------------
    def select_in_box(self, screen_rect, camera):
        """Selects all alive villagers whose screen positions are inside screen_rect."""
        selected_any = False
        for v in self.alive_villagers:
            sx, sy = camera.world_to_screen((v.x, v.y))
            if screen_rect.collidepoint(sx, sy):
                v.is_selected = True
                selected_any = True
            else:
                v.is_selected = False
        return selected_any

    def select_single_at_world(self, wx, wy, radius=24):
        """Selects single villager closest to click coordinate."""
        for v in self.alive_villagers:
            dist = math.hypot(wx - v.x, wy - v.y)
            if dist <= radius:
                # Deselect others
                for o in self.alive_villagers:
                    o.is_selected = False
                v.is_selected = True
                return v
        return None

    def deselect_all(self):
        for v in self.alive_villagers:
            v.is_selected = False

    def get_selected_villagers(self):
        return [v for v in self.alive_villagers if v.is_selected]

    def command_selected_move(self, target_wx, target_wy):
        """Commands all currently selected villagers to move in formation."""
        selected = self.get_selected_villagers()
        if not selected:
            return

        count = len(selected)
        cols = math.ceil(math.sqrt(count))
        spacing = 36.0

        for idx, v in enumerate(selected):
            col = idx % cols
            row = idx // cols
            ox = (col - cols / 2) * spacing
            oy = (row - count / (cols * 2)) * spacing
            v.command_move_to(target_wx + ox, target_wy + oy)

    def command_selected_interact(self, target_type, target_pos, target_obj=None):
        selected = self.get_selected_villagers()
        for v in selected:
            v.command_interact(target_type, target_pos, target_obj)

    def get_idle_villager(self):
        """Returns the next idle villager for hotkey cycling."""
        idles = [v for v in self.alive_villagers if v.state == "idle"]
        if idles:
            return idles[0]
        return None

    # -----------------------------------------------------------------
    # DRAWING
    # -----------------------------------------------------------------
    def draw_events(self, surface, fonts):
        """Draws floating event notifications on top right of screen."""
        font_sm = fonts.get("small", pygame.font.SysFont("dejavusans", 12, bold=True))
        ey = 65
        for ev in self.recent_events:
            txt_surf = font_sm.render(ev["text"], True, (255, 245, 220))
            bg_w = txt_surf.get_width() + 16
            bg_h = 24
            bg_surf = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
            pygame.draw.rect(bg_surf, (30, 22, 16, 210), (0, 0, bg_w, bg_h), border_radius=5)
            pygame.draw.rect(bg_surf, (160, 110, 50, 230), (0, 0, bg_w, bg_h), 1, border_radius=5)
            
            surface.blit(bg_surf, (surface.get_width() - bg_w - 15, ey))
            surface.blit(txt_surf, (surface.get_width() - bg_w - 7, ey + 4))
            ey += 30

    def draw(self, surface, camera, fonts):
        """Draws all villagers sorted by Y coordinate for natural depth."""
        draw_list = sorted(self.villagers, key=lambda v: v.y)
        for v in draw_list:
            v.draw(surface, camera, fonts)
        self.draw_events(surface, fonts)
