using System;
using System.Collections.Generic;
using Godot;

namespace PrimevalWorld.Flora
{
    /// <summary>
    /// Generates clean, high-transparency (>= 58% alpha==0) Botanical Leaf & Bark PNG textures
    /// into res://assets/textures/flora/ at startup so leaves show crisp serrated twigs & fronds
    /// instead of solid green squares.
    /// </summary>
    public static class BotanicalTextureGenerator
    {
        public sealed class BotanicalTextures
        {
            public ImageTexture BroadleafTex { get; set; } = null!;
            public ImageTexture ConiferTex { get; set; } = null!;
            public ImageTexture AcaciaTex { get; set; } = null!;
            public ImageTexture PalmFernTex { get; set; } = null!;
            public ImageTexture BarkRoughTex { get; set; } = null!;
            public ImageTexture BarkPaleTex { get; set; } = null!;
            public Dictionary<string, float> TransparentPercent { get; } = new();
            public Dictionary<string, int> BorderOpaquePixels { get; } = new();
        }

        private static BotanicalTextures? _cached;

        public static BotanicalTextures EnsureAndLoadAll()
        {
            if (_cached != null) return _cached;

            const string dir = "assets/textures/flora";
            DirAccess.MakeDirRecursiveAbsolute(ProjectSettings.GlobalizePath($"res://{dir}"));
            DirAccess.MakeDirRecursiveAbsolute(ProjectSettings.GlobalizePath("res://debug_outputs"));

            var res = new BotanicalTextures();
            res.BroadleafTex = GenerateLeafPng($"{dir}/leaf_broadleaf.png", 512, 0, res.TransparentPercent, res.BorderOpaquePixels, out byte[] bBytes);
            res.ConiferTex = GenerateLeafPng($"{dir}/leaf_conifer.png", 512, 1, res.TransparentPercent, res.BorderOpaquePixels, out byte[] cBytes);
            res.AcaciaTex = GenerateLeafPng($"{dir}/leaf_acacia.png", 512, 2, res.TransparentPercent, res.BorderOpaquePixels, out byte[] aBytes);
            res.PalmFernTex = GenerateLeafPng($"{dir}/leaf_palm_fern.png", 512, 3, res.TransparentPercent, res.BorderOpaquePixels, out byte[] pBytes);
            res.BarkRoughTex = GenerateBarkPng($"{dir}/bark_rough.png", 256, pale: false);
            res.BarkPaleTex = GenerateBarkPng($"{dir}/bark_pale.png", 256, pale: true);

            SaveCompositeCheckPng("debug_outputs/leaf_atlas_check.png", 512, bBytes, cBytes, aBytes, pBytes);

            _cached = res;
            return res;
        }

        private static void SaveCompositeCheckPng(string relPath, int qSize, byte[] b, byte[] c, byte[] a, byte[] p)
        {
            int full = qSize * 2;
            byte[] comp = new byte[full * full * 4];
            BlitQuad(b, comp, qSize, full, 0, 0);
            BlitQuad(c, comp, qSize, full, qSize, 0);
            BlitQuad(a, comp, qSize, full, 0, qSize);
            BlitQuad(p, comp, qSize, full, qSize, qSize);
            var img = Image.CreateFromData(full, full, false, Image.Format.Rgba8, comp);
            img.SavePng(ProjectSettings.GlobalizePath($"res://{relPath}"));
        }

        private static void BlitQuad(byte[] src, byte[] dst, int qSize, int dstW, int ox, int oy)
        {
            for (int y = 0; y < qSize; y++)
                Buffer.BlockCopy(src, y * qSize * 4, dst, ((oy + y) * dstW + ox) * 4, qSize * 4);
        }

