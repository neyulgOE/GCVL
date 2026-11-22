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
    /// Tier 4: Causal Ecological Niche MultiMesh Engine.
    /// Places 20,000-26,000 Emergent/Canopy trees + Understory + Shrubs + Grass + Litter
    /// purely by scoring FloraNicheProfiles against ClimateSimulator & SoilSimulator fields.
    /// Zero hardcoded biome_id if/else chains!
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

        private readonly FloraNicheProfile[] _canopyNiches =
        {
            // 0. Giant Sequoia: warm-temperate, high moisture, deep alluvial/forest soil, sheltered from extreme wind
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.GiantSequoia,
                IdealTempC = 17.5f, TempTolerance = 8.5f,
                IdealMoisture = 0.78f, MoistureTolerance = 0.25f,
                MaxWindSpeed = 14.5f, MaxSlope = 0.09f, MinSoilDepth = 0.45f, SalinityTolerance = 0.25f,
                SoilAffinities = new[] { 1.0f, 0.85f, 0.10f, 0.02f, 0.05f, 0.01f }
            },
            // 1. Primeval Broadleaf: mild-warm, moist alluvial & brown forest soil
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.PrimevalBroadleaf,
                IdealTempC = 18.0f, TempTolerance = 9.5f,
                IdealMoisture = 0.66f, MoistureTolerance = 0.30f,
                MaxWindSpeed = 16.5f, MaxSlope = 0.11f, MinSoilDepth = 0.30f, SalinityTolerance = 0.35f,
                SoilAffinities = new[] { 0.95f, 1.0f, 0.25f, 0.04f, 0.10f, 0.02f }
            },
            // 2. Autumn Ginkgo: cool-temperate, moderate moisture, thrives in SteppeLoess & ForestBrown
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.AutumnGinkgo,
                IdealTempC = 11.5f, TempTolerance = 7.0f,
                IdealMoisture = 0.46f, MoistureTolerance = 0.26f,
                MaxWindSpeed = 18.0f, MaxSlope = 0.115f, MinSoilDepth = 0.26f, SalinityTolerance = 0.25f,
                SoilAffinities = new[] { 0.45f, 0.75f, 1.0f, 0.10f, 0.05f, 0.05f }
            },
            // 3. Autumn Maple: slightly more moisture-loving companion on SteppeLoess / ForestBrown
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.AutumnMaple,
                IdealTempC = 12.5f, TempTolerance = 6.5f,
                IdealMoisture = 0.54f, MoistureTolerance = 0.24f,
                MaxWindSpeed = 17.0f, MaxSlope = 0.11f, MinSoilDepth = 0.28f, SalinityTolerance = 0.20f,
                SoilAffinities = new[] { 0.60f, 0.85f, 0.95f, 0.05f, 0.05f, 0.05f }
            },
            // 4. Alpine Conifer: cold-tolerant, handles thin permafrost/rock soil & brisk mountain wind
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.AlpineConifer,
                IdealTempC = 2.0f, TempTolerance = 8.5f,
                IdealMoisture = 0.55f, MoistureTolerance = 0.32f,
                MaxWindSpeed = 21.0f, MaxSlope = 0.135f, MinSoilDepth = 0.14f, SalinityTolerance = 0.30f,
                SoilAffinities = new[] { 0.30f, 0.65f, 0.65f, 0.02f, 0.05f, 0.95f }
            },
            // 5. Desert Baobab / Dragon Blood: hot, semi-arid red sand & rocky wadis
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.DesertBaobab,
                IdealTempC = 27.0f, TempTolerance = 8.0f,
                IdealMoisture = 0.22f, MoistureTolerance = 0.22f,
                MaxWindSpeed = 19.5f, MaxSlope = 0.12f, MinSoilDepth = 0.15f, SalinityTolerance = 0.35f,
                SoilAffinities = new[] { 0.15f, 0.20f, 0.35f, 1.0f, 0.20f, 0.10f }
            },
            // 6. Oasis & Coastal Palm: warm, tolerates high coastal salinity OR wet desert oases!
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.OasisPalm,
                IdealTempC = 23.0f, TempTolerance = 7.5f,
                IdealMoisture = 0.72f, MoistureTolerance = 0.28f,
                MaxWindSpeed = 18.5f, MaxSlope = 0.10f, MinSoilDepth = 0.15f, SalinityTolerance = 1.0f,
                SoilAffinities = new[] { 0.85f, 0.35f, 0.10f, 0.45f, 1.0f, 0.02f }
            },
        };

        public int TotalInstanceCount { get; private set; }

        public ImageTexture BuildFlora(WorldGenerator terrain, ClimateSimulator climate, SoilSimulator soil)
        {
            foreach (MultiMeshInstance3D layer in _layers)
            {
                layer.QueueFree();
            }
            _layers.Clear();
            TotalInstanceCount = 0;

            EnsureAssets(climate);

            var sequoias = new List<FloraInstanceData>(4000);
            var broadleafs = new List<FloraInstanceData>(12000);
            var ginkgos = new List<FloraInstanceData>(4500);
            var maples = new List<FloraInstanceData>(4000);
            var conifers = new List<FloraInstanceData>(5500);
            var desertTrees = new List<FloraInstanceData>(2500);
            var palms = new List<FloraInstanceData>(3500);

            var krummholz = new List<FloraInstanceData>(1800);
            var ferns = new List<FloraInstanceData>(6500);
            var shrubs = new List<FloraInstanceData>(5500);
            var grasses = new List<FloraInstanceData>(13000);
            var fallenLogs = new List<FloraInstanceData>(1600);
            var boulders = new List<FloraInstanceData>(2400);

            var rng = new Random(terrain.Seed + 4242);

            const float shadeCell = 8.0f;
            int shadeW = (int)(WorldGenerator.RegionWidthMeters / shadeCell) + 1;
            int shadeD = (int)(WorldGenerator.RegionDepthMeters / shadeCell) + 1;
            float[] canopyShade = new float[shadeW * shadeD];

            const float occCell = 4.0f;
            int occW = (int)(WorldGenerator.RegionWidthMeters / occCell) + 1;
            int occD = (int)(WorldGenerator.RegionDepthMeters / occCell) + 1;
            bool[] treeOccupied = new bool[occW * occD];

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
            // PHASE 1: Ecological Niche Canopy Placement (Target: 20,000-26,000 trees!)
            // ==================================================================
            const float treeStep = 6.2f;
            float[] scores = new float[_canopyNiches.Length];

            for (float z = 48.0f; z < WorldGenerator.RegionDepthMeters - 48.0f; z += treeStep)
            {
                for (float x = 48.0f; x < WorldGenerator.RegionWidthMeters - 48.0f; x += treeStep)
                {
                    float wx = x + (float)(rng.NextDouble() - 0.5) * treeStep * 0.90f;
                    float wz = z + (float)(rng.NextDouble() - 0.5) * treeStep * 0.90f;

                    float h = terrain.SampleHeight(wx, wz);
                    float riverMask = terrain.SampleRiverMask(wx, wz);
                    if (h < 1.1f || riverMask > 0.52f) continue;

                    Vector3 normal = terrain.SampleNormal(wx, wz);
                    float slope = 1.0f - Math.Clamp(normal.Y, 0.0f, 1.0f);
                    ClimateSample cs = climate.SampleClimate(wx, wz);
                    SoilSample ss = soil.SampleSoil(wx, wz);

                    // Score every canopy species against physical climate & soil
                    float totalScore = 0.0f;
                    float maxScore = 0.0f;
                    for (int i = 0; i < _canopyNiches.Length; i++)
                    {
                        float sc = _canopyNiches[i].EvaluateSuitability(cs, ss, slope);
                        scores[i] = sc;
                        totalScore += sc;
                        if (sc > maxScore) maxScore = sc;
                    }

                    // Natural grove clumping + open wind-swept meadows/dunes
                    float groveNoise = FastNoise.Fbm2D(wx * 0.0026f + 13.7f, wz * 0.0026f - 5.2f, terrain.Seed + 907, 4);
                    float densityGate = maxScore * (0.62f + groveNoise * 0.65f);
                    if (densityGate < 0.08f || rng.NextDouble() > Math.Clamp(densityGate * 1.65f, 0.08f, 0.96f))
                    {
                        // Cold windy treeline check for Krummholz dwarf pines
                        if (cs.TemperatureC > -5.5f && cs.TemperatureC < 1.5f && slope < 0.14f && ss.SoilDepth > 0.08f && rng.NextDouble() < 0.25)
                        {
                            float kSc = 0.75f + (float)rng.NextDouble() * 0.55f;
                            krummholz.Add(new FloraInstanceData(
                                MakeTreeTransform(wx, h - 0.10f, wz, (float)rng.NextDouble() * MathF.Tau, kSc, 0, 0, normal, 0.35f),
                                new Color(0.84f, 0.94f, 0.96f)));
                        }
                        continue;
                    }

                    int ox = Math.Clamp((int)(wx / occCell), 0, occW - 1);
                    int oz = Math.Clamp((int)(wz / occCell), 0, occD - 1);
                    if (treeOccupied[oz * occW + ox]) continue;
                    treeOccupied[oz * occW + ox] = true;

                    // Weighted random selection among suitable species -> natural mixed transition zones!
                    float pick = (float)rng.NextDouble() * totalScore;
                    float accum = 0.0f;
                    int chosenIdx = 0;
                    for (int i = 0; i < _canopyNiches.Length; i++)
                    {
                        accum += scores[i];
                        if (pick <= accum)
                        {
                            chosenIdx = i;
                            break;
                        }
                    }

                    float yaw = (float)rng.NextDouble() * MathF.Tau;
                    float tiltX = (float)(rng.NextDouble() - 0.5) * 0.12f;
                    float tiltZ = (float)(rng.NextDouble() - 0.5) * 0.12f;

                    switch (_canopyNiches[chosenIdx].Id)
                    {
                        case FloraSpeciesId.GiantSequoia:
                        {
                            float sc = 0.85f + (float)rng.NextDouble() * 0.50f;
                            sequoias.Add(new FloraInstanceData(MakeTreeTransform(wx, h - 0.25f, wz, yaw, sc, tiltX, tiltZ, normal, 0.05f), VaryGreenTint(rng, 0.86f, 1.12f)));
                            AddShade(wx, wz, 18.0f, 0.85f);
                            break;
                        }
                        case FloraSpeciesId.PrimevalBroadleaf:
                        {
                            float sc = 0.78f + (float)rng.NextDouble() * 0.62f;
                            broadleafs.Add(new FloraInstanceData(MakeTreeTransform(wx, h - 0.25f, wz, yaw, sc, tiltX, tiltZ, normal, 0.08f), VaryGreenTint(rng, 0.76f, 1.18f)));
                            AddShade(wx, wz, 14.0f, 0.75f);
                            break;
                        }
                        case FloraSpeciesId.AutumnGinkgo:
                        {
                            float sc = 0.74f + (float)rng.NextDouble() * 0.60f;
                            ginkgos.Add(new FloraInstanceData(MakeTreeTransform(wx, h - 0.20f, wz, yaw, sc, tiltX, tiltZ, normal, 0.08f),
                                new Color(1.04f, 0.92f + (float)rng.NextDouble() * 0.12f, 0.58f)));
                            AddShade(wx, wz, 12.0f, 0.62f);
                            break;
                        }
                        case FloraSpeciesId.AutumnMaple:
                        {
                            float sc = 0.74f + (float)rng.NextDouble() * 0.60f;
                            Color tint = rng.NextDouble() < 0.5 ? new Color(1.05f, 0.60f, 0.30f) : new Color(0.96f, 0.32f, 0.20f);
                            maples.Add(new FloraInstanceData(MakeTreeTransform(wx, h - 0.20f, wz, yaw, sc, tiltX, tiltZ, normal, 0.08f), tint));
                            AddShade(wx, wz, 12.0f, 0.62f);
                            break;
                        }
                        case FloraSpeciesId.AlpineConifer:
                        {
                            float sc = 0.75f + (float)rng.NextDouble() * 0.62f;
                            conifers.Add(new FloraInstanceData(MakeTreeTransform(wx, h - 0.20f, wz, yaw, sc, tiltX, tiltZ, normal, 0.06f),
                                new Color(0.80f + (float)rng.NextDouble() * 0.24f, 0.92f + (float)rng.NextDouble() * 0.16f, 0.96f)));
                            AddShade(wx, wz, 10.0f, 0.58f);
                            break;
                        }
                        case FloraSpeciesId.DesertBaobab:
                        {
                            float sc = 0.80f + (float)rng.NextDouble() * 0.65f;
                            desertTrees.Add(new FloraInstanceData(MakeTreeTransform(wx, h - 0.20f, wz, yaw, sc, tiltX, tiltZ, normal, 0.08f),
                                new Color(0.92f + (float)rng.NextDouble() * 0.16f, 0.88f, 0.74f)));
                            AddShade(wx, wz, 10.0f, 0.45f);
                            break;
                        }
                        case FloraSpeciesId.OasisPalm:
                        {
                            float sc = 0.82f + (float)rng.NextDouble() * 0.55f;
                            palms.Add(new FloraInstanceData(MakeTreeTransform(wx, h - 0.15f, wz, yaw, sc, tiltX, tiltZ, normal, 0.14f), VaryGreenTint(rng, 0.88f, 1.12f)));
                            AddShade(wx, wz, 9.0f, 0.48f);
                            break;
                        }
                    }
                }
            }

            // ==================================================================
            // PHASE 2: Understory, Ecotone Shrubs, Balanced Grass (12k) & Litter
            // ==================================================================
            const float groundStep = 6.0f;
            for (float z = 56.0f; z < WorldGenerator.RegionDepthMeters - 56.0f; z += groundStep)
            {
                for (float x = 56.0f; x < WorldGenerator.RegionWidthMeters - 56.0f; x += groundStep)
                {
                    float wx = x + (float)(rng.NextDouble() - 0.5) * groundStep * 0.90f;
                    float wz = z + (float)(rng.NextDouble() - 0.5) * groundStep * 0.90f;

                    float h = terrain.SampleHeight(wx, wz);
                    float riverMask = terrain.SampleRiverMask(wx, wz);
                    Vector3 normal = terrain.SampleNormal(wx, wz);
                    float slope = 1.0f - Math.Clamp(normal.Y, 0.0f, 1.0f);
                    ClimateSample cs = climate.SampleClimate(wx, wz);
                    SoilSample ss = soil.SampleSoil(wx, wz);

                    // Boulders where soil is thin / rocky slopes / riverbanks
                    if ((riverMask > 0.16f && riverMask < 0.68f && rng.NextDouble() < 0.10)
                        || (ss.SoilDepth < 0.32f && slope > 0.07f && h > 1.0f && rng.NextDouble() < 0.07)
                        || (ss.CoastalSalinity > 0.45f && h > -0.2f && rng.NextDouble() < 0.06))
                    {
                        float bSc = 0.75f + (float)rng.NextDouble() * 1.50f;
                        Color bTint = ss.WAridRed > 0.45f
                            ? new Color(1.20f, 0.80f, 0.60f)
                            : new Color(0.88f + (float)rng.NextDouble() * 0.22f, 0.90f, 0.92f);
                        boulders.Add(new FloraInstanceData(MakeTreeTransform(wx, h - 0.18f, wz, (float)rng.NextDouble() * MathF.Tau, bSc, 0, 0, normal, 0.35f), bTint));
                    }

                    if (h < 1.0f || cs.TemperatureC < -1.0f || slope > 0.14f || riverMask > 0.56f)
                        continue;

                    int sx = Math.Clamp((int)(wx / shadeCell), 0, shadeW - 1);
                    int sz = Math.Clamp((int)(wz / shadeCell), 0, shadeD - 1);
                    float shade = canopyShade[sz * shadeW + sx];
                    float yaw = (float)rng.NextDouble() * MathF.Tau;

                    // Shaded moist core or riparian: Tree Ferns & Fallen Logs
                    if ((shade > 0.42f || riverMask > 0.14f) && cs.TemperatureC > 7.0f && cs.Moisture > 0.40f)
                    {
                        if (rng.NextDouble() < 0.26)
                        {
                            ferns.Add(new FloraInstanceData(MakeTreeTransform(wx, h - 0.05f, wz, yaw, 0.80f + (float)rng.NextDouble() * 0.70f, 0, 0, normal, 0.22f), VaryGreenTint(rng, 0.78f, 1.15f)));
                            continue;
                        }
                        if (shade > 0.58f && rng.NextDouble() < 0.07 && fallenLogs.Count < 1550)
                        {
                            fallenLogs.Add(new FloraInstanceData(MakeTreeTransform(wx, h - 0.04f, wz, yaw, 0.85f + (float)rng.NextDouble() * 0.65f, 0, 0, normal, 0.45f), new Color(0.95f, 0.92f, 0.85f)));
                            continue;
                        }
                    }

                    // Ecotone Skirt Shrubs (0.10 < shade <= 0.46)
                    if (shade > 0.10f && shade <= 0.46f && ss.SoilDepth > 0.18f && rng.NextDouble() < 0.28)
                    {
                        Color shTint = ss.WSteppeLoess > 0.40f
                            ? new Color(1.15f, 0.76f, 0.34f)
                            : (ss.WAridRed > 0.40f ? new Color(0.86f, 0.82f, 0.58f) : VaryGreenTint(rng, 0.80f, 1.15f));
                        shrubs.Add(new FloraInstanceData(MakeTreeTransform(wx, h - 0.08f, wz, yaw, 0.75f + (float)rng.NextDouble() * 0.65f, 0, 0, normal, 0.20f), shTint));
                        continue;
                    }

                    // Balanced Grass & Reeds (capped at 12,500 so budget goes to L1+L2 Trees!)
                    if (grasses.Count < 12500 && cs.Moisture > 0.24f && ss.SoilDepth > 0.20f && rng.NextDouble() < 0.22)
                    {
                        Color gTint = ss.WSteppeLoess > 0.40f
                            ? new Color(1.18f, 0.82f, 0.34f)
                            : (ss.WAridRed > 0.40f ? new Color(0.98f, 0.85f, 0.52f) : VaryGreenTint(rng, 0.82f, 1.16f));
                        grasses.Add(new FloraInstanceData(MakeTreeTransform(wx, h - 0.05f, wz, yaw, 0.85f + (float)rng.NextDouble() * 0.75f, 0, 0, normal, 0.30f), gTint));
                    }
                }
            }

            // Build MultiMesh Layers (Shadows on L1 + L2 within DirectionalShadowMaxDistance)
            CreateMultiMeshLayer("L1_Emergent_Sequoias", _sequoiaMesh!, _foliageMat!, sequoias, true, 0.0f);
            CreateMultiMeshLayer("L2_Canopy_Broadleaf", _broadleafMesh!, _foliageMat!, broadleafs, true, 2200.0f);
            CreateMultiMeshLayer("L2_Canopy_Ginkgo", _autumnMesh!, _foliageMat!, ginkgos, true, 2200.0f);
            CreateMultiMeshLayer("L2_Canopy_Maple", _autumnMesh!, _foliageMat!, maples, true, 2200.0f);
            CreateMultiMeshLayer("L2_Canopy_Conifer", _coniferMesh!, _foliageMat!, conifers, true, 2200.0f);
            CreateMultiMeshLayer("L2_Canopy_Baobab", _desertTreeMesh!, _foliageMat!, desertTrees, true, 2000.0f);
            CreateMultiMeshLayer("L2_Canopy_Palm", _palmMesh!, _foliageMat!, palms, true, 1600.0f);

            CreateMultiMeshLayer("L3_Understory_Krummholz", _krummholzMesh!, _foliageMat!, krummholz, false, 500.0f);
            CreateMultiMeshLayer("L3_Understory_TreeFerns", _fernMesh!, _foliageMat!, ferns, false, 380.0f);
            CreateMultiMeshLayer("L4_Shrub_Ecotone", _shrubMesh!, _foliageMat!, shrubs, false, 320.0f);
            CreateMultiMeshLayer("L5_Herb_GrassReeds", _grassMesh!, _grassMat!, grasses, false, 210.0f);
            CreateMultiMeshLayer("L6_Litter_FallenLogs", _fallenLogMesh!, _boulderMat!, fallenLogs, false, 220.0f);
            CreateMultiMeshLayer("L6_Litter_Boulders", _boulderMesh!, _boulderMat!, boulders, false, 600.0f);

            int totalTrees = sequoias.Count + broadleafs.Count + ginkgos.Count + maples.Count + conifers.Count + desertTrees.Count + palms.Count;
            GD.Print($"[PrimevalNiche] Total={TotalInstanceCount:N0} | Trees(L1+L2)={totalTrees:N0} " +
                     $"(Sequoia={sequoias.Count}, Broadleaf={broadleafs.Count}, Ginkgo={ginkgos.Count}, Maple={maples.Count}, " +
                     $"Conifer={conifers.Count}, Baobab={desertTrees.Count}, Palm={palms.Count}) | " +
                     $"L3_Understory={krummholz.Count + ferns.Count} | L4_Shrub={shrubs.Count} | L5_Herb={grasses.Count} | L6_Litter={fallenLogs.Count + boulders.Count}");

            // Bake CanopyCoverageMap for terrain_triplanar.gdshader
            byte[] covData = new byte[shadeW * shadeD];
            for (int i = 0; i < shadeW * shadeD; i++)
                covData[i] = (byte)(Math.Clamp(canopyShade[i], 0.0f, 1.0f) * 255.0f);

            Image covImg = Image.CreateFromData(shadeW, shadeD, false, Image.Format.L8, covData);
            return ImageTexture.CreateFromImage(covImg);
        }

        private void EnsureAssets(ClimateSimulator climate)
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
                _grassMat.SetShaderParameter("fade_start", 140.0f);
                _grassMat.SetShaderParameter("fade_end", 205.0f);

                _boulderMat = new StandardMaterial3D
                {
                    VertexColorUseAsAlbedo = true,
                    Roughness = 0.85f,
                };
            }

            _foliageMat.SetShaderParameter("wind_dir", climate.GlobalPrevailingWind);
            _grassMat!.SetShaderParameter("wind_dir", climate.GlobalPrevailingWind);

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
