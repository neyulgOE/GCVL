using System;
using System.Collections.Generic;
using Godot;
using PrimevalWorld.Core;
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
    /// Optional Stage 1+2 Flora preview layer (toggled via [F], default OFF during geology/soil inspection;
    /// will be upgraded with Spatial Streaming in Stage 3).
    /// </summary>
    public partial class FloraManager : Node3D
    {
        private readonly List<MultiMeshInstance3D> _layers = new();
        private ShaderMaterial? _foliageMat;
        private Mesh? _broadleafMesh;
        private Mesh? _autumnMesh;
        private Mesh? _coniferMesh;
        private Mesh? _desertTreeMesh;
        private Mesh? _palmMesh;

        private readonly FloraNicheProfile[] _canopyNiches =
        {
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.PrimevalBroadleaf,
                IdealTempC = 18.0f, TempTolerance = 9.5f,
                IdealMoisture = 0.66f, MoistureTolerance = 0.30f,
                MaxWindSpeed = 16.5f, MaxSlope = 0.28f, MinSoilDepth = 0.25f, SalinityTolerance = 0.35f,
                SoilAffinities = new[] { 0.95f, 1.0f, 0.25f, 0.04f, 0.10f, 0.02f }
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.AutumnGinkgo,
                IdealTempC = 11.5f, TempTolerance = 7.5f,
                IdealMoisture = 0.46f, MoistureTolerance = 0.28f,
                MaxWindSpeed = 18.5f, MaxSlope = 0.30f, MinSoilDepth = 0.22f, SalinityTolerance = 0.25f,
                SoilAffinities = new[] { 0.45f, 0.75f, 1.0f, 0.10f, 0.05f, 0.05f }
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.AlpineConifer,
                IdealTempC = 2.0f, TempTolerance = 8.5f,
                IdealMoisture = 0.55f, MoistureTolerance = 0.32f,
                MaxWindSpeed = 22.0f, MaxSlope = 0.32f, MinSoilDepth = 0.12f, SalinityTolerance = 0.30f,
                SoilAffinities = new[] { 0.30f, 0.65f, 0.65f, 0.02f, 0.05f, 0.95f }
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.DesertBaobab,
                IdealTempC = 27.0f, TempTolerance = 8.5f,
                IdealMoisture = 0.22f, MoistureTolerance = 0.24f,
                MaxWindSpeed = 20.0f, MaxSlope = 0.30f, MinSoilDepth = 0.12f, SalinityTolerance = 0.35f,
                SoilAffinities = new[] { 0.15f, 0.20f, 0.35f, 1.0f, 0.20f, 0.10f }
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.OasisPalm,
                IdealTempC = 23.0f, TempTolerance = 8.0f,
                IdealMoisture = 0.72f, MoistureTolerance = 0.28f,
                MaxWindSpeed = 19.0f, MaxSlope = 0.26f, MinSoilDepth = 0.12f, SalinityTolerance = 1.0f,
                SoilAffinities = new[] { 0.85f, 0.35f, 0.10f, 0.45f, 1.0f, 0.02f }
            },
        };

        public int TotalInstanceCount { get; private set; }

        public void ClearFlora()
        {
            foreach (MultiMeshInstance3D layer in _layers)
                layer.QueueFree();
            _layers.Clear();
            TotalInstanceCount = 0;
        }

        public ImageTexture BuildEmptyCoverageTexture()
        {
            byte[] zero = new byte[64 * 64];
            return ImageTexture.CreateFromImage(Image.CreateFromData(64, 64, false, Image.Format.L8, zero));
        }

        public ImageTexture BuildFlora(
            ErosionPhysics erosion,
            HydrologySolver hydrology,
            AtmosphereClimate climate,
            SoilPedology soil,
            int seed)
        {
            ClearFlora();
            EnsureAssets(climate);

            var broadleafs = new List<FloraInstanceData>(6000);
            var ginkgos = new List<FloraInstanceData>(4000);
            var conifers = new List<FloraInstanceData>(6000);
            var desertTrees = new List<FloraInstanceData>(2500);
            var palms = new List<FloraInstanceData>(1500);

            var rng = new Random(seed + 4242);
            const float step = 28.0f;
            float[] scores = new float[_canopyNiches.Length];

            for (float z = 120.0f; z < WorldPhysicsConfig.WorldDepth - 120.0f; z += step)
            {
                for (float x = 120.0f; x < WorldPhysicsConfig.WorldWidth - 120.0f; x += step)
                {
                    float wx = x + (float)(rng.NextDouble() - 0.5) * step * 0.85f;
                    float wz = z + (float)(rng.NextDouble() - 0.5) * step * 0.85f;
                    float h = erosion.SampleHeight(wx, wz);
                    if (h < 2.0f || hydrology.SampleRiverMask(wx, wz) > 0.50f) continue;

                    float slopeNorm = 1.0f - Math.Clamp(MathF.Cos(Mathf.DegToRad(erosion.SampleSlopeDeg(wx, wz))), 0.0f, 1.0f);
                    ClimateSample cs = climate.SampleClimate(wx, wz);
                    SoilSample ss = soil.SampleSoil(wx, wz);

                    // Evaluate niche profile using continuous soil weights
                    float total = 0.0f;
                    float maxSc = 0.0f;
                    for (int i = 0; i < _canopyNiches.Length; i++)
                    {
                        var n = _canopyNiches[i];
                        if (slopeNorm > n.MaxSlope || ss.SoilDepth < n.MinSoilDepth || cs.WindSpeed > n.MaxWindSpeed)
                        {
                            scores[i] = 0.0f;
                            continue;
                        }
                        float tDiff = (cs.TemperatureC - n.IdealTempC) / n.TempTolerance;
                        float mDiff = (cs.Moisture - n.IdealMoisture) / n.MoistureTolerance;
                        float sScore = ss.WAlluvial * n.SoilAffinities[0]
                                     + ss.WForestBrown * n.SoilAffinities[1]
                                     + ss.WSteppeLoess * n.SoilAffinities[2]
                                     + ss.WAridRed * n.SoilAffinities[3]
                                     + ss.WCoastalSand * n.SoilAffinities[4]
                                     + ss.WPermafrostRock * n.SoilAffinities[5];
                        float sc = MathF.Exp(-tDiff * tDiff * 1.3f) * MathF.Exp(-mDiff * mDiff * 1.2f) * MathF.Max(0.02f, sScore);
                        scores[i] = sc;
                        total += sc;
                        if (sc > maxSc) maxSc = sc;
                    }

                    if (maxSc < 0.08f || rng.NextDouble() > Math.Clamp(maxSc * 1.4f, 0.05f, 0.90f))
                        continue;

                    float pick = (float)rng.NextDouble() * total;
                    float acc = 0.0f;
                    int chosen = 0;
                    for (int i = 0; i < _canopyNiches.Length; i++)
                    {
                        acc += scores[i];
                        if (pick <= acc) { chosen = i; break; }
                    }

                    float yaw = (float)rng.NextDouble() * MathF.Tau;
                    float scale = 1.15f + (float)rng.NextDouble() * 0.85f;
                    var xf = new Transform3D(Basis.Identity.Rotated(Vector3.Up, yaw).Scaled(new Vector3(scale, scale, scale)), new Vector3(wx, h - 0.3f, wz));

                    switch (_canopyNiches[chosen].Id)
                    {
                        case FloraSpeciesId.PrimevalBroadleaf:
                            broadleafs.Add(new FloraInstanceData(xf, new Color(0.85f, 1.0f, 0.85f)));
                            break;
                        case FloraSpeciesId.AutumnGinkgo:
                            ginkgos.Add(new FloraInstanceData(xf, new Color(1.05f, 0.90f, 0.55f)));
                            break;
                        case FloraSpeciesId.AlpineConifer:
                            conifers.Add(new FloraInstanceData(xf, new Color(0.85f, 0.95f, 0.98f)));
                            break;
                        case FloraSpeciesId.DesertBaobab:
                            desertTrees.Add(new FloraInstanceData(xf, new Color(0.95f, 0.88f, 0.74f)));
                            break;
                        case FloraSpeciesId.OasisPalm:
                            palms.Add(new FloraInstanceData(xf, new Color(0.92f, 1.04f, 0.86f)));
                            break;
                    }
                }
            }

            CreateLayer("Broadleaf", _broadleafMesh!, broadleafs, 2600.0f);
            CreateLayer("Ginkgo", _autumnMesh!, ginkgos, 2600.0f);
            CreateLayer("Conifer", _coniferMesh!, conifers, 2600.0f);
            CreateLayer("Baobab", _desertTreeMesh!, desertTrees, 2400.0f);
            CreateLayer("Palm", _palmMesh!, palms, 2000.0f);

            return BuildEmptyCoverageTexture();
        }

        private void EnsureAssets(AtmosphereClimate climate)
        {
            if (_foliageMat == null)
            {
                var windShader = GD.Load<Shader>("res://shaders/foliage_wind.gdshader");
                _foliageMat = new ShaderMaterial { Shader = windShader };
                _foliageMat.SetShaderParameter("wind_speed", 1.45f);
                _foliageMat.SetShaderParameter("wind_strength", 0.16f);
                _foliageMat.SetShaderParameter("enable_distance_fade", false);
            }
            _foliageMat.SetShaderParameter("wind_dir", climate.GlobalPrevailingWind);

            _broadleafMesh ??= FloraMeshBuilder.CreatePrimevalBroadleafMesh();
            _autumnMesh ??= FloraMeshBuilder.CreateAutumnDeciduousMesh();
            _coniferMesh ??= FloraMeshBuilder.CreateAlpineConiferMesh();
            _desertTreeMesh ??= FloraMeshBuilder.CreateDesertUmbrellaTreeMesh();
            _palmMesh ??= FloraMeshBuilder.CreatePalmMesh();
        }

        private void CreateLayer(string name, Mesh mesh, List<FloraInstanceData> items, float visEnd)
        {
            if (items.Count == 0) return;
            var mm = new MultiMesh
            {
                TransformFormat = MultiMesh.TransformFormatEnum.Transform3D,
                UseColors = true,
                Mesh = mesh,
                InstanceCount = items.Count,
            };
            for (int i = 0; i < items.Count; i++)
            {
                mm.SetInstanceTransform(i, items[i].Transform);
                mm.SetInstanceColor(i, items[i].Tint);
            }
            var mmi = new MultiMeshInstance3D
            {
                Name = name,
                Multimesh = mm,
                MaterialOverride = _foliageMat,
                CastShadow = GeometryInstance3D.ShadowCastingSetting.On,
                VisibilityRangeEnd = visEnd,
                VisibilityRangeEndMargin = 80.0f,
            };
            AddChild(mmi);
            _layers.Add(mmi);
            TotalInstanceCount += items.Count;
        }
    }
}
