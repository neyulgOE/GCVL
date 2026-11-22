using System;
using System.Collections.Generic;
using Godot;

namespace PrimevalWorld.WorldGen
{
    public enum BiomeId : byte
    {
        DeepOcean = 0,
        CoastalReef = 1,
        PrimevalForest = 2,
        AutumnSteppe = 3,
        TerracottaDesert = 4,
        GlacialAlpine = 5,
        SanctuaryIsland = 6,
    }

    public readonly struct TerrainSample
    {
        public readonly float Height;
        public readonly float RiverMask;
        public readonly float RiverWaterHeight;
        public readonly float CoastalMask;
        public readonly float Moisture;
        public readonly float ForestDensity;
        public readonly BiomeId Biome;

        public TerrainSample(
            float height,
            float riverMask,
            float riverWaterHeight,
            float coastalMask,
            float moisture,
            float forestDensity,
            BiomeId biome)
        {
            Height = height;
            RiverMask = riverMask;
            RiverWaterHeight = riverWaterHeight;
            CoastalMask = coastalMask;
            Moisture = moisture;
            ForestDensity = forestDensity;
            Biome = biome;
        }
    }

    public readonly struct RiverNode
    {
        public readonly Vector3 Position;
        public readonly float HalfWidth;
        public readonly Vector2 Tangent;
        public readonly float Curvature;

        public RiverNode(Vector3 position, float halfWidth, Vector2 tangent, float curvature)
        {
            Position = position;
            HalfWidth = halfWidth;
            Tangent = tangent;
            Curvature = curvature;
        }
    }

    /// <summary>
    /// Prehistoric Multi-Continent World Generator (3072m x 3072m, 769x769 heightfield).
    /// Generates 4 distinct continents & 5 prehistoric biomes 100% mathematically from Seed:
    /// 1. NW: Glacial Alpine Massif & Fjords
    /// 2. SW: Terracotta Dunes, Crater Rim & Turquoise Oasis
    /// 3. Center/East: Primeval Forest Valley, Crescent Bay & Meandering River
    /// 4. NE: Autumn Steppes Plateau
    /// 5. SE: Sanctuary Archipelago
    /// </summary>
    public sealed class WorldGenerator
    {
        public int Seed { get; private set; }

        public const float RegionSizeMeters = 3072.0f;
        public const float ChunkSizeMeters = 256.0f;
        public const int ChunksPerAxis = 12;         // 12 * 256m = 3072m
        public const int ChunkVerticesPerSide = 65;  // 4.0m vertex spacing
        public const float SeaLevel = 0.0f;

        private const int GridSize = 769; // 4.0m per cell across 3072m
        private const float CellSize = RegionSizeMeters / (GridSize - 1);

        private readonly float[] _heightGrid = new float[GridSize * GridSize];
        private readonly float[] _riverMaskGrid = new float[GridSize * GridSize];
        private readonly float[] _riverWaterYGrid = new float[GridSize * GridSize];
        private readonly float[] _moistureGrid = new float[GridSize * GridSize];
        private readonly float[] _forestGrid = new float[GridSize * GridSize];
        private readonly float[] _autumnWeight = new float[GridSize * GridSize];
        private readonly float[] _desertWeight = new float[GridSize * GridSize];
        private readonly float[] _glacialWeight = new float[GridSize * GridSize];
        private readonly float[] _sanctuaryWeight = new float[GridSize * GridSize];
        private readonly BiomeId[] _biomeGrid = new BiomeId[GridSize * GridSize];

        public List<RiverNode> MainRiverNodes { get; } = new();
        public List<RiverNode> TributaryNodes { get; } = new();
        public List<RiverNode> NwRiverNodes { get; } = new();
        public Vector2 OasisCenter { get; private set; }

        public WorldGenerator(int seed = 2026)
        {
            SetSeed(seed);
        }

        public void SetSeed(int newSeed)
        {
            Seed = newSeed;
            BuildRiverNetworks();
            GenerateHeightfield();
        }

        private static Vector2 EvalCubicBezier(Vector2 p0, Vector2 p1, Vector2 p2, Vector2 p3, float t)
        {
            float u = 1.0f - t;
            return u * u * u * p0
                 + 3.0f * u * u * t * p1
                 + 3.0f * u * t * t * p2
                 + t * t * t * p3;
        }

