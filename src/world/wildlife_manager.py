"""
Autonomous Wildlife Ecosystem Manager.
Quản lý Hệ sinh thái Động vật Tiền sử (Hoàn toàn tự vận hành, không có con người):
- Đồng bộ sinh cảnh ôn đới: Bò rừng (Ancient Bison), Hươu lớn (Giant Deer),
  Lợn rừng (Wild Boar), Gấu núi đá (Cave Bear), Sói săn mồi theo đàn (Dire Wolf).
- AI Sinh thái (FSM): Idle/Rest -> SeekFood (Đồng cỏ/Bụi quả) -> SeekWater (Bãi bồi bờ sông)
  -> Flee/Chase (Tương tác Thú săn mồi - Con mồi) -> ReturnToHerd.
"""

import pygame
import random
import math
from src.settings import TILE_SIZE, MAP_COLS, MAP_ROWS
from src.entities.wildlife import PrehistoricBeast


class WildlifeManager:
    def __init__(self, map_mgr=None):
        self.map_mgr = map_mgr
        self.beasts = []
        self.respawn_timer = 120.0
        self.animal_tracks = []  # Dấu chân động vật lưu lại trên bùn/cát ẩm
        self._spawn_valley_ecosystem()

    def _spawn_valley_ecosystem(self):
        """Phân bổ các loài đúng với sinh cảnh địa lý của thung lũng (không trộn loài lệch đới khí hậu)."""
        ts = TILE_SIZE

        # 1. Động vật ăn cỏ cỡ lớn: Đàn Bò rừng (Ancient Bison) ở Đồng cỏ trung tâm (Open Meadow)
        for bx, by in [(26, 34), (29, 36), (31, 33), (28, 39)]:
            self.beasts.append(PrehistoricBeast("ancient_bison", bx * ts, by * ts, self.map_mgr))

        # 2. Đàn Hươu/Nai sừng lớn (Giant Deer) ở rìa Rừng hỗn hợp & Bãi cỏ ven suối
        for dx, dy in [(52, 28), (55, 31), (50, 35), (22, 48), (25, 50)]:
            self.beasts.append(PrehistoricBeast("giant_deer", dx * ts, dy * ts, self.map_mgr))

        # 3. Động vật ăn tạp: Lợn rừng (Wild Boar) kiếm củ/quả rụng dưới tán rừng & bờ bùn
        for wx, wy in [(42, 44), (45, 46), (34, 24), (36, 26)]:
            self.beasts.append(PrehistoricBeast("wild_boar", wx * ts, wy * ts, self.map_mgr))

        # 4. Gấu núi đá (Cave Bear) ở vùng Đồi đá Tây-Bắc & Thượng nguồn suối (bắt cá/ăn quả)
        for cx, cy in [(14, 18), (64, 20)]:
            self.beasts.append(PrehistoricBeast("cave_bear", cx * ts, cy * ts, self.map_mgr))

        # 5. Động vật ăn thịt: Đàn Sói (Dire Wolf) tuần tra sườn đồi và rìa rừng
        for vx, vy in [(18, 28), (20, 30), (60, 42), (62, 45)]:
            self.beasts.append(PrehistoricBeast("dire_wolf", vx * ts, vy * ts, self.map_mgr))

    def update(self, dt: float, villagers=None, player=None, settlement_mgr=None):
        """
        Cập nhật hành vi sinh thái tự nhiên của toàn bộ quần thể động vật.
        (Giữ tham số mặc định = None để tương thích ngược nếu vòng lặp cũ còn truyền vào).
        """
        alive_beasts = [b for b in self.beasts if not b.is_dead]

        for b in alive_beasts:
            self._update_ecological_ai(b, dt, alive_beasts)
            b.update(dt, alive_beasts)

            # Lưu lại dấu chân khi thú đi qua đất bùn hoặc cát ướt ven sông
            if self.map_mgr and random.random() < 0.08:
                col = int(b.x // TILE_SIZE)
                row = int(b.y // TILE_SIZE)
                if 0 <= col < MAP_COLS and 0 <= row < MAP_ROWS:
                    if self.map_mgr.soil_type[row][col] in ("mud_silt", "sand"):
                        self.animal_tracks.append({
                            "x": b.x, "y": b.y, "z": b.z, "life": 45.0, "max_life": 45.0
                        })

        # Làm mờ dần dấu chân trên bùn theo thời gian
        for tr in self.animal_tracks:
            tr["life"] -= dt
        self.animal_tracks = [tr for tr in self.animal_tracks if tr["life"] > 0]
        if len(self.animal_tracks) > 150:
            self.animal_tracks = self.animal_tracks[-150:]

        # Cân bằng sinh thái & Tái sinh tự nhiên
        self.respawn_timer -= dt
        if self.respawn_timer <= 0:
            self.respawn_timer = 150.0
            self.beasts = [b for b in self.beasts if not b.is_dead]
            if len(self.beasts) < 14:
                spawn_type = random.choice(["ancient_bison", "giant_deer", "wild_boar"])
                sx = random.randint(20, MAP_COLS - 20) * TILE_SIZE
                sy = random.randint(20, MAP_ROWS - 20) * TILE_SIZE
                self.beasts.append(PrehistoricBeast(spawn_type, sx, sy, self.map_mgr))

    def _update_ecological_ai(self, beast, dt: float, all_beasts: list):
        """
        Máy trạng thái hữu hạn (FSM) điều khiển tập tính tự nhiên:
        - Con mồi phát hiện thú săn mồi trong bán kính 180px -> Bỏ chạy (Flee).
        - Thú ăn cỏ định kỳ di chuyển ra bãi bồi bờ sông uống nước (SeekWater) hoặc tụ về đàn (ReturnToHerd).
        """
        is_predator = (getattr(beast, "type", "") or getattr(beast, "beast_type", "")) in ("dire_wolf", "cave_bear", "sabertooth")

        if not is_predator:
            # Kiểm tra mối đe dọa từ thú săn mồi gần đó
            for other in all_beasts:
                if (getattr(other, "type", "") or getattr(other, "beast_type", "")) in ("dire_wolf", "cave_bear", "sabertooth"):
                    dist = math.hypot(beast.x - other.x, beast.y - other.y)
                    if dist < 180.0 and dist > 1.0:
                        # Bỏ chạy ngược hướng thú săn mồi
                        dx = (beast.x - other.x) / dist
                        dy = (beast.y - other.y) / dist
                        beast.target_x = max(128, min((MAP_COLS - 3) * TILE_SIZE, beast.x + dx * 160))
                        beast.target_y = max(128, min((MAP_ROWS - 3) * TILE_SIZE, beast.y + dy * 160))
                        return

            # Tập tính ra bờ sông uống nước hoặc đi theo đàn
            if self.map_mgr and random.random() < 0.005:
                row = max(5, min(MAP_ROWS - 6, int(beast.y // TILE_SIZE)))
                river_c = self.map_mgr.get_river_center_float(row)
                hw = self.map_mgr.get_river_half_width_float(row)
                bank_col = river_c - hw - 2.0 if beast.x < river_c * TILE_SIZE else river_c + hw + 2.0
                beast.target_x = bank_col * TILE_SIZE
                beast.target_y = row * TILE_SIZE

    def get_beast_at_world(self, wx, wy, radius=48):
        for b in self.beasts:
            if not b.is_dead and b.hitbox.collidepoint(wx, wy):
                return b
        return None

    def draw(self, surface, camera, fonts, fog_of_war=None):
        """Vẽ dấu chân động vật trên bãi bồi/bùn và vẽ các cá thể thú theo chiều sâu Y."""
        for tr in self.animal_tracks:
            z_offset = self.map_mgr.get_height_screen_offset(tr.get("z", 0.5)) if self.map_mgr else 0.0
            sx, sy = camera.world_to_screen((tr["x"], tr["y"]), z_offset)
            if 0 <= sx <= surface.get_width() and 0 <= sy <= surface.get_height():
                alpha = int(110 * (tr["life"] / tr["max_life"]))
                tr_surf = pygame.Surface((10, 8), pygame.SRCALPHA)
                pygame.draw.ellipse(tr_surf, (55, 42, 30, alpha), (0, 0, 4, 6))
                pygame.draw.ellipse(tr_surf, (55, 42, 30, alpha), (5, 2, 4, 6))
                surface.blit(tr_surf, (sx - 5, sy - 4))

        sorted_beasts = sorted(self.beasts, key=lambda b: b.y)
        for b in sorted_beasts:
            b.draw(surface, camera, fonts)
