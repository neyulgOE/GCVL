using System;
using Godot;
using PrimevalWorld.Core;
using PrimevalWorld.Flora;
using PrimevalWorld.Weather;

namespace PrimevalWorld.WorldGen
{
    /// <summary>
    /// Generates the 6-mode [M] World Map visualization textures directly from physical simulation grids.
    /// </summary>
    public static class WorldMapVisualizer
    {
        private const int MapW = 640;
        private const int MapH = 360;

        public static ImageTexture[] BuildAllModes(
            TectonicContinentGen tectonic,
            ErosionPhysics erosion,
            HydrologySolver hydrology,
            AtmosphereClimate climate,
            SoilPedology soil,
            EcosystemSpawner? flora = null,
            DynamicWeatherSystem? weather = null)
        {
            var textures = new ImageTexture[9];
            textures[0] = BuildTerrainHydrologyMap(erosion, hydrology, soil);
            textures[1] = BuildTemperatureMap(climate);
            textures[2] = BuildPrecipitationWindMap(climate);
            textures[3] = BuildMoistureFlowMap(hydrology, climate);
            textures[4] = BuildSoilMap(erosion, soil);
            textures[5] = BuildSlopeSedimentMap(erosion);
            textures[6] = flora != null ? BuildSevenEcosystemsMap(erosion, hydrology, flora) : textures[0];
            textures[7] = flora != null ? BuildFloraMap(erosion, hydrology, flora) : textures[0];
            textures[8] = weather != null ? BuildWeatherRadarMap(erosion, weather) : textures[0];
            return textures;
        }

        private static int MapToGridIdx(int px, int py)
        {
            int gx = Math.Clamp((int)((px / (float)(MapW - 1)) * (WorldPhysicsConfig.VertW - 1)), 0, WorldPhysicsConfig.VertW - 1);
            int gz = Math.Clamp((int)((py / (float)(MapH - 1)) * (WorldPhysicsConfig.VertH - 1)), 0, WorldPhysicsConfig.VertH - 1);
            return gz * WorldPhysicsConfig.VertW + gx;
        }

        private static ImageTexture BuildTerrainHydrologyMap(ErosionPhysics erosion, HydrologySolver hydrology, SoilPedology soil)
        {
            byte[] rgb = new byte[MapW * MapH * 3];
            Vector3 sunDir = new Vector3(-0.55f, 0.65f, -0.52f).Normalized();

            for (int py = 0; py < MapH; py++)
                for (int px = 0; px < MapW; px++)
                {
                    int idx = MapToGridIdx(px, py);
                    float h = erosion.HeightMap[idx];
                    float shade = 0.55f + 0.55f * Math.Clamp(erosion.NormalMap[idx].Dot(sunDir), 0.0f, 1.0f);

                    Color col;
                    if (h < -7.5f) col = new Color(0.04f, 0.16f, 0.30f);
                    else if (h < 0.3f) col = new Color(0.04f, 0.16f, 0.30f).Lerp(new Color(0.11f, 0.72f, 0.77f), FastNoise.SmoothStep(-7.5f, 0.3f, h));
                    else if (hydrology.HasInlandWater[idx] || hydrology.RiverMaskMap[idx] > 0.48f) col = new Color(0.14f, 0.60f, 0.76f);
                    else
                    {
                        col = soil.DominantSoilMap[idx] switch
                        {
                            SoilType.AlluvialLoam => new Color(0.14f, 0.30f, 0.12f),
                            SoilType.ForestBrownSoil => new Color(0.24f, 0.38f, 0.15f),
                            SoilType.SteppeLoess => new Color(0.74f, 0.50f, 0.16f),
                            SoilType.AridRedSand => new Color(0.76f, 0.38f, 0.20f),
                            SoilType.CoastalSand => new Color(0.78f, 0.72f, 0.50f),
                            _ => h > 160.0f ? new Color(0.90f, 0.94f, 0.98f) : new Color(0.32f, 0.33f, 0.34f),
                        };
                        col = new Color(Math.Clamp(col.R * shade, 0, 1), Math.Clamp(col.G * shade, 0, 1), Math.Clamp(col.B * shade, 0, 1));
                    }
                    WriteRgb(rgb, py * MapW + px, col);
                }

            return ImageTexture.CreateFromImage(Image.CreateFromData(MapW, MapH, false, Image.Format.Rgb8, rgb));
        }

