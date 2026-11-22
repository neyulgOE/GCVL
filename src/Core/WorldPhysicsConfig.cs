using System;
using Godot;

namespace PrimevalWorld.Core
{
    /// <summary>
    /// Central SI-unit physical constants and 16:9 grid/LOD configuration
    /// for the 9.6 x 5.4 km (~51.8 km2) Primeval Reach world.
    /// </summary>
    public static class WorldPhysicsConfig
    {
        // World Dimensions (exact 16:9, float32 safe)
        public const float WorldWidth = 9600.0f;   // X (meters)
        public const float WorldDepth = 5400.0f;   // Z (meters)

        // Physics Simulation Grid (1024 x 576 cells = 1025 x 577 vertices)
        public const int GridW = 1024;
        public const int GridH = 576;
        public const int VertW = GridW + 1;        // 1025
        public const int VertH = GridH + 1;        // 577
        public const float CellSize = 9.375f;      // 9600 / 1024 = 5400 / 576 = 9.375m

        // 4-Level Terrain Chunk Grid (32 x 18 = 576 chunks, each 300m x 300m = 32 x 32 cells)
        public const int ChunksX = 32;
        public const int ChunksZ = 18;
        public const int CellsPerChunk = 32;
        public const float ChunkSize = CellsPerChunk * CellSize; // 300.0m

        // LOD Distance Thresholds (meters)
        public const float Lod0Dist = 750.0f;
        public const float Lod1Dist = 1800.0f;
        public const float Lod2Dist = 3800.0f;
        public const float SkirtDepth = 24.0f;

        // Elevation & Ocean Constants (meters)
        public const float MaxMountainHeight = 460.0f;
        public const float SeaLevel = 0.0f;
        public const float MaxOceanDepth = -65.0f;

        // Atmospheric & Geological Physics Constants (SI)
        public const float Gravity = 9.81f;
        public const float LapseRate = 0.048f; // °C drop per meter (450m peak ~21.6°C colder)
        public const float SandReposeDeg = 32.0f;
        public const float SoilReposeDeg = 40.0f;
        public const float RockReposeDeg = 64.0f;

        public static readonly float SandTanRepose = MathF.Tan(Mathf.DegToRad(SandReposeDeg));
        public static readonly float SoilTanRepose = MathF.Tan(Mathf.DegToRad(SoilReposeDeg));
        public static readonly float RockTanRepose = MathF.Tan(Mathf.DegToRad(RockReposeDeg));

        // Horizon & Camera Constants
        public const float HorizonOceanSize = 48000.0f;
        public const float CameraFar = 16000.0f;
        public const float MaxFlySpeed = 1000.0f;
    }
}
