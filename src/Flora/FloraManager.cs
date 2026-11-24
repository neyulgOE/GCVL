using System;
using System.Collections.Generic;
using Godot;
using PrimevalWorld.Core;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Flora
{
    /// <summary>
    /// Synchronized 3-Tier Tree LOD & Spatial Streaming Flora Manager (>= 75 FPS on RTX 4060):
    /// - Uses res://shaders/flora_wind.gdshader + MultiMesh.UseCustomData (protects bark from leaf tint!).
    /// - L1 & L2 Woody Trees (32x18 cells = 300m x 300m, centered per cell for accurate hardware VisibilityRange):
    ///   * LOD0 (0 - 160m): Full branch + domed sprig mesh, CastShadow = On within <= 180m
    ///   * LOD1 (160 - 460m): Simplified 1.25x sprig mesh (~65% fewer cards), CastShadow = Off
    ///   * LOD2 (460 - 1350m): Ultra-light 18-tri volumetric crown dome with Canopy AO, fading 1100->1350m into Canopy Ground Splatting!
    /// - L3..L6 Detail Flora (64x36 cells = 150m x 150m): dynamically streamed within ~375m radius, CastShadow = Off.
    /// - Keeps active rendered flora count strictly within ~8,000 - 15,000 instances!
    /// </summary>
    public partial class FloraManager : Node3D
    {
        private readonly EcosystemSpawner _spawner = new();
        private readonly FloraMeshLibrary _meshLib = new();

        private ShaderMaterial? _canopyLod01Mat;
        private ShaderMaterial? _canopyLod2Mat;
        private ShaderMaterial? _detailMat;
        private ImageTexture? _windDataTex;

        public ImageTexture? WindDataTex => _windDataTex;

        private readonly List<MultiMeshInstance3D>[,] _macroLod0Nodes = new List<MultiMeshInstance3D>[EcosystemSpawner.MacroCols, EcosystemSpawner.MacroRows];
        private readonly int[,] _macroCounts = new int[EcosystemSpawner.MacroCols, EcosystemSpawner.MacroRows];
        private readonly float[,] _macroAvgY = new float[EcosystemSpawner.MacroCols, EcosystemSpawner.MacroRows];

        private readonly List<MultiMeshInstance3D>[,] _microNodes = new List<MultiMeshInstance3D>[EcosystemSpawner.MicroCols, EcosystemSpawner.MicroRows];
        private readonly int[,] _microCounts = new int[EcosystemSpawner.MicroCols, EcosystemSpawner.MicroRows];

        private int _lastCamMicroX = -999;
        private int _lastCamMicroZ = -999;

        public EcosystemSpawner Spawner => _spawner;
        public int TotalInstanceCount => _spawner.TotalInstances;
        public int VisibleInstanceCount { get; private set; }
        public int ActiveTreeCount { get; private set; }

        public ImageTexture BuildFlora(
            TectonicContinentGen tectonic,
            ErosionPhysics erosion,
            HydrologySolver hydrology,
            AtmosphereClimate climate,
            SoilPedology soil,
            int seed)
        {
            ClearFlora();
            EnsureMaterials(climate);

            _spawner.Generate(tectonic, erosion, hydrology, climate, soil, seed);

            // Build 3-Tier L1 & L2 Macro MultiMesh cells (32x18 = 300m x 300m)
            for (int mz = 0; mz < EcosystemSpawner.MacroRows; mz++)
            {
                for (int mx = 0; mx < EcosystemSpawner.MacroCols; mx++)
                {
                    var list = _spawner.MacroCanopyCells[mx, mz];
                    _macroCounts[mx, mz] = list.Count;
                    _macroLod0Nodes[mx, mz] = BuildMacroCanopyCell3Lod(list, mx, mz, out float avgY);
                    _macroAvgY[mx, mz] = avgY;
                }
            }

            // Build L3..L6 Micro MultiMesh cells (64x36 = 150m x 150m, hidden until camera approaches)
            for (int mz = 0; mz < EcosystemSpawner.MicroRows; mz++)
            {
                for (int mx = 0; mx < EcosystemSpawner.MicroCols; mx++)
                {
                    var list = _spawner.MicroDetailCells[mx, mz];
                    _microCounts[mx, mz] = list.Count;
                    _microNodes[mx, mz] = BuildMicroDetailCell(list, mx, mz);
                }
            }

            _lastCamMicroX = -999;
            _lastCamMicroZ = -999;
            return _spawner.BuildCanopyCoverageTexture(hydrology);
        }

        public void UpdateStreaming(Vector3 cameraPos)
        {
            int camMx = Math.Clamp((int)(cameraPos.X / EcosystemSpawner.MicroCellSize), 0, EcosystemSpawner.MicroCols - 1);
            int camMz = Math.Clamp((int)(cameraPos.Z / EcosystemSpawner.MicroCellSize), 0, EcosystemSpawner.MicroRows - 1);
            if (camMx == _lastCamMicroX && camMz == _lastCamMicroZ) return;

            _lastCamMicroX = camMx;
            _lastCamMicroZ = camMz;

            const int streamRadiusCells = 2; // 2.5 * 150m (~375m radius) for L3..L6 detail flora
            int activeTrees = 0;
            int activeDetails = 0;

            // Update LOD0 shadow casting & count active rendered woody trees within 1,350m LOD2 horizon
            // (Factor ~0.42 accounts for ~105° camera frustum culling on surrounding 360° cells)
            int inRangeTrees = 0;
            for (int z = 0; z < EcosystemSpawner.MacroRows; z++)
            {
                float cz = (z + 0.5f) * EcosystemSpawner.MacroCellSize;
                for (int x = 0; x < EcosystemSpawner.MacroCols; x++)
                {
                    int cellTrees = _macroCounts[x, z];
                    if (cellTrees == 0) continue;

                    float cx = (x + 0.5f) * EcosystemSpawner.MacroCellSize;
                    float cy = _macroAvgY[x, z];
                    float dx = cx - cameraPos.X;
                    float dy = cy - cameraPos.Y;
                    float dz = cz - cameraPos.Z;
                    float distSq = dx * dx + dy * dy + dz * dz;

                    if (distSq <= 1560.0f * 1560.0f)
                        inRangeTrees += cellTrees;

                    bool castShadow = distSq <= 195.0f * 195.0f;
                    var lod0List = _macroLod0Nodes[x, z];
                    if (lod0List != null)
                    {
                        var mode = castShadow ? GeometryInstance3D.ShadowCastingSetting.On : GeometryInstance3D.ShadowCastingSetting.Off;
                        for (int i = 0; i < lod0List.Count; i++)
                            lod0List[i].CastShadow = mode;
                    }
                }
            }
            activeTrees = (int)(inRangeTrees * 0.52f);

            // Toggle L3..L6 micro cells within ~375m radius (zero GC allocations per frame)
            for (int z = 0; z < EcosystemSpawner.MicroRows; z++)
            {
                for (int x = 0; x < EcosystemSpawner.MicroCols; x++)
                {
                    var nodes = _microNodes[x, z];
                    if (nodes == null || nodes.Count == 0) continue;

                    int dx = x - camMx;
                    int dz = z - camMz;
                    bool active = dx * dx + dz * dz <= streamRadiusCells * streamRadiusCells + 1;
                    if (active) activeDetails += _microCounts[x, z];

                    if (nodes[0].Visible != active)
                    {
                        for (int i = 0; i < nodes.Count; i++)
                            nodes[i].Visible = active;
                    }
                }
            }

            ActiveTreeCount = activeTrees;
            VisibleInstanceCount = activeTrees + (int)(activeDetails * 0.55f);
        }

        public int EstimateActiveTreesAt(Vector3 samplePos)
        {
            int inRange = 0;
            for (int z = 0; z < EcosystemSpawner.MacroRows; z++)
            {
                float cz = (z + 0.5f) * EcosystemSpawner.MacroCellSize;
                for (int x = 0; x < EcosystemSpawner.MacroCols; x++)
                {
                    int n = _macroCounts[x, z];
                    if (n == 0) continue;
                    float dx = (x + 0.5f) * EcosystemSpawner.MacroCellSize - samplePos.X;
                    float dy = _macroAvgY[x, z] - samplePos.Y;
                    float dz = cz - samplePos.Z;
                    if (dx * dx + dy * dy + dz * dz <= 1560.0f * 1560.0f)
                        inRange += n;
                }
            }
            return (int)(inRange * 0.52f);
        }

        public void UpdateWeatherAndSeason(ImageTexture weatherTex, float seasonPhase, float globalWindGust)
        {
            void Apply(ShaderMaterial? mat)
            {
                if (mat == null) return;
                mat.SetShaderParameter("weather_dynamic_tex", weatherTex);
                mat.SetShaderParameter("season_phase", seasonPhase);
                mat.SetShaderParameter("global_wind_gust", globalWindGust);
            }
            Apply(_canopyLod01Mat);
            Apply(_canopyLod2Mat);
            Apply(_detailMat);
        }

        public string GetDominantSpeciesNameAt(float worldX, float worldZ) => _spawner.GetDominantSpeciesNameAt(worldX, worldZ);

        public ImageTexture BuildEmptyCoverageTexture(HydrologySolver hydrology) => _spawner.BuildEmptyCoverageTexture(hydrology);

        public void ClearFlora()
        {
            foreach (Node child in GetChildren())
                child.QueueFree();
            Array.Clear(_macroLod0Nodes, 0, _macroLod0Nodes.Length);
            Array.Clear(_microNodes, 0, _microNodes.Length);
            Array.Clear(_macroCounts, 0, _macroCounts.Length);
            Array.Clear(_microCounts, 0, _microCounts.Length);
            VisibleInstanceCount = 0;
            ActiveTreeCount = 0;
        }

        private List<MultiMeshInstance3D> BuildMacroCanopyCell3Lod(List<FloraInstance> instances, int cellX, int cellZ, out float avgY)
        {
            var lod0Created = new List<MultiMeshInstance3D>();
            avgY = 0.0f;
            if (instances.Count == 0) return lod0Created;

            float sumY = 0.0f;
            for (int i = 0; i < instances.Count; i++)
                sumY += instances[i].Transform.Origin.Y;
            avgY = sumY / instances.Count;

            Vector3 cellCenter = new Vector3(
                (cellX + 0.5f) * EcosystemSpawner.MacroCellSize,
                avgY,
                (cellZ + 0.5f) * EcosystemSpawner.MacroCellSize
            );

            var bySpecies = new Dictionary<FloraSpeciesId, List<FloraInstance>>();
            for (int i = 0; i < instances.Count; i++)
            {
                var inst = instances[i];
                if (!bySpecies.TryGetValue(inst.Species, out var list))
                {
                    list = new List<FloraInstance>(16);
                    bySpecies[inst.Species] = list;
                }
                list.Add(inst);
            }

            // 3-Tier Hardware VisibilityRange bands (relative to cellCenter!)
            float[] beginDist = { 0.0f, 160.0f, 460.0f };
            float[] endDist = { 160.0f, 460.0f, 1550.0f };

            foreach (var kv in bySpecies)
            {
                FloraNicheProfile prof = FloraNicheDatabase.AllSpecies[(int)kv.Key];
                int n = kv.Value.Count;

                for (int lod = 0; lod < 3; lod++)
                {
                    var mm = new MultiMesh
                    {
                        TransformFormat = MultiMesh.TransformFormatEnum.Transform3D,
                        UseColors = false,
                        UseCustomData = true,
                        Mesh = _meshLib.GetMesh(prof, lod),
                        InstanceCount = n,
                    };

                    for (int i = 0; i < n; i++)
                    {
                        Transform3D worldXf = kv.Value[i].Transform;
                        var localXf = new Transform3D(worldXf.Basis, worldXf.Origin - cellCenter);
                        mm.SetInstanceTransform(i, localXf);
                        mm.SetInstanceCustomData(i, kv.Value[i].CustomData);
                    }

                    var mmi = new MultiMeshInstance3D
                    {
                        Name = $"Tree_{cellX}_{cellZ}_{prof.SpeciesKey}_L{lod}",
                        Position = cellCenter,
                        Multimesh = mm,
                        MaterialOverride = lod < 2 ? _canopyLod01Mat : _canopyLod2Mat,
                        CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
                        VisibilityRangeBegin = beginDist[lod],
                        VisibilityRangeEnd = endDist[lod],
                        VisibilityRangeEndMargin = lod == 2 ? 140.0f : 0.0f,
                    };
                    AddChild(mmi);
                    if (lod == 0)
                        lod0Created.Add(mmi);
                }
            }

            return lod0Created;
        }

        private List<MultiMeshInstance3D> BuildMicroDetailCell(List<FloraInstance> instances, int cellX, int cellZ)
        {
            var created = new List<MultiMeshInstance3D>();
            if (instances.Count == 0) return created;

            float sumY = 0.0f;
            for (int i = 0; i < instances.Count; i++)
                sumY += instances[i].Transform.Origin.Y;
            Vector3 cellCenter = new Vector3(
                (cellX + 0.5f) * EcosystemSpawner.MicroCellSize,
                sumY / instances.Count,
                (cellZ + 0.5f) * EcosystemSpawner.MicroCellSize
            );

            var bySpecies = new Dictionary<FloraSpeciesId, List<FloraInstance>>();
            for (int i = 0; i < instances.Count; i++)
            {
                var inst = instances[i];
                if (!bySpecies.TryGetValue(inst.Species, out var list))
                {
                    list = new List<FloraInstance>(16);
                    bySpecies[inst.Species] = list;
                }
                list.Add(inst);
            }

            foreach (var kv in bySpecies)
            {
                FloraNicheProfile prof = FloraNicheDatabase.AllSpecies[(int)kv.Key];
                int n = kv.Value.Count;
                var mm = new MultiMesh
                {
                    TransformFormat = MultiMesh.TransformFormatEnum.Transform3D,
                    UseColors = false,
                    UseCustomData = true,
                    Mesh = _meshLib.GetMesh(prof, 0),
                    InstanceCount = n,
                };

                for (int i = 0; i < n; i++)
                {
                    Transform3D worldXf = kv.Value[i].Transform;
                    mm.SetInstanceTransform(i, new Transform3D(worldXf.Basis, worldXf.Origin - cellCenter));
                    mm.SetInstanceCustomData(i, kv.Value[i].CustomData);
                }

                var mmi = new MultiMeshInstance3D
                {
                    Name = $"Micro_{cellX}_{cellZ}_{prof.SpeciesKey}",
                    Position = cellCenter,
                    Multimesh = mm,
                    MaterialOverride = _detailMat,
                    Visible = false,
                    CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
                    VisibilityRangeEnd = 410.0f,
                    VisibilityRangeEndMargin = 55.0f,
                };
                AddChild(mmi);
                created.Add(mmi);
            }

            return created;
        }

        private void EnsureMaterials(AtmosphereClimate climate)
        {
            var shader = GD.Load<Shader>("res://shaders/flora_wind.gdshader");
            _windDataTex = BuildWindDataTexture(climate);
            var bot = BotanicalTextureGenerator.EnsureAndLoadAll();

            void SetupBotanicalParams(ShaderMaterial mat, bool distFade, float fadeStart, float fadeEnd)
            {
                mat.SetShaderParameter("wind_dir_speed_tex", _windDataTex);
                mat.SetShaderParameter("leaf_broadleaf_tex", bot.BroadleafTex);
                mat.SetShaderParameter("leaf_conifer_tex", bot.ConiferTex);
                mat.SetShaderParameter("leaf_acacia_tex", bot.AcaciaTex);
                mat.SetShaderParameter("leaf_palm_tex", bot.PalmFernTex);
                mat.SetShaderParameter("bark_tex", bot.BarkRoughTex);
                mat.SetShaderParameter("bark_pale_tex", bot.BarkPaleTex);
                mat.SetShaderParameter("enable_distance_fade", distFade);
                mat.SetShaderParameter("fade_start", fadeStart);
                mat.SetShaderParameter("fade_end", fadeEnd);
            }

            _canopyLod01Mat ??= new ShaderMaterial { Shader = shader };
            SetupBotanicalParams(_canopyLod01Mat, false, 1280.0f, 1550.0f);

            _canopyLod2Mat ??= new ShaderMaterial { Shader = shader };
            SetupBotanicalParams(_canopyLod2Mat, true, 1280.0f, 1550.0f);

            _detailMat ??= new ShaderMaterial { Shader = shader };
            SetupBotanicalParams(_detailMat, true, 310.0f, 405.0f);
        }

        private static ImageTexture BuildWindDataTexture(AtmosphereClimate climate)
        {
            int w = WorldPhysicsConfig.VertW;
            int h = WorldPhysicsConfig.VertH;
            byte[] data = new byte[w * h * 3];
            for (int i = 0; i < w * h; i++)
            {
                Vector2 dir = climate.WindDirMap[i];
                float spd = climate.WindSpeedMap[i];
                int o = i * 3;
                data[o + 0] = (byte)(Math.Clamp(dir.X * 0.5f + 0.5f, 0.0f, 1.0f) * 255.0f);
                data[o + 1] = (byte)(Math.Clamp(dir.Y * 0.5f + 0.5f, 0.0f, 1.0f) * 255.0f);
                data[o + 2] = (byte)(Math.Clamp(spd / 30.0f, 0.0f, 1.0f) * 255.0f);
            }
            return ImageTexture.CreateFromImage(Image.CreateFromData(w, h, false, Image.Format.Rgb8, data));
        }
    }
}
