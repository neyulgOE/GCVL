using System;
using System.Collections.Generic;
using Godot;

namespace PrimevalWorld.WorldGen
{
    public enum BiomeId : byte
    {
        DeepOcean = 0,
        CoastalReef = 1,
        PrimevalForest = 2,
        AutumnSteppe = 3,
        TerracottaDesert = 4,
        GlacialAlpine = 5,
        SanctuaryIsland = 6,
    }

    /// <summary>
    /// Tier 1: Macro Blueprint + 3D Relief Terrain + Flow Accumulation (3840m x 2048m, 961x513).
    /// Provides pure physical terrain, slope, aspect, river/lake hydrology, and D8 flow accumulation
    /// to Tier 2 (ClimateSimulator) and Tier 3 (SoilSimulator).
    /// </summary>
    public sealed class WorldGenerator
    {
        public int Seed { get; private set; }

        public const float RegionWidthMeters = 3840.0f;
        public const float RegionDepthMeters = 2048.0f;
        public const float ChunkSizeMeters = 256.0f;
        public const int ChunksX = 15;
        public const int ChunksZ = 8;
        public const int ChunkVerticesPerSide = 65;
        public const float SeaLevel = 0.0f;

        public const int GridWidth = 961;
        public const int GridDepth = 513;
        public const float CellSize = 4.0f;

        private readonly float[] _heightGrid = new float[GridWidth * GridDepth];
        private readonly float[] _riverMaskGrid = new float[GridWidth * GridDepth];
        private readonly float[] _inlandWaterYGrid = new float[GridWidth * GridDepth];
        private readonly bool[] _hasInlandWater = new bool[GridWidth * GridDepth];
        private readonly float[] _flowAccumGrid = new float[GridWidth * GridDepth];
        private readonly float[] _coastalMaskGrid = new float[GridWidth * GridDepth];

        private Image? _blueprintCropped;

        public WorldGenerator(int seed = 2026)
        {
            LoadBlueprintImage();
            SetSeed(seed);
        }

        private void LoadBlueprintImage()
        {
            const string path = "res://assets/maps/primeval_reach_canonical.jpg";
            byte[] bytes = FileAccess.GetFileAsBytes(path);
            if (bytes.Length == 0)
            {
                GD.PushError($"Failed to load canonical blueprint at {path}");
                return;
            }

            var raw = new Image();
            if (raw.LoadJpgFromBuffer(bytes) == Error.Ok)
            {
                _blueprintCropped = raw.GetRegion(new Rect2I(21, 18, 982, 536));
            }
        }

        public void SetSeed(int newSeed)
        {
            Seed = newSeed;
            GenerateTerrainAndHydrology();
        }