        private static ImageTexture GenerateLeafPng(
            string relPath, int size, int style,
            Dictionary<string, float> stats, Dictionary<string, int> borderStats, out byte[] outBytes)
        {
            byte[] rgba = new byte[size * size * 4]; // Starts 100% transparent (alpha = 0)
            var rng = new Random(2026 + style * 97);

            if (style == 0) // Broadleaf: central woody twig + 20 distinct serrated ovate leaves (target 60-72% transparent)
            {
                DrawTwigLine(rgba, size, size * 0.5f, size * 0.94f, size * 0.5f, size * 0.14f, 5.0f, new Color(0.32f, 0.23f, 0.14f));
                for (int i = 0; i < 20; i++)
                {
                    float t = 0.16f + (i / 19.0f) * 0.74f;
                    float side = (i % 2 == 0) ? 1.0f : -1.0f;
                    float stemX = size * 0.5f + MathF.Sin(t * 4.0f) * 8.0f;
                    float stemY = size * (0.92f - t * 0.78f);
                    float ang = side * (0.55f + (1.0f - t) * 0.45f) + (float)(rng.NextDouble() - 0.5) * 0.25f;
                    float len = 82.0f + (1.0f - MathF.Abs(t - 0.5f)) * 52.0f;
                    float wid = len * 0.56f;
                    float tipX = stemX + MathF.Sin(ang) * len;
                    float tipY = stemY - MathF.Cos(ang) * len;
                    DrawTwigLine(rgba, size, stemX, stemY, tipX, tipY, 2.5f, new Color(0.35f, 0.26f, 0.16f));
                    DrawSerratedLeaf(rgba, size, (stemX + tipX) * 0.5f, (stemY + tipY) * 0.5f, wid, len * 0.92f, ang, 0.78f + (float)rng.NextDouble() * 0.22f);
                }
                DrawSerratedLeaf(rgba, size, size * 0.5f, size * 0.13f, 48f, 88f, 0.0f, 0.95f);
            }
            else if (style == 1) // Conifer: central branchlet + fine radiating needle sprays
            {
                DrawTwigLine(rgba, size, size * 0.5f, size * 0.95f, size * 0.5f, size * 0.08f, 4.0f, new Color(0.30f, 0.20f, 0.12f));
                for (int s = 0; s < 5; s++)
                {
                    float st = s / 4.0f;
                    float baseY = size * (0.86f - st * 0.68f);
                    for (int side = -1; side <= 1; side += 2)
                    {
                        float subLen = (1.0f - st * 0.45f) * 145.0f;
                        float endX = size * 0.5f + side * subLen * 0.85f;
                        float endY = baseY - subLen * 0.52f;
                        DrawTwigLine(rgba, size, size * 0.5f, baseY, endX, endY, 2.2f, new Color(0.32f, 0.22f, 0.14f));
                        for (int n = 0; n < 22; n++)
                        {
                            float nt = n / 21.0f;
                            float nx = Mathf.Lerp(size * 0.5f, endX, nt);
                            float ny = Mathf.Lerp(baseY, endY, nt);
                            float nAng = side * (0.45f + (float)rng.NextDouble() * 0.8f) - 0.35f;
                            DrawNeedle(rgba, size, nx, ny, 3.8f, 36.0f + (1.0f - nt) * 14.0f, nAng, 0.72f + (float)rng.NextDouble() * 0.28f);
                        }
                    }
                }
            }
            else if (style == 2) // Acacia / Desert: airy delicate bipinnate leaflets
            {
                DrawTwigLine(rgba, size, size * 0.5f, size * 0.94f, size * 0.5f, size * 0.16f, 3.5f, new Color(0.38f, 0.28f, 0.20f));
                for (int b = 0; b < 6; b++)
                {
                    float t = b / 5.0f;
                    float side = (b % 2 == 0) ? 1.0f : -1.0f;
                    float sy = size * (0.84f - t * 0.62f);
                    float ex = size * 0.5f + side * (110.0f + (1.0f - t) * 45.0f);
                    float ey = sy - 55.0f;
                    DrawTwigLine(rgba, size, size * 0.5f, sy, ex, ey, 1.8f, new Color(0.38f, 0.28f, 0.20f));
                    for (int l = 0; l < 12; l++)
                    {
                        float lt = 0.2f + (l / 11.0f) * 0.8f;
                        float lx = Mathf.Lerp(size * 0.5f, ex, lt) + (float)(rng.NextDouble() - 0.5) * 24f;
                        float ly = Mathf.Lerp(sy, ey, lt) + (float)(rng.NextDouble() - 0.5) * 24f;
                        DrawSerratedLeaf(rgba, size, lx, ly, 14f, 24f, (float)rng.NextDouble() * 3.14f, 0.75f + (float)rng.NextDouble() * 0.25f);
                    }
                }
            }
            else // Style 3: Palm / Tree Fern pinnate frond with crisp separated pinnae
            {
                DrawTwigLine(rgba, size, size * 0.5f, size * 0.95f, size * 0.5f, size * 0.06f, 4.5f, new Color(0.36f, 0.34f, 0.18f));
                for (int p = 0; p < 18; p++)
                {
                    float t = p / 17.0f;
                    float py = size * (0.88f - t * 0.76f);
                    float span = MathF.Sin(0.15f + t * 2.65f) * 165.0f + 22.0f;
                    for (int side = -1; side <= 1; side += 2)
                    {
                        float ang = side * (1.28f - t * 0.45f);
                        float cx = size * 0.5f + side * span * 0.52f;
                        float cy = py - MathF.Cos(ang) * span * 0.45f;
                        DrawNeedle(rgba, size, cx, cy, 13.0f, span * 0.92f, ang, 0.76f + (float)rng.NextDouble() * 0.24f);
                    }
                }
            }

            // Ensure 4px outer border is 100% transparent (alpha == 0)
            for (int y = 0; y < size; y++)
                for (int x = 0; x < size; x++)
                    if (x < 4 || x >= size - 4 || y < 4 || y >= size - 4)
                        rgba[(y * size + x) * 4 + 3] = 0;

            int transparentCount = 0;
            int borderOpaque = 0;
            for (int y = 0; y < size; y++)
                for (int x = 0; x < size; x++)
                {
                    byte a = rgba[(y * size + x) * 4 + 3];
                    if (a < 128) transparentCount++;
                    if ((x == 0 || x == size - 1 || y == 0 || y == size - 1) && a >= 128)
                        borderOpaque++;
                }
            stats[relPath] = transparentCount * 100.0f / (size * size);
            borderStats[relPath] = borderOpaque;
            outBytes = rgba;

            var img = Image.CreateFromData(size, size, false, Image.Format.Rgba8, rgba);
            img.SavePng(ProjectSettings.GlobalizePath($"res://{relPath}"));
            img.GenerateMipmaps();
            return ImageTexture.CreateFromImage(img);
        }