        private static ImageTexture BuildTemperatureMap(AtmosphereClimate climate)
        {
            byte[] rgb = new byte[MapW * MapH * 3];
            for (int py = 0; py < MapH; py++)
                for (int px = 0; px < MapW; px++)
                {
                    int idx = MapToGridIdx(px, py);
                    float t = Math.Clamp((climate.TemperatureMap[idx] + 15.0f) / 53.0f, 0.0f, 1.0f);
                    Color c = t < 0.35f
                        ? new Color(0.12f, 0.36f, 0.88f).Lerp(new Color(0.22f, 0.80f, 0.74f), t / 0.35f)
                        : (t < 0.68f
                            ? new Color(0.22f, 0.80f, 0.74f).Lerp(new Color(0.92f, 0.78f, 0.18f), (t - 0.35f) / 0.33f)
                            : new Color(0.92f, 0.78f, 0.18f).Lerp(new Color(0.90f, 0.20f, 0.10f), (t - 0.68f) / 0.32f));
                    WriteRgb(rgb, py * MapW + px, c);
                }
            return ImageTexture.CreateFromImage(Image.CreateFromData(MapW, MapH, false, Image.Format.Rgb8, rgb));
        }

        private static ImageTexture BuildPrecipitationWindMap(AtmosphereClimate climate)
        {
            byte[] rgb = new byte[MapW * MapH * 3];
            for (int py = 0; py < MapH; py++)
                for (int px = 0; px < MapW; px++)
                {
                    int idx = MapToGridIdx(px, py);
                    float p = climate.PrecipitationMap[idx];
                    Color c = p < 0.45f
                        ? new Color(0.78f, 0.42f, 0.18f).Lerp(new Color(0.74f, 0.72f, 0.32f), p / 0.45f)
                        : new Color(0.74f, 0.72f, 0.32f).Lerp(new Color(0.08f, 0.56f, 0.72f), (p - 0.45f) / 0.55f);
                    WriteRgb(rgb, py * MapW + px, c);
                }

            // Overlay crisp wind direction arrows every 32 pixels
            for (int py = 18; py < MapH - 18; py += 36)
                for (int px = 18; px < MapW - 18; px += 36)
                {
                    int idx = MapToGridIdx(px, py);
                    Vector2 dir = climate.WindDirMap[idx];
                    DrawArrow(rgb, px, py, dir, new Color(1.0f, 1.0f, 1.0f));
                }

            return ImageTexture.CreateFromImage(Image.CreateFromData(MapW, MapH, false, Image.Format.Rgb8, rgb));
        }

        private static ImageTexture BuildMoistureFlowMap(HydrologySolver hydrology, AtmosphereClimate climate)
        {
            byte[] rgb = new byte[MapW * MapH * 3];
            for (int py = 0; py < MapH; py++)
                for (int px = 0; px < MapW; px++)
                {
                    int idx = MapToGridIdx(px, py);
                    float m = climate.MoistureMap[idx];
                    float f = hydrology.FlowAccumMap[idx];
                    Color c = new Color(0.68f, 0.44f, 0.22f).Lerp(new Color(0.10f, 0.58f, 0.42f), m);
                    c = c.Lerp(new Color(0.15f, 0.85f, 0.95f), FastNoise.SmoothStep(0.32f, 0.75f, f));
                    WriteRgb(rgb, py * MapW + px, c);
                }
            return ImageTexture.CreateFromImage(Image.CreateFromData(MapW, MapH, false, Image.Format.Rgb8, rgb));
        }

