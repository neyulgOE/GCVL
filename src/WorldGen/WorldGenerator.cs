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

    public readonly struct TerrainSample
    {
        public readonly float Height;
        public readonly float RiverMask;
        public readonly float InlandWaterY;
        public readonly float CoastalMask;
        public readonly float Moisture;
        public readonly float ForestDensity;
        public readonly float Temperature;
        public readonly float SaltExposure;
        public readonly float MegafaunaCorridor;
        public readonly BiomeId Biome;

        public TerrainSample(
            float height,
            float riverMask,
            float inlandWaterY,
            float coastalMask,
            float moisture,
            float forestDensity,
            float temperature,
            float saltExposure,
            float megafaunaCorridor,
            BiomeId biome)
        {
            Height = height;
            RiverMask = riverMask;
            InlandWaterY = inlandWaterY;
            CoastalMask = coastalMask;
            Moisture = moisture;
            ForestDensity = forestDensity;
            Temperature = temperature;
            SaltExposure = saltExposure;
            MegafaunaCorridor = megafaunaCorridor;
            Biome = biome;
        }
    }

    /// <summary>
    /// Macro Blueprint + Procedural 3D Detail World Generator (3840m x 2048m, 961x513).
    /// Reads res://assets/maps/primeval_reach_canonical.jpg strictly as the macro layout
    /// blueprint (exact 4 continents, fjords, bays, rivers, delta & 5 biomes),
    /// smooths coastlines to eliminate pixel stairs, and adds high-resolution 3D Ridged Noise
    /// + 70,000-droplet Particle Hydraulic Erosion.
    /// </summary>
    public sealed class WorldGenerator
    {
        public int Seed { get; private set; }

        public const float RegionWidthMeters = 3840.0f;  // 15 * 256m
        public const float RegionDepthMeters = 2048.0f;  // 8 * 256m
        public const float ChunkSizeMeters = 256.0f;
        public const int ChunksX = 15;
        public const int ChunksZ = 8;
        public const int ChunkVerticesPerSide = 65;      // 4.0m vertex spacing
        public const float SeaLevel = 0.0f;

        public const int GridWidth = 961;                // 15 * 64 + 1
        public const int GridDepth = 513;                // 8 * 64 + 1
        private const float CellSize = 4.0f;

        private readonly float[] _heightGrid = new float[GridWidth * GridDepth];
        private readonly float[] _riverMaskGrid = new float[GridWidth * GridDepth];
        private readonly float[] _inlandWaterYGrid = new float[GridWidth * GridDepth];
        private readonly bool[] _hasInlandWater = new bool[GridWidth * GridDepth];
        private readonly float[] _moistureGrid = new float[GridWidth * GridDepth];
        private readonly float[] _forestGrid = new float[GridWidth * GridDepth];
        private readonly float[] _autumnWeight = new float[GridWidth * GridDepth];
        private readonly float[] _desertWeight = new float[GridWidth * GridDepth];
        private readonly float[] _glacialWeight = new float[GridWidth * GridDepth];
        private readonly BiomeId[] _biomeGrid = new BiomeId[GridWidth * GridDepth];

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
            Error err = raw.LoadJpgFromBuffer(bytes);
            if (err != Error.Ok)
            {
                GD.PushError($"Failed to decode JPG blueprint: {err}");
                return;
            }

            // Crop inner map inside vintage parchment border (x: 21..1003, y: 18..554)
            _blueprintCropped = raw.GetRegion(new Rect2I(21, 18, 982, 536));
        }

        public void SetSeed(int newSeed)
        {
            Seed = newSeed;
            GenerateFromBlueprint();
        }

        private void GenerateFromBlueprint()
        {
            int count = GridWidth * GridDepth;
            float[] landMask = new float[count];
            float[] rawWaterMask = new float[count];
            float[] snowFeature = new float[count];
            float[] forestFeature = new float[count];
            float[] ridgeFeature = new float[count];

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

                        // Regional Biome weights directly matching the canonical map layout
                        _glacialWeight[idx] = (1.0f - FastNoise.SmoothStep(0.42f, 0.52f, nx))
                                            * (1.0f - FastNoise.SmoothStep(0.42f, 0.52f, nz));
                        _desertWeight[idx] = (1.0f - FastNoise.SmoothStep(0.40f, 0.50f, nx))
                                           * FastNoise.SmoothStep(0.43f, 0.52f, nz);
                        _autumnWeight[idx] = FastNoise.SmoothStep(0.50f, 0.58f, nx)
                                           * (1.0f - FastNoise.SmoothStep(0.38f, 0.49f, nz));

                        // Snow & alpine rock features in NW
                        bool isSnow = !isWater && brightness > 0.56f && sat < 0.20f && nx < 0.48f && nz < 0.46f;
                        snowFeature[idx] = isSnow ? 1.0f : 0.0f;

                        // Dark rocky crater rim / mountain ridges
                        bool isRidge = !isWater && ((_desertWeight[idx] > 0.5f && g > 0.35f && r < 0.72f) || isSnow);
                        ridgeFeature[idx] = isRidge ? 1.0f : 0.0f;

                        // Dense dark primeval forest groves directly from blueprint green canopy regions
                        bool isForestGreen = !isWater && (g > r + 0.02f) && (g > b + 0.04f) && (g < 0.42f);
                        forestFeature[idx] = isForestGreen ? 1.0f : 0.0f;
                    }
                }
            }

            // Smooth masks twice to remove all image pixel staircases
            SmoothGrid(landMask, 2);
            SmoothGrid(snowFeature, 3);
            SmoothGrid(ridgeFeature, 3);
            SmoothGrid(forestFeature, 2);
            SmoothGrid(rawWaterMask, 1);

            // Identify ocean-connected water vs inland rivers/highland lakes via BFS from (0, 0)
            bool[] isOceanConnected = FloodFillOcean(landMask);

            // Compute distance from coast (in cells) for natural inland elevation rise
            float[] coastDist = ComputeCoastDistance(landMask, isOceanConnected);

            // Pass 1: Build 3D relief heightfield combining smooth blueprint + 3D Ridged Noise
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

                    float fbm = FastNoise.Fbm2D(worldX * 0.0022f, worldZ * 0.0022f, Seed + 101, 5);
                    float ridged = MathF.Pow(FastNoise.RidgedFbm2D(worldX * 0.0028f, worldZ * 0.0028f, Seed + 307, 6), 1.15f);
                    float micro = (FastNoise.Fbm2D(worldX * 0.014f, worldZ * 0.014f, Seed + 173, 3) - 0.5f) * 2.2f;

                    // Base coastal rise
                    float baseLandH = 2.8f + FastNoise.SmoothStep(0.0f, 110.0f, dMeters) * 18.0f + fbm * 10.0f + micro;

                    // NW Glacial Alpine Massif peaks
                    float nwLift = snowFeature[idx] * (38.0f + ridged * 76.0f);

                    // SW Terracotta Crater Rim & Sand Dunes
                    float swDunes = _desertWeight[idx] * FastNoise.RidgedFbm2D(worldX * 0.006f, worldZ * 0.0025f, Seed + 419, 3) * 9.0f;
                    float swRim = _desertWeight[idx] * ridgeFeature[idx] * (18.0f + ridged * 32.0f);

                    // NE Autumn Steppes Plateau
                    float nePlateau = _autumnWeight[idx] * (12.0f + fbm * 14.0f + ridged * 18.0f);

                    // East Crescent Forest Ridge
                    float eastRidge = (nx > 0.52f && nz > 0.45f) ? forestFeature[idx] * ridged * 16.0f : 0.0f;

                    float totalLandH = baseLandH + nwLift + swDunes + swRim + nePlateau + eastRidge;

                    // Shallow coral shelf (-3.2m .. 0m) transitioning to deep ocean (-13m)
                    float shelfT = FastNoise.SmoothStep(0.0f, 36.0f, -dMeters);
                    float oceanFloor = Mathf.Lerp(-2.8f, -13.0f, shelfT) + fbm * 1.8f;

                    float landBlend = FastNoise.SmoothStep(0.28f, 0.62f, land);
                    _heightGrid[idx] = oceanFloor * (1.0f - landBlend) + totalLandH * landBlend;
                }
            }

            // Pass 2: 65,000-Droplet Hydraulic Erosion for sharp gullies & rocky ridges
            ApplyHydraulicErosion(65000);

            // Pass 3: Carve inland rivers & highland lakes gently (NO deep black pits!) and set Biome/Flora grids
            for (int gz = 0; gz < GridDepth; gz++)
            {
                for (int gx = 0; gx < GridWidth; gx++)
                {
                    int idx = gz * GridWidth + gx;
                    float h = _heightGrid[idx];
                    bool isInlandRiverOrLake = rawWaterMask[idx] > 0.38f && !isOceanConnected[idx];

                    _hasInlandWater[idx] = isInlandRiverOrLake;
                    _riverMaskGrid[idx] = rawWaterMask[idx];

                    if (isInlandRiverOrLake)
                    {
                        // Sample local surrounding bank height so river/lake sits naturally in its valley
                        float bankH = SampleLocalBankHeight(gx, gz, rawWaterMask);
                        float waterSurfaceY = MathF.Max(0.2f, bankH - 0.8f);
                        _inlandWaterYGrid[idx] = waterSurfaceY;
                        _heightGrid[idx] = waterSurfaceY - 2.0f; // Gentle 2m riverbed
                    }
                    else
                    {
                        _inlandWaterYGrid[idx] = SeaLevel;
                    }

                    float riverProximity = rawWaterMask[idx];
                    float coastal = FastNoise.SmoothStep(3.5f, -1.5f, _heightGrid[idx]);
                    float moisture = Math.Clamp(
                        0.42f + riverProximity * 0.50f + coastal * 0.18f
                        - _desertWeight[idx] * 0.34f - (_heightGrid[idx] / 120.0f) * 0.25f,
                        0.0f, 1.0f);
                    _moistureGrid[idx] = moisture;

                    float nx = gx / (float)(GridWidth - 1);
                    float nz = gz / (float)(GridDepth - 1);

                    if (_heightGrid[idx] < -3.6f) _biomeGrid[idx] = BiomeId.DeepOcean;
                    else if (_heightGrid[idx] < 0.7f) _biomeGrid[idx] = BiomeId.CoastalReef;
                    else if (nx > 0.80f && nz > 0.72f) _biomeGrid[idx] = BiomeId.SanctuaryIsland;
                    else if (_glacialWeight[idx] > 0.45f) _biomeGrid[idx] = BiomeId.GlacialAlpine;
                    else if (_desertWeight[idx] > 0.45f) _biomeGrid[idx] = BiomeId.TerracottaDesert;
                    else if (_autumnWeight[idx] > 0.45f) _biomeGrid[idx] = BiomeId.AutumnSteppe;
                    else _biomeGrid[idx] = BiomeId.PrimevalForest;

                    float altSuit = FastNoise.SmoothStep(1.2f, 3.5f, _heightGrid[idx])
                                  * (1.0f - FastNoise.SmoothStep(44.0f, 58.0f, _heightGrid[idx]));
                    float worldX = gx * CellSize;
                    float worldZ = gz * CellSize;
                    float groveNoise = FastNoise.Fbm2D(worldX * 0.0032f + 19.4f, worldZ * 0.0032f - 8.7f, Seed + 907, 4);
                    float regionalGrove = _biomeGrid[idx] switch
                    {
                        BiomeId.AutumnSteppe => FastNoise.SmoothStep(0.42f, 0.65f, groveNoise) * 0.78f,
                        BiomeId.GlacialAlpine => FastNoise.SmoothStep(0.34f, 0.62f, groveNoise) * 0.85f,
                        _ => forestFeature[idx],
                    };
                    _forestGrid[idx] = Math.Clamp(MathF.Max(regionalGrove, riverProximity * 0.70f) * altSuit, 0.0f, 1.0f);
                }
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

            // Seed flood-fill from all 4 outer borders
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

        private static float[] ComputeCoastDistance(float[] landMask, bool[] isOcean)
        {
            int count = GridWidth * GridDepth;
            float[] dist = new float[count];
            const float inf = 9999.0f;

            for (int i = 0; i < count; i++)
            {
                bool isLand = landMask[i] >= 0.45f;
                dist[i] = isLand ? inf : 0.0f;
            }

            // Forward pass
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

            // Backward pass
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

            // Negative distance for shallow coastal shelf outside land
            float[] oceanDist = new float[count];
            for (int i = 0; i < count; i++)
            {
                oceanDist[i] = landMask[i] >= 0.45f ? 0.0f : inf;
            }
            for (int z = 1; z < GridDepth; z++)
            {
                for (int x = 1; x < GridWidth - 1; x++)
                {
                    int idx = z * GridWidth + x;
                    if (oceanDist[idx] == 0.0f) continue;
                    float d = MathF.Min(oceanDist[idx], oceanDist[idx - 1] + 1.0f);
                    d = MathF.Min(d, oceanDist[idx - GridWidth] + 1.0f);
                    oceanDist[idx] = d;
                }
            }
            for (int z = GridDepth - 2; z >= 0; z--)
            {
                for (int x = GridWidth - 2; x >= 1; x--)
                {
                    int idx = z * GridWidth + x;
                    if (oceanDist[idx] == 0.0f) continue;
                    float d = MathF.Min(oceanDist[idx], oceanDist[idx + 1] + 1.0f);
                    d = MathF.Min(d, oceanDist[idx + GridWidth] + 1.0f);
                    oceanDist[idx] = d;
                }
            }

            for (int i = 0; i < count; i++)
            {
                if (landMask[i] < 0.45f)
                    dist[i] = -oceanDist[i];
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
            float tx = fx - x0;
            float ty = fy - y0;

            Color c00 = img.GetPixel(x0, y0);
            Color c10 = img.GetPixel(x1, y0);
            Color c01 = img.GetPixel(x0, y1);
            Color c11 = img.GetPixel(x1, y1);

            return c00.Lerp(c10, tx).Lerp(c01.Lerp(c11, tx), ty);
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
                float dirX = 0.0f;
                float dirZ = 0.0f;
                float speed = 1.0f;
                float water = 1.0f;
                float sediment = 0.0f;

                for (int step = 0; step < maxLifetime; step++)
                {
                    int nodeX = (int)posX;
                    int nodeZ = (int)posZ;
                    if (nodeX < 1 || nodeX >= GridWidth - 2 || nodeZ < 1 || nodeZ >= GridDepth - 2) break;

                    float cellOffsetX = posX - nodeX;
                    float cellOffsetZ = posZ - nodeZ;

                    int idx00 = nodeZ * GridWidth + nodeX;
                    float h00 = _heightGrid[idx00];
                    float h10 = _heightGrid[idx00 + 1];
                    float h01 = _heightGrid[idx00 + GridWidth];
                    float h11 = _heightGrid[idx00 + GridWidth + 1];

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
                    float u = posX - newX;
                    float v = posZ - newZ;
                    int nIdx = newZ * GridWidth + newX;
                    float newH = (_heightGrid[nIdx] * (1 - u) + _heightGrid[nIdx + 1] * u) * (1 - v)
                               + (_heightGrid[nIdx + GridWidth] * (1 - u) + _heightGrid[nIdx + GridWidth + 1] * u) * v;

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
                        _heightGrid[idx00 + GridWidth] += amountToDeposit * (1 - cellOffsetX) * cellOffsetZ;
                        _heightGrid[idx00 + GridWidth + 1] += amountToDeposit * cellOffsetX * cellOffsetZ;
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
                                if (tx < 0 || tx >= GridWidth || tz < 0 || tz >= GridDepth) continue;
                                float dist = MathF.Sqrt(bx * bx + bz * bz);
                                if (dist < brushRadius) totalWeight += brushRadius - dist;
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
            int x0 = (int)cx;
            int z0 = (int)cz;
            float tx = cx - x0;
            float tz = cz - z0;

            int idx = z0 * GridWidth + x0;
            float v00 = grid[idx];
            float v10 = grid[idx + 1];
            float v01 = grid[idx + GridWidth];
            float v11 = grid[idx + GridWidth + 1];

            return (v00 * (1 - tx) + v10 * tx) * (1 - tz) + (v01 * (1 - tx) + v11 * tx) * tz;
        }

        public bool HasInlandWaterAtCell(int gx, int gz) => _hasInlandWater[gz * GridWidth + gx];
        public float GetInlandWaterYAtCell(int gx, int gz) => _inlandWaterYGrid[gz * GridWidth + gx];

        public TerrainSample SamplePoint(float worldX, float worldZ)
        {
            if (worldX < 0.0f || worldX > RegionWidthMeters || worldZ < 0.0f || worldZ > RegionDepthMeters)
            {
                return new TerrainSample(-12.0f, 0.0f, SeaLevel, 1.0f, 1.0f, 0.0f, 0.35f, 1.0f, 0.0f, BiomeId.DeepOcean);
            }

            float gx = worldX / CellSize;
            float gz = worldZ / CellSize;

            float height = SampleBilinear(_heightGrid, gx, gz);
            float riverMask = SampleBilinear(_riverMaskGrid, gx, gz);
            float inlandWaterY = SampleBilinear(_inlandWaterYGrid, gx, gz);
            float moisture = SampleBilinear(_moistureGrid, gx, gz);
            float forest = SampleBilinear(_forestGrid, gx, gz);
            float coastalMask = FastNoise.SmoothStep(3.5f, -1.5f, height);

            int ix = Math.Clamp((int)MathF.Round(gx), 0, GridWidth - 1);
            int iz = Math.Clamp((int)MathF.Round(gz), 0, GridDepth - 1);
            BiomeId biome = _biomeGrid[iz * GridWidth + ix];

            // 1. TemperatureMap: cools northward (low Z) and with altitude (lapse rate)
            float latNorm = worldZ / RegionDepthMeters; // 0 = cold North, 1 = warm South
            float temp = Math.Clamp(0.32f + latNorm * 0.56f - MathF.Max(0.0f, height) / 95.0f * 0.68f
                                  + _desertWeight[iz * GridWidth + ix] * 0.24f
                                  - _glacialWeight[iz * GridWidth + ix] * 0.14f, 0.0f, 1.0f);

            // 2. CoastSaltExposureMap: strong near sea level & ocean-facing low shores
            float saltExposure = FastNoise.SmoothStep(4.2f, 0.2f, height) * (1.0f - riverMask * 0.75f);

            // 3. MegafaunaCorridorMap: winding open savanna/steppe game trails across flat lowlands
            float trailWave = FastNoise.GradientNoise2D(worldX * 0.0028f, worldZ * 0.0028f, Seed + 1231);
            float megafaunaCorridor = (1.0f - FastNoise.SmoothStep(0.0f, 0.14f, MathF.Abs(trailWave)))
                                    * FastNoise.SmoothStep(2.0f, 5.0f, height)
                                    * (1.0f - FastNoise.SmoothStep(22.0f, 34.0f, height));

            return new TerrainSample(height, riverMask, inlandWaterY, coastalMask, moisture, forest, temp, saltExposure, megafaunaCorridor, biome);
        }

        public float SampleHeight(float worldX, float worldZ) => SamplePoint(worldX, worldZ).Height;

        public Vector3 SampleNormal(float worldX, float worldZ, float eps = 2.5f)
        {
            float hL = SampleHeight(worldX - eps, worldZ);
            float hR = SampleHeight(worldX + eps, worldZ);
            float hD = SampleHeight(worldX, worldZ - eps);
            float hU = SampleHeight(worldX, worldZ + eps);
            return new Vector3(hL - hR, 2.0f * eps, hD - hU).Normalized();
        }

        public ImageTexture BuildBiomeSplatTexture()
        {
            byte[] data = new byte[GridWidth * GridDepth * 4];
            for (int i = 0; i < GridWidth * GridDepth; i++)
            {
                int o = i * 4;
                data[o + 0] = (byte)(Math.Clamp(_autumnWeight[i], 0.0f, 1.0f) * 255.0f);
                data[o + 1] = (byte)(Math.Clamp(_desertWeight[i], 0.0f, 1.0f) * 255.0f);
                data[o + 2] = (byte)(Math.Clamp(_glacialWeight[i], 0.0f, 1.0f) * 255.0f);
                data[o + 3] = (byte)(Math.Clamp(_forestGrid[i], 0.0f, 1.0f) * 255.0f);
            }

            Image img = Image.CreateFromData(GridWidth, GridDepth, false, Image.Format.Rgba8, data);
            return ImageTexture.CreateFromImage(img);
        }

        public ImageTexture BuildWorldMapTexture()
        {
            if (_blueprintCropped != null)
            {
                return ImageTexture.CreateFromImage(_blueprintCropped);
            }
            return BuildBiomeSplatTexture();
        }
    }
}
