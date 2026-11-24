using System;
using System.Collections.Generic;
using Godot;

namespace PrimevalWorld.Flora
{
    /// <summary>
    /// Loads real 1024x1024 botanical RGBA8 leaf textures plus CC0 1K Poly Haven PBR Bark & Moss maps
    /// (bark_brown_02, pine_bark, moss_01) with mipmaps and alpha statistics.
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

            // CC0 1K PBR Bark & Moss maps (Poly Haven: bark_brown_02, pine_bark, moss_01)
            public ImageTexture BarkHardwoodAlbedo { get; set; } = null!;
            public ImageTexture BarkHardwoodNormal { get; set; } = null!;
            public ImageTexture BarkHardwoodRoughness { get; set; } = null!;
            public ImageTexture BarkConiferAlbedo { get; set; } = null!;
            public ImageTexture BarkConiferNormal { get; set; } = null!;
            public ImageTexture BarkConiferRoughness { get; set; } = null!;
            public ImageTexture MossAlbedo { get; set; } = null!;
            public ImageTexture MossNormal { get; set; } = null!;

            public Dictionary<string, float> TransparentPercent { get; } = new();
            public Dictionary<string, int> BorderOpaquePixels { get; } = new();
        }

        private static BotanicalTextures? _cached;

        public static BotanicalTextures EnsureAndLoadAll()
        {
            if (_cached != null) return _cached;

            const string dir = "assets/textures/flora";
            const string barkDir = "assets/textures/flora/bark";

            var res = new BotanicalTextures
            {
                BroadleafTex = LoadRgbaPng($"{dir}/leaf_broadleaf.png"),
                ConiferTex = LoadRgbaPng($"{dir}/leaf_conifer.png"),
                AcaciaTex = LoadRgbaPng($"{dir}/leaf_acacia.png"),
                PalmFernTex = LoadRgbaPng($"{dir}/leaf_palm_fern.png"),
                BarkRoughTex = LoadRgbTex($"{dir}/bark_rough.png"),
                BarkPaleTex = LoadRgbTex($"{dir}/bark_pale.png"),

                BarkHardwoodAlbedo = LoadRgbTex($"{barkDir}/bark_hardwood_albedo.jpg"),
                BarkHardwoodNormal = LoadRgbTex($"{barkDir}/bark_hardwood_normal.jpg"),
                BarkHardwoodRoughness = LoadRgbTex($"{barkDir}/bark_hardwood_roughness.jpg"),
                BarkConiferAlbedo = LoadRgbTex($"{barkDir}/bark_conifer_albedo.jpg"),
                BarkConiferNormal = LoadRgbTex($"{barkDir}/bark_conifer_normal.jpg"),
                BarkConiferRoughness = LoadRgbTex($"{barkDir}/bark_conifer_roughness.jpg"),
                MossAlbedo = LoadRgbTex($"{barkDir}/moss_albedo.jpg"),
                MossNormal = LoadRgbTex($"{barkDir}/moss_normal.jpg"),
            };

            MeasureAlpha($"{dir}/leaf_broadleaf.png", res.TransparentPercent, res.BorderOpaquePixels);
            MeasureAlpha($"{dir}/leaf_conifer.png", res.TransparentPercent, res.BorderOpaquePixels);
            MeasureAlpha($"{dir}/leaf_acacia.png", res.TransparentPercent, res.BorderOpaquePixels);
            MeasureAlpha($"{dir}/leaf_palm_fern.png", res.TransparentPercent, res.BorderOpaquePixels);

            _cached = res;
            return res;
        }

        private static ImageTexture LoadRgbaPng(string relPath)
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
            return ImageTexture.CreateFromImage(Image.CreateEmpty(4, 4, false, Image.Format.Rgba8));
        }

        private static ImageTexture LoadRgbTex(string relPath)
        {
            string absPath = ProjectSettings.GlobalizePath($"res://{relPath}");
            var img = new Image();
            if (img.Load(absPath) == Error.Ok)
            {
                img.GenerateMipmaps();
                return ImageTexture.CreateFromImage(img);
            }
            GD.PushError($"Missing PBR bark/moss texture: {absPath}");
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
