using System;
using System.Collections.Generic;
using Godot;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Flora
{
    /// <summary>
    /// Prehistoric Ecological MultiMesh Distributor (45,000-65,000 instances at 80+ FPS):
    /// - Supports automatic .glb mesh override from res://assets/models/flora/<name>.glb
    ///   with crisp low-poly procedural fallback.
    /// - Sub-cell clumping for dense continuous forest canopies + open megafauna corridors.
    /// - Biome-specific silhouettes (Redwood, Broadleaf, Golden Ginkgo, Crimson Maple,
    ///   Alpine Spruce, Baobab/Dragon Blood, Oasis Palm, Tree Fern, Shrubs, Grass, Boulders).
    /// - Shadows disabled on grass/ferns/shrubs/boulders + VisibilityRangeEnd culling.
    /// </summary>
    public partial class FloraManager : Node3D
    {
        private readonly List<MultiMeshInstance3D> _layers = new();
        private ShaderMaterial? _foliageMat;
        private ShaderMaterial? _grassMat;
        private StandardMaterial3D? _boulderMat;

        private Mesh? _redwoodMesh;
        private Mesh? _broadleafMesh;
        private Mesh? _ginkgoMesh;
        private Mesh? _mapleMesh;
        private Mesh? _coniferMesh;
        private Mesh? _desertTreeMesh;
        private Mesh? _palmMesh;
        private Mesh? _fernMesh;
        private Mesh? _shrubMesh;
        private Mesh? _grassMesh;
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

            var redwoods = new List<Transform3D>(2200);
            var broadleafs = new List<Transform3D>(6500);
            var ginkgos = new List<Transform3D>(2400);
            var maples = new List<Transform3D>(2200);
            var conifers = new List<Transform3D>(3200);
            var desertTrees = new List<Transform3D>(900);
            var palms = new List<Transform3D>(900);
            var ferns = new List<Transform3D>(7500);
            var shrubs = new List<Transform3D>(7500);
            var grasses = new List<Transform3D>(24000);
            var boulders = new List<Transform3D>(2800);

            var rng = new Random(generator.Seed + 4242);

            // 1. Canopy Trees + Sub-Cell Clumping + Boulders (18m coarse grid across 3072m x 3072m)
            const float treeStep = 18.0f;
            for (float z = 90.0f; z < WorldGenerator.RegionSizeMeters - 90.0f; z += treeStep)
            {
                for (float x = 90.0f; x < WorldGenerator.RegionSizeMeters - 90.0f; x += treeStep)
                {
                    float wx = x + (float)(rng.NextDouble() - 0.5) * treeStep * 0.90f;
                    float wz = z + (float)(rng.NextDouble() - 0.5) * treeStep * 0.90f;

                    TerrainSample s = generator.SamplePoint(wx, wz);
                    Vector3 normal = generator.SampleNormal(wx, wz);
                    float slope = 1.0f - Math.Clamp(normal.Y, 0.0f, 1.0f);

                    // Boulders on riverbanks, cliff bases, & rocky shores
                    bool nearRiver = s.RiverMask > 0.16f && s.RiverMask < 0.72f;
                    bool cliffBase = slope > 0.075f && slope < 0.25f && s.Height > 1.2f && s.Height < 75.0f;
                    bool rockyShore = s.Height > -0.3f && s.Height < 2.4f && s.CoastalMask > 0.30f;

                    if ((nearRiver && rng.NextDouble() < 0.16)
                        || (cliffBase && rng.NextDouble() < 0.12)
                        || (rockyShore && rng.NextDouble() < 0.08))
                    {
                        float bScale = 0.75f + (float)rng.NextDouble() * 1.65f;
                        boulders.Add(MakeTransform(wx, s.Height - 0.18f, wz, (float)rng.NextDouble() * MathF.Tau, bScale, normal, 0.35f));
                    }

                    // Trees forbidden underwater, on beaches, steep cliffs (>27 deg), or snow peaks
                    if (s.Height < 1.6f || s.Height > 54.0f || slope > 0.11f || s.RiverMask > 0.52f)
                        continue;

                    if (s.ForestDensity < 0.28f && rng.NextDouble() > 0.03)
                        continue;

                    float yaw = (float)rng.NextDouble() * MathF.Tau;

                    switch (s.Biome)
                    {
                        case BiomeId.PrimevalForest:
                        case BiomeId.SanctuaryIsland:
                        {
                            // Emergent Giant Redwoods in deep forest core + Sanctuary Island
                            if ((s.ForestDensity > 0.68f || s.Biome == BiomeId.SanctuaryIsland) && rng.NextDouble() < 0.26)
                            {
                                float rScale = 0.90f + (float)rng.NextDouble() * 0.55f;
                                redwoods.Add(MakeTransform(wx, s.Height - 0.2f, wz, yaw, rScale, normal, 0.06f));
                            }
                            else
                            {
                                float bScale = 0.85f + (float)rng.NextDouble() * 0.70f;
                                broadleafs.Add(MakeTransform(wx, s.Height - 0.2f, wz, yaw, bScale, normal, 0.10f));
                            }

                            // Sub-cell clumping: add 1-2 satellite broadleaf/fern neighbors to close the canopy
                            int clumpCount = s.ForestDensity > 0.58f ? 2 : 1;
                            for (int c = 0; c < clumpCount; c++)
                            {
                                float ox = wx + (float)(rng.NextDouble() - 0.5) * 11.0f;
                                float oz = wz + (float)(rng.NextDouble() - 0.5) * 11.0f;
                                TerrainSample cs = generator.SamplePoint(ox, oz);
                                if (cs.Height > 1.6f && cs.RiverMask < 0.50f)
                                {
                                    broadleafs.Add(MakeTransform(ox, cs.Height - 0.2f, oz,
                                        (float)rng.NextDouble() * MathF.Tau, 0.68f + (float)rng.NextDouble() * 0.55f, normal, 0.10f));
                                }
                            }
                            break;
                        }

                        case BiomeId.AutumnSteppe:
                        {
                            if (rng.NextDouble() < 0.55)
                            {
                                ginkgos.Add(MakeTransform(wx, s.Height - 0.2f, wz, yaw, 0.80f + (float)rng.NextDouble() * 0.65f, normal, 0.10f));
                            }
                            else
                            {
                                maples.Add(MakeTransform(wx, s.Height - 0.2f, wz, yaw, 0.78f + (float)rng.NextDouble() * 0.60f, normal, 0.10f));
                            }

                            // Sub-cell autumn grove clustering
                            if (s.ForestDensity > 0.48f)
                            {
                                float ox = wx + (float)(rng.NextDouble() - 0.5) * 10.0f;
                                float oz = wz + (float)(rng.NextDouble() - 0.5) * 10.0f;
                                TerrainSample cs = generator.SamplePoint(ox, oz);
                                if (cs.Height > 2.0f)
                                {
                                    var target = rng.NextDouble() < 0.5 ? ginkgos : maples;
                                    target.Add(MakeTransform(ox, cs.Height - 0.2f, oz,
                                        (float)rng.NextDouble() * MathF.Tau, 0.70f + (float)rng.NextDouble() * 0.50f, normal, 0.10f));
                                }
                            }
                            break;
                        }

                        case BiomeId.GlacialAlpine:
                        {
                            if (s.Height < 44.0f)
                            {
                                conifers.Add(MakeTransform(wx, s.Height - 0.2f, wz, yaw, 0.85f + (float)rng.NextDouble() * 0.65f, normal, 0.08f));
                                if (s.ForestDensity > 0.50f)
                                {
                                    float ox = wx + (float)(rng.NextDouble() - 0.5) * 9.5f;
                                    float oz = wz + (float)(rng.NextDouble() - 0.5) * 9.5f;
                                    TerrainSample cs = generator.SamplePoint(ox, oz);
                                    if (cs.Height > 2.0f && cs.Height < 44.0f)
                                    {
                                        conifers.Add(MakeTransform(ox, cs.Height - 0.2f, oz,
                                            (float)rng.NextDouble() * MathF.Tau, 0.72f + (float)rng.NextDouble() * 0.50f, normal, 0.08f));
                                    }
                                }
                            }
                            break;
                        }

                        case BiomeId.TerracottaDesert:
                        {
                            // Lush palms tightly clustered around the turquoise oasis
                            if (s.Moisture > 0.55f)
                            {
                                palms.Add(MakeTransform(wx, s.Height - 0.15f, wz, yaw, 0.85f + (float)rng.NextDouble() * 0.55f, normal, 0.12f));
                                float ox = wx + (float)(rng.NextDouble() - 0.5) * 9.0f;
                                float oz = wz + (float)(rng.NextDouble() - 0.5) * 9.0f;
                                TerrainSample cs = generator.SamplePoint(ox, oz);
                                if (cs.Height > 1.2f)
                                {
                                    palms.Add(MakeTransform(ox, cs.Height - 0.15f, oz,
                                        (float)rng.NextDouble() * MathF.Tau, 0.75f + (float)rng.NextDouble() * 0.45f, normal, 0.12f));
                                }
                            }
                            // Sparse umbrella Baobab / Dragon Blood trees on desert ridges
                            else if (rng.NextDouble() < 0.45)
                            {
                                desertTrees.Add(MakeTransform(wx, s.Height - 0.2f, wz, yaw, 0.85f + (float)rng.NextDouble() * 0.60f, normal, 0.08f));
                            }
                            break;
                        }
                    }
                }
            }

            // 2. Dense Understory Ferns, Shrubs & Tall Grass (11m grid with multi-clump fill -> ~40k instances)
            const float groundStep = 11.0f;
            for (float z = 100.0f; z < WorldGenerator.RegionSizeMeters - 100.0f; z += groundStep)
            {
                for (float x = 100.0f; x < WorldGenerator.RegionSizeMeters - 100.0f; x += groundStep)
                {
                    float wx = x + (float)(rng.NextDouble() - 0.5) * groundStep * 0.88f;
                    float wz = z + (float)(rng.NextDouble() - 0.5) * groundStep * 0.88f;

                    TerrainSample s = generator.SamplePoint(wx, wz);
                    if (s.Height < 1.3f || s.Height > 44.0f || s.RiverMask > 0.58f)
                        continue;

                    Vector3 normal = generator.SampleNormal(wx, wz);
                    float slope = 1.0f - Math.Clamp(normal.Y, 0.0f, 1.0f);
                    if (slope > 0.13f)
                        continue;

                    // Keep desert dunes mostly open except oasis rim
                    if (s.Biome == BiomeId.TerracottaDesert && s.Moisture < 0.48f && rng.NextDouble() > 0.08)
                        continue;

                    float yaw = (float)rng.NextDouble() * MathF.Tau;

                    if ((s.RiverMask > 0.10f || s.ForestDensity > 0.45f) && s.Height < 30.0f && rng.NextDouble() < 0.28)
                    {
                        ferns.Add(MakeTransform(wx, s.Height - 0.05f, wz, yaw, 0.85f + (float)rng.NextDouble() * 0.70f, normal, 0.25f));
                    }
                    else if (s.ForestDensity > 0.25f && rng.NextDouble() < 0.22)
                    {
                        shrubs.Add(MakeTransform(wx, s.Height - 0.08f, wz, yaw, 0.80f + (float)rng.NextDouble() * 0.65f, normal, 0.20f));
                    }
                    else if (grasses.Count < 23500 && s.Height < 36.0f && rng.NextDouble() < 0.58)
                    {
                        grasses.Add(MakeTransform(wx, s.Height - 0.05f, wz, yaw, 0.90f + (float)rng.NextDouble() * 0.75f, normal, 0.35f));
                    }
                }
            }

            // Canopy trees cast shadows (with generous visibility); understory/grass/boulders skip shadows for 80+ FPS
            CreateMultiMeshLayer("GiantRedwoods", _redwoodMesh!, _foliageMat!, redwoods, true, 0.0f);
            CreateMultiMeshLayer("PrimevalBroadleafs", _broadleafMesh!, _foliageMat!, broadleafs, true, 1600.0f);
            CreateMultiMeshLayer("AutumnGinkgos", _ginkgoMesh!, _foliageMat!, ginkgos, true, 1600.0f);
            CreateMultiMeshLayer("AutumnMaples", _mapleMesh!, _foliageMat!, maples, true, 1600.0f);
            CreateMultiMeshLayer("AlpineConifers", _coniferMesh!, _foliageMat!, conifers, true, 1600.0f);
            CreateMultiMeshLayer("DesertBaobabs", _desertTreeMesh!, _foliageMat!, desertTrees, true, 1600.0f);
            CreateMultiMeshLayer("OasisPalms", _palmMesh!, _foliageMat!, palms, true, 1400.0f);

            CreateMultiMeshLayer("TreeFerns", _fernMesh!, _foliageMat!, ferns, false, 360.0f);
            CreateMultiMeshLayer("ForestShrubs", _shrubMesh!, _foliageMat!, shrubs, false, 380.0f);
            CreateMultiMeshLayer("MeadowGrass", _grassMesh!, _grassMat!, grasses, false, 260.0f);
            CreateMultiMeshLayer("TerrainBoulders", _boulderMesh!, _boulderMat!, boulders, false, 650.0f);
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
                _grassMat.SetShaderParameter("fade_start", 170.0f);
                _grassMat.SetShaderParameter("fade_end", 255.0f);

                _boulderMat = new StandardMaterial3D
                {
                    VertexColorUseAsAlbedo = true,
                    Roughness = 0.85f,
                };
            }

            _redwoodMesh ??= LoadGlbOrFallback("redwood", FloraMeshBuilder.CreateRedwoodMesh);
            _broadleafMesh ??= LoadGlbOrFallback("broadleaf", FloraMeshBuilder.CreateBroadleafTreeMesh);
            _ginkgoMesh ??= LoadGlbOrFallback("ginkgo", () => FloraMeshBuilder.CreateAutumnTreeMesh(false));
            _mapleMesh ??= LoadGlbOrFallback("maple", () => FloraMeshBuilder.CreateAutumnTreeMesh(true));
            _coniferMesh ??= LoadGlbOrFallback("conifer", FloraMeshBuilder.CreateConiferMesh);
            _desertTreeMesh ??= LoadGlbOrFallback("baobab", FloraMeshBuilder.CreateDesertTreeMesh);
            _palmMesh ??= LoadGlbOrFallback("palm", FloraMeshBuilder.CreatePalmMesh);
            _fernMesh ??= LoadGlbOrFallback("fern", FloraMeshBuilder.CreateFernMesh);
            _shrubMesh ??= LoadGlbOrFallback("shrub", FloraMeshBuilder.CreateShrubMesh);
            _grassMesh ??= LoadGlbOrFallback("grass", FloraMeshBuilder.CreateGrassClumpMesh);
            _boulderMesh ??= LoadGlbOrFallback("boulder", FloraMeshBuilder.CreateBoulderMesh);
        }

        /// <summary>
        /// Checks res://assets/models/flora/<name>.glb first so high-detail 3D models
        /// can drop in seamlessly; otherwise builds the lightweight procedural mesh.
        /// </summary>
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
            List<Transform3D> transforms,
            bool castShadows,
            float visibilityEnd)
        {
            if (transforms.Count == 0) return;

            var multiMesh = new MultiMesh
            {
                TransformFormat = MultiMesh.TransformFormatEnum.Transform3D,
                Mesh = mesh,
                InstanceCount = transforms.Count,
            };

            for (int i = 0; i < transforms.Count; i++)
            {
                multiMesh.SetInstanceTransform(i, transforms[i]);
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
            TotalInstanceCount += transforms.Count;
        }

        private static Transform3D MakeTransform(
            float x, float y, float z, float yaw, float scale, Vector3 terrainNormal, float alignToSlope)
        {
            Vector3 up = Vector3.Up.Lerp(terrainNormal, alignToSlope).Normalized();
            Basis basis = Basis.Identity.Rotated(Vector3.Up, yaw);
            Quaternion tilt = new Quaternion(Vector3.Up, up);
            basis = (new Basis(tilt) * basis).Scaled(new Vector3(scale, scale, scale));
            return new Transform3D(basis, new Vector3(x, y, z));
        }
    }
}