        private List<RiverNode> BuildCurvySpline(
            Vector2 p0, Vector2 p1, Vector2 p2, Vector2 p3,
            float startY, float endY, float startW, float endW,
            int steps, float meanderAmp, int noiseSeedOffset)
        {
            var raw = new Vector2[steps + 1];
            for (int i = 0; i <= steps; i++)
            {
                float t = i / (float)steps;
                Vector2 pt = EvalCubicBezier(p0, p1, p2, p3, t);
                Vector2 prev = EvalCubicBezier(p0, p1, p2, p3, MathF.Max(0.0f, t - 0.02f));
                Vector2 next = EvalCubicBezier(p0, p1, p2, p3, MathF.Min(1.0f, t + 0.02f));
                Vector2 dir = (next - prev).Normalized();
                Vector2 perp = new Vector2(-dir.Y, dir.X);

                float fade = MathF.Sin(t * MathF.PI);
                float offset = (MathF.Sin(t * MathF.PI * 5.0f) * 0.55f
                              + (FastNoise.Fbm2D(t * 7.5f, 14.2f, Seed + noiseSeedOffset, 3) - 0.5f) * 1.4f)
                             * meanderAmp * fade;
                raw[i] = pt + perp * offset;
            }

            var result = new List<RiverNode>(steps + 1);
            for (int i = 0; i <= steps; i++)
            {
                float t = i / (float)steps;
                Vector2 prev = raw[Math.Max(0, i - 1)];
                Vector2 next = raw[Math.Min(steps, i + 1)];
                Vector2 tangent = (next - prev).Normalized();

                Vector2 prev2 = raw[Math.Max(0, i - 4)];
                Vector2 next2 = raw[Math.Min(steps, i + 4)];
                Vector2 t1 = (raw[i] - prev2).Normalized();
                Vector2 t2 = (next2 - raw[i]).Normalized();
                float curvature = t1.X * t2.Y - t1.Y * t2.X;

                float waterY = Mathf.Lerp(startY, endY, FastNoise.SmoothStep(0.0f, 0.92f, t));
                waterY = MathF.Max(SeaLevel, waterY);

                float wNoise = FastNoise.Fbm2D(t * 8.0f, 33.1f, Seed + noiseSeedOffset + 23, 3);
                float halfW = Mathf.Lerp(startW, endW, FastNoise.SmoothStep(0.0f, 1.0f, t)) + (wNoise - 0.5f) * 4.5f;
                halfW = MathF.Max(4.5f, halfW);

                result.Add(new RiverNode(new Vector3(raw[i].X, waterY, raw[i].Y), halfW, tangent, curvature));
            }
            return result;
        }

        private void BuildRiverNetworks()
        {
            float sx = FastNoise.GradientNoise2D(Seed * 0.17f, 2.3f, Seed + 11) * 70.0f;
            float sz = FastNoise.GradientNoise2D(Seed * 0.17f, 8.1f, Seed + 19) * 60.0f;

            OasisCenter = new Vector2(880.0f + sx * 0.5f, 2090.0f + sz * 0.4f);

            // 1. East Continent Main River: Autumn Steppes foothills -> Primeval Valley -> Southern Bay
            MainRiverNodes.Clear();
            MainRiverNodes.AddRange(BuildCurvySpline(
                new Vector2(2150.0f + sx, 980.0f + sz),
                new Vector2(1820.0f, 1340.0f),
                new Vector2(2140.0f, 1780.0f),
                new Vector2(1740.0f, 2480.0f),
                14.5f, 0.0f, 8.5f, 24.0f, 220, 82.0f, 503));

            // 2. Curvy Tributary from Eastern Ridge joining Main River organically (NOT a straight line!)
            int joinIdx = (int)(MainRiverNodes.Count * 0.44f);
            RiverNode join = MainRiverNodes[joinIdx];
            TributaryNodes.Clear();
            TributaryNodes.AddRange(BuildCurvySpline(
                new Vector2(2560.0f, 1280.0f),
                new Vector2(2380.0f, 1480.0f),
                new Vector2(2240.0f, 1320.0f),
                new Vector2(join.Position.X, join.Position.Z),
                join.Position.Y + 6.0f, join.Position.Y, 5.0f, 8.5f, 95, 58.0f, 733));

            // 3. NW Glacial Continent Meltwater Stream flowing from alpine valley to southern fjord bay
            NwRiverNodes.Clear();
            NwRiverNodes.AddRange(BuildCurvySpline(
                new Vector2(840.0f, 680.0f),
                new Vector2(1040.0f, 830.0f),
                new Vector2(780.0f, 1020.0f),
                new Vector2(930.0f, 1240.0f),
                12.0f, 0.0f, 6.5f, 14.0f, 100, 48.0f, 887));
        }

