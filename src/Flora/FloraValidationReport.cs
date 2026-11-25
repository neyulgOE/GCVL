using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.Text;
using System.Threading.Tasks;
using Godot;
using PrimevalWorld.Core;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Flora
{
    /// <summary>
    /// Batch A Quantitative Canopy & Spatial Integrity Auditor:
    /// - Rasterizes true Union of Crown Disks at 2048 x 1152 (4.6875m/px, 32x32 px per 150m x 150m sample cell)
    ///   so overlapping tree crowns never exceed 1.00 (100%).
    /// - Measures per-ecosystem: Trees/km2, Canopy Coverage (Mean / P50 / P95), Min & Mean Nearest-Neighbor distance,
    ///   Crown Overlap Rate (%), Megafauna Corridor share (%), and Deep Water (> 0.30m) violation count.
    /// - Compares directly against ecological targets with [PASS / GAP] diagnostics for Batch B tuning.
    /// </summary>
    public static class FloraValidationReport
    {
        private const int RasterW = 2048;
        private const int RasterH = 1152;
        private const float PixelSizeM = WorldPhysicsConfig.WorldWidth / RasterW; // 4.6875m
        private const int PixelsPerSampleCell = 32; // 32 * 4.6875m = 150.0m exact!

        public static void RunAndPrint(FloraManager floraMgr, HydrologySolver hydrology)
        {
            var sw = Stopwatch.StartNew();
            EcosystemSpawner spawner = floraMgr.Spawner;
            var trees = spawner.AcceptedWoodyRecords;
            int nTrees = trees.Count;

            // 1. Rasterize Union of Woody Crown Disks onto 2048 x 1152 grid (values 0 or 1)
            byte[] unionMask = new byte[RasterW * RasterH];
            for (int i = 0; i < nTrees; i++)
            {
                WoodyTreeRecord t = trees[i];
                float r = t.ActualCrownRadiusM;
                float rSq = r * r;

                int xMin = Math.Max(0, (int)((t.X - r) / PixelSizeM));
                int xMax = Math.Min(RasterW - 1, (int)((t.X + r) / PixelSizeM));
                int zMin = Math.Max(0, (int)((t.Z - r) / PixelSizeM));
                int zMax = Math.Min(RasterH - 1, (int)((t.Z + r) / PixelSizeM));

                for (int pz = zMin; pz <= zMax; pz++)
                {
                    float wz = (pz + 0.5f) * PixelSizeM;
                    float dz = wz - t.Z;
                    float dzSq = dz * dz;
                    int rowOff = pz * RasterW;
                    for (int px = xMin; px <= xMax; px++)
                    {
                        float wx = (px + 0.5f) * PixelSizeM;
                        float dx = wx - t.X;
                        if (dx * dx + dzSq <= rSq)
                            unionMask[rowOff + px] = 1;
                    }
                }
            }

            // 2. Group 150m x 150m Sample Cells (64 x 36) by Dominant Ecosystem & Measure Raster Union Coverage
            var cellCoveragesByEco = new List<float>[8];
            for (int e = 1; e <= 7; e++)
                cellCoveragesByEco[e] = new List<float>(512);

            int vertW = WorldPhysicsConfig.VertW;
            int vertH = WorldPhysicsConfig.VertH;
            Span<int> ecoPixCounts = stackalloc int[8];
            Span<int> ecoCovCounts = stackalloc int[8];

            for (int cz = 0; cz < FloraLodConfig.NearRows; cz++)
            {
                int pzStart = cz * PixelsPerSampleCell;
                for (int cx = 0; cx < FloraLodConfig.NearCols; cx++)
                {
                    int pxStart = cx * PixelsPerSampleCell;
                    ecoPixCounts.Clear();
                    ecoCovCounts.Clear();
                    int landPix = 0;

                    for (int lz = 0; lz < PixelsPerSampleCell; lz++)
                    {
                        int pz = pzStart + lz;
                        int gz = Math.Min(vertH - 1, pz >> 1);
                        int rOff = pz * RasterW;
                        int gOff = gz * vertW;

                        for (int lx = 0; lx < PixelsPerSampleCell; lx++)
                        {
                            int px = pxStart + lx;
                            int gx = Math.Min(vertW - 1, px >> 1);
                            int ecoId = (int)spawner.EcosystemMap[gOff + gx];
                            if (ecoId >= 1 && ecoId <= 7)
                            {
                                landPix++;
                                ecoPixCounts[ecoId]++;
                                if (unionMask[rOff + px] != 0)
                                    ecoCovCounts[ecoId]++;
                            }
                        }
                    }

                    // Require >= 40% emergent land pixels in the 150m x 150m sample cell
                    if (landPix < 410) continue;

                    int domEco = 1;
                    int bestCnt = -1;
                    for (int e = 1; e <= 7; e++)
                    {
                        if (ecoPixCounts[e] > bestCnt)
                        {
                            bestCnt = ecoPixCounts[e];
                            domEco = e;
                        }
                    }

                    if (bestCnt >= 128)
                    {
                        float cov = ecoCovCounts[domEco] / (float)bestCnt;
                        cellCoveragesByEco[domEco].Add(cov);
                    }
                }
            }

            // 3. Spatial Grid Nearest-Neighbor Distance & Crown Overlap Rate across all Woody Trees
            const float gridStep = 16.0f;
            int gw = (int)(WorldPhysicsConfig.WorldWidth / gridStep) + 1;
            int gh = (int)(WorldPhysicsConfig.WorldDepth / gridStep) + 1;
            var buckets = new List<int>?[gw * gh];
            for (int i = 0; i < nTrees; i++)
            {
                int bx = Math.Clamp((int)(trees[i].X / gridStep), 0, gw - 1);
                int bz = Math.Clamp((int)(trees[i].Z / gridStep), 0, gh - 1);
                int bIdx = bz * gw + bx;
                var list = buckets[bIdx];
                if (list == null)
                {
                    list = new List<int>(8);
                    buckets[bIdx] = list;
                }
                list.Add(i);
            }

            float[] nnDists = new float[nTrees];
            bool[] hasOverlap = new bool[nTrees];

            Parallel.For(0, nTrees, i =>
            {
                WoodyTreeRecord ti = trees[i];
                int bx = Math.Clamp((int)(ti.X / gridStep), 0, gw - 1);
                int bz = Math.Clamp((int)(ti.Z / gridStep), 0, gh - 1);

                float bestDistSq = float.MaxValue;
                bool overlapped = false;
                const int maxRing = 20; // up to 320m search radius

                for (int ring = 0; ring <= maxRing; ring++)
                {
                    if (ring >= 3)
                    {
                        float minPossible = (ring - 1) * gridStep;
                        if (minPossible * minPossible > bestDistSq)
                            break;
                    }

                    int z0 = Math.Max(0, bz - ring);
                    int z1 = Math.Min(gh - 1, bz + ring);
                    int x0 = Math.Max(0, bx - ring);
                    int x1 = Math.Min(gw - 1, bx + ring);

                    for (int nz = z0; nz <= z1; nz++)
                    {
                        for (int nx = x0; nx <= x1; nx++)
                        {
                            if (ring > 0 && nz > bz - ring && nz < bz + ring && nx > bx - ring && nx < bx + ring)
                                continue; // Only check perimeter of expanding ring!

                            var cell = buckets[nz * gw + nx];
                            if (cell == null) continue;

                            for (int k = 0; k < cell.Count; k++)
                            {
                                int j = cell[k];
                                if (j == i) continue;
                                WoodyTreeRecord tj = trees[j];
                                float dx = ti.X - tj.X;
                                float dz = ti.Z - tj.Z;
                                float dSq = dx * dx + dz * dz;
                                if (dSq < bestDistSq)
                                    bestDistSq = dSq;

                                if (!overlapped)
                                {
                                    float sumR = ti.ActualCrownRadiusM + tj.ActualCrownRadiusM;
                                    if (dSq < sumR * sumR)
                                        overlapped = true;
                                }
                            }
                        }
                    }
                }

                nnDists[i] = bestDistSq < float.MaxValue ? MathF.Sqrt(bestDistSq) : 320.0f;
                hasOverlap[i] = overlapped;
            });

            // 4. Aggregate per Ecosystem + Corridor & Deep Water Integrity
            int[] ecoTreeCount = new int[8];
            float[] ecoMinNn = new float[8];
            double[] ecoSumNn = new double[8];
            int[] ecoOverlapCnt = new int[8];
            int corridorTrees = 0;
            int deepWaterWoody = 0;

            for (int e = 1; e <= 7; e++)
                ecoMinNn[e] = float.MaxValue;

            for (int i = 0; i < nTrees; i++)
            {
                WoodyTreeRecord t = trees[i];
                int e = (int)t.Ecosystem;
                if (e >= 1 && e <= 7)
                {
                    ecoTreeCount[e]++;
                    if (nnDists[i] < ecoMinNn[e]) ecoMinNn[e] = nnDists[i];
                    ecoSumNn[e] += nnDists[i];
                    if (hasOverlap[i]) ecoOverlapCnt[e]++;
                }
                if (t.CorridorValue >= 0.35f) corridorTrees++;
                float maxAllowedDepth = t.ToleratesShallowFlood ? 0.45f : 0.30f;
                if (t.WaterDepthM > maxAllowedDepth) deepWaterWoody++;
            }

            sw.Stop();
            var inv = CultureInfo.InvariantCulture;
            float cellAreaKm2 = (WorldPhysicsConfig.CellSize * WorldPhysicsConfig.CellSize) * 1e-6f;
            int totalDeepWater = deepWaterWoody + spawner.DeepWaterDetailCount;
            float corridorPct = nTrees > 0 ? corridorTrees * 100.0f / nTrees : 0.0f;

            // Compare MultiMeshInstance3D count: Previous 150m Static All-Mounted (24,941) vs New Dynamic Pool + 600m LOD2 (< 1,200!)
            var ecotoneSample = floraMgr.SamplePerspectiveTelemetry(new Vector3(6350f, 32f, 3420f), new Vector3(6420f, 28f, 3260f));
            var forestCoreSample = floraMgr.SamplePerspectiveTelemetry(new Vector3(7650f, 65f, 3150f), new Vector3(7950f, 55f, 2950f));

            var sb = new StringBuilder(2048);
            sb.AppendLine();
            sb.AppendLine(string.Create(inv, $"=== [Phase 0 Flora Streaming & Canopy Audit | AuditTime={sw.Elapsed.TotalMilliseconds:F1}ms] ==="));
            sb.AppendLine(string.Create(inv, $"[MultiMeshNodeAudit] PrevStaticAllMounted=24,941 | NewStaticLOD2_600m={floraMgr.Lod2NodeCount:N0} | Mounted@FloodplainEdge={ecotoneSample.MountedNodes:N0} | Mounted@ForestInterior={forestCoreSample.MountedNodes:N0} (Target < 1,200)"));
            sb.AppendLine(string.Create(inv, $"[SamplePerspective@FloodplainEdge] BucketActive(LOD0/1/2)={ecotoneSample.Lod0:N0} / {ecotoneSample.Lod1:N0} / {ecotoneSample.Lod2:N0} | ShadowTrees={ecotoneSample.Shadow:N0} (<=LOD0: {(ecotoneSample.Shadow <= ecotoneSample.Lod0 ? "PASS" : "FAIL")}) | VisibleNodes={ecotoneSample.VisNodes:N0}/{ecotoneSample.MountedNodes:N0}"));
            sb.AppendLine(string.Create(inv, $"[SamplePerspective@ForestInterior] BucketActive(LOD0/1/2)={forestCoreSample.Lod0:N0} / {forestCoreSample.Lod1:N0} / {forestCoreSample.Lod2:N0} | ShadowTrees={forestCoreSample.Shadow:N0} (<=LOD0: {(forestCoreSample.Shadow <= forestCoreSample.Lod0 ? "PASS" : "FAIL")}) | VisibleNodes={forestCoreSample.VisNodes:N0}/{forestCoreSample.MountedNodes:N0}"));
            sb.AppendLine("[CanopyCoverageReport] Raster=2048x1152 (4.69m/px Union) | SampleCell=150x150m:");
            sb.AppendLine("  Ecosystem             | Area(km2) | Trees/km2 | Cov Mean / P50 / P95  | NN Min / Mean | Overlap% | Target Eval");
            sb.AppendLine("  ----------------------+-----------+-----------+-----------------------+---------------+----------+-------------------------");

            string[] names =
            {
                "",
                "1. PrimevalForest    ",
                "2. AlluvialFloodplain",
                "3. WetlandDelta      ",
                "4. OpenSteppe        ",
                "5. AridRedDesert     ",
                "6. AlpineSnowRock    ",
                "7. CoastlineDunes    "
            };

            for (int e = 1; e <= 7; e++)
            {
                float areaKm2 = MathF.Max(0.01f, spawner.EcosystemLandCounts[e] * cellAreaKm2);
                float treesPerKm2 = ecoTreeCount[e] / areaKm2;

                var covList = cellCoveragesByEco[e];
                covList.Sort();
                float meanCov = 0.0f, p50Cov = 0.0f, p95Cov = 0.0f;
                if (covList.Count > 0)
                {
                    double sum = 0.0;
                    for (int k = 0; k < covList.Count; k++) sum += covList[k];
                    meanCov = (float)(sum / covList.Count);
                    p50Cov = covList[(int)((covList.Count - 1) * 0.50f)];
                    p95Cov = covList[(int)((covList.Count - 1) * 0.95f)];
                }

                float minNn = ecoTreeCount[e] > 0 ? ecoMinNn[e] : 0.0f;
                float meanNn = ecoTreeCount[e] > 0 ? (float)(ecoSumNn[e] / ecoTreeCount[e]) : 0.0f;
                float overlapPct = ecoTreeCount[e] > 0 ? ecoOverlapCnt[e] * 100.0f / ecoTreeCount[e] : 0.0f;
                string status = EvaluateTarget(e, meanCov, p50Cov);

                sb.AppendLine(string.Create(inv,
                    $"  {names[e]} | {areaKm2,9:F2} | {treesPerKm2,9:F0} | {meanCov,5:F2} / {p50Cov,4:F2} / {p95Cov,4:F2}   | {minNn,5:F2}m / {meanNn,5:F2}m | {overlapPct,7:F1}% | {status}"));
            }

            int activeFloraSpecies = 0;
            int maxWoodyCount = 0;
            string maxWoodyKey = "-";
            int birchCount = spawner.SpeciesCounts[(int)FloraSpeciesId.WeepingSilverBirch];
            for (int s = 0; s < FloraNicheDatabase.AllSpecies.Length; s++)
            {
                var prof = FloraNicheDatabase.AllSpecies[s];
                int c = spawner.SpeciesCounts[s];
                if (!prof.IsGeological && c > 0) activeFloraSpecies++;
                if (prof.Layer <= FloraLayer.Canopy && c > maxWoodyCount)
                {
                    maxWoodyCount = c;
                    maxWoodyKey = prof.SpeciesKey;
                }
            }
            float maxWoodyPct = nTrees > 0 ? maxWoodyCount * 100.0f / nTrees : 0.0f;
            float birchPct = nTrees > 0 ? birchCount * 100.0f / nTrees : 0.0f;

            string waterEval = deepWaterWoody == 0 && totalDeepWater == 0 ? "[PASS]" : $"[GAP: woody={deepWaterWoody}, detail={spawner.DeepWaterDetailCount}]";
            sb.AppendLine(string.Create(inv, $"[SpeciesAudit] ActiveFloraSpecies={activeFloraSpecies}/59 | MaxWoody={maxWoodyKey} ({maxWoodyPct:F1}%, Target <= 16%) | Birch={birchCount:N0} ({birchPct:F1}%, Target 6-10%)"));
            sb.AppendLine(string.Create(inv, $"[AquaticAudit] DeepWaterWoody(>0.30m, flood-exempt<=0.45m)={deepWaterWoody} | AquaticFloating(water_lily)={spawner.WaterLilyValidDepth:N0}/{spawner.WaterLilyTotal:N0} (0.15-1.25m) | UnderwaterBenthic(sea_kelp)={spawner.SeaKelpValidDepth:N0}/{spawner.SeaKelpTotal:N0} (0.45-2.80m)"));
            sb.AppendLine(string.Create(inv, $"[IntegrityCheck] CorridorWoodyTrees={corridorPct:F2}% ({corridorTrees:N0}/{nTrees:N0}) | DeepWaterFlora(>0.30m)={totalDeepWater} (Woody={deepWaterWoody}, Detail={spawner.DeepWaterDetailCount}) -> {waterEval}"));
            GD.Print(sb.ToString());
        }

        private static string EvaluateTarget(int ecoId, float meanCov, float p50Cov) => ecoId switch
        {
            1 => (meanCov >= 0.80f && meanCov <= 0.95f) ? "[PASS] (0.80-0.95)" : string.Create(CultureInfo.InvariantCulture, $"[GAP: want 0.80-0.95, got {meanCov:F2}]"),
            2 => (meanCov >= 0.01f && meanCov <= 0.04f) ? "[PASS] (0.01-0.04)" : string.Create(CultureInfo.InvariantCulture, $"[GAP: want 0.01-0.04, got {meanCov:F2}]"),
            3 => (meanCov >= 0.15f && meanCov <= 0.30f) ? "[PASS] (0.15-0.30)" : string.Create(CultureInfo.InvariantCulture, $"[GAP: want 0.15-0.30, got {meanCov:F2}]"),
            4 => (meanCov >= 0.05f && meanCov <= 0.16f && p50Cov <= 0.06f) ? "[PASS] (Groves)" : string.Create(CultureInfo.InvariantCulture, $"[GAP: want Mean 0.05-0.16 & P50<=0.06, got {meanCov:F2}/{p50Cov:F2}]"),
            5 => (meanCov <= 0.04f && p50Cov <= 0.01f) ? "[PASS] (Oasis/Wadi)" : string.Create(CultureInfo.InvariantCulture, $"[GAP: want Mean<=0.04 & P50<=0.01, got {meanCov:F2}/{p50Cov:F2}]"),
            6 => (meanCov <= 0.10f) ? "[PASS] (<=0.10)" : string.Create(CultureInfo.InvariantCulture, $"[GAP: want <=0.10, got {meanCov:F2}]"),
            7 => (meanCov >= 0.01f && meanCov <= 0.12f) ? "[PASS] (0.01-0.12)" : string.Create(CultureInfo.InvariantCulture, $"[GAP: want 0.01-0.12, got {meanCov:F2}]"),
            _ => "[N/A]",
        };
    }
}
