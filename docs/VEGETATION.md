# Kiến trúc Hệ Sinh Thái Thực Vật & LOD Không Gian (Godot 4.7 / C# / Forward+)

Tài liệu này mô tả hệ thống thực vật tiền sử 6 tầng và kiến trúc phân vùng LOD không gian hiện hành của **Primeval Reach** trên bản đồ **9.6 × 5.4 km** (`51.84 km²`, lưới vật lý `1025 × 577`, bước ô `9.375m`). Toàn bộ pipeline sinh thái, dựng mesh và streaming được viết thuần bằng **C# (.NET 8)** và **Godot 4 Spatial Shaders**, không phụ thuộc bất kỳ script Python tiền xử lý hay file `.json`/`.npz` tĩnh nào.

---

## 1. Các Module Cốt Lõi

| Thành phần | Đường dẫn | Vai trò chính |
| --- | --- | --- |
| **Bảng hằng số LOD hợp nhất** | `src/Flora/FloraLodConfig.cs` | Nguồn cấu hình duy nhất cho khoảng cách `LOD0 / LOD1 / LOD2`, dải dither `TransitionHalfBand`, `FarFade`, `CanopyGroundBlend`, `CellHysteresisMargin` và kích thước cell `150m` / `300m`. Truyền trực tiếp xuống shader uniform lúc khởi tạo. |
| **Cơ sở dữ liệu ổ sinh thái** | `src/Flora/FloraNicheDatabase.cs` | Định nghĩa 36 loài tiền sử chia thành **6 Tầng (`FloraLayer`)**, **4 Nhóm Thân (`StemGroup`)** và **14 Kiến trúc Hình thái (`FloraArchitecture`)**, đánh giá độ thích nghi theo nhiệt độ, độ ẩm, mực nước ngầm, gió, độ dốc, độ dày đất và độ mặn. |
| **Quy hoạch 7 Hệ sinh thái & Phân bố** | `src/Flora/EcosystemSpawner.cs` | Phân bổ 100% đất nổi thành 7 hệ sinh thái (Rừng già khép tán, Đồng bằng phù sa, Đầm lầy & Châu thổ, Thảo nguyên gió, Hoang mạc cát đỏ & Ốc đảo, Núi tuyết & Đá trơ, Bờ biển & Cồn cát); chạy tự tỉa thưa (Self-Thinning), tính ánh sáng đáy rừng Beer-Lambert, hành lang thú lớn và kiểm soát nghiêm ngặt `water_depth <= 0.30m`. |
| **Quản lý Cell Phân Cấp Thưa & Telemetry** | `src/Flora/FloraManager.cs` | Dựng static `MultiMeshInstance3D` theo **Hierarchical Sparse Cells** (`150×150m` cho LOD0/LOD1/L3–L6 và `300×300m` cho LOD2), quản lý bóng đổ chặt ở bucket gần, bật/tắt `LOD Debug View [L]` và đo telemetry thực tế ở tần số 4 Hz (0 GC allocation). |
| **Dựng cây phân cành & 3 tầng LOD** | `src/Flora/ProceduralTreeBuilder.cs`, `src/Flora/FloraMeshLibrary.cs` | Sinh mesh cây theo quy tắc ống dẫn Da Vinci và góc vàng `137.5°` ở 3 cấp chi tiết (`LOD0`, `LOD1`, `LOD2`), nướng trực tiếp **3D Canopy AO (`0.54..1.06`)** vào `UV2.x` và tách màu từng cá thể qua `INSTANCE_CUSTOM` để bảo toàn màu vỏ cây. |
| **Thảm cỏ & Dương xỉ GPU cận cảnh** | `src/Flora/GpuGrassRing.cs` | Vòng cỏ `30,000` bụi (`70m`) và thảm dương xỉ đáy rừng `9,000` bụi (`56m`) bám theo camera bằng `height_tex` thực (`Err = 0.000m`), 0 truy vấn địa hình CPU mỗi frame. |
| **Kiểm toán Định lượng Canopy & Không gian** | `src/Flora/FloraValidationReport.cs` | Đo **Canopy Coverage** thực tế bằng **Raster Union (`2048 × 1152`, `4.69m/px`)** trên từng ô mẫu `150m × 150m`, tính `Trees/km²`, `Mean / P50 / P95`, khoảng cách láng giềng gần nhất (`NN Min / Mean`), `Crown Overlap %` và kiểm tra `DeepWaterFlora (>0.30m) == 0`. |
| **Shader Thực vật & Mặt đất** | `shaders/flora_wind.gdshader`, `shaders/terrain_triplanar.gdshader` | Chuyển đổi mùa (Xuân xanh diệp lục, Thu vàng/đỏ cho cây rụng lá, Đông phủ tuyết), rung gió theo lưới khí tượng, cắt Alpha lá 1024×1024, **Bayer 4×4 Dither Crossfade** không lỗ hổng giữa các tầng LOD và hòa mượt sang **Canopy Ground Splatting** ở `1100–1350m`. |

