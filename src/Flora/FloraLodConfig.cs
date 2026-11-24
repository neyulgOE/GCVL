using Godot;
using PrimevalWorld.Core;

namespace PrimevalWorld.Flora
{
    /// <summary>
    /// Single source of truth for all Tree LOD distance bands, crossfade widths,
    /// terrain canopy-ground blend distances, and Hierarchical Dynamic Streaming Cell dimensions.
    /// Pushed directly to shaders/flora_wind.gdshader and shaders/terrain_triplanar.gdshader.
    /// </summary>
    public static class FloraLodConfig
    {
        // Dynamic Streaming Near Grid: 150m x 150m (64 x 36) for LOD0, LOD1, and L3..L6 Detail
        // Only cells within StreamingRadiusM (<= 580m) are mounted into the SceneTree via Object Pool!
        public const float NearCellSize = 150.0f;
        public const int NearCols = (int)(WorldPhysicsConfig.WorldWidth / NearCellSize);  // 64
        public const int NearRows = (int)(WorldPhysicsConfig.WorldDepth / NearCellSize);  // 36

        public const float NearLod0MountRadiusM = 310.0f;   // Only mount LOD0 on 150m cells within 310m
        public const float NearLod1MountRadiusM = 580.0f;   // Only mount LOD1 on 150m cells within 580m
        public const float NearDetailMountRadiusM = 420.0f; // Only mount L3..L6 on 150m cells within 420m
        public const float UnmountHysteresisM = 40.0f;      // Prevents boundary thrashing when walking on cell edges

        // Macro Far Grid for LOD2: 600m x 600m (16 x 9 = 144 cells) grouped into 4 canopy archetypes
        public const float FarCellSize = 600.0f;
        public const int FarCols = (int)(WorldPhysicsConfig.WorldWidth / FarCellSize);    // 16
        public const int FarRows = (int)(WorldPhysicsConfig.WorldDepth / FarCellSize);    // 9

        // Canonical 3-Tier Woody Tree LOD Thresholds (meters)
        public const float Lod0Start = 0.0f;
        public const float Lod0End = 150.0f;

        public const float Lod1Start = 150.0f;
        public const float Lod1End = 450.0f;

        public const float Lod2Start = 450.0f;
        public const float Lod2End = 1350.0f;

        // 30m Dither Crossfade Overlap Band (+-15m):
        // LOD0 <-> LOD1 across [135m .. 165m], LOD1 <-> LOD2 across [435m .. 465m]
        public const float TransitionHalfBand = 15.0f;

        // Horizon Dissolve Band (100% synchronized between LOD2 trees and Terrain Canopy Splatting)
        public const float FarFadeStart = 1100.0f;
        public const float FarFadeEnd = 1350.0f;

        public const float CanopyGroundBlendStart = 1100.0f;
        public const float CanopyGroundBlendEnd = 1350.0f;

        // L3..L6 Understory / Shrub / Herb Dissolve
        public const float DetailFadeStart = 310.0f;
        public const float DetailFadeEnd = 400.0f;

        // VisibilityRange Hysteresis & Minimum Half-Diagonal Cell Safety Padding
        public const float CellHysteresisMargin = 25.0f;
        public const float MinNearCellDiagPad = 110.0f; // 150m cell XZ half-diag = 106.07m -> >= +110m
        public const float MinFarCellDiagPad = 430.0f;  // 600m cell XZ half-diag = 424.26m -> >= +430m

        public static void ApplyToFloraMaterial(ShaderMaterial mat, int lodLevel, bool lodDebugEnabled)
        {
            mat.SetShaderParameter("lod_level", lodLevel);
            mat.SetShaderParameter("lod_debug_mode", lodDebugEnabled ? 1 : 0);
            mat.SetShaderParameter("lod0_end", Lod0End);
            mat.SetShaderParameter("lod1_start", Lod1Start);
            mat.SetShaderParameter("lod1_end", Lod1End);
            mat.SetShaderParameter("lod2_start", Lod2Start);
            mat.SetShaderParameter("transition_half_band", TransitionHalfBand);
            mat.SetShaderParameter("far_fade_start", FarFadeStart);
            mat.SetShaderParameter("far_fade_end", FarFadeEnd);
            mat.SetShaderParameter("detail_fade_start", DetailFadeStart);
            mat.SetShaderParameter("detail_fade_end", DetailFadeEnd);
        }

        public static void ApplyToTerrainMaterial(ShaderMaterial mat)
        {
            mat.SetShaderParameter("canopy_ground_blend_start", CanopyGroundBlendStart);
            mat.SetShaderParameter("canopy_ground_blend_end", CanopyGroundBlendEnd);
        }
    }
}