        private void GenerateTerrainAndHydrology()
        {
            int count = GridWidth * GridDepth;
            float[] landMask = new float[count];
            float[] rawWaterMask = new float[count];
            float[] snowFeature = new float[count];
            float[] forestFeature = new float[count];
            float[] ridgeFeature = new float[count];
            float[] nwWeight = new float[count];
            float[] swWeight = new float[count];
            float[] neWeight = new float[count];

            if (_blueprintCropped != null)
            {
                int bw = _blueprintCropped.GetWidth();
                int bh = _blueprintCropped.GetHeight();

                for (int gz = 0; gz < GridDepth; gz++)
                {
                    float fy = (gz / (float)(GridDepth - 1)) * (bh - 1);
                    float nz = gz / (float)(GridDepth - 1);
                    for (int gx = 0; gx < GridWidth; gx++)
                    {
                        float fx = (gx / (float)(GridWidth - 1)) * (bw - 1);
                        float nx = gx / (float)(GridWidth - 1);
                        int idx = gz * GridWidth + gx;

                        Color c = SampleImageBilinear(_blueprintCropped, fx, fy);
                        float r = c.R, g = c.G, b = c.B;
                        float brightness = (r + g + b) / 3.0f;
                        float sat = MathF.Max(r, MathF.Max(g, b)) - MathF.Min(r, MathF.Min(g, b));

                        bool isDeepOcean = (b > r + 0.12f) && (b > 0.23f) && (g < 0.43f) && (r < 0.20f);
                        bool isReef = (g > 0.48f) && (b > 0.56f) && (r < 0.36f);
                        bool isInlandWater = (b > r + 0.06f) && (b > 0.28f) && (r < 0.42f) && !isDeepOcean && !isReef;

                        bool isWater = isDeepOcean || isReef || isInlandWater;
                        landMask[idx] = isWater ? 0.0f : 1.0f;
                        rawWaterMask[idx] = isInlandWater ? 1.0f : 0.0f;

                        nwWeight[idx] = (1.0f - FastNoise.SmoothStep(0.42f, 0.52f, nx))
                                      * (1.0f - FastNoise.SmoothStep(0.42f, 0.52f, nz));
                        swWeight[idx] = (1.0f - FastNoise.SmoothStep(0.40f, 0.50f, nx))
                                      * FastNoise.SmoothStep(0.43f, 0.52f, nz);
                        neWeight[idx] = FastNoise.SmoothStep(0.50f, 0.58f, nx)
                                      * (1.0f - FastNoise.SmoothStep(0.38f, 0.49f, nz));

                        bool isSnow = !isWater && brightness > 0.56f && sat < 0.20f && nx < 0.48f && nz < 0.46f;
                        snowFeature[idx] = isSnow ? 1.0f : 0.0f;

                        bool isRidge = !isWater && ((swWeight[idx] > 0.5f && g > 0.35f && r < 0.72f) || isSnow);
                        ridgeFeature[idx] = isRidge ? 1.0f : 0.0f;

                        bool isForestGreen = !isWater && (g > r + 0.02f) && (g > b + 0.04f) && (g < 0.42f);
                        forestFeature[idx] = isForestGreen ? 1.0f : 0.0f;
                    }
                }
            }

            SmoothGrid(landMask, 2);
            SmoothGrid(snowFeature, 3);
            SmoothGrid(ridgeFeature, 4);
            SmoothGrid(forestFeature, 2);
            SmoothGrid(rawWaterMask, 1);

            bool[] isOceanConnected = FloodFillOcean(landMask);
            float[] coastDist = ComputeCoastDistance(landMask);

            // Pass 1: 3D Relief Heightfield (smoothed SW sandstone mesas & wind-carved sand dunes, sharp NW peaks)
            for (int gz = 0; gz < GridDepth; gz++)
            {
                float worldZ = gz * CellSize;
                float nz = gz / (float)(GridDepth - 1);
                for (int gx = 0; gx < GridWidth; gx++)
                {
                    float worldX = gx * CellSize;
                    float nx = gx / (float)(GridWidth - 1);
                    int idx = gz * GridWidth + gx;

                    float land = landMask[idx];
                    float dMeters = coastDist[idx] * CellSize;

                    float fbm = FastNoise.Fbm2D(worldX * 0.0020f, worldZ * 0.0020f, Seed + 101, 5);
                    float ridged = MathF.Pow(FastNoise.RidgedFbm2D(worldX * 0.0026f, worldZ * 0.0026f, Seed + 307, 6), 1.15f);
                    float micro = (FastNoise.Fbm2D(worldX * 0.012f, worldZ * 0.012f, Seed + 173, 3) - 0.5f) * 2.0f;

                    float baseLandH = 2.8f + FastNoise.SmoothStep(0.0f, 110.0f, dMeters) * 18.0f + fbm * 10.0f + micro;

                    // NW Glacial Alpine Massif sharp peaks
                    float nwLift = snowFeature[idx] * (36.0f + ridged * 76.0f);

                    // SW Terracotta: gentle wind-carved sand dunes + weathered flat-topped sandstone mesas (NO jagged spikes!)
                    float swDunes = swWeight[idx] * FastNoise.Fbm2D(worldX * 0.0055f, worldZ * 0.0022f, Seed + 419, 4) * 11.0f;
                    float swMesaRaw = fbm * 20.0f + MathF.Pow(ridged, 1.8f) * 10.0f;
                    float swMesa = MathF.Floor(swMesaRaw / 6.5f) * 6.5f + FastNoise.SmoothStep(0.2f, 0.8f, (swMesaRaw % 6.5f) / 6.5f) * 6.5f;
                    float swRim = swWeight[idx] * ridgeFeature[idx] * (8.0f + swMesa);

                    // NE Autumn Steppes Plateau
                    float nePlateau = neWeight[idx] * (11.0f + fbm * 14.0f + MathF.Pow(ridged, 1.4f) * 14.0f);

                    // East Crescent Forest Ridge
                    float eastRidge = (nx > 0.52f && nz > 0.45f) ? forestFeature[idx] * MathF.Pow(ridged, 1.3f) * 15.0f : 0.0f;

                    float totalLandH = baseLandH + nwLift + swDunes + swRim + nePlateau + eastRidge;

                    float shelfT = FastNoise.SmoothStep(0.0f, 36.0f, -dMeters);
                    float oceanFloor = Mathf.Lerp(-2.8f, -13.0f, shelfT) + fbm * 1.8f;

                    float landBlend = FastNoise.SmoothStep(0.28f, 0.62f, land);
                    _heightGrid[idx] = oceanFloor * (1.0f - landBlend) + totalLandH * landBlend;
                }
            }

            ApplyHydraulicErosion(60000);

            // Carve inland rivers & lakes gently
            for (int gz = 0; gz < GridDepth; gz++)
            {
                for (int gx = 0; gx < GridWidth; gx++)
                {
                    int idx = gz * GridWidth + gx;
                    bool isInlandRiverOrLake = rawWaterMask[idx] > 0.38f && !isOceanConnected[idx];
                    _hasInlandWater[idx] = isInlandRiverOrLake;
                    _riverMaskGrid[idx] = rawWaterMask[idx];

                    if (isInlandRiverOrLake)
                    {
                        float bankH = SampleLocalBankHeight(gx, gz, rawWaterMask);
                        float waterSurfaceY = MathF.Max(0.2f, bankH - 0.8f);
                        _inlandWaterYGrid[idx] = waterSurfaceY;
                        _heightGrid[idx] = waterSurfaceY - 2.0f;
                    }
                    else
                    {
                        _inlandWaterYGrid[idx] = SeaLevel;
                    }

                    _coastalMaskGrid[idx] = FastNoise.SmoothStep(4.0f, -1.5f, _heightGrid[idx]);
                }
            }

            // Compute D8 Flow Accumulation across the terrain
            ComputeFlowAccumulation();
        }

