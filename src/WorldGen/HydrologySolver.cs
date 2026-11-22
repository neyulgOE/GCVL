using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Godot;
using PrimevalWorld.Core;

namespace PrimevalWorld.WorldGen
{
    /// <summary>
    /// Stage 1C: Dynamic Hydrology Solver (1025x577):
    /// - Carves blueprint inland rivers & lakes gently with smooth bank-derived WaterSurfaceY
    /// - D8 Flow Accumulation from peaks to coasts
    /// - Hydraulic Discharge Q = A * v -> WaterDepthMap & WaterVelocityMap
    /// - Lateral Groundwater diffusion for riparian soil moisture
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
        public float[] InlandWaterY { get; } = new float[W * H];
        public bool[] HasInlandWater { get; } = new bool[W * H];
        public float[] RiverMaskMap { get; } = new float[W * H];

        public void Solve(TectonicContinentGen tectonic, ErosionPhysics erosion)
        {
            int count = W * H;

            // 1. Carve blueprint inland lakes & rivers gently (no deep black holes)
            Parallel.For(0, H, gz =>
            {
                for (int gx = 0; gx < W; gx++)
                {
                    int idx = gz * W + gx;
                    float rawW = tectonic.RawWaterMask[idx];
                    RiverMaskMap[idx] = rawW;

                    bool isInland = rawW > 0.36f && !tectonic.IsOceanConnected[idx];
                    HasInlandWater[idx] = isInland;

                    if (isInland)
                    {
                        float bankH = SampleLocalBankHeight(erosion.HeightMap, gx, gz, tectonic.RawWaterMask);
                        float waterSurfaceY = MathF.Max(0.4f, bankH - 1.2f);
                        InlandWaterY[idx] = waterSurfaceY;
                        float depth = 2.6f + rawW * 2.2f;
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

            // Recompute continuous surface derivatives after gentle river carving
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

            // 3. Hydraulic Velocity v & Discharge Q = A * v + Groundwater Diffusion
            Parallel.For(0, H, gz =>
            {
                for (int gx = 0; gx < W; gx++)
                {
                    int idx = gz * W + gx;
                    float logFlow = Math.Clamp(MathF.Log2(1.0f + FlowAccumMap[idx]) / 10.0f, 0.0f, 1.0f);
                    FlowAccumMap[idx] = logFlow;

                    float slopeSin = MathF.Sin(Mathf.DegToRad(erosion.SlopeDegMap[idx]));
                    // Manning-inspired velocity: higher on steeper slopes and higher discharge
                    float v = Math.Clamp(0.45f + MathF.Sqrt(MathF.Max(0.0f, slopeSin)) * 3.8f + logFlow * 1.4f, 0.3f, 5.5f);
                    WaterVelocityMap[idx] = v;

                    if (HasInlandWater[idx])
                    {
                        // Q = A * v -> deeper/slower in flat basins, shallower/faster in steep rapids
                        WaterDepthMap[idx] = Math.Clamp(WaterDepthMap[idx] * (1.2f - slopeSin * 0.6f), 1.5f, 6.5f);
                    }
                }
            });

            // 4. Lateral Groundwater Diffusion from rivers, lakes & coastal water
            for (int i = 0; i < count; i++)
            {
                GroundwaterMap[i] = (HasInlandWater[i] || RiverMaskMap[i] > 0.35f || erosion.HeightMap[i] < 1.2f)
                    ? 1.0f
                    : FlowAccumMap[i] * 0.45f;
            }

            float[] tmp = new float[count];
            for (int pass = 0; pass < 8; pass++)
            {
                Parallel.For(1, H - 1, z =>
                {
                    for (int x = 1; x < W - 1; x++)
                    {
                        int idx = z * W + x;
                        float avg = (GroundwaterMap[idx - 1] + GroundwaterMap[idx + 1] + GroundwaterMap[idx - W] + GroundwaterMap[idx + W]) * 0.25f;
                        // Diffusion weakens uphill
                        float hDiff = MathF.Max(0.0f, erosion.HeightMap[idx] - 6.0f) * 0.015f;
                        tmp[idx] = MathF.Max(GroundwaterMap[idx], MathF.Max(0.0f, avg * 0.88f - hDiff));
                    }
                });
                Array.Copy(tmp, GroundwaterMap, count);
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

        public float SampleFlowAccum(float wx, float wz) => SampleBilinear(FlowAccumMap, wx, wz);
        public float SampleGroundwater(float wx, float wz) => SampleBilinear(GroundwaterMap, wx, wz);
        public float SampleRiverMask(float wx, float wz) => SampleBilinear(RiverMaskMap, wx, wz);
    }
}
