using System;
using Godot;

namespace PrimevalWorld.WorldGen
{
    public enum SoilType : byte
    {
        AlluvialLoam = 0,       // Đất phù sa / mùn đen ẩm
        ForestBrownSoil = 1,    // Đất rừng nâu
        SteppeLoess = 2,        // Đất thảo nguyên giàu gió
        AridRedSand = 3,        // Đất đỏ phong hóa / cát khô
        CoastalSand = 4,        // Cát biển nhiễm mặn
        PermafrostAndRock = 5,  // Băng vĩnh cửu / đá gốc trơ
    }

    public readonly struct SoilSample
    {
        public readonly float SoilDepth;       // 0 .. 1
        public readonly float CoastalSalinity; // 0 .. 1
        public readonly SoilType DominantSoil;
        public readonly float WAlluvial;
        public readonly float WForestBrown;
        public readonly float WSteppeLoess;
        public readonly float WAridRed;
        public readonly float WCoastalSand;
        public readonly float WPermafrostRock;

        public SoilSample(
            float depth, float salinity, SoilType dom,
            float wAlluvial, float wForestBrown, float wSteppe,
            float wArid, float wCoastal, float wPermafrost)
        {
            SoilDepth = depth;
            CoastalSalinity = salinity;
            DominantSoil = dom;
            WAlluvial = wAlluvial;
            WForestBrown = wForestBrown;
            WSteppeLoess = wSteppe;
            WAridRed = wArid;
            WCoastalSand = wCoastal;
            WPermafrostRock = wPermafrost;
        }
    }

    /// <summary>
    /// Tier 3: Pedology & Surface Soil Simulator.
    /// Derives SoilDepth, CoastalSalinity, and 6 physical SoilType weights directly from
    /// Terrain (Slope, Height, Flow) + Climate (Temperature, Moisture, Wind).
    /// </summary>
    public sealed class SoilSimulator
    {
        public const int Width = ClimateSimulator.Width;
        public const int Depth = ClimateSimulator.Depth;
        public const float CellSize = ClimateSimulator.CellSize;

        private readonly float[] _soilDepth = new float[Width * Depth];
        private readonly float[] _salinity = new float[Width * Depth];
        private readonly float[] _wAlluvial = new float[Width * Depth];
        private readonly float[] _wForestBrown = new float[Width * Depth];
        private readonly float[] _wSteppeLoess = new float[Width * Depth];
        private readonly float[] _wAridRed = new float[Width * Depth];
        private readonly float[] _wCoastalSand = new float[Width * Depth];
        private readonly float[] _wPermafrostRock = new float[Width * Depth];
        private readonly SoilType[] _dominantSoil = new SoilType[Width * Depth];

