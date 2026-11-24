using System;
using Godot;

namespace PrimevalWorld.Core
{
    public enum SeasonType : byte
    {
        Spring = 0, // Days 0..29
        Summer = 1, // Days 30..59
        Autumn = 2, // Days 60..89
        Winter = 3, // Days 90..119
    }

    /// <summary>
    /// Stage 4: Astronomical 24h Clock & 4-Season Calendar (120 days/year, 30 days/season).
    /// Computes Sun/Moon vectors with 23.4° axial tilt, DeltaT_Day and DeltaT_Season.
    /// </summary>
    public sealed class SimulationClock
    {
        public const int DaysPerSeason = 30;
        public const int DaysPerYear = 120;
        public const float AxialTiltDeg = 23.4f;

        // 1x = 1 game day in 12 real minutes (720s) -> 24h / 720s = 1/30 hour per real second
        private const float BaseHoursPerSecond = 24.0f / 720.0f;
        private static readonly float[] SpeedPresets = { 0.0f, 1.0f, 10.0f, 60.0f, 300.0f };

        private int _speedIndex = 1; // Default 1x
        private bool _paused;

        public float TimeOfDay { get; private set; } = 8.75f; // 08:45 AM cinematic oblique sun (~29° elevation)
        public int DayOfYear { get; private set; } = 15;      // Mid-Spring default
        public bool IsPaused => _paused || _speedIndex == 0;
        public float SpeedMultiplier => _paused ? 0.0f : SpeedPresets[_speedIndex];

        public float SeasonPhase => (DayOfYear + TimeOfDay / 24.0f) / DaysPerYear;
        public SeasonType CurrentSeason => (SeasonType)(Math.Clamp(DayOfYear / DaysPerSeason, 0, 3));

        public string SeasonNameVi => CurrentSeason switch
        {
            SeasonType.Spring => "Xuân",
            SeasonType.Summer => "Hạ",
            SeasonType.Autumn => "Thu",
            _ => "Đông",
        };

        public float DeltaTDayC { get; private set; }
        public float DeltaTSeasonC { get; private set; }
        public Vector3 SunDirection { get; private set; } = new Vector3(0.4f, 0.7f, 0.4f).Normalized();
        public float SunElevationDeg { get; private set; }
        public bool IsDaytime => SunDirection.Y > 0.02f;

        public SimulationClock()
        {
            UpdateAstronomicalState();
        }

        public void Advance(float realDeltaSeconds)
        {
            if (!IsPaused)
            {
                float simHours = realDeltaSeconds * BaseHoursPerSecond * SpeedPresets[_speedIndex];
                AddHours(simHours);
            }
        }

        public void AddHours(float hours)
        {
            TimeOfDay += hours;
            while (TimeOfDay >= 24.0f)
            {
                TimeOfDay -= 24.0f;
                DayOfYear = (DayOfYear + 1) % DaysPerYear;
            }
            while (TimeOfDay < 0.0f)
            {
                TimeOfDay += 24.0f;
                DayOfYear = (DayOfYear + DaysPerYear - 1) % DaysPerYear;
            }
            UpdateAstronomicalState();
        }

        public void AdvanceToNextSeason()
        {
            int nextSeason = ((int)CurrentSeason + 1) % 4;
            DayOfYear = nextSeason * DaysPerSeason + 14; // Jump to middle of next season for clear visual contrast
            UpdateAstronomicalState();
        }

        public void TogglePause() => _paused = !_paused;

        public void StepSpeed(int delta)
        {
            _paused = false;
            _speedIndex = Math.Clamp(_speedIndex + delta, 0, SpeedPresets.Length - 1);
        }

        private void UpdateAstronomicalState()
        {
            float phase = SeasonPhase;

            // Diurnal cycle: coldest ~02:30, warmest ~14:30
            DeltaTDayC = -5.5f * MathF.Cos((TimeOfDay - 14.5f) * MathF.PI / 12.0f);

            // Seasonal cycle: Summer peak around phase 0.375 (day 45), Winter trough around 0.875 (day 105)
            DeltaTSeasonC = -9.5f * MathF.Cos((phase - 0.375f) * 2.0f * MathF.PI);

            // Solar declination with 23.4° axial tilt
            float declRad = Mathf.DegToRad(AxialTiltDeg) * MathF.Sin((phase - 0.125f) * 2.0f * MathF.PI);
            float hourAngle = (TimeOfDay - 12.0f) * (MathF.PI / 12.0f);

            // Assume world latitude ~42°N so North (-Z) is cooler and midday sun arcs from the South (+Z)
            float latRad = Mathf.DegToRad(42.0f);
            float sinAlt = MathF.Sin(latRad) * MathF.Sin(declRad) + MathF.Cos(latRad) * MathF.Cos(declRad) * MathF.Cos(hourAngle);
            float altRad = MathF.Asin(Math.Clamp(sinAlt, -1.0f, 1.0f));
            SunElevationDeg = Mathf.RadToDeg(altRad);

            float dirX = -MathF.Sin(hourAngle) * MathF.Cos(declRad);
            float dirY = MathF.Sin(altRad);
            float dirZ = MathF.Cos(latRad) * MathF.Sin(declRad) - MathF.Sin(latRad) * MathF.Cos(declRad) * MathF.Cos(hourAngle);
            SunDirection = new Vector3(dirX, dirY, -dirZ).Normalized();
        }
    }
}
