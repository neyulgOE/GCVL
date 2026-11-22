using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Godot;
using PrimevalWorld.Core;

namespace PrimevalWorld.WorldGen
{
    /// <summary>
    /// Stage 1A: Tectonic 4-Continent Layout Generator (9600m x 5400m, 1025x577 vertices).
    /// Preserves 100% of the canonical 4-continent blueprint (NW Glacial + Fjords, SW Terracotta + Oasis,
    /// East Primeval Forest + NE Autumn Steppes + Crescent Bay + Delta, SE Sanctuary Archipelago)
    /// while separating BedrockHeight and SedimentDepth for physical erosion.
    /// </summary>
    public sealed class TectonicContinentGen
    {
        private const int W = WorldPhysicsConfig.VertW;
        private const int H = WorldPhysicsConfig.VertH;
        private const float Cell = WorldPhysicsConfig.CellSize;

        public float[] BedrockHeight { get; } = new float[W * H];
        public float[] SedimentDepth { get; } = new float[W * H];
        public float[] LandMask { get; } = new float[W * H];
        public float[] RawWaterMask { get; } = new float[W * H];
        public bool[] IsOceanConnected { get; private set; } = new bool[W * H];
        public float[] CoastDistMeters { get; private set; } = new float[W * H];

        public float[] NwGlacialWeight { get; } = new float[W * H];
        public float[] SwDesertWeight { get; } = new float[W * H];
        public float[] NeAutumnWeight { get; } = new float[W * H];
        public float[] ForestFeature { get; } = new float[W * H];

        private Image? _blueprintCropped;

        public Image? BlueprintImage => _blueprintCropped;

