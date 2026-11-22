using System;
using Godot;

namespace PrimevalWorld.WorldGen
{
    public readonly struct ClimateSample
    {
        public readonly float TemperatureC;   // -15C .. +38C
        public readonly float Precipitation;  // 0 .. 1
        public readonly float Moisture;       // 0 .. 1 (soil moisture from rain + flow + rivers)
        public readonly float WindSpeed;      // m/s (2 .. 24)
        public readonly Vector2 WindDir;      // Normalized XZ wind direction

        public ClimateSample(float tempC, float precip, float moisture, float windSpeed, Vector2 windDir)
        {
            TemperatureC = tempC;
            Precipitation = precip;
            Moisture = moisture;
            WindSpeed = windSpeed;
            WindDir = windDir;
        }
    }

    /// <summary>
    /// Tier 2: Atmosphere, Prevailing Wind, Temperature Lapse Rate & Orographic Rain Shadow Simulator.
    /// Computes physical climate fields directly from Tier 1 Terrain & FlowAccumulation.
    /// </summary>
    public sealed class ClimateSimulator
    {
        public const int Width = 481;   // 8m cell spacing across 3840m
        public const int Depth = 257;   // 8m cell spacing across 2048m
        public const float CellSize = 8.0f;

        private readonly float[] _tempGrid = new float[Width * Depth];
        private readonly float[] _precipGrid = new float[Width * Depth];
        private readonly float[] _moistureGrid = new float[Width * Depth];
        private readonly float[] _windSpeedGrid = new float[Width * Depth];
        private readonly Vector2[] _windDirGrid = new Vector2[Width * Depth];

        public Vector2 GlobalPrevailingWind { get; private set; } = new Vector2(0.82f, 0.57f).Normalized();