        private static ImageTexture BuildSoilMap(ErosionPhysics erosion, SoilPedology soil)
        {
            byte[] rgb = new byte[MapW * MapH * 3];
            for (int py = 0; py < MapH; py++)
                for (int px = 0; px < MapW; px++)
                {
                    int idx = MapToGridIdx(px, py);
                    if (erosion.HeightMap[idx] <= 0.1f)
                    {
                        WriteRgb(rgb, py * MapW + px, new Color(0.05f, 0.18f, 0.34f));
                        continue;
                    }
                    Color c = soil.DominantSoilMap[idx] switch
                    {
                        SoilType.AlluvialLoam => new Color(0.12f, 0.32f, 0.12f),
                        SoilType.ForestBrownSoil => new Color(0.34f, 0.46f, 0.16f),
                        SoilType.SteppeLoess => new Color(0.80f, 0.62f, 0.20f),
                        SoilType.AridRedSand => new Color(0.82f, 0.36f, 0.18f),
                        SoilType.CoastalSand => new Color(0.88f, 0.82f, 0.54f),
                        _ => new Color(0.62f, 0.66f, 0.74f),
                    };
                    WriteRgb(rgb, py * MapW + px, c);
                }
            return ImageTexture.CreateFromImage(Image.CreateFromData(MapW, MapH, false, Image.Format.Rgb8, rgb));
        }

        private static ImageTexture BuildSlopeSedimentMap(ErosionPhysics erosion)
        {
            byte[] rgb = new byte[MapW * MapH * 3];
            for (int py = 0; py < MapH; py++)
                for (int px = 0; px < MapW; px++)
                {
                    int idx = MapToGridIdx(px, py);
                    float slopeT = Math.Clamp(erosion.SlopeDegMap[idx] / 55.0f, 0.0f, 1.0f);
                    float sedT = Math.Clamp(erosion.SedimentMap[idx] / 18.0f, 0.0f, 1.0f);
                    Color c = new Color(0.12f + sedT * 0.65f, 0.28f + sedT * 0.30f - slopeT * 0.15f, 0.22f + slopeT * 0.65f);
                    WriteRgb(rgb, py * MapW + px, c);
                }
            return ImageTexture.CreateFromImage(Image.CreateFromData(MapW, MapH, false, Image.Format.Rgb8, rgb));
        }

        private static ImageTexture BuildSevenEcosystemsMap(ErosionPhysics erosion, HydrologySolver hydrology, EcosystemSpawner flora)
        {
            byte[] rgb = new byte[MapW * MapH * 3];
            Vector3 sunDir = new Vector3(-0.55f, 0.65f, -0.52f).Normalized();

            for (int py = 0; py < MapH; py++)
                for (int px = 0; px < MapW; px++)
                {
                    int idx = MapToGridIdx(px, py);
                    float h = erosion.HeightMap[idx];
                    LandEcosystemId eco = flora.EcosystemMap[idx];
                    float shade = 0.68f + 0.36f * Math.Clamp(erosion.NormalMap[idx].Dot(sunDir), 0.0f, 1.0f);

                    Color col;
                    if (eco == LandEcosystemId.OceanOrLake)
                    {
                        col = h < -6.0f
                            ? new Color(0.04f, 0.14f, 0.28f)
                            : (h < 0.25f ? new Color(0.10f, 0.50f, 0.62f) : new Color(0.14f, 0.58f, 0.78f));
                    }
                    else
                    {
                        float cov = flora.CanopyCoverageMap[idx];
                        col = eco switch
                        {
                            LandEcosystemId.PrimevalDenseForest => new Color(0.06f, 0.36f, 0.12f).Lerp(new Color(0.03f, 0.22f, 0.07f), cov * 0.65f),
                            LandEcosystemId.AlluvialFloodplain => new Color(0.40f, 0.78f, 0.25f),
                            LandEcosystemId.WetlandAndDelta => new Color(0.12f, 0.58f, 0.52f).Lerp(new Color(0.08f, 0.40f, 0.36f), hydrology.WetlandWaterFactor[idx]),
                            LandEcosystemId.OpenSteppePlateau => new Color(0.82f, 0.68f, 0.22f).Lerp(new Color(0.32f, 0.56f, 0.18f), cov * 0.60f),
                            LandEcosystemId.AridRedDesertOasis => new Color(0.84f, 0.38f, 0.18f),
                            LandEcosystemId.AlpineSnowTundraRock => h > 165.0f ? new Color(0.88f, 0.93f, 0.98f) : new Color(0.56f, 0.62f, 0.70f),
                            LandEcosystemId.CoastlineSaltDunes => new Color(0.92f, 0.86f, 0.56f),
                            _ => new Color(0.20f, 0.30f, 0.20f),
                        };
                        col = new Color(Math.Clamp(col.R * shade, 0, 1), Math.Clamp(col.G * shade, 0, 1), Math.Clamp(col.B * shade, 0, 1));
                    }
                    WriteRgb(rgb, py * MapW + px, col);
                }

            return ImageTexture.CreateFromImage(Image.CreateFromData(MapW, MapH, false, Image.Format.Rgb8, rgb));
        }