        private void GenerateHeightfield()
        {
            for (int gz = 0; gz < GridSize; gz++)
            {
                float worldZ = gz * CellSize;
                for (int gx = 0; gx < GridSize; gx++)
                {
                    float worldX = gx * CellSize;
                    int idx = gz * GridSize + gx;

                    // Strong domain warping for organic fjords, capes & archipelagos
                    float warpX = (FastNoise.Fbm2D(worldX * 0.0010f, worldZ * 0.0010f, Seed + 11, 4) - 0.5f) * 340.0f;
                    float warpZ = (FastNoise.Fbm2D(worldX * 0.0010f + 39.2f, worldZ * 0.0010f - 21.7f, Seed + 29, 4) - 0.5f) * 340.0f;
                    float wx = worldX + warpX;
                    float wz = worldZ + warpZ;
                    float coastNoise = (FastNoise.Fbm2D(worldX * 0.0022f, worldZ * 0.0022f, Seed + 71, 4) - 0.5f) * 0.34f;

                    // --- 1. NW Glacial Alpine Continent ---
                    float nwDist = MathF.Sqrt(MathF.Pow((wx - 790.0f) / 480.0f, 2) + MathF.Pow((wz - 730.0f) / 470.0f, 2));
                    float nwFjord = FastNoise.Fbm2D(worldX * 0.0055f, worldZ * 0.0055f, Seed + 131, 4);
                    float nwMask = 1.0f - FastNoise.SmoothStep(0.55f, 1.02f, nwDist + coastNoise + (nwFjord - 0.5f) * 0.25f);

                    // --- 2. SW Terracotta Dunes Continent ---
                    float swDist = MathF.Sqrt(MathF.Pow((wx - 760.0f) / 450.0f, 2) + MathF.Pow((wz - 2140.0f) / 430.0f, 2));
                    float swMask = 1.0f - FastNoise.SmoothStep(0.58f, 1.02f, swDist + coastNoise);

                    // --- 3. East & Center Grand Continent (Autumn Steppes NE + Primeval Forest Center/South) ---
                    float eNorthDist = MathF.Sqrt(MathF.Pow((wx - 2140.0f) / 560.0f, 2) + MathF.Pow((wz - 880.0f) / 490.0f, 2));
                    float eSouthDist = MathF.Sqrt(MathF.Pow((wx - 1960.0f) / 620.0f, 2) + MathF.Pow((wz - 1880.0f) / 640.0f, 2));
                    float eBridgeDist = MathF.Sqrt(MathF.Pow((wx - 2080.0f) / 420.0f, 2) + MathF.Pow((wz - 1340.0f) / 400.0f, 2));
                    float eRaw = MathF.Max(
                        1.0f - FastNoise.SmoothStep(0.56f, 1.02f, eNorthDist + coastNoise),
                        MathF.Max(
                            1.0f - FastNoise.SmoothStep(0.58f, 1.03f, eSouthDist + coastNoise),
                            1.0f - FastNoise.SmoothStep(0.55f, 1.02f, eBridgeDist + coastNoise)
                        )
                    );
                    // Carve Crescent Bay on the southern-east coast
                    float bayDist = MathF.Sqrt(MathF.Pow((wx - 2120.0f) / 240.0f, 2) + MathF.Pow((wz - 2080.0f) / 250.0f, 2));
                    float bayCarve = 1.0f - FastNoise.SmoothStep(0.32f, 0.96f, bayDist);
                    float eastMask = eRaw * (1.0f - bayCarve * 0.92f);

                    // --- 4. SE Sanctuary Archipelago ---
                    float seDist = MathF.Sqrt(MathF.Pow((wx - 2660.0f) / 210.0f, 2) + MathF.Pow((wz - 2560.0f) / 205.0f, 2));
                    float seMain = 1.0f - FastNoise.SmoothStep(0.50f, 0.96f, seDist + coastNoise * 0.6f);
                    float seRing = 1.0f - FastNoise.SmoothStep(0.18f, 0.36f, MathF.Abs(seDist - 1.18f) + coastNoise * 0.4f);
                    float seMask = MathF.Max(seMain, seRing * 0.72f);

                    float continentMask = MathF.Max(MathF.Max(nwMask, swMask), MathF.Max(eastMask, seMask));

                    // --- Biome Regional Weights ---
                    float wGlacial = nwMask;
                    float wDesert = swMask;
                    float wSanctuary = seMask;
                    float wAutumn = eastMask * FastNoise.SmoothStep(1320.0f, 960.0f, wz);
                    _glacialWeight[idx] = wGlacial;
                    _desertWeight[idx] = wDesert;
                    _sanctuaryWeight[idx] = wSanctuary;
                    _autumnWeight[idx] = wAutumn;

                    // --- Elevation Profiles per Continent ---
                    float plains = FastNoise.Fbm2D(wx * 0.0014f, wz * 0.0014f, Seed + 101, 5);
                    float ridged = MathF.Pow(FastNoise.RidgedFbm2D(wx * 0.0017f, wz * 0.0017f, Seed + 307, 6), 1.18f);
                    float dunes = FastNoise.RidgedFbm2D(worldX * 0.0045f, worldZ * 0.0018f, Seed + 419, 3);

                    // NW Alpine Peaks (sharp snow peaks in north of NW continent)
                    float nwPeakZone = nwMask * FastNoise.SmoothStep(920.0f, 440.0f, wz);
                    float nwHeight = 5.0f + plains * 18.0f + nwPeakZone * ridged * 118.0f;

                    // SW Terracotta Crater Rim & Sand Dunes Basin + Oasis Depression
                    float craterRim = swMask * MathF.Exp(-MathF.Pow((swDist - 0.56f) / 0.24f, 2));
                    float oasisDist = MathF.Sqrt(MathF.Pow(worldX - OasisCenter.X, 2) + MathF.Pow(worldZ - OasisCenter.Y, 2));
                    float oasisCarve = 1.0f - FastNoise.SmoothStep(35.0f, 130.0f, oasisDist);
                    float swHeight = (6.0f + dunes * 11.0f + craterRim * (28.0f + ridged * 38.0f)) * (1.0f - oasisCarve)
                                   + (-2.2f) * oasisCarve;

                    // East Continent: Autumn Steppes Plateau (NE) + Broad Primeval Valley (Center/South)
                    float plateauBoost = wAutumn * (14.0f + plains * 14.0f);
                    float eastRidge = eastMask * FastNoise.SmoothStep(2350.0f, 2650.0f, wx) * ridged * 36.0f;
                    float eastHeight = 4.0f + plains * 16.0f + plateauBoost + eastRidge;

                    // SE Sanctuary Island
                    float seHeight = 5.0f + plains * 14.0f + seMain * ridged * 24.0f;

                    float rawLandH = (nwHeight * nwMask + swHeight * swMask + eastHeight * eastMask + seHeight * seMask)
                                   / MathF.Max(0.001f, nwMask + swMask + eastMask + seMask);

                    // Shallow turquoise coral shelf (-3.5m .. 0m) transitioning to deep ocean (-13m)
                    float shelfT = FastNoise.SmoothStep(0.0f, 0.24f, continentMask);
                    float seaBed = -13.0f + plains * 2.5f;
                    float shelfBed = -3.2f + plains * 1.2f;
                    float oceanFloor = seaBed * (1.0f - shelfT) + shelfBed * shelfT;

                    float landBlend = FastNoise.SmoothStep(0.14f, 0.34f, continentMask);
                    _heightGrid[idx] = oceanFloor * (1.0f - landBlend) + rawLandH * landBlend;
                }
            }

            // Particle Hydraulic Erosion (70,000 droplets for crisp mountain gullies & ridges)
            ApplyHydraulicErosion(70000);

            // Carve curvy rivers & compute biome/forest splat fields
            CarveHydrologyAndEcology();
        }

