using System;

namespace PrimevalWorld.WorldGen
{
    public readonly struct TerrainSample
    {
        public readonly float Height;
        public readonly float RiverMask;
        public readonly float RiverWaterHeight;
        public readonly float CoastalMask;
        public readonly float Moisture;

        public TerrainSample(float height, float riverMask, float riverWaterHeight, float coastalMask, float moisture)
        {
            Height = height;
            RiverMask = riverMask;
            RiverWaterHeight = riverWaterHeight;
            CoastalMask = coastalMask;
            Moisture = moisture;
        }
    }

    /// <summary>
    /// Stage 1 Vertical Slice World Generator (1024m x 1024m).
    /// Generates a 513x513 heightfield from Seed using:
    /// - Domain-warped Island Falloff (natural coastlines, bays, zero square cutoffs)
    /// - Sharp Ridged Multifractal + Rock Strata Terracing
    /// - 50,000-droplet Particle Hydraulic Erosion (carves gullies & sharp ridges)
    /// - Variable-width, asymmetric meandering river carving
    /// </summary>
    public sealed class WorldGenerator
    {
        public int Seed { get; private set; }

        public const float RegionSizeMeters = 1024.0f;
        public const float ChunkSizeMeters = 128.0f;
        public const int ChunksPerAxis = 8; // 8 * 128m = 1024m
        public const int ChunkVerticesPerSide = 65; // 2.0m vertex spacing
        public const float SeaLevel = 0.0f;

        private const int GridSize = 513; // 2.0m per cell across 1024m
        private const float CellSize = RegionSizeMeters / (GridSize - 1); // 2.0m

        private readonly float[] _heightGrid = new float[GridSize * GridSize];
        private readonly float[] _riverMaskGrid = new float[GridSize * GridSize];
        private readonly float[] _riverWaterYGrid = new float[GridSize * GridSize];
        private readonly float[] _moistureGrid = new float[GridSize * GridSize];

        public WorldGenerator(int seed = 2026)
        {
            SetSeed(seed);
        }

        public void SetSeed(int newSeed)
        {
            Seed = newSeed;
            GenerateHeightfield();
        }

        /// <summary>
        /// Parametric meandering river spine with variable width (narrows in rocky gorges,
        /// widens at bends/delta) and asymmetric bank profile.
        /// </summary>
        public (float CenterX, float WaterY, float HalfWidth, float Curvature) SampleRiverSpine(float worldZ)
        {
            float t = Math.Clamp(worldZ / RegionSizeMeters, 0.0f, 1.0f);

            // Flows from NE highland valley (~x=720) toward SW coastal bay (~x=310)
            float baseCenter = 720.0f - 410.0f * t;

            float warp = (FastNoise.Fbm2D(worldZ * 0.0024f, 17.3f, Seed + 501, 3) - 0.5f) * 210.0f;
            float bend = MathF.Sin(t * MathF.PI * 2.8f - 0.4f) * 86.0f;
            float centerX = baseCenter + bend + warp;

            // Approximate local bend curvature for asymmetric cutbank vs point bar
            float dBend = MathF.Cos(t * MathF.PI * 2.8f - 0.4f);

            // Organic width variation: narrow rapids vs wider pools & delta mouth
            float widthNoise = FastNoise.Fbm2D(worldZ * 0.007f, 91.2f, Seed + 613, 3);
            float halfWidth = 7.5f + widthNoise * 11.0f + 18.0f * FastNoise.SmoothStep(0.55f, 0.88f, t);

            // Downhill water profile from +12m in upper gorge down to 0.0m sea level
            float slopeDrop = 1.0f - FastNoise.SmoothStep(0.08f, 0.72f, t);
            float waterY = MathF.Max(SeaLevel, slopeDrop * 12.0f);

            return (centerX, waterY, halfWidth, dBend);
        }

