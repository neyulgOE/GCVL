using System;
using System.Collections.Generic;
using Godot;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Flora
{
    /// <summary>
    /// Stage 2 Ecological MultiMesh Distributor:
    /// Scatters procedural Broadleaf Trees, Conifers, Ferns, Shrubs, Grass Clumps, and Boulders
    /// across the 2x2 km terrain using forest grove clustering, riparian corridors,
    /// slope/altitude limits, and distance VisibilityRangeEnd culling.
    /// </summary>
    public partial class FloraManager : Node3D
    {
        private readonly List<MultiMeshInstance3D> _layers = new();
        private ShaderMaterial? _foliageMat;
        private ShaderMaterial? _grassMat;
        private StandardMaterial3D? _boulderMat;

        private Mesh? _coniferMesh;
        private Mesh? _broadleafMesh;
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

            var conifers = new List<Transform3D>(3500);
            var broadleafs = new List<Transform3D>(3500);
            var ferns = new List<Transform3D>(4500);
            var shrubs = new List<Transform3D>(4500);
            var grasses = new List<Transform3D>(14000);
            var boulders = new List<Transform3D>(2000);

            var rng = new Random(generator.Seed + 4242);

            // 1. Trees & Boulders pass (14m stratified grid with organic jitter)
            const float treeStep = 14.0f;
            for (float z = 80.0f; z < WorldGenerator.RegionSizeMeters - 80.0f; z += treeStep)
            {
                for (float x = 80.0f; x < WorldGenerator.RegionSizeMeters - 80.0f; x += treeStep)
                {
                    float wx = x + (float)(rng.NextDouble() - 0.5) * treeStep * 0.92f;
                    float wz = z + (float)(rng.NextDouble() - 0.5) * treeStep * 0.92f;

                    TerrainSample s = generator.SamplePoint(wx, wz);
                    Vector3 normal = generator.SampleNormal(wx, wz);
                    float slope = 1.0f - Math.Clamp(normal.Y, 0.0f, 1.0f); // > 0.115 is ~28 deg

                    // Boulders: along riverbanks, cliff bases, or rocky shores
                    bool nearRiver = s.RiverMask > 0.18f && s.RiverMask < 0.72f;
                    bool cliffBase = slope > 0.075f && slope < 0.24f && s.Height > 1.2f && s.Height < 65.0f;
                    bool rockyShore = s.Height > -0.3f && s.Height < 2.2f && s.CoastalMask > 0.35f;

                    if ((nearRiver && rng.NextDouble() < 0.14)
                        || (cliffBase && rng.NextDouble() < 0.10)
                        || (rockyShore && rng.NextDouble() < 0.07))
                    {
                        float bScale = 0.65f + (float)rng.NextDouble() * 1.45f;
                        boulders.Add(MakeTransform(wx, s.Height - 0.15f, wz, (float)rng.NextDouble() * MathF.Tau, bScale, normal, 0.35f));
                    }

                    // Trees forbidden underwater, on sandy beaches, on steep cliffs (>27 deg), or snow peaks
                    if (s.Height < 1.8f || s.Height > 52.0f || slope > 0.11f || s.RiverMask > 0.55f)
                        continue;

                    // Clustered Forest Groves + Riparian Corridors
                    float groveThreshold = 0.44f - s.RiverMask * 0.25f;
                    if (s.ForestDensity < groveThreshold && rng.NextDouble() > 0.04)
                        continue;

                    float yaw = (float)rng.NextDouble() * MathF.Tau;

                    // Species zonation by altitude & moisture
                    if (s.Height > 26.0f || (s.Height > 17.0f && s.Moisture < 0.52f))
                    {
                        float scale = 0.85f + (float)rng.NextDouble() * 0.65f;
                        conifers.Add(MakeTransform(wx, s.Height - 0.15f, wz, yaw, scale, normal, 0.12f));
                    }
                    else
                    {
                        float scale = 0.82f + (float)rng.NextDouble() * 0.68f;
                        broadleafs.Add(MakeTransform(wx, s.Height - 0.15f, wz, yaw, scale, normal, 0.10f));
                    }
                }
            }

            // 2. Understory Ferns, Shrubs & Grass Clumps pass (9m stratified grid)
            const float groundStep = 9.0f;
            for (float z = 90.0f; z < WorldGenerator.RegionSizeMeters - 90.0f; z += groundStep)
            {
                for (float x = 90.0f; x < WorldGenerator.RegionSizeMeters - 90.0f; x += groundStep)
                {
                    float wx = x + (float)(rng.NextDouble() - 0.5) * groundStep * 0.90f;
                    float wz = z + (float)(rng.NextDouble() - 0.5) * groundStep * 0.90f;

                    TerrainSample s = generator.SamplePoint(wx, wz);
                    if (s.Height < 1.3f || s.Height > 44.0f || s.RiverMask > 0.62f)
                        continue;

                    Vector3 normal = generator.SampleNormal(wx, wz);
                    float slope = 1.0f - Math.Clamp(normal.Y, 0.0f, 1.0f);
                    if (slope > 0.125f)
                        continue;

                    float yaw = (float)rng.NextDouble() * MathF.Tau;

                    // Ferns thrive along moist riverbanks & shaded woodland understory
                    if ((s.RiverMask > 0.10f || s.ForestDensity > 0.42f) && s.Height < 28.0f && rng.NextDouble() < 0.34)
                    {
                        float fScale = 0.75f + (float)rng.NextDouble() * 0.65f;
                        ferns.Add(MakeTransform(wx, s.Height - 0.05f, wz, yaw, fScale, normal, 0.25f));
                    }
                    // Shrubs along forest edges & moist clearings
                    else if (s.ForestDensity > 0.28f && s.ForestDensity < 0.78f && rng.NextDouble() < 0.22)
                    {
                        float shScale = 0.70f + (float)rng.NextDouble() * 0.60f;
                        shrubs.Add(MakeTransform(wx, s.Height - 0.08f, wz, yaw, shScale, normal, 0.20f));
                    }
                    // Grass clumps across open meadows & woodland edges (capped for steady frame times)
                    else if (grasses.Count < 13500 && s.Height < 34.0f && rng.NextDouble() < 0.48)
                    {
                        float gScale = 0.85f + (float)rng.NextDouble() * 0.75f;
                        grasses.Add(MakeTransform(wx, s.Height - 0.05f, wz, yaw, gScale, normal, 0.35f));
                    }
                }
            }

            CreateMultiMeshLayer("BroadleafTrees", _broadleafMesh!, _foliageMat!, broadleafs, true, 0.0f);
            CreateMultiMeshLayer("AlpineConifers", _coniferMesh!, _foliageMat!, conifers, true, 0.0f);
            CreateMultiMeshLayer("RiverbankFerns", _fernMesh!, _foliageMat!, ferns, true, 360.0f);
            CreateMultiMeshLayer("ForestShrubs", _shrubMesh!, _foliageMat!, shrubs, true, 380.0f);
            CreateMultiMeshLayer("MeadowGrass", _grassMesh!, _grassMat!, grasses, false, 260.0f);
            CreateMultiMeshLayer("TerrainBoulders", _boulderMesh!, _boulderMat!, boulders, true, 750.0f);
        }

        private void EnsureAssets()
        {
            if (_foliageMat == null)
            {
                var windShader = GD.Load<Shader>("res://shaders/foliage_wind.gdshader");
                _foliageMat = new ShaderMaterial { Shader = windShader };
                _foliageMat.SetShaderParameter("wind_speed", 1.5f);
                _foliageMat.SetShaderParameter("wind_strength", 0.16f);
                _foliageMat.SetShaderParameter("enable_distance_fade", false);

                _grassMat = new ShaderMaterial { Shader = windShader };
                _grassMat.SetShaderParameter("wind_speed", 2.1f);
                _grassMat.SetShaderParameter("wind_strength", 0.24f);
                _grassMat.SetShaderParameter("enable_distance_fade", true);
                _grassMat.SetShaderParameter("fade_start", 170.0f);
                _grassMat.SetShaderParameter("fade_end", 255.0f);

                _boulderMat = new StandardMaterial3D
                {
                    VertexColorUseAsAlbedo = true,
                    Roughness = 0.84f,
                };
            }

            _coniferMesh ??= FloraMeshBuilder.CreateConiferMesh();
            _broadleafMesh ??= FloraMeshBuilder.CreateBroadleafTreeMesh();
            _fernMesh ??= FloraMeshBuilder.CreateFernMesh();
            _shrubMesh ??= FloraMeshBuilder.CreateShrubMesh();
            _grassMesh ??= FloraMeshBuilder.CreateGrassClumpMesh();
            _boulderMesh ??= FloraMeshBuilder.CreateBoulderMesh();
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
