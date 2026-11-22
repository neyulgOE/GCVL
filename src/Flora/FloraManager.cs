using System;
using System.Collections.Generic;
using Godot;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Flora
{
    internal readonly struct FloraInstanceData
    {
        public readonly Transform3D Transform;
        public readonly Color Tint;

        public FloraInstanceData(Transform3D transform, Color tint)
        {
            Transform = transform;
            Tint = tint;
        }
    }

    /// <summary>
    /// 2-Phase Hierarchical Ecological MultiMesh Engine aligned with docs/VEGETATION.md
    /// and docs/Thuc_vat_dong_vat_he_sinh_thai_game_thoi_ky_do_da.docx:
    /// - 6 Ordered Layers: emergent, canopy, understory, shrub, herb_ground, litter_soil
    /// - 5 Environmental Fields: Temperature, Moisture/Riparian, Slope, SaltExposure, MegafaunaCorridor
    /// - Phase 1: Old-growth Core + Self-Thinning -> bakes CanopyShadeMap
    /// - Phase 2: Mantle, Ecotone Skirt, Shaded Understory, Riparian Palms/Ferns, Litter Logs
    /// - UseColors = true per-instance tinting, shadows ONLY on Emergent/Canopy, tiered VisibilityRangeEnd
    /// </summary>
    public partial class FloraManager : Node3D
    {
        private readonly List<MultiMeshInstance3D> _layers = new();
        private ShaderMaterial? _foliageMat;
        private ShaderMaterial? _grassMat;
        private StandardMaterial3D? _boulderMat;

        private Mesh? _sequoiaMesh;
        private Mesh? _broadleafMesh;
        private Mesh? _coniferMesh;
        private Mesh? _krummholzMesh;
        private Mesh? _autumnMesh;
        private Mesh? _desertTreeMesh;
        private Mesh? _palmMesh;
        private Mesh? _fernMesh;
        private Mesh? _shrubMesh;
        private Mesh? _grassMesh;
        private Mesh? _fallenLogMesh;
        private Mesh? _boulderMesh;

        public int TotalInstanceCount { get; private set; }

        public void BuildFlora(WorldGenerator generator)
        {
            foreach (MultiMeshInstance3D layer in _layers)
            {
                layer.QueueFree();
            }
            _layers.Clear();
            TotalInstanceCount = 0;

            EnsureAssets();

            // 6 Ordered Ecological Layers
            var sequoias = new List<FloraInstanceData>(2200);       // L1: emergent
            var broadleafs = new List<FloraInstanceData>(7500);     // L2: canopy (Primeval / Sanctuary)
            var autumns = new List<FloraInstanceData>(4200);        // L2: canopy (Autumn Ginkgo / Maple)
            var conifers = new List<FloraInstanceData>(3800);       // L2: canopy (Glacial Alpine)
            var desertTrees = new List<FloraInstanceData>(1200);    // L2: canopy (Baobab / Dragon Blood)

            var krummholz = new List<FloraInstanceData>(1200);      // L3: understory treeline
            var palms = new List<FloraInstanceData>(2200);          // L3: understory riparian/coastal
            var ferns = new List<FloraInstanceData>(8500);          // L3: understory shade/riparian

            var shrubs = new List<FloraInstanceData>(9000);         // L4: shrub (ecotone skirt)
            var grasses = new List<FloraInstanceData>(24000);       // L5: herb_ground (meadow/reeds)
            var fallenLogs = new List<FloraInstanceData>(1600);     // L6: litter_soil
            var boulders = new List<FloraInstanceData>(2600);       // L6: litter_soil

            var rng = new Random(generator.Seed + 4242);

            // Spatial Canopy Shade & Self-Thinning Grid (6m cells across 3840m x 2048m)
            const float shadeCell = 6.0f;
            int shadeW = (int)(WorldGenerator.RegionWidthMeters / shadeCell) + 1;
            int shadeD = (int)(WorldGenerator.RegionDepthMeters / shadeCell) + 1;
            float[] canopyShade = new float[shadeW * shadeD];
            bool[] treeOccupied = new bool[shadeW * shadeD];

            void AddShade(float wx, float wz, float radiusMeters, float strength)
            {
                int cx = (int)(wx / shadeCell);
                int cz = (int)(wz / shadeCell);
                int rCells = (int)MathF.Ceiling(radiusMeters / shadeCell);
                for (int dz = -rCells; dz <= rCells; dz++)
                {
                    int tz = cz + dz;
                    if (tz < 0 || tz >= shadeD) continue;
                    for (int dx = -rCells; dx <= rCells; dx++)
                    {
                        int tx = cx + dx;
                        if (tx < 0 || tx >= shadeW) continue;
                        float dist = MathF.Sqrt(dx * dx + dz * dz) * shadeCell;
                        if (dist <= radiusMeters)
                        {
                            float falloff = 1.0f - (dist / radiusMeters);
                            int idx = tz * shadeW + tx;
                            canopyShade[idx] = MathF.Min(1.0f, canopyShade[idx] + strength * falloff);
                        }
                    }
                }
            }

            // ==================================================================
            // PHASE 1: Old-Growth Core & Canopy Trees (Self-Thinning + Nucleation)
            // ==================================================================
            const float treeStep = 10.0f;
            for (float z = 60.0f; z < WorldGenerator.RegionDepthMeters - 60.0f; z += treeStep)
            {
                for (float x = 60.0f; x < WorldGenerator.RegionWidthMeters - 60.0f; x += treeStep)
                {
                    float wx = x + (float)(rng.NextDouble() - 0.5) * treeStep * 0.88f;
                    float wz = z + (float)(rng.NextDouble() - 0.5) * treeStep * 0.88f;

                    TerrainSample s = generator.SamplePoint(wx, wz);
                    Vector3 normal = generator.SampleNormal(wx, wz);
                    float slope = 1.0f - Math.Clamp(normal.Y, 0.0f, 1.0f);

                    // Skip underwater, salt-spray zone, steep cliffs (>27 deg), and open megafauna corridors
                    if (s.Height < 1.5f || s.SaltExposure > 0.72f || slope > 0.11f || s.RiverMask > 0.50f)
                        continue;

                    if (s.MegafaunaCorridor > 0.58f && s.RiverMask < 0.20f)
                        continue;

                    // Self-thinning occupancy check
                    int ox = Math.Clamp((int)(wx / shadeCell), 0, shadeW - 1);
                    int oz = Math.Clamp((int)(wz / shadeCell), 0, shadeD - 1);
                    if (treeOccupied[oz * shadeW + ox])
                        continue;

                    float yaw = (float)rng.NextDouble() * MathF.Tau;
                    float tiltX = (float)(rng.NextDouble() - 0.5) * 0.12f;
                    float tiltZ = (float)(rng.NextDouble() - 0.5) * 0.12f;

                    switch (s.Biome)
                    {
                        case BiomeId.PrimevalForest:
                        case BiomeId.SanctuaryIsland:
                        {
                            float densityReq = s.Biome == BiomeId.SanctuaryIsland ? 0.20f : 0.30f;
                            if (s.ForestDensity < densityReq && rng.NextDouble() > 0.04) continue;

                            treeOccupied[oz * shadeW + ox] = true;

                            // Layer 1 Emergent Giant Sequoia in deep core & Sanctuary Island
                            if ((s.ForestDensity > 0.62f || s.Biome == BiomeId.SanctuaryIsland) && rng.NextDouble() < 0.24)
                            {
                                float sc = 0.85f + (float)rng.NextDouble() * 0.50f;
                                Color tint = VaryGreenTint(rng, 0.88f, 1.10f);
                                sequoias.Add(new FloraInstanceData(MakeTreeTransform(wx, s.Height - 0.25f, wz, yaw, sc, tiltX, tiltZ, normal, 0.05f), tint));
                                AddShade(wx, wz, 18.0f, 0.85f);
                            }
                            else
                            {
                                // Layer 2 Wide Primeval Broadleaf (non-uniform crown stretch for organic closure)
                                float sc = 0.78f + (float)rng.NextDouble() * 0.62f;
                                Color tint = VaryGreenTint(rng, 0.78f, 1.18f);
                                broadleafs.Add(new FloraInstanceData(MakeTreeTransform(wx, s.Height - 0.25f, wz, yaw, sc, tiltX, tiltZ, normal, 0.08f), tint));
                                AddShade(wx, wz, 14.0f, 0.75f);
                            }
                            break;
                        }

                        case BiomeId.AutumnSteppe:
                        {
                            // Open savanna (70% open) -> groves along streams & sheltered hills
                            if (s.ForestDensity < 0.36f && s.RiverMask < 0.12f && rng.NextDouble() > 0.03) continue;
                            treeOccupied[oz * shadeW + ox] = true;

                            float sc = 0.72f + (float)rng.NextDouble() * 0.65f;
                            // Shift instance tint between bright golden Ginkgo, burnt orange, & crimson Maple!
                            float rRoll = (float)rng.NextDouble();
                            Color tint = rRoll < 0.45f
                                ? new Color(1.05f, 0.95f, 0.65f)   // Golden Ginkgo
                                : (rRoll < 0.80f
                                    ? new Color(1.05f, 0.62f, 0.32f) // Burnt Amber
                                    : new Color(0.95f, 0.34f, 0.22f)); // Crimson Maple
                            autumns.Add(new FloraInstanceData(MakeTreeTransform(wx, s.Height - 0.20f, wz, yaw, sc, tiltX, tiltZ, normal, 0.08f), tint));
                            AddShade(wx, wz, 12.0f, 0.65f);
                            break;
                        }

                        case BiomeId.GlacialAlpine:
                        {
                            // Treeline limit controlled by TemperatureMap & altitude
                            if (s.Temperature < 0.18f || s.Height > 46.0f) continue;
                            if (s.ForestDensity < 0.26f && rng.NextDouble() > 0.08) continue;
                            treeOccupied[oz * shadeW + ox] = true;

                            if (s.Height > 36.0f || s.Temperature < 0.26f)
                            {
                                // Treeline Krummholz dwarf wind-twisted pine
                                float sc = 0.75f + (float)rng.NextDouble() * 0.55f;
                                Color tint = new Color(0.85f, 0.95f, 0.98f);
                                krummholz.Add(new FloraInstanceData(MakeTreeTransform(wx, s.Height - 0.12f, wz, yaw, sc, tiltX * 1.5f, tiltZ * 1.5f, normal, 0.35f), tint));
                            }
                            else
                            {
                                float sc = 0.78f + (float)rng.NextDouble() * 0.62f;
                                Color tint = new Color(0.80f + (float)rng.NextDouble() * 0.25f, 0.92f + (float)rng.NextDouble() * 0.18f, 0.95f);
                                conifers.Add(new FloraInstanceData(MakeTreeTransform(wx, s.Height - 0.20f, wz, yaw, sc, tiltX, tiltZ, normal, 0.06f), tint));
                                AddShade(wx, wz, 10.0f, 0.60f);
                            }
                            break;
                        }

                        case BiomeId.TerracottaDesert:
                        {
                            // Oasis palms ring the wet oasis; Baobab / Dragon Blood on rocky terraces
                            if (s.Moisture > 0.52f)
                            {
                                treeOccupied[oz * shadeW + ox] = true;
                                float sc = 0.85f + (float)rng.NextDouble() * 0.55f;
                                palms.Add(new FloraInstanceData(MakeTreeTransform(wx, s.Height - 0.15f, wz, yaw, sc, tiltX, tiltZ, normal, 0.12f), new Color(0.95f, 1.02f, 0.88f)));
                                AddShade(wx, wz, 9.0f, 0.50f);
                            }
                            else if (s.Height > 12.0f && s.Height < 38.0f && rng.NextDouble() < 0.14)
                            {
                                treeOccupied[oz * shadeW + ox] = true;
                                float sc = 0.82f + (float)rng.NextDouble() * 0.60f;
                                Color tint = new Color(0.92f + (float)rng.NextDouble() * 0.16f, 0.88f, 0.76f);
                                desertTrees.Add(new FloraInstanceData(MakeTreeTransform(wx, s.Height - 0.20f, wz, yaw, sc, tiltX, tiltZ, normal, 0.08f), tint));
                                AddShade(wx, wz, 10.0f, 0.45f);
                            }
                            break;
                        }
                    }
                }
            }

            // ==================================================================
            // PHASE 2: Mantle, Ecotone Skirt, Shaded Understory, Ground & Litter
            // ==================================================================
            const float groundStep = 5.5f;
            for (float z = 64.0f; z < WorldGenerator.RegionDepthMeters - 64.0f; z += groundStep)
            {
                for (float x = 64.0f; x < WorldGenerator.RegionWidthMeters - 64.0f; x += groundStep)
                {
                    float wx = x + (float)(rng.NextDouble() - 0.5) * groundStep * 0.90f;
                    float wz = z + (float)(rng.NextDouble() - 0.5) * groundStep * 0.90f;

                    TerrainSample s = generator.SamplePoint(wx, wz);
                    Vector3 normal = generator.SampleNormal(wx, wz);
                    float slope = 1.0f - Math.Clamp(normal.Y, 0.0f, 1.0f);

                    // Layer 6 Boulders: riverbanks, cliff bases, rocky shores
                    if ((s.RiverMask > 0.16f && s.RiverMask < 0.68f && rng.NextDouble() < 0.12)
                        || (slope > 0.08f && slope < 0.26f && s.Height > 1.2f && s.Height < 75.0f && rng.NextDouble() < 0.08)
                        || (s.Height > -0.3f && s.Height < 2.2f && s.CoastalMask > 0.30f && rng.NextDouble() < 0.06))
                    {
                        float bSc = 0.75f + (float)rng.NextDouble() * 1.55f;
                        Color bTint = s.Biome == BiomeId.TerracottaDesert
                            ? new Color(1.22f, 0.82f, 0.62f)
                            : new Color(0.88f + (float)rng.NextDouble() * 0.22f, 0.90f, 0.92f);
                        boulders.Add(new FloraInstanceData(MakeTreeTransform(wx, s.Height - 0.18f, wz, (float)rng.NextDouble() * MathF.Tau, bSc, 0, 0, normal, 0.35f), bTint));
                    }

                    if (s.Height < 1.1f || s.Height > 46.0f || slope > 0.135f || s.RiverMask > 0.56f)
                        continue;

                    int sx = Math.Clamp((int)(wx / shadeCell), 0, shadeW - 1);
                    int sz = Math.Clamp((int)(wz / shadeCell), 0, shadeD - 1);
                    float shade = canopyShade[sz * shadeW + sx];
                    float yaw = (float)rng.NextDouble() * MathF.Tau;

                    // Coastal Salt-Spray Palms around Sanctuary Island & sheltered Tropical Bays
                    if ((s.Biome == BiomeId.SanctuaryIsland || s.Biome == BiomeId.PrimevalForest)
                        && s.SaltExposure > 0.35f && s.Height > 1.2f && s.Height < 6.5f && rng.NextDouble() < 0.24)
                    {
                        palms.Add(new FloraInstanceData(MakeTreeTransform(wx, s.Height - 0.15f, wz, yaw, 0.82f + (float)rng.NextDouble() * 0.50f, 0, 0, normal, 0.15f), VaryGreenTint(rng, 0.85f, 1.10f)));
                        continue;
                    }

                    // Riparian Gallery & Shaded Core (shade > 0.42 or near water): Layer 3 Tree Ferns & Layer 6 Fallen Logs
                    if ((shade > 0.42f || s.RiverMask > 0.12f) && s.Biome != BiomeId.GlacialAlpine && s.Height < 30.0f)
                    {
                        if (rng.NextDouble() < 0.32)
                        {
                            ferns.Add(new FloraInstanceData(MakeTreeTransform(wx, s.Height - 0.05f, wz, yaw, 0.80f + (float)rng.NextDouble() * 0.75f, 0, 0, normal, 0.22f), VaryGreenTint(rng, 0.78f, 1.15f)));
                            continue;
                        }
                        if (shade > 0.55f && rng.NextDouble() < 0.08 && fallenLogs.Count < 1550)
                        {
                            fallenLogs.Add(new FloraInstanceData(MakeTreeTransform(wx, s.Height - 0.04f, wz, yaw, 0.85f + (float)rng.NextDouble() * 0.65f, 0, 0, normal, 0.45f), new Color(0.95f, 0.92f, 0.85f)));
                            continue;
                        }
                    }

                    // Ecotone Skirt (0.12 < shade <= 0.45): Shrubs bridging forest to meadow
                    if (shade > 0.10f && shade <= 0.48f && rng.NextDouble() < 0.32)
                    {
                        Color shTint = s.Biome == BiomeId.AutumnSteppe
                            ? new Color(1.15f, 0.78f, 0.35f)
                            : (s.Biome == BiomeId.TerracottaDesert ? new Color(0.85f, 0.82f, 0.62f) : VaryGreenTint(rng, 0.80f, 1.15f));
                        shrubs.Add(new FloraInstanceData(MakeTreeTransform(wx, s.Height - 0.08f, wz, yaw, 0.75f + (float)rng.NextDouble() * 0.65f, 0, 0, normal, 0.20f), shTint));
                        continue;
                    }

                    // Layer 5 Herb / Grass / Reeds (meadows, riverbanks, autumn steppes)
                    if (s.Biome == BiomeId.TerracottaDesert && s.Moisture < 0.48f && rng.NextDouble() > 0.06)
                        continue;

                    if (grasses.Count < 28000 && s.Height < 38.0f && rng.NextDouble() < 0.56)
                    {
                        Color gTint = s.Biome switch
                        {
                            BiomeId.AutumnSteppe => new Color(1.18f, 0.82f, 0.34f), // Golden steppe grass
                            BiomeId.GlacialAlpine => new Color(0.75f, 0.85f, 0.70f),
                            BiomeId.TerracottaDesert => new Color(0.95f, 0.85f, 0.55f),
                            _ => VaryGreenTint(rng, 0.82f, 1.16f),
                        };
                        grasses.Add(new FloraInstanceData(MakeTreeTransform(wx, s.Height - 0.05f, wz, yaw, 0.85f + (float)rng.NextDouble() * 0.75f, 0, 0, normal, 0.30f), gTint));
                    }
                }
            }

            // Build MultiMeshInstance3D Layers (Shadows ONLY on L1 Emergent & L2 Canopy!)
            CreateMultiMeshLayer("L1_Emergent_Sequoias", _sequoiaMesh!, _foliageMat!, sequoias, true, 0.0f);
            CreateMultiMeshLayer("L2_Canopy_Broadleaf", _broadleafMesh!, _foliageMat!, broadleafs, true, 2200.0f);
            CreateMultiMeshLayer("L2_Canopy_Autumn", _autumnMesh!, _foliageMat!, autumns, true, 2200.0f);
            CreateMultiMeshLayer("L2_Canopy_Conifer", _coniferMesh!, _foliageMat!, conifers, true, 2200.0f);
            CreateMultiMeshLayer("L2_Canopy_Desert", _desertTreeMesh!, _foliageMat!, desertTrees, true, 2000.0f);

            CreateMultiMeshLayer("L3_Understory_Krummholz", _krummholzMesh!, _foliageMat!, krummholz, false, 500.0f);
            CreateMultiMeshLayer("L3_Understory_Palms", _palmMesh!, _foliageMat!, palms, false, 950.0f);
            CreateMultiMeshLayer("L3_Understory_TreeFerns", _fernMesh!, _foliageMat!, ferns, false, 400.0f);

            CreateMultiMeshLayer("L4_Shrub_Ecotone", _shrubMesh!, _foliageMat!, shrubs, false, 340.0f);
            CreateMultiMeshLayer("L5_Herb_GrassReeds", _grassMesh!, _grassMat!, grasses, false, 240.0f);
            CreateMultiMeshLayer("L6_Litter_FallenLogs", _fallenLogMesh!, _boulderMat!, fallenLogs, false, 240.0f);
            CreateMultiMeshLayer("L6_Litter_Boulders", _boulderMesh!, _boulderMat!, boulders, false, 650.0f);

            GD.Print($"[PrimevalFlora] 6-Layer Ecological Census (Total: {TotalInstanceCount:N0}): " +
                     $"L1_Emergent={sequoias.Count} | L2_Canopy={broadleafs.Count + autumns.Count + conifers.Count + desertTrees.Count} " +
                     $"(Broadleaf={broadleafs.Count}, Autumn={autumns.Count}, Conifer={conifers.Count}, Desert={desertTrees.Count}) | " +
                     $"L3_Understory={krummholz.Count + palms.Count + ferns.Count} | L4_Shrub={shrubs.Count} | " +
                     $"L5_Herb={grasses.Count} | L6_Litter={fallenLogs.Count + boulders.Count}");
        }

        private void EnsureAssets()
        {
            if (_foliageMat == null)
            {
                var windShader = GD.Load<Shader>("res://shaders/foliage_wind.gdshader");
                _foliageMat = new ShaderMaterial { Shader = windShader };
                _foliageMat.SetShaderParameter("wind_speed", 1.45f);
                _foliageMat.SetShaderParameter("wind_strength", 0.14f);
                _foliageMat.SetShaderParameter("enable_distance_fade", false);

                _grassMat = new ShaderMaterial { Shader = windShader };
                _grassMat.SetShaderParameter("wind_speed", 2.0f);
                _grassMat.SetShaderParameter("wind_strength", 0.22f);
                _grassMat.SetShaderParameter("enable_distance_fade", true);
                _grassMat.SetShaderParameter("fade_start", 160.0f);
                _grassMat.SetShaderParameter("fade_end", 235.0f);

                _boulderMat = new StandardMaterial3D
                {
                    VertexColorUseAsAlbedo = true,
                    Roughness = 0.85f,
                };
            }

            _sequoiaMesh ??= LoadGlbOrFallback("sequoia", FloraMeshBuilder.CreateGiantSequoiaMesh);
            _broadleafMesh ??= LoadGlbOrFallback("broadleaf", FloraMeshBuilder.CreatePrimevalBroadleafMesh);
            _autumnMesh ??= LoadGlbOrFallback("autumn", FloraMeshBuilder.CreateAutumnDeciduousMesh);
            _coniferMesh ??= LoadGlbOrFallback("conifer", FloraMeshBuilder.CreateAlpineConiferMesh);
            _krummholzMesh ??= LoadGlbOrFallback("krummholz", FloraMeshBuilder.CreateKrummholzMesh);
            _desertTreeMesh ??= LoadGlbOrFallback("baobab", FloraMeshBuilder.CreateDesertUmbrellaTreeMesh);
            _palmMesh ??= LoadGlbOrFallback("palm", FloraMeshBuilder.CreatePalmMesh);
            _fernMesh ??= LoadGlbOrFallback("fern", FloraMeshBuilder.CreateTreeFernMesh);
            _shrubMesh ??= LoadGlbOrFallback("shrub", FloraMeshBuilder.CreateShrubMesh);
            _grassMesh ??= LoadGlbOrFallback("grass", FloraMeshBuilder.CreateGrassClumpMesh);
            _fallenLogMesh ??= LoadGlbOrFallback("fallen_log", FloraMeshBuilder.CreateFallenLogMesh);
            _boulderMesh ??= LoadGlbOrFallback("boulder", FloraMeshBuilder.CreateBoulderMesh);
        }

        private static Mesh LoadGlbOrFallback(string modelName, Func<ArrayMesh> fallback)
        {
            string glbPath = $"res://assets/models/flora/{modelName}.glb";
            if (ResourceLoader.Exists(glbPath))
            {
                var packed = GD.Load<PackedScene>(glbPath);
                if (packed != null)
                {
                    Node root = packed.Instantiate();
                    Mesh? found = FindFirstMesh(root);
                    root.QueueFree();
                    if (found != null) return found;
                }
            }
            return fallback();
        }

        private static Mesh? FindFirstMesh(Node node)
        {
            if (node is MeshInstance3D mi && mi.Mesh != null) return mi.Mesh;
            foreach (Node child in node.GetChildren())
            {
                Mesh? found = FindFirstMesh(child);
                if (found != null) return found;
            }
            return null;
        }

        private void CreateMultiMeshLayer(
            string layerName,
            Mesh mesh,
            Material material,
            List<FloraInstanceData> items,
            bool castShadows,
            float visibilityEnd)
        {
            if (items.Count == 0) return;

            var multiMesh = new MultiMesh
            {
                TransformFormat = MultiMesh.TransformFormatEnum.Transform3D,
                UseColors = true,
                Mesh = mesh,
                InstanceCount = items.Count,
            };

            for (int i = 0; i < items.Count; i++)
            {
                multiMesh.SetInstanceTransform(i, items[i].Transform);
                multiMesh.SetInstanceColor(i, items[i].Tint);
            }

            var instance = new MultiMeshInstance3D
            {
                Name = layerName,
                Multimesh = multiMesh,
                MaterialOverride = material,
                CastShadow = castShadows
                    ? GeometryInstance3D.ShadowCastingSetting.On
                    : GeometryInstance3D.ShadowCastingSetting.Off,
            };

            if (visibilityEnd > 0.0f)
            {
                instance.VisibilityRangeEnd = visibilityEnd;
                instance.VisibilityRangeEndMargin = 25.0f;
            }

            AddChild(instance);
            _layers.Add(instance);
            TotalInstanceCount += items.Count;
        }

        private static Color VaryGreenTint(Random rng, float minVal, float maxVal)
        {
            float v = minVal + (float)rng.NextDouble() * (maxVal - minVal);
            float warmShift = (float)(rng.NextDouble() - 0.5) * 0.14f;
            return new Color(v + warmShift, v, v - warmShift * 0.5f, 1.0f);
        }

        private static Transform3D MakeTreeTransform(
            float x, float y, float z, float yaw, float scale, float tiltX, float tiltZ, Vector3 terrainNormal, float alignToSlope)
        {
            Vector3 up = Vector3.Up.Lerp(terrainNormal, alignToSlope).Normalized();
            Basis basis = Basis.Identity.Rotated(Vector3.Up, yaw)
                                        .Rotated(Vector3.Right, tiltX)
                                        .Rotated(Vector3.Forward, tiltZ);
            Quaternion tilt = new Quaternion(Vector3.Up, up);
            basis = (new Basis(tilt) * basis).Scaled(new Vector3(scale, scale, scale));
            return new Transform3D(basis, new Vector3(x, y, z));
        }
    }
}
