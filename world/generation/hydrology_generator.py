"""
world/generation/hydrology_generator.py
Phase 4: Hệ thống Thủy văn Lưu vực (Priority-Flood, D8 Flow Routing,
Watershed Delineation, Exorheic vs. Endorheic Lakes, River Network & GeoJSON Export).
Đảm bảo 100% sông suối chảy xuôi chiều cao độ từ núi/hồ băng xuống biển hoặc bồn địa nội lưu.
"""

from dataclasses import dataclass
import heapq
import math
from typing import List, Dict, Any, Tuple
import numpy as np

from world.config.world_config import WorldConfig
from world.generation.landmass_generator import LandmassResult
from world.generation.geology_generator import GeologyResult
from world.generation.terrain_generator import TerrainResult
from world.generation.climate_generator import ClimateResult


# 8 hướng lân cận D8: (dr, dc)
D8_OFFSETS: Tuple[Tuple[int, int], ...] = (
    (-1, 0), (-1, 1), (0, 1), (1, 1),
    (1, 0), (1, -1), (0, -1), (-1, -1),
)


@dataclass
class HydrologyResult:
    filled_heightmap: np.ndarray     # Độ cao sau khi xử lý Priority-Flood [0..1]
    flow_dir_idx: np.ndarray         # Chỉ số hướng chảy D8 (0..7, -1 = điểm thu nước cuối)
    flow_accumulation: np.ndarray    # Tích lũy dòng chảy có trọng số lượng mưa
    watershed_id: np.ndarray         # Mã lưu vực (int32)
    stream_order: np.ndarray         # Cấp bậc sông suối (0 = không sông, 1..5 = suối -> sông cái)
    river_mask: np.ndarray           # Mặt nạ sông suối (bool)
    river_width: np.ndarray          # Bề rộng lòng sông [px] mở rộng dần về hạ lưu
    lake_mask: np.ndarray            # Mặt nạ toàn bộ hồ nước ngọt & hồ nội lưu
    endorheic_lake_mask: np.ndarray  # Mặt nạ riêng cho Hồ Nội Lưu vùng khuất mưa Tây Nam
    delta_mask: np.ndarray           # Vùng châu thổ / cửa sông Nam & Vịnh Nội Địa
    river_features: List[Dict[str, Any]]  # Danh sách nhánh sông để xuất GeoJSON & kiểm định