        private static ImageTexture BuildFloraMap(ErosionPhysics erosion, HydrologySolver hydrology, EcosystemSpawner flora)
        {
            byte[] rgb = new byte[MapW * MapH * 3];
            for (int py = 0; py < MapH; py++)
                for (int px = 0; px < MapW; px++)
                {
                    int idx = MapToGridIdx(px, py);
                    float h = erosion.HeightMap[idx];
                    Color col;
                    if (h < -6.0f) col = new Color(0.04f, 0.14f, 0.26f);
                    else if (h < 0.3f) col = new Color(0.10f, 0.44f, 0.54f);
                    else if (hydrology.HasInlandWater[idx] || hydrology.RiverMaskMap[idx] > 0.48f) col = new Color(0.12f, 0.56f, 0.72f);
                    else
                    {
                        sbyte spId = flora.DominantSpeciesMap[idx];
                        float cov = flora.CanopyCoverageMap[idx];
                        if (spId >= 0 && spId < FloraNicheDatabase.AllSpecies.Length)
                        {
                            Color spCol = FloraNicheDatabase.AllSpecies[spId].MapColor;
                            float shade = 0.62f + cov * 0.48f;
                            col = new Color(Math.Clamp(spCol.R * shade, 0, 1), Math.Clamp(spCol.G * shade, 0, 1), Math.Clamp(spCol.B * shade, 0, 1));
                        }
                        else
                        {
                            col = h > 180.0f ? new Color(0.84f, 0.88f, 0.94f) : new Color(0.38f, 0.34f, 0.28f);
                        }
                    }
                    WriteRgb(rgb, py * MapW + px, col);
                }
            return ImageTexture.CreateFromImage(Image.CreateFromData(MapW, MapH, false, Image.Format.Rgb8, rgb));
        }

        public static ImageTexture BuildWeatherRadarMap(ErosionPhysics erosion, DynamicWeatherSystem weather)
        {
            byte[] rgb = new byte[MapW * MapH * 3];
            FillWeatherRadarBytes(rgb, erosion, weather);
            return ImageTexture.CreateFromImage(Image.CreateFromData(MapW, MapH, false, Image.Format.Rgb8, rgb));
        }

        public static void RefreshWeatherRadarMap(ImageTexture tex, ErosionPhysics erosion, DynamicWeatherSystem weather)
        {
            byte[] rgb = new byte[MapW * MapH * 3];
            FillWeatherRadarBytes(rgb, erosion, weather);
            tex.Update(Image.CreateFromData(MapW, MapH, false, Image.Format.Rgb8, rgb));
        }

