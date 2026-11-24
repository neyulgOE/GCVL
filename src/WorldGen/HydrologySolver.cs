using System;
using System.Threading.Tasks;
using Godot;
using PrimevalWorld.Core;

namespace PrimevalWorld.WorldGen
{
    /// <summary>
    /// Stage 1C + Overhaul: Dynamic Hydrology, Floodplain & Wetland Solver (1025x577):
    /// - Smooth organic river/lake carving (domain-warped banks, smoothed InlandWaterY)
    /// - D8 Flow Accumulation & Manning Hydraulic Velocity / Discharge
    /// - Lateral Groundwater & LocalWaterTableMap relaxation across valleys
    /// - Physical FloodplainMask (gentle alluvial valleys 0.8..9.5m above water table)
    /// - Physical WetlandMask (deltas, lakeshores, flat depressions, NW peat bogs) with
    ///   shallow 0.18..0.65m murky wetland pools alternating with mossy dry hummocks.
    /// </summary>
    public sealed class HydrologySolver
    {
        private const int W = WorldPhysicsConfig.VertW;
        private const int H = WorldPhysicsConfig.VertH;
        private const float Cell = WorldPhysicsConfig.CellSize;

        public float[] FlowAccumMap { get; } = new float[W * H];
        public float[] WaterDepthMap { get; } = new float[W * H];
        public float[] WaterVelocityMap { get; } = new float[W * H];
        public float[] GroundwaterMap { get; } = new float[W * H];
        public float[] LocalWaterTableMap { get; } = new float[W * H];
        public float[] InlandWaterY { get; } = new float[W * H];
        public bool[] HasInlandWater { get; } = new bool[W * H];
        public float[] RiverMaskMap { get; } = new float[W * H];
        public float[] FloodplainMask { get; } = new float[W * H];
        public float[] WetlandMask { get; } = new float[W * H];
        public float[] WetlandWaterFactor { get; } = new float[W * H];