        private void CarveHydrologyAndEcology()
        {
            for (int gz = 0; gz < GridSize; gz++)
            {
                float worldZ = gz * CellSize;
                for (int gx = 0; gx < GridSize; gx++)
                {
                    int idx = gz * GridSize + gx;
                    float worldX = gx * CellSize;
                    float h = _heightGrid[idx];

                    float bestRiverMask = 0.0f;
                    float bestValleyT = 0.0f;
                    float targetWaterY = SeaLevel;

                    // Carve all 3 curvy rivers gently (only 2.0-2.8m below WaterY so no deep black canyons!)
                    void ApplyRiver(List<RiverNode> nodes, float depth)
                    {
                        var (dist, node, cross) = FindClosestRiverNode(nodes, worldX, worldZ);
                        if (dist >= node.HalfWidth * 4.5f) return;

                        float bankJitter = (FastNoise.Fbm2D(worldX * 0.020f, worldZ * 0.020f, Seed + 709, 3) - 0.5f) * 7.5f;
                        float effDist = MathF.Abs(dist + bankJitter);
                        bool isOuterBank = (cross * node.Curvature) > 0.0f;
                        float bankMult = isOuterBank ? 1.15f : 1.70f;

                        float valleyT = 1.0f - FastNoise.SmoothStep(node.HalfWidth * 1.1f, node.HalfWidth * 4.2f, effDist);
                        bestValleyT = MathF.Max(bestValleyT, valleyT);

                        float valleyFloor = node.Position.Y + 1.5f;
                        h = h * (1.0f - valleyT * 0.55f) + MathF.Min(h, valleyFloor + 6.0f) * (valleyT * 0.55f);

                        float channelT = 1.0f - FastNoise.SmoothStep(node.HalfWidth * 0.45f, node.HalfWidth * bankMult, effDist);
                        if (channelT > 0.001f)
                        {
                            float bedY = node.Position.Y - depth;
                            h = h * (1.0f - channelT) + MathF.Min(h, bedY) * channelT;
                            targetWaterY = node.Position.Y;
                        }

                        float sandT = 1.0f - FastNoise.SmoothStep(node.HalfWidth * 0.65f, node.HalfWidth * (isOuterBank ? 1.25f : 1.95f), effDist);
                        bestRiverMask = MathF.Max(bestRiverMask, MathF.Max(channelT, sandT * 0.78f));
                    }

                    ApplyRiver(MainRiverNodes, 2.6f);
                    ApplyRiver(TributaryNodes, 1.9f);
                    ApplyRiver(NwRiverNodes, 2.2f);

                    _heightGrid[idx] = h;
                    _riverMaskGrid[idx] = bestRiverMask;
                    _riverWaterYGrid[idx] = targetWaterY;

                    // Oasis moisture boost in SW desert
                    float oasisDist = MathF.Sqrt(MathF.Pow(worldX - OasisCenter.X, 2) + MathF.Pow(worldZ - OasisCenter.Y, 2));
                    float oasisMoist = 1.0f - FastNoise.SmoothStep(30.0f, 165.0f, oasisDist);

                    float coastal = FastNoise.SmoothStep(3.5f, -1.5f, h);
                    float moisture = Math.Clamp(
                        0.40f + bestValleyT * 0.45f + oasisMoist * 0.75f + coastal * 0.20f
                        - _desertWeight[idx] * 0.34f - (h / 120.0f) * 0.28f,
                        0.0f, 1.0f);
                    _moistureGrid[idx] = moisture;

                    // Dominant Biome classification
                    if (h < -4.2f) _biomeGrid[idx] = BiomeId.DeepOcean;
                    else if (h < 0.8f) _biomeGrid[idx] = BiomeId.CoastalReef;
                    else if (_glacialWeight[idx] > 0.45f) _biomeGrid[idx] = BiomeId.GlacialAlpine;
                    else if (_desertWeight[idx] > 0.45f) _biomeGrid[idx] = BiomeId.TerracottaDesert;
                    else if (_sanctuaryWeight[idx] > 0.40f) _biomeGrid[idx] = BiomeId.SanctuaryIsland;
                    else if (_autumnWeight[idx] > 0.45f) _biomeGrid[idx] = BiomeId.AutumnSteppe;
                    else _biomeGrid[idx] = BiomeId.PrimevalForest;

                    // Dense Prehistoric Forest Canopy Coverage (organic groves + riparian + oasis + sanctuary)
                    float groveNoise = FastNoise.Fbm2D(worldX * 0.0028f + 19.4f, worldZ * 0.0028f - 8.7f, Seed + 907, 4);
                    float groveMask = FastNoise.SmoothStep(0.38f, 0.62f, groveNoise);

                    float biomeForestFactor = _biomeGrid[idx] switch
                    {
                        BiomeId.PrimevalForest => MathF.Max(groveMask * 1.05f, bestValleyT * 0.90f),
                        BiomeId.SanctuaryIsland => MathF.Max(0.75f, groveMask),
                        BiomeId.AutumnSteppe => MathF.Max(groveMask * 0.52f, bestValleyT * 0.75f),
                        BiomeId.GlacialAlpine => FastNoise.SmoothStep(0.42f, 0.68f, groveNoise) * (1.0f - FastNoise.SmoothStep(36.0f, 52.0f, h)),
                        BiomeId.TerracottaDesert => MathF.Max(oasisMoist * 0.95f, (groveMask - 0.55f) * 0.6f),
                        _ => 0.0f,
                    };

                    float altLimit = FastNoise.SmoothStep(1.2f, 3.8f, h) * (1.0f - FastNoise.SmoothStep(48.0f, 62.0f, h));
                    _forestGrid[idx] = Math.Clamp(biomeForestFactor * altLimit, 0.0f, 1.0f);
                }
            }
        }

