using System;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Flora
{
    public enum FloraSpeciesId
    {
        GiantSequoia = 0,
        PrimevalBroadleaf = 1,
        AutumnGinkgo = 2,
        AutumnMaple = 3,
        AlpineConifer = 4,
        DesertBaobab = 5,
        OasisPalm = 6,
        KrummholzPine = 7,
        TreeFern = 8,
    }

    /// <summary>
    /// Declarative ecological niche profile for a prehistoric plant species.
    /// Replaces hardcoded biome checks with physical environmental suitability scoring.
    /// </summary>
    public sealed class FloraNicheProfile
    {
        public FloraSpeciesId Id { get; init; }
        public float IdealTempC { get; init; }
        public float TempTolerance { get; init; }
        public float IdealMoisture { get; init; }
        public float MoistureTolerance { get; init; }
        public float MaxWindSpeed { get; init; }
        public float MaxSlope { get; init; }
        public float MinSoilDepth { get; init; }
        public float SalinityTolerance { get; init; } // 0 = sensitive to salt, 1 = thrives in coastal salt spray

        // Affinity weights for [AlluvialLoam, ForestBrown, SteppeLoess, AridRedSand, CoastalSand, PermafrostRock]
        public float[] SoilAffinities { get; init; } = new float[6];

        public float EvaluateSuitability(
            in ClimateSample climate,
            in SoilSample soil,
            float slope)
        {
            if (slope > MaxSlope || soil.SoilDepth < MinSoilDepth || climate.WindSpeed > MaxWindSpeed)
                return 0.0f;

            // Gaussian temperature & moisture curves
            float tDiff = (climate.TemperatureC - IdealTempC) / TempTolerance;
            float tScore = MathF.Exp(-tDiff * tDiff * 1.4f);
            if (tScore < 0.05f) return 0.0f;

            float mDiff = (climate.Moisture - IdealMoisture) / MoistureTolerance;
            float mScore = MathF.Exp(-mDiff * mDiff * 1.3f);
            if (mScore < 0.05f) return 0.0f;

            // Salinity penalty if species is not salt-tolerant
            float salPenalty = soil.CoastalSalinity > SalinityTolerance
                ? MathF.Max(0.0f, 1.0f - (soil.CoastalSalinity - SalinityTolerance) * 2.5f)
                : 1.0f;
            if (salPenalty <= 0.02f) return 0.0f;

            // Wind stress fade near MaxWindSpeed
            float windScore = 1.0f - FastNoise.SmoothStep(MaxWindSpeed * 0.65f, MaxWindSpeed, climate.WindSpeed) * 0.5f;

            // Soil affinity dot product
            float soilScore =
                soil.WAlluvial * SoilAffinities[0] +
                soil.WForestBrown * SoilAffinities[1] +
                soil.WSteppeLoess * SoilAffinities[2] +
                soil.WAridRed * SoilAffinities[3] +
                soil.WCoastalSand * SoilAffinities[4] +
                soil.WPermafrostRock * SoilAffinities[5];

            return tScore * mScore * salPenalty * windScore * MathF.Max(0.02f, soilScore);
        }
    }
}
