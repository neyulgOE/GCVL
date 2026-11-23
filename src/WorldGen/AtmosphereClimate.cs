using System;
using System.Threading.Tasks;
using Godot;
using PrimevalWorld.Core;

namespace PrimevalWorld.WorldGen
{
    public readonly struct ClimateSample
    {
        public readonly float TemperatureC;
        public readonly float Precipitation;
        public readonly float Moisture;
        public readonly float WindSpeed;
        public readonly Vector2 WindDir;

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
    /// Stage 2A: Atmosphere, Wind Field, Lapse-Rate Temperature & Orographic Rain Shadow (1025x577).
    /// </summary>
    public sealed class AtmosphereClimate
    {
        private const int W = WorldPhysicsConfig.VertW;
        private const int H = WorldPhysicsConfig.VertH;
        private const float Cell = WorldPhysicsConfig.CellSize;

        public float[] TemperatureMap { get; } = new float[W * H];
        public float[] PrecipitationMap { get; } = new float[W * H];
        public float[] MoistureMap { get; } = new float[W * H];
        public float[] WindSpeedMap { get; } = new float[W * H];
        public Vector2[] WindDirMap { get; } = new Vector2[W * H];

        public Vector2 GlobalPrevailingWind { get; private set; }

        public float MinTempC { get; private set; }
        public float MaxTempC { get; private set; }
        public float MeanPrecip { get; private set; }

        public void Simulate(TectonicContinentGen tectonic, ErosionPhysics erosion, HydrologySolver hydrology, int seed)
        {
            float windAngle = 0.54f + FastNoise.GradientNoise2D(seed * 0.11f, 3.7f, seed + 41) * 0.22f;
            GlobalPrevailingWind = new Vector2(MathF.Cos(windAngle), MathF.Sin(windAngle)).Normalized();

            // 1. Parallel Wind & Temperature (°C)
            Parallel.For(0, H, gz =>
            {
                float latNorm = gz / (float)(H - 1); // 0 = Cold North, 1 = Warm South
                for (int gx = 0; gx < W; gx++)
                {
                    int idx = gz * W + gx;
                    float h = erosion.HeightMap[idx];
                    Vector3 n = erosion.NormalMap[idx];

                    Vector2 slopeGrad = new Vector2(-n.X, -n.Z);
                    WindDirMap[idx] = (GlobalPrevailingWind + slopeGrad * 0.45f).Normalized();

                    float exposure = MathF.Max(0.0f, h) / 280.0f;
                    float oceanBoost = h <= 0.5f ? 0.35f : 0.0f;
                    float shelter = MathF.Max(0.0f, -slopeGrad.Dot(GlobalPrevailingWind)) * 0.50f;
                    WindSpeedMap[idx] = Math.Clamp(7.0f + exposure * 16.0f + oceanBoost * 5.0f - shelter * 6.0f, 2.0f, 28.0f);

                    // Maritime moderation (coastlines stay slightly milder than deep inland extremes)
                    float coastDist = MathF.Abs(tectonic.CoastDistMeters[idx]);
                    float maritime = 1.0f - FastNoise.SmoothStep(0.0f, 550.0f, coastDist);

                    float baseLatTemp = 4.0f + latNorm * 27.5f;
                    float lapseDrop = MathF.Max(0.0f, h) * WorldPhysicsConfig.LapseRate; // ~21.6°C drop at 450m!
                    float aspectWarm = erosion.AspectMap[idx] * 2.6f;
                    float swHeat = tectonic.SwDesertWeight[idx] * 6.8f;
                    float nwChill = tectonic.NwGlacialWeight[idx] * 4.5f;
                    float seaModeration = (18.0f - baseLatTemp) * maritime * 0.16f;

                    TemperatureMap[idx] = Math.Clamp(baseLatTemp - lapseDrop + aspectWarm + swHeat - nwChill + seaModeration, -15.0f, 38.0f);
                }
            });

            // 2. Parallel Orographic Rain Shadow & Moisture Sweep along Prevailing Wind
            const int marchSteps = 120;
            const float stepMeters = 48.0f;

            Parallel.For(0, H, gz =>
            {
                float worldZ = gz * Cell;
                for (int gx = 0; gx < W; gx++)
                {
                    float worldX = gx * Cell;
                    int idx = gz * W + gx;

                    float airMoisture = 0.85f;
                    float prevH = 0.0f;
                    float localPrecip = 0.35f;

                    for (int s = marchSteps; s >= 0; s--)
                    {
                        float sx = worldX - GlobalPrevailingWind.X * s * stepMeters;
                        float sz = worldZ - GlobalPrevailingWind.Y * s * stepMeters;
                        if (sx < 0.0f || sx >= WorldPhysicsConfig.WorldWidth || sz < 0.0f || sz >= WorldPhysicsConfig.WorldDepth)
                        {
                            airMoisture = MathF.Min(1.0f, airMoisture + 0.08f);
                            prevH = 0.0f;
                            continue;
                        }

                        int sgx = Math.Clamp((int)(sx / Cell), 0, W - 1);
                        int sgz = Math.Clamp((int)(sz / Cell), 0, H - 1);
                        float sh = erosion.HeightMap[sgz * W + sgx];

                        if (sh <= 0.2f)
                        {
                            airMoisture = MathF.Min(1.0f, airMoisture + 0.09f);
                            prevH = 0.0f;
                        }
                        else
                        {
                            float lift = MathF.Max(0.0f, sh - prevH);
                            float orographicRain = airMoisture * (0.012f + lift * 0.0085f);
                            airMoisture = Math.Max(0.10f, airMoisture - orographicRain * 0.85f);
                            if (s == 0)
                            {
                                localPrecip = Math.Clamp(0.20f + airMoisture * 0.65f + lift * 0.018f, 0.08f, 1.0f);
                            }
                            prevH = sh;
                        }
                    }

                    // Leeward rain shadow behind western/northern ridges into SW desert
                    float swShadow = tectonic.SwDesertWeight[idx];
                    localPrecip *= (1.0f - swShadow * 0.65f);
                    PrecipitationMap[idx] = Math.Clamp(localPrecip, 0.05f, 1.0f);

                    // Soil Moisture = Precip + Groundwater + Flow - Evaporation(Temp, Wind) + Micro-habitat variation (~350-500m)
                    float wx = gx * Cell;
                    float wz = gz * Cell;
                    float microClim = (FastNoise.Fbm2D(wx * 0.0028f, wz * 0.0028f, seed + 523, 3) - 0.5f) * 0.24f;
                    float aspectDry = MathF.Max(0.0f, erosion.AspectMap[idx]) * 0.07f; // South-facing slopes slightly drier/warmer
                    float evap = FastNoise.SmoothStep(16.0f, 36.0f, TemperatureMap[idx]) * 0.22f
                               + FastNoise.SmoothStep(10.0f, 26.0f, WindSpeedMap[idx]) * 0.10f + aspectDry;
                    float moist = PrecipitationMap[idx] * 0.54f
                                + hydrology.GroundwaterMap[idx] * 0.36f
                                + hydrology.FlowAccumMap[idx] * 0.28f
                                + microClim
                                - evap;
                    if (erosion.HeightMap[idx] <= 0.2f) moist = 1.0f;
                    MoistureMap[idx] = Math.Clamp(moist, 0.04f, 1.0f);
                }
            });

            // Compute summary stats
            float minT = 999f, maxT = -999f, sumP = 0f;
            for (int i = 0; i < W * H; i++)
            {
                if (TemperatureMap[i] < minT) minT = TemperatureMap[i];
                if (TemperatureMap[i] > maxT) maxT = TemperatureMap[i];
                sumP += PrecipitationMap[i];
            }
            MinTempC = minT;
            MaxTempC = maxT;
            MeanPrecip = sumP / (W * H);
        }

        private static float SampleBilinear(float[] grid, float worldX, float worldZ)
        {
            float cx = Math.Clamp(worldX / Cell, 0.0f, W - 1.001f);
            float cz = Math.Clamp(worldZ / Cell, 0.0f, H - 1.001f);
            int x0 = (int)cx, z0 = (int)cz;
            float tx = cx - x0, tz = cz - z0;
            int idx = z0 * W + x0;
            return (grid[idx] * (1 - tx) + grid[idx + 1] * tx) * (1 - tz)
                 + (grid[idx + W] * (1 - tx) + grid[idx + W + 1] * tx) * tz;
        }

        public ClimateSample SampleClimate(float worldX, float worldZ)
        {
            int gx = Math.Clamp((int)(worldX / Cell), 0, W - 1);
            int gz = Math.Clamp((int)(worldZ / Cell), 0, H - 1);
            return new ClimateSample(
                SampleBilinear(TemperatureMap, worldX, worldZ),
                SampleBilinear(PrecipitationMap, worldX, worldZ),
                SampleBilinear(MoistureMap, worldX, worldZ),
                SampleBilinear(WindSpeedMap, worldX, worldZ),
                WindDirMap[gz * W + gx]
            );
        }
    }
}