        private static ImageTexture GenerateBarkPng(string relPath, int size, bool pale)
        {
            byte[] rgb = new byte[size * size * 3];
            for (int y = 0; y < size; y++)
            {
                for (int x = 0; x < size; x++)
                {
                    float u = x / (float)size;
                    float v = y / (float)size;
                    float ridge = MathF.Sin(u * Mathf.Tau * 12.0f + MathF.Sin(v * Mathf.Tau * 2.0f) * 1.5f) * 0.5f + 0.5f;
                    float crack = MathF.Abs(MathF.Sin(u * Mathf.Tau * 24.0f + v * 5.0f));
                    float grain = MathF.Sin(v * Mathf.Tau * 32.0f + u * 6.0f) * 0.10f;
                    float val = pale
                        ? Math.Clamp(0.68f + ridge * 0.20f - (1.0f - crack) * 0.14f + grain, 0.42f, 0.96f)
                        : Math.Clamp(0.45f + ridge * 0.34f - (1.0f - crack) * 0.20f + grain, 0.18f, 0.92f);

                    int o = (y * size + x) * 3;
                    rgb[o + 0] = (byte)(val * (pale ? 248f : 235f));
                    rgb[o + 1] = (byte)(val * (pale ? 242f : 212f));
                    rgb[o + 2] = (byte)(val * (pale ? 230f : 188f));
                }
            }
            var img = Image.CreateFromData(size, size, false, Image.Format.Rgb8, rgb);
            img.SavePng(ProjectSettings.GlobalizePath($"res://{relPath}"));
            img.GenerateMipmaps();
            return ImageTexture.CreateFromImage(img);
        }