        private void ComputeFlowAccumulation()
        {
            int count = GridWidth * GridDepth;
            var order = new int[count];
            for (int i = 0; i < count; i++)
            {
                order[i] = i;
                _flowAccumGrid[i] = _heightGrid[i] > 0.2f ? 1.0f : 0.0f;
            }

            // Sort cells from highest to lowest elevation
            Array.Sort(order, (a, b) => _heightGrid[b].CompareTo(_heightGrid[a]));

            int[] dx = { -1, 0, 1, -1, 1, -1, 0, 1 };
            int[] dz = { -1, -1, -1, 0, 0, 1, 1, 1 };
            float[] dist = { 1.414f, 1.0f, 1.414f, 1.0f, 1.0f, 1.414f, 1.0f, 1.414f };

            for (int k = 0; k < count; k++)
            {
                int idx = order[k];
                float h = _heightGrid[idx];
                if (h <= 0.1f) continue;

                int x = idx % GridWidth;
                int z = idx / GridWidth;
                if (x == 0 || x == GridWidth - 1 || z == 0 || z == GridDepth - 1) continue;

                float bestSlope = 0.0f;
                int bestTarget = -1;
                for (int d = 0; d < 8; d++)
                {
                    int nIdx = (z + dz[d]) * GridWidth + (x + dx[d]);
                    float s = (h - _heightGrid[nIdx]) / dist[d];
                    if (s > bestSlope)
                    {
                        bestSlope = s;
                        bestTarget = nIdx;
                    }
                }

                if (bestTarget >= 0)
                {
                    _flowAccumGrid[bestTarget] += _flowAccumGrid[idx];
                }
            }

            // Normalize log-flow accumulation to [0..1]
            for (int i = 0; i < count; i++)
            {
                _flowAccumGrid[i] = Math.Clamp(MathF.Log2(1.0f + _flowAccumGrid[i]) / 9.5f, 0.0f, 1.0f);
            }
        }

        private float SampleLocalBankHeight(int gx, int gz, float[] rawWaterMask)
        {
            float sum = 0.0f;
            int cnt = 0;
            for (int dz = -6; dz <= 6; dz += 2)
            {
                int tz = gz + dz;
                if (tz < 0 || tz >= GridDepth) continue;
                for (int dx = -6; dx <= 6; dx += 2)
                {
                    int tx = gx + dx;
                    if (tx < 0 || tx >= GridWidth) continue;
                    int tidx = tz * GridWidth + tx;
                    if (rawWaterMask[tidx] < 0.25f && _heightGrid[tidx] > 0.5f)
                    {
                        sum += _heightGrid[tidx];
                        cnt++;
                    }
                }
            }
            return cnt > 0 ? MathF.Min(sum / cnt, 24.0f) : 4.0f;
        }

