using System;
using System.Threading.Tasks;
using Godot;
using PrimevalWorld.Core;

namespace PrimevalWorld.WorldGen
{
    /// <summary>
    /// Stage 1B: Physical Geology & Erosion Solver (1025x577):
    /// 1. Material-Dependent Thermal Erosion (Angle of Repose: Sand 32°, Soil 40°, Bedrock 64°).
    /// 2. Kinetic Hydraulic Droplet Erosion (90,000 droplets carving mountain gullies & alluvial fans).
    /// 3. Aeolian Dune Ripples perpendicular to wind in dry sandy SW basins.
    /// Computes HeightMap, SlopeDegMap, AspectMap, NormalMap, BedrockMask & SedimentMap.
    /// </summary>
    public sealed class ErosionPhysics
    {
        private const int W = WorldPhysicsConfig.VertW;
        private const int H = WorldPhysicsConfig.VertH;
        private const float Cell = WorldPhysicsConfig.CellSize;

        public float[] HeightMap { get; } = new float[W * H];
        public float[] SedimentMap { get; } = new float[W * H];
        public float[] BedrockMask { get; } = new float[W * H];
        public float[] SlopeDegMap { get; } = new float[W * H];
        public float[] AspectMap { get; } = new float[W * H];
        public Vector3[] NormalMap { get; } = new Vector3[W * H];

        public void Solve(TectonicContinentGen tectonic, int seed)
        {
            int count = W * H;
            float[] bedrock = new float[count];
            for (int i = 0; i < count; i++)
            {
                bedrock[i] = tectonic.BedrockHeight[i];
                SedimentMap[i] = tectonic.SedimentDepth[i];
                HeightMap[i] = bedrock[i] + SedimentMap[i];
            }

            // 1. Material-Dependent Thermal Erosion (Angle of Repose: Sand 32°, Soil 40°, Bedrock 64°)
            ApplyThermalErosion(tectonic, bedrock, passes: 10);

            // 2. Kinetic Hydraulic Droplet Erosion (90,000 droplets)
            ApplyHydraulicErosion(bedrock, seed, numDroplets: 90000);

            // Prevent erosion from sinking canonical coastal plains below sea level
            Parallel.For(0, count, i =>
            {
                if (tectonic.LandMask[i] > 0.60f && tectonic.RawWaterMask[i] < 0.25f)
                {
                    float minFloor = tectonic.CoastDistMeters[i] > 95.0f ? 6.5f : 0.9f;
                    if (HeightMap[i] < minFloor)
                    {
                        float lift = minFloor - HeightMap[i];
                        SedimentMap[i] += lift;
                        HeightMap[i] = minFloor;
                    }
                }
            });

            // 3. Aeolian Wind Dune Ripples in dry SW desert sediment
            ApplyAeolianDunes(tectonic, seed);

            // 4. Compute Slope (deg), Aspect, BedrockMask & Continuous Normals across full 1025x577 grid
            ComputeSurfaceDerivatives(bedrock);
        }

        private void ApplyThermalErosion(TectonicContinentGen tectonic, float[] bedrock, int passes)
        {
            float[] delta = new float[W * H];
            int[] dx = { -1, 1, 0, 0, -1, 1, -1, 1 };
            int[] dz = { 0, 0, -1, 1, -1, -1, 1, 1 };
            float[] dist = { Cell, Cell, Cell, Cell, Cell * 1.414f, Cell * 1.414f, Cell * 1.414f, Cell * 1.414f };

            for (int p = 0; p < passes; p++)
            {
                Array.Clear(delta, 0, delta.Length);

                for (int z = 1; z < H - 1; z++)
                {
                    for (int x = 1; x < W - 1; x++)
                    {
                        int idx = z * W + x;
                        float h = HeightMap[idx];
                        if (h <= WorldPhysicsConfig.SeaLevel) continue;

                        // Determine local talus angle based on material (Sand 32° vs Soil 40° vs Bedrock 64°)
                        float sed = SedimentMap[idx];
                        float tanRepose = tectonic.SwDesertWeight[idx] > 0.45f && sed > 1.5f
                            ? WorldPhysicsConfig.SandTanRepose
                            : (sed > 0.8f ? WorldPhysicsConfig.SoilTanRepose : WorldPhysicsConfig.RockTanRepose);

                        float maxDiff = 0.0f;
                        float totalExcess = 0.0f;
                        int bestNeighbor = -1;

                        for (int n = 0; n < 8; n++)
                        {
                            int nIdx = (z + dz[n]) * W + (x + dx[n]);
                            float diff = h - HeightMap[nIdx];
                            float talus = tanRepose * dist[n];
                            if (diff > talus)
                            {
                                float excess = diff - talus;
                                totalExcess += excess;
                                if (excess > maxDiff)
                                {
                                    maxDiff = excess;
                                    bestNeighbor = nIdx;
                                }
                            }
                        }

                        if (bestNeighbor >= 0 && totalExcess > 0.001f)
                        {
                            float move = MathF.Min(maxDiff * 0.45f, sed > 0.2f ? sed * 0.6f + 0.35f : 0.45f);
                            delta[idx] -= move;
                            delta[bestNeighbor] += move;
                        }
                    }
                }

                Parallel.For(0, W * H, i =>
                {
                    float d = delta[i];
                    if (d < 0.0f)
                    {
                        float fromSed = MathF.Min(SedimentMap[i], -d);
                        SedimentMap[i] -= fromSed;
                        bedrock[i] -= (-d - fromSed);
                    }
                    else if (d > 0.0f)
                    {
                        SedimentMap[i] += d;
                    }
                    HeightMap[i] = bedrock[i] + SedimentMap[i];
                });
            }
        }