        public TectonicContinentGen()
        {
            LoadBlueprintImage();
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

        public void Generate(int seed)
        {
            int count = W * H;
            float[] snowFeature = new float[count];
            float[] ridgeFeature = new float[count];

            if (_blueprintCropped != null)
            {
                int bw = _blueprintCropped.GetWidth();
                int bh = _blueprintCropped.GetHeight();

                // Read blueprint into fast byte array so Parallel.For is thread-safe
                byte[] imgBytes = _blueprintCropped.GetData();
                int channels = _blueprintCropped.GetFormat() == Image.Format.Rgba8 ? 4 : 3;

                Parallel.For(0, H, gz =>
                {
                    float fy = (gz / (float)(H - 1)) * (bh - 1);
                    float nz = gz / (float)(H - 1);
                    int y0 = Math.Clamp((int)fy, 0, bh - 1);
                    int y1 = Math.Min(bh - 1, y0 + 1);
                    float ty = fy - y0;

                    for (int gx = 0; gx < W; gx++)
                    {
                        float fx = (gx / (float)(W - 1)) * (bw - 1);
                        float nx = gx / (float)(W - 1);
                        int x0 = Math.Clamp((int)fx, 0, bw - 1);
                        int x1 = Math.Min(bw - 1, x0 + 1);
                        float tx = fx - x0;

                        Color c00 = ReadPixel(imgBytes, bw, channels, x0, y0);
                        Color c10 = ReadPixel(imgBytes, bw, channels, x1, y0);
                        Color c01 = ReadPixel(imgBytes, bw, channels, x0, y1);
                        Color c11 = ReadPixel(imgBytes, bw, channels, x1, y1);
                        Color c = c00.Lerp(c10, tx).Lerp(c01.Lerp(c11, tx), ty);

                        int idx = gz * W + gx;
                        float r = c.R, g = c.G, b = c.B;
                        float brightness = (r + g + b) / 3.0f;
                        float sat = MathF.Max(r, MathF.Max(g, b)) - MathF.Min(r, MathF.Min(g, b));

                        bool isDeepOcean = (b > r + 0.12f) && (b > 0.23f) && (g < 0.43f) && (r < 0.20f);
                        bool isReef = (g > 0.48f) && (b > 0.56f) && (r < 0.36f);
                        bool isInlandWater = (b > r + 0.06f) && (b > 0.28f) && (r < 0.42f) && !isDeepOcean && !isReef;
                        bool isWater = isDeepOcean || isReef || isInlandWater;

                        LandMask[idx] = isWater ? 0.0f : 1.0f;
                        RawWaterMask[idx] = isInlandWater ? 1.0f : 0.0f;

                        NwGlacialWeight[idx] = (1.0f - FastNoise.SmoothStep(0.42f, 0.52f, nx))
                                             * (1.0f - FastNoise.SmoothStep(0.42f, 0.52f, nz));
                        SwDesertWeight[idx] = (1.0f - FastNoise.SmoothStep(0.40f, 0.50f, nx))
                                            * FastNoise.SmoothStep(0.43f, 0.52f, nz);
                        NeAutumnWeight[idx] = FastNoise.SmoothStep(0.50f, 0.58f, nx)
                                            * (1.0f - FastNoise.SmoothStep(0.38f, 0.49f, nz));

                        bool isSnow = !isWater && brightness > 0.56f && sat < 0.20f && nx < 0.48f && nz < 0.46f;
                        snowFeature[idx] = isSnow ? 1.0f : 0.0f;

                        bool isRidge = !isWater && ((SwDesertWeight[idx] > 0.5f && g > 0.35f && r < 0.72f) || isSnow);
                        ridgeFeature[idx] = isRidge ? 1.0f : 0.0f;

                        bool isForestGreen = !isWater && (g > r + 0.02f) && (g > b + 0.04f) && (g < 0.42f);
                        ForestFeature[idx] = isForestGreen ? 1.0f : 0.0f;
                    }
                });
            }

            SmoothGrid(LandMask, 2);
            SmoothGrid(snowFeature, 3);
            SmoothGrid(ridgeFeature, 4);
            SmoothGrid(ForestFeature, 2);
            SmoothGrid(RawWaterMask, 1);

            IsOceanConnected = FloodFillOcean(LandMask);
            CoastDistMeters = ComputeCoastDistanceMeters(LandMask);

            // Synthesize BedrockHeight & initial SedimentDepth on 9600m x 5400m scale
            Parallel.For(0, H, gz =>
            {
                float worldZ = gz * Cell;
                float nz = gz / (float)(H - 1);
                for (int gx = 0; gx < W; gx++)
                {
                    float worldX = gx * Cell;
                    float nx = gx / (float)(W - 1);
                    int idx = gz * W + gx;

                    float land = LandMask[idx];
                    float dMeters = CoastDistMeters[idx];

                    float fbm = FastNoise.Fbm2D(worldX * 0.00085f, worldZ * 0.00085f, seed + 101, 5);
                    float ridged = MathF.Pow(FastNoise.RidgedFbm2D(worldX * 0.0011f, worldZ * 0.0011f, seed + 307, 6), 1.15f);
                    float micro = (FastNoise.Fbm2D(worldX * 0.005f, worldZ * 0.005f, seed + 173, 3) - 0.5f) * 4.0f;

                    // Gentle coastal beach ramp (0.6..7.0m) rising to broad lowland plains (10..55m)
                    float beachRamp = FastNoise.SmoothStep(0.0f, 95.0f, dMeters);
                    float inlandRamp = FastNoise.SmoothStep(70.0f, 360.0f, dMeters);
                    float baseLandH = 0.8f + beachRamp * 7.5f + beachRamp * (inlandRamp * 32.0f + fbm * 22.0f) + micro * 0.5f;

                    // NW Glacial Alpine peaks up to ~440-460m
                    float nwLift = snowFeature[idx] * (125.0f + ridged * 285.0f);

                    // SW Terracotta: weathered sandstone mesas (bedrock) + deep loose sand (sediment)
                    float swMesa = fbm * 42.0f + MathF.Pow(ridged, 1.7f) * 28.0f;
                    float swRim = SwDesertWeight[idx] * ridgeFeature[idx] * (18.0f + swMesa);

                    // NE Autumn Steppes rolling plateau (45-135m)
                    float nePlateau = NeAutumnWeight[idx] * (28.0f + fbm * 34.0f + MathF.Pow(ridged, 1.4f) * 45.0f);

                    // East Primeval Crescent forest ridge (40-110m)
                    float eastRidge = (nx > 0.52f && nz > 0.45f) ? ForestFeature[idx] * MathF.Pow(ridged, 1.3f) * 44.0f : 0.0f;

                    float totalBedrock = baseLandH + nwLift + swRim + nePlateau + eastRidge;

                    // Shallow coral shelf (-2.4m..0m) -> Deep ocean (-65m)
                    float shelfT = FastNoise.SmoothStep(0.0f, 180.0f, -dMeters);
                    float oceanFloor = Mathf.Lerp(-2.4f, WorldPhysicsConfig.MaxOceanDepth, shelfT) + fbm * 3.0f;

                    float landBlend = FastNoise.SmoothStep(0.24f, 0.56f, land);
                    BedrockHeight[idx] = oceanFloor * (1.0f - landBlend) + totalBedrock * landBlend;

                    // Initial loose sediment cover (thick sand in SW desert, moderate loam in valleys, thin on peaks)
                    float swSand = SwDesertWeight[idx] * landBlend * (14.0f + fbm * 18.0f);
                    float valleyLoam = landBlend * (1.0f - snowFeature[idx]) * (2.5f + fbm * 4.5f);
                    SedimentDepth[idx] = swSand + valleyLoam;
                }
            });
        }

        private static Color ReadPixel(byte[] data, int w, int ch, int x, int y)
        {
            int o = (y * w + x) * ch;
            return new Color(data[o] / 255.0f, data[o + 1] / 255.0f, data[o + 2] / 255.0f);
        }

        private static bool[] FloodFillOcean(float[] landMask)
        {
            int count = W * H;
            bool[] ocean = new bool[count];
            var queue = new Queue<int>(32768);

            for (int x = 0; x < W; x++) { TryEnqueue(x, 0); TryEnqueue(x, H - 1); }
            for (int z = 0; z < H; z++) { TryEnqueue(0, z); TryEnqueue(W - 1, z); }

            void TryEnqueue(int x, int z)
            {
                int idx = z * W + x;
                if (!ocean[idx] && landMask[idx] < 0.45f)
                {
                    ocean[idx] = true;
                    queue.Enqueue(idx);
                }
            }

            while (queue.Count > 0)
            {
                int cur = queue.Dequeue();
                int cx = cur % W;
                int cz = cur / W;
                if (cx > 0) TryEnqueue(cx - 1, cz);
                if (cx < W - 1) TryEnqueue(cx + 1, cz);
                if (cz > 0) TryEnqueue(cx, cz - 1);
                if (cz < H - 1) TryEnqueue(cx, cz + 1);
            }
            return ocean;
        }

        private static float[] ComputeCoastDistanceMeters(float[] landMask)
        {
            int count = W * H;
            float[] dist = new float[count];
            const float inf = 9999.0f;

            for (int i = 0; i < count; i++) dist[i] = landMask[i] >= 0.45f ? inf : 0.0f;

            for (int z = 1; z < H; z++)
                for (int x = 1; x < W - 1; x++)
                {
                    int idx = z * W + x;
                    if (dist[idx] == 0.0f) continue;
                    float d = MathF.Min(dist[idx], dist[idx - 1] + 1.0f);
                    d = MathF.Min(d, dist[idx - W] + 1.0f);
                    d = MathF.Min(d, dist[idx - W - 1] + 1.414f);
                    d = MathF.Min(d, dist[idx - W + 1] + 1.414f);
                    dist[idx] = d;
                }

            for (int z = H - 2; z >= 0; z--)
                for (int x = W - 2; x >= 1; x--)
                {
                    int idx = z * W + x;
                    if (dist[idx] == 0.0f) continue;
                    float d = MathF.Min(dist[idx], dist[idx + 1] + 1.0f);
                    d = MathF.Min(d, dist[idx + W] + 1.0f);
                    d = MathF.Min(d, dist[idx + W + 1] + 1.414f);
                    d = MathF.Min(d, dist[idx + W - 1] + 1.414f);
                    dist[idx] = d;
                }

            float[] oceanDist = new float[count];
            for (int i = 0; i < count; i++) oceanDist[i] = landMask[i] >= 0.45f ? 0.0f : inf;

            for (int z = 1; z < H; z++)
                for (int x = 1; x < W - 1; x++)
                {
                    int idx = z * W + x;
                    if (oceanDist[idx] == 0.0f) continue;
                    oceanDist[idx] = MathF.Min(oceanDist[idx], MathF.Min(oceanDist[idx - 1], oceanDist[idx - W]) + 1.0f);
                }

            for (int z = H - 2; z >= 0; z--)
                for (int x = W - 2; x >= 1; x--)
                {
                    int idx = z * W + x;
                    if (oceanDist[idx] == 0.0f) continue;
                    oceanDist[idx] = MathF.Min(oceanDist[idx], MathF.Min(oceanDist[idx + 1], oceanDist[idx + W]) + 1.0f);
                }

            for (int i = 0; i < count; i++)
                dist[i] = (landMask[i] < 0.45f ? -oceanDist[i] : dist[i]) * Cell;

            return dist;
        }

        private static void SmoothGrid(float[] grid, int passes)
        {
            float[] tmp = new float[grid.Length];
            for (int p = 0; p < passes; p++)
            {
                Parallel.For(1, H - 1, z =>
                {
                    for (int x = 1; x < W - 1; x++)
                    {
                        int idx = z * W + x;
                        tmp[idx] = (grid[idx] * 4.0f + grid[idx - 1] + grid[idx + 1] + grid[idx - W] + grid[idx + W]) / 8.0f;
                    }
                });
                Array.Copy(tmp, grid, grid.Length);
            }
        }
    }
}
