using System;

namespace PrimevalWorld.WorldGen
{
    public enum BiomeType
    {
        DeepOcean = 0,
        CoastalReef = 1,
        PrimevalForest = 2,
        AutumnSteppe = 3,
        TerracottaBasin = 4,
        GlacialAlpine = 5,
    }

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
    /// Pure mathematical Seed-based generation (fBm + Ridged + Domain Warping + River Spline)
    /// architected cleanly for Stage 3 expansion into multi-continent SDF + Climate worlds.
    /// </summary>
    public sealed class WorldGenerator
    {
        public int Seed { get; private set; }

        public const float RegionSizeMeters = 1024.0f;
        public const float ChunkSizeMeters = 128.0f;
        public const int ChunksPerAxis = 8; // 8 * 128m = 1024m
        public const int ChunkVerticesPerSide = 65; // 2.0m vertex spacing
        public const float SeaLevel = 0.0f;

        public WorldGenerator(int seed = 2026)
        {
            Seed = seed;
        }

        public void SetSeed(int newSeed)
        {
            Seed = newSeed;
        }

        /// <summary>
        /// Parametric meandering river spine flowing from NE highlands (z = 0..1024)
        /// toward the SW coastal bay. Returns centerline X and river surface Y.
        /// </summary>
        public (float CenterX, float WaterY, float HalfWidth) SampleRiverSpine(float worldZ)
        {
            float t = Math.Clamp(worldZ / RegionSizeMeters, 0.0f, 1.0f);

            // Diagonal flow from NE (x ~ 760) to SW bay (x ~ 290)
            float baseCenter = 760.0f - 470.0f * t;

            // Multi-frequency domain-warped meandering
            float warp = (FastNoise.Fbm2D(worldZ * 0.0022f, 17.3f, Seed + 501, 3) - 0.5f) * 190.0f;
            float bend = MathF.Sin(t * MathF.PI * 2.4f - 0.5f) * 78.0f;
            float centerX = baseCenter + bend + warp;

            // River widens as it approaches the coastal delta
            float halfWidth = 10.5f + 16.0f * FastNoise.SmoothStep(0.35f, 0.92f, t);

            // Gentle downhill water surface from +11.5m in the upper valley down to sea level 0.0m
            float slopeDrop = 1.0f - FastNoise.SmoothStep(0.05f, 0.78f, t);
            float waterY = MathF.Max(SeaLevel, slopeDrop * 11.5f);

            return (centerX, waterY, halfWidth);
        }

        /// <summary>
        /// Samples continuous height & ecological masks at any world (x, z) coordinate in meters.
        /// </summary>
        public TerrainSample SamplePoint(float worldX, float worldZ)
        {
            // Normalized coordinates [0..1] across the 1x1 km vertical slice
            float nx = worldX / RegionSizeMeters;
            float nz = worldZ / RegionSizeMeters;

            // Domain warping for organic ridges & shorelines
            float warpX = (FastNoise.Fbm2D(worldX * 0.0018f, worldZ * 0.0018f, Seed + 11, 3) - 0.5f) * 140.0f;
            float warpZ = (FastNoise.Fbm2D(worldX * 0.0018f + 31.7f, worldZ * 0.0018f - 19.4f, Seed + 29, 3) - 0.5f) * 140.0f;
            float wx = worldX + warpX;
            float wz = worldZ + warpZ;

            // 1. Macro landform gradient:
            //    - High alpine massif in North / Northwest
            //    - Rolling hills in East
            //    - Gentle coastal bay & shallow turquoise reef in South / Southwest
            float dxBay = (wx - 240.0f) / 360.0f;
            float dzBay = (wz - 940.0f) / 290.0f;
            float bayDist = MathF.Sqrt(dxBay * dxBay + dzBay * dzBay);
            float bayCarve = 1.0f - FastNoise.SmoothStep(0.45f, 1.15f, bayDist);

            // Southern ocean shelf drop-off
            float southSea = FastNoise.SmoothStep(0.76f, 0.98f, wz / RegionSizeMeters);
            float oceanMask = MathF.Max(bayCarve, southSea * 0.85f);

            // Base rolling plains & valley elevation
            float rollingHills = FastNoise.Fbm2D(wx * 0.0024f, wz * 0.0024f, Seed + 101, 5);
            float detail = (FastNoise.Fbm2D(worldX * 0.014f, worldZ * 0.014f, Seed + 173, 3) - 0.5f) * 3.2f;

            // Northern / Northwestern alpine mountain ridge
            float mountainZone = FastNoise.SmoothStep(0.48f, 0.08f, wz / RegionSizeMeters)
                               * (0.55f + 0.45f * FastNoise.SmoothStep(0.95f, 0.15f, wx / RegionSizeMeters));
            float ridged = FastNoise.RidgedFbm2D(wx * 0.0028f, wz * 0.0028f, Seed + 307, 5);
            float alpineHeight = mountainZone * MathF.Pow(ridged, 1.35f) * 78.0f;

            // Secondary eastern ridge framing the valley
            float eastRidgeZone = FastNoise.SmoothStep(0.60f, 0.94f, wx / RegionSizeMeters)
                                * FastNoise.SmoothStep(0.85f, 0.25f, wz / RegionSizeMeters);
            float eastRidge = eastRidgeZone * MathF.Pow(FastNoise.RidgedFbm2D(wx * 0.0034f + 8.2f, wz * 0.0034f, Seed + 409, 4), 1.4f) * 42.0f;

            float baseLandHeight = 4.0f + rollingHills * 22.0f + alpineHeight + eastRidge + detail;

            // Smoothly submerge coastal shelf below sea level
            float seaFloorHeight = -9.5f + rollingHills * 3.0f;
            float rawHeight = baseLandHeight * (1.0f - oceanMask) + seaFloorHeight * oceanMask;

            // 2. Carve the meandering river valley & channel
            var (riverX, riverWaterY, riverHalfW) = SampleRiverSpine(worldZ);
            float distToRiver = MathF.Abs(worldX - riverX);

            // Wide floodplain flattening so riverbanks sit naturally in a valley
            float valleyT = 1.0f - FastNoise.SmoothStep(riverHalfW * 1.1f, riverHalfW * 5.2f, distToRiver);
            float targetValleyFloor = riverWaterY + 1.6f;
            float valleyFlattened = rawHeight * (1.0f - valleyT * 0.72f) + targetValleyFloor * (valleyT * 0.72f);

            // Deep river channel cut below riverWaterY
            float channelT = 1.0f - FastNoise.SmoothStep(riverHalfW * 0.45f, riverHalfW * 1.35f, distToRiver);
            // Fade river carving once it merges into the open coastal bay
            float riverActive = 1.0f - FastNoise.SmoothStep(0.74f, 0.88f, nz);
            channelT *= riverActive;

            float riverBedY = riverWaterY - 3.6f;
            float finalHeight = valleyFlattened * (1.0f - channelT) + MathF.Min(valleyFlattened, riverBedY) * channelT;

            float coastalMask = FastNoise.SmoothStep(3.0f, -1.5f, finalHeight);
            float moisture = Math.Clamp(0.42f + valleyT * 0.48f + coastalMask * 0.25f - (finalHeight / 85.0f) * 0.3f, 0.0f, 1.0f);

            return new TerrainSample(finalHeight, channelT, riverWaterY, coastalMask, moisture);
        }

        public float SampleHeight(float worldX, float worldZ) => SamplePoint(worldX, worldZ).Height;
    }
}