        private static bool[] FloodFillOcean(float[] landMask)
        {
            int count = GridWidth * GridDepth;
            bool[] ocean = new bool[count];
            var queue = new Queue<int>(16384);

            for (int x = 0; x < GridWidth; x++)
            {
                TryEnqueue(x, 0);
                TryEnqueue(x, GridDepth - 1);
            }
            for (int z = 0; z < GridDepth; z++)
            {
                TryEnqueue(0, z);
                TryEnqueue(GridWidth - 1, z);
            }

            void TryEnqueue(int x, int z)
            {
                int idx = z * GridWidth + x;
                if (!ocean[idx] && landMask[idx] < 0.45f)
                {
                    ocean[idx] = true;
                    queue.Enqueue(idx);
                }
            }

            while (queue.Count > 0)
            {
                int cur = queue.Dequeue();
                int cx = cur % GridWidth;
                int cz = cur / GridWidth;

                if (cx > 0) TryEnqueue(cx - 1, cz);
                if (cx < GridWidth - 1) TryEnqueue(cx + 1, cz);
                if (cz > 0) TryEnqueue(cx, cz - 1);
                if (cz < GridDepth - 1) TryEnqueue(cx, cz + 1);
            }

            return ocean;
        }

        private static float[] ComputeCoastDistance(float[] landMask)
        {
            int count = GridWidth * GridDepth;
            float[] dist = new float[count];
            const float inf = 9999.0f;

            for (int i = 0; i < count; i++)
                dist[i] = landMask[i] >= 0.45f ? inf : 0.0f;

            for (int z = 1; z < GridDepth; z++)
            {
                for (int x = 1; x < GridWidth - 1; x++)
                {
                    int idx = z * GridWidth + x;
                    if (dist[idx] == 0.0f) continue;
                    float d = MathF.Min(dist[idx], dist[idx - 1] + 1.0f);
                    d = MathF.Min(d, dist[idx - GridWidth] + 1.0f);
                    d = MathF.Min(d, dist[idx - GridWidth - 1] + 1.414f);
                    d = MathF.Min(d, dist[idx - GridWidth + 1] + 1.414f);
                    dist[idx] = d;
                }
            }

            for (int z = GridDepth - 2; z >= 0; z--)
            {
                for (int x = GridWidth - 2; x >= 1; x--)
                {
                    int idx = z * GridWidth + x;
                    if (dist[idx] == 0.0f) continue;
                    float d = MathF.Min(dist[idx], dist[idx + 1] + 1.0f);
                    d = MathF.Min(d, dist[idx + GridWidth] + 1.0f);
                    d = MathF.Min(d, dist[idx + GridWidth + 1] + 1.414f);
                    d = MathF.Min(d, dist[idx + GridWidth - 1] + 1.414f);
                    dist[idx] = d;
                }
            }

            float[] oceanDist = new float[count];
            for (int i = 0; i < count; i++)
                oceanDist[i] = landMask[i] >= 0.45f ? 0.0f : inf;

            for (int z = 1; z < GridDepth; z++)
            {
                for (int x = 1; x < GridWidth - 1; x++)
                {
                    int idx = z * GridWidth + x;
                    if (oceanDist[idx] == 0.0f) continue;
                    oceanDist[idx] = MathF.Min(oceanDist[idx], MathF.Min(oceanDist[idx - 1], oceanDist[idx - GridWidth]) + 1.0f);
                }
            }
            for (int z = GridDepth - 2; z >= 0; z--)
            {
                for (int x = GridWidth - 2; x >= 1; x--)
                {
                    int idx = z * GridWidth + x;
                    if (oceanDist[idx] == 0.0f) continue;
                    oceanDist[idx] = MathF.Min(oceanDist[idx], MathF.Min(oceanDist[idx + 1], oceanDist[idx + GridWidth]) + 1.0f);
                }
            }

            for (int i = 0; i < count; i++)
            {
                if (landMask[i] < 0.45f) dist[i] = -oceanDist[i];
            }

            return dist;
        }

        private static void SmoothGrid(float[] grid, int passes)
        {
            float[] tmp = new float[grid.Length];
            for (int p = 0; p < passes; p++)
            {
                for (int z = 1; z < GridDepth - 1; z++)
                {
                    for (int x = 1; x < GridWidth - 1; x++)
                    {
                        int idx = z * GridWidth + x;
                        tmp[idx] = (grid[idx] * 4.0f
                                  + grid[idx - 1] + grid[idx + 1]
                                  + grid[idx - GridWidth] + grid[idx + GridWidth]) / 8.0f;
                    }
                }
                Array.Copy(tmp, grid, grid.Length);
            }
        }

