using System;
using System.Collections.Generic;
using Godot;

namespace PrimevalWorld.Flora
{
    /// <summary>
    /// Loads the real botanical RGBA8 PNG textures from res://assets/textures/flora/
    /// (zero procedural leaf drawing overwrite!) and generates mipmaps + alpha statistics.
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
            var res = new BotanicalTextures
            {
                BroadleafTex = LoadLeafPng($"{dir}/leaf_broadleaf.png", res_t: null),
                ConiferTex = LoadLeafPng($"{dir}/leaf_conifer.png", res_t: null),
                AcaciaTex = LoadLeafPng($"{dir}/leaf_acacia.png", res_t: null),
                PalmFernTex = LoadLeafPng($"{dir}/leaf_palm_fern.png", res_t: null),
                BarkRoughTex = LoadBarkPng($"{dir}/bark_rough.png"),
                BarkPaleTex = LoadBarkPng($"{dir}/bark_pale.png"),
            };

            MeasureAlpha($"{dir}/leaf_broadleaf.png", res.TransparentPercent, res.BorderOpaquePixels);
            MeasureAlpha($"{dir}/leaf_conifer.png", res.TransparentPercent, res.BorderOpaquePixels);
            MeasureAlpha($"{dir}/leaf_acacia.png", res.TransparentPercent, res.BorderOpaquePixels);
            MeasureAlpha($"{dir}/leaf_palm_fern.png", res.TransparentPercent, res.BorderOpaquePixels);

            _cached = res;
            return res;
        }

        private static ImageTexture LoadLeafPng(string relPath, object? res_t)
        {
            string absPath = ProjectSettings.GlobalizePath($"res://{relPath}");
            var img = new Image();
            if (img.Load(absPath) == Error.Ok)
            {
                if (img.GetFormat() != Image.Format.Rgba8)
                    img.Convert(Image.Format.Rgba8);
                img.GenerateMipmaps();
                return ImageTexture.CreateFromImage(img);
            }
            GD.PushError($"Missing botanical leaf texture: {absPath}");
            var fallback = Image.CreateEmpty(4, 4, false, Image.Format.Rgba8);
            return ImageTexture.CreateFromImage(fallback);
        }

        private static ImageTexture LoadBarkPng(string relPath)
        {
            string absPath = ProjectSettings.GlobalizePath($"res://{relPath}");
            var img = new Image();
            if (img.Load(absPath) == Error.Ok)
            {
                img.GenerateMipmaps();
                return ImageTexture.CreateFromImage(img);
            }
            GD.PushError($"Missing bark texture: {absPath}");
            return ImageTexture.CreateFromImage(Image.CreateEmpty(4, 4, false, Image.Format.Rgb8));
        }

        private static void MeasureAlpha(string relPath, Dictionary<string, float> stats, Dictionary<string, int> borderStats)
        {
            string absPath = ProjectSettings.GlobalizePath($"res://{relPath}");
            var img = new Image();
            if (img.Load(absPath) != Error.Ok) return;
            if (img.GetFormat() != Image.Format.Rgba8) img.Convert(Image.Format.Rgba8);

            int w = img.GetWidth(), h = img.GetHeight();
            byte[] data = img.GetData();
            int trans = 0, borderOpaque = 0;

            for (int y = 0; y < h; y++)
                for (int x = 0; x < w; x++)
                {
                    byte a = data[(y * w + x) * 4 + 3];
                    if (a < 128) trans++;
                    if ((x == 0 || x == w - 1 || y == 0 || y == h - 1) && a >= 128)
                        borderOpaque++;
                }

            stats[relPath] = trans * 100.0f / (w * h);
            borderStats[relPath] = borderOpaque;
        }
    }
}
