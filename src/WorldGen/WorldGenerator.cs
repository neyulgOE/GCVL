using System;
using System.Collections.Generic;
using Godot;

namespace PrimevalWorld.WorldGen
{
    public readonly struct TerrainSample
    {
        public readonly float Height;
        public readonly float RiverMask;
        public readonly float RiverWaterHeight;
        public readonly float CoastalMask;
        public readonly float Moisture;
        public readonly float ForestDensity;

        public TerrainSample(
            float height,
            float riverMask,
            float riverWaterHeight,
            float coastalMask,
            float moisture,
            float forestDensity)
        {
            Height = height;
            RiverMask = riverMask;
            RiverWaterHeight = riverWaterHeight;
            CoastalMask = coastalMask;
            Moisture = moisture;
            ForestDensity = forestDensity;
        }
    }

    public readonly struct RiverNode
    {
        public readonly Vector3 Position; // X, WaterY, Z
        public readonly float HalfWidth;
        public readonly Vector2 Tangent;  // Normalized XZ flow direction
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
    /// Stage 1+2 World Generator (2048m x 2048m, 769x769 heightfield).
    /// - Main island with northern/NW alpine massif, 60%+ open valleys/plains, & 2 offshore rocky islets.
    /// - 70,000-droplet Particle Hydraulic Erosion for crisp ridges & gullies.
    /// - Highland source lake + S-curve meandering river + tributary stream flowing monotonically to bay.
    /// - Forest grove density & moisture fields for ecological MultiMesh placement & ground shading.
    /// </summary>
    public sealed class WorldGenerator
    {
        public int Seed { get; private set; }

        public const float RegionSizeMeters = 2048.0f;
        public const float ChunkSizeMeters = 256.0f;
        public const int ChunksPerAxis = 8;          // 8 * 256m = 2048m
        public const int ChunkVerticesPerSide = 97;  // 2.6667m spacing
        public const float SeaLevel = 0.0f;

        private const int GridSize = 769; // 3 * 256 + 1
        private const float CellSize = RegionSizeMeters / (GridSize - 1);

        private readonly float[] _heightGrid = new float[GridSize * GridSize];
        private readonly float[] _riverMaskGrid = new float[GridSize * GridSize];
        private readonly float[] _riverWaterYGrid = new float[GridSize * GridSize];
        private readonly float[] _moistureGrid = new float[GridSize * GridSize];
        private readonly float[] _forestGrid = new float[GridSize * GridSize];

        public List<RiverNode> MainRiverNodes { get; } = new();
        public List<RiverNode> TributaryNodes { get; } = new();
        public Vector3 SourceLakeCenter { get; private set; }
        public float SourceLakeRadius { get; private set; } = 52.0f;

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

        private void BuildRiverNetworks()
        {
            MainRiverNodes.Clear();
            TributaryNodes.Clear();

            // Slight seed-driven shift of source lake & mouth while keeping balanced layout
            float sxOff = (FastNoise.GradientNoise2D(Seed * 0.13f, 3.1f, Seed + 11)) * 75.0f;
            float szOff = (FastNoise.GradientNoise2D(Seed * 0.13f, 7.9f, Seed + 17)) * 50.0f;

            // Source lake nestled at the southern foothills of the NW alpine massif
            Vector2 p0 = new Vector2(670.0f + sxOff, 690.0f + szOff);
            Vector2 p1 = new Vector2(1180.0f + sxOff * 0.5f, 890.0f);
            Vector2 p2 = new Vector2(720.0f - sxOff * 0.4f, 1290.0f);
            Vector2 p3 = new Vector2(1080.0f, 1690.0f); // Flows into the southern coastal bay

            SourceLakeCenter = new Vector3(p0.X, 17.5f, p0.Y);

            const int mainSteps = 240;
            var rawMain = new Vector2[mainSteps + 1];
            for (int i = 0; i <= mainSteps; i++)
            {
                float t = i / (float)mainSteps;
                Vector2 basePos = EvalCubicBezier(p0, p1, p2, p3, t);
                // Natural meandering S-ripples (fade at source & bay mouth)
                float meanderFade = MathF.Sin(t * MathF.PI);
                float meander = MathF.Sin(t * MathF.PI * 4.5f) * 58.0f
                              + (FastNoise.Fbm2D(t * 6.5f, 12.4f, Seed + 503, 3) - 0.5f) * 85.0f;
                rawMain[i] = basePos + new Vector2(meander * meanderFade, 0.0f);
            }

            for (int i = 0; i <= mainSteps; i++)
            {
                float t = i / (float)mainSteps;
                Vector2 prev = rawMain[Math.Max(0, i - 1)];
                Vector2 next = rawMain[Math.Min(mainSteps, i + 1)];
                Vector2 tangent = (next - prev).Normalized();

                // Curvature approximation for asymmetric cutbank vs point bar
                Vector2 prev2 = rawMain[Math.Max(0, i - 4)];
                Vector2 next2 = rawMain[Math.Min(mainSteps, i + 4)];
                Vector2 t1 = (rawMain[i] - prev2).Normalized();
                Vector2 t2 = (next2 - rawMain[i]).Normalized();
                float curvature = t1.X * t2.Y - t1.Y * t2.X;

                // Monotonically descending water surface from +17.5m source lake down to 0.0m sea level
                float waterY = SourceLakeCenter.Y * (1.0f - FastNoise.SmoothStep(0.02f, 0.88f, t));
                waterY = MathF.Max(SeaLevel, waterY);

                // Variable width: 9m upper stream -> 28m lower delta mouth
                float wNoise = FastNoise.Fbm2D(t * 9.0f, 44.1f, Seed + 617, 3);
                float halfWidth = 8.5f + wNoise * 7.5f + 22.0f * FastNoise.SmoothStep(0.60f, 0.94f, t);

                MainRiverNodes.Add(new RiverNode(new Vector3(rawMain[i].X, waterY, rawMain[i].Y), halfWidth, tangent, curvature));
            }

            // Tributary stream from eastern hills joining the main river around t = 0.45
            int joinIdx = (int)(mainSteps * 0.45f);
            RiverNode joinNode = MainRiverNodes[joinIdx];
            Vector2 tp0 = new Vector2(1460.0f, 790.0f + szOff * 0.6f);
            Vector2 tp1 = new Vector2(1310.0f, 920.0f);
            Vector2 tp2 = new Vector2(1140.0f, 1020.0f);
            Vector2 tp3 = new Vector2(joinNode.Position.X, joinNode.Position.Z);

            const int tribSteps = 90;
            var rawTrib = new Vector2[tribSteps + 1];
            for (int i = 0; i <= tribSteps; i++)
            {
                float t = i / (float)tribSteps;
                Vector2 basePos = EvalCubicBezier(tp0, tp1, tp2, tp3, t);
                float jitter = (FastNoise.Fbm2D(t * 5.0f, 88.3f, Seed + 733, 2) - 0.5f) * 38.0f * MathF.Sin(t * MathF.PI);
                rawTrib[i] = basePos + new Vector2(0.0f, jitter);
            }

            float tribStartY = joinNode.Position.Y + 6.5f;
            for (int i = 0; i <= tribSteps; i++)
            {
                float t = i / (float)tribSteps;
                Vector2 prev = rawTrib[Math.Max(0, i - 1)];
                Vector2 next = rawTrib[Math.Min(tribSteps, i + 1)];
                Vector2 tangent = (next - prev).Normalized();

                float waterY = Mathf.Lerp(tribStartY, joinNode.Position.Y, FastNoise.SmoothStep(0.0f, 1.0f, t));
                float halfWidth = 4.5f + FastNoise.Fbm2D(t * 6.0f, 19.2f, Seed + 751, 2) * 3.0f;

                TributaryNodes.Add(new RiverNode(new Vector3(rawTrib[i].X, waterY, rawTrib[i].Y), halfWidth, tangent, 0.0f));
            }
        }

        private void GenerateHeightfield()
        {
            // Pass 1: 2x2 km Island + North/NW Alpine Massif + Open Plains + 2 Offshore Rocky Islets
            for (int gz = 0; gz < GridSize; gz++)
            {
                float worldZ = gz * CellSize;
                float nz = worldZ / RegionSizeMeters;

                for (int gx = 0; gx < GridSize; gx++)
                {
                    float worldX = gx * CellSize;
                    float nx = worldX / RegionSizeMeters;

                    float warpX = (FastNoise.Fbm2D(worldX * 0.0012f, worldZ * 0.0012f, Seed + 11, 4) - 0.5f) * 310.0f;
                    float warpZ = (FastNoise.Fbm2D(worldX * 0.0012f + 43.1f, worldZ * 0.0012f - 27.8f, Seed + 29, 4) - 0.5f) * 310.0f;
                    float wx = worldX + warpX;
                    float wz = worldZ + warpZ;

                    // Main island radial mask (submerges smoothly before all 4 edges)
                    float dx = (wx - RegionSizeMeters * 0.49f) / (RegionSizeMeters * 0.41f);
                    float dz = (wz - RegionSizeMeters * 0.47f) / (RegionSizeMeters * 0.41f);
                    float radialDist = MathF.Sqrt(dx * dx + dz * dz);

                    // Southern bay indentation where the main river meets the sea
                    float bayDx = (wx - 1080.0f) / 360.0f;
                    float bayDz = (wz - 1720.0f) / 280.0f;
                    float bayDist = MathF.Sqrt(bayDx * bayDx + bayDz * bayDz);
                    float bayCarve = 1.0f - FastNoise.SmoothStep(0.32f, 1.02f, bayDist);

                    float coastNoise = (FastNoise.Fbm2D(worldX * 0.0024f, worldZ * 0.0024f, Seed + 71, 4) - 0.5f) * 0.32f;
                    float mainIsland = (1.0f - FastNoise.SmoothStep(0.62f, 1.03f, radialDist + coastNoise)) * (1.0f - bayCarve * 0.88f);

                    // Two offshore rocky satellite islets (SE & SW) for visual depth
                    float i1Dx = (wx - 1660.0f) / 145.0f;
                    float i1Dz = (wz - 1600.0f) / 135.0f;
                    float islet1 = 1.0f - FastNoise.SmoothStep(0.45f, 1.05f, MathF.Sqrt(i1Dx * i1Dx + i1Dz * i1Dz) + coastNoise * 0.6f);

                    float i2Dx = (wx - 430.0f) / 115.0f;
                    float i2Dz = (wz - 1570.0f) / 110.0f;
                    float islet2 = 1.0f - FastNoise.SmoothStep(0.45f, 1.05f, MathF.Sqrt(i2Dx * i2Dx + i2Dz * i2Dz) + coastNoise * 0.6f);

                    float landMask = MathF.Max(mainIsland, MathF.Max(islet1 * 0.85f, islet2 * 0.80f));

                    // Sharp Ridged Multifractal grouped in North/NW (~30% of island), leaving 60%+ open plains/valleys
                    float ridged = MathF.Pow(FastNoise.RidgedFbm2D(wx * 0.0018f, wz * 0.0018f, Seed + 307, 6), 1.18f);
                    float nwMassif = FastNoise.SmoothStep(0.52f, 0.18f, nz)
                                   * (0.55f + 0.45f * FastNoise.SmoothStep(0.85f, 0.22f, nx));
                    float neFoothills = FastNoise.SmoothStep(0.58f, 0.25f, nz)
                                      * FastNoise.SmoothStep(0.55f, 0.82f, nx);

                    float plainsFbm = FastNoise.Fbm2D(wx * 0.0016f, wz * 0.0016f, Seed + 101, 5);
                    float micro = (FastNoise.Fbm2D(worldX * 0.012f, worldZ * 0.012f, Seed + 173, 3) - 0.5f) * 2.4f;

                    float rawElevation = 4.5f
                        + plainsFbm * 17.5f
                        + nwMassif * ridged * 112.0f
                        + neFoothills * ridged * 38.0f
                        + (islet1 + islet2) * ridged * 24.0f
                        + micro;

                    // Subtle rock strata terracing on mountain slopes
                    float terraceMask = FastNoise.SmoothStep(24.0f, 52.0f, rawElevation);
                    float strataStep = 10.5f;
                    float terraced = MathF.Floor(rawElevation / strataStep) * strataStep
                                   + FastNoise.SmoothStep(0.15f, 0.85f, (rawElevation % strataStep) / strataStep) * strataStep;
                    rawElevation = rawElevation * (1.0f - terraceMask * 0.22f) + terraced * (terraceMask * 0.22f);

                    float seaBed = -12.0f + plainsFbm * 3.5f;
                    _heightGrid[gz * GridSize + gx] = seaBed * (1.0f - landMask) + rawElevation * landMask;
                }
            }

            // Pass 2: 70,000-Droplet Particle Hydraulic Erosion (carves gullies & sharp ridges)
            ApplyHydraulicErosion(70000);

            // Pass 3: Carve Highland Source Lake, Main River & Tributary gently (2.5m-4m below WaterY)
            CarveHydrologyAndEcology();
        }

        private void CarveHydrologyAndEcology()
        {
            // Spatial acceleration: for each cell, check distance to source lake + nearby river segments
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

                    // 1. Source Lake basin at mountain foot
                    float lakeDx = worldX - SourceLakeCenter.X;
                    float lakeDz = worldZ - SourceLakeCenter.Z;
                    float lakeDist = MathF.Sqrt(lakeDx * lakeDx + lakeDz * lakeDz);
                    float lakeJitter = (FastNoise.Fbm2D(worldX * 0.015f, worldZ * 0.015f, Seed + 821, 3) - 0.5f) * 22.0f;
                    float lakeEffDist = lakeDist + lakeJitter;

                    if (lakeEffDist < SourceLakeRadius * 2.8f)
                    {
                        float lakeValley = 1.0f - FastNoise.SmoothStep(SourceLakeRadius, SourceLakeRadius * 2.8f, lakeEffDist);
                        float lakeBed = 1.0f - FastNoise.SmoothStep(SourceLakeRadius * 0.65f, SourceLakeRadius * 1.15f, lakeEffDist);
                        bestValleyT = MathF.Max(bestValleyT, lakeValley);
                        if (lakeBed > 0.001f)
                        {
                            float floorH = SourceLakeCenter.Y + 1.5f;
                            h = h * (1.0f - lakeValley * 0.6f) + floorH * (lakeValley * 0.6f);
                            h = h * (1.0f - lakeBed) + MathF.Min(h, SourceLakeCenter.Y - 3.6f) * lakeBed;
                            bestRiverMask = MathF.Max(bestRiverMask, lakeBed);
                            targetWaterY = SourceLakeCenter.Y;
                        }
                    }

                    // 2. Main River spline closest segment
                    var (mDist, mNode, mCross) = FindClosestRiverNode(MainRiverNodes, worldX, worldZ);
                    if (mDist < mNode.HalfWidth * 5.0f)
                    {
                        float bankJitter = (FastNoise.Fbm2D(worldX * 0.022f, worldZ * 0.022f, Seed + 709, 3) - 0.5f) * 8.0f;
                        float effDist = MathF.Abs(mDist + bankJitter);
                        bool isOuterBank = (mCross * mNode.Curvature) > 0.0f;
                        float bankMult = isOuterBank ? 1.12f : 1.68f;

                        float valleyT = 1.0f - FastNoise.SmoothStep(mNode.HalfWidth * 1.1f, mNode.HalfWidth * 4.5f, effDist);
                        bestValleyT = MathF.Max(bestValleyT, valleyT);

                        // Gentle valley floor around river + 3.2m channel carve below WaterY
                        float valleyFloor = mNode.Position.Y + 1.8f;
                        h = h * (1.0f - valleyT * 0.62f) + MathF.Min(h, valleyFloor + 8.0f) * (valleyT * 0.62f);

                        float channelT = 1.0f - FastNoise.SmoothStep(mNode.HalfWidth * 0.45f, mNode.HalfWidth * bankMult, effDist);
                        if (channelT > 0.001f)
                        {
                            float bedY = mNode.Position.Y - 3.2f;
                            h = h * (1.0f - channelT) + MathF.Min(h, bedY) * channelT;
                            targetWaterY = mNode.Position.Y;
                        }

                        float sandT = 1.0f - FastNoise.SmoothStep(mNode.HalfWidth * 0.65f, mNode.HalfWidth * (isOuterBank ? 1.25f : 2.0f), effDist);
                        bestRiverMask = MathF.Max(bestRiverMask, MathF.Max(channelT, sandT * 0.80f));
                    }

                    // 3. Tributary stream closest segment
                    var (tDist, tNode, _) = FindClosestRiverNode(TributaryNodes, worldX, worldZ);
                    if (tDist < tNode.HalfWidth * 4.2f)
                    {
                        float tValley = 1.0f - FastNoise.SmoothStep(tNode.HalfWidth, tNode.HalfWidth * 3.8f, tDist);
                        bestValleyT = MathF.Max(bestValleyT, tValley * 0.85f);
                        float tChannel = 1.0f - FastNoise.SmoothStep(tNode.HalfWidth * 0.4f, tNode.HalfWidth * 1.4f, tDist);
                        if (tChannel > 0.001f)
                        {
                            float bedY = tNode.Position.Y - 2.2f;
                            h = h * (1.0f - tChannel) + MathF.Min(h, bedY) * tChannel;
                        }
                        bestRiverMask = MathF.Max(bestRiverMask, tChannel * 0.85f);
                    }

                    _heightGrid[idx] = h;
                    _riverMaskGrid[idx] = bestRiverMask;
                    _riverWaterYGrid[idx] = targetWaterY;

                    float coastal = FastNoise.SmoothStep(3.5f, -1.5f, h);
                    float moisture = Math.Clamp(0.36f + bestValleyT * 0.50f + coastal * 0.22f - (h / 105.0f) * 0.35f, 0.0f, 1.0f);
                    _moistureGrid[idx] = moisture;

                    // Forest grove density: clustered organic woodlands + riparian corridors, leaving open meadows
                    float groveMacro = FastNoise.Fbm2D(worldX * 0.0038f + 19.4f, worldZ * 0.0038f - 8.7f, Seed + 907, 4);
                    float groveMask = FastNoise.SmoothStep(0.45f, 0.68f, groveMacro);
                    float riparianCorridor = bestValleyT * 0.82f;
                    float altSuitability = FastNoise.SmoothStep(1.2f, 4.0f, h) * (1.0f - FastNoise.SmoothStep(44.0f, 58.0f, h));
                    _forestGrid[idx] = Math.Clamp(MathF.Max(groveMask, riparianCorridor) * altSuitability, 0.0f, 1.0f);
                }
            }
        }

