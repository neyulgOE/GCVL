using System;
using Godot;

namespace PrimevalWorld.Flora
{
    /// <summary>
    /// Generates crisp procedural 512x512 Alpha-Cutout Leaf Cluster Atlas (4 quadrants)
    /// and 256x256 Procedural Bark Texture at startup so trees never look like solid PS1 blobs.
    /// Quadrants:
    ///   (0,0) UV [0..0.5, 0..0.5]: Serrated Broadleaf cluster
    ///   (1,0) UV [0.5..1, 0..0.5]: Conifer Needle spray
    ///   (0,1) UV [0..0.5, 0.5..1]: Acacia / Baobab fine leaflet spray
    ///   (1,1) UV [0.5..1, 0.5..1]: Palm / Tree Fern pinnate frond
    /// </summary>
    public static class FloraTextureAtlas
    {
        public static ImageTexture BuildLeafAtlasTexture()
        {
            const int size = 512;
            const int half = 256;
            byte[] rgba = new byte[size * size * 4];
            var rng = new Random(1337);

            // Quadrant 0 (Top-Left): Broadleaf clusters
            StampLeafCluster(rgba, size, 0, 0, half, 46, leafW: 34f, leafH: 48f, rng);
            // Quadrant 1 (Top-Right): Conifer needles
            StampConiferSpray(rgba, size, half, 0, half, rng);
            // Quadrant 2 (Bottom-Left): Fine acacia/desert leaflets
            StampLeafCluster(rgba, size, 0, half, half, 72, leafW: 18f, leafH: 26f, rng);
            // Quadrant 3 (Bottom-Right): Palm / Fern pinnate frond
            StampPinnateFrond(rgba, size, half, half, half, rng);

            var img = Image.CreateFromData(size, size, false, Image.Format.Rgba8, rgba);
            img.GenerateMipmaps();
            return ImageTexture.CreateFromImage(img);
        }

        public static ImageTexture BuildBarkTexture()
        {
            const int size = 256;
            byte[] rgb = new byte[size * size * 3];
            for (int y = 0; y < size; y++)
            {
                for (int x = 0; x < size; x++)
                {
                    float u = x / (float)size;
                    float v = y / (float)size;
                    // Vertical furrowed bark ridges + fine cross-grain
                    float ridge = MathF.Sin(u * Mathf.Tau * 10.0f + MathF.Sin(v * Mathf.Tau * 3.0f) * 1.4f) * 0.5f + 0.5f;
                    float crack = MathF.Abs(MathF.Sin(u * Mathf.Tau * 22.0f + v * 6.0f));
                    float grain = MathF.Sin(v * Mathf.Tau * 28.0f + u * 8.0f) * 0.12f;
                    float val = Math.Clamp(0.48f + ridge * 0.34f - (1.0f - crack) * 0.18f + grain, 0.18f, 0.96f);

                    int o = (y * size + x) * 3;
                    rgb[o + 0] = (byte)(val * 245.0f);
                    rgb[o + 1] = (byte)(val * 225.0f);
                    rgb[o + 2] = (byte)(val * 205.0f);
                }
            }
            var img = Image.CreateFromData(size, size, false, Image.Format.Rgb8, rgb);
            img.GenerateMipmaps();
            return ImageTexture.CreateFromImage(img);
        }

        private static void StampLeafCluster(byte[] rgba, int stride, int ox, int oy, int qSize, int count, float leafW, float leafH, Random rng)
        {
            for (int i = 0; i < count; i++)
            {
                float ang = (float)(rng.NextDouble() * Mathf.Tau);
                float dist = (float)Math.Sqrt(rng.NextDouble()) * (qSize * 0.34f);
                float cx = ox + qSize * 0.5f + MathF.Cos(ang) * dist;
                float cy = oy + qSize * 0.5f + MathF.Sin(ang) * dist;
                float rot = ang + (float)(rng.NextDouble() - 0.5) * 0.9f;
                float shade = 0.72f + (float)rng.NextDouble() * 0.28f;
                DrawLeafShape(rgba, stride, ox, oy, qSize, cx, cy, leafW * (0.75f + (float)rng.NextDouble() * 0.45f),
                    leafH * (0.75f + (float)rng.NextDouble() * 0.45f), rot, shade);
            }
        }