        private static Color SampleImageBilinear(Image img, float fx, float fy)
        {
            int w = img.GetWidth();
            int h = img.GetHeight();
            int x0 = Math.Clamp((int)fx, 0, w - 1);
            int y0 = Math.Clamp((int)fy, 0, h - 1);
            int x1 = Math.Min(w - 1, x0 + 1);
            int y1 = Math.Min(h - 1, y0 + 1);
            return img.GetPixel(x0, y0).Lerp(img.GetPixel(x1, y0), fx - x0)
                      .Lerp(img.GetPixel(x0, y1).Lerp(img.GetPixel(x1, y1), fx - x0), fy - y0);
        }

        private void ApplyHydraulicErosion(int numDroplets)
        {
            var rng = new Random(Seed + 991);
            const int maxLifetime = 28;
            const float inertia = 0.08f;
            const float sedimentCapacityFactor = 3.6f;
            const float minSedimentCapacity = 0.01f;
            const float erodeSpeed = 0.28f;
            const float depositSpeed = 0.28f;
            const float evaporateSpeed = 0.02f;
            const float gravity = 4.0f;
            const int brushRadius = 2;

            for (int d = 0; d < numDroplets; d++)
            {
                float posX = (float)(rng.NextDouble() * (GridWidth - 4) + 2);
                float posZ = (float)(rng.NextDouble() * (GridDepth - 4) + 2);
                float dirX = 0.0f, dirZ = 0.0f, speed = 1.0f, water = 1.0f, sediment = 0.0f;

                for (int step = 0; step < maxLifetime; step++)
                {
                    int nodeX = (int)posX;
                    int nodeZ = (int)posZ;
                    if (nodeX < 1 || nodeX >= GridWidth - 2 || nodeZ < 1 || nodeZ >= GridDepth - 2) break;

                    float cellOffsetX = posX - nodeX;
                    float cellOffsetZ = posZ - nodeZ;

                    int idx00 = nodeZ * GridWidth + nodeX;
                    float h00 = _heightGrid[idx00], h10 = _heightGrid[idx00 + 1];
                    float h01 = _heightGrid[idx00 + GridWidth], h11 = _heightGrid[idx00 + GridWidth + 1];

                    float oldH = (h00 * (1 - cellOffsetX) + h10 * cellOffsetX) * (1 - cellOffsetZ)
                               + (h01 * (1 - cellOffsetX) + h11 * cellOffsetX) * cellOffsetZ;
                    if (oldH < SeaLevel - 0.5f) break;

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
                    if (posX < 1 || posX >= GridWidth - 2 || posZ < 1 || posZ >= GridDepth - 2) break;

                    int newX = (int)posX;
                    int newZ = (int)posZ;
                    float u = posX - newX, v = posZ - newZ;
                    int nIdx = newZ * GridWidth + newX;
                    float newH = (_heightGrid[nIdx] * (1 - u) + _heightGrid[nIdx + 1] * u) * (1 - v)
                               + (_heightGrid[nIdx + GridWidth] * (1 - u) + _heightGrid[nIdx + GridWidth + 1] * u) * v;

                    float deltaH = newH - oldH;
                    float capacity = MathF.Max(-deltaH * speed * water * sedimentCapacityFactor, minSedimentCapacity);

                    if (sediment > capacity || deltaH > 0.0f)
                    {
                        float amountToDeposit = deltaH > 0.0f ? MathF.Min(deltaH, sediment) : (sediment - capacity) * depositSpeed;
                        sediment -= amountToDeposit;
                        _heightGrid[idx00] += amountToDeposit * (1 - cellOffsetX) * (1 - cellOffsetZ);
                        _heightGrid[idx00 + 1] += amountToDeposit * cellOffsetX * (1 - cellOffsetZ);
                        _heightGrid[idx00 + GridWidth] += amountToDeposit * (1 - cellOffsetX) * cellOffsetZ;
                        _heightGrid[idx00 + GridWidth + 1] += amountToDeposit * cellOffsetX * cellOffsetZ;
                    }
                    else
                    {
                        float amountToErode = MathF.Min((capacity - sediment) * erodeSpeed, -deltaH);
                        float totalWeight = 0.0f;
                        for (int bz = -brushRadius; bz <= brushRadius; bz++)
                            for (int bx = -brushRadius; bx <= brushRadius; bx++)
                            {
                                int tx = nodeX + bx, tz = nodeZ + bz;
                                if (tx < 0 || tx >= GridWidth || tz < 0 || tz >= GridDepth) continue;
                                float dist = MathF.Sqrt(bx * bx + bz * bz);
                                if (dist < brushRadius) totalWeight += brushRadius - dist;
                            }

                        if (totalWeight > 1e-5f)
                        {
                            for (int bz = -brushRadius; bz <= brushRadius; bz++)
                                for (int bx = -brushRadius; bx <= brushRadius; bx++)
                                {
                                    int tx = nodeX + bx, tz = nodeZ + bz;
                                    if (tx < 0 || tx >= GridWidth || tz < 0 || tz >= GridDepth) continue;
                                    float dist = MathF.Sqrt(bx * bx + bz * bz);
                                    if (dist < brushRadius)
                                    {
                                        float w = (brushRadius - dist) / totalWeight;
                                        float deltaSediment = MathF.Min(_heightGrid[tz * GridWidth + tx] - (SeaLevel - 13.0f), amountToErode * w);
                                        _heightGrid[tz * GridWidth + tx] -= deltaSediment;
                                        sediment += deltaSediment;
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
            float cx = Math.Clamp(gx, 0.0f, GridWidth - 1.001f);
            float cz = Math.Clamp(gz, 0.0f, GridDepth - 1.001f);
            int x0 = (int)cx, z0 = (int)cz;
            float tx = cx - x0, tz = cz - z0;
            int idx = z0 * GridWidth + x0;
            return (grid[idx] * (1 - tx) + grid[idx + 1] * tx) * (1 - tz)
                 + (grid[idx + GridWidth] * (1 - tx) + grid[idx + GridWidth + 1] * tx) * tz;
        }

        public bool HasInlandWaterAtCell(int gx, int gz) => _hasInlandWater[gz * GridWidth + gx];
        public float GetInlandWaterYAtCell(int gx, int gz) => _inlandWaterYGrid[gz * GridWidth + gx];
        public float GetHeightAtCell(int gx, int gz) => _heightGrid[gz * GridWidth + gx];
        public float GetRiverMaskAtCell(int gx, int gz) => _riverMaskGrid[gz * GridWidth + gx];
        public float GetFlowAccumAtCell(int gx, int gz) => _flowAccumGrid[gz * GridWidth + gx];

        public float SampleHeight(float worldX, float worldZ)
        {
            if (worldX < 0.0f || worldX > RegionWidthMeters || worldZ < 0.0f || worldZ > RegionDepthMeters)
                return -12.0f;
            return SampleBilinear(_heightGrid, worldX / CellSize, worldZ / CellSize);
        }

        public float SampleRiverMask(float worldX, float worldZ)
        {
            if (worldX < 0.0f || worldX > RegionWidthMeters || worldZ < 0.0f || worldZ > RegionDepthMeters)
                return 0.0f;
            return SampleBilinear(_riverMaskGrid, worldX / CellSize, worldZ / CellSize);
        }

        public float SampleFlowAccum(float worldX, float worldZ)
        {
            if (worldX < 0.0f || worldX > RegionWidthMeters || worldZ < 0.0f || worldZ > RegionDepthMeters)
                return 0.0f;
            return SampleBilinear(_flowAccumGrid, worldX / CellSize, worldZ / CellSize);
        }

        public float SampleCoastalMask(float worldX, float worldZ)
        {
            if (worldX < 0.0f || worldX > RegionWidthMeters || worldZ < 0.0f || worldZ > RegionDepthMeters)
                return 1.0f;
            return SampleBilinear(_coastalMaskGrid, worldX / CellSize, worldZ / CellSize);
        }

        public Vector3 SampleNormal(float worldX, float worldZ, float eps = 2.5f)
        {
            float hL = SampleHeight(worldX - eps, worldZ);
            float hR = SampleHeight(worldX + eps, worldZ);
            float hD = SampleHeight(worldX, worldZ - eps);
            float hU = SampleHeight(worldX, worldZ + eps);
            return new Vector3(hL - hR, 2.0f * eps, hD - hU).Normalized();
        }

        public ImageTexture BuildBlueprintTexture()
        {
            if (_blueprintCropped != null)
                return ImageTexture.CreateFromImage(_blueprintCropped);
            return ImageTexture.CreateFromImage(Image.CreateEmpty(64, 64, false, Image.Format.Rgb8));
        }
    }
}