        private static (float Dist, RiverNode Node, float SignedCross) FindClosestRiverNode(
            List<RiverNode> nodes, float wx, float wz)
        {
            float bestDistSq = float.MaxValue;
            int bestIdx = 0;

            // Coarse stride then local refine for fast O(N/6) lookup
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
            const int maxLifetime = 32;
            const float inertia = 0.08f;
            const float sedimentCapacityFactor = 4.0f;
            const float minSedimentCapacity = 0.01f;
            const float erodeSpeed = 0.32f;
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
                    if (nodeX < 1 || nodeX >= GridSize - 2 || nodeZ < 1 || nodeZ >= GridSize - 2)
                        break;

                    float cellOffsetX = posX - nodeX;
                    float cellOffsetZ = posZ - nodeZ;

                    int idx00 = nodeZ * GridSize + nodeX;
                    float h00 = _heightGrid[idx00];
                    float h10 = _heightGrid[idx00 + 1];
                    float h01 = _heightGrid[idx00 + GridSize];
                    float h11 = _heightGrid[idx00 + GridSize + 1];

                    float oldH = (h00 * (1 - cellOffsetX) + h10 * cellOffsetX) * (1 - cellOffsetZ)
                               + (h01 * (1 - cellOffsetX) + h11 * cellOffsetX) * cellOffsetZ;
                    if (oldH < SeaLevel - 0.5f)
                        break;

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
                    if (posX < 1 || posX >= GridSize - 2 || posZ < 1 || posZ >= GridSize - 2)
                        break;

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
                                if (dist < brushRadius)
                                    totalWeight += brushRadius - dist;
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
                                        float deltaSediment = MathF.Min(_heightGrid[tz * GridSize + tx] - (SeaLevel - 12.0f), amountToErode * w);
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
                return new TerrainSample(-10.0f, 0.0f, SeaLevel, 1.0f, 1.0f, 0.0f);
            }

            float gx = worldX / CellSize;
            float gz = worldZ / CellSize;

            float height = SampleBilinear(_heightGrid, gx, gz);
            float riverMask = SampleBilinear(_riverMaskGrid, gx, gz);
            float riverWaterY = SampleBilinear(_riverWaterYGrid, gx, gz);
            float moisture = SampleBilinear(_moistureGrid, gx, gz);
            float forest = SampleBilinear(_forestGrid, gx, gz);
            float coastalMask = FastNoise.SmoothStep(3.5f, -1.5f, height);

            return new TerrainSample(height, riverMask, riverWaterY, coastalMask, moisture, forest);
        }

        public float SampleHeight(float worldX, float worldZ) => SamplePoint(worldX, worldZ).Height;

        public Vector3 SampleNormal(float worldX, float worldZ, float eps = 1.5f)
        {
            float hL = SampleHeight(worldX - eps, worldZ);
            float hR = SampleHeight(worldX + eps, worldZ);
            float hD = SampleHeight(worldX, worldZ - eps);
            float hU = SampleHeight(worldX, worldZ + eps);
            return new Vector3(hL - hR, 2.0f * eps, hD - hU).Normalized();
        }
    }
}