        private static (float Dist, RiverNode Node, float SignedCross) FindClosestRiverNode(
            List<RiverNode> nodes, float wx, float wz)
        {
            float bestDistSq = float.MaxValue;
            int bestIdx = 0;

            for (int i = 0; i < nodes.Count; i += 6)
            {
                Vector3 p = nodes[i].Position;
                float dx = wx - p.X;
                float dz = wz - p.Z;
                float d2 = dx * dx + dz * dz;
                if (d2 < bestDistSq)
                {
                    bestDistSq = d2;
                    bestIdx = i;
                }
            }

            int start = Math.Max(0, bestIdx - 6);
            int end = Math.Min(nodes.Count - 1, bestIdx + 6);
            for (int i = start; i <= end; i++)
            {
                Vector3 p = nodes[i].Position;
                float dx = wx - p.X;
                float dz = wz - p.Z;
                float d2 = dx * dx + dz * dz;
                if (d2 < bestDistSq)
                {
                    bestDistSq = d2;
                    bestIdx = i;
                }
            }

            RiverNode node = nodes[bestIdx];
            float rx = wx - node.Position.X;
            float rz = wz - node.Position.Z;
            float cross = rx * node.Tangent.Y - rz * node.Tangent.X;
            return (MathF.Sqrt(bestDistSq), node, cross);
        }