        private static void StampConiferSpray(byte[] rgba, int stride, int ox, int oy, int qSize, Random rng)
        {
            for (int b = 0; b < 56; b++)
            {
                float t = b / 55.0f;
                float cy = oy + 26.0f + t * (qSize - 52.0f);
                float side = (b % 2 == 0) ? 1.0f : -1.0f;
                float cx = ox + qSize * 0.5f + side * (12.0f + (1.0f - t) * 44.0f) * (0.5f + (float)rng.NextDouble() * 0.6f);
                float rot = side * (0.65f + (float)rng.NextDouble() * 0.45f);
                float shade = 0.70f + (float)rng.NextDouble() * 0.30f;
                DrawLeafShape(rgba, stride, ox, oy, qSize, cx, cy, 8.0f, 38.0f, rot, shade);
            }
        }

        private static void StampPinnateFrond(byte[] rgba, int stride, int ox, int oy, int qSize, Random rng)
        {
            // Central rachis + 28 paired leaflets
            for (int p = 0; p < 28; p++)
            {
                float t = p / 27.0f;
                float cy = oy + 22.0f + t * (qSize - 44.0f);
                float span = MathF.Sin(t * MathF.PI) * 84.0f + 16.0f;
                for (int side = -1; side <= 1; side += 2)
                {
                    float cx = ox + qSize * 0.5f + side * span * 0.5f;
                    float rot = side * (1.15f - t * 0.35f);
                    float shade = 0.74f + (float)rng.NextDouble() * 0.26f;
                    DrawLeafShape(rgba, stride, ox, oy, qSize, cx, cy, 11.0f, span * 0.55f, rot, shade);
                }
            }
        }

        private static void DrawLeafShape(
            byte[] rgba, int stride, int minX, int minY, int qSize,
            float cx, float cy, float w, float h, float rot, float shade)
        {
            float cos = MathF.Cos(rot), sin = MathF.Sin(rot);
            int rad = (int)MathF.Ceiling(MathF.Max(w, h) * 0.75f);
            int x0 = Math.Max(minX + 2, (int)(cx - rad));
            int x1 = Math.Min(minX + qSize - 3, (int)(cx + rad));
            int y0 = Math.Max(minY + 2, (int)(cy - rad));
            int y1 = Math.Min(minY + qSize - 3, (int)(cy + rad));

            for (int y = y0; y <= y1; y++)
            {
                for (int x = x0; x <= x1; x++)
                {
                    float dx = x - cx, dy = y - cy;
                    float lx = (dx * cos + dy * sin) / (w * 0.5f);
                    float ly = (-dx * sin + dy * cos) / (h * 0.5f);
                    // Pointed ovate leaf silhouette
                    float pinch = 1.0f - MathF.Abs(ly) * 0.45f;
                    float d = (lx / MathF.Max(0.15f, pinch)) * (lx / MathF.Max(0.15f, pinch)) + ly * ly;
                    if (d <= 1.0f)
                    {
                        float edge = Math.Clamp((1.0f - d) * 3.5f, 0.0f, 1.0f);
                        float midrib = 1.0f - FastNoiseSmooth(MathF.Abs(lx) * 6.0f) * 0.10f;
                        byte col = (byte)(Math.Clamp(shade * midrib * (0.85f + 0.15f * edge), 0.3f, 1.0f) * 255.0f);
                        int o = (y * stride + x) * 4;
                        rgba[o + 0] = col;
                        rgba[o + 1] = col;
                        rgba[o + 2] = col;
                        rgba[o + 3] = 255;
                    }
                }
            }
        }

        private static float FastNoiseSmooth(float t)
        {
            float c = Math.Clamp(t, 0.0f, 1.0f);
            return c * c * (3.0f - 2.0f * c);
        }
    }
}