        private void ApplyHydraulicErosion(float[] bedrock, int seed, int numDroplets)
        {
            var rng = new Random(seed + 991);
            const int maxLifetime = 30;
            const float inertia = 0.08f;
            const float kc = 4.2f;
            const float minCapacity = 0.02f;
            const float erodeSpeed = 0.28f;
            const float depositSpeed = 0.28f;
            const float evaporateSpeed = 0.025f;
            const int brushRadius = 2;

            for (int d = 0; d < numDroplets; d++)
            {
                float posX = (float)(rng.NextDouble() * (W - 4) + 2);
                float posZ = (float)(rng.NextDouble() * (H - 4) + 2);
                float dirX = 0.0f, dirZ = 0.0f, speed = 1.0f, water = 1.0f, sediment = 0.0f;

                for (int step = 0; step < maxLifetime; step++)
                {
                    int nodeX = (int)posX;
                    int nodeZ = (int)posZ;
                    if (nodeX < 1 || nodeX >= W - 2 || nodeZ < 1 || nodeZ >= H - 2) break;

                    float ox = posX - nodeX;
                    float oz = posZ - nodeZ;
                    int idx00 = nodeZ * W + nodeX;

                    float h00 = HeightMap[idx00], h10 = HeightMap[idx00 + 1];
                    float h01 = HeightMap[idx00 + W], h11 = HeightMap[idx00 + W + 1];
                    float oldH = (h00 * (1 - ox) + h10 * ox) * (1 - oz) + (h01 * (1 - ox) + h11 * ox) * oz;
                    if (oldH < WorldPhysicsConfig.SeaLevel - 0.5f) break;

                    float gradX = ((h10 - h00) * (1 - oz) + (h11 - h01) * oz) / Cell;
                    float gradZ = ((h01 - h00) * (1 - ox) + (h11 - h10) * ox) / Cell;

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
                    if (posX < 1 || posX >= W - 2 || posZ < 1 || posZ >= H - 2) break;

                    int newX = (int)posX;
                    int newZ = (int)posZ;
                    float u = posX - newX, v = posZ - newZ;
                    int nIdx = newZ * W + newX;
                    float newH = (HeightMap[nIdx] * (1 - u) + HeightMap[nIdx + 1] * u) * (1 - v)
                               + (HeightMap[nIdx + W] * (1 - u) + HeightMap[nIdx + W + 1] * u) * v;

                    float deltaH = newH - oldH;
                    float capacity = MathF.Max(-deltaH * speed * water * kc, minCapacity);

                    if (sediment > capacity || deltaH > 0.0f)
                    {
                        float dep = deltaH > 0.0f ? MathF.Min(deltaH, sediment) : (sediment - capacity) * depositSpeed;
                        sediment -= dep;
                        Deposit(idx00, dep * (1 - ox) * (1 - oz));
                        Deposit(idx00 + 1, dep * ox * (1 - oz));
                        Deposit(idx00 + W, dep * (1 - ox) * oz);
                        Deposit(idx00 + W + 1, dep * ox * oz);
                    }
                    else
                    {
                        float erode = MathF.Min((capacity - sediment) * erodeSpeed, -deltaH);
                        float totalW = 0.0f;
                        for (int bz = -brushRadius; bz <= brushRadius; bz++)
                            for (int bx = -brushRadius; bx <= brushRadius; bx++)
                            {
                                int tx = nodeX + bx, tz = nodeZ + bz;
                                if (tx < 0 || tx >= W || tz < 0 || tz >= H) continue;
                                float dist = MathF.Sqrt(bx * bx + bz * bz);
                                if (dist < brushRadius) totalW += brushRadius - dist;
                            }

                        if (totalW > 1e-5f)
                        {
                            for (int bz = -brushRadius; bz <= brushRadius; bz++)
                                for (int bx = -brushRadius; bx <= brushRadius; bx++)
                                {
                                    int tx = nodeX + bx, tz = nodeZ + bz;
                                    if (tx < 0 || tx >= W || tz < 0 || tz >= H) continue;
                                    float dist = MathF.Sqrt(bx * bx + bz * bz);
                                    if (dist < brushRadius)
                                    {
                                        int tidx = tz * W + tx;
                                        float w = (brushRadius - dist) / totalW;
                                        float ds = MathF.Min(HeightMap[tidx] - (WorldPhysicsConfig.SeaLevel - 15.0f), erode * w);
                                        float fromSed = MathF.Min(SedimentMap[tidx], ds);
                                        SedimentMap[tidx] -= fromSed;
                                        bedrock[tidx] -= (ds - fromSed);
                                        HeightMap[tidx] = bedrock[tidx] + SedimentMap[tidx];
                                        sediment += ds;
                                    }
                                }
                        }
                    }

                    speed = MathF.Sqrt(MathF.Max(0.01f, speed * speed + (-deltaH) * WorldPhysicsConfig.Gravity * 0.25f));
                    water *= (1.0f - evaporateSpeed);
                }
            }

            void Deposit(int idx, float amount)
            {
                SedimentMap[idx] += amount;
                HeightMap[idx] += amount;
            }
        }