        public void Simulate(WorldGenerator terrain)
        {
            // Seed slightly shifts prevailing ocean breeze (NW->SE or WNW->ESE)
            float windAngle = 0.52f + FastNoise.GradientNoise2D(terrain.Seed * 0.11f, 3.7f, terrain.Seed + 41) * 0.25f;
            GlobalPrevailingWind = new Vector2(MathF.Cos(windAngle), MathF.Sin(windAngle)).Normalized();

            // 1. Compute Wind Field & Temperature (°C)
            for (int gz = 0; gz < Depth; gz++)
            {
                float worldZ = gz * CellSize;
                float latNorm = worldZ / WorldGenerator.RegionDepthMeters; // 0 = Cold North, 1 = Warm South
                for (int gx = 0; gx < Width; gx++)
                {
                    float worldX = gx * CellSize;
                    float nx = worldX / WorldGenerator.RegionWidthMeters;
                    int idx = gz * Width + gx;

                    float h = terrain.SampleHeight(worldX, worldZ);
                    Vector3 n = terrain.SampleNormal(worldX, worldZ, 6.0f);

                    // Deflect wind slightly around terrain slopes & accelerate on ridges/open seas
                    Vector2 slopeGrad = new Vector2(-n.X, -n.Z);
                    Vector2 localDir = (GlobalPrevailingWind + slopeGrad * 0.45f).Normalized();
                    _windDirGrid[idx] = localDir;

                    float exposure = MathF.Max(0.0f, h) / 90.0f;
                    float isOceanBoost = h <= 0.5f ? 0.35f : 0.0f;
                    float shelter = MathF.Max(0.0f, -slopeGrad.Dot(GlobalPrevailingWind)) * 0.45f;
                    float windSpd = Math.Clamp(7.5f + exposure * 14.0f + isOceanBoost * 5.0f - shelter * 5.0f, 2.2f, 24.0f);
                    _windSpeedGrid[idx] = windSpd;

                    // Temperature (°C): Latitude (+4C North .. +31C South) - Lapse Rate (-0.36C/m) + Sun Aspect (+2.8C)
                    float baseLatTemp = 4.0f + latNorm * 27.0f;
                    float lapseDrop = MathF.Max(0.0f, h) * 0.36f;
                    float aspectHeat = Math.Clamp(n.Z, -1.0f, 1.0f) * 2.8f;
                    float swBelt = (1.0f - FastNoise.SmoothStep(0.38f, 0.56f, nx)) * FastNoise.SmoothStep(0.42f, 0.58f, latNorm) * 7.5f;
                    float nwCold = (1.0f - FastNoise.SmoothStep(0.38f, 0.56f, nx)) * (1.0f - FastNoise.SmoothStep(0.38f, 0.55f, latNorm)) * 7.5f;

                    _tempGrid[idx] = Math.Clamp(baseLatTemp - lapseDrop + aspectHeat + swBelt - nwCold, -15.0f, 38.0f);
                }
            }

            // 2. Orographic Precipitation & Rain Shadow Sweep along Prevailing Wind
            // March air parcels from upwind ocean edges across the landscape
            int steps = 140;
            float stepMeters = 18.0f;
            for (int gz = 0; gz < Depth; gz++)
            {
                float worldZ = gz * CellSize;
                for (int gx = 0; gx < Width; gx++)
                {
                    float worldX = gx * CellSize;
                    int idx = gz * Width + gx;

                    // Trace upwind to accumulate moisture pickup & rain-shadow depletion
                    float airMoisture = 0.85f;
                    float prevH = 0.0f;
                    float localPrecip = 0.35f;

                    for (int s = steps; s >= 0; s--)
                    {
                        float sx = worldX - GlobalPrevailingWind.X * s * stepMeters;
                        float sz = worldZ - GlobalPrevailingWind.Y * s * stepMeters;
                        if (sx < 0.0f || sx > WorldGenerator.RegionWidthMeters || sz < 0.0f || sz > WorldGenerator.RegionDepthMeters)
                        {
                            airMoisture = MathF.Min(1.0f, airMoisture + 0.08f);
                            prevH = 0.0f;
                            continue;
                        }

                        float sh = terrain.SampleHeight(sx, sz);
                        if (sh <= 0.2f)
                        {
                            // Over ocean/bays: evaporate moisture into air parcel
                            airMoisture = MathF.Min(1.0f, airMoisture + 0.09f);
                            prevH = 0.0f;
                        }
                        else
                        {
                            float lift = MathF.Max(0.0f, sh - prevH);
                            float orographicRain = airMoisture * (0.015f + lift * 0.022f);
                            airMoisture = MathF.Max(0.10f, airMoisture - orographicRain * 0.85f);
                            if (s == 0)
                            {
                                localPrecip = Math.Clamp(0.22f + airMoisture * 0.65f + lift * 0.04f, 0.08f, 1.0f);
                            }
                            prevH = sh;
                        }
                    }

                    // Regional tropical bay moisture boost in East/SE + leeward rain shadow in SW
                    float nx = worldX / WorldGenerator.RegionWidthMeters;
                    float nz = worldZ / WorldGenerator.RegionDepthMeters;
                    float swShadow = (1.0f - FastNoise.SmoothStep(0.38f, 0.50f, nx)) * FastNoise.SmoothStep(0.45f, 0.56f, nz);
                    localPrecip *= (1.0f - swShadow * 0.62f);

                    _precipGrid[idx] = Math.Clamp(localPrecip, 0.05f, 1.0f);
                }
            }

            // 3. Soil Moisture = Precipitation + FlowAccumulation + River/Lake Groundwater Diffusion
            for (int gz = 0; gz < Depth; gz++)
            {
                float worldZ = gz * CellSize;
                for (int gx = 0; gx < Width; gx++)
                {
                    float worldX = gx * CellSize;
                    int idx = gz * Width + gx;

                    float h = terrain.SampleHeight(worldX, worldZ);
                    float precip = _precipGrid[idx];
                    float flow = terrain.SampleFlowAccum(worldX, worldZ);
                    float riverMask = terrain.SampleRiverMask(worldX, worldZ);

                    float baseMoist = precip * 0.62f + flow * 0.34f + riverMask * 0.55f;
                    if (h <= 0.2f) baseMoist = 1.0f;
                    _moistureGrid[idx] = Math.Clamp(baseMoist, 0.04f, 1.0f);
                }
            }
        }