        private void ApplyHydraulicErosion(int numDroplets)
        {
            var rng = new Random(Seed + 991);
            const int maxLifetime = 30;
            const float inertia = 0.08f;
            const float sedimentCapacityFactor = 3.8f;
            const float minSedimentCapacity = 0.01f;
            const float erodeSpeed = 0.30f;
            const float depositSpeed = 0.28f;
            const float evaporateSpeed = 0.02f;
            const float gravity = 4.0f;
            const int brushRadius = 2;

            for (int d = 0; d < numDroplets; d++)
            {
                float posX = (float)(rng.NextDouble() * (GridSize - 4) + 2);
                float posZ = (float)(rng.NextDouble() * (GridSize - 4) + 2);
                float dirX = 0.0f;
                float dirZ = 0.0f;
                float speed = 1.0f;
                float water = 1.0f;
                float sediment = 0.0f;

                for (int step = 0; step < maxLifetime; step++)
                {
                    int nodeX = (int)posX;
                    int nodeZ = (int)posZ;
                    if (nodeX < 1 || nodeX >= GridSize - 2 || nodeZ < 1 || nodeZ >= GridSize - 2) break;

                    float cellOffsetX = posX - nodeX;
                    float cellOffsetZ = posZ - nodeZ;

                    int idx00 = nodeZ * GridSize + nodeX;
                    float h00 = _heightGrid[idx00];
                    float h10 = _heightGrid[idx00 + 1];
                    float h01 = _heightGrid[idx00 + GridSize];
                    float h11 = _heightGrid[idx00 + GridSize + 1];

                    float oldH = (h00 * (1 - cellOffsetX) + h10 * cellOffsetX) * (1 - cellOffsetZ)
                               + (h01 * (1 - cellOffsetX) + h11 * cellOffsetX) * cellOffsetZ;
                    if (oldH < SeaLevel - 0.5f) break;

                    float gradX = (h10 - h00) * (1 - cellOffsetZ) + (h11 - h01) * cellOffsetZ;
                    float gradZ = (h01 - h00) * (1 - cellOffsetX) + (h11 - h10) * cellOffsetX;

                    dirX = dirX * inertia - gradX * (1.0f - inertia);
                    dirZ = dirZ * inertia - gradZ * (1.0f - inertia);
                    float len = MathF.Sqrt(dirX * dirX + dirZ * dirZ);
                    if (len < 1e-5f)
                    {
                        float angle = (float)(rng.NextDouble() * MathF.PI * 2.0);
                        dirX = MathF.Cos(angle);
                        dirZ = MathF.Sin(angle);
                    }
                    else
                    {
                        dirX /= len;
                        dirZ /= len;
                    }

                    posX += dirX;
                    posZ += dirZ;
                    if (posX < 1 || posX >= GridSize - 2 || posZ < 1 || posZ >= GridSize - 2) break;

                    int newX = (int)posX;
                    int newZ = (int)posZ;
                    float u = posX - newX;
                    float v = posZ - newZ;
                    int nIdx = newZ * GridSize + newX;
                    float newH = (_heightGrid[nIdx] * (1 - u) + _heightGrid[nIdx + 1] * u) * (1 - v)
                               + (_heightGrid[nIdx + GridSize] * (1 - u) + _heightGrid[nIdx + GridSize + 1] * u) * v;

                    float deltaH = newH - oldH;
                    float capacity = MathF.Max(-deltaH * speed * water * sedimentCapacityFactor, minSedimentCapacity);

                    if (sediment > capacity || deltaH > 0.0f)
                    {
                        float amountToDeposit = deltaH > 0.0f
                            ? MathF.Min(deltaH, sediment)
                            : (sediment - capacity) * depositSpeed;
                        sediment -= amountToDeposit;

                        _heightGrid[idx00] += amountToDeposit * (1 - cellOffsetX) * (1 - cellOffsetZ);
                        _heightGrid[idx00 + 1] += amountToDeposit * cellOffsetX * (1 - cellOffsetZ);
                        _heightGrid[idx00 + GridSize] += amountToDeposit * (1 - cellOffsetX) * cellOffsetZ;
                        _heightGrid[idx00 + GridSize + 1] += amountToDeposit * cellOffsetX * cellOffsetZ;
                    }
                    else
                    {
                        float amountToErode = MathF.Min((capacity - sediment) * erodeSpeed, -deltaH);
                        float totalWeight = 0.0f;
                        for (int bz = -brushRadius; bz <= brushRadius; bz++)
                        {
                            for (int bx = -brushRadius; bx <= brushRadius; bx++)
                            {
                                int tx = nodeX + bx;
                                int tz = nodeZ + bz;
                                if (tx < 0 || tx >= GridSize || tz < 0 || tz >= GridSize) continue;
                                float dist = MathF.Sqrt(bx * bx + bz * bz);
                                if (dist < brushRadius) totalWeight += brushRadius - dist;
                            }
                        }

                        if (totalWeight > 1e-5f)
                        {
                            for (int bz = -brushRadius; bz <= brushRadius; bz++)
                            {
                                for (int bx = -brushRadius; bx <= brushRadius; bx++)
                                {
                                    int tx = nodeX + bx;
                                    int tz = nodeZ + bz;
                                    if (tx < 0 || tx >= GridSize || tz < 0 || tz >= GridSize) continue;
                                    float dist = MathF.Sqrt(bx * bx + bz * bz);
                                    if (dist < brushRadius)
                                    {
                                        float w = (brushRadius - dist) / totalWeight;
                                        float deltaSediment = MathF.Min(_heightGrid[tz * GridSize + tx] - (SeaLevel - 13.0f), amountToErode * w);
                                        _heightGrid[tz * GridSize + tx] -= deltaSediment;
                                        sediment += deltaSediment;
                                    }
                                }
                            }
                        }
                    }

                    speed = MathF.Sqrt(MathF.Max(0.01f, speed * speed + deltaH * gravity));
                    water *= (1.0f - evaporateSpeed);
                }
            }
        }

