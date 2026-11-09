# BỘ ĐÓNG GÓI TẤT CẢ TRONG 1 (ALL-IN-ONE): THỜI ĐỒ ĐÁ RTS (STONE AGE RTS & COLONY SIM)

Gói `stone_age_rts_complete_all_in_one_bundle.zip` này đóng gói **toàn bộ 100% hình ảnh (128 PNG đã tách nền + 17 Master Sheets + 6 Atlas Poster), dữ liệu tọa độ JSON và toàn bộ mã nguồn Game/Engine (HTML5 All-in-One + JS + Python)** vào 1 file duy nhất.

---

## 1. CẤU TRÚC THƯ MỤC TRONG FILE ĐÓNG GÓI

1. **`00_GAME_PLAYABLE_SINGLE_FILE/stone_age_map_preview_and_viewport.html`**
   - **File đơn chạy ngay (Single-File All-in-One HTML5 Game, ~4.5 MB)**: Đã nhúng sẵn toàn bộ 58 sprite PNG (Base64), CSS giao diện Thời Đồ Đá, bộ sinh bản đồ lục địa `200x200` ô, Map Preview 2.5D, Minimap tròn, AI "Dân Ngu" Bộ Lạc (FSM), chọn đội hình RTS (Marquee Box-Selection) và hệ thống Motion Bước Đi Tách Khớp Chân (`drawAnimatedCharacterOrBeast`).
   - **Cách dùng**: Chỉ cần mở trực tiếp bằng bất kỳ trình duyệt nào (Chrome, Edge, Firefox, Safari) — không cần cài đặt hay kết nối mạng.

2. **`01_SOURCE_CODE_AND_ENGINE/`**
   - `stone_age_rts_engine.js`: Toàn bộ mã nguồn JavaScript của hệ thống (World Generator 200x200, Off-screen Map Preview Baker, Minimap Renderer, NPC Villager FSM AI, RTS Selection/Command Controller, và Split-Body Walk/Work Motion Engine).
   - `procedural_stone_age_world_generator.py`: Mã nguồn Python sinh bản đồ lục địa 200x200, giải phương trình nước ngầm Darcy, tìm đường mù A* và xuất ảnh bản đồ 2.5D.
   - `stone_age_sprite_slicer_pipeline.py`: Script Python tự động khử nền và cắt 128 sprite PNG trong suốt từ các tấm Master Sheet.
   - `build_webapp.py`: Script đóng gói toàn bộ tài nguyên PNG và mã nguồn thành 1 file `.html` duy nhất.

3. **`02_SLICED_SPRITES_128_PNG/`**
   - Chứa **128 file PNG nền trong suốt (RGBA)** chia thành 11 thư mục chuyên biệt:
     - `01_units_villagers/` (40 frames: Dân hái lượm, Thợ đốn củi, Thợ săn phóng lao, Chiến binh chùy xương, Pháp sư cầm đuốc)
     - `02_megafauna_wildlife/` (18 frames: Voi Ma Mút, Hổ Răng Kiếm, Bò Rừng Thảo Nguyên, Lợn Lòi)
     - `03_buildings_structures/` (6 công trình: Hang Đá Cội Nguồn, Lều Da Thú, Xưởng Đá Lửa, Giàn Phơi Thịt, Đàn Tế Cự Thạch, Cổng Rào Gỗ)
     - `04_prehistoric_trees_and_wood/` (12 cây cổ đại, gốc cây và bó củi)
     - `05_forageable_flora_3stages/` (24 sprite hệ thực vật 3 giai đoạn sinh trưởng: Quả mọng, Nấm, Củ mài, Lúa mì hoang, Bụi sậy)
     - `06_terrain_tiles_and_cliffs/` (5 mảng địa hình liền mạch)
     - `07_ui_hud_and_tech_icons/` (10 khung HUD đá hổ phách, khung Minimap tròn & icon tài nguyên)
     - `08_decals_and_footprints/` (Dấu chân bùn, tuyết, tro lửa trại)
     - `09_trailblazing_and_waypoints/` (4 cột đá chỉ đường & totem cảnh báo)
     - `10_scouts_and_mapmaking_items/` (16 frames Trinh sát cầm đuốc, Chó săn, Dân mở đường đắp đá & Cầu gỗ)
     - `11_weather_groundwater_and_disasters/` (6 hiệu ứng Suối nước nóng, Mạch nước ngầm, Giếng đá, Tuyết đóng băng, Lũ quét & Cháy rừng)
   - Kèm file `atlas_manifest.json` liệt kê kích thước, đường dẫn và thông số từng sprite.

4. **`03_MASTER_SHEETS_AND_ATLAS_POSTERS/`**
   - 17 tấm ảnh gốc độ phân giải cao (`00_master_sheets_full_res/`)
   - 6 tấm bản đồ và bảng tổng hợp trực quan (`stone_age_sliced_sprites_catalog.png`, `stone_age_25d_terraced_map_preview.png`, `stone_age_biome_stitching_terrace_atlas.png`, `stone_age_flora_foraging_atlas.png`, `stone_age_mapping_pathfinding_atlas.png`, `stone_age_physics_weather_disasters_atlas.png`, `stone_age_world_tactical_atlas.png`).