        private float SampleBilinear(float[] grid, float worldX, float worldZ)
        {
            float cx = Math.Clamp(worldX / CellSize, 0.0f, Width - 1.001f);
            float cz = Math.Clamp(worldZ / CellSize, 0.0f, Depth - 1.001f);
            int x0 = (int)cx, z0 = (int)cz;
            float tx = cx - x0, tz = cz - z0;
            int idx = z0 * Width + x0;
            return (grid[idx] * (1 - tx) + grid[idx + 1] * tx) * (1 - tz)
                 + (grid[idx + Width] * (1 - tx) + grid[idx + Width + 1] * tx) * tz;
        }

        public ClimateSample SampleClimate(float worldX, float worldZ)
        {
            float t = SampleBilinear(_tempGrid, worldX, worldZ);
            float p = SampleBilinear(_precipGrid, worldX, worldZ);
            float m = SampleBilinear(_moistureGrid, worldX, worldZ);
            float w = SampleBilinear(_windSpeedGrid, worldX, worldZ);
            int gx = Math.Clamp((int)(worldX / CellSize), 0, Width - 1);
            int gz = Math.Clamp((int)(worldZ / CellSize), 0, Depth - 1);
            return new ClimateSample(t, p, m, w, _windDirGrid[gz * Width + gx]);
        }

        public ImageTexture BuildTemperatureMapTexture()
        {
            byte[] rgb = new byte[Width * Depth * 3];
            for (int i = 0; i < Width * Depth; i++)
            {
                float t = Math.Clamp((_tempGrid[i] + 15.0f) / 53.0f, 0.0f, 1.0f);
                Color c = t < 0.35f
                    ? new Color(0.15f, 0.35f, 0.85f).Lerp(new Color(0.25f, 0.78f, 0.75f), t / 0.35f)
                    : (t < 0.68f
                        ? new Color(0.25f, 0.78f, 0.75f).Lerp(new Color(0.90f, 0.78f, 0.20f), (t - 0.35f) / 0.33f)
                        : new Color(0.90f, 0.78f, 0.20f).Lerp(new Color(0.88f, 0.22f, 0.12f), (t - 0.68f) / 0.32f));
                int o = i * 3;
                rgb[o + 0] = (byte)(c.R * 255);
                rgb[o + 1] = (byte)(c.G * 255);
                rgb[o + 2] = (byte)(c.B * 255);
            }
            return ImageTexture.CreateFromImage(Image.CreateFromData(Width, Depth, false, Image.Format.Rgb8, rgb));
        }

        public ImageTexture BuildMoistureMapTexture()
        {
            byte[] rgb = new byte[Width * Depth * 3];
            for (int i = 0; i < Width * Depth; i++)
            {
                float m = _moistureGrid[i];
                Color c = m < 0.45f
                    ? new Color(0.76f, 0.42f, 0.20f).Lerp(new Color(0.68f, 0.66f, 0.30f), m / 0.45f)
                    : new Color(0.68f, 0.66f, 0.30f).Lerp(new Color(0.08f, 0.48f, 0.76f), (m - 0.45f) / 0.55f);
                int o = i * 3;
                rgb[o + 0] = (byte)(c.R * 255);
                rgb[o + 1] = (byte)(c.G * 255);
                rgb[o + 2] = (byte)(c.B * 255);
            }
            return ImageTexture.CreateFromImage(Image.CreateFromData(Width, Depth, false, Image.Format.Rgb8, rgb));
        }

        public ImageTexture BuildWindMapTexture()
        {
            byte[] rgb = new byte[Width * Depth * 3];
            for (int i = 0; i < Width * Depth; i++)
            {
                float w = Math.Clamp((_windSpeedGrid[i] - 2.0f) / 20.0f, 0.0f, 1.0f);
                Color c = new Color(0.08f, 0.14f, 0.28f).Lerp(new Color(0.95f, 0.85f, 0.25f), w);
                int o = i * 3;
                rgb[o + 0] = (byte)(c.R * 255);
                rgb[o + 1] = (byte)(c.G * 255);
                rgb[o + 2] = (byte)(c.B * 255);
            }
            return ImageTexture.CreateFromImage(Image.CreateFromData(Width, Depth, false, Image.Format.Rgb8, rgb));
        }
    }
}
