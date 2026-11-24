using System;
using System.Collections.Generic;
using Godot;
using PrimevalWorld.Core;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Flora
{
    /// <summary>
    /// Batch A Overhaul — Hierarchical Sparse Cell Flora Manager:
    /// - Near Canopy Buckets (LOD0 0..150m, LOD1 150..450m): 64 x 36 sparse cells (150m x 150m)
    /// - Far Canopy Bucket (LOD2 450..1350m): 32 x 18 sparse cells (300m x 300m)
    /// - Understory/Detail Buckets (L3..L6): 64 x 36 sparse cells (150m x 150m) streamed near camera
    /// - Strict sparse allocation: ONLY creates MultiMeshInstance3D when count > 0
    /// - Shadow discipline: CastShadow = On ONLY on active LOD0 (150m) cells; Off on all LOD1, LOD2, L3..L6
    /// - Real 4 Hz frustum-checked bucket telemetry (zero fake 0.52 multipliers, zero per-frame GC allocation).
    /// </summary>
    public partial class FloraManager : Node3D
    {
        private struct NearCanopyCell
        {
            public Vector3 Center;
            public float Radius3D;
            public int TreeCount;
            public float Lod0VisEnd;
            public float Lod1VisEnd;
            public bool ShadowEnabled;
            public MultiMeshInstance3D[] Lod0Nodes;
            public MultiMeshInstance3D[] Lod1Nodes;
        }

        private struct FarCanopyCell
        {
            public Vector3 Center;
            public float Radius3D;
            public int TreeCount;
            public float Lod2VisBegin;
            public float Lod2VisEnd;
            public MultiMeshInstance3D[] Lod2Nodes;
        }

        private struct MicroDetailCell
        {
            public Vector3 Center;
            public float Radius3D;
            public int InstanceCount;
            public bool Visible;
            public MultiMeshInstance3D[] Nodes;
        }

        private readonly EcosystemSpawner _spawner = new();
        private readonly FloraMeshLibrary _meshLib = new();

        private ShaderMaterial? _canopyLod0Mat;
        private ShaderMaterial? _canopyLod1Mat;
        private ShaderMaterial? _canopyLod2Mat;
        private ShaderMaterial? _detailMat;
        private ImageTexture? _windDataTex;

        private readonly NearCanopyCell[] _nearCells = new NearCanopyCell[FloraLodConfig.NearCols * FloraLodConfig.NearRows];
        private int _activeNearCellCount;

        private readonly FarCanopyCell[] _farCells = new FarCanopyCell[FloraLodConfig.FarCols * FloraLodConfig.FarRows];
        private int _activeFarCellCount;

        private readonly MicroDetailCell[,] _microCells = new MicroDetailCell[FloraLodConfig.NearCols, FloraLodConfig.NearRows];

        private int _lastCamMicroX = -999;
        private int _lastCamMicroZ = -999;
        private float _telemetryAccum = 999.0f;

        public EcosystemSpawner Spawner => _spawner;
        public ImageTexture? WindDataTex => _windDataTex;
        public bool LodDebugEnabled { get; private set; }

        // Exact Sparse Node Allocation Counts
        public int Lod0NodeCount { get; private set; }
        public int Lod1NodeCount { get; private set; }
        public int Lod2NodeCount { get; private set; }
        public int DetailNodeCount { get; private set; }
        public int TotalSparseNodes => Lod0NodeCount + Lod1NodeCount + Lod2NodeCount + DetailNodeCount;
        public int TotalInstanceCount => _spawner.TotalInstances;

        // Real Measured HUD Telemetry (Updated at 4 Hz with Zero GC)
        public int BucketActiveLod0Trees { get; private set; }
        public int BucketActiveLod1Trees { get; private set; }
        public int BucketActiveLod2Trees { get; private set; }
        public int ActiveTreeCount => BucketActiveLod0Trees + BucketActiveLod1Trees + BucketActiveLod2Trees;
        public int ShadowTrees { get; private set; }
        public int VisibleMultiMeshNodes { get; private set; }
        public int ActiveDetailInstances { get; private set; }
        public int VisibleInstanceCount => ActiveTreeCount + ActiveDetailInstances;

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

            // 1. Partition woody trees into 64x36 (150m x 150m) Near Lists for LOD0 & LOD1
            var nearBuckets = new List<FloraInstance>?[FloraLodConfig.NearCols, FloraLodConfig.NearRows];
            for (int fz = 0; fz < FloraLodConfig.FarRows; fz++)
            {
                for (int fx = 0; fx < FloraLodConfig.FarCols; fx++)
                {
                    var macroList = _spawner.MacroCanopyCells[fx, fz];
                    for (int i = 0; i < macroList.Count; i++)
                    {
                        FloraInstance inst = macroList[i];
                        int nx = Math.Clamp((int)(inst.Transform.Origin.X / FloraLodConfig.NearCellSize), 0, FloraLodConfig.NearCols - 1);
                        int nz = Math.Clamp((int)(inst.Transform.Origin.Z / FloraLodConfig.NearCellSize), 0, FloraLodConfig.NearRows - 1);
                        var cellList = nearBuckets[nx, nz];
                        if (cellList == null)
                        {
                            cellList = new List<FloraInstance>(32);
                            nearBuckets[nx, nz] = cellList;
                        }
                        cellList.Add(inst);
                    }
                }
            }

            // 2. Build Sparse 150m x 150m Near Canopy Cells (LOD0 + LOD1)
            _activeNearCellCount = 0;
            for (int nz = 0; nz < FloraLodConfig.NearRows; nz++)
            {
                for (int nx = 0; nx < FloraLodConfig.NearCols; nx++)
                {
                    var list = nearBuckets[nx, nz];
                    if (list == null || list.Count == 0) continue; // Strict sparse allocation!

                    _nearCells[_activeNearCellCount++] = BuildNearCanopyCell(list, nx, nz);
                }
            }

            // 3. Build Sparse 300m x 300m Far Canopy Cells (LOD2 only)
            _activeFarCellCount = 0;
            for (int fz = 0; fz < FloraLodConfig.FarRows; fz++)
            {
                for (int fx = 0; fx < FloraLodConfig.FarCols; fx++)
                {
                    var list = _spawner.MacroCanopyCells[fx, fz];
                    if (list.Count == 0) continue; // Strict sparse allocation!

                    _farCells[_activeFarCellCount++] = BuildFarCanopyCellLod2(list, fx, fz);
                }
            }

            // 4. Build Sparse 150m x 150m Micro Detail Cells (L3..L6)
            for (int mz = 0; mz < FloraLodConfig.NearRows; mz++)
            {
                for (int mx = 0; mx < FloraLodConfig.NearCols; mx++)
                {
                    var list = _spawner.MicroDetailCells[mx, mz];
                    if (list.Count == 0) continue;

                    _microCells[mx, mz] = BuildMicroDetailCell(list, mx, mz);
                }
            }

            _lastCamMicroX = -999;
            _lastCamMicroZ = -999;
            _telemetryAccum = 999.0f;

            return _spawner.BuildCanopyCoverageTexture(hydrology);
        }

        public void ToggleLodDebugMode()
        {
            SetLodDebugMode(!LodDebugEnabled);
        }

        public void SetLodDebugMode(bool enabled)
        {
            LodDebugEnabled = enabled;
            int val = enabled ? 1 : 0;
            _canopyLod0Mat?.SetShaderParameter("lod_debug_mode", val);
            _canopyLod1Mat?.SetShaderParameter("lod_debug_mode", val);
            _canopyLod2Mat?.SetShaderParameter("lod_debug_mode", val);
            _detailMat?.SetShaderParameter("lod_debug_mode", val);
        }

        public void UpdateStreaming(Camera3D camera, float dt)
        {
            Vector3 camPos = camera.GlobalPosition;
            int camMx = Math.Clamp((int)(camPos.X / FloraLodConfig.NearCellSize), 0, FloraLodConfig.NearCols - 1);
            int camMz = Math.Clamp((int)(camPos.Z / FloraLodConfig.NearCellSize), 0, FloraLodConfig.NearRows - 1);

            bool cellMoved = camMx != _lastCamMicroX || camMz != _lastCamMicroZ;
            if (cellMoved)
            {
                _lastCamMicroX = camMx;
                _lastCamMicroZ = camMz;
                UpdateMicroCellStreaming(camMx, camMz);
                UpdateLod0Shadows(camPos);
            }

            _telemetryAccum += dt;
            if (cellMoved || _telemetryAccum >= 0.25f)
            {
                _telemetryAccum = 0.0f;
                if (!cellMoved)
                    UpdateLod0Shadows(camPos);
                MeasureRealFrustumTelemetry(camera);
            }
        }

        private void UpdateMicroCellStreaming(int camMx, int camMz)
        {
            int r = FloraLodConfig.DetailStreamRadiusCells;
            int maxDistSq = r * r + 1;

            for (int z = 0; z < FloraLodConfig.NearRows; z++)
            {
                int dz = z - camMz;
                for (int x = 0; x < FloraLodConfig.NearCols; x++)
                {
                    ref MicroDetailCell cell = ref _microCells[x, z];
                    if (cell.InstanceCount == 0 || cell.Nodes == null) continue;

                    int dx = x - camMx;
                    bool shouldShow = dx * dx + dz * dz <= maxDistSq;
                    if (cell.Visible != shouldShow)
                    {
                        cell.Visible = shouldShow;
                        for (int i = 0; i < cell.Nodes.Length; i++)
                            cell.Nodes[i].Visible = shouldShow;
                    }
                }
            }
        }

        private void UpdateLod0Shadows(Vector3 camPos)
        {
            for (int i = 0; i < _activeNearCellCount; i++)
            {
                ref NearCanopyCell cell = ref _nearCells[i];
                // Enable CastShadow ONLY on LOD0 (150m) cells that can contain visible LOD0 trees (<= 165m + cellRadius)
                float shadowDist = FloraLodConfig.Lod0End + FloraLodConfig.TransitionHalfBand + cell.Radius3D;
                float distSq = camPos.DistanceSquaredTo(cell.Center);
                bool enableShadow = distSq <= shadowDist * shadowDist;
                if (cell.ShadowEnabled != enableShadow)
                {
                    cell.ShadowEnabled = enableShadow;
                    var mode = enableShadow ? GeometryInstance3D.ShadowCastingSetting.On : GeometryInstance3D.ShadowCastingSetting.Off;
                    for (int k = 0; k < cell.Lod0Nodes.Length; k++)
                        cell.Lod0Nodes[k].CastShadow = mode;
                }
            }
        }

        // Zero-GC exact 3D sphere-vs-camera-frustum & LOD bucket measurement
        public void MeasureRealFrustumTelemetry(Camera3D camera)
        {
            Vector3 camPos = camera.GlobalPosition;
            Basis basis = camera.GlobalTransform.Basis;
            Vector3 fwd = -basis.Z;
            Vector3 right = basis.X;
            Vector3 up = basis.Y;

            Viewport? vp = camera.GetViewport();
            Vector2 vpSize = vp != null ? vp.GetVisibleRect().Size : new Vector2(1600f, 900f);
            float aspect = vpSize.Y > 1.0f ? vpSize.X / vpSize.Y : 1.7778f;
            float halfV = MathF.Tan(Mathf.DegToRad(camera.Fov) * 0.5f);
            float halfH = halfV * aspect;

            Vector3 nRight = (fwd * halfH - right).Normalized();
            Vector3 nLeft = (fwd * halfH + right).Normalized();
            Vector3 nTop = (fwd * halfV - up).Normalized();
            Vector3 nBottom = (fwd * halfV + up).Normalized();
            float farClip = camera.Far;

            bool InFrustum(Vector3 center, float radius)
            {
                Vector3 v = center - camPos;
                float z = v.Dot(fwd);
                if (z < -radius || z > farClip + radius) return false;
                if (v.Dot(nRight) < -radius) return false;
                if (v.Dot(nLeft) < -radius) return false;
                if (v.Dot(nTop) < -radius) return false;
                if (v.Dot(nBottom) < -radius) return false;
                return true;
            }

            int lod0Trees = 0;
            int lod1Trees = 0;
            int lod2Trees = 0;
            int shadowTrees = 0;
            int visNodes = 0;
            int detailInstances = 0;

            for (int i = 0; i < _activeNearCellCount; i++)
            {
                ref NearCanopyCell cell = ref _nearCells[i];
                if (cell.ShadowEnabled)
                    shadowTrees += cell.TreeCount;

                float dist = camPos.DistanceTo(cell.Center);
                if (dist > cell.Lod1VisEnd) continue;
                if (!InFrustum(cell.Center, cell.Radius3D)) continue;

                if (dist <= cell.Lod0VisEnd)
                    visNodes += cell.Lod0Nodes.Length;
                if (dist <= cell.Lod1VisEnd)
                    visNodes += cell.Lod1Nodes.Length;

                // Disjoint cell-center bucket counts for clear HUD readability
                if (dist <= FloraLodConfig.Lod0End)
                    lod0Trees += cell.TreeCount;
                else if (dist <= FloraLodConfig.Lod1End)
                    lod1Trees += cell.TreeCount;
            }

            for (int i = 0; i < _activeFarCellCount; i++)
            {
                ref FarCanopyCell cell = ref _farCells[i];
                float dist = camPos.DistanceTo(cell.Center);
                if (dist < cell.Lod2VisBegin || dist > cell.Lod2VisEnd) continue;
                if (!InFrustum(cell.Center, cell.Radius3D)) continue;

                visNodes += cell.Lod2Nodes.Length;
                if (dist > FloraLodConfig.Lod2Start && dist <= FloraLodConfig.Lod2End)
                    lod2Trees += cell.TreeCount;
            }

            for (int z = 0; z < FloraLodConfig.NearRows; z++)
            {
                for (int x = 0; x < FloraLodConfig.NearCols; x++)
                {
                    ref MicroDetailCell cell = ref _microCells[x, z];
                    if (!cell.Visible || cell.Nodes == null) continue;
                    float dist = camPos.DistanceTo(cell.Center);
                    if (dist > FloraLodConfig.DetailFadeEnd + cell.Radius3D) continue;
                    if (!InFrustum(cell.Center, cell.Radius3D)) continue;

                    visNodes += cell.Nodes.Length;
                    detailInstances += cell.InstanceCount;
                }
            }

            BucketActiveLod0Trees = lod0Trees;
            BucketActiveLod1Trees = lod1Trees;
            BucketActiveLod2Trees = lod2Trees;
            ShadowTrees = shadowTrees;
            VisibleMultiMeshNodes = visNodes;
            ActiveDetailInstances = detailInstances;
        }

        public (int Lod0, int Lod1, int Lod2, int Shadow, int VisNodes) SamplePerspectiveTelemetry(
            Vector3 samplePos, Vector3 lookTarget, float fovDeg = 75.0f)
        {
            Vector3 fwd = (lookTarget - samplePos).Normalized();
            Vector3 right = fwd.Cross(Vector3.Up).Normalized();
            Vector3 up = right.Cross(fwd).Normalized();
            float halfV = MathF.Tan(Mathf.DegToRad(fovDeg) * 0.5f);
            float halfH = halfV * (16.0f / 9.0f);

            Vector3 nRight = (fwd * halfH - right).Normalized();
            Vector3 nLeft = (fwd * halfH + right).Normalized();
            Vector3 nTop = (fwd * halfV - up).Normalized();
            Vector3 nBottom = (fwd * halfV + up).Normalized();

            bool InFrustum(Vector3 center, float radius)
            {
                Vector3 v = center - samplePos;
                float z = v.Dot(fwd);
                if (z < -radius || z > WorldPhysicsConfig.CameraFar + radius) return false;
                return v.Dot(nRight) >= -radius && v.Dot(nLeft) >= -radius && v.Dot(nTop) >= -radius && v.Dot(nBottom) >= -radius;
            }

            int l0 = 0, l1 = 0, l2 = 0, sh = 0, vn = 0;
            for (int i = 0; i < _activeNearCellCount; i++)
            {
                ref NearCanopyCell c = ref _nearCells[i];
                float dist = samplePos.DistanceTo(c.Center);
                if (dist <= FloraLodConfig.Lod0End + FloraLodConfig.TransitionHalfBand + c.Radius3D)
                    sh += c.TreeCount;
                if (dist > c.Lod1VisEnd || !InFrustum(c.Center, c.Radius3D)) continue;
                if (dist <= c.Lod0VisEnd) vn += c.Lod0Nodes.Length;
                if (dist <= c.Lod1VisEnd) vn += c.Lod1Nodes.Length;
                if (dist <= FloraLodConfig.Lod0End) l0 += c.TreeCount;
                else if (dist <= FloraLodConfig.Lod1End) l1 += c.TreeCount;
            }
            for (int i = 0; i < _activeFarCellCount; i++)
            {
                ref FarCanopyCell c = ref _farCells[i];
                float dist = samplePos.DistanceTo(c.Center);
                if (dist < c.Lod2VisBegin || dist > c.Lod2VisEnd || !InFrustum(c.Center, c.Radius3D)) continue;
                vn += c.Lod2Nodes.Length;
                if (dist > FloraLodConfig.Lod2Start && dist <= FloraLodConfig.Lod2End) l2 += c.TreeCount;
            }
            return (l0, l1, l2, sh, vn);
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
            Apply(_canopyLod0Mat);
            Apply(_canopyLod1Mat);
            Apply(_canopyLod2Mat);
            Apply(_detailMat);
        }

        public string GetDominantSpeciesNameAt(float worldX, float worldZ) => _spawner.GetDominantSpeciesNameAt(worldX, worldZ);

        public ImageTexture BuildEmptyCoverageTexture(HydrologySolver hydrology) => _spawner.BuildEmptyCoverageTexture(hydrology);

        public void ClearFlora()
        {
            foreach (Node child in GetChildren())
                child.QueueFree();
            Array.Clear(_nearCells, 0, _nearCells.Length);
            Array.Clear(_farCells, 0, _farCells.Length);
            Array.Clear(_microCells, 0, _microCells.Length);
            _activeNearCellCount = 0;
            _activeFarCellCount = 0;
            Lod0NodeCount = 0;
            Lod1NodeCount = 0;
            Lod2NodeCount = 0;
            DetailNodeCount = 0;
            BucketActiveLod0Trees = 0;
            BucketActiveLod1Trees = 0;
            BucketActiveLod2Trees = 0;
            ShadowTrees = 0;
            VisibleMultiMeshNodes = 0;
            ActiveDetailInstances = 0;
        }

        private NearCanopyCell BuildNearCanopyCell(List<FloraInstance> instances, int nx, int nz)
        {
            float sumY = 0.0f;
            for (int i = 0; i < instances.Count; i++)
                sumY += instances[i].Transform.Origin.Y;

            Vector3 cellCenter = new Vector3(
                (nx + 0.5f) * FloraLodConfig.NearCellSize,
                sumY / instances.Count,
                (nz + 0.5f) * FloraLodConfig.NearCellSize
            );

            float maxOffSq = 0.0f;
            var bySpecies = new Dictionary<FloraSpeciesId, List<FloraInstance>>();
            for (int i = 0; i < instances.Count; i++)
            {
                var inst = instances[i];
                float dSq = inst.Transform.Origin.DistanceSquaredTo(cellCenter);
                if (dSq > maxOffSq) maxOffSq = dSq;

                if (!bySpecies.TryGetValue(inst.Species, out var list))
                {
                    list = new List<FloraInstance>(12);
                    bySpecies[inst.Species] = list;
                }
                list.Add(inst);
            }

            // Safety pad >= +110m (or actual 3D half-span + 18m crown allowance on steep cliffs)
            float radius3D = MathF.Sqrt(maxOffSq) + 18.0f;
            float diagPad = MathF.Max(FloraLodConfig.MinNearCellDiagPad, radius3D);
            float margin = FloraLodConfig.CellHysteresisMargin;

            // Guarantee cell stays visible in Godot SceneTree until EVERY tree in the cell finishes shader dither!
            float lod0VisEnd = FloraLodConfig.Lod0End + FloraLodConfig.TransitionHalfBand + diagPad + margin;
            float lod1VisEnd = FloraLodConfig.Lod1End + FloraLodConfig.TransitionHalfBand + diagPad + margin;

            var lod0Nodes = new List<MultiMeshInstance3D>(bySpecies.Count);
            var lod1Nodes = new List<MultiMeshInstance3D>(bySpecies.Count);

            foreach (var kv in bySpecies)
            {
                FloraNicheProfile prof = FloraNicheDatabase.AllSpecies[(int)kv.Key];
                int n = kv.Value.Count;
                if (n == 0) continue;

                for (int lod = 0; lod <= 1; lod++)
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
                        mm.SetInstanceTransform(i, new Transform3D(worldXf.Basis, worldXf.Origin - cellCenter));
                        mm.SetInstanceCustomData(i, kv.Value[i].CustomData);
                    }

                    var mmi = new MultiMeshInstance3D
                    {
                        Name = $"Near_{nx}_{nz}_{prof.SpeciesKey}_L{lod}",
                        Position = cellCenter,
                        Multimesh = mm,
                        MaterialOverride = lod == 0 ? _canopyLod0Mat : _canopyLod1Mat,
                        CastShadow = GeometryInstance3D.ShadowCastingSetting.Off, // Toggled On strictly for near LOD0
                        VisibilityRangeBegin = 0.0f,
                        VisibilityRangeBeginMargin = 0.0f,
                        VisibilityRangeEnd = lod == 0 ? lod0VisEnd : lod1VisEnd,
                        VisibilityRangeEndMargin = margin,
                    };
                    AddChild(mmi);

                    if (lod == 0)
                    {
                        lod0Nodes.Add(mmi);
                        Lod0NodeCount++;
                    }
                    else
                    {
                        lod1Nodes.Add(mmi);
                        Lod1NodeCount++;
                    }
                }
            }

            return new NearCanopyCell
            {
                Center = cellCenter,
                Radius3D = diagPad,
                TreeCount = instances.Count,
                Lod0VisEnd = lod0VisEnd,
                Lod1VisEnd = lod1VisEnd,
                ShadowEnabled = false,
                Lod0Nodes = lod0Nodes.ToArray(),
                Lod1Nodes = lod1Nodes.ToArray(),
            };
        }

        private FarCanopyCell BuildFarCanopyCellLod2(List<FloraInstance> instances, int fx, int fz)
        {
            float sumY = 0.0f;
            for (int i = 0; i < instances.Count; i++)
                sumY += instances[i].Transform.Origin.Y;

            Vector3 cellCenter = new Vector3(
                (fx + 0.5f) * FloraLodConfig.FarCellSize,
                sumY / instances.Count,
                (fz + 0.5f) * FloraLodConfig.FarCellSize
            );

            float maxOffSq = 0.0f;
            var bySpecies = new Dictionary<FloraSpeciesId, List<FloraInstance>>();
            for (int i = 0; i < instances.Count; i++)
            {
                var inst = instances[i];
                float dSq = inst.Transform.Origin.DistanceSquaredTo(cellCenter);
                if (dSq > maxOffSq) maxOffSq = dSq;

                if (!bySpecies.TryGetValue(inst.Species, out var list))
                {
                    list = new List<FloraInstance>(16);
                    bySpecies[inst.Species] = list;
                }
                list.Add(inst);
            }

            // Safety pad >= +215m (or actual 3D half-span + 18m on steep mountains)
            float radius3D = MathF.Sqrt(maxOffSq) + 18.0f;
            float diagPad = MathF.Max(FloraLodConfig.MinFarCellDiagPad, radius3D);
            float margin = FloraLodConfig.CellHysteresisMargin;

            float rawBegin = (FloraLodConfig.Lod2Start - FloraLodConfig.TransitionHalfBand) - diagPad - margin;
            float lod2VisBegin = MathF.Max(0.0f, rawBegin);
            float lod2VisEnd = FloraLodConfig.FarFadeEnd + diagPad + margin;

            var lod2Nodes = new List<MultiMeshInstance3D>(bySpecies.Count);
            foreach (var kv in bySpecies)
            {
                FloraNicheProfile prof = FloraNicheDatabase.AllSpecies[(int)kv.Key];
                int n = kv.Value.Count;
                if (n == 0) continue;

                var mm = new MultiMesh
                {
                    TransformFormat = MultiMesh.TransformFormatEnum.Transform3D,
                    UseColors = false,
                    UseCustomData = true,
                    Mesh = _meshLib.GetMesh(prof, 2),
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
                    Name = $"Far_{fx}_{fz}_{prof.SpeciesKey}_L2",
                    Position = cellCenter,
                    Multimesh = mm,
                    MaterialOverride = _canopyLod2Mat,
                    CastShadow = GeometryInstance3D.ShadowCastingSetting.Off, // Mandatory Off for LOD2
                    VisibilityRangeBegin = lod2VisBegin,
                    VisibilityRangeBeginMargin = lod2VisBegin > 0.0f ? margin : 0.0f,
                    VisibilityRangeEnd = lod2VisEnd,
                    VisibilityRangeEndMargin = margin,
                };
                AddChild(mmi);
                lod2Nodes.Add(mmi);
                Lod2NodeCount++;
            }

            return new FarCanopyCell
            {
                Center = cellCenter,
                Radius3D = diagPad,
                TreeCount = instances.Count,
                Lod2VisBegin = lod2VisBegin,
                Lod2VisEnd = lod2VisEnd,
                Lod2Nodes = lod2Nodes.ToArray(),
            };
        }

        private MicroDetailCell BuildMicroDetailCell(List<FloraInstance> instances, int mx, int mz)
        {
            float sumY = 0.0f;
            for (int i = 0; i < instances.Count; i++)
                sumY += instances[i].Transform.Origin.Y;

            Vector3 cellCenter = new Vector3(
                (mx + 0.5f) * FloraLodConfig.NearCellSize,
                sumY / instances.Count,
                (mz + 0.5f) * FloraLodConfig.NearCellSize
            );

            float maxOffSq = 0.0f;
            var bySpecies = new Dictionary<FloraSpeciesId, List<FloraInstance>>();
            for (int i = 0; i < instances.Count; i++)
            {
                var inst = instances[i];
                float dSq = inst.Transform.Origin.DistanceSquaredTo(cellCenter);
                if (dSq > maxOffSq) maxOffSq = dSq;

                if (!bySpecies.TryGetValue(inst.Species, out var list))
                {
                    list = new List<FloraInstance>(12);
                    bySpecies[inst.Species] = list;
                }
                list.Add(inst);
            }

            float diagPad = MathF.Max(FloraLodConfig.MinNearCellDiagPad, MathF.Sqrt(maxOffSq) + 8.0f);
            float margin = FloraLodConfig.CellHysteresisMargin;
            float detVisEnd = FloraLodConfig.DetailFadeEnd + diagPad + margin;

            var created = new List<MultiMeshInstance3D>(bySpecies.Count);
            foreach (var kv in bySpecies)
            {
                FloraNicheProfile prof = FloraNicheDatabase.AllSpecies[(int)kv.Key];
                int n = kv.Value.Count;
                if (n == 0) continue;

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
                    Name = $"Micro_{mx}_{mz}_{prof.SpeciesKey}",
                    Position = cellCenter,
                    Multimesh = mm,
                    MaterialOverride = _detailMat,
                    Visible = false,
                    CastShadow = GeometryInstance3D.ShadowCastingSetting.Off, // Mandatory Off for L3..L6
                    VisibilityRangeEnd = detVisEnd,
                    VisibilityRangeEndMargin = margin,
                };
                AddChild(mmi);
                created.Add(mmi);
                DetailNodeCount++;
            }

            return new MicroDetailCell
            {
                Center = cellCenter,
                Radius3D = diagPad,
                InstanceCount = instances.Count,
                Visible = false,
                Nodes = created.ToArray(),
            };
        }

        private void EnsureMaterials(AtmosphereClimate climate)
        {
            var shader = GD.Load<Shader>("res://shaders/flora_wind.gdshader");
            _windDataTex = BuildWindDataTexture(climate);
            var bot = BotanicalTextureGenerator.EnsureAndLoadAll();

            ShaderMaterial BuildOrUpdateMat(ShaderMaterial? existing, int lodLevel)
            {
                var mat = existing ?? new ShaderMaterial { Shader = shader };
                mat.SetShaderParameter("wind_dir_speed_tex", _windDataTex);
                mat.SetShaderParameter("leaf_broadleaf_tex", bot.BroadleafTex);
                mat.SetShaderParameter("leaf_conifer_tex", bot.ConiferTex);
                mat.SetShaderParameter("leaf_acacia_tex", bot.AcaciaTex);
                mat.SetShaderParameter("leaf_palm_tex", bot.PalmFernTex);
                mat.SetShaderParameter("bark_tex", bot.BarkRoughTex);
                mat.SetShaderParameter("bark_pale_tex", bot.BarkPaleTex);
                FloraLodConfig.ApplyToFloraMaterial(mat, lodLevel, LodDebugEnabled);
                return mat;
            }

            _canopyLod0Mat = BuildOrUpdateMat(_canopyLod0Mat, 0);
            _canopyLod1Mat = BuildOrUpdateMat(_canopyLod1Mat, 1);
            _canopyLod2Mat = BuildOrUpdateMat(_canopyLod2Mat, 2);
            _detailMat = BuildOrUpdateMat(_detailMat, -1);
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
