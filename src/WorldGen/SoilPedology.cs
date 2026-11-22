using System;
using System.Threading.Tasks;
using Godot;
using PrimevalWorld.Core;

namespace PrimevalWorld.WorldGen
{
    public enum SoilType : byte
    {
        AlluvialLoam = 0,
        ForestBrownSoil = 1,
        SteppeLoess = 2,
        AridRedSand = 3,
        CoastalSand = 4,
        PermafrostAndRock = 5,
    }

    public readonly struct SoilSample
    {
        public readonly float SoilDepth;
        public readonly float CoastalSalinity;
        public readonly SoilType DominantSoil;
        public readonly float WAlluvial;
        public readonly float WForestBrown;
        public readonly float WSteppeLoess;
        public readonly float WAridRed;
        public readonly float WCoastalSand;
        public readonly float WPermafrostRock;

        public SoilSample(
            float depth,
            float salinity,
            SoilType dom,
            float wAlluvial,
            float wForestBrown,
            float wSteppeLoess,
            float wAridRed,
            float wCoastalSand,
            float wPermafrostRock)
        {
            SoilDepth = depth;
            CoastalSalinity = salinity;
            DominantSoil = dom;
            WAlluvial = wAlluvial;
            WForestBrown = wForestBrown;
            WSteppeLoess = wSteppeLoess;
            WAridRed = wAridRed;
            WCoastalSand = wCoastalSand;
            WPermafrostRock = wPermafrostRock;
        }
    }

    /// <summary>
    /// Stage 2B: Pedology & 6-Soil Classification (1025x577) + GPU Data Texture Exporter.
    /// Computes SoilDepth, CoastalSalinity, SurfaceFriction & 6 normalized SoilWeights.
    /// </summary>
    public sealed class SoilPedology
    {
        private const int W = WorldPhysicsConfig.VertW;
        private const int H = WorldPhysicsConfig.VertH;
        private const float Cell = WorldPhysicsConfig.CellSize;

        public float[] SoilDepthMap { get; } = new float[W * H];
        public float[] CoastalSalinityMap { get; } = new float[W * H];
        public float[] WAlluvial { get; } = new float[W * H];
        public float[] WForestBrown { get; } = new float[W * H];
        public float[] WSteppeLoess { get; } = new float[W * H];
        public float[] WAridRed { get; } = new float[W * H];
        public float[] WCoastalSand { get; } = new float[W * H];
        public float[] WPermafrostRock { get; } = new float[W * H];
        public SoilType[] DominantSoilMap { get; } = new SoilType[W * H];

        public int[] LandSoilCounts { get; } = new int[6];
        public int TotalLandCells { get; private set; }