        private void GenerateHeightfield()
        {
            // Pass 1: Macro Island Falloff + Sharp Ridged Mountains + Terracing
            for (int gz = 0; gz < GridSize; gz++)
            {
                float worldZ = gz * CellSize;
                float nz = worldZ / RegionSizeMeters;

                for (int gx = 0; gx < GridSize; gx++)
                {
                    float worldX = gx * CellSize;
                    float nx = worldX / RegionSizeMeters;

                    // Domain warping for irregular bays, headlands & coves
                    float warpX = (FastNoise.Fbm2D(worldX * 0.0022f, worldZ * 0.0022f, Seed + 11, 4) - 0.5f) * 190.0f;
                    float warpZ = (FastNoise.Fbm2D(worldX * 0.0022f + 37.1f, worldZ * 0.0022f - 23.8f, Seed + 29, 4) - 0.5f) * 190.0f;
                    float wx = worldX + warpX;
                    float wz = worldZ + warpZ;

                    // Radial + domain-warped Island Mask: ensures ALL 4 borders submerge smoothly below sea level
                    float dx = (wx - RegionSizeMeters * 0.5f) / (RegionSizeMeters * 0.44f);
                    float dz = (wz - RegionSizeMeters * 0.47f) / (RegionSizeMeters * 0.44f);
                    float radialDist = MathF.Sqrt(dx * dx + dz * dz);

                    // Extra SW bay indentation where the river meets the ocean
                    float bayDx = (wx - 280.0f) / 260.0f;
                    float bayDz = (wz - 820.0f) / 220.0f;
                    float bayDist = MathF.Sqrt(bayDx * bayDx + bayDz * bayDz);
                    float bayCarve = 1.0f - FastNoise.SmoothStep(0.35f, 1.05f, bayDist);

                    float coastNoise = (FastNoise.Fbm2D(worldX * 0.0045f, worldZ * 0.0045f, Seed + 71, 4) - 0.5f) * 0.34f;
                    float islandMask = (1.0f - FastNoise.SmoothStep(0.62f, 1.04f, radialDist + coastNoise)) * (1.0f - bayCarve * 0.85f);

                    // Sharp Ridged Multifractal peaks (North/NW massif + East ridge)
                    float ridgedPrimary = FastNoise.RidgedFbm2D(wx * 0.0029f, wz * 0.0029f, Seed + 307, 6);
                    float ridgedSharp = MathF.Pow(ridgedPrimary, 1.15f);

                    float northMassif = FastNoise.SmoothStep(0.58f, 0.14f, nz)
                                      * (0.60f + 0.40f * FastNoise.SmoothStep(0.92f, 0.22f, nx));
                    float eastMassif = FastNoise.SmoothStep(0.45f, 0.82f, nx)
                                     * FastNoise.SmoothStep(0.80f, 0.22f, nz);

                    float hills = FastNoise.Fbm2D(wx * 0.0026f, wz * 0.0026f, Seed + 101, 5);
                    float micro = (FastNoise.Fbm2D(worldX * 0.018f, worldZ * 0.018f, Seed + 173, 3) - 0.5f) * 2.8f;

                    float rawElevation = 3.5f
                        + hills * 20.0f
                        + northMassif * ridgedSharp * 92.0f
                        + eastMassif * ridgedSharp * 44.0f
                        + micro;

                    // Subtle geological rock terracing/strata on mid-high elevations
                    float terraceMask = FastNoise.SmoothStep(18.0f, 45.0f, rawElevation);
                    float strataStep = 9.5f;
                    float terraced = MathF.Floor(rawElevation / strataStep) * strataStep
                                   + FastNoise.SmoothStep(0.15f, 0.85f, (rawElevation % strataStep) / strataStep) * strataStep;
                    rawElevation = rawElevation * (1.0f - terraceMask * 0.24f) + terraced * (terraceMask * 0.24f);

                    // Blend smoothly down into deep ocean seabed (-12m) outside island mask
                    float seaBed = -12.0f + hills * 3.5f;
                    float height = seaBed * (1.0f - islandMask) + rawElevation * islandMask;

                    _heightGrid[gz * GridSize + gx] = height;
                }
            }

            // Pass 2: 50,000-Droplet Particle Hydraulic Erosion (carves gullies & sharp arêtes)
            ApplyHydraulicErosion(50000);

            // Pass 3: Carve variable-width, asymmetric meandering river & compute ecological masks
            for (int gz = 0; gz < GridSize; gz++)
            {
                float worldZ = gz * CellSize;
                float nz = worldZ / RegionSizeMeters;
                var (riverX, riverWaterY, riverHalfW, curvature) = SampleRiverSpine(worldZ);

                for (int gx = 0; gx < GridSize; gx++)
                {
                    int idx = gz * GridSize + gx;
                    float worldX = gx * CellSize;
                    float h = _heightGrid[idx];

                    // Irregular bank edge perturbation so shores aren't parallel
                    float bankJitter = (FastNoise.Fbm2D(worldX * 0.025f, worldZ * 0.025f, Seed + 709, 3) - 0.5f) * 9.0f;
                    float signedOffset = worldX - riverX;
                    float distToRiver = MathF.Abs(signedOffset + bankJitter);

                    // Asymmetric cutbank (outer bend steeper) vs point bar (inner bend gentler)
                    bool isOuterBank = (signedOffset * curvature) > 0.0f;
                    float bankSlopeMult = isOuterBank ? 1.15f : 1.75f;

                    float valleyT = 1.0f - FastNoise.SmoothStep(riverHalfW * 1.1f, riverHalfW * 4.6f, distToRiver);
                    float riverActive = (1.0f - FastNoise.SmoothStep(0.72f, 0.86f, nz))
                                      * FastNoise.SmoothStep(0.06f, 0.14f, nz);

                    // Only carve river where land is near or above river level
                    float targetFloor = riverWaterY + 1.4f;
                    float valleyH = h * (1.0f - valleyT * 0.68f * riverActive) + targetFloor * (valleyT * 0.68f * riverActive);

                    float channelT = (1.0f - FastNoise.SmoothStep(riverHalfW * 0.42f, riverHalfW * bankSlopeMult, distToRiver)) * riverActive;
                    float riverBedY = riverWaterY - 3.4f;
                    float finalH = valleyH * (1.0f - channelT) + MathF.Min(valleyH, riverBedY) * channelT;

                    _heightGrid[idx] = finalH;

                    // Asymmetric gravel/sand mask (wider on gentle point bars, narrower on steep cutbanks)
                    float shoreNoise = FastNoise.Fbm2D(worldX * 0.032f, worldZ * 0.032f, Seed + 811, 3);
                    float bankSandT = (1.0f - FastNoise.SmoothStep(riverHalfW * 0.6f, riverHalfW * (isOuterBank ? 1.25f : 1.95f) + shoreNoise * 5.0f, distToRiver)) * riverActive;
                    _riverMaskGrid[idx] = MathF.Max(channelT, bankSandT * 0.82f);
                    _riverWaterYGrid[idx] = riverWaterY;

                    float coastal = FastNoise.SmoothStep(3.5f, -1.5f, finalH);
                    _moistureGrid[idx] = Math.Clamp(0.38f + valleyT * 0.48f + coastal * 0.22f - (finalH / 95.0f) * 0.35f, 0.0f, 1.0f);
                }
            }
        }