        private static void DrawTwigLine(byte[] rgba, int size, float x0, float y0, float x1, float y1, float thick, Color col)
        {
            int steps = (int)MathF.Ceiling(MathF.Sqrt((x1 - x0) * (x1 - x0) + (y1 - y0) * (y1 - y0)));
            int rad = (int)MathF.Ceiling(thick);
            for (int s = 0; s <= steps; s++)
            {
                float t = steps > 0 ? s / (float)steps : 0f;
                float cx = Mathf.Lerp(x0, x1, t);
                float cy = Mathf.Lerp(y0, y1, t);
                for (int dy = -rad; dy <= rad; dy++)
                    for (int dx = -rad; dx <= rad; dx++)
                    {
                        if (dx * dx + dy * dy > thick * thick) continue;
                        int px = Math.Clamp((int)(cx + dx), 1, size - 2);
                        int py = Math.Clamp((int)(cy + dy), 1, size - 2);
                        int o = (py * size + px) * 4;
                        rgba[o + 0] = (byte)(col.R * 255);
                        rgba[o + 1] = (byte)(col.G * 255);
                        rgba[o + 2] = (byte)(col.B * 255);
                        rgba[o + 3] = 255;
                    }
            }
        }

        private static void DrawSerratedLeaf(byte[] rgba, int size, float cx, float cy, float w, float h, float rot, float shade)
        {
            float cos = MathF.Cos(rot), sin = MathF.Sin(rot);
            int rad = (int)MathF.Ceiling(MathF.Max(w, h) * 0.72f);
            int x0 = Math.Max(4, (int)(cx - rad));
            int x1 = Math.Min(size - 5, (int)(cx + rad));
            int y0 = Math.Max(4, (int)(cy - rad));
            int y1 = Math.Min(size - 5, (int)(cy + rad));

            for (int y = y0; y <= y1; y++)
            {
                for (int x = x0; x <= x1; x++)
                {
                    float dx = x - cx, dy = y - cy;
                    float lx = (dx * cos + dy * sin) / (w * 0.5f);
                    float ly = (-dx * sin + dy * cos) / (h * 0.5f);
                    float serration = 1.0f + 0.10f * MathF.Sin(ly * 18.0f);
                    float pinch = (1.0f - MathF.Abs(ly) * 0.48f) * serration;
                    float d = (lx / MathF.Max(0.12f, pinch)) * (lx / MathF.Max(0.12f, pinch)) + ly * ly;
                    if (d <= 1.0f)
                    {
                        float midrib = MathF.Abs(lx) < 0.08f ? 1.12f : 1.0f;
                        byte v = (byte)(Math.Clamp(shade * midrib * (0.84f + 0.16f * (1.0f - d)), 0.35f, 1.0f) * 255f);
                        int o = (y * size + x) * 4;
                        rgba[o + 0] = v;
                        rgba[o + 1] = v;
                        rgba[o + 2] = v;
                        rgba[o + 3] = 255;
                    }
                }
            }
        }

        private static void DrawNeedle(byte[] rgba, int size, float cx, float cy, float w, float h, float rot, float shade)
        {
            float cos = MathF.Cos(rot), sin = MathF.Sin(rot);
            int rad = (int)MathF.Ceiling(MathF.Max(w, h) * 0.65f);
            int x0 = Math.Max(4, (int)(cx - rad));
            int x1 = Math.Min(size - 5, (int)(cx + rad));
            int y0 = Math.Max(4, (int)(cy - rad));
            int y1 = Math.Min(size - 5, (int)(cy + rad));

            for (int y = y0; y <= y1; y++)
            {
                for (int x = x0; x <= x1; x++)
                {
                    float dx = x - cx, dy = y - cy;
                    float lx = (dx * cos + dy * sin) / (w * 0.5f);
                    float ly = (-dx * sin + dy * cos) / (h * 0.5f);
                    float taper = 1.0f - MathF.Abs(ly) * 0.72f;
                    if (MathF.Abs(lx) <= taper && MathF.Abs(ly) <= 1.0f)
                    {
                        byte v = (byte)(Math.Clamp(shade, 0.35f, 1.0f) * 255f);
                        int o = (y * size + x) * 4;
                        rgba[o + 0] = v;
                        rgba[o + 1] = v;
                        rgba[o + 2] = v;
                        rgba[o + 3] = 255;
                    }
                }
            }
        }
    }
}