        public void Simulate(TectonicContinentGen tectonic, ErosionPhysics erosion, HydrologySolver hydrology, AtmosphereClimate climate)
        {
            Array.Clear(LandSoilCounts, 0, 6);
            TotalLandCells = 0;

            Parallel.For(0, H, gz =>
            {
                for (int gx = 0; gx < W; gx++)
                {
                    int idx = gz * W + gx;
                    float h = erosion.HeightMap[idx];
                    float slopeDeg = erosion.SlopeDegMap[idx];
                    float sed = erosion.SedimentMap[idx];
                    float flow = hydrology.FlowAccumMap[idx];
                    float riverMask = hydrology.RiverMaskMap[idx];
                    float temp = climate.TemperatureMap[idx];
                    float moist = climate.MoistureMap[idx];
                    float wind = climate.WindSpeedMap[idx];

                    float slopeLoss = FastNoise.SmoothStep(16.0f, 38.0f, slopeDeg);
                    float windLoss = FastNoise.SmoothStep(14.0f, 26.0f, wind) * 0.35f;
                    float depth = Math.Clamp((0.35f + MathF.Min(1.0f, sed / 8.0f) * 0.35f + flow * 0.35f + moist * 0.25f) * (1.0f - slopeLoss) - windLoss, 0.0f, 1.0f);
                    if (h <= 0.1f) depth = 0.2f;
                    SoilDepthMap[idx] = depth;

                    float sal = FastNoise.SmoothStep(8.0f, 0.2f, h)
                              * (1.0f - riverMask * 0.75f)
                              * FastNoise.SmoothStep(115.0f, 15.0f, tectonic.CoastDistMeters[idx]);
                    CoastalSalinityMap[idx] = Math.Clamp(sal, 0.0f, 1.0f);

                    // Coastal Sand on gentle beaches 0..10m within 140m of shoreline
                    float wCoastal = FastNoise.SmoothStep(10.5f, 0.2f, h)
                                   * FastNoise.SmoothStep(-1.5f, 0.05f, h)
                                   * FastNoise.SmoothStep(150.0f, 10.0f, tectonic.CoastDistMeters[idx])
                                   * (1.0f - riverMask * 0.70f)
                                   * (1.0f - FastNoise.SmoothStep(20.0f, 36.0f, slopeDeg))
                                   * 2.40f;

                    float wPerma = MathF.Max(
                        FastNoise.SmoothStep(1.2f, -4.5f, temp),
                        MathF.Max(FastNoise.SmoothStep(29.0f, 42.0f, slopeDeg), FastNoise.SmoothStep(0.17f, 0.04f, depth))
                    );

                    // Alluvial Loam along rivers, deltas, and very moist low floodplains
                    float wAlluvial = (FastNoise.SmoothStep(0.58f, 0.88f, moist) * FastNoise.SmoothStep(28.0f, 4.0f, h) * 0.45f
                                    + flow * 0.85f + riverMask * 1.15f)
                                    * (1.0f - wCoastal * 0.65f)
                                    * (1.0f - wPerma * 0.85f);

                    // Arid Red Sand focused in hot rain-shadow SW desert
                    float wArid = (FastNoise.SmoothStep(19.5f, 29.0f, temp) * (1.0f - FastNoise.SmoothStep(0.20f, 0.48f, moist))
                                + tectonic.SwDesertWeight[idx] * (1.0f - FastNoise.SmoothStep(0.38f, 0.68f, moist)) * 0.95f)
                                * (1.0f - wCoastal * 0.70f) * (1.0f - wPerma * 0.75f);

                    // Steppe Loess concentrated on cool, windy NE plateaus
                    float wSteppe = FastNoise.SmoothStep(4.0f, 11.5f, temp)
                                  * (1.0f - FastNoise.SmoothStep(14.5f, 20.5f, temp))
                                  * (1.0f - FastNoise.SmoothStep(0.26f, 0.48f, moist))
                                  * (0.20f + FastNoise.SmoothStep(8.0f, 16.0f, wind) * 0.40f + tectonic.NeAutumnWeight[idx] * 1.10f)
                                  * (1.0f - wPerma * 0.75f) * (1.0f - wArid * 0.80f) * (1.0f - wCoastal * 0.70f);

                    // Forest Brown Soil dominant across humid temperate/tropical East & SE plains
                    float wForest = FastNoise.SmoothStep(4.0f, 26.0f, temp)
                                  * FastNoise.SmoothStep(0.22f, 0.56f, moist)
                                  * (0.95f + tectonic.ForestFeature[idx] * 0.75f)
                                  * (1.0f - wPerma * 0.85f) * (1.0f - wCoastal * 0.75f) * (1.0f - wArid * 0.85f) * (1.0f - wSteppe * 0.55f);

                    float sum = wAlluvial + wForest + wSteppe + wArid + wCoastal + wPerma;
                    if (sum < 1e-5f)
                    {
                        wForest = 1.0f;
                        sum = 1.0f;
                    }
                    WAlluvial[idx] = wAlluvial / sum;
                    WForestBrown[idx] = wForest / sum;
                    WSteppeLoess[idx] = wSteppe / sum;
                    WAridRed[idx] = wArid / sum;
                    WCoastalSand[idx] = wCoastal / sum;
                    WPermafrostRock[idx] = wPerma / sum;

                    SoilType dom = SoilType.ForestBrownSoil;
                    float best = WForestBrown[idx];
                    void Pick(SoilType t, float w) { if (w > best) { best = w; dom = t; } }
                    Pick(SoilType.AlluvialLoam, WAlluvial[idx]);
                    Pick(SoilType.SteppeLoess, WSteppeLoess[idx]);
                    Pick(SoilType.AridRedSand, WAridRed[idx]);
                    Pick(SoilType.CoastalSand, WCoastalSand[idx]);
                    Pick(SoilType.PermafrostAndRock, WPermafrostRock[idx]);
                    DominantSoilMap[idx] = dom;
                }
            });

            for (int i = 0; i < W * H; i++)
            {
                if (erosion.HeightMap[i] > 0.2f)
                {
                    LandSoilCounts[(int)DominantSoilMap[i]]++;
                    TotalLandCells++;
                }
            }
        }

