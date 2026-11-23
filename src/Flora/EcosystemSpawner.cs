using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Threading.Tasks;
using Godot;
using PrimevalWorld.Core;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Flora
{
    public readonly struct FloraInstance
    {
        public readonly FloraSpeciesId Species;
        public readonly Transform3D Transform;
        public readonly Color Tint;

        public FloraInstance(FloraSpeciesId species, Transform3D transform, Color tint)
        {
            Species = species;
            Transform = transform;
            Tint = tint;
        }
    }

    /// <summary>
    /// Stage 3: 2-Phase Physical Ecosystem Spawner across the 9.6 x 5.4 km world:
    /// - Megafauna Migration Corridors (gentle open trails to point bars & fords)
    /// - Phase 1: Layer 1 (Emergent) & Layer 2 (Canopy) with Nucleation + Self-Thinning (target 45k-75k trees)
    /// - Beer-Lambert Light Attenuation: I = I0 * exp(-0.65 * LAI) -> GroundLightMap & CanopyCoverageMap
    /// - Phase 2: Layers 3-6 (Understory, Shrub, Herb/Ground, Litter/Geology) driven by GroundLight, Ecotone & Groundwater
    /// </summary>
    public sealed class EcosystemSpawner
    {
        public const int MacroCols = 16; // 600m x 600m macro cells for L1/L2 frustum culling
        public const int MacroRows = 9;
        public const float MacroCellSize = 600.0f;

        public const int MicroCols = 64; // 150m x 150m micro cells for L3-L6 dynamic streaming
        public const int MicroRows = 36;
        public const float MicroCellSize = 150.0f;

        private const int W = WorldPhysicsConfig.VertW;
        private const int H = WorldPhysicsConfig.VertH;
        private const float Cell = WorldPhysicsConfig.CellSize;

        public float[] LaiMap { get; } = new float[W * H];
        public float[] GroundLightMap { get; } = new float[W * H];
        public float[] CanopyCoverageMap { get; } = new float[W * H];
        public float[] CorridorMask { get; } = new float[W * H];
        public sbyte[] DominantSpeciesMap { get; } = new sbyte[W * H];

        public List<FloraInstance>[,] MacroCanopyCells { get; } = new List<FloraInstance>[MacroCols, MacroRows];
        public List<FloraInstance>[,] MicroDetailCells { get; } = new List<FloraInstance>[MicroCols, MicroRows];

        public int[] LayerCounts { get; } = new int[7]; // indices 1..6
        public int[] SpeciesCounts { get; } = new int[FloraNicheDatabase.AllSpecies.Length];
        public int TotalInstances { get; private set; }
        public double LastSpawnMs { get; private set; }

        private struct CandidateTree
        {
            public float X, Y, Z;
            public FloraSpeciesId Species;
            public float Radius;
            public float Height;
            public Color Tint;
            public Vector2 WindDir;
            public uint Hash;
        }

        public void Generate(
            ErosionPhysics erosion,
            HydrologySolver hydrology,
            AtmosphereClimate climate,
            SoilPedology soil,
            int seed)
        {
            var sw = Stopwatch.StartNew();

            Array.Clear(LaiMap, 0, LaiMap.Length);
            Array.Clear(CanopyCoverageMap, 0, CanopyCoverageMap.Length);
            Array.Clear(LayerCounts, 0, LayerCounts.Length);
            Array.Clear(SpeciesCounts, 0, SpeciesCounts.Length);
            Array.Fill(GroundLightMap, 1.0f);
            Array.Fill(DominantSpeciesMap, (sbyte)-1);
            TotalInstances = 0;

            for (int z = 0; z < MacroRows; z++)
                for (int x = 0; x < MacroCols; x++)
                    MacroCanopyCells[x, z] = new List<FloraInstance>(256);

            for (int z = 0; z < MicroRows; z++)
                for (int x = 0; x < MicroCols; x++)
                    MicroDetailCells[x, z] = new List<FloraInstance>(96);

            BuildMegafaunaCorridors(erosion, hydrology, seed);

            // ===================== PHASE 1: L1 EMERGENT + L2 CANOPY =====================
            var canopySpecies = new List<FloraNicheProfile>();
            foreach (var sp in FloraNicheDatabase.AllSpecies)
            {
                if (sp.Layer == FloraLayer.Emergent || sp.Layer == FloraLayer.Canopy)
                    canopySpecies.Add(sp);
            }

            const float step1 = 12.5f;
            int candW = (int)(WorldPhysicsConfig.WorldWidth / step1);
            int candH = (int)(WorldPhysicsConfig.WorldDepth / step1);
            var rowCandidates = new List<CandidateTree>[candH];

            Parallel.For(0, candH, cz =>
            {
                var list = new List<CandidateTree>(candW / 3);
                rowCandidates[cz] = list;
                float[] scores = new float[canopySpecies.Count];

                for (int cx = 0; cx < candW; cx++)
                {
                    uint hKey = Hash2D(cx, cz, seed + 17);
                    float jx = ((hKey & 0xFF) / 255.0f - 0.5f) * step1 * 0.88f;
                    float jz = (((hKey >> 8) & 0xFF) / 255.0f - 0.5f) * step1 * 0.88f;
                    float wx = cx * step1 + step1 * 0.5f + jx;
                    float wz = cz * step1 + step1 * 0.5f + jz;
                    if (wx < 20f || wx > WorldPhysicsConfig.WorldWidth - 20f || wz < 20f || wz > WorldPhysicsConfig.WorldDepth - 20f)
                        continue;

                    float h = erosion.SampleHeight(wx, wz);
                    if (h <= 0.45f) continue;

                    int gx = Math.Clamp((int)(wx / Cell), 0, W - 1);
                    int gz = Math.Clamp((int)(wz / Cell), 0, H - 1);
                    int gIdx = gz * W + gx;

                    if (hydrology.RiverMaskMap[gIdx] > 0.45f && hydrology.WaterDepthMap[gIdx] > 0.55f) continue;

                    float slopeDeg = erosion.SlopeDegMap[gIdx];
                    ClimateSample cs = climate.SampleClimate(wx, wz);
                    SoilSample ss = soil.SampleSoil(wx, wz);
                    float gw = hydrology.GroundwaterMap[gIdx];

                    // Megafauna corridor reduction (open migratory trails)
                    float corridor = CorridorMask[gIdx];
                    float corridorKeep = 1.0f - corridor * 0.82f;
                    if (((hKey >> 16) & 0xFF) / 255.0f > corridorKeep) continue;

                    float total = 0.0f;
                    float bestScore = 0.0f;
                    int bestIdx = -1;
                    for (int i = 0; i < canopySpecies.Count; i++)
                    {
                        float sc = canopySpecies[i].EvaluateSuitability(cs, ss, slopeDeg, gw, 1.0f);
                        // Moderate emergent probability so Emergent stays ~12-18% of Canopy
                        if (canopySpecies[i].Layer == FloraLayer.Emergent)
                            sc *= 0.42f;
                        scores[i] = sc;
                        total += sc;
                        if (sc > bestScore) { bestScore = sc; bestIdx = i; }
                    }

                    if (bestScore < 0.045f || bestIdx < 0) continue;

                    // Probability gate: dense closed canopy in humid cores, sparse natural groves in arid SW
                    float spawnProb = Math.Clamp(bestScore * 1.45f + ss.WAridRed * 0.12f, 0.04f, 0.94f);
                    float roll = ((hKey >> 24) & 0xFF) / 255.0f;
                    if (roll > spawnProb) continue;

                    // Weighted mixed-forest selection from top candidates
                    float pick = ((Hash2D(cx + 31, cz + 71, seed + 53) & 0xFFFF) / 65535.0f) * total;
                    float acc = 0.0f;
                    int chosen = bestIdx;
                    for (int i = 0; i < canopySpecies.Count; i++)
                    {
                        acc += scores[i];
                        if (acc >= pick) { chosen = i; break; }
                    }

                    FloraNicheProfile sp = canopySpecies[chosen];
                    float tVar = (Hash2D(cx * 3, cz * 5, seed + 109) & 0xFF) / 255.0f;
                    float height = Mathf.Lerp(sp.HeightMinM, sp.HeightMaxM, tVar);
                    float scaleFactor = height / ((sp.HeightMinM + sp.HeightMaxM) * 0.5f);

                    // Individual color variation (cold frost, autumn gold/crimson mix, interior shade)
                    float hueShift = ((Hash2D(cx + 7, cz + 13, seed + 211) & 0xFF) / 255.0f - 0.5f) * 0.14f;
                    Color tint = ShiftTint(sp.BaseTint, hueShift, cs.TemperatureC, sp.Id);

                    list.Add(new CandidateTree
                    {
                        X = wx, Y = h, Z = wz,
                        Species = sp.Id,
                        Radius = sp.CrownRadiusM * scaleFactor,
                        Height = height,
                        Tint = tint,
                        WindDir = cs.WindDir,
                        Hash = hKey
                    });
                }
            });

            // Self-Thinning Pass via Spatial Hash Grid (cell = 12m)
            const float thinCell = 12.0f;
            int shW = (int)(WorldPhysicsConfig.WorldWidth / thinCell) + 1;
            int shH = (int)(WorldPhysicsConfig.WorldDepth / thinCell) + 1;
            var spatialGrid = new List<int>[shW * shH];
            var acceptedTrees = new List<CandidateTree>(75000);

            for (int cz = 0; cz < candH; cz++)
            {
                var row = rowCandidates[cz];
                for (int i = 0; i < row.Count; i++)
                {
                    CandidateTree cand = row[i];
                    int sx = Math.Clamp((int)(cand.X / thinCell), 0, shW - 1);
                    int sz = Math.Clamp((int)(cand.Z / thinCell), 0, shH - 1);

                    bool crowded = false;
                    for (int dz = -1; dz <= 1 && !crowded; dz++)
                    {
                        int nz = sz + dz;
                        if (nz < 0 || nz >= shH) continue;
                        for (int dx = -1; dx <= 1; dx++)
                        {
                            int nx = sx + dx;
                            if (nx < 0 || nx >= shW) continue;
                            var bucket = spatialGrid[nz * shW + nx];
                            if (bucket == null) continue;
                            for (int b = 0; b < bucket.Count; b++)
                            {
                                CandidateTree other = acceptedTrees[bucket[b]];
                                float minDist = (cand.Radius + other.Radius) * 0.64f;
                                float ddx = cand.X - other.X;
                                float ddz = cand.Z - other.Z;
                                if (ddx * ddx + ddz * ddz < minDist * minDist)
                                {
                                    crowded = true;
                                    break;
                                }
                            }
                        }
                    }

                    if (crowded) continue;

                    int newIdx = acceptedTrees.Count;
                    acceptedTrees.Add(cand);
                    int bIdx = sz * shW + sx;
                    spatialGrid[bIdx] ??= new List<int>(4);
                    spatialGrid[bIdx].Add(newIdx);

                    FloraNicheProfile prof = FloraNicheDatabase.AllSpecies[(int)cand.Species];
                    float avgH = (prof.HeightMinM + prof.HeightMaxM) * 0.5f;
                    float s = cand.Height / avgH;
                    float yaw = (cand.Hash & 0xFFF) / 4095.0f * Mathf.Tau;
                    float lean = ((cand.Hash >> 12) & 0xFF) / 255.0f * 0.06f;
                    var basis = Basis.Identity.Rotated(Vector3.Up, yaw).Rotated(Vector3.Right, lean).Scaled(new Vector3(s, s, s));
                    var xform = new Transform3D(basis, new Vector3(cand.X, cand.Y - 0.25f, cand.Z));

                    int mx = Math.Clamp((int)(cand.X / MacroCellSize), 0, MacroCols - 1);
                    int mz = Math.Clamp((int)(cand.Z / MacroCellSize), 0, MacroRows - 1);
                    MacroCanopyCells[mx, mz].Add(new FloraInstance(cand.Species, xform, cand.Tint));

                    LayerCounts[(int)prof.Layer]++;
                    SpeciesCounts[(int)cand.Species]++;
                    TotalInstances++;

                    // Accumulate LAI for Beer-Lambert Light Attenuation
                    AccumulateTreeLai(cand.X, cand.Z, cand.Radius, prof.Layer == FloraLayer.Emergent ? 2.4f : 1.75f);
                }
            }

            // Compute Beer-Lambert GroundLight = exp(-0.65 * LAI) & CanopyCoverage
            Parallel.For(0, W * H, i =>
            {
                float lai = LaiMap[i];
                float light = MathF.Exp(-0.65f * lai);
                GroundLightMap[i] = light;
                CanopyCoverageMap[i] = Math.Clamp(1.0f - light, 0.0f, 1.0f);
            });

            // ===================== PHASE 2: L3..L6 (LIGHT, ECOTONE, RIPARIAN, GEOLOGY) =====================
            var detailSpecies = new List<FloraNicheProfile>();
            foreach (var sp in FloraNicheDatabase.AllSpecies)
            {
                if (sp.Layer >= FloraLayer.Understory)
                    detailSpecies.Add(sp);
            }

            // Parallelize across MicroRows (0..35) so each MicroCell is written by one thread cleanly
            Parallel.For(0, MicroRows, mz =>
            {
                float[] scores = new float[detailSpecies.Count];
                float zStart = mz * MicroCellSize;

                for (int mx = 0; mx < MicroCols; mx++)
                {
                    float xStart = mx * MicroCellSize;
                    var cellList = MicroDetailCells[mx, mz];

                    const float step2 = 13.5f;
                    int stepsPerCell = (int)(MicroCellSize / step2);

                    for (int sz = 0; sz < stepsPerCell; sz++)
                    {
                        for (int sx = 0; sx < stepsPerCell; sx++)
                        {
                            uint hKey = Hash2D(mx * 16 + sx, mz * 16 + sz, seed + 409);
                            float jx = ((hKey & 0xFF) / 255.0f) * step2 * 0.85f;
                            float jz = (((hKey >> 8) & 0xFF) / 255.0f) * step2 * 0.85f;
                            float wx = xStart + sx * step2 + jx;
                            float wz = zStart + sz * step2 + jz;
                            if (wx < 12f || wx > WorldPhysicsConfig.WorldWidth - 12f || wz < 12f || wz > WorldPhysicsConfig.WorldDepth - 12f)
                                continue;

                            float h = erosion.SampleHeight(wx, wz);
                            if (h <= 0.35f) continue;

                            int gx = Math.Clamp((int)(wx / Cell), 0, W - 1);
                            int gz = Math.Clamp((int)(wz / Cell), 0, H - 1);
                            int gIdx = gz * W + gx;

                            if (hydrology.RiverMaskMap[gIdx] > 0.45f && hydrology.WaterDepthMap[gIdx] > 0.50f) continue;

                            float slopeDeg = erosion.SlopeDegMap[gIdx];
                            float gw = hydrology.GroundwaterMap[gIdx];
                            float groundLight = GroundLightMap[gIdx];
                            ClimateSample cs = climate.SampleClimate(wx, wz);
                            SoilSample ss = soil.SampleSoil(wx, wz);

                            float total = 0.0f;
                            float bestScore = 0.0f;
                            int bestIdx = -1;
                            for (int i = 0; i < detailSpecies.Count; i++)
                            {
                                var sp = detailSpecies[i];
                                float sc = sp.EvaluateSuitability(cs, ss, slopeDeg, gw, groundLight);

                                // Boost Ecotone berries & tallgrass at forest edges (0.45 <= Light <= 0.82)
                                if (sp.Layer == FloraLayer.Shrub && groundLight >= 0.42f && groundLight <= 0.84f)
                                    sc *= 1.45f;
                                // Boost Riparian & Geology deposits in their physical niches
                                if (sp.Id == FloraSpeciesId.NipaWaterPalm && gw > 0.38f)
                                    sc *= 1.65f;
                                if ((sp.Id == FloraSpeciesId.ExposedCopperOre || sp.Id == FloraSpeciesId.Boulder) && slopeDeg > 22.0f)
                                    sc *= 1.55f;

                                scores[i] = sc;
                                total += sc;
                                if (sc > bestScore) { bestScore = sc; bestIdx = i; }
                            }

                            if (bestScore < 0.06f || bestIdx < 0) continue;

                            float roll = ((hKey >> 16) & 0xFF) / 255.0f;
                            if (roll > Math.Clamp(bestScore * 1.15f, 0.05f, 0.78f)) continue;

                            float pick = ((Hash2D(mx * 19 + sx, mz * 23 + sz, seed + 613) & 0xFFFF) / 65535.0f) * total;
                            float acc = 0.0f;
                            int chosen = bestIdx;
                            for (int i = 0; i < detailSpecies.Count; i++)
                            {
                                acc += scores[i];
                                if (acc >= pick) { chosen = i; break; }
                            }

                            FloraNicheProfile chosenSp = detailSpecies[chosen];
                            float tVar = ((hKey >> 24) & 0xFF) / 255.0f;
                            float height = Mathf.Lerp(chosenSp.HeightMinM, chosenSp.HeightMaxM, tVar);
                            float avgH = (chosenSp.HeightMinM + chosenSp.HeightMaxM) * 0.5f;
                            float s = height / MathF.Max(0.1f, avgH);

                            float yaw = chosenSp.Id == FloraSpeciesId.KrummholzDwarfPine
                                ? MathF.Atan2(cs.WindDir.Y, cs.WindDir.X) // Wind-twisted krummholz leans downwind!
                                : ((hKey & 0xFFF) / 4095.0f * Mathf.Tau);

                            var basis = Basis.Identity.Rotated(Vector3.Up, yaw).Scaled(new Vector3(s, s, s));
                            var xform = new Transform3D(basis, new Vector3(wx, h - 0.12f, wz));

                            Color tint = chosenSp.BaseTint;
                            if (chosenSp.Id == FloraSpeciesId.WildBerryBush)
                            {
                                // 3-stage fruiting cycle staggered by regional noise
                                float stageNoise = FastNoise.Fbm2D(wx * 0.004f, wz * 0.004f, seed + 887, 2);
                                tint = stageNoise < 0.38f
                                    ? new Color(0.24f, 0.48f, 0.16f) // Sprouting green
                                    : (stageNoise < 0.68f
                                        ? new Color(0.58f, 0.16f, 0.28f) // Ripe berries
                                        : new Color(0.55f, 0.34f, 0.14f)); // Late autumn
                            }
                            else
                            {
                                float hueShift = (((hKey >> 4) & 0xFF) / 255.0f - 0.5f) * 0.12f;
                                tint = ShiftTint(tint, hueShift, cs.TemperatureC, chosenSp.Id);
                            }

                            cellList.Add(new FloraInstance(chosenSp.Id, xform, tint));
                        }
                    }
                }
            });

            // Aggregate L3..L6 counts + DominantSpeciesMap for HUD & Mode [7] Map
            for (int mz = 0; mz < MicroRows; mz++)
            {
                for (int mx = 0; mx < MicroCols; mx++)
                {
                    var list = MicroDetailCells[mx, mz];
                    for (int i = 0; i < list.Count; i++)
                    {
                        FloraSpeciesId sp = list[i].Species;
                        FloraLayer layer = FloraNicheDatabase.AllSpecies[(int)sp].Layer;
                        LayerCounts[(int)layer]++;
                        SpeciesCounts[(int)sp]++;
                        TotalInstances++;
                    }
                }
            }

            BuildDominantSpeciesGrid(erosion, hydrology, climate, soil);

            sw.Stop();
            LastSpawnMs = sw.Elapsed.TotalMilliseconds;
        }

        private void BuildMegafaunaCorridors(ErosionPhysics erosion, HydrologySolver hydrology, int seed)
        {
            Parallel.For(0, H, gz =>
            {
                float wz = gz * Cell;
                for (int gx = 0; gx < W; gx++)
                {
                    int idx = gz * W + gx;
                    float h = erosion.HeightMap[idx];
                    float slope = erosion.SlopeDegMap[idx];
                    if (h < 1.0f || slope > 11.0f) { CorridorMask[idx] = 0.0f; continue; }

                    float wx = gx * Cell;
                    float n = FastNoise.Fbm2D(wx * 0.0016f, wz * 0.0016f, seed + 701, 3);
                    float ridgeTrail = 1.0f - MathF.Abs(n - 0.5f) * 18.0f;
                    float nearWater = FastNoise.SmoothStep(0.18f, 0.55f, hydrology.GroundwaterMap[idx]);
                    float gentle = 1.0f - FastNoise.SmoothStep(5.0f, 11.0f, slope);
                    CorridorMask[idx] = Math.Clamp(MathF.Max(0.0f, ridgeTrail) * gentle * (0.45f + nearWater * 0.55f), 0.0f, 1.0f);
                }
            });
        }

        private void AccumulateTreeLai(float wx, float wz, float crownRadiusM, float peakLai)
        {
            int cx = (int)(wx / Cell);
            int cz = (int)(wz / Cell);
            int rCells = Math.Max(1, (int)MathF.Ceiling(crownRadiusM / Cell));
            float invR2 = 1.0f / MathF.Max(1.0f, crownRadiusM * crownRadiusM);

            for (int dz = -rCells; dz <= rCells; dz++)
            {
                int gz = cz + dz;
                if (gz < 0 || gz >= H) continue;
                for (int dx = -rCells; dx <= rCells; dx++)
                {
                    int gx = cx + dx;
                    if (gx < 0 || gx >= W) continue;
                    float dist2 = (dx * Cell) * (dx * Cell) + (dz * Cell) * (dz * Cell);
                    float w = MathF.Exp(-dist2 * invR2 * 1.8f);
                    LaiMap[gz * W + gx] += peakLai * w;
                }
            }
        }

        private void BuildDominantSpeciesGrid(
            ErosionPhysics erosion,
            HydrologySolver hydrology,
            AtmosphereClimate climate,
            SoilPedology soil)
        {
            Parallel.For(0, H, gz =>
            {
                float wz = gz * Cell;
                for (int gx = 0; gx < W; gx++)
                {
                    int idx = gz * W + gx;
                    if (erosion.HeightMap[idx] <= 0.4f) { DominantSpeciesMap[idx] = -1; continue; }

                    float wx = gx * Cell;
                    ClimateSample cs = climate.SampleClimate(wx, wz);
                    SoilSample ss = soil.SampleSoil(wx, wz);
                    float slope = erosion.SlopeDegMap[idx];
                    float gw = hydrology.GroundwaterMap[idx];
                    float gl = GroundLightMap[idx];

                    float best = 0.03f;
                    sbyte bestId = -1;
                    for (int s = 0; s < FloraNicheDatabase.AllSpecies.Length; s++)
                    {
                        var sp = FloraNicheDatabase.AllSpecies[s];
                        if (sp.Layer > FloraLayer.Understory) continue;
                        float sc = sp.EvaluateSuitability(cs, ss, slope, gw, gl);
                        if (sc > best) { best = sc; bestId = (sbyte)s; }
                    }
                    DominantSpeciesMap[idx] = bestId;
                }
            });
        }

        public string GetDominantSpeciesNameAt(float worldX, float worldZ)
        {
            int gx = Math.Clamp((int)(worldX / Cell), 0, W - 1);
            int gz = Math.Clamp((int)(worldZ / Cell), 0, H - 1);
            sbyte id = DominantSpeciesMap[gz * W + gx];
            return id >= 0 && id < FloraNicheDatabase.AllSpecies.Length
                ? FloraNicheDatabase.AllSpecies[id].DisplayName
                : "Không có (Biển/Đá trơ)";
        }

        public ImageTexture BuildCanopyCoverageTexture()
        {
            byte[] data = new byte[W * H];
            for (int i = 0; i < data.Length; i++)
                data[i] = (byte)(Math.Clamp(CanopyCoverageMap[i], 0.0f, 1.0f) * 255.0f);
            return ImageTexture.CreateFromImage(Image.CreateFromData(W, H, false, Image.Format.L8, data));
        }

        public ImageTexture BuildEmptyCoverageTexture()
        {
            byte[] data = new byte[W * H];
            return ImageTexture.CreateFromImage(Image.CreateFromData(W, H, false, Image.Format.L8, data));
        }

        private static Color ShiftTint(Color baseTint, float shift, float tempC, FloraSpeciesId id)
        {
            float r = baseTint.R + shift * 0.7f;
            float g = baseTint.G + shift * 0.5f;
            float b = baseTint.B - shift * 0.3f;
            if (tempC < 2.0f && (id == FloraSpeciesId.BorealSnowPine || id == FloraSpeciesId.SilverGlacierSpruce))
            {
                r += 0.06f; g += 0.08f; b += 0.11f; // Frost dusting
            }
            return new Color(Math.Clamp(r, 0.04f, 0.98f), Math.Clamp(g, 0.04f, 0.98f), Math.Clamp(b, 0.04f, 0.98f));
        }

        private static uint Hash2D(int x, int y, int seed)
        {
            uint h = (uint)(x * 374761393 + y * 668265263 + seed * 1442695041);
            h = (h ^ (h >> 13)) * 1274126177U;
            return h ^ (h >> 16);
        }
    }
}
