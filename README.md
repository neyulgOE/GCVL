# Primeval Reach (GCVL) — Godot 4.7 (.NET 8 / C#)

Mô phỏng thế giới tự nhiên tiền sử 3D thời gian thực quy mô **`9.6 × 5.4 km` (~51.8 km²)** bằng **Godot 4.7 (.NET 8 / C#)** với **Forward+ Vulkan Renderer**.

> Bản prototype Python/Pygame cũ đã được đóng băng và lưu trữ nguyên vẹn tại nhánh `archive/python-prototype`.

---

## Kiến trúc Hiện tại (Hoàn thành Giai đoạn 1–4 + Animal POV)

```text
PrimevalWorld/
├── project.godot                       # Cấu hình Godot 4.7 Forward+ & .NET 8
├── PrimevalWorld.csproj                # Dự án .NET 8 (Godot.NET.Sdk/4.7.2)
├── run.sh                              # Khởi chạy bằng GPU rời NVIDIA PRIME Offload
├── test.sh                             # Smoke Test tự động (dotnet build + godot4 --headless + df)
├── assets/
│   └── maps/
│       └── primeval_reach_canonical.jpg # Macro Blueprint 4 đại lục gốc
├── docs/                               # Tài liệu thiết kế (PIPELINE.md, VEGETATION.md, PDF/DOCX)
├── scenes/
│   └── Main.tscn                       # Scene chính 9.6 × 5.4 km
├── shaders/
│   ├── terrain_triplanar.gdshader      # Triplanar 6 loại đất, tuyết/ẩm động, bóng mây, Beer-Lambert mùn rừng
│   ├── water_river_ocean.gdshader      # Biển chân trời 48 km, sông dốc, bọt thác, dâng nước & đóng băng hồ
│   ├── foliage_wind.gdshader           # Gió thực tế theo 3 kiểu thân, đổi màu 4 mùa & tuyết phủ tán
│   └── cloud_canopy.gdshader           # Mây bão tầng cao (1,380m) trôi theo trường gió
└── src/
    ├── Core/
    │   ├── WorldPhysicsConfig.cs       # Hằng số SI (9600x5400m, núi 620m, lưới 1025x577, 32x18 chunks)
    │   ├── SimulationClock.cs          # Đồng hồ thiên văn 24h & 4 mùa (120 ngày/năm, nghiêng trục 23.4°)
    │   └── MainController.cs           # Điều phối pipeline, ánh sáng thiên văn, HUD & Bản đồ [M] 8 lớp
    ├── WorldGen/
    │   ├── TectonicContinentGen.cs     # Khôi phục 4 đại lục gốc + tách Bedrock/Sediment
    │   ├── ErosionPhysics.cs           # Xói mòn nhiệt (32°/40°/64°), thủy lực 90k giọt & cồn cát gió
    │   ├── HydrologySolver.cs          # Dòng chảy D8, thủy văn Q = A·v & mạch nước ngầm
    │   ├── AtmosphereClimate.cs        # Trường gió, nhiệt độ, bóng mưa sườn núi & vi khí hậu
    │   ├── SoilPedology.cs             # 6 loại đất chuẩn hóa & xuất GPU data textures
    │   ├── WorldMapVisualizer.cs       # Bản đồ phân tích 8 lớp + Radar thời tiết [M]
    │   └── FastNoise.cs                # Noise & SmoothStep đa luồng
    ├── Terrain/
    │   ├── TerrainChunk.cs             # Chunk 300x300m với LOD (>=8x8, khóa bờ biển LOD1) & Skirt 24m
    │   ├── TerrainChunkManager.cs      # Quản lý 576 chunks & cập nhật LOD theo camera
    │   └── WaterSurface.cs             # Biển 48 km & sông/hồ nội địa
    ├── Flora/
    │   ├── FloraNicheDatabase.cs       # 36 loài cổ sinh, 6 tầng tán, 4 nhóm thân, 14 dáng (tỷ lệ 0.65x)
    │   ├── FloraMeshLibrary.cs         # 14 nguyên mẫu procedural ArrayMesh + ưu tiên nạp .glb
    │   ├── EcosystemSpawner.cs         # Trồng rừng 2 pha, Self-Thinning, Beer-Lambert LAI & vòng cộng sinh
    │   └── FloraManager.cs             # Spatial Streaming 2 cấp (16x9 vĩ mô + 64x36 vi mô quanh camera)
    ├── Weather/
    │   ├── SeasonalState.cs            # Nhiệt tức thời, tích tụ/tan tuyết, độ ẩm mặt, đóng băng & dâng sông
    │   ├── DynamicWeatherSystem.cs     # Mô phỏng 2 Hz (256x144), 5 xoáy bão trôi theo gió & Orographic Boost
    │   └── LocalWeatherVfx.cs          # GPUParticles3D cục bộ quanh camera (Mưa / Tuyết / Bão cát đỏ)
    └── Camera/
        └── SpectatorCamera.cs          # Bay tự do [0] + 3 Góc nhìn Động vật [V]: Sói (0.85m), Bò Rừng (1.65m), Ma Mút (3.6m)
```

---

## Các Giai đoạn đã hoàn thành

1. **Giai đoạn 1 — Địa chất, Thủy văn Vật lý & Chunk LOD (`9.6 × 5.4 km`):** Lưới `1025 × 577`, 576 terrain chunks (`32 × 18`, khóa bờ biển tối thiểu LOD1 `16×16`), xói mòn nhiệt theo góc nghỉ vật liệu, xói mòn thủy lực, dòng chảy $Q = A \cdot v$, tỷ lệ chuẩn `620m : 0.65x`.
2. **Giai đoạn 2 — Khí hậu, Bóng mưa & Thổ nhưỡng 6 loại đất:** Trường gió `WindDir/WindSpeed`, hiệu ứng bóng mưa sườn núi, 6 loại đất (`AlluvialLoam`, `ForestBrownSoil`, `SteppeLoess`, `AridRedSand`, `CoastalSand`, `PermafrostAndRock`) và Bản đồ `[M]`.
3. **Giai đoạn 3 — Hệ Sinh Thái Thực Vật Đa Hình Thái 6 Tầng Tán:** 36 loài cổ sinh phân theo **4 nhóm cấu trúc thân** & **14 dáng mesh** (hỗ trợ `.glb` tại `assets/models/flora/<species_id>.glb`), suy giảm ánh sáng Beer–Lambert, vòng cộng sinh quanh gốc, cơ học gió 3 cấp và Spatial Streaming 2 cấp.
4. **Giai đoạn 4 — Chu kỳ 24h, 4 Mùa & Thời tiết Động 2 Hz:** Mặt Trời/Mặt Trăng nghiêng trục `23.4°`, tuyết tích tụ/tan theo mùa, mặt nước đóng băng & dâng sông, đổi màu lá 4 mùa, mây tầng cao, hạt mưa/tuyết/bão cát cục bộ và Radar `[M]` Lớp 8.
5. **Công cụ Nghiệm thu — Góc nhìn Động vật `[V]`:** 3 mốc tầm mắt bám địa hình (`Sói 0.85m`, `Bò Rừng 1.65m`, `Voi Ma Mút 3.60m`) với `HeadBob`, giới hạn leo dốc, phản hồi cát/nước nông và chặn nước sâu.

---

## Kiểm thử & Khởi chạy

### Smoke Test tự động (Build + Headless + Disk Check)

```bash
./test.sh
```

### Chạy 3D trực tiếp (Linux / NVIDIA PRIME Offload)

```bash
./run.sh
```

### Phím điều khiển

* **Di chuyển & Camera:** `WASD` di chuyển | `Chuột phải + kéo` xoay | `E / Q` lên/xuống (ở chế độ Tự do) | `Shift` bay nhanh / chạy nước rút | `Cuộn chuột` chỉnh tốc độ bay (tối đa `1,000 m/s`) | `R` về toàn cảnh | `ESC` thoát.
* **Góc nhìn Động vật `[V]`:** Chuyển vòng `Tự do` $\rightarrow$ `Sói (0.85m)` $\rightarrow$ `Bò Rừng (1.65m)` $\rightarrow$ `Voi Ma Mút (3.60m)` (`Space` nhảy nhẹ ở chế độ Sói/Bò Rừng).
* **Khám phá & Bản đồ:** `1–5` nhảy sát 5 vùng sinh thái (`22–38m`) | `M` mở/đóng Bản đồ 8 lớp (bấm `1–8` để đổi lớp, click bản đồ để bay tới) | `F` bật/tắt thảm thực vật | `G` đổi Seed mới.
* **Thời gian & Thời tiết:** `Space` tạm dừng/chạy (ở chế độ Tự do) | `[` / `]` giảm/tăng tốc độ (`0x..300x`) | `T` tua `+3h` | `Y` nhảy sang mùa kế tiếp | `P` đổi chế độ thử nghiệm thời tiết.
