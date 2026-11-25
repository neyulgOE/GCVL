using System;
using System.Collections.Generic;
using Godot;

namespace PrimevalWorld.Flora
{
    /// <summary>
    /// Loads all 10 botanical 1024x1024 RGBA8 foliage/specialty/atlas textures plus 4 seamless 1K PBR Bark sets
    /// (bark_ancient_mossy, bark_sequoia_conifer, bark_hardwood, bark_conifer) and CC0 moss maps.
    /// </summary>
    public static class BotanicalTextureGenerator
    {
        public sealed class BotanicalTextures
        {
            // 8 Single/Multi-strip 1024x1024 RGBA8 botanical textures
            public ImageTexture BroadleafTex { get; set; } = null!;
            public ImageTexture ConiferTex { get; set; } = null!;
            public ImageTexture AutumnTex { get; set; } = null!;
            public ImageTexture PalmFernTex { get; set; } = null!;
            public ImageTexture LianaMossTex { get; set; } = null!;
            public ImageTexture AraucariaCypressTex { get; set; } = null!;
            public ImageTexture WillowAcaciaBerryTex { get; set; } = null!;
            public ImageTexture AgaveBambooTex { get; set; } = null!;

            // 2 Specialty 2x2 Atlas 1024x1024 RGBA8 textures (16+ understory/aquatic/desert/coastal species)
            public ImageTexture SpecialtyAtlasATex { get; set; } = null!;
            public ImageTexture SpecialtyAtlasBTex { get; set; } = null!;

            // 4 Seamless 1K PBR Bark sets + Moss
            public ImageTexture BarkHardwoodAlbedo { get; set; } = null!;
            public ImageTexture BarkHardwoodNormal { get; set; } = null!;
            public ImageTexture BarkHardwoodRoughness { get; set; } = null!;

            public ImageTexture BarkConiferAlbedo { get; set; } = null!;
            public ImageTexture BarkConiferNormal { get; set; } = null!;
            public ImageTexture BarkConiferRoughness { get; set; } = null!;

            public ImageTexture BarkAncientMossyAlbedo { get; set; } = null!;
            public ImageTexture BarkAncientMossyNormal { get; set; } = null!;
            public ImageTexture BarkAncientMossyRoughness { get; set; } = null!;

            public ImageTexture BarkSequoiaConiferAlbedo { get; set; } = null!;
            public ImageTexture BarkSequoiaConiferNormal { get; set; } = null!;
            public ImageTexture BarkSequoiaConiferRoughness { get; set; } = null!;

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
                AutumnTex = LoadRgbaPng($"{dir}/leaf_autumn.png"),
                PalmFernTex = LoadRgbaPng($"{dir}/leaf_palm_fern.png"),
                LianaMossTex = LoadRgbaPng($"{dir}/flora_liana_moss.png"),
                AraucariaCypressTex = LoadRgbaPng($"{dir}/leaf_araucaria_cypress.png"),
                WillowAcaciaBerryTex = LoadRgbaPng($"{dir}/leaf_willow_acacia_berry.png"),
                AgaveBambooTex = LoadRgbaPng($"{dir}/leaf_agave_bamboo.png"),
                SpecialtyAtlasATex = LoadRgbaPng($"{dir}/flora_specialty_atlas_a.png"),
                SpecialtyAtlasBTex = LoadRgbaPng($"{dir}/flora_specialty_atlas_b.png"),

                BarkHardwoodAlbedo = LoadRgbTex($"{barkDir}/bark_hardwood_albedo.jpg"),
                BarkHardwoodNormal = LoadRgbTex($"{barkDir}/bark_hardwood_normal.jpg"),
                BarkHardwoodRoughness = LoadRgbTex($"{barkDir}/bark_hardwood_roughness.jpg"),

                BarkConiferAlbedo = LoadRgbTex($"{barkDir}/bark_conifer_albedo.jpg"),
                BarkConiferNormal = LoadRgbTex($"{barkDir}/bark_conifer_normal.jpg"),
                BarkConiferRoughness = LoadRgbTex($"{barkDir}/bark_conifer_roughness.jpg"),

                BarkAncientMossyAlbedo = LoadRgbTex($"{barkDir}/bark_ancient_mossy_albedo.jpg"),
                BarkAncientMossyNormal = LoadRgbTex($"{barkDir}/bark_ancient_mossy_normal.jpg"),
                BarkAncientMossyRoughness = LoadRgbTex($"{barkDir}/bark_ancient_mossy_roughness.jpg"),

                BarkSequoiaConiferAlbedo = LoadRgbTex($"{barkDir}/bark_sequoia_conifer_albedo.jpg"),
                BarkSequoiaConiferNormal = LoadRgbTex($"{barkDir}/bark_sequoia_conifer_normal.jpg"),
                BarkSequoiaConiferRoughness = LoadRgbTex($"{barkDir}/bark_sequoia_conifer_roughness.jpg"),

                MossAlbedo = LoadRgbTex($"{barkDir}/moss_albedo.jpg"),
                MossNormal = LoadRgbTex($"{barkDir}/moss_normal.jpg"),
            };

            string[] audited =
            {
                $"{dir}/leaf_broadleaf.png",
                $"{dir}/leaf_conifer.png",
                $"{dir}/leaf_autumn.png",
                $"{dir}/leaf_palm_fern.png",
                $"{dir}/flora_liana_moss.png",
                $"{dir}/leaf_araucaria_cypress.png",
                $"{dir}/leaf_willow_acacia_berry.png",
                $"{dir}/leaf_agave_bamboo.png",
                $"{dir}/flora_specialty_atlas_a.png",
                $"{dir}/flora_specialty_atlas_b.png",
            };
            foreach (string p in audited)
                MeasureAlpha(p, res.TransparentPercent, res.BorderOpaquePixels);

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
                if (img.GetFormat() != Image.Format.Rgb8)
                    img.Convert(Image.Format.Rgb8);
                img.GenerateMipmaps();
                return ImageTexture.CreateFromImage(img);
            }
            GD.PushError($"Missing bark/moss texture: {absPath}");
            return ImageTexture.CreateFromImage(Image.CreateEmpty(4, 4, false, Image.Format.Rgb8));
        }

        private static void MeasureAlpha(string relPath, Dictionary<string, float> transparentPct, Dictionary<string, int> borderOpaque)
        {
            string absPath = ProjectSettings.GlobalizePath($"res://{relPath}");
            var img = new Image();
            if (img.Load(absPath) != Error.Ok) return;
            int w = img.GetWidth();
            int h = img.GetHeight();
            int total = w * h;
            int trans = 0;
            int border = 0;
            for (int y = 0; y < h; y++)
            {
                for (int x = 0; x < w; x++)
                {
                    float a = img.GetPixel(x, y).A;
                    if (a < 0.45f) trans++;
                    else if (x == 0 || y == 0 || x == w - 1 || y == h - 1) border++;
                }
            }
            transparentPct[relPath] = total > 0 ? trans * 100.0f / total : 0.0f;
            borderOpaque[relPath] = border;
        }
    }
}