        public void Solve(TectonicContinentGen tectonic, ErosionPhysics erosion)
        {
            int count = W * H;
            Array.Clear(FloodplainMask, 0, count);
            Array.Clear(WetlandMask, 0, count);
            Array.Clear(WetlandWaterFactor, 0, count);

            // 1. Carve blueprint inland lakes & rivers gently with organic domain-warped banks
            Parallel.For(0, H, gz =>
            {
                float wz = gz * Cell;
                for (int gx = 0; gx < W; gx++)
                {
                    int idx = gz * W + gx;
                    float wx = gx * Cell;
                    float bankWarp = (FastNoise.Fbm2D(wx * 0.022f, wz * 0.022f, 313, 3) - 0.5f) * 0.14f;
                    float rawW = Math.Clamp(tectonic.RawWaterMask[idx] + (tectonic.RawWaterMask[idx] > 0.05f ? bankWarp : 0.0f), 0.0f, 1.0f);
                    RiverMaskMap[idx] = rawW;

                    bool isInland = rawW > 0.36f && !tectonic.IsOceanConnected[idx];
                    HasInlandWater[idx] = isInland;

                    if (isInland)
                    {
                        float bankH = SampleLocalBankHeight(erosion.HeightMap, gx, gz, tectonic.RawWaterMask);
                        float waterSurfaceY = MathF.Max(0.35f, bankH - 1.15f);
                        InlandWaterY[idx] = waterSurfaceY;
                        float depth = 2.2f + rawW * 2.4f;
                        WaterDepthMap[idx] = depth;
                        erosion.HeightMap[idx] = waterSurfaceY - depth;
                    }
                    else
                    {
                        InlandWaterY[idx] = WorldPhysicsConfig.SeaLevel;
                        WaterDepthMap[idx] = erosion.HeightMap[idx] < 0.0f ? -erosion.HeightMap[idx] : 0.0f;
                    }
                }
            });

            // Smooth InlandWaterY across connected river/lake cells so surface never stair-steps
            SmoothInlandWaterSurface(3);
            erosion.ComputeSurfaceDerivatives();

            // 2. D8 Flow Accumulation sorted from highest to lowest
            var order = new int[count];
            for (int i = 0; i < count; i++)
            {
                order[i] = i;
                FlowAccumMap[i] = erosion.HeightMap[i] > 0.2f ? 1.0f : 0.0f;
            }
            Array.Sort(order, (a, b) => erosion.HeightMap[b].CompareTo(erosion.HeightMap[a]));

            int[] dx = { -1, 0, 1, -1, 1, -1, 0, 1 };
            int[] dz = { -1, -1, -1, 0, 0, 1, 1, 1 };
            float[] dist = { 1.414f, 1.0f, 1.414f, 1.0f, 1.0f, 1.414f, 1.0f, 1.414f };

            for (int k = 0; k < count; k++)
            {
                int idx = order[k];
                float h = erosion.HeightMap[idx];
                if (h <= 0.1f) continue;

                int x = idx % W;
                int z = idx / W;
                if (x == 0 || x == W - 1 || z == 0 || z == H - 1) continue;

                float bestSlope = 0.0f;
                int bestTarget = -1;
                for (int d = 0; d < 8; d++)
                {
                    int nIdx = (z + dz[d]) * W + (x + dx[d]);
                    float s = (h - erosion.HeightMap[nIdx]) / dist[d];
                    if (s > bestSlope)
                    {
                        bestSlope = s;
                        bestTarget = nIdx;
                    }
                }
                if (bestTarget >= 0)
                {
                    FlowAccumMap[bestTarget] += FlowAccumMap[idx];
                }
            }

            // 3. Hydraulic Velocity v & Discharge Q = A * v
            Parallel.For(0, H, gz =>
            {
                for (int gx = 0; gx < W; gx++)
                {
                    int idx = gz * W + gx;
                    float logFlow = Math.Clamp(MathF.Log2(1.0f + FlowAccumMap[idx]) / 10.0f, 0.0f, 1.0f);
                    FlowAccumMap[idx] = logFlow;

                    float slopeSin = MathF.Sin(Mathf.DegToRad(erosion.SlopeDegMap[idx]));
                    float v = Math.Clamp(0.45f + MathF.Sqrt(MathF.Max(0.0f, slopeSin)) * 3.8f + logFlow * 1.4f, 0.25f, 5.5f);
                    WaterVelocityMap[idx] = v;

                    if (HasInlandWater[idx])
                    {
                        WaterDepthMap[idx] = Math.Clamp(WaterDepthMap[idx] * (1.2f - slopeSin * 0.6f), 1.4f, 6.5f);
                    }
                }
            });

            // 4. Lateral Groundwater & LocalWaterTableMap diffusion across river valleys and deltas
            for (int i = 0; i < count; i++)
            {
                bool isSurfaceWater = HasInlandWater[i] || RiverMaskMap[i] > 0.35f || erosion.HeightMap[i] <= 0.15f;
                GroundwaterMap[i] = isSurfaceWater ? 1.0f : FlowAccumMap[i] * 0.50f;
                LocalWaterTableMap[i] = HasInlandWater[i]
                    ? InlandWaterY[i]
                    : (erosion.HeightMap[i] <= 0.15f ? 0.0f : erosion.HeightMap[i] - 16.0f);
            }

            float[] tmpGw = new float[count];
            float[] tmpWt = new float[count];
            for (int pass = 0; pass < 18; pass++)
            {
                Parallel.For(1, H - 1, z =>
                {
                    for (int x = 1; x < W - 1; x++)
                    {
                        int idx = z * W + x;
                        float avgGw = (GroundwaterMap[idx - 1] + GroundwaterMap[idx + 1] + GroundwaterMap[idx - W] + GroundwaterMap[idx + W]) * 0.25f;
                        float hDiff = MathF.Max(0.0f, erosion.HeightMap[idx] - 8.0f) * 0.009f;
                        tmpGw[idx] = MathF.Max(GroundwaterMap[idx], MathF.Max(0.0f, avgGw * 0.93f - hDiff));

                        float maxNeighborWt = MathF.Max(
                            MathF.Max(LocalWaterTableMap[idx - 1], LocalWaterTableMap[idx + 1]),
                            MathF.Max(LocalWaterTableMap[idx - W], LocalWaterTableMap[idx + W])
                        ) - 0.12f;
                        tmpWt[idx] = MathF.Min(erosion.HeightMap[idx] + 0.5f, MathF.Max(LocalWaterTableMap[idx], maxNeighborWt));
                    }
                });
                Array.Copy(tmpGw, GroundwaterMap, count);
                Array.Copy(tmpWt, LocalWaterTableMap, count);
            }

            // 5. Compute Physical FloodplainMask & WetlandMask + Carve Shallow Wetland Pools / Hummocks
            Parallel.For(0, H, gz =>
            {
                float wz = gz * Cell;
                for (int gx = 0; gx < W; gx++)
                {
                    int idx = gz * W + gx;
                    float h = erosion.HeightMap[idx];
                    if (h <= 0.18f || HasInlandWater[idx]) continue;

                    float wx = gx * Cell;
                    float slopeDeg = erosion.SlopeDegMap[idx];
                    float flow = FlowAccumMap[idx];
                    float gw = GroundwaterMap[idx];
                    float coastDist = tectonic.CoastDistMeters[idx];
                    float swArid = tectonic.SwDesertWeight[idx];
                    float nwCold = tectonic.NwGlacialWeight[idx];
                    float hAboveWater = MathF.Max(-0.5f, h - LocalWaterTableMap[idx]);

                    float warpA = FastNoise.Fbm2D(wx * 0.0022f, wz * 0.0022f, 907, 3);
                    float warpB = FastNoise.Fbm2D(wx * 0.0075f, wz * 0.0075f, 941, 2);

                    // WetlandMask: deltas, flat river/lake depressions (-0.5..+2.2m above water table), & NW cold peat bogs
                    float flatWet = 1.0f - FastNoise.SmoothStep(1.6f, 3.6f, slopeDeg);
                    float lowTable = 1.0f - FastNoise.SmoothStep(0.85f, 2.6f, hAboveWater + (warpB - 0.5f) * 0.7f);
                    float deltaFactor = FastNoise.SmoothStep(14.0f, 1.2f, h)
                                      * FastNoise.SmoothStep(25.0f, 160.0f, coastDist)
                                      * FastNoise.SmoothStep(0.18f, 0.52f, gw + flow * 0.6f);
                    float basinMarsh = lowTable * FastNoise.SmoothStep(0.32f, 0.70f, gw + flow * 0.45f) * FastNoise.SmoothStep(42.0f, 8.0f, h);
                    float nwPeatBog = nwCold * flatWet * FastNoise.SmoothStep(38.0f, 6.0f, h) * FastNoise.SmoothStep(0.38f, 0.66f, warpA) * 0.90f;

                    float wetland = Math.Clamp(flatWet * MathF.Max(MathF.Max(deltaFactor * 1.15f, basinMarsh), nwPeatBog) * (1.0f - swArid * 0.88f), 0.0f, 1.0f);
                    WetlandMask[idx] = wetland;

                    // FloodplainMask: wide gentle alluvial valleys & point bars (slope < 4.8°, 0.6..9.5m above water table / lowland plains)
                    float gentleSlope = 1.0f - FastNoise.SmoothStep(2.6f, 5.2f, slopeDeg);
                    float valleyBand = FastNoise.SmoothStep(-0.1f, 0.75f, hAboveWater) * (1.0f - FastNoise.SmoothStep(6.5f, 13.5f, hAboveWater));
                    float lowlandPlain = FastNoise.SmoothStep(1.8f, 5.0f, h) * (1.0f - FastNoise.SmoothStep(24.0f, 40.0f, h))
                                       * FastNoise.SmoothStep(65.0f, 210.0f, coastDist)
                                       * FastNoise.SmoothStep(0.36f, 0.64f, 1.0f - warpA + gw * 0.32f);

                    float floodplain = gentleSlope
                                     * MathF.Max(valleyBand * FastNoise.SmoothStep(0.16f, 0.52f, gw + flow * 0.5f), lowlandPlain * 0.92f)
                                     * (1.0f - swArid * 0.92f)
                                     * (1.0f - nwCold * 0.55f)
                                     * (1.0f - FastNoise.SmoothStep(0.45f, 0.78f, wetland));
                    FloodplainMask[idx] = Math.Clamp(floodplain, 0.0f, 1.0f);
                }
            });

            // 6. Depress shallow murky wetland pools (0.18..0.62m) alternating with dry mossy hummocks where WetlandMask > 0.50
            Parallel.For(1, H - 1, gz =>
            {
                float wz = gz * Cell;
                for (int gx = 1; gx < W - 1; gx++)
                {
                    int idx = gz * W + gx;
                    float wm = WetlandMask[idx];
                    if (wm <= 0.50f || HasInlandWater[idx] || tectonic.IsOceanConnected[idx]) continue;

                    float wx = gx * Cell;
                    float poolNoise = FastNoise.Fbm2D(wx * 0.028f, wz * 0.028f, 571, 3);
                    float strength = FastNoise.SmoothStep(0.50f, 0.85f, wm);

                    if (poolNoise < 0.45f)
                    {
                        float poolDepth = (0.18f + (0.45f - poolNoise) * 0.95f) * (0.65f + 0.35f * strength);
                        float waterY = MathF.Max(0.30f, erosion.HeightMap[idx] - 0.05f);
                        InlandWaterY[idx] = waterY;
                        erosion.HeightMap[idx] = waterY - poolDepth;
                        WaterDepthMap[idx] = poolDepth;
                        WaterVelocityMap[idx] = 0.12f;
                        HasInlandWater[idx] = true;
                        WetlandWaterFactor[idx] = Math.Clamp(0.55f + 0.45f * strength, 0.0f, 1.0f);
                    }
                    else
                    {
                        // Slightly raised mossy hummock island between wetland channels
                        float mound = (poolNoise - 0.45f) * 0.65f * strength;
                        erosion.HeightMap[idx] += mound;
                    }
                }
            });

            // Tag river/delta water passing through wetlands with WetlandWaterFactor for murky olive-brown tint
            for (int i = 0; i < count; i++)
            {
                if (HasInlandWater[i] && WetlandWaterFactor[i] < 0.05f)
                {
                    int x = Math.Clamp(i % W, 1, W - 2);
                    int z = Math.Clamp(i / W, 1, H - 2);
                    float nearWet = MathF.Max(
                        MathF.Max(WetlandMask[z * W + x - 1], WetlandMask[z * W + x + 1]),
                        MathF.Max(WetlandMask[(z - 1) * W + x], WetlandMask[(z + 1) * W + x])
                    );
                    WetlandWaterFactor[i] = FastNoise.SmoothStep(0.32f, 0.72f, nearWet) * 0.75f;
                }
            }

            SmoothInlandWaterSurface(2);
            erosion.ComputeSurfaceDerivatives();
        }

