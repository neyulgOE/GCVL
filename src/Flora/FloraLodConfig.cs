using Godot;
using PrimevalWorld.Core;

namespace PrimevalWorld.Flora
{
    /// <summary>
    /// Single source of truth for all Tree LOD distance bands, crossfade widths,
    /// terrain canopy-ground blend distances, and Hierarchical Sparse Cell dimensions.
    /// Pushed directly to shaders/flora_wind.gdshader and shaders/terrain_triplanar.gdshader.
    /// </summary>
    public static class FloraLodConfig
    {
        // Hierarchical Sparse Cell Grid Dimensions
        // LOD0 + LOD1 use 150m x 150m cells (64 x 36); LOD2 uses 300m x 300m cells (32 x 18).
        public const float NearCellSize = 150.0f;
        public const int NearCols = (int)(WorldPhysicsConfig.WorldWidth / NearCellSize);  // 64
        public const int NearRows = (int)(WorldPhysicsConfig.WorldDepth / NearCellSize);  // 36

        public const float FarCellSize = 300.0f;
        public const int FarCols = (int)(WorldPhysicsConfig.WorldWidth / FarCellSize);    // 32
        public const int FarRows = (int)(WorldPhysicsConfig.WorldDepth / FarCellSize);    // 18

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

        // L3..L6 Understory / Shrub / Herb Streaming & Dissolve
        public const int DetailStreamRadiusCells = 2; // ~375m radius around camera cell
        public const float DetailFadeStart = 310.0f;
        public const float DetailFadeEnd = 400.0f;

        // VisibilityRange Hysteresis & Minimum Half-Diagonal Cell Safety Padding
        public const float CellHysteresisMargin = 25.0f;
        public const float MinNearCellDiagPad = 110.0f; // 150m cell XZ half-diag = 106.07m -> >= +110m
        public const float MinFarCellDiagPad = 215.0f;  // 300m cell XZ half-diag = 212.13m -> >= +215m

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