        public SoilSample SampleSoil(float worldX, float worldZ)
        {
            int gx = Math.Clamp((int)(worldX / Cell), 0, W - 1);
            int gz = Math.Clamp((int)(worldZ / Cell), 0, H - 1);
            int idx = gz * W + gx;
            return new SoilSample(
                SoilDepthMap[idx],
                CoastalSalinityMap[idx],
                DominantSoilMap[idx],
                WAlluvial[idx],
                WForestBrown[idx],
                WSteppeLoess[idx],
                WAridRed[idx],
                WCoastalSand[idx],
                WPermafrostRock[idx]);
        }

        public (ImageTexture SoilA, ImageTexture SoilB, ImageTexture ClimateTex) BuildGpuDataTextures(
            ErosionPhysics erosion, HydrologySolver hydrology, AtmosphereClimate climate)
        {
            int count = W * H;
            byte[] dataA = new byte[count * 4];
            byte[] dataB = new byte[count * 4];
            byte[] dataC = new byte[count * 4];

            Parallel.For(0, count, i =>
            {
                int o = i * 4;
                dataA[o + 0] = (byte)(Math.Clamp(WAlluvial[i], 0.0f, 1.0f) * 255.0f);
                dataA[o + 1] = (byte)(Math.Clamp(WForestBrown[i], 0.0f, 1.0f) * 255.0f);
                dataA[o + 2] = (byte)(Math.Clamp(WSteppeLoess[i], 0.0f, 1.0f) * 255.0f);
                dataA[o + 3] = (byte)(Math.Clamp(WAridRed[i], 0.0f, 1.0f) * 255.0f);

                dataB[o + 0] = (byte)(Math.Clamp(WCoastalSand[i], 0.0f, 1.0f) * 255.0f);
                dataB[o + 1] = (byte)(Math.Clamp(WPermafrostRock[i], 0.0f, 1.0f) * 255.0f);
                dataB[o + 2] = (byte)(Math.Clamp(SoilDepthMap[i], 0.0f, 1.0f) * 255.0f);
                dataB[o + 3] = (byte)(Math.Clamp(erosion.BedrockMask[i], 0.0f, 1.0f) * 255.0f);

                float tempNorm = Math.Clamp((climate.TemperatureMap[i] + 15.0f) / 53.0f, 0.0f, 1.0f);
                dataC[o + 0] = (byte)(tempNorm * 255.0f);
                dataC[o + 1] = (byte)(Math.Clamp(climate.MoistureMap[i], 0.0f, 1.0f) * 255.0f);
                dataC[o + 2] = (byte)(Math.Clamp(hydrology.RiverMaskMap[i], 0.0f, 1.0f) * 255.0f);
                dataC[o + 3] = (byte)(Math.Clamp(hydrology.FlowAccumMap[i], 0.0f, 1.0f) * 255.0f);
            });

            var texA = ImageTexture.CreateFromImage(Image.CreateFromData(W, H, false, Image.Format.Rgba8, dataA));
            var texB = ImageTexture.CreateFromImage(Image.CreateFromData(W, H, false, Image.Format.Rgba8, dataB));
            var texC = ImageTexture.CreateFromImage(Image.CreateFromData(W, H, false, Image.Format.Rgba8, dataC));
            return (texA, texB, texC);
        }
    }
}
