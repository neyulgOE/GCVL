using System;
using System.Collections.Generic;
using Godot;
using PrimevalWorld.Core;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Flora
{
    /// <summary>
    /// Stage 3 Spatial Streaming Flora Manager:
    /// - L1 & L2 (Emergent + Canopy): 16x9 Macro Cells (600m x 600m) for hardware Frustum Culling + VisibilityRangeEnd fade.
    /// - L3..L6 (Understory, Shrub, Herb, Litter): 64x36 Micro Cells (150m x 150m) dynamically streamed within ~540m of camera.
    /// - Wind Shader driven directly by Stage 2 WindDirMap & WindSpeedMap GPU texture.
    /// </summary>
    public partial class FloraManager : Node3D
    {
        private readonly EcosystemSpawner _spawner = new();
        private readonly FloraMeshLibrary _meshLib = new();

        private ShaderMaterial? _canopyMat;
        private ShaderMaterial? _detailMat;
        private ImageTexture? _windDataTex;

        public ImageTexture? WindDataTex => _windDataTex;

        private readonly List<MultiMeshInstance3D>[,] _macroNodes = new List<MultiMeshInstance3D>[EcosystemSpawner.MacroCols, EcosystemSpawner.MacroRows];
        private readonly List<MultiMeshInstance3D>[,] _microNodes = new List<MultiMeshInstance3D>[EcosystemSpawner.MicroCols, EcosystemSpawner.MicroRows];
        private readonly int[,] _macroCounts = new int[EcosystemSpawner.MacroCols, EcosystemSpawner.MacroRows];
        private readonly int[,] _microCounts = new int[EcosystemSpawner.MicroCols, EcosystemSpawner.MicroRows];

        private int _lastCamMicroX = -999;
        private int _lastCamMicroZ = -999;

        public EcosystemSpawner Spawner => _spawner;
        public int TotalInstanceCount => _spawner.TotalInstances;
        public int VisibleInstanceCount { get; private set; }

        public ImageTexture BuildFlora(
            ErosionPhysics erosion,
            HydrologySolver hydrology,
            AtmosphereClimate climate,
            SoilPedology soil,
            int seed)
        {
            ClearFlora();
            EnsureMaterials(climate);

            _spawner.Generate(erosion, hydrology, climate, soil, seed);

            // Build L1 & L2 Macro MultiMesh cells (16x9)
            for (int mz = 0; mz < EcosystemSpawner.MacroRows; mz++)
            {
                for (int mx = 0; mx < EcosystemSpawner.MacroCols; mx++)
                {
                    var list = _spawner.MacroCanopyCells[mx, mz];
                    _macroCounts[mx, mz] = list.Count;
                    var nodeList = BuildCellMultiMeshes(list, _canopyMat!, isMacroCanopy: true, mx, mz);
                    _macroNodes[mx, mz] = nodeList;
                }
            }

            // Build L3..L6 Micro MultiMesh cells (64x36, initially hidden until streamed near camera)
            for (int mz = 0; mz < EcosystemSpawner.MicroRows; mz++)
            {
                for (int mx = 0; mx < EcosystemSpawner.MicroCols; mx++)
                {
                    var list = _spawner.MicroDetailCells[mx, mz];
                    _microCounts[mx, mz] = list.Count;
                    var nodeList = BuildCellMultiMeshes(list, _detailMat!, isMacroCanopy: false, mx, mz);
                    _microNodes[mx, mz] = nodeList;
                }
            }

            _lastCamMicroX = -999;
            _lastCamMicroZ = -999;
            return _spawner.BuildCanopyCoverageTexture();
        }

        public void UpdateStreaming(Vector3 cameraPos)
        {
            int camMx = Math.Clamp((int)(cameraPos.X / EcosystemSpawner.MicroCellSize), 0, EcosystemSpawner.MicroCols - 1);
            int camMz = Math.Clamp((int)(cameraPos.Z / EcosystemSpawner.MicroCellSize), 0, EcosystemSpawner.MicroRows - 1);
            if (camMx == _lastCamMicroX && camMz == _lastCamMicroZ) return;

            _lastCamMicroX = camMx;
            _lastCamMicroZ = camMz;

            const int streamRadiusCells = 4; // 4 * 150m = 600m radius
            int visCount = 0;

            // Count macro canopy instances within visibility range (~2900m)
            for (int z = 0; z < EcosystemSpawner.MacroRows; z++)
            {
                float cz = (z + 0.5f) * EcosystemSpawner.MacroCellSize;
                for (int x = 0; x < EcosystemSpawner.MacroCols; x++)
                {
                    float cx = (x + 0.5f) * EcosystemSpawner.MacroCellSize;
                    float dx = cx - cameraPos.X;
                    float dz = cz - cameraPos.Z;
                    bool inRange = dx * dx + dz * dz < 3100.0f * 3100.0f;
                    if (inRange) visCount += _macroCounts[x, z];

                    // Enable shadows only on very close macro cells (< 260m) to keep >= 85 FPS on RTX 4060
                    bool nearShadow = dx * dx + dz * dz < 260.0f * 260.0f;
                    var nodes = _macroNodes[x, z];
                    if (nodes == null) continue;
                    for (int i = 0; i < nodes.Count; i++)
                        nodes[i].CastShadow = nearShadow ? GeometryInstance3D.ShadowCastingSetting.On : GeometryInstance3D.ShadowCastingSetting.Off;
                }
            }

            // Toggle L3..L6 micro cells within 4-cell (~600m) radius (zero GC allocations per frame!)
            for (int z = 0; z < EcosystemSpawner.MicroRows; z++)
            {
                for (int x = 0; x < EcosystemSpawner.MicroCols; x++)
                {
                    var nodes = _microNodes[x, z];
                    if (nodes == null || nodes.Count == 0) continue;

                    int dx = x - camMx;
                    int dz = z - camMz;
                    bool active = dx * dx + dz * dz <= streamRadiusCells * streamRadiusCells;
                    if (active) visCount += _microCounts[x, z];

                    if (nodes[0].Visible != active)
                    {
                        for (int i = 0; i < nodes.Count; i++)
                            nodes[i].Visible = active;
                    }
                }
            }

            VisibleInstanceCount = visCount;
        }

        public void UpdateWeatherAndSeason(ImageTexture weatherTex, float seasonPhase, float globalWindGust)
        {
            if (_canopyMat != null)
            {
                _canopyMat.SetShaderParameter("weather_dynamic_tex", weatherTex);
                _canopyMat.SetShaderParameter("season_phase", seasonPhase);
                _canopyMat.SetShaderParameter("global_wind_gust", globalWindGust);
            }
            if (_detailMat != null)
            {
                _detailMat.SetShaderParameter("weather_dynamic_tex", weatherTex);
                _detailMat.SetShaderParameter("season_phase", seasonPhase);
                _detailMat.SetShaderParameter("global_wind_gust", globalWindGust);
            }
        }

        public string GetDominantSpeciesNameAt(float worldX, float worldZ) => _spawner.GetDominantSpeciesNameAt(worldX, worldZ);

        public ImageTexture BuildEmptyCoverageTexture() => _spawner.BuildEmptyCoverageTexture();

        public void ClearFlora()
        {
            foreach (Node child in GetChildren())
                child.QueueFree();
            Array.Clear(_macroNodes, 0, _macroNodes.Length);
            Array.Clear(_microNodes, 0, _microNodes.Length);
            Array.Clear(_macroCounts, 0, _macroCounts.Length);
            Array.Clear(_microCounts, 0, _microCounts.Length);
            VisibleInstanceCount = 0;
        }

        private List<MultiMeshInstance3D> BuildCellMultiMeshes(
            List<FloraInstance> instances,
            ShaderMaterial mat,
            bool isMacroCanopy,
            int cellX,
            int cellZ)
        {
            var created = new List<MultiMeshInstance3D>();
            if (instances.Count == 0) return created;

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
                var mm = new MultiMesh
                {
                    TransformFormat = MultiMesh.TransformFormatEnum.Transform3D,
                    UseColors = true,
                    Mesh = _meshLib.GetMesh(prof),
                    InstanceCount = kv.Value.Count,
                };
                for (int i = 0; i < kv.Value.Count; i++)
                {
                    mm.SetInstanceTransform(i, kv.Value[i].Transform);
                    mm.SetInstanceColor(i, kv.Value[i].Tint);
                }

                var mmi = new MultiMeshInstance3D
                {
                    Name = $"{(isMacroCanopy ? "Macro" : "Micro")}_{cellX}_{cellZ}_{prof.SpeciesKey}",
                    Multimesh = mm,
                    MaterialOverride = mat,
                    Visible = isMacroCanopy,
                    CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
                    VisibilityRangeEnd = isMacroCanopy ? 2950.0f : 620.0f,
                    VisibilityRangeEndMargin = isMacroCanopy ? 350.0f : 80.0f,
                };
                AddChild(mmi);
                created.Add(mmi);
            }

            return created;
        }

        private void EnsureMaterials(AtmosphereClimate climate)
        {
            var shader = GD.Load<Shader>("res://shaders/foliage_wind.gdshader");
            _windDataTex = BuildWindDataTexture(climate);
            var bot = BotanicalTextureGenerator.EnsureAndLoadAll();

            _canopyMat ??= new ShaderMaterial { Shader = shader };
            _canopyMat.SetShaderParameter("wind_dir_speed_tex", _windDataTex);
            _canopyMat.SetShaderParameter("leaf_broadleaf_tex", bot.BroadleafTex);
            _canopyMat.SetShaderParameter("leaf_conifer_tex", bot.ConiferTex);
            _canopyMat.SetShaderParameter("leaf_acacia_tex", bot.AcaciaTex);
            _canopyMat.SetShaderParameter("leaf_palm_tex", bot.PalmFernTex);
            _canopyMat.SetShaderParameter("bark_tex", bot.BarkRoughTex);
            _canopyMat.SetShaderParameter("enable_distance_fade", true);
            _canopyMat.SetShaderParameter("fade_start", 2450.0f);
            _canopyMat.SetShaderParameter("fade_end", 2950.0f);

            _detailMat ??= new ShaderMaterial { Shader = shader };
            _detailMat.SetShaderParameter("wind_dir_speed_tex", _windDataTex);
            _detailMat.SetShaderParameter("leaf_broadleaf_tex", bot.BroadleafTex);
            _detailMat.SetShaderParameter("leaf_conifer_tex", bot.ConiferTex);
            _detailMat.SetShaderParameter("leaf_acacia_tex", bot.AcaciaTex);
            _detailMat.SetShaderParameter("leaf_palm_tex", bot.PalmFernTex);
            _detailMat.SetShaderParameter("bark_tex", bot.BarkRoughTex);
            _detailMat.SetShaderParameter("enable_distance_fade", true);
            _detailMat.SetShaderParameter("fade_start", 460.0f);
            _detailMat.SetShaderParameter("fade_end", 610.0f);
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