        private void ApplyHydraulicErosion(int numDroplets)
        {
            var rng = new Random(Seed + 991);
            const int maxLifetime = 30;
            const float inertia = 0.08f;
            const float sedimentCapacityFactor = 3.8f;
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

                    // Don't erode underwater seabed
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
            // Outside the 1x1 km island region, continue smoothly as deep ocean seabed
            if (worldX < 0.0f || worldX > RegionSizeMeters || worldZ < 0.0f || worldZ > RegionSizeMeters)
            {
                return new TerrainSample(-10.0f, 0.0f, SeaLevel, 1.0f, 1.0f);
            }

            float gx = worldX / CellSize;
            float gz = worldZ / CellSize;

            float height = SampleBilinear(_heightGrid, gx, gz);
            float riverMask = SampleBilinear(_riverMaskGrid, gx, gz);
            float riverWaterY = SampleBilinear(_riverWaterYGrid, gx, gz);
            float moisture = SampleBilinear(_moistureGrid, gx, gz);
            float coastalMask = FastNoise.SmoothStep(3.5f, -1.5f, height);

            return new TerrainSample(height, riverMask, riverWaterY, coastalMask, moisture);
        }

        public float SampleHeight(float worldX, float worldZ) => SamplePoint(worldX, worldZ).Height;
    }
}
