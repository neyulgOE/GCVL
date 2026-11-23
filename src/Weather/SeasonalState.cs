using System;
using PrimevalWorld.Core;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Weather
{
    /// <summary>
    /// Stage 4: Dynamic Surface State on the 256x144 Weather Grid:
    /// LiveTemp(x,z,t), SnowAccumulation, Wetness, SurfaceIce & RiverSurgeOffset.
    /// Zero per-frame allocations.
    /// </summary>
    public sealed class SeasonalState
    {
        public const int SimW = 256;
        public const int SimH = 144;
        public const int CellCount = SimW * SimH;

        public float[] LiveTempMap { get; } = new float[CellCount];
        public float[] SnowAccumulationMap { get; } = new float[CellCount];
        public float[] WetnessMap { get; } = new float[CellCount];
        public float[] SurfaceIceMap { get; } = new float[CellCount];

        public float RiverSurgeOffset { get; private set; }
        public float MeanSnowPercent { get; private set; }
        public float MeanWetnessPercent { get; private set; }

        // Pre-sampled static base arrays on 256x144 for ultra-fast 2 Hz updates
        private readonly float[] _baseTemp = new float[CellCount];
        private readonly float[] _baseSlopeDeg = new float[CellCount];
        private readonly float[] _baseHeight = new float[CellCount];
        private readonly float[] _baseWindSpeed = new float[CellCount];
        private readonly bool[] _isWaterSurface = new bool[CellCount];

        public void InitializeFromWorld(
            ErosionPhysics erosion,
            HydrologySolver hydrology,
            AtmosphereClimate climate)
        {
            for (int sz = 0; sz < SimH; sz++)
            {
                int gz = Math.Clamp((int)((sz / (float)(SimH - 1)) * (WorldPhysicsConfig.VertH - 1)), 0, WorldPhysicsConfig.VertH - 1);
                for (int sx = 0; sx < SimW; sx++)
                {
                    int gx = Math.Clamp((int)((sx / (float)(SimW - 1)) * (WorldPhysicsConfig.VertW - 1)), 0, WorldPhysicsConfig.VertW - 1);
                    int sIdx = sz * SimW + sx;
                    int gIdx = gz * WorldPhysicsConfig.VertW + gx;

                    _baseTemp[sIdx] = climate.TemperatureMap[gIdx];
                    _baseSlopeDeg[sIdx] = erosion.SlopeDegMap[gIdx];
                    _baseHeight[sIdx] = erosion.HeightMap[gIdx];
                    _baseWindSpeed[sIdx] = climate.WindSpeedMap[gIdx];
                    _isWaterSurface[sIdx] = hydrology.HasInlandWater[gIdx] || hydrology.RiverMaskMap[gIdx] > 0.45f || erosion.HeightMap[gIdx] <= 0.2f;

                    LiveTempMap[sIdx] = _baseTemp[sIdx];
                    // Seed initial permanent snow on freezing peaks
                    SnowAccumulationMap[sIdx] = _baseTemp[sIdx] < -1.0f && _baseSlopeDeg[sIdx] < 40.0f
                        ? Math.Clamp((-1.0f - _baseTemp[sIdx]) * 0.14f, 0.0f, 1.0f)
                        : 0.0f;
                    WetnessMap[sIdx] = 0.0f;
                    SurfaceIceMap[sIdx] = _isWaterSurface[sIdx] && _baseTemp[sIdx] < -3.0f ? 0.65f : 0.0f;
                }
            }
            RiverSurgeOffset = 0.0f;
        }

        public void Step(
            float dtSimHours,
            float deltaTDay,
            float deltaTSeason,
            float[] cloudCover,
            float[] rainIntensity)
        {
            float totalRain = 0.0f;
            float totalMelt = 0.0f;
            float totalSnow = 0.0f;
            float totalWet = 0.0f;
            int landCells = 0;

            float dtScale = Math.Clamp(dtSimHours, 0.01f, 4.0f);

            for (int i = 0; i < CellCount; i++)
            {
                float cloud = cloudCover[i];
                float rain = rainIntensity[i];
                float temp = _baseTemp[i] + deltaTSeason + deltaTDay - cloud * 2.5f;
                LiveTempMap[i] = temp;

                float slope = _baseSlopeDeg[i];
                float wind = _baseWindSpeed[i];
                bool isWater = _isWaterSurface[i];

                // Snow accumulation & melt
                float snow = SnowAccumulationMap[i];
                if (!isWater && _baseHeight[i] > 0.2f)
                {
                    landCells++;
                    if (rain > 0.05f && temp <= 0.5f)
                    {
                        float slopeRetention = 1.0f - FastNoise.SmoothStep(24.0f, 44.0f, slope);
                        snow += rain * 0.35f * slopeRetention * dtScale;
                    }
                    else if (temp > 1.5f && snow > 0.0f)
                    {
                        float melt = (temp - 1.5f) * 0.055f * (1.0f - cloud * 0.4f) * dtScale;
                        float actualMelt = MathF.Min(snow, melt);
                        snow -= actualMelt;
                        totalMelt += actualMelt;
                        WetnessMap[i] = MathF.Min(1.0f, WetnessMap[i] + actualMelt * 1.4f);
                    }

                    // Keep permanent alpine snowcap when base temp is freezing
                    if (_baseTemp[i] < -2.5f && slope < 38.0f)
                        snow = MathF.Max(snow, Math.Clamp((-2.5f - _baseTemp[i]) * 0.12f, 0.0f, 0.85f));

                    snow = Math.Clamp(snow, 0.0f, 1.0f);
                    SnowAccumulationMap[i] = snow;
                    totalSnow += snow;

                    // Surface Wetness
                    float wet = WetnessMap[i];
                    if (rain > 0.05f && temp > 0.5f)
                    {
                        wet += rain * 0.55f * dtScale;
                        totalRain += rain;
                    }
                    else
                    {
                        float evap = (0.04f + MathF.Max(0.0f, temp) * 0.008f + wind * 0.005f) * (1.0f - cloud * 0.5f) * dtScale;
                        wet -= evap;
                    }
                    wet = Math.Clamp(wet, 0.0f, 1.0f);
                    WetnessMap[i] = wet;
                    totalWet += wet;
                }
                else if (isWater)
                {
                    // Surface Ice on cold inland lakes & calm streams
                    float ice = SurfaceIceMap[i];
                    if (temp < -2.0f)
                        ice += (-2.0f - temp) * 0.04f * dtScale;
                    else if (temp > 0.5f)
                        ice -= (temp - 0.5f) * 0.08f * dtScale;
                    SurfaceIceMap[i] = Math.Clamp(ice, 0.0f, 1.0f);
                }
            }

            float targetSurge = Math.Clamp((totalRain / Math.Max(1, landCells)) * 4.5f + (totalMelt / Math.Max(1, landCells)) * 8.0f, 0.0f, 1.6f);
            RiverSurgeOffset += (targetSurge - RiverSurgeOffset) * 0.25f;
            MeanSnowPercent = landCells > 0 ? (totalSnow / landCells) * 100.0f : 0.0f;
            MeanWetnessPercent = landCells > 0 ? (totalWet / landCells) * 100.0f : 0.0f;
        }
    }
}
