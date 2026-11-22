# Primeval Reach (GCVL) — Godot 4 (.NET / C#)

Mô phỏng thế giới tự nhiên tiền sử 3D thời gian thực bằng **Godot 4.7 (.NET 8 / C#)** với **Forward+ Vulkan Renderer**.

> Bản prototype Python/Pygame cũ đã được đóng băng và lưu trữ nguyên vẹn tại nhánh `archive/python-prototype`.

---

## Kiến trúc Clean Slate

```text
PrimevalWorld/
├── project.godot               # Cấu hình Godot 4.7 Forward+ & C#
├── PrimevalWorld.csproj        # Dự án .NET 8 (Godot.NET.Sdk/4.7.2)
├── run.sh                      # Khởi chạy bằng GPU rời NVIDIA PRIME Offload
├── scenes/
│   └── Main.tscn               # Scene chính Chặng 1 (Vertical Slice 1x1 km)
├── shaders/
│   ├── terrain_triplanar.gdshader  # Shader địa hình đa tầng (cát, cỏ, vách đá triplanar, tuyết)
│   └── water_river_ocean.gdshader  # Shader nước (sóng, Fresnel, độ sâu, bọt bờ)
├── src/
│   ├── Core/MainController.cs      # WorldEnvironment (ProceduralSky, Shadow, ACES, Depth Fog) & HUD
│   ├── WorldGen/                   # Sinh địa hình 100% toán học theo Seed
│   ├── Terrain/                    # TerrainChunks pháp tuyến mượt & mặt nước sông/biển
│   └── Camera/                     # Spectator Free Camera mượt
└── docs/                           # Tài liệu thiết kế & kiến trúc
```

---

## Lộ trình Vertical Slice (4 Chặng)

1. **Chặng 1 (Hiện tại) — Vertical Slice 1×1 km:** Địa hình procedural C# theo Seed chia thành 8×8 Terrain Chunks (`128m × 128m`), Triplanar Terrain Shader, dòng sông cắt lõm với Water Shader, bầu trời `ProceduralSkyMaterial` + `DirectionalLight3D` đổ bóng mềm + `ACES` + `Depth Fog`, Free Camera & HUD đổi Seed.
2. **Chặng 2 — Hệ sinh thái thực vật 6 tầng:** GPU Instancing (`MultiMeshInstance3D`) phân bổ theo độ dốc và khoảng cách tới sông.
3. **Chặng 3 — Thế giới Đa lục địa & Bản đồ `[M]`:** Mở rộng 4 lục địa / 5 quần xã bằng SDF + Climate/Moisture thuần toán học và Chunk Streaming.
4. **Chặng 4 — Động vật cổ đại (Utility AI) & Chu kỳ 4 mùa.**

---

## Khởi chạy trên Linux (NVIDIA RTX 4060 / Forward+)

```bash
./run.sh
```

Điều khiển: `WASD` di chuyển | `Chuột phải + kéo` xoay | `Q/E` lên xuống | `Shift` bay nhanh | `Cuộn chuột` chỉnh tốc độ | `G` đổi Seed mới | `R` đặt lại camera | `ESC` thoát.