---

## 2. Kiến Trúc 6 Tầng Thực Vật (`FloraLayer`)

1. **Tầng 1 — Vượt tán (`Emergent`, `22–32m`):** Đa cổ thụ rễ bạnh, Tùng Hồng Thủy Sam, Đại thụ Thánh địa, Bao báp cổ sinh.
2. **Tầng 2 — Tán chính (`Canopy`, `8–18m`):** Vú sữa cổ đại, Liễu rủ ven sông, Bạch dương rủ, Bạch quả cổ sinh, Phong thảo nguyên, Thông tuyết, Vân sam bạc, Cây Máu Rồng, Cổ thụ Xavan.
3. **Tầng 3 — Dưới tán & Thân cột (`Understory`, `1.0–8.5m`):** Dương xỉ thân gỗ, Tuế cổ đại, Khóm Vầu khổng lồ, Dừa nước / Cọ ốc đảo, Thông lùn Krummholz bò sát đá.
4. **Tầng 4 — Cây bụi rìa rừng (`Shrub`, `0.8–2.2m`):** Bụi quả dại, Sơn tra, Quả tuyết, Bụi gai khô (tập trung ở dải chuyển tiếp ánh sáng Ecotone).
5. **Tầng 5 — Thân thảo, Đầm lầy, Mọng nước & Dây leo (`HerbGround`, `0.22–1.8m`):** Cỏ lau bông trắng, Bãi sậy ven sông, Ráy tai voi, Cỏ lông vũ thảo nguyên, Thùa gai, Sen đá, Trầu bà leo gốc, Rêu ẩm, Nấm rừng, Rêu tuần lộc.
6. **Tầng 6 — Thảm mục & Địa chất (`LitterSoil`, `0.3–1.7m`):** Thân gỗ mục rỗng, Đất sét ven suối, Quặng đồng lộ thiên, Đá tảng.

---

## 3. Kiến Trúc Hierarchical Sparse Cells & Dither Crossfade (`FloraLodConfig`)

- **Phân vùng không gian thưa (Sparse Allocation — chỉ cấp phát node khi `count > 0`):**
  - `LOD0` (`0–150m`) & `LOD1` (`150–450m`): Lưới **`64 × 36` ô (`150m × 150m`)**, giảm một nửa bán kính sai lệch khoảng cách và giữ `CastShadow = On` duy nhất trên các ô `LOD0` gần camera.
  - `LOD2` (`450–1350m`): Lưới **`32 × 18` ô (`300m × 300m`)**, tắt hoàn toàn bóng đổ (`CastShadow = Off`) để tối ưu số lượng draw call ở tầm xa.
  - `L3–L6 Detail` (`0–400m`): Lưới **`64 × 36` ô (`150m × 150m`)**, bật/tắt theo bán kính xung quanh camera, `CastShadow = Off`.
- **Đồng bộ chuyển tiếp không giật cục (Zero-Popping Bayer 4×4 Dither):**
  - `LOD0 ↔ LOD1`: Giao thoa đối xứng qua ma trận Bayer 4×4 trong dải **`135m – 165m`** (`150m ± 15m`).
  - `LOD1 ↔ LOD2`: Giao thoa đối xứng trong dải **`435m – 465m`** (`450m ± 15m`).
  - `LOD2 ↔ Mặt đất`: Cả `FarFade` của `LOD2` và `CanopyGroundBlend` của `terrain_triplanar.gdshader` khóa chung dải **`1100m – 1350m`**.
  - `VisibilityRange` trên từng cell cộng biên an toàn tối thiểu bằng nửa đường chéo ô (`>= +110m` cho ô `150m`, `>= +215m` cho ô `300m`) kèm `CellHysteresisMargin = 25m`.

---

## 4. Phím Tắt Kiểm Chứng & Kiểm Thử

- **`[F]`**: Bật / tắt toàn bộ hệ thực vật.
- **`[L]`**: Bật / tắt **Chế độ Soi màu LOD (`LOD Debug View`)** — **Đỏ (`LOD0`)**, **Vàng (`LOD1`)**, **Xanh Cyan (`LOD2`)**.
- **`[M]` -> Phím `[7]` / `[8]`**: Mở bản đồ **Quy hoạch 7 Hệ sinh thái** và **Phân bố 36 loài & Độ che phủ tán**.
- **Chạy kiểm thử tự động & in báo cáo định lượng `FloraValidationReport`:**

```bash
./test.sh
./run.sh --flora-test
```
