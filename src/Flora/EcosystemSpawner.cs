using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Threading.Tasks;
using Godot;
using PrimevalWorld.Core;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Flora
{
    public enum LandEcosystemId : byte
    {
        OceanOrLake = 0,
        PrimevalDenseForest = 1,   // 1. Rừng già nguyên sinh khép tán (24-28%)
        AlluvialFloodplain = 2,    // 2. Đồng bằng phù sa & Bãi bồi ven sông (20-24%)
        WetlandAndDelta = 3,       // 3. Đầm lầy, Châu thổ & Bãi ngập nước (8-12%)
        OpenSteppePlateau = 4,     // 4. Thảo nguyên mở & Cao nguyên gió (16-18%)
        AridRedDesertOasis = 5,    // 5. Hoang mạc cát đỏ, Khe cạn & Ốc đảo (12-14%)
        AlpineSnowTundraRock = 6,  // 6. Núi tuyết, Đài nguyên & Vách đá trơ (10-12%)
        CoastlineSaltDunes = 7,    // 7. Bờ biển, Đầm mặn & Cồn cát (4-6%)
    }

    public readonly struct WoodyTreeRecord
    {
        public readonly float X;
        public readonly float Z;
        public readonly float ActualCrownRadiusM;
        public readonly LandEcosystemId Ecosystem;
        public readonly float CorridorValue;
        public readonly float WaterDepthM;

        public WoodyTreeRecord(float x, float z, float actualCrownRadiusM, LandEcosystemId eco, float corridorValue, float waterDepthM)
        {
            X = x;
            Z = z;
            ActualCrownRadiusM = actualCrownRadiusM;
            Ecosystem = eco;
            CorridorValue = corridorValue;
            WaterDepthM = waterDepthM;
        }
    }

    public readonly struct FloraInstance
    {
        public readonly FloraSpeciesId Species;
        public readonly byte Variant;
        public readonly Transform3D Transform;
        public readonly Color CustomData; // RGB = hue/tint multiplier, A = per-instance phenology seed [0..1]

        public FloraInstance(FloraSpeciesId species, Transform3D transform, Color customData, byte variant = 0)
        {
            Species = species;
            Variant = variant;
            Transform = transform;
            CustomData = customData;
        }
    }

    /// <summary>
    /// Synchronized 7-Ecosystem Master Planner & Polarized 6-Layer Flora Spawner (9.6 x 5.4 km):
    /// - Enforces physical 7-Ecosystem Land Budget across 100% of emergent land:
    ///   Forest (24-28%), Floodplain (20-24%), Wetland (8-12%), Steppe (16-18%), Desert (12-14%), Alpine (10-12%), Coast (4-6%)
    /// - Polarizes woody trees (50,000 - 65,000 L1+L2 trees) densely into closed-canopy Primeval Forest (80-95%),
    ///   Riparian gallery edges (<20m), Wetland hummocks (15-30%), and sheltered Steppe Groves (8-15%),
    ///   while keeping Alluvial Floodplains (1-4% Landmark trees), Open Steppe, and Red Desert wide open!
    /// - Partitions L1+L2 trees into 32x18 cells (300m x 300m) for accurate 3-Tier MultiMesh LOD switching.
    /// </summary>
    public sealed class EcosystemSpawner
    {
        public const int MacroCols = 32; // 300m x 300m cells matching TerrainChunk grid for sharp 3-Tier LOD
        public const int MacroRows = 18;
        public const float MacroCellSize = 300.0f;

        public const int MicroCols = 64; // 150m x 150m micro cells for L3..L6 understory/shrub/herb streaming
        public const int MicroRows = 36;
        public const float MicroCellSize = 150.0f;

        private const int W = WorldPhysicsConfig.VertW;
        private const int H = WorldPhysicsConfig.VertH;
        private const float Cell = WorldPhysicsConfig.CellSize;

        public float[] LaiMap { get; } = new float[W * H];
        public float[] GroundLightMap { get; } = new float[W * H];
        public float[] CanopyCoverageMap { get; } = new float[W * H];
        public float[] ForestMacroMask { get; } = new float[W * H];
        public float[] CorridorMask { get; } = new float[W * H];
        public LandEcosystemId[] EcosystemMap { get; } = new LandEcosystemId[W * H];
        public sbyte[] DominantSpeciesMap { get; } = new sbyte[W * H];

        public int[] EcosystemLandCounts { get; } = new int[8]; // indices 1..7
        public int TotalEmergentLandCells { get; private set; }

        public List<FloraInstance>[,] MacroCanopyCells { get; } = new List<FloraInstance>[MacroCols, MacroRows];
        public List<FloraInstance>[,] MicroDetailCells { get; } = new List<FloraInstance>[MicroCols, MicroRows];
        public List<WoodyTreeRecord> AcceptedWoodyRecords { get; } = new(64000);
        public int DeepWaterDetailCount { get; private set; }

        public int[] LayerCounts { get; } = new int[7];     // indices 1..6
        public int[] StemGroupCounts { get; } = new int[4]; // indices 0..3
        public int[] SpeciesCounts { get; } = new int[FloraNicheDatabase.AllSpecies.Length];
        public int TotalWoodyTrees => LayerCounts[1] + LayerCounts[2];
        public int TotalInstances { get; private set; }
        public double LastSpawnMs { get; private set; }

        private struct CandidateTree
        {
            public float X, Y, Z;
            public FloraSpeciesId Species;
            public float Radius;
            public float Height;
            public float AgeRatio;
            public LandEcosystemId Eco;
            public Color CustomData;
            public uint Hash;
        }

        public void Generate(
            TectonicContinentGen tectonic,
            ErosionPhysics erosion,
            HydrologySolver hydrology,
            AtmosphereClimate climate,
            SoilPedology soil,
            int seed)
        {
            var sw = Stopwatch.StartNew();

            Array.Clear(LaiMap, 0, LaiMap.Length);
            Array.Clear(CanopyCoverageMap, 0, CanopyCoverageMap.Length);
            Array.Clear(ForestMacroMask, 0, ForestMacroMask.Length);
            Array.Clear(EcosystemMap, 0, EcosystemMap.Length);
            Array.Clear(EcosystemLandCounts, 0, EcosystemLandCounts.Length);
            Array.Clear(LayerCounts, 0, LayerCounts.Length);
            Array.Clear(StemGroupCounts, 0, StemGroupCounts.Length);
            Array.Clear(SpeciesCounts, 0, SpeciesCounts.Length);
            Array.Fill(GroundLightMap, 1.0f);
            Array.Fill(DominantSpeciesMap, (sbyte)-1);
            AcceptedWoodyRecords.Clear();
            DeepWaterDetailCount = 0;
            TotalInstances = 0;

            for (int z = 0; z < MacroRows; z++)
                for (int x = 0; x < MacroCols; x++)
                    MacroCanopyCells[x, z] = new List<FloraInstance>(128);

            for (int z = 0; z < MicroRows; z++)
                for (int x = 0; x < MicroCols; x++)
                    MicroDetailCells[x, z] = new List<FloraInstance>(96);

            ClassifySevenEcosystems(tectonic, erosion, hydrology, climate, soil, seed);
            BuildMegafaunaCorridors(erosion, hydrology, seed);

            // ===================== PHASE 1: POLARIZED WOODY CANOPY + EMERGENT (50k - 65k TREES) =====================
            var canopySpecies = new List<FloraNicheProfile>();
            foreach (var sp in FloraNicheDatabase.AllSpecies)
            {
                if (sp.Layer == FloraLayer.Emergent || sp.Layer == FloraLayer.Canopy)
                    canopySpecies.Add(sp);
            }

            const float step1 = 7.45f;
            int candW = (int)(WorldPhysicsConfig.WorldWidth / step1);
            int candH = (int)(WorldPhysicsConfig.WorldDepth / step1);
            var rowCandidates = new List<CandidateTree>[candH];

            Parallel.For(0, candH, cz =>
            {
                var list = new List<CandidateTree>(candW / 4);
                rowCandidates[cz] = list;
                float[] scores = new float[canopySpecies.Count];

                for (int cx = 0; cx < candW; cx++)
                {
                    uint hKey = Hash2D(cx, cz, seed + 17);
                    float jx = ((hKey & 0xFF) / 255.0f - 0.5f) * step1 * 0.86f;
                    float jz = (((hKey >> 8) & 0xFF) / 255.0f - 0.5f) * step1 * 0.86f;
                    float wx = cx * step1 + step1 * 0.5f + jx;
                    float wz = cz * step1 + step1 * 0.5f + jz;
                    if (wx < 20f || wx > WorldPhysicsConfig.WorldWidth - 20f || wz < 20f || wz > WorldPhysicsConfig.WorldDepth - 20f)
                        continue;

                    float h = erosion.SampleHeight(wx, wz);
                    if (h <= 0.40f) continue;

                    // Strict deep-water gate: 0 woody trees allowed where water_depth > 0.30m!
                    if (hydrology.SampleWaterDepthAt(wx, wz, h) > 0.30f) continue;

                    int gx = Math.Clamp((int)(wx / Cell), 0, W - 1);
                    int gz = Math.Clamp((int)(wz / Cell), 0, H - 1);
                    int gIdx = gz * W + gx;

                    if (hydrology.HasInlandWater[gIdx] || (hydrology.RiverMaskMap[gIdx] > 0.42f && hydrology.WaterDepthMap[gIdx] > 0.25f))
                        continue;

                    LandEcosystemId eco = EcosystemMap[gIdx];
                    if (eco == LandEcosystemId.OceanOrLake) continue;

                    float slopeDeg = erosion.SlopeDegMap[gIdx];
                    float gw = hydrology.GroundwaterMap[gIdx];
                    float flow = hydrology.FlowAccumMap[gIdx];
                    float riverMask = hydrology.RiverMaskMap[gIdx];
                    float coastDist = tectonic.CoastDistMeters[gIdx];

                    // Winding megafauna trails clear narrow natural sightlines inside dense woods
                    float corridorKeep = 1.0f - CorridorMask[gIdx] * 0.82f;
                    if (((hKey >> 16) & 0xFF) / 255.0f > corridorKeep) continue;

                    float groveNoise = FastNoise.Fbm2D(wx * 0.0038f, wz * 0.0038f, seed + 643, 3);
                    bool isRiparian20m = riverMask > 0.16f && riverMask < 0.42f && slopeDeg < 14.0f;

                    // Strict Ecological Polarization Probability per Ecosystem
                    float ecoTreeGate;
                    bool forceAncientLandmark = false;
                    switch (eco)
                    {
                        case LandEcosystemId.PrimevalDenseForest:
                            ecoTreeGate = 0.90f + ForestMacroMask[gIdx] * 0.10f; // 80-95% closed billowing canopy ocean!
                            break;

                        case LandEcosystemId.AlluvialFloodplain:
                            if (isRiparian20m)
                                ecoTreeGate = 0.20f; // Graceful riverside Willows (<20m of water)
                            else
                            {
                                ecoTreeGate = 0.0075f; // Only 1-3% isolated Landmark Trees on wide open green floodplains!
                                forceAncientLandmark = true;
                            }
                            break;

                        case LandEcosystemId.WetlandAndDelta:
                            // Clumped flood-tolerant trees ONLY on dry raised mossy hummocks (15-28%)
                            ecoTreeGate = groveNoise > 0.52f ? 0.28f : 0.03f;
                            break;

                        case LandEcosystemId.OpenSteppePlateau:
                            // 84-88% open feather-grass steppe; woody Ginkgo/Maple/Birch clustered into sheltered Groves!
                            ecoTreeGate = (groveNoise > 0.62f && slopeDeg < 22.0f) ? 0.36f : 0.002f;
                            break;

                        case LandEcosystemId.AridRedDesertOasis:
                            // 96%+ bare sand/rock (P50 <= 0.01); DragonBlood/Baobab/Acacia strictly in wadis & oasis rims
                            ecoTreeGate = (flow > 0.34f || gw > 0.38f) ? 0.08f : 0.0004f;
                            break;

                        case LandEcosystemId.AlpineSnowTundraRock:
                            // Bare rock cliffs (>27°) & freezing peaks = 0%; sheltered lower subalpine pockets = Snow Pine
                            ecoTreeGate = (slopeDeg < 26.5f && climate.TemperatureMap[gIdx] > -3.5f && groveNoise > 0.54f) ? 0.22f : 0.0f;
                            break;

                        case LandEcosystemId.CoastlineSaltDunes:
                            // Clean surf beaches (<30m); sparse salt-tolerant trees set back on inner dunes
                            ecoTreeGate = (coastDist > 30.0f && slopeDeg < 18.0f && groveNoise > 0.56f) ? 0.12f : 0.0f;
                            break;

                        default:
                            ecoTreeGate = 0.0f;
                            break;
                    }

                    float gateRoll = ((hKey >> 20) & 0xFFF) / 4095.0f;
                    if (gateRoll > ecoTreeGate) continue;

                    ClimateSample cs = climate.SampleClimate(wx, wz);
                    SoilSample ss = soil.SampleSoil(wx, wz);

                    float total = 0.0f;
                    float bestScore = 0.0f;
                    int bestIdx = -1;
                    for (int i = 0; i < canopySpecies.Count; i++)
                    {
                        var candSp = canopySpecies[i];
                        float sc = candSp.EvaluateSuitability(cs, ss, slopeDeg, gw, 1.0f);
                        if (candSp.Layer == FloraLayer.Emergent && !forceAncientLandmark)
                            sc *= 0.34f;
                        if (forceAncientLandmark)
                            sc *= (candSp.Id == FloraSpeciesId.PrimevalBanyanFig || candSp.Id == FloraSpeciesId.SacredAncientHardwood) ? 3.5f : 0.15f;
                        if ((eco == LandEcosystemId.WetlandAndDelta || isRiparian20m) && candSp.Id == FloraSpeciesId.WeepingRiverWillow)
                            sc *= 2.8f;
                        if (eco == LandEcosystemId.PrimevalDenseForest && (candSp.Id == FloraSpeciesId.GinkgoAncientGold || candSp.Id == FloraSpeciesId.CrimsonSteppeMaple))
                            sc *= 0.22f; // Keep deciduous Ginkgo/Maple concentrated in Steppe Groves & cool Ecotones
                        // Intermix 10-20% dark conifers on cool/high Primeval Forest slopes for natural color & silhouette contrast!
                        if (eco == LandEcosystemId.PrimevalDenseForest && (candSp.Id == FloraSpeciesId.BorealSnowPine || candSp.Id == FloraSpeciesId.GiantSequoiaReddawn))
                            sc *= (cs.TemperatureC < 17.5f || h > 45.0f) ? 2.2f : 1.15f;

                        scores[i] = sc;
                        total += sc;
                        if (sc > bestScore) { bestScore = sc; bestIdx = i; }
                    }

                    if (bestScore < 0.035f || bestIdx < 0) continue;

                    float pick = ((Hash2D(cx + 31, cz + 71, seed + 53) & 0xFFFF) / 65535.0f) * total;
                    float acc = 0.0f;
                    int chosen = bestIdx;
                    for (int i = 0; i < canopySpecies.Count; i++)
                    {
                        acc += scores[i];
                        if (acc >= pick) { chosen = i; break; }
                    }

                    FloraNicheProfile sp = canopySpecies[chosen];
                    float rawAge = (Hash2D(cx * 3, cz * 5, seed + 109) & 0xFF) / 255.0f;
                    // Deep forest cores & floodplain landmarks grow ancient wide crowns; forest edges have younger trees
                    float ageRatio = forceAncientLandmark
                        ? 0.85f + rawAge * 0.15f
                        : (eco == LandEcosystemId.PrimevalDenseForest ? Math.Clamp(rawAge * 0.75f + ForestMacroMask[gIdx] * 0.28f, 0.1f, 1.0f) : rawAge * 0.85f);

                    float height = Mathf.Lerp(sp.HeightMinM, sp.HeightMaxM, ageRatio);
                    float hueShift = ((Hash2D(cx + 7, cz + 13, seed + 211) & 0xFF) / 255.0f - 0.5f) * 0.16f;
                    float phenoSeed = ((Hash2D(cx + 41, cz + 97, seed + 331) & 0xFF) / 255.0f);
                    Color custom = BuildInstanceTint(sp.BaseTint, hueShift, cs.TemperatureC, sp.Id, ageRatio, phenoSeed);

                    list.Add(new CandidateTree
                    {
                        X = wx, Y = h, Z = wz,
                        Species = sp.Id,
                        Radius = sp.CrownRadiusM * Mathf.Lerp(0.76f, 1.18f, ageRatio),
                        Height = height,
                        AgeRatio = ageRatio,
                        Eco = eco,
                        CustomData = custom,
                        Hash = hKey
                    });
                }
            });

            // Self-Thinning Pass via Spatial Hash Grid (dense overlapping crowns inside Primeval Forest, airy spacing outside)
            const float thinCell = 9.0f;
            int shW = (int)(WorldPhysicsConfig.WorldWidth / thinCell) + 1;
            int shH = (int)(WorldPhysicsConfig.WorldDepth / thinCell) + 1;
            var spatialGrid = new List<int>[shW * shH];
            var acceptedTrees = new List<CandidateTree>(64000);

            for (int cz = 0; cz < candH; cz++)
            {
                var row = rowCandidates[cz];
                for (int i = 0; i < row.Count; i++)
                {
                    CandidateTree cand = row[i];
                    int sx = Math.Clamp((int)(cand.X / thinCell), 0, shW - 1);
                    int sz = Math.Clamp((int)(cand.Z / thinCell), 0, shH - 1);
                    float spacingFactor = cand.Eco == LandEcosystemId.PrimevalDenseForest ? 0.33f : 0.58f;

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
                                float minDist = (cand.Radius + other.Radius) * spacingFactor;
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
                    float sY = cand.Height / avgH;
                    float sXZ = sY * Mathf.Lerp(0.84f, 1.18f, cand.AgeRatio) * (cand.Eco == LandEcosystemId.PrimevalDenseForest ? 1.12f : 1.0f);
                    float yaw = (cand.Hash & 0xFFF) / 4095.0f * Mathf.Tau;
                    float lean = ((cand.Hash >> 12) & 0xFF) / 255.0f * 0.05f;
                    var basis = Basis.Identity.Rotated(Vector3.Up, yaw).Rotated(Vector3.Right, lean).Scaled(new Vector3(sXZ, sY, sXZ));
                    var xform = new Transform3D(basis, new Vector3(cand.X, cand.Y - 0.25f, cand.Z));

                    int mx = Math.Clamp((int)(cand.X / MacroCellSize), 0, MacroCols - 1);
                    int mz = Math.Clamp((int)(cand.Z / MacroCellSize), 0, MacroRows - 1);
                    byte variant = (byte)((cand.Hash >> 4) & 3);
                    MacroCanopyCells[mx, mz].Add(new FloraInstance(cand.Species, xform, cand.CustomData, variant));

                    int cgx = Math.Clamp((int)(cand.X / Cell), 0, W - 1);
                    int cgz = Math.Clamp((int)(cand.Z / Cell), 0, H - 1);
                    float actualCrownR = prof.CrownRadiusM * sXZ;
                    float wDepth = hydrology.SampleWaterDepthAt(cand.X, cand.Z, cand.Y);
                    AcceptedWoodyRecords.Add(new WoodyTreeRecord(
                        cand.X, cand.Z, actualCrownR, cand.Eco, CorridorMask[cgz * W + cgx], wDepth));

                    LayerCounts[(int)prof.Layer]++;
                    StemGroupCounts[(int)prof.Stem]++;
                    SpeciesCounts[(int)cand.Species]++;
                    TotalInstances++;

                    AccumulateTreeLai(cand.X, cand.Z, cand.Radius * 1.12f, prof.Layer == FloraLayer.Emergent ? 2.65f : 1.95f);
                }
            }

            // Compute Beer-Lambert GroundLight = exp(-0.68 * LAI) -> 80-95% CanopyCoverage inside Primeval Forest!
            Parallel.For(0, W * H, i =>
            {
                float lai = LaiMap[i];
                float light = MathF.Exp(-0.68f * lai);
                GroundLightMap[i] = light;
                CanopyCoverageMap[i] = Math.Clamp(1.0f - light, 0.0f, 1.0f);
            });

            // ===================== SYMBIOTIC ROOT MICRO-CLUSTERS, LIANAS & DENSE UNDERSTORY =====================
            for (int i = 0; i < acceptedTrees.Count; i++)
            {
                CandidateTree tree = acceptedTrees[i];
                FloraNicheProfile prof = FloraNicheDatabase.AllSpecies[(int)tree.Species];
                int tgx = Math.Clamp((int)(tree.X / Cell), 0, W - 1);
                int tgz = Math.Clamp((int)(tree.Z / Cell), 0, H - 1);
                int tgIdx = tgz * W + tgx;
                float localMoisture = climate.MoistureMap[tgIdx];
                float localCanopy = CanopyCoverageMap[tgIdx];

                // Hanging Moss Lianas draping from humid rainforest canopy limbs (Moisture > 0.55 && Canopy > 0.55)
                if (tree.Eco == LandEcosystemId.PrimevalDenseForest && localMoisture > 0.55f && localCanopy > 0.55f && (tree.Hash & 3) == 0)
                {
                    AddDetailInstance(FloraSpeciesId.LianaMossCurtain, tree.X, tree.Z, tree.Y,
                        0.90f + ((tree.Hash >> 8) & 15) / 40.0f, (tree.Hash & 0xFFF) / 4095.0f * Mathf.Tau,
                        new Color(0.86f, 1.00f, 0.76f, 0.5f), (byte)((tree.Hash >> 5) & 1));
                }

                // Dense understory ferns, broadleaf aroids, shrubs & mossy fallen logs around humid forest trunks (0-3.5m eye-level fill!)
                if ((tree.Eco == LandEcosystemId.PrimevalDenseForest || tree.Eco == LandEcosystemId.WetlandAndDelta) && (tree.Hash & 1) == 0)
                {
                    int ringItems = prof.Layer == FloraLayer.Emergent ? 4 : 2;
                    for (int k = 0; k < ringItems; k++)
                    {
                        uint sh = Hash2D(i, k + 11, seed + 1301);
                        float ang = (sh & 0xFF) / 255.0f * Mathf.Tau;
                        float dist = 2.2f + ((sh >> 8) & 0xFF) / 255.0f * 5.8f;
                        float px = tree.X + MathF.Cos(ang) * dist;
                        float pz = tree.Z + MathF.Sin(ang) * dist;
                        if (px < 15f || px > WorldPhysicsConfig.WorldWidth - 15f || pz < 15f || pz > WorldPhysicsConfig.WorldDepth - 15f)
                            continue;
                        float ph = erosion.SampleHeight(px, pz);
                        if (ph <= 0.4f || hydrology.SampleWaterDepthAt(px, pz, ph) > 0.30f) continue;

                        uint roll = (sh >> 16) % 10;
                        FloraSpeciesId uId = roll < 4 ? FloraSpeciesId.LushSwordFern
                                           : (roll < 6 ? FloraSpeciesId.WildBerryBush
                                           : (roll < 8 ? FloraSpeciesId.GiantElephantEar
                                           : FloraSpeciesId.HollowFallenTrunk));
                        byte uVar = (byte)((sh >> 20) & 1);
                        float uScale = 0.85f + ((sh >> 22) & 15) / 35.0f;
                        Color uTint = uId == FloraSpeciesId.HollowFallenTrunk
                            ? new Color(1.0f, 1.0f, 1.0f, 0.5f)
                            : new Color(0.90f + (uVar * 0.08f), 1.04f, 0.84f, ((sh >> 4) & 0xFF) / 255.0f);
                        AddDetailInstance(uId, px, pz, ph, uScale, ang, uTint, uVar);
                    }
                }

                if (prof.Layer != FloraLayer.Emergent || tree.Species == FloraSpeciesId.BaobabPrehistoric)
                    continue;

                float vineH = erosion.SampleHeight(tree.X + 0.35f, tree.Z + 0.25f);
                if (vineH > 0.35f && hydrology.SampleWaterDepthAt(tree.X + 0.35f, tree.Z + 0.25f, vineH) <= 0.30f)
                {
                    AddDetailInstance(FloraSpeciesId.EpiphyteBaseVine, tree.X + 0.35f, tree.Z + 0.25f,
                        vineH, 1.05f, (tree.Hash & 0xFFF) / 4095.0f * Mathf.Tau,
                        new Color(0.92f, 1.04f, 0.86f, 0.5f), 0);
                }

                if (tree.Eco != LandEcosystemId.PrimevalDenseForest && tree.Eco != LandEcosystemId.WetlandAndDelta)
                    continue;

                FloraSpeciesId[] symbiotes =
                {
                    FloraSpeciesId.ArborescentTreeFern,
                    FloraSpeciesId.CycadPrehistoric,
                    FloraSpeciesId.BiolumForestMushroom,
                    FloraSpeciesId.HollowFallenTrunk,
                };
                for (int k = 0; k < 3; k++)
                {
                    uint sh = Hash2D(i, k, seed + 997);
                    float ang = (sh & 0xFF) / 255.0f * Mathf.Tau;
                    float dist = 3.5f + ((sh >> 8) & 0xFF) / 255.0f * 5.0f;
                    float px = tree.X + MathF.Cos(ang) * dist;
                    float pz = tree.Z + MathF.Sin(ang) * dist;
                    if (px < 15f || px > WorldPhysicsConfig.WorldWidth - 15f || pz < 15f || pz > WorldPhysicsConfig.WorldDepth - 15f)
                        continue;
                    float ph = erosion.SampleHeight(px, pz);
                    if (ph <= 0.4f || hydrology.SampleWaterDepthAt(px, pz, ph) > 0.30f) continue;

                    FloraSpeciesId symId = symbiotes[(sh >> 16) % (uint)symbiotes.Length];
                    Color symTint = symId == FloraSpeciesId.ArborescentTreeFern || symId == FloraSpeciesId.CycadPrehistoric
                        ? new Color(0.94f, 1.04f, 0.88f, 0.5f)
                        : FloraNicheDatabase.AllSpecies[(int)symId].BaseTint;
                    AddDetailInstance(symId, px, pz, ph, 0.9f + ((sh >> 20) & 0xF) / 30.0f, ang, symTint, (byte)((sh >> 24) & 1));
                }
            }

            // ===================== PHASE 2: L3..L6 ECOSYSTEM-AWARE UNDERSTORY, WETLAND & ECOTONE SPAWN =====================
            var detailSpecies = new List<FloraNicheProfile>();
            foreach (var sp in FloraNicheDatabase.AllSpecies)
            {
                if (sp.Layer >= FloraLayer.Understory)
                    detailSpecies.Add(sp);
            }

            Parallel.For(0, MicroRows, mz =>
            {
                float[] scores = new float[detailSpecies.Count];
                float zStart = mz * MicroCellSize;

                for (int mx = 0; mx < MicroCols; mx++)
                {
                    float xStart = mx * MicroCellSize;
                    var cellList = MicroDetailCells[mx, mz];
                    const float step2 = 11.5f;
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
                            if (h <= 0.22f || hydrology.SampleWaterDepthAt(wx, wz, h) > 0.30f) continue;

                            int gx = Math.Clamp((int)(wx / Cell), 0, W - 1);
                            int gz = Math.Clamp((int)(wz / Cell), 0, H - 1);
                            int gIdx = gz * W + gx;

                            if (hydrology.RiverMaskMap[gIdx] > 0.45f && hydrology.WaterDepthMap[gIdx] > 0.30f) continue;

                            LandEcosystemId eco = EcosystemMap[gIdx];
                            float slopeDeg = erosion.SlopeDegMap[gIdx];
                            float gw = hydrology.GroundwaterMap[gIdx];
                            float groundLight = GroundLightMap[gIdx];
                            ClimateSample cs = climate.SampleClimate(wx, wz);
                            SoilSample ss = soil.SampleSoil(wx, wz);

                            // Keep open Alluvial Floodplain & Desert cleanly open (mostly GPU grass carpet on floodplains!)
                            if (eco == LandEcosystemId.AlluvialFloodplain && hydrology.RiverMaskMap[gIdx] < 0.12f && groundLight > 0.85f)
                            {
                                if (((hKey >> 20) & 0xFF) / 255.0f > 0.12f) continue;
                            }
                            if (eco == LandEcosystemId.AridRedDesertOasis && gw < 0.22f && (((hKey >> 20) & 0xFF) / 255.0f > 0.16f))
                                continue;

                            float total = 0.0f;
                            float bestScore = 0.0f;
                            int bestIdx = -1;
                            bool isEcotone = groundLight >= 0.35f && groundLight <= 0.82f;

                            for (int i = 0; i < detailSpecies.Count; i++)
                            {
                                var sp = detailSpecies[i];
                                float sc = sp.EvaluateSuitability(cs, ss, slopeDeg, gw, groundLight);

                                // Ecotone shrub & bamboo transition belt framing dense forests
                                if (isEcotone && (sp.Layer == FloraLayer.Shrub || sp.Id == FloraSpeciesId.GiantBambooVau || sp.Id == FloraSpeciesId.PampasPlumeTallgrass))
                                    sc *= 1.85f;

                                // Wetland & Oasis specialization: dense Reeds, Nipa Palm, Elephant Ear, Fallen Logs!
                                if (eco == LandEcosystemId.WetlandAndDelta)
                                {
                                    if (sp.Id == FloraSpeciesId.RiverbankReedBed || sp.Id == FloraSpeciesId.NipaWaterPalm ||
                                        sp.Id == FloraSpeciesId.GiantElephantEar || sp.Id == FloraSpeciesId.HollowFallenTrunk)
                                        sc *= 2.8f;
                                }
                                else if ((sp.Id == FloraSpeciesId.NipaWaterPalm || sp.Id == FloraSpeciesId.RiverbankReedBed) && gw > 0.36f)
                                {
                                    sc *= 1.9f; // Oasis rims & riverbanks
                                }

                                if (eco == LandEcosystemId.OpenSteppePlateau && (sp.Id == FloraSpeciesId.FeatherSteppeGrass || sp.Id == FloraSpeciesId.PampasPlumeTallgrass))
                                    sc *= 1.75f;

                                if ((sp.Id == FloraSpeciesId.ExposedCopperOre || sp.Id == FloraSpeciesId.Boulder) && slopeDeg > 22.0f)
                                    sc *= 1.55f;

                                scores[i] = sc;
                                total += sc;
                                if (sc > bestScore) { bestScore = sc; bestIdx = i; }
                            }

                            if (bestScore < 0.050f || bestIdx < 0) continue;

                            float probMult = eco == LandEcosystemId.WetlandAndDelta ? 1.55f : (isEcotone ? 1.35f : 1.05f);
                            float roll = ((hKey >> 16) & 0xFF) / 255.0f;
                            if (roll > Math.Clamp(bestScore * probMult, 0.04f, 0.84f)) continue;

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
                                ? MathF.Atan2(cs.WindDir.Y, cs.WindDir.X)
                                : ((hKey & 0xFFF) / 4095.0f * Mathf.Tau);

                            var basis = Basis.Identity.Rotated(Vector3.Up, yaw).Scaled(new Vector3(s, s, s));
                            var xform = new Transform3D(basis, new Vector3(wx, h - 0.10f, wz));

                            bool usesLeafTex = chosenSp.Architecture == FloraArchitecture.ArchColumnarPalmFern
                                            || chosenSp.Architecture == FloraArchitecture.ArchCaudexCycad
                                            || chosenSp.Architecture == FloraArchitecture.ArchBambooCulm
                                            || chosenSp.Architecture == FloraArchitecture.ArchKrummholz
                                            || chosenSp.Architecture == FloraArchitecture.ArchWoodyShrub
                                            || chosenSp.Id == FloraSpeciesId.EpiphyteBaseVine;

                            Color custom;
                            if (usesLeafTex)
                            {
                                float v = 0.88f + (((hKey >> 4) & 0xFF) / 255.0f) * 0.24f;
                                custom = new Color(v, v * 1.03f, v * 0.94f, tVar);
                            }
                            else
                            {
                                Color baseC = chosenSp.BaseTint;
                                float shift = (((hKey >> 4) & 0xFF) / 255.0f - 0.5f) * 0.10f;
                                custom = new Color(
                                    Math.Clamp(baseC.R + shift, 0.05f, 1.0f),
                                    Math.Clamp(baseC.G + shift, 0.05f, 1.0f),
                                    Math.Clamp(baseC.B - shift * 0.5f, 0.05f, 1.0f),
                                    tVar);
                            }

                            cellList.Add(new FloraInstance(chosenSp.Id, xform, custom, (byte)((hKey >> 2) & 1)));
                        }
                    }
                }
            });

            // Aggregate L3..L6 counts
            for (int mz = 0; mz < MicroRows; mz++)
            {
                for (int mx = 0; mx < MicroCols; mx++)
                {
                    var list = MicroDetailCells[mx, mz];
                    for (int i = 0; i < list.Count; i++)
                    {
                        FloraSpeciesId sp = list[i].Species;
                        FloraNicheProfile prof = FloraNicheDatabase.AllSpecies[(int)sp];
                        Vector3 o = list[i].Transform.Origin;
                        if (hydrology.SampleWaterDepthAt(o.X, o.Z, o.Y + 0.10f) > 0.30f)
                            DeepWaterDetailCount++;
                        LayerCounts[(int)prof.Layer]++;
                        StemGroupCounts[(int)prof.Stem]++;
                        SpeciesCounts[(int)sp]++;
                        TotalInstances++;
                    }
                }
            }

            BuildDominantSpeciesGrid(erosion, hydrology, climate, soil);

            sw.Stop();
            LastSpawnMs = sw.Elapsed.TotalMilliseconds;
        }

        private void ClassifySevenEcosystems(
            TectonicContinentGen tectonic,
            ErosionPhysics erosion,
            HydrologySolver hydrology,
            AtmosphereClimate climate,
            SoilPedology soil,
            int seed)
        {
            int count = W * H;
            var landIndices = new List<int>(count * 3 / 4);
            for (int i = 0; i < count; i++)
            {
                // Include shallow depressed wetland pools as part of emergent continent land budget!
                bool isEmergent = erosion.HeightMap[i] > 0.20f || (!tectonic.IsOceanConnected[i] && hydrology.WetlandMask[i] > 0.45f);
                if (isEmergent && !(hydrology.RiverMaskMap[i] > 0.55f && hydrology.WaterDepthMap[i] > 1.2f))
                    landIndices.Add(i);
            }

            int totalLand = Math.Max(1, landIndices.Count);
            TotalEmergentLandCells = totalLand;

            // Compute domain-warped ForestMacroMask across the continent (sharp natural forest boundary via smoothstep(0.45, 0.56))
            Parallel.For(0, H, gz =>
            {
                float wz = gz * Cell;
                for (int gx = 0; gx < W; gx++)
                {
                    int idx = gz * W + gx;
                    float wx = gx * Cell;
                    float warpX = (FastNoise.Fbm2D(wx * 0.0024f, wz * 0.0024f, seed + 811, 3) - 0.5f) * 420.0f;
                    float warpZ = (FastNoise.Fbm2D(wx * 0.0024f + 19.3f, wz * 0.0024f + 7.1f, seed + 829, 3) - 0.5f) * 420.0f;
                    float macroPatch = FastNoise.Fbm2D((wx + warpX) * 0.00115f, (wz + warpZ) * 0.00115f, seed + 853, 4);
                    float windwardForest = climate.MoistureMap[idx] * 0.52f + tectonic.ForestFeature[idx] * 0.34f + macroPatch * 0.48f
                                         - hydrology.FloodplainMask[idx] * 0.45f - hydrology.WetlandMask[idx] * 0.35f;
                    ForestMacroMask[idx] = FastNoise.SmoothStep(0.45f, 0.56f, windwardForest);
                }
            });

            // Hierarchical physical suitability assignment calibrated to exact target land shares:
            // Coastline (5.0%), Alpine/Cliffs (10.8%), Arid Red Desert (12.8%), Wetland/Delta (9.8%),
            // Open Steppe (16.8%), Alluvial Floodplain (21.2%), Primeval Dense Forest (remaining 23.6% -> tuned to 25.4%)!
            bool[] assigned = new bool[count];
            var scored = new (float Score, int Idx)[totalLand];

            void AssignTopShare(float shareOfTotalLand, LandEcosystemId targetEco, Func<int, float> scoreFn)
            {
                int targetCount = (int)MathF.Round(totalLand * shareOfTotalLand);
                int n = 0;
                for (int k = 0; k < landIndices.Count; k++)
                {
                    int idx = landIndices[k];
                    if (assigned[idx]) continue;
                    scored[n++] = (scoreFn(idx), idx);
                }
                Array.Sort(scored, 0, n, Comparer<(float Score, int Idx)>.Create((a, b) => b.Score.CompareTo(a.Score)));
                int take = Math.Min(targetCount, n);
                for (int k = 0; k < take; k++)
                {
                    int idx = scored[k].Idx;
                    assigned[idx] = true;
                    EcosystemMap[idx] = targetEco;
                    EcosystemLandCounts[(int)targetEco]++;
                }
            }

            // 7. Coastline & Salt Dunes: 4.6% (target 4-6%)
            AssignTopShare(0.046f, LandEcosystemId.CoastlineSaltDunes, idx =>
                FastNoise.SmoothStep(140.0f, 6.0f, tectonic.CoastDistMeters[idx])
                * FastNoise.SmoothStep(14.0f, 0.4f, erosion.HeightMap[idx])
                * (1.0f - FastNoise.SmoothStep(22.0f, 35.0f, erosion.SlopeDegMap[idx]))
                * (1.0f - hydrology.RiverMaskMap[idx] * 0.65f));

            // 6. Alpine Snow, Tundra & Bare Cliffs: 10.6% (target 10-12%)
            AssignTopShare(0.106f, LandEcosystemId.AlpineSnowTundraRock, idx =>
                MathF.Max(
                    FastNoise.SmoothStep(4.5f, -4.5f, climate.TemperatureMap[idx]) * 1.15f,
                    MathF.Max(
                        FastNoise.SmoothStep(25.0f, 38.0f, erosion.SlopeDegMap[idx]) * 1.20f,
                        FastNoise.SmoothStep(115.0f, 220.0f, erosion.HeightMap[idx]) * 0.95f)));

            // 5. Arid Red Desert, Wadis & Oasis: 12.6% (target 12-14%)
            AssignTopShare(0.126f, LandEcosystemId.AridRedDesertOasis, idx =>
                soil.WAridRed[idx] * 1.30f + tectonic.SwDesertWeight[idx] * 0.95f
                + FastNoise.SmoothStep(21.0f, 31.0f, climate.TemperatureMap[idx]) * (1.0f - climate.MoistureMap[idx]) * 0.55f);

            // 3. Wetland & River Delta: 9.6% (target 8-12%)
            AssignTopShare(0.096f, LandEcosystemId.WetlandAndDelta, idx =>
            {
                float hAbove = MathF.Max(-0.5f, erosion.HeightMap[idx] - hydrology.LocalWaterTableMap[idx]);
                return hydrology.WetlandMask[idx] * 1.60f
                     + (hydrology.HasInlandWater[idx] ? 1.10f : 0.0f)
                     + (1.0f - FastNoise.SmoothStep(1.8f, 4.5f, erosion.SlopeDegMap[idx]))
                       * FastNoise.SmoothStep(3.8f, 0.2f, hAbove)
                       * (hydrology.GroundwaterMap[idx] + hydrology.FlowAccumMap[idx] * 0.6f) * 0.85f;
            });

            // 4. Open Steppe & Windy Plateau: 16.6% (target 16-18%)
            AssignTopShare(0.166f, LandEcosystemId.OpenSteppePlateau, idx =>
                soil.WSteppeLoess[idx] * 1.35f + tectonic.NeAutumnWeight[idx] * 1.05f
                + FastNoise.SmoothStep(9.0f, 21.0f, climate.WindSpeedMap[idx]) * (1.0f - climate.MoistureMap[idx] * 0.65f) * 0.55f);

            // 2. Alluvial Floodplain & Point Bars: 20.8% (target 20-24%)
            AssignTopShare(0.208f, LandEcosystemId.AlluvialFloodplain, idx =>
                hydrology.FloodplainMask[idx] * 1.45f
                + (1.0f - FastNoise.SmoothStep(2.5f, 8.5f, erosion.SlopeDegMap[idx]))
                  * FastNoise.SmoothStep(42.0f, 3.0f, erosion.HeightMap[idx])
                  * (0.55f + hydrology.GroundwaterMap[idx] * 0.45f)
                - ForestMacroMask[idx] * 0.80f);

            // 1. Primeval Dense Forest: Remaining 25.2% (target 24-28%) -> exact 100.0% total!
            for (int k = 0; k < landIndices.Count; k++)
            {
                int idx = landIndices[k];
                if (!assigned[idx])
                {
                    assigned[idx] = true;
                    EcosystemMap[idx] = LandEcosystemId.PrimevalDenseForest;
                    EcosystemLandCounts[(int)LandEcosystemId.PrimevalDenseForest]++;
                }
            }

            // Synchronize GPU FloodplainMask, WetlandMask & ForestMacroMask with final 7-Ecosystem classification (smoothed 2 passes)
            for (int i = 0; i < count; i++)
            {
                switch (EcosystemMap[i])
                {
                    case LandEcosystemId.PrimevalDenseForest:
                        ForestMacroMask[i] = MathF.Max(ForestMacroMask[i], 0.85f);
                        hydrology.FloodplainMask[i] *= 0.20f;
                        break;
                    case LandEcosystemId.AlluvialFloodplain:
                        hydrology.FloodplainMask[i] = MathF.Max(hydrology.FloodplainMask[i], 0.78f);
                        ForestMacroMask[i] = 0.0f;
                        break;
                    case LandEcosystemId.WetlandAndDelta:
                        hydrology.WetlandMask[i] = MathF.Max(hydrology.WetlandMask[i], 0.76f);
                        ForestMacroMask[i] *= 0.25f;
                        break;
                    default:
                        ForestMacroMask[i] *= 0.15f;
                        break;
                }
            }
            SmoothFloatGrid(hydrology.FloodplainMask, 2);
            SmoothFloatGrid(hydrology.WetlandMask, 2);
            SmoothFloatGrid(ForestMacroMask, 2);
        }

        private static void SmoothFloatGrid(float[] grid, int passes)
        {
            float[] tmp = new float[grid.Length];
            for (int p = 0; p < passes; p++)
            {
                Array.Copy(grid, tmp, grid.Length);
                Parallel.For(1, H - 1, z =>
                {
                    for (int x = 1; x < W - 1; x++)
                    {
                        int idx = z * W + x;
                        tmp[idx] = (grid[idx] * 4.0f + grid[idx - 1] + grid[idx + 1] + grid[idx - W] + grid[idx + W]) / 8.0f;
                    }
                });
                Array.Copy(tmp, grid, grid.Length);
            }
        }

        private void AddDetailInstance(FloraSpeciesId id, float wx, float wz, float h, float scale, float yaw, Color customData, byte variant = 0)
        {
            int mx = Math.Clamp((int)(wx / MicroCellSize), 0, MicroCols - 1);
            int mz = Math.Clamp((int)(wz / MicroCellSize), 0, MicroRows - 1);
            var basis = Basis.Identity.Rotated(Vector3.Up, yaw).Scaled(new Vector3(scale, scale, scale));
            MicroDetailCells[mx, mz].Add(new FloraInstance(id, new Transform3D(basis, new Vector3(wx, h - 0.10f, wz)), customData, variant));
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
                    float w = MathF.Exp(-dist2 * invR2 * 1.65f);
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
            int idx = gz * W + gx;
            string ecoLabel = GetEcosystemNameVi(EcosystemMap[idx]);
            sbyte id = DominantSpeciesMap[idx];
            return id >= 0 && id < FloraNicheDatabase.AllSpecies.Length
                ? $"{ecoLabel} ({FloraNicheDatabase.AllSpecies[id].DisplayName})"
                : ecoLabel;
        }

        public static string GetEcosystemNameVi(LandEcosystemId eco) => eco switch
        {
            LandEcosystemId.PrimevalDenseForest => "Rừng Già Khép Tán",
            LandEcosystemId.AlluvialFloodplain => "Đồng Bằng Phù Sa",
            LandEcosystemId.WetlandAndDelta => "Đầm Lầy & Châu Thổ",
            LandEcosystemId.OpenSteppePlateau => "Thảo Nguyên Gió",
            LandEcosystemId.AridRedDesertOasis => "Hoang Mạc & Ốc Đảo",
            LandEcosystemId.AlpineSnowTundraRock => "Núi Tuyết & Đá Trơ",
            LandEcosystemId.CoastlineSaltDunes => "Bờ Biển & Cồn Cát",
            _ => "Biển / Hồ Nội Địa",
        };

        // RGBA8 Ecological Masks Texture: R=CanopyCoverage, G=FloodplainMask, B=WetlandMask, A=ForestMacroMask
        public ImageTexture BuildCanopyCoverageTexture(HydrologySolver hydrology)
        {
            byte[] data = new byte[W * H * 4];
            Parallel.For(0, W * H, i =>
            {
                int o = i * 4;
                data[o + 0] = (byte)(Math.Clamp(CanopyCoverageMap[i], 0.0f, 1.0f) * 255.0f);
                data[o + 1] = (byte)(Math.Clamp(hydrology.FloodplainMask[i], 0.0f, 1.0f) * 255.0f);
                data[o + 2] = (byte)(Math.Clamp(hydrology.WetlandMask[i], 0.0f, 1.0f) * 255.0f);
                data[o + 3] = (byte)(Math.Clamp(ForestMacroMask[i], 0.0f, 1.0f) * 255.0f);
            });
            return ImageTexture.CreateFromImage(Image.CreateFromData(W, H, false, Image.Format.Rgba8, data));
        }

        public ImageTexture BuildEmptyCoverageTexture(HydrologySolver hydrology)
        {
            byte[] data = new byte[W * H * 4];
            Parallel.For(0, W * H, i =>
            {
                int o = i * 4;
                data[o + 0] = 0;
                data[o + 1] = (byte)(Math.Clamp(hydrology.FloodplainMask[i], 0.0f, 1.0f) * 255.0f);
                data[o + 2] = (byte)(Math.Clamp(hydrology.WetlandMask[i], 0.0f, 1.0f) * 255.0f);
                data[o + 3] = 0;
            });
            return ImageTexture.CreateFromImage(Image.CreateFromData(W, H, false, Image.Format.Rgba8, data));
        }

        private static Color BuildInstanceTint(Color baseMult, float shift, float tempC, FloraSpeciesId id, float ageRatio, float phenoSeed)
        {
            // Keep RGB multiplier centered near [0.76..1.18] so real botanical leaf greens & Canopy AO stay vivid!
            float ageShade = Mathf.Lerp(1.06f, 0.90f, ageRatio);
            float r = (baseMult.R + shift * 0.7f) * ageShade;
            float g = (baseMult.G + shift * 0.6f) * ageShade;
            float b = (baseMult.B - shift * 0.3f) * ageShade;
            if (tempC < 2.0f && (id == FloraSpeciesId.BorealSnowPine || id == FloraSpeciesId.SilverGlacierSpruce))
            {
                r += 0.05f; g += 0.06f; b += 0.10f;
            }
            return new Color(Math.Clamp(r, 0.68f, 1.22f), Math.Clamp(g, 0.72f, 1.24f), Math.Clamp(b, 0.64f, 1.18f), phenoSeed);
        }

        private static uint Hash2D(int x, int y, int seed)
        {
            uint h = (uint)(x * 374761393 + y * 668265263 + seed * 1442695041);
            h = (h ^ (h >> 13)) * 1274126177U;
            return h ^ (h >> 16);
        }
    }
}
