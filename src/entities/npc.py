"""
NPC (Non-Player Character) Entity System for Stone Age: Dawn of Tribe.
Represents Stone Tribe Elders, Shamans, and Hunters with personalities,
patience gauges for tribal barter, and rich dialogues.
"""

import pygame
import random
from src.settings import TILE_SIZE

class NPC:
    def __init__(self, npc_id, name, role, col, row, personality="friendly"):
        self.id = npc_id
        self.name = name
        self.role = role
        self.col = col
        self.row = row
        self.x = col * TILE_SIZE
        self.y = row * TILE_SIZE
        self.personality = personality
        
        # State
        self.patience = 100
        self.friendship = 15
        self.facing = "down"
        self.anim_frame = 0
        self.anim_timer = 0.0

        self._init_dialogues()

    def _init_dialogues(self):
        if self.id in ["toc_truong_ogg", "cu_ba_tri"]:
            self.avatar_color = (210, 140, 50)
            self.greeting = "Hỡi người anh em tiền sử! Căn cứ của ngươi đã nhóm được lửa trại chưa? Bộ tộc Núi Đá luôn sẵn sàng tương trợ!"
            self.success_quotes = [
                "Ha ha! Lời đề nghị rất xứng đáng với một chiến binh quả cảm. Ta đồng ý trao đổi!",
                "Đúng là người có tầm nhìn thủ lĩnh! Bộ lạc ta chấp thuận mức giá này.",
                "Tốt lắm! Sự thịnh vượng của ngươi cũng là sự phát triển của cả bộ tộc ta!"
            ]
            self.fail_quotes = [
                "Vỏ sò ít ỏi thế này không đủ để đổi lấy bảo vật tổ tiên đâu bạn trẻ!",
                "Thần núi không cho phép ta trao đổi với mức giá rẻ mạt như vậy.",
                "Ngươi ép giá quá đấy, thần linh không hài lòng đâu!"
            ]
            self.angry_quote = "Đủ rồi! Tộc trưởng ta cần tĩnh tâm làm lễ, ngươi hãy lui ra!"

        elif self.id in ["thay_mo_kraa", "co_mai"]:
            self.avatar_color = (70, 180, 130)
            self.greeting = "Thần linh rừng thẳm thì thầm trong gió... Ta nắm giữ hạt giống cổ xưa và tri thức dược thảo chữa lành."
            self.success_quotes = [
                "Gió lành đã thổi qua! Thảo mộc và hạt giống thần này thuộc về ngươi.",
                "Hương cỏ hoang dã chứng giám cho sự công bằng, ta đồng ý mức đổi này!",
                "Lời nói của ngươi êm dịu như dòng suối đầu nguồn, chốt trao đổi!"
            ]
            self.fail_quotes = [
                "Linh hồn cây rừng lắc đầu... Lễ vật ngươi đưa chưa đủ thành tâm.",
                "Hạt giống nguyên thủy quý báu lắm, không thể đổi rẻ được đâu.",
                "Chưa được rồi, đất mẹ đòi hỏi sự công bằng hơn thế."
            ]
            self.angry_quote = "Màn sương che mờ tâm trí... Ta không thể tiếp tục bàn luận với kẻ tham lam!"

        elif self.id in ["tho_san_boomer", "bac_bay"]:
            self.avatar_color = (190, 85, 45)
            self.greeting = "Cầm chắc rìu và giáo lên! Thiên nhiên hoang dã chỉ khuất phục trước công cụ sắc bén và lòng can đảm!"
            self.success_quotes = [
                "Khá lắm! Ngươi biết nhìn nhận giá trị của quặng quý và vũ khí tốt. Ta đồng ý!",
                "Sòng phẳng và dứt khoát! Ta ưng cái bụng rồi đấy, chốt trao đổi!",
                "Được! Đồ nghề của thợ săn chỉ truyền cho người xứng đáng!"
            ]
            self.fail_quotes = [
                "Cầm mấy cái vỏ sò vụn này mà đòi đổi rìu sắc của ta à? Quên đi!",
                "Đá lửa và quặng đồng phải đổi bằng mồ hôi xương máu, giá đó không bán!",
                "Kỳ kèo kiểu đó sang thung lũng khác mà nhặt cành cây khô!"
            ]
            self.angry_quote = "Biến đi cho ta ghè đá! Đừng làm vướng tay thợ săn!"
        else:
            self.avatar_color = (180, 160, 130)
            self.greeting = f"Chào người bạn tiền sử! Tôi là {self.name}."
            self.success_quotes = ["Đồng ý trao đổi!"]
            self.fail_quotes = ["Vật phẩm chưa đủ tương xứng."]
            self.angry_quote = "Hết kiên nhẫn rồi!"

    def reset_daily_patience(self):
        self.patience = 100

    def update(self, dt):
        self.anim_timer += dt
        if self.anim_timer >= 0.4:
            self.anim_timer = 0.0
            self.anim_frame = (self.anim_frame + 1) % 2

    def is_player_near(self, px, py, radius=TILE_SIZE * 2.2):
        cx = self.x + TILE_SIZE // 2
        cy = self.y + TILE_SIZE // 2
        dist_sq = (px - cx) ** 2 + (py - cy) ** 2
        return dist_sq <= radius ** 2