        private static float SampleBilinear(float[] grid, float gx, float gz)
        {
            float cx = Math.Clamp(gx, 0.0f, GridSize - 1.001f);
            float cz = Math.Clamp(gz, 0.0f, GridSize - 1.001f);
            int x0 = (int)cx;
            int z0 = (int)cz;
            float tx = cx - x0;
            float tz = cz - z0;

            int idx = z0 * GridSize + x0;
            float v00 = grid[idx];
            float v10 = grid[idx + 1];
            float v01 = grid[idx + GridSize];
            float v11 = grid[idx + GridSize + 1];

            return (v00 * (1 - tx) + v10 * tx) * (1 - tz) + (v01 * (1 - tx) + v11 * tx) * tz;
        }

        public TerrainSample SamplePoint(float worldX, float worldZ)
        {
            if (worldX < 0.0f || worldX > RegionSizeMeters || worldZ < 0.0f || worldZ > RegionSizeMeters)
            {
                return new TerrainSample(-12.0f, 0.0f, SeaLevel, 1.0f, 1.0f, 0.0f, BiomeId.DeepOcean);
            }

            float gx = worldX / CellSize;
            float gz = worldZ / CellSize;

            float height = SampleBilinear(_heightGrid, gx, gz);
            float riverMask = SampleBilinear(_riverMaskGrid, gx, gz);
            float riverWaterY = SampleBilinear(_riverWaterYGrid, gx, gz);
            float moisture = SampleBilinear(_moistureGrid, gx, gz);
            float forest = SampleBilinear(_forestGrid, gx, gz);
            float coastalMask = FastNoise.SmoothStep(3.5f, -1.5f, height);

            int ix = Math.Clamp((int)MathF.Round(gx), 0, GridSize - 1);
            int iz = Math.Clamp((int)MathF.Round(gz), 0, GridSize - 1);
            BiomeId biome = _biomeGrid[iz * GridSize + ix];

            return new TerrainSample(height, riverMask, riverWaterY, coastalMask, moisture, forest, biome);
        }

        public float SampleHeight(float worldX, float worldZ) => SamplePoint(worldX, worldZ).Height;

