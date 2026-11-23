using System;
using System.Diagnostics;
using Godot;
using PrimevalWorld.Core;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Weather
{
    public enum WeatherOverrideMode : byte
    {
        Natural = 0,
        ClearSun = 1,
        RainStorm = 2,
        BlizzardOrSandstorm = 3,
    }

    public readonly struct LiveWeatherSample
    {
        public readonly float LiveTempC;
        public readonly float CloudCover;
        public readonly float RainIntensity;
        public readonly float SnowAccum;
        public readonly float Wetness;
        public readonly float SurfaceIce;
        public readonly float LiveWindSpeed;
        public readonly Vector2 WindDir;
        public readonly string ConditionLabel;

        public LiveWeatherSample(
            float temp, float cloud, float rain, float snow, float wet, float ice,
            float windSpd, Vector2 windDir, string label)
        {
            LiveTempC = temp;
            CloudCover = cloud;
            RainIntensity = rain;
            SnowAccum = snow;
            Wetness = wet;
            SurfaceIce = ice;
            LiveWindSpeed = windSpd;
            WindDir = windDir;
            ConditionLabel = label;
        }
    }

    /// <summary>
    /// Stage 4: 2 Hz Dynamic Weather & Pressure System on 256x144 grid.
    /// 5 drifting storm cells move along WindDirMap with Orographic Boost on windward slopes
    /// and dissipation in the SW rain shadow. Uploads WeatherDynamicTex via ImageTexture.Update() (<0.3ms).
    /// </summary>
    public sealed class DynamicWeatherSystem
    {
        private const int SimW = SeasonalState.SimW;
        private const int SimH = SeasonalState.SimH;

        private struct StormCell
        {
            public float GridX;
            public float GridZ;
            public float RadiusCells;
            public float Intensity;
        }

        private readonly StormCell[] _storms = new StormCell[5];
        private readonly float[] _cloudCover = new float[SeasonalState.CellCount];
        private readonly float[] _rainIntensity = new float[SeasonalState.CellCount];
        private readonly float[] _liveWindSpeed = new float[SeasonalState.CellCount];

        // Pre-sampled static fields on 256x144
        private readonly float[] _basePrecip = new float[SeasonalState.CellCount];
        private readonly float[] _baseWindSpd = new float[SeasonalState.CellCount];
        private readonly Vector2[] _baseWindDir = new Vector2[SeasonalState.CellCount];
        private readonly float[] _aridWeight = new float[SeasonalState.CellCount];

        private readonly byte[] _gpuBytes = new byte[SeasonalState.CellCount * 4];
        private Image? _weatherImage;
        private ImageTexture? _weatherTex;

        private float _accumSeconds;
        private AtmosphereClimate? _climate;
        private SoilPedology? _soil;

        public SeasonalState SurfaceState { get; } = new();
        public WeatherOverrideMode OverrideMode { get; set; } = WeatherOverrideMode.Natural;
        public float GlobalWindGust { get; private set; } = 1.0f;
        public double LastUpdateMs { get; private set; }

        public ImageTexture WeatherDynamicTex => _weatherTex!;
        public float[] CloudCoverMap => _cloudCover;
        public float[] RainIntensityMap => _rainIntensity;

        public void Initialize(
            ErosionPhysics erosion,
            HydrologySolver hydrology,
            AtmosphereClimate climate,
            SoilPedology soil,
            int seed)
        {
            _climate = climate;
            _soil = soil;
            SurfaceState.InitializeFromWorld(erosion, hydrology, climate);

            for (int sz = 0; sz < SimH; sz++)
            {
                int gz = Math.Clamp((int)((sz / (float)(SimH - 1)) * (WorldPhysicsConfig.VertH - 1)), 0, WorldPhysicsConfig.VertH - 1);
                for (int sx = 0; sx < SimW; sx++)
                {
                    int gx = Math.Clamp((int)((sx / (float)(SimW - 1)) * (WorldPhysicsConfig.VertW - 1)), 0, WorldPhysicsConfig.VertW - 1);
                    int sIdx = sz * SimW + sx;
                    int gIdx = gz * WorldPhysicsConfig.VertW + gx;

                    _basePrecip[sIdx] = climate.PrecipitationMap[gIdx];
                    _baseWindSpd[sIdx] = climate.WindSpeedMap[gIdx];
                    _baseWindDir[sIdx] = climate.WindDirMap[gIdx];
                    _aridWeight[sIdx] = soil.WAridRed[gIdx];
                }
            }

            var rng = new Random(seed + 404);
            for (int i = 0; i < _storms.Length; i++)
            {
                _storms[i] = new StormCell
                {
                    GridX = (float)(rng.NextDouble() * SimW),
                    GridZ = (float)(rng.NextDouble() * SimH),
                    RadiusCells = 24.0f + (float)rng.NextDouble() * 24.0f,
                    Intensity = 0.65f + (float)rng.NextDouble() * 0.35f,
                };
            }

            _weatherImage = Image.CreateFromData(SimW, SimH, false, Image.Format.Rgba8, _gpuBytes);
            _weatherTex = ImageTexture.CreateFromImage(_weatherImage);
            StepSimulation(0.25f, new SimulationClock());
        }

        public void Update(float realDelta, SimulationClock clock)
        {
            if (clock.IsPaused) return;
            _accumSeconds += realDelta;
            if (_accumSeconds < 0.5f) return; // 2 Hz simulation beat

            float dtStep = _accumSeconds;
            _accumSeconds = 0.0f;
            float simHours = dtStep * (24.0f / 720.0f) * clock.SpeedMultiplier;
            StepSimulation(Math.Clamp(simHours, 0.02f, 3.0f), clock);
        }

        public void ForceImmediateStep(SimulationClock clock)
        {
            StepSimulation(0.35f, clock);
        }

        private void StepSimulation(float simHours, SimulationClock clock)
        {
            var sw = Stopwatch.StartNew();

            // 1. Drift storm cells along local wind field
            float driftScale = simHours * 10.5f;
            for (int s = 0; s < _storms.Length; s++)
            {
                int gx = Math.Clamp((int)_storms[s].GridX, 0, SimW - 1);
                int gz = Math.Clamp((int)_storms[s].GridZ, 0, SimH - 1);
                int idx = gz * SimW + gx;
                Vector2 wDir = _baseWindDir[idx];
                float wSpd = _baseWindSpd[idx] * 0.08f;

                _storms[s].GridX = (_storms[s].GridX + wDir.X * wSpd * driftScale + SimW) % SimW;
                _storms[s].GridZ = (_storms[s].GridZ + wDir.Y * wSpd * driftScale + SimH) % SimH;
            }

            // 2. Evaluate CloudCover, Orographic RainIntensity & LiveWindSpeed
            float maxGust = 1.0f;
            for (int z = 0; z < SimH; z++)
            {
                for (int x = 0; x < SimW; x++)
                {
                    int idx = z * SimW + x;
                    float cloud = 0.10f;

                    for (int s = 0; s < _storms.Length; s++)
                    {
                        float dx = x - _storms[s].GridX;
                        float dz = z - _storms[s].GridZ;
                        if (dx > SimW * 0.5f) dx -= SimW;
                        if (dx < -SimW * 0.5f) dx += SimW;
                        if (dz > SimH * 0.5f) dz -= SimH;
                        if (dz < -SimH * 0.5f) dz += SimH;

                        float r = _storms[s].RadiusCells;
                        float d2 = (dx * dx + dz * dz) / (r * r);
                        if (d2 < 1.8f)
                            cloud += MathF.Exp(-d2 * 1.9f) * _storms[s].Intensity;
                    }

                    // Orographic boost on moist windward slopes, dissipation in dry SW rain shadow
                    float orographic = 0.45f + _basePrecip[idx] * 1.10f;
                    cloud = Math.Clamp(cloud * orographic, 0.0f, 1.0f);

                    float rain = FastNoise.SmoothStep(0.38f, 0.88f, cloud) * Math.Clamp(0.45f + _basePrecip[idx] * 0.85f, 0.2f, 1.0f);

                    if (OverrideMode == WeatherOverrideMode.ClearSun)
                    {
                        cloud = 0.04f;
                        rain = 0.0f;
                    }
                    else if (OverrideMode == WeatherOverrideMode.RainStorm)
                    {
                        cloud = Math.Clamp(0.84f + cloud * 0.16f, 0.0f, 1.0f);
                        rain = Math.Clamp(0.75f + _basePrecip[idx] * 0.25f, 0.0f, 1.0f);
                    }
                    else if (OverrideMode == WeatherOverrideMode.BlizzardOrSandstorm)
                    {
                        cloud = 0.92f;
                        rain = _aridWeight[idx] > 0.35f ? 0.05f : 0.88f;
                    }

                    _cloudCover[idx] = cloud;
                    _rainIntensity[idx] = rain;

                    float gustMult = 1.0f + cloud * 0.55f + (OverrideMode >= WeatherOverrideMode.RainStorm ? 0.45f : 0.0f);
                    _liveWindSpeed[idx] = Math.Clamp(_baseWindSpd[idx] * gustMult, 2.0f, 36.0f);
                    if (gustMult > maxGust) maxGust = gustMult;
                }
            }
            GlobalWindGust = maxGust;

            // 3. Step Surface State (LiveTemp, Snow, Wetness, Ice, RiverSurge)
            SurfaceState.Step(simHours, clock.DeltaTDayC, clock.DeltaTSeasonC, _cloudCover, _rainIntensity);

            // 4. Pack RGBA8 buffer & update GPU texture in-place
            for (int i = 0; i < SeasonalState.CellCount; i++)
            {
                int o = i * 4;
                _gpuBytes[o + 0] = (byte)(Math.Clamp(SurfaceState.SnowAccumulationMap[i], 0.0f, 1.0f) * 255.0f);
                _gpuBytes[o + 1] = (byte)(Math.Clamp(SurfaceState.WetnessMap[i], 0.0f, 1.0f) * 255.0f);
                _gpuBytes[o + 2] = (byte)(Math.Clamp(SurfaceState.SurfaceIceMap[i], 0.0f, 1.0f) * 255.0f);
                _gpuBytes[o + 3] = (byte)(Math.Clamp(_cloudCover[i], 0.0f, 1.0f) * 255.0f);
            }

            if (_weatherImage != null && _weatherTex != null)
            {
                _weatherImage.SetData(SimW, SimH, false, Image.Format.Rgba8, _gpuBytes);
                _weatherTex.Update(_weatherImage);
            }

            sw.Stop();
            LastUpdateMs = sw.Elapsed.TotalMilliseconds;
        }

        public LiveWeatherSample SampleAt(float worldX, float worldZ)
        {
            int sx = Math.Clamp((int)((worldX / WorldPhysicsConfig.WorldWidth) * (SimW - 1)), 0, SimW - 1);
            int sz = Math.Clamp((int)((worldZ / WorldPhysicsConfig.WorldDepth) * (SimH - 1)), 0, SimH - 1);
            int idx = sz * SimW + sx;

            float temp = SurfaceState.LiveTempMap[idx];
            float cloud = _cloudCover[idx];
            float rain = _rainIntensity[idx];
            float snow = SurfaceState.SnowAccumulationMap[idx];
            float wet = SurfaceState.WetnessMap[idx];
            float ice = SurfaceState.SurfaceIceMap[idx];
            float wind = _liveWindSpeed[idx];
            Vector2 wDir = _baseWindDir[idx];
            bool isArid = _aridWeight[idx] > 0.35f;

            string label = "Nắng ráo";
            if (isArid && wet < 0.18f && wind > 13.5f) label = "Bão cát đỏ";
            else if (rain > 0.12f && temp <= 0.5f) label = "Tuyết rơi";
            else if (rain > 0.12f) label = rain > 0.55f ? "Mưa bão" : "Mưa rào";
            else if (cloud > 0.45f) label = "Nhiều mây";

            return new LiveWeatherSample(temp, cloud, rain, snow, wet, ice, wind, wDir, label);
        }
    }
}