        private static void FillWeatherRadarBytes(byte[] rgb, ErosionPhysics erosion, DynamicWeatherSystem weather)
        {
            for (int py = 0; py < MapH; py++)
            {
                int sz = Math.Clamp((int)((py / (float)(MapH - 1)) * (SeasonalState.SimH - 1)), 0, SeasonalState.SimH - 1);
                for (int px = 0; px < MapW; px++)
                {
                    int sx = Math.Clamp((int)((px / (float)(MapW - 1)) * (SeasonalState.SimW - 1)), 0, SeasonalState.SimW - 1);
                    int gIdx = MapToGridIdx(px, py);
                    int wIdx = sz * SeasonalState.SimW + sx;

                    float h = erosion.HeightMap[gIdx];
                    float temp = weather.SurfaceState.LiveTempMap[wIdx];
                    float snow = weather.SurfaceState.SnowAccumulationMap[wIdx];
                    float rain = weather.RainIntensityMap[wIdx];
                    float cloud = weather.CloudCoverMap[wIdx];

                    Color baseCol = h <= 0.2f ? new Color(0.05f, 0.12f, 0.22f) : new Color(0.16f, 0.20f, 0.18f);
                    // Snow cover overlay
                    baseCol = baseCol.Lerp(new Color(0.90f, 0.94f, 0.99f), snow * 0.85f);
                    // Cloud & Rain Radar (green -> yellow -> magenta for heavy storms)
                    if (cloud > 0.25f)
                        baseCol = baseCol.Lerp(new Color(0.45f, 0.55f, 0.65f), (cloud - 0.25f) * 0.6f);
                    if (rain > 0.12f)
                    {
                        Color radarCol = temp <= 0.5f
                            ? new Color(0.45f, 0.85f, 1.0f) // Snowfall radar
                            : (rain < 0.5f ? new Color(0.15f, 0.85f, 0.32f) : new Color(0.95f, 0.72f, 0.12f));
                        baseCol = baseCol.Lerp(radarCol, Math.Clamp(rain * 1.1f, 0.0f, 0.92f));
                    }

                    // 0°C Isotherm contour line
                    if (MathF.Abs(temp) < 0.75f && h > 0.2f)
                        baseCol = new Color(0.35f, 0.90f, 1.0f);

                    WriteRgb(rgb, py * MapW + px, baseCol);
                }
            }
        }

        private static void DrawArrow(byte[] rgb, int cx, int cy, Vector2 dir, Color col)
        {
            for (int i = -6; i <= 6; i++)
            {
                int px = cx + (int)MathF.Round(dir.X * i);
                int py = cy + (int)MathF.Round(dir.Y * i);
                if (px >= 0 && px < MapW && py >= 0 && py < MapH)
                    WriteRgb(rgb, py * MapW + px, col);
            }
            Vector2 perp = new Vector2(-dir.Y, dir.X);
            int tipX = cx + (int)MathF.Round(dir.X * 6);
            int tipY = cy + (int)MathF.Round(dir.Y * 6);
            for (int s = 1; s <= 3; s++)
            {
                int ax = tipX - (int)MathF.Round(dir.X * s - perp.X * s);
                int ay = tipY - (int)MathF.Round(dir.Y * s - perp.Y * s);
                int bx = tipX - (int)MathF.Round(dir.X * s + perp.X * s);
                int by = tipY - (int)MathF.Round(dir.Y * s + perp.Y * s);
                if (ax >= 0 && ax < MapW && ay >= 0 && ay < MapH) WriteRgb(rgb, ay * MapW + ax, col);
                if (bx >= 0 && bx < MapW && by >= 0 && by < MapH) WriteRgb(rgb, by * MapW + bx, col);
            }
        }

        private static void WriteRgb(byte[] rgb, int pixelIdx, Color c)
        {
            int o = pixelIdx * 3;
            rgb[o + 0] = (byte)(Math.Clamp(c.R, 0.0f, 1.0f) * 255.0f);
            rgb[o + 1] = (byte)(Math.Clamp(c.G, 0.0f, 1.0f) * 255.0f);
            rgb[o + 2] = (byte)(Math.Clamp(c.B, 0.0f, 1.0f) * 255.0f);
        }
    }
}