        public Vector3 SampleNormal(float worldX, float worldZ, float eps = 2.0f)
        {
            float hL = SampleHeight(worldX - eps, worldZ);
            float hR = SampleHeight(worldX + eps, worldZ);
            float hD = SampleHeight(worldX, worldZ - eps);
            float hU = SampleHeight(worldX, worldZ + eps);
            return new Vector3(hL - hR, 2.0f * eps, hD - hU).Normalized();
        }

        /// <summary>
        /// Generates an RGBA8 splat texture for terrain_triplanar.gdshader:
        /// R = AutumnSteppe, G = TerracottaDesert, B = GlacialAlpine, A = ForestCanopyCoverage.
        /// </summary>
        public ImageTexture BuildBiomeSplatTexture()
        {
            byte[] data = new byte[GridSize * GridSize * 4];
            for (int i = 0; i < GridSize * GridSize; i++)
            {
                int o = i * 4;
                data[o + 0] = (byte)(Math.Clamp(_autumnWeight[i], 0.0f, 1.0f) * 255.0f);
                data[o + 1] = (byte)(Math.Clamp(_desertWeight[i], 0.0f, 1.0f) * 255.0f);
                data[o + 2] = (byte)(Math.Clamp(_glacialWeight[i], 0.0f, 1.0f) * 255.0f);
                data[o + 3] = (byte)(Math.Clamp(_forestGrid[i], 0.0f, 1.0f) * 255.0f);
            }

            Image img = Image.CreateFromData(GridSize, GridSize, false, Image.Format.Rgba8, data);
            return ImageTexture.CreateFromImage(img);
        }

        /// <summary>
        /// Generates a crisp 512x512 2D Topographic Atlas ImageTexture directly from live world data
        /// for the [M] World Map overlay.
        /// </summary>
        public ImageTexture BuildWorldMapTexture(int size = 512)
        {
            byte[] rgb = new byte[size * size * 3];
            for (int py = 0; py < size; py++)
            {
                float wz = (py / (float)(size - 1)) * RegionSizeMeters;
                for (int px = 0; px < size; px++)
                {
                    float wx = (px / (float)(size - 1)) * RegionSizeMeters;
                    TerrainSample s = SamplePoint(wx, wz);
                    Vector3 n = SampleNormal(wx, wz, 4.0f);
                    float shade = 0.55f + 0.55f * Math.Clamp(n.Dot(new Vector3(-0.55f, 0.65f, -0.52f).Normalized()), 0.0f, 1.0f);

                    Color col;
                    if (s.Height < -4.2f)
                    {
                        col = new Color(0.04f, 0.16f, 0.30f);
                    }
                    else if (s.Height < 0.4f)
                    {
                        float t = FastNoise.SmoothStep(-4.2f, 0.4f, s.Height);
                        col = new Color(0.04f, 0.16f, 0.30f).Lerp(new Color(0.11f, 0.72f, 0.77f), t);
                    }
                    else if (s.RiverMask > 0.48f)
                    {
                        col = new Color(0.14f, 0.56f, 0.72f);
                    }
                    else
                    {
                        col = s.Biome switch
                        {
                            BiomeId.GlacialAlpine => s.Height > 46.0f
                                ? new Color(0.90f, 0.94f, 0.98f)
                                : new Color(0.24f, 0.35f, 0.22f),
                            BiomeId.TerracottaDesert => s.Moisture > 0.62f
                                ? new Color(0.15f, 0.48f, 0.28f)
                                : new Color(0.76f, 0.40f, 0.22f),
                            BiomeId.AutumnSteppe => new Color(0.78f, 0.50f, 0.18f),
                            BiomeId.SanctuaryIsland => new Color(0.11f, 0.36f, 0.16f),
                            _ => new Color(0.15f, 0.34f, 0.14f).Lerp(new Color(0.07f, 0.20f, 0.08f), s.ForestDensity),
                        };
                        col = new Color(
                            Math.Clamp(col.R * shade, 0.0f, 1.0f),
                            Math.Clamp(col.G * shade, 0.0f, 1.0f),
                            Math.Clamp(col.B * shade, 0.0f, 1.0f)
                        );
                    }

                    int o = (py * size + px) * 3;
                    rgb[o + 0] = (byte)(col.R * 255.0f);
                    rgb[o + 1] = (byte)(col.G * 255.0f);
                    rgb[o + 2] = (byte)(col.B * 255.0f);
                }
            }

            Image img = Image.CreateFromData(size, size, false, Image.Format.Rgb8, rgb);
            return ImageTexture.CreateFromImage(img);
        }
    }
}