class HydrologyGenerator:
    def __init__(self, config: WorldConfig) -> None:
        self.cfg = config

    def _priority_flood_with_endorheic_sink(
        self,
        landmass: LandmassResult,
        geology: GeologyResult,
        terrain: TerrainResult,
        climate: ClimateResult,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Thuật toán Priority-Flood đảm bảo mọi ô đất liền đều có đường thoát nước đơn điệu:
        - Toàn bộ đường bờ biển là lối thoát ra đại dương (Exorheic Outlets).
        - Duy nhất tâm bồn địa khô hạn Tây Nam (Rain Shadow Basin) được giữ làm điểm thu nước
          nội lưu (Endorheic Sink) để tạo Hồ Nội Lưu tự nhiên.
        """
        h, w = self.cfg.height, self.cfg.width
        elev = terrain.final_heightmap.copy()
        land = landmass.landmask

        # Xác định vùng lõi Hồ Nội Lưu ở bồn địa khuất mưa Tây Nam
        ny, nx = np.meshgrid(
            np.linspace(0.0, 1.0, h, dtype=np.float32),
            np.linspace(0.0, 1.0, w, dtype=np.float32),
            indexing="ij",
        )
        sw_sink_score = (
            geology.basin_field
            * climate.rain_shadow
            * np.exp(-(((nx - 0.29) / 0.055) ** 2 + ((ny - 0.65) / 0.055) ** 2))
            * land
        )
        endorheic_lake = sw_sink_score > 0.14
        # Hạ nhẹ đáy bồn địa Tây Nam để thu nước vùng khuất mưa
        elev = np.where(endorheic_lake, np.minimum(elev, self.cfg.sea_level + 0.035), elev)

        # Khởi tạo hàng đợi ưu tiên (Min-Heap) từ biển và tâm hồ nội lưu
        visited = np.zeros((h, w), dtype=bool)
        filled = elev.copy()
        pq: List[Tuple[float, int, int]] = []

        # Đưa các ô biển sát bờ và tâm hồ nội lưu vào Heap
        for r in range(h):
            for c in range(w):
                if not land[r, c] or endorheic_lake[r, c]:
                    visited[r, c] = True
                    heapq.heappush(pq, (float(filled[r, c]), r, c))

        eps = 1e-5
        while pq:
            cur_z, r, c = heapq.heappop(pq)
            for dr, dc in D8_OFFSETS:
                nr, nc = r + dr, c + dc
                if 0 <= nr < h and 0 <= nc < w and not visited[nr, nc]:
                    visited[nr, nc] = True
                    if filled[nr, nc] <= cur_z:
                        filled[nr, nc] = cur_z + eps
                    heapq.heappush(pq, (float(filled[nr, nc]), nr, nc))

        # Các vùng trũng được làm đầy lớn hơn ngưỡng trên núi cao/đồng bằng -> Tạo Hồ Nước Ngọt (Exorheic Lakes)
        depression_depth = filled - elev
        freshwater_lakes = (
            land
            & (~endorheic_lake)
            & (
                (depression_depth > 0.012)
                | (
                    # Hồ băng thượng nguồn phía Bắc & Hồ lớn Đông Bắc
                    (np.exp(-(((nx - 0.44) / 0.035) ** 2 + ((ny - 0.20) / 0.030) ** 2)) > 0.55)
                    | (np.exp(-(((nx - 0.63) / 0.042) ** 2 + ((ny - 0.35) / 0.036) ** 2)) > 0.52)
                )
            )
        )
        all_lakes = freshwater_lakes | endorheic_lake

        return filled, all_lakes, endorheic_lake

    def generate(
        self,
        landmass: LandmassResult,
        geology: GeologyResult,
        terrain: TerrainResult,
        climate: ClimateResult,
    ) -> HydrologyResult:
        h, w = self.cfg.height, self.cfg.width
        land = landmass.landmask

        # 1. Xử lý hố trũng bằng Priority-Flood & tạo hệ thống Hồ
        filled, lake_mask, endorheic_lake_mask = self._priority_flood_with_endorheic_sink(
            landmass, geology, terrain, climate
        )

        # 2. Tính hướng dòng chảy D8 (Luôn chảy xuống ô lân cận có độ dốc lớn nhất)
        flow_dir_idx = np.full((h, w), -1, dtype=np.int8)
        for r in range(h):
            for c in range(w):
                if not land[r, c] or endorheic_lake_mask[r, c]:
                    continue
                z = filled[r, c]
                best_slope = 0.0
                best_k = -1
                for k, (dr, dc) in enumerate(D8_OFFSETS):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < h and 0 <= nc < w:
                        dist = 1.41421356 if (dr != 0 and dc != 0) else 1.0
                        drop = (z - filled[nr, nc]) / dist
                        if drop > best_slope:
                            best_slope = drop
                            best_k = k
                flow_dir_idx[r, c] = best_k

        # 3. Tích lũy dòng chảy (Flow Accumulation) có trọng số theo Lượng mưa + Băng tan Bắc Cao
        ny_line = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
        snowmelt_bonus = np.where((ny_line < 0.28) & (terrain.final_heightmap > 0.62), 0.55, 0.0)
        runoff_weight = (0.25 + climate.precipitation * 1.35 + snowmelt_bonus) * land

        flow_accum = runoff_weight.copy().astype(np.float32)

        # Sắp xếp toàn bộ ô đất nổi theo độ cao giảm dần (từ đỉnh núi xuống cửa biển)
        land_coords = np.argwhere(land)
        land_elevs = filled[land_coords[:, 0], land_coords[:, 1]]
        sorted_order = np.argsort(-land_elevs)

        for idx in sorted_order:
            r, c = int(land_coords[idx, 0]), int(land_coords[idx, 1])
            k = int(flow_dir_idx[r, c])
            if k >= 0:
                dr, dc = D8_OFFSETS[k]
                nr, nc = r + dr, c + dc
                if 0 <= nr < h and 0 <= nc < w:
                    flow_accum[nr, nc] += flow_accum[r, c]

        # 4. Định danh Lưu vực (Watershed Delineation) bằng cách truyền ngược ID từ cửa sông/hồ nội lưu
        watershed_id = np.zeros((h, w), dtype=np.int32)
        next_ws_id = 1
        # Duyệt từ thấp lên cao để gán mã lưu vực
        for idx in reversed(sorted_order):
            r, c = int(land_coords[idx, 0]), int(land_coords[idx, 1])
            k = int(flow_dir_idx[r, c])
            if k < 0:
                watershed_id[r, c] = next_ws_id
                next_ws_id += 1
            else:
                dr, dc = D8_OFFSETS[k]
                nr, nc = r + dr, c + dc
                if not land[nr, nc] or endorheic_lake_mask[nr, nc]:
                    # Gom các cửa thoát nước gần nhau vào cùng lưu vực lớn
                    coarse_outlet_id = ((nr // 16) * 64 + (nc // 16)) + 10
                    watershed_id[r, c] = coarse_outlet_id
                else:
                    watershed_id[r, c] = watershed_id[nr, nc]

        # 5. Phân cấp Mạng lưới Sông suối (Stream Ordering & River Width)
        stream_order = np.zeros((h, w), dtype=np.uint8)
        stream_order = np.where(flow_accum >= 28.0, 1, stream_order)   # Suối đầu nguồn (Headwater)
        stream_order = np.where(flow_accum >= 75.0, 2, stream_order)   # Phụ lưu nhỏ (Minor Tributary)
        stream_order = np.where(flow_accum >= 190.0, 3, stream_order)  # Phụ lưu chính (Major Tributary)
        stream_order = np.where(flow_accum >= 450.0, 4, stream_order)  # Sông lớn (Main River)
        stream_order = np.where(flow_accum >= 950.0, 5, stream_order)  # Đại giang / Cửa sông (Estuary Trunk)
        stream_order = (stream_order * land).astype(np.uint8)

        river_mask = (stream_order >= 1) & (~lake_mask)

        # Bề rộng lòng sông tăng theo hàm căn bậc hai của lưu lượng (Hydraulic Geometry)
        river_width = np.where(
            river_mask,
            np.clip(np.sqrt(flow_accum / 25.0), 1.0, 4.5),
            0.0,
        ).astype(np.float32)

        # Mở rộng mặt nạ sông cho các dòng sông cấp 4-5 ở hạ lưu
        thick_river_mask = river_mask.copy()
        major_cells = np.argwhere(stream_order >= 4)
        for r, c in major_cells:
            rad = 1 if stream_order[r, c] == 4 else 2
            r0, r1 = max(0, r - rad), min(h, r + rad + 1)
            c0, c1 = max(0, c - rad), min(w, c + rad + 1)
            thick_river_mask[r0:r1, c0:c1] |= land[r0:r1, c0:c1]

        # Hạ nhẹ độ cao tại lòng sông để khắc thung lũng sông khớp 100% với địa hình
        terrain.final_heightmap = np.where(
            thick_river_mask,
            np.maximum(self.cfg.sea_level + 0.003, terrain.final_heightmap - 0.018 * stream_order),
            terrain.final_heightmap,
        )

        # 6. Xác định vùng Cửa sông Châu thổ (Southern Delta & Inland Bay Estuaries)
        coastal_band = land & (terrain.final_heightmap < self.cfg.sea_level + 0.045)
        delta_mask = coastal_band & (flow_accum >= 120.0)

        # 7. Trích xuất Vector các nhánh sông thành cấu trúc GeoJSON (Kiểm định độ dốc đơn điệu)
        river_features = self._extract_river_geojson_features(
            filled, flow_dir_idx, flow_accum, stream_order, land
        )

        return HydrologyResult(
            filled_heightmap=filled.astype(np.float32),
            flow_dir_idx=flow_dir_idx,
            flow_accumulation=flow_accum,
            watershed_id=watershed_id,
            stream_order=stream_order,
            river_mask=thick_river_mask,
            river_width=river_width,
            lake_mask=lake_mask,
            endorheic_lake_mask=endorheic_lake_mask,
            delta_mask=delta_mask,
            river_features=river_features,
        )

    def _extract_river_geojson_features(
        self,
        filled: np.ndarray,
        flow_dir_idx: np.ndarray,
        flow_accum: np.ndarray,
        stream_order: np.ndarray,
        land: np.ndarray,
    ) -> List[Dict[str, Any]]:
        """Trích xuất các tuyến sông chính thành LineString GeoJSON kèm dữ liệu độ cao từng nút."""
        h, w = filled.shape
        visited_edge = np.zeros((h, w), dtype=bool)
        features: List[Dict[str, Any]] = []

        # Lấy các điểm khởi đầu của suối từ cấp 2 trở lên
        candidates = np.argwhere(stream_order >= 2)
        # Ưu tiên truy vết từ thượng nguồn cao nhất xuống hạ lưu
        cand_elevs = filled[candidates[:, 0], candidates[:, 1]]
        order_idx = np.argsort(-cand_elevs)

        for idx in order_idx:
            sr, sc = int(candidates[idx, 0]), int(candidates[idx, 1])
            if visited_edge[sr, sc]:
                continue

            coords: List[List[float]] = []
            elev_trace: List[float] = []
            curr_r, curr_c = sr, sc
            max_ord = int(stream_order[sr, sc])

            for _ in range(h + w):
                coords.append([float(curr_c), float(curr_r)])
                elev_trace.append(round(float(filled[curr_r, curr_c]), 5))
                max_ord = max(max_ord, int(stream_order[curr_r, curr_c]))

                k = int(flow_dir_idx[curr_r, curr_c])
                if k < 0:
                    break
                dr, dc = D8_OFFSETS[k]
                nr, nc = curr_r + dr, curr_c + dc
                if not (0 <= nr < h and 0 <= nc < w):
                    break

                # Nếu nhập vào một dòng sông lớn đã được vẽ trước đó, thêm điểm hợp lưu rồi dừng
                if visited_edge[nr, nc]:
                    coords.append([float(nc), float(nr)])
                    elev_trace.append(round(float(filled[nr, nc]), 5))
                    visited_edge[curr_r, curr_c] = True
                    break

                visited_edge[curr_r, curr_c] = True
                if not land[nr, nc]:
                    coords.append([float(nc), float(nr)])
                    elev_trace.append(round(float(filled[nr, nc]), 5))
                    break

                curr_r, curr_c = nr, nc

            if len(coords) >= 5:
                features.append({
                    "type": "Feature",
                    "properties": {
                        "stream_order": max_ord,
                        "length_nodes": len(coords),
                        "source_elevation": elev_trace[0],
                        "mouth_elevation": elev_trace[-1],
                        "elevations": elev_trace,
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coords,
                    },
                })

        return features