        public void Simulate(WorldGenerator terrain, ClimateSimulator climate)
        {
            for (int gz = 0; gz < Depth; gz++)
            {
                float worldZ = gz * CellSize;
                for (int gx = 0; gx < Width; gx++)
                {
                    float worldX = gx * CellSize;
                    int idx = gz * Width + gx;

                    float h = terrain.SampleHeight(worldX, worldZ);
                    Vector3 n = terrain.SampleNormal(worldX, worldZ, 5.0f);
                    float slope = 1.0f - Math.Clamp(n.Y, 0.0f, 1.0f);
                    float flow = terrain.SampleFlowAccum(worldX, worldZ);
                    float riverMask = terrain.SampleRiverMask(worldX, worldZ);
                    ClimateSample cs = climate.SampleClimate(worldX, worldZ);

                    // SoilDepth: eroded away on steep cliffs (>28 deg) & strong wind peaks; thick in moist valleys
                    float slopeLoss = FastNoise.SmoothStep(0.06f, 0.22f, slope);
                    float windLoss = FastNoise.SmoothStep(14.0f, 23.0f, cs.WindSpeed) * 0.35f;
                    float depth = Math.Clamp((0.45f + flow * 0.45f + cs.Moisture * 0.30f) * (1.0f - slopeLoss) - windLoss, 0.0f, 1.0f);
                    if (h <= 0.1f) depth = 0.2f;
                    _soilDepth[idx] = depth;

                    // CoastalSalinity: high near low ocean shores & salt-spray zones
                    float sal = FastNoise.SmoothStep(4.5f, 0.2f, h) * (1.0f - riverMask * 0.80f);
                    _salinity[idx] = Math.Clamp(sal, 0.0f, 1.0f);

                    // Compute physical affinity weights for all 6 soil types
                    float wCoastal = sal * 1.4f;
                    float wPerma = MathF.Max(
                        FastNoise.SmoothStep(2.0f, -4.0f, cs.TemperatureC),
                        FastNoise.SmoothStep(0.28f, 0.06f, depth)
                    );
                    float wAlluvial = FastNoise.SmoothStep(0.45f, 0.85f, cs.Moisture)
                                    * (0.4f + flow * 0.6f + riverMask * 0.8f)
                                    * (1.0f - wCoastal * 0.7f)
                                    * (1.0f - wPerma * 0.8f);
                    float wArid = FastNoise.SmoothStep(18.0f, 29.0f, cs.TemperatureC)
                                * (1.0f - FastNoise.SmoothStep(0.22f, 0.56f, cs.Moisture))
                                * (1.0f - wCoastal * 0.6f);
                    float wSteppe = FastNoise.SmoothStep(5.0f, 18.0f, cs.TemperatureC)
                                  * (1.0f - FastNoise.SmoothStep(19.0f, 26.0f, cs.TemperatureC))
                                  * (1.0f - FastNoise.SmoothStep(0.42f, 0.72f, cs.Moisture))
                                  * (0.5f + FastNoise.SmoothStep(7.0f, 15.0f, cs.WindSpeed) * 0.5f)
                                  * (1.0f - wPerma * 0.7f);
                    float wForest = FastNoise.SmoothStep(6.0f, 24.0f, cs.TemperatureC)
                                  * FastNoise.SmoothStep(0.32f, 0.70f, cs.Moisture)
                                  * (1.0f - wPerma * 0.8f)
                                  * (1.0f - wCoastal * 0.7f)
                                  * (1.0f - wArid * 0.8f);

                    float sum = wAlluvial + wForest + wSteppe + wArid + wCoastal + wPerma + 1e-5f;
                    _wAlluvial[idx] = wAlluvial / sum;
                    _wForestBrown[idx] = wForest / sum;
                    _wSteppeLoess[idx] = wSteppe / sum;
                    _wAridRed[idx] = wArid / sum;
                    _wCoastalSand[idx] = wCoastal / sum;
                    _wPermafrostRock[idx] = wPerma / sum;

                    // Dominant classification
                    SoilType dom = SoilType.ForestBrownSoil;
                    float bestW = _wForestBrown[idx];
                    void Check(SoilType t, float w) { if (w > bestW) { bestW = w; dom = t; } }
                    Check(SoilType.AlluvialLoam, _wAlluvial[idx]);
                    Check(SoilType.SteppeLoess, _wSteppeLoess[idx]);
                    Check(SoilType.AridRedSand, _wAridRed[idx]);
                    Check(SoilType.CoastalSand, _wCoastalSand[idx]);
                    Check(SoilType.PermafrostAndRock, _wPermafrostRock[idx]);
                    _dominantSoil[idx] = dom;
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

        public SoilSample SampleSoil(float worldX, float worldZ)
        {
            int gx = Math.Clamp((int)(worldX / CellSize), 0, Width - 1);
            int gz = Math.Clamp((int)(worldZ / CellSize), 0, Depth - 1);
            return new SoilSample(
                SampleBilinear(_soilDepth, worldX, worldZ),
                SampleBilinear(_salinity, worldX, worldZ),
                _dominantSoil[gz * Width + gx],
                SampleBilinear(_wAlluvial, worldX, worldZ),
                SampleBilinear(_wForestBrown, worldX, worldZ),
                SampleBilinear(_wSteppeLoess, worldX, worldZ),
                SampleBilinear(_wAridRed, worldX, worldZ),
                SampleBilinear(_wCoastalSand, worldX, worldZ),
                SampleBilinear(_wPermafrostRock, worldX, worldZ)
            );
        }

        /// <summary>
        /// Exports RGBA8 Soil Splat Texture for terrain_triplanar.gdshader:
        /// R = Alluvial/ForestHumus, G = SteppeLoess (golden), B = AridRedSand (terracotta), A = Permafrost/Bedrock.
        /// </summary>
        public ImageTexture BuildSoilSplatTexture()
        {
            byte[] data = new byte[Width * Depth * 4];
            for (int i = 0; i < Width * Depth; i++)
            {
                int o = i * 4;
                data[o + 0] = (byte)(Math.Clamp(_wAlluvial[i] + _wForestBrown[i] * 0.6f, 0.0f, 1.0f) * 255.0f);
                data[o + 1] = (byte)(Math.Clamp(_wSteppeLoess[i], 0.0f, 1.0f) * 255.0f);
                data[o + 2] = (byte)(Math.Clamp(_wAridRed[i], 0.0f, 1.0f) * 255.0f);
                data[o + 3] = (byte)(Math.Clamp(_wPermafrostRock[i], 0.0f, 1.0f) * 255.0f);
            }
            return ImageTexture.CreateFromImage(Image.CreateFromData(Width, Depth, false, Image.Format.Rgba8, data));
        }

        public ImageTexture BuildSoilMapTexture()
        {
            byte[] rgb = new byte[Width * Depth * 3];
            for (int i = 0; i < Width * Depth; i++)
            {
                Color c = _dominantSoil[i] switch
                {
                    SoilType.AlluvialLoam => new Color(0.14f, 0.28f, 0.11f),
                    SoilType.ForestBrownSoil => new Color(0.28f, 0.36f, 0.16f),
                    SoilType.SteppeLoess => new Color(0.74f, 0.56f, 0.18f),
                    SoilType.AridRedSand => new Color(0.78f, 0.36f, 0.18f),
                    SoilType.CoastalSand => new Color(0.84f, 0.78f, 0.54f),
                    _ => new Color(0.54f, 0.58f, 0.64f),
                };
                int o = i * 3;
                rgb[o + 0] = (byte)(c.R * 255);
                rgb[o + 1] = (byte)(c.G * 255);
                rgb[o + 2] = (byte)(c.B * 255);
            }
            return ImageTexture.CreateFromImage(Image.CreateFromData(Width, Depth, false, Image.Format.Rgb8, rgb));
        }
    }
}
