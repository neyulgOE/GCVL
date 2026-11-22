# Kiến trúc Pipeline Sinh Thế Giới — Godot 4 (.NET / C#)

Dự án sử dụng quy trình sinh thế giới **100% Procedural từ Seed** trong C# và kết xuất trực tiếp bằng GPU qua `Forward+` Vulkan:

1. **`FastNoise.cs`**: Gradient Perlin-style 2D, fBm, Ridged multifractal và Domain Warping.
2. **`WorldGenerator.cs`**: Tính toán trường độ cao liên tục `SamplePoint(x, z)` kết hợp rãnh sông uốn khúc `SampleRiverSpine(z)` và thềm biển.
3. **`TerrainManager.cs` + `TerrainChunk.cs`**: Chia vùng thành các Chunk `128m × 128m` (`65 × 65` đỉnh), tính pháp tuyến bằng sai phân trung tâm trên trường liên tục nên không có đường nối giữa các chunk.
4. **`WaterSurface.cs`**: Tạo mặt biển phẳng ở `SeaLevel = 0.0m` và dải lưới sông (`RiverRibbon`) chảy xuôi theo độ dốc thung lũng.
5. **Shaders (`.gdshader`)**:
   - `terrain_triplanar.gdshader`: Phân tầng vật liệu theo độ cao, độ dốc và `riverMask`/`moisture` kết hợp chi tiết triplanar không giãn trên vách đá đứng.
   - `water_river_ocean.gdshader`: Hấp thụ ánh sáng theo độ sâu (`DEPTH_TEXTURE`), khúc xạ (`SCREEN_TEXTURE`), phản chiếu Fresnel và bọt trắng ven bờ.