        private void SmoothInlandWaterSurface(int passes)
        {
            float[] tmp = new float[W * H];
            for (int p = 0; p < passes; p++)
            {
                Array.Copy(InlandWaterY, tmp, tmp.Length);
                Parallel.For(1, H - 1, z =>
                {
                    for (int x = 1; x < W - 1; x++)
                    {
                        int idx = z * W + x;
                        if (!HasInlandWater[idx]) continue;
                        float sum = InlandWaterY[idx] * 2.0f;
                        float wt = 2.0f;
                        int[] nbs = { idx - 1, idx + 1, idx - W, idx + W };
                        for (int k = 0; k < 4; k++)
                        {
                            if (HasInlandWater[nbs[k]])
                            {
                                sum += InlandWaterY[nbs[k]];
                                wt += 1.0f;
                            }
                        }
                        tmp[idx] = sum / wt;
                    }
                });
                Array.Copy(tmp, InlandWaterY, tmp.Length);
            }
        }

        private static float SampleLocalBankHeight(float[] heightMap, int gx, int gz, float[] rawWaterMask)
        {
            float sum = 0.0f;
            int cnt = 0;
            for (int dz = -6; dz <= 6; dz += 2)
            {
                int tz = gz + dz;
                if (tz < 0 || tz >= H) continue;
                for (int dx = -6; dx <= 6; dx += 2)
                {
                    int tx = gx + dx;
                    if (tx < 0 || tx >= W) continue;
                    int tidx = tz * W + tx;
                    if (rawWaterMask[tidx] < 0.25f && heightMap[tidx] > 1.0f)
                    {
                        sum += heightMap[tidx];
                        cnt++;
                    }
                }
            }
            return cnt > 0 ? MathF.Min(sum / cnt, 55.0f) : 8.0f;
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

        public float SampleFlowAccum(float worldX, float worldZ) => SampleBilinear(FlowAccumMap, worldX, worldZ);
        public float SampleGroundwater(float worldX, float worldZ) => SampleBilinear(GroundwaterMap, worldX, worldZ);
        public float SampleRiverMask(float worldX, float worldZ) => SampleBilinear(RiverMaskMap, worldX, worldZ);
        public float SampleFloodplain(float worldX, float worldZ) => SampleBilinear(FloodplainMask, worldX, worldZ);
        public float SampleWetland(float worldX, float worldZ) => SampleBilinear(WetlandMask, worldX, worldZ);
    }
}