        private void ApplyAeolianDunes(TectonicContinentGen tectonic, int seed)
        {
            Parallel.For(1, H - 1, z =>
            {
                float wz = z * Cell;
                for (int x = 1; x < W - 1; x++)
                {
                    int idx = z * W + x;
                    if (tectonic.SwDesertWeight[idx] < 0.35f || HeightMap[idx] < 2.0f) continue;

                    float wx = x * Cell;
                    float slopeApprox = MathF.Abs(HeightMap[idx + 1] - HeightMap[idx - 1]) / (2.0f * Cell);
                    if (slopeApprox > 0.35f) continue;

                    // Gentle wind-perpendicular sand dune waves
                    float phase = (wx * 0.82f + wz * 0.57f) * 0.022f + FastNoise.Fbm2D(wx * 0.002f, wz * 0.002f, seed + 433, 3) * 5.0f;
                    float duneWave = (1.0f - MathF.Abs(MathF.Sin(phase))) * 4.5f * tectonic.SwDesertWeight[idx] * FastNoise.SmoothStep(1.0f, 6.0f, SedimentMap[idx]);
                    SedimentMap[idx] += duneWave;
                    HeightMap[idx] += duneWave;
                }
            });
        }

        public void ComputeSurfaceDerivatives(float[]? bedrock = null)
        {
            Parallel.For(0, H, z =>
            {
                int zm = Math.Max(0, z - 1);
                int zp = Math.Min(H - 1, z + 1);
                for (int x = 0; x < W; x++)
                {
                    int xm = Math.Max(0, x - 1);
                    int xp = Math.Min(W - 1, x + 1);
                    int idx = z * W + x;

                    float hL = HeightMap[z * W + xm];
                    float hR = HeightMap[z * W + xp];
                    float hD = HeightMap[zm * W + x];
                    float hU = HeightMap[zp * W + x];

                    Vector3 n = new Vector3(hL - hR, 2.0f * Cell, hD - hU).Normalized();
                    NormalMap[idx] = n;

                    float slopeRad = MathF.Acos(Math.Clamp(n.Y, 0.0f, 1.0f));
                    float slopeDeg = Mathf.RadToDeg(slopeRad);
                    SlopeDegMap[idx] = slopeDeg;
                    AspectMap[idx] = n.Z; // +1 = South-facing warm, -1 = North-facing shaded

                    // Exposed bedrock where sediment is thin or slope exceeds soil repose
                    float exposed = MathF.Max(
                        FastNoise.SmoothStep(2.0f, 0.2f, SedimentMap[idx]),
                        FastNoise.SmoothStep(26.0f, 38.0f, slopeDeg)
                    );
                    BedrockMask[idx] = Math.Clamp(exposed, 0.0f, 1.0f);
                }
            });
        }

        private float SampleBilinear(float[] grid, float worldX, float worldZ)
        {
            float cx = Math.Clamp(worldX / Cell, 0.0f, W - 1.001f);
            float cz = Math.Clamp(worldZ / Cell, 0.0f, H - 1.001f);
            int x0 = (int)cx, z0 = (int)cz;
            float tx = cx - x0, tz = cz - z0;
            int idx = z0 * W + x0;
            return (grid[idx] * (1 - tx) + grid[idx + 1] * tx) * (1 - tz)
                 + (grid[idx + W] * (1 - tx) + grid[idx + W + 1] * tx) * tz;
        }

        public float SampleHeight(float worldX, float worldZ) => SampleBilinear(HeightMap, worldX, worldZ);
        public float SampleSlopeDeg(float worldX, float worldZ) => SampleBilinear(SlopeDegMap, worldX, worldZ);
        public float SampleSediment(float worldX, float worldZ) => SampleBilinear(SedimentMap, worldX, worldZ);
    }
}
