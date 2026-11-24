using System;
using System.Collections.Generic;
using Godot;
using PrimevalWorld.Core;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Flora
{
    /// <summary>
    /// Phase 0 + Phase 1 Dynamic Streaming Pool Flora Manager (< 1,200 SceneTree Nodes, Shadow <= LOD0):
    /// - 2-Surface PBR Bark/Moss (shaders/bark_moss.gdshader) + Botanical Foliage (shaders/flora_wind.gdshader)
    ///   for LOD0, LOD1, Detail & Close Understory (using ArrayMesh.SurfaceSetMaterial + MaterialOverride = null).
    /// - Shared morphological MeshKey batching (4 Broadleaf variants, 3 Conifer variants, 2 Weeping/Desert/Palm variants)
    ///   keeps SceneTree node count strictly < 1,200 even in dense multi-variant rainforests!
    /// - Close Understory (LushSwordFern, GiantElephantEar, LianaMossCurtain, MossyFallenLog, DenseShrub) streams
    ///   strictly within <= 200m (dither fade 75..100m, CastShadow = Off) for lush 0.85m eye-level forest floors!
    /// - Macro 600m x 600m LOD2 (16x9 cells x 4 puffy canopy archetypes = ~312 nodes across whole 52 km2).
    /// </summary>
    public partial class FloraManager : Node3D
    {
        private enum Lod2Archetype : byte
        {
            Broadleaf = 0,
            Conifer = 1,
            Deciduous = 2,
            DesertUmbrella = 3,
        }

        private sealed class VariantBatchData
        {
            public readonly FloraMeshLibrary.MeshKey Key;
            public readonly Transform3D[] LocalTransforms;
            public readonly Color[] CustomDatas;
            public MultiMesh? CachedLod0Mm;
            public MultiMesh? CachedLod1Mm;
            public MultiMesh? CachedDetailMm;

            public VariantBatchData(FloraMeshLibrary.MeshKey key, List<FloraInstance> src, Vector3 cellCenter)
            {
                Key = key;
                int n = src.Count;
                LocalTransforms = new Transform3D[n];
                CustomDatas = new Color[n];
                for (int i = 0; i < n; i++)
                {
                    Transform3D w = src[i].Transform;
                    LocalTransforms[i] = new Transform3D(w.Basis, w.Origin - cellCenter);
                    CustomDatas[i] = src[i].CustomData;
                }
            }

            public MultiMesh GetOrBuildMultiMesh(
                FloraMeshLibrary meshLib,
                int lod,
                bool isDetail,
                Material? barkMat,
                Material? leafMat)
            {
                if (isDetail)
                {
                    if (CachedDetailMm != null) return CachedDetailMm;
                    CachedDetailMm = BuildMultiMesh(meshLib.GetMesh(Key.CanonicalSpecies, Key.Variant, 0, barkMat, leafMat));
                    return CachedDetailMm;
                }
                if (lod == 0)
                {
                    if (CachedLod0Mm != null) return CachedLod0Mm;
                    CachedLod0Mm = BuildMultiMesh(meshLib.GetMesh(Key.CanonicalSpecies, Key.Variant, 0, barkMat, leafMat));
                    return CachedLod0Mm;
                }
                if (CachedLod1Mm != null) return CachedLod1Mm;
                CachedLod1Mm = BuildMultiMesh(meshLib.GetMesh(Key.CanonicalSpecies, Key.Variant, 1, barkMat, leafMat));
                return CachedLod1Mm;
            }

            private MultiMesh BuildMultiMesh(Mesh mesh)
            {
                int n = LocalTransforms.Length;
                var mm = new MultiMesh
                {
                    TransformFormat = MultiMesh.TransformFormatEnum.Transform3D,
                    UseColors = false,
                    UseCustomData = true,
                    Mesh = mesh,
                    InstanceCount = n,
                };
                for (int i = 0; i < n; i++)
                {
                    mm.SetInstanceTransform(i, LocalTransforms[i]);
                    mm.SetInstanceCustomData(i, CustomDatas[i]);
                }
                return mm;
            }
        }

        private sealed class CellFloraData
        {
            public Vector3 Center;
            public float Radius3D;
            public int TreeCount;
            public int DetailCount;
            public int CloseUnderstoryCount;
            public float Lod0VisEnd;
            public float Lod1VisEnd;
            public float DetailVisEnd;
            public float CloseUnderstoryVisEnd;
            public VariantBatchData[] TreeBatches = Array.Empty<VariantBatchData>();
            public VariantBatchData[] DetailBatches = Array.Empty<VariantBatchData>();
            public VariantBatchData[] CloseUnderstoryBatches = Array.Empty<VariantBatchData>();

            public bool Lod0Mounted;
            public bool Lod1Mounted;
            public bool DetailMounted;
            public bool CloseUnderstoryMounted;
            public bool ShadowEnabled;
            public readonly List<MultiMeshInstance3D> MountedLod0Nodes = new(8);
            public readonly List<MultiMeshInstance3D> MountedLod1Nodes = new(8);
            public readonly List<MultiMeshInstance3D> MountedDetailNodes = new(8);
            public readonly List<MultiMeshInstance3D> MountedCloseUnderstoryNodes = new(10);
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

        private readonly EcosystemSpawner _spawner = new();
        private readonly FloraMeshLibrary _meshLib = new();

        private ShaderMaterial? _leafLod0Mat;
        private ShaderMaterial? _leafLod1Mat;
        private ShaderMaterial? _leafLod2Mat;
        private ShaderMaterial? _leafDetailMat;
        private ShaderMaterial? _leafCloseUnderstoryMat;

        private ShaderMaterial? _barkLod0Mat;
        private ShaderMaterial? _barkLod1Mat;
        private ShaderMaterial? _barkDetailMat;
        private ShaderMaterial? _barkCloseUnderstoryMat;

        private ImageTexture? _windDataTex;

        private readonly CellFloraData?[,] _nearGrid = new CellFloraData?[FloraLodConfig.NearCols, FloraLodConfig.NearRows];
        private readonly List<CellFloraData> _mountedNearCells = new(96);
        private readonly Stack<MultiMeshInstance3D> _nodePool = new(512);

        private readonly FarCanopyCell[] _farCells = new FarCanopyCell[FloraLodConfig.FarCols * FloraLodConfig.FarRows];
        private int _activeFarCellCount;

        private int _lastCamCellX = -999;
        private int _lastCamCellZ = -999;
        private float _telemetryAccum = 999.0f;

        public EcosystemSpawner Spawner => _spawner;
        public ImageTexture? WindDataTex => _windDataTex;
        public bool LodDebugEnabled { get; private set; }

        public int MountedLod0NodeCount { get; private set; }
        public int MountedLod1NodeCount { get; private set; }
        public int MountedDetailNodeCount { get; private set; }
        public int MountedCloseUnderstoryNodeCount { get; private set; }
        public int Lod2NodeCount { get; private set; }
        public int TotalSceneTreeNodes => MountedLod0NodeCount + MountedLod1NodeCount + MountedDetailNodeCount + MountedCloseUnderstoryNodeCount + Lod2NodeCount;
        public int TotalSparseNodes => TotalSceneTreeNodes;
        public int TotalInstanceCount => _spawner.TotalInstances;

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
            int seed,
            ImageTexture? climateTex = null)
        {
            ClearFlora();
            EnsureMaterials(climate);

            _spawner.Generate(tectonic, erosion, hydrology, climate, soil, seed);
            ImageTexture canopyTex = _spawner.BuildCanopyCoverageTexture(hydrology);
            BindSiteMossTextures(climateTex, canopyTex);

            // 1. Collect woody trees into pure C# RAM lists per 150m & 600m cell
            var nearTreeLists = new List<FloraInstance>?[FloraLodConfig.NearCols, FloraLodConfig.NearRows];
            var farTreeLists = new List<FloraInstance>?[FloraLodConfig.FarCols, FloraLodConfig.FarRows];

            for (int mz = 0; mz < EcosystemSpawner.MacroRows; mz++)
            {
                for (int mx = 0; mx < EcosystemSpawner.MacroCols; mx++)
                {
                    var macroList = _spawner.MacroCanopyCells[mx, mz];
                    for (int i = 0; i < macroList.Count; i++)
                    {
                        FloraInstance inst = macroList[i];
                        Vector3 o = inst.Transform.Origin;

                        int nx = Math.Clamp((int)(o.X / FloraLodConfig.NearCellSize), 0, FloraLodConfig.NearCols - 1);
                        int nz = Math.Clamp((int)(o.Z / FloraLodConfig.NearCellSize), 0, FloraLodConfig.NearRows - 1);
                        nearTreeLists[nx, nz] ??= new List<FloraInstance>(32);
                        nearTreeLists[nx, nz]!.Add(inst);

                        int fx = Math.Clamp((int)(o.X / FloraLodConfig.FarCellSize), 0, FloraLodConfig.FarCols - 1);
                        int fz = Math.Clamp((int)(o.Z / FloraLodConfig.FarCellSize), 0, FloraLodConfig.FarRows - 1);
                        farTreeLists[fx, fz] ??= new List<FloraInstance>(128);
                        farTreeLists[fx, fz]!.Add(inst);
                    }
                }
            }

            // 2. Pack pure C# CellFloraData for 64x36 (150m) cells (0 SceneTree nodes allocated yet!)
            for (int nz = 0; nz < FloraLodConfig.NearRows; nz++)
            {
                for (int nx = 0; nx < FloraLodConfig.NearCols; nx++)
                {
                    var tList = nearTreeLists[nx, nz];
                    var dList = _spawner.MicroDetailCells[nx, nz];
                    if ((tList == null || tList.Count == 0) && dList.Count == 0) continue;

                    _nearGrid[nx, nz] = BuildPureNearCellData(tList, dList, nx, nz);
                }
            }

            // 3. Build Static Grouped-Archetype Puffy LOD2 for 16x9 (600m x 600m) macro cells
            _activeFarCellCount = 0;
            for (int fz = 0; fz < FloraLodConfig.FarRows; fz++)
            {
                for (int fx = 0; fx < FloraLodConfig.FarCols; fx++)
                {
                    var list = farTreeLists[fx, fz];
                    if (list == null || list.Count == 0) continue;

                    _farCells[_activeFarCellCount++] = BuildGroupedFarCellLod2(list, fx, fz);
                }
            }

            _lastCamCellX = -999;
            _lastCamCellZ = -999;
            _telemetryAccum = 999.0f;

            return canopyTex;
        }

        public void BindSiteMossTextures(ImageTexture? climateTex, ImageTexture? canopyTex)
        {
            void Apply(ShaderMaterial? mat)
            {
                if (mat == null) return;
                if (climateTex != null) mat.SetShaderParameter("climate_tex", climateTex);
                if (canopyTex != null) mat.SetShaderParameter("canopy_coverage_tex", canopyTex);
            }
            Apply(_barkLod0Mat);
            Apply(_barkLod1Mat);
            Apply(_barkDetailMat);
            Apply(_barkCloseUnderstoryMat);
        }

        public void ToggleLodDebugMode() => SetLodDebugMode(!LodDebugEnabled);

        public void SetLodDebugMode(bool enabled)
        {
            LodDebugEnabled = enabled;
            int val = enabled ? 1 : 0;
            _leafLod0Mat?.SetShaderParameter("lod_debug_mode", val);
            _leafLod1Mat?.SetShaderParameter("lod_debug_mode", val);
            _leafLod2Mat?.SetShaderParameter("lod_debug_mode", val);
            _leafDetailMat?.SetShaderParameter("lod_debug_mode", val);
            _leafCloseUnderstoryMat?.SetShaderParameter("lod_debug_mode", val);

            _barkLod0Mat?.SetShaderParameter("lod_debug_mode", val);
            _barkLod1Mat?.SetShaderParameter("lod_debug_mode", val);
            _barkDetailMat?.SetShaderParameter("lod_debug_mode", val);
            _barkCloseUnderstoryMat?.SetShaderParameter("lod_debug_mode", val);
        }

        public void UpdateStreaming(Camera3D camera, float dt)
        {
            Vector3 camPos = camera.GlobalPosition;
            int camCx = Math.Clamp((int)(camPos.X / FloraLodConfig.NearCellSize), 0, FloraLodConfig.NearCols - 1);
            int camCz = Math.Clamp((int)(camPos.Z / FloraLodConfig.NearCellSize), 0, FloraLodConfig.NearRows - 1);

            bool cellMoved = camCx != _lastCamCellX || camCz != _lastCamCellZ;
            if (cellMoved)
            {
                _lastCamCellX = camCx;
                _lastCamCellZ = camCz;
                UpdateDynamicNearCellPool(camPos, camCx, camCz);
            }

            _telemetryAccum += dt;
            if (cellMoved || _telemetryAccum >= 0.25f)
            {
                _telemetryAccum = 0.0f;
                MeasureRealFrustumTelemetryAndShadows(camera);
            }
        }

        private void UpdateDynamicNearCellPool(Vector3 camPos, int camCx, int camCz)
        {
            float lod0MountSq = FloraLodConfig.NearLod0MountRadiusM * FloraLodConfig.NearLod0MountRadiusM;
            float lod0UnmountSq = (FloraLodConfig.NearLod0MountRadiusM + FloraLodConfig.UnmountHysteresisM)
                                * (FloraLodConfig.NearLod0MountRadiusM + FloraLodConfig.UnmountHysteresisM);

            float lod1MountSq = FloraLodConfig.NearLod1MountRadiusM * FloraLodConfig.NearLod1MountRadiusM;
            float lod1UnmountSq = (FloraLodConfig.NearLod1MountRadiusM + FloraLodConfig.UnmountHysteresisM)
                                * (FloraLodConfig.NearLod1MountRadiusM + FloraLodConfig.UnmountHysteresisM);

            float detMountSq = FloraLodConfig.NearDetailMountRadiusM * FloraLodConfig.NearDetailMountRadiusM;
            float detUnmountSq = (FloraLodConfig.NearDetailMountRadiusM + FloraLodConfig.UnmountHysteresisM)
                               * (FloraLodConfig.NearDetailMountRadiusM + FloraLodConfig.UnmountHysteresisM);

            float cuMountSq = FloraLodConfig.NearUnderstoryMountRadiusM * FloraLodConfig.NearUnderstoryMountRadiusM;
            float cuUnmountSq = (FloraLodConfig.NearUnderstoryMountRadiusM + FloraLodConfig.UnmountHysteresisM)
                              * (FloraLodConfig.NearUnderstoryMountRadiusM + FloraLodConfig.UnmountHysteresisM);

            for (int i = _mountedNearCells.Count - 1; i >= 0; i--)
            {
                CellFloraData cell = _mountedNearCells[i];
                float dx = cell.Center.X - camPos.X;
                float dz = cell.Center.Z - camPos.Z;
                float dSqXZ = dx * dx + dz * dz;

                if (cell.Lod0Mounted && dSqXZ > lod0UnmountSq) UnmountLayer(cell, 0);
                if (cell.Lod1Mounted && dSqXZ > lod1UnmountSq) UnmountLayer(cell, 1);
                if (cell.DetailMounted && dSqXZ > detUnmountSq) UnmountLayer(cell, 2);
                if (cell.CloseUnderstoryMounted && dSqXZ > cuUnmountSq) UnmountLayer(cell, 3);

                if (!cell.Lod0Mounted && !cell.Lod1Mounted && !cell.DetailMounted && !cell.CloseUnderstoryMounted)
                {
                    int last = _mountedNearCells.Count - 1;
                    _mountedNearCells[i] = _mountedNearCells[last];
                    _mountedNearCells.RemoveAt(last);
                }
            }

            int radCells = (int)MathF.Ceiling(FloraLodConfig.NearLod1MountRadiusM / FloraLodConfig.NearCellSize) + 1;
            int minX = Math.Max(0, camCx - radCells);
            int maxX = Math.Min(FloraLodConfig.NearCols - 1, camCx + radCells);
            int minZ = Math.Max(0, camCz - radCells);
            int maxZ = Math.Min(FloraLodConfig.NearRows - 1, camCz + radCells);

            for (int z = minZ; z <= maxZ; z++)
            {
                for (int x = minX; x <= maxX; x++)
                {
                    CellFloraData? cell = _nearGrid[x, z];
                    if (cell == null) continue;

                    float dx = cell.Center.X - camPos.X;
                    float dz = cell.Center.Z - camPos.Z;
                    float dSqXZ = dx * dx + dz * dz;
                    if (dSqXZ > lod1MountSq) continue;

                    bool wasMounted = cell.Lod0Mounted || cell.Lod1Mounted || cell.DetailMounted || cell.CloseUnderstoryMounted;

                    if (cell.TreeCount > 0)
                    {
                        if (!cell.Lod0Mounted && dSqXZ <= lod0MountSq) MountLayer(cell, 0);
                        if (!cell.Lod1Mounted && dSqXZ <= lod1MountSq) MountLayer(cell, 1);
                    }
                    if (cell.DetailCount > 0 && !cell.DetailMounted && dSqXZ <= detMountSq)
                        MountLayer(cell, 2);
                    if (cell.CloseUnderstoryCount > 0 && !cell.CloseUnderstoryMounted && dSqXZ <= cuMountSq)
                        MountLayer(cell, 3);

                    bool nowMounted = cell.Lod0Mounted || cell.Lod1Mounted || cell.DetailMounted || cell.CloseUnderstoryMounted;
                    if (!wasMounted && nowMounted)
                        _mountedNearCells.Add(cell);
                }
            }
        }

        private void MountLayer(CellFloraData cell, int layerType) // 0=LOD0, 1=LOD1, 2=Detail, 3=CloseUnderstory
        {
            VariantBatchData[] batches = layerType switch
            {
                0 or 1 => cell.TreeBatches,
                2 => cell.DetailBatches,
                _ => cell.CloseUnderstoryBatches,
            };
            List<MultiMeshInstance3D> targetList = layerType switch
            {
                0 => cell.MountedLod0Nodes,
                1 => cell.MountedLod1Nodes,
                2 => cell.MountedDetailNodes,
                _ => cell.MountedCloseUnderstoryNodes,
            };
            ShaderMaterial? barkMat = layerType switch
            {
                0 => _barkLod0Mat,
                1 => _barkLod1Mat,
                2 => _barkDetailMat,
                _ => _barkCloseUnderstoryMat,
            };
            ShaderMaterial? leafMat = layerType switch
            {
                0 => _leafLod0Mat,
                1 => _leafLod1Mat,
                2 => _leafDetailMat,
                _ => _leafCloseUnderstoryMat,
            };
            float visEnd = layerType switch
            {
                0 => cell.Lod0VisEnd,
                1 => cell.Lod1VisEnd,
                2 => cell.DetailVisEnd,
                _ => cell.CloseUnderstoryVisEnd,
            };

            bool isDetail = layerType >= 2;
            int lodIdx = layerType == 1 ? 1 : 0;

            for (int i = 0; i < batches.Length; i++)
            {
                MultiMeshInstance3D mmi = AcquirePooledNode();
                mmi.Multimesh = batches[i].GetOrBuildMultiMesh(_meshLib, lodIdx, isDetail, barkMat, leafMat);
                mmi.Position = cell.Center;
                mmi.MaterialOverride = null; // Multi-surface ArrayMesh uses Surface 0 (bark_moss) + Surface 1 (flora_wind)!
                mmi.CastShadow = GeometryInstance3D.ShadowCastingSetting.Off;
                mmi.VisibilityRangeBegin = 0.0f;
                mmi.VisibilityRangeBeginMargin = 0.0f;
                mmi.VisibilityRangeEnd = visEnd;
                mmi.VisibilityRangeEndMargin = FloraLodConfig.CellHysteresisMargin;
                mmi.Visible = true;
                AddChild(mmi);
                targetList.Add(mmi);
            }

            if (layerType == 0) { cell.Lod0Mounted = true; cell.ShadowEnabled = false; MountedLod0NodeCount += batches.Length; }
            else if (layerType == 1) { cell.Lod1Mounted = true; MountedLod1NodeCount += batches.Length; }
            else if (layerType == 2) { cell.DetailMounted = true; MountedDetailNodeCount += batches.Length; }
            else { cell.CloseUnderstoryMounted = true; MountedCloseUnderstoryNodeCount += batches.Length; }
        }

        private void UnmountLayer(CellFloraData cell, int layerType)
        {
            List<MultiMeshInstance3D> list = layerType switch
            {
                0 => cell.MountedLod0Nodes,
                1 => cell.MountedLod1Nodes,
                2 => cell.MountedDetailNodes,
                _ => cell.MountedCloseUnderstoryNodes,
            };

            int cnt = list.Count;
            for (int i = 0; i < cnt; i++)
                ReleasePooledNode(list[i]);
            list.Clear();

            if (layerType == 0) { cell.Lod0Mounted = false; cell.ShadowEnabled = false; MountedLod0NodeCount -= cnt; }
            else if (layerType == 1) { cell.Lod1Mounted = false; MountedLod1NodeCount -= cnt; }
            else if (layerType == 2) { cell.DetailMounted = false; MountedDetailNodeCount -= cnt; }
            else { cell.CloseUnderstoryMounted = false; MountedCloseUnderstoryNodeCount -= cnt; }
        }

        private MultiMeshInstance3D AcquirePooledNode()
        {
            if (_nodePool.Count > 0)
                return _nodePool.Pop();

            return new MultiMeshInstance3D
            {
                CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
            };
        }

        private void ReleasePooledNode(MultiMeshInstance3D mmi)
        {
            mmi.Visible = false;
            mmi.CastShadow = GeometryInstance3D.ShadowCastingSetting.Off;
            mmi.Multimesh = null;
            if (mmi.GetParent() == this)
                RemoveChild(mmi);
            _nodePool.Push(mmi);
        }

        private void MeasureRealFrustumTelemetryAndShadows(Camera3D camera)
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

            float lod0ShadowCutoff = FloraLodConfig.Lod0End + FloraLodConfig.TransitionHalfBand + 35.0f;
            for (int i = 0; i < _mountedNearCells.Count; i++)
            {
                CellFloraData cell = _mountedNearCells[i];
                float dist = camPos.DistanceTo(cell.Center);
                bool inFrustum = InFrustum(cell.Center, cell.Radius3D);

                bool shouldCastShadow = cell.Lod0Mounted && inFrustum && dist <= lod0ShadowCutoff;
                if (cell.Lod0Mounted && cell.ShadowEnabled != shouldCastShadow)
                {
                    cell.ShadowEnabled = shouldCastShadow;
                    var mode = shouldCastShadow
                        ? GeometryInstance3D.ShadowCastingSetting.On
                        : GeometryInstance3D.ShadowCastingSetting.Off;
                    for (int k = 0; k < cell.MountedLod0Nodes.Count; k++)
                        cell.MountedLod0Nodes[k].CastShadow = mode;
                }

                if (!inFrustum) continue;

                if (cell.Lod0Mounted && dist <= cell.Lod0VisEnd) visNodes += cell.MountedLod0Nodes.Count;
                if (cell.Lod1Mounted && dist <= cell.Lod1VisEnd) visNodes += cell.MountedLod1Nodes.Count;
                if (cell.DetailMounted && dist <= cell.DetailVisEnd)
                {
                    visNodes += cell.MountedDetailNodes.Count;
                    detailInstances += cell.DetailCount;
                }
                if (cell.CloseUnderstoryMounted && dist <= cell.CloseUnderstoryVisEnd)
                {
                    visNodes += cell.MountedCloseUnderstoryNodes.Count;
                    detailInstances += cell.CloseUnderstoryCount;
                }

                if (cell.Lod0Mounted && dist <= lod0ShadowCutoff)
                {
                    lod0Trees += cell.TreeCount;
                    if (cell.ShadowEnabled) shadowTrees += cell.TreeCount;
                }
                else if (cell.Lod1Mounted && dist <= FloraLodConfig.Lod1End + FloraLodConfig.TransitionHalfBand)
                {
                    lod1Trees += cell.TreeCount;
                }
            }

            for (int i = 0; i < _activeFarCellCount; i++)
            {
                ref FarCanopyCell cell = ref _farCells[i];
                float dist = camPos.DistanceTo(cell.Center);
                if (dist < cell.Lod2VisBegin || dist > cell.Lod2VisEnd) continue;
                if (!InFrustum(cell.Center, cell.Radius3D)) continue;

                visNodes += cell.Lod2Nodes.Length;
                if (dist > FloraLodConfig.Lod2Start && dist <= FloraLodConfig.Lod2End + 180.0f)
                    lod2Trees += cell.TreeCount;
            }

            BucketActiveLod0Trees = lod0Trees;
            BucketActiveLod1Trees = lod1Trees;
            BucketActiveLod2Trees = lod2Trees;
            ShadowTrees = shadowTrees;
            VisibleMultiMeshNodes = visNodes;
            ActiveDetailInstances = detailInstances;
        }

        public (int Lod0, int Lod1, int Lod2, int Shadow, int VisNodes, int MountedNodes) SamplePerspectiveTelemetry(
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

            float lod0ShadowCutoff = FloraLodConfig.Lod0End + FloraLodConfig.TransitionHalfBand + 35.0f;
            int l0 = 0, l1 = 0, l2 = 0, sh = 0, vn = 0;
            int mountedTotal = Lod2NodeCount;

            for (int z = 0; z < FloraLodConfig.NearRows; z++)
            {
                for (int x = 0; x < FloraLodConfig.NearCols; x++)
                {
                    CellFloraData? c = _nearGrid[x, z];
                    if (c == null) continue;
                    float dx = c.Center.X - samplePos.X;
                    float dz = c.Center.Z - samplePos.Z;
                    float dXZ = MathF.Sqrt(dx * dx + dz * dz);

                    bool m0 = c.TreeCount > 0 && dXZ <= FloraLodConfig.NearLod0MountRadiusM;
                    bool m1 = c.TreeCount > 0 && dXZ <= FloraLodConfig.NearLod1MountRadiusM;
                    bool md = c.DetailCount > 0 && dXZ <= FloraLodConfig.NearDetailMountRadiusM;
                    bool mc = c.CloseUnderstoryCount > 0 && dXZ <= FloraLodConfig.NearUnderstoryMountRadiusM;
                    if (m0) mountedTotal += c.TreeBatches.Length;
                    if (m1) mountedTotal += c.TreeBatches.Length;
                    if (md) mountedTotal += c.DetailBatches.Length;
                    if (mc) mountedTotal += c.CloseUnderstoryBatches.Length;
                    if (!m0 && !m1 && !md && !mc) continue;

                    float dist = samplePos.DistanceTo(c.Center);
                    if (!InFrustum(c.Center, c.Radius3D)) continue;

                    if (m0 && dist <= c.Lod0VisEnd) vn += c.TreeBatches.Length;
                    if (m1 && dist <= c.Lod1VisEnd) vn += c.TreeBatches.Length;
                    if (md && dist <= c.DetailVisEnd) vn += c.DetailBatches.Length;
                    if (mc && dist <= c.CloseUnderstoryVisEnd) vn += c.CloseUnderstoryBatches.Length;

                    if (m0 && dist <= lod0ShadowCutoff) { l0 += c.TreeCount; sh += c.TreeCount; }
                    else if (m1 && dist <= FloraLodConfig.Lod1End + FloraLodConfig.TransitionHalfBand) { l1 += c.TreeCount; }
                }
            }

            for (int i = 0; i < _activeFarCellCount; i++)
            {
                ref FarCanopyCell c = ref _farCells[i];
                float dist = samplePos.DistanceTo(c.Center);
                if (dist < c.Lod2VisBegin || dist > c.Lod2VisEnd || !InFrustum(c.Center, c.Radius3D)) continue;
                vn += c.Lod2Nodes.Length;
                if (dist > FloraLodConfig.Lod2Start && dist <= FloraLodConfig.Lod2End + 180.0f)
                    l2 += c.TreeCount;
            }
            return (l0, l1, l2, sh, vn, mountedTotal);
        }

        public void UpdateWeatherAndSeason(ImageTexture weatherTex, float seasonPhase, float globalWindGust)
        {
            void ApplyLeaf(ShaderMaterial? mat)
            {
                if (mat == null) return;
                mat.SetShaderParameter("weather_dynamic_tex", weatherTex);
                mat.SetShaderParameter("season_phase", seasonPhase);
                mat.SetShaderParameter("global_wind_gust", globalWindGust);
            }
            void ApplyBark(ShaderMaterial? mat)
            {
                if (mat == null) return;
                mat.SetShaderParameter("weather_dynamic_tex", weatherTex);
                mat.SetShaderParameter("global_wind_gust", globalWindGust);
            }
            ApplyLeaf(_leafLod0Mat);
            ApplyLeaf(_leafLod1Mat);
            ApplyLeaf(_leafLod2Mat);
            ApplyLeaf(_leafDetailMat);
            ApplyLeaf(_leafCloseUnderstoryMat);

            ApplyBark(_barkLod0Mat);
            ApplyBark(_barkLod1Mat);
            ApplyBark(_barkDetailMat);
            ApplyBark(_barkCloseUnderstoryMat);
        }

        public string GetDominantSpeciesNameAt(float worldX, float worldZ) => _spawner.GetDominantSpeciesNameAt(worldX, worldZ);

        public ImageTexture BuildEmptyCoverageTexture(HydrologySolver hydrology) => _spawner.BuildEmptyCoverageTexture(hydrology);

        public void ClearFlora()
        {
            _mountedNearCells.Clear();
            while (_nodePool.Count > 0)
                _nodePool.Pop().QueueFree();

            foreach (Node child in GetChildren())
                child.QueueFree();

            Array.Clear(_nearGrid, 0, _nearGrid.Length);
            Array.Clear(_farCells, 0, _farCells.Length);
            _activeFarCellCount = 0;
            MountedLod0NodeCount = 0;
            MountedLod1NodeCount = 0;
            MountedDetailNodeCount = 0;
            MountedCloseUnderstoryNodeCount = 0;
            Lod2NodeCount = 0;
            BucketActiveLod0Trees = 0;
            BucketActiveLod1Trees = 0;
            BucketActiveLod2Trees = 0;
            ShadowTrees = 0;
            VisibleMultiMeshNodes = 0;
            ActiveDetailInstances = 0;
        }

        private static CellFloraData BuildPureNearCellData(
            List<FloraInstance>? trees,
            List<FloraInstance> allDetails,
            int nx,
            int nz)
        {
            float sumY = 0.0f;
            int totalCnt = 0;
            if (trees != null)
                for (int i = 0; i < trees.Count; i++) { sumY += trees[i].Transform.Origin.Y; totalCnt++; }
            for (int i = 0; i < allDetails.Count; i++) { sumY += allDetails[i].Transform.Origin.Y; totalCnt++; }

            Vector3 cellCenter = new Vector3(
                (nx + 0.5f) * FloraLodConfig.NearCellSize,
                totalCnt > 0 ? sumY / totalCnt : 0.0f,
                (nz + 0.5f) * FloraLodConfig.NearCellSize
            );

            var tallDetails = new List<FloraInstance>(allDetails.Count / 2);
            var closeUnderstory = new List<FloraInstance>(allDetails.Count / 2);
            float maxOffSq = 0.0f;

            if (trees != null)
            {
                for (int i = 0; i < trees.Count; i++)
                {
                    float dSq = trees[i].Transform.Origin.DistanceSquaredTo(cellCenter);
                    if (dSq > maxOffSq) maxOffSq = dSq;
                }
            }
            for (int i = 0; i < allDetails.Count; i++)
            {
                FloraInstance inst = allDetails[i];
                float dSq = inst.Transform.Origin.DistanceSquaredTo(cellCenter);
                if (dSq > maxOffSq) maxOffSq = dSq;
                if (FloraMeshLibrary.IsCloseUnderstorySpecies(inst.Species))
                    closeUnderstory.Add(inst);
                else
                    tallDetails.Add(inst);
            }

            float radius3D = MathF.Sqrt(maxOffSq) + 18.0f;
            float diagPad = MathF.Max(FloraLodConfig.MinNearCellDiagPad, radius3D);
            float margin = FloraLodConfig.CellHysteresisMargin;

            return new CellFloraData
            {
                Center = cellCenter,
                Radius3D = diagPad,
                TreeCount = trees?.Count ?? 0,
                DetailCount = tallDetails.Count,
                CloseUnderstoryCount = closeUnderstory.Count,
                Lod0VisEnd = FloraLodConfig.Lod0End + FloraLodConfig.TransitionHalfBand + diagPad + margin,
                Lod1VisEnd = FloraLodConfig.Lod1End + FloraLodConfig.TransitionHalfBand + diagPad + margin,
                DetailVisEnd = FloraLodConfig.DetailFadeEnd + diagPad + margin,
                CloseUnderstoryVisEnd = FloraLodConfig.CloseUnderstoryFadeEnd + diagPad + margin,
                TreeBatches = trees != null && trees.Count > 0 ? GroupByCanonicalMeshKey(trees, cellCenter) : Array.Empty<VariantBatchData>(),
                DetailBatches = tallDetails.Count > 0 ? GroupByCanonicalMeshKey(tallDetails, cellCenter) : Array.Empty<VariantBatchData>(),
                CloseUnderstoryBatches = closeUnderstory.Count > 0 ? GroupByCanonicalMeshKey(closeUnderstory, cellCenter) : Array.Empty<VariantBatchData>(),
            };
        }

        private static VariantBatchData[] GroupByCanonicalMeshKey(List<FloraInstance> instances, Vector3 cellCenter)
        {
            var byKey = new Dictionary<FloraMeshLibrary.MeshKey, List<FloraInstance>>();
            for (int i = 0; i < instances.Count; i++)
            {
                var inst = instances[i];
                var key = FloraMeshLibrary.GetCanonicalMeshKey(inst.Species, inst.Variant);
                if (!byKey.TryGetValue(key, out var list))
                {
                    list = new List<FloraInstance>(12);
                    byKey[key] = list;
                }
                list.Add(inst);
            }

            var result = new VariantBatchData[byKey.Count];
            int idx = 0;
            foreach (var kv in byKey)
                result[idx++] = new VariantBatchData(kv.Key, kv.Value, cellCenter);
            return result;
        }

        private FarCanopyCell BuildGroupedFarCellLod2(List<FloraInstance> instances, int fx, int fz)
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
            var byArch = new List<FloraInstance>?[4];
            for (int i = 0; i < instances.Count; i++)
            {
                FloraInstance inst = instances[i];
                float dSq = inst.Transform.Origin.DistanceSquaredTo(cellCenter);
                if (dSq > maxOffSq) maxOffSq = dSq;

                int arch = (int)GetLod2Archetype(inst.Species);
                byArch[arch] ??= new List<FloraInstance>(32);
                byArch[arch]!.Add(inst);
            }

            float radius3D = MathF.Sqrt(maxOffSq) + 18.0f;
            float diagPad = MathF.Max(FloraLodConfig.MinFarCellDiagPad, radius3D);
            float margin = FloraLodConfig.CellHysteresisMargin;

            float rawBegin = (FloraLodConfig.Lod2Start - FloraLodConfig.TransitionHalfBand) - diagPad - margin;
            float lod2VisBegin = MathF.Max(0.0f, rawBegin);
            float lod2VisEnd = FloraLodConfig.FarFadeEnd + diagPad + margin;

            FloraSpeciesId[] repSpecies =
            {
                FloraSpeciesId.StarAppleCanopy,
                FloraSpeciesId.BorealSnowPine,
                FloraSpeciesId.GinkgoAncientGold,
                FloraSpeciesId.DragonBloodTree,
            };

            var lod2Nodes = new List<MultiMeshInstance3D>(4);
            for (int a = 0; a < 4; a++)
            {
                var list = byArch[a];
                if (list == null || list.Count == 0) continue;

                var mm = new MultiMesh
                {
                    TransformFormat = MultiMesh.TransformFormatEnum.Transform3D,
                    UseColors = false,
                    UseCustomData = true,
                    Mesh = _meshLib.GetMesh(repSpecies[a], 0, 2, null, _leafLod2Mat),
                    InstanceCount = list.Count,
                };

                for (int i = 0; i < list.Count; i++)
                {
                    Transform3D w = list[i].Transform;
                    mm.SetInstanceTransform(i, new Transform3D(w.Basis, w.Origin - cellCenter));
                    mm.SetInstanceCustomData(i, list[i].CustomData);
                }

                var mmi = new MultiMeshInstance3D
                {
                    Name = $"Far600_{fx}_{fz}_A{a}_L2",
                    Position = cellCenter,
                    Multimesh = mm,
                    MaterialOverride = null,
                    CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
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

        private static Lod2Archetype GetLod2Archetype(FloraSpeciesId sp) => sp switch
        {
            FloraSpeciesId.GiantSequoiaReddawn or FloraSpeciesId.BorealSnowPine or FloraSpeciesId.SilverGlacierSpruce => Lod2Archetype.Conifer,
            FloraSpeciesId.GinkgoAncientGold or FloraSpeciesId.CrimsonSteppeMaple or FloraSpeciesId.WeepingSilverBirch => Lod2Archetype.Deciduous,
            FloraSpeciesId.DragonBloodTree or FloraSpeciesId.SavannaUmbrellaAcacia or FloraSpeciesId.BaobabPrehistoric => Lod2Archetype.DesertUmbrella,
            _ => Lod2Archetype.Broadleaf,
        };

        private void EnsureMaterials(AtmosphereClimate climate)
        {
            var leafShader = GD.Load<Shader>("res://shaders/flora_wind.gdshader");
            var barkShader = GD.Load<Shader>("res://shaders/bark_moss.gdshader");
            _windDataTex = BuildWindDataTexture(climate);
            var bot = BotanicalTextureGenerator.EnsureAndLoadAll();

            ShaderMaterial BuildLeafMat(ShaderMaterial? existing, int lodLevel)
            {
                var mat = existing ?? new ShaderMaterial { Shader = leafShader };
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

            ShaderMaterial BuildBarkMat(ShaderMaterial? existing, int lodLevel)
            {
                var mat = existing ?? new ShaderMaterial { Shader = barkShader };
                mat.SetShaderParameter("wind_dir_speed_tex", _windDataTex);
                mat.SetShaderParameter("bark_hardwood_albedo", bot.BarkHardwoodAlbedo);
                mat.SetShaderParameter("bark_hardwood_normal", bot.BarkHardwoodNormal);
                mat.SetShaderParameter("bark_hardwood_roughness", bot.BarkHardwoodRoughness);
                mat.SetShaderParameter("bark_conifer_albedo", bot.BarkConiferAlbedo);
                mat.SetShaderParameter("bark_conifer_normal", bot.BarkConiferNormal);
                mat.SetShaderParameter("bark_conifer_roughness", bot.BarkConiferRoughness);
                mat.SetShaderParameter("bark_pale_albedo", bot.BarkPaleTex);
                mat.SetShaderParameter("moss_albedo", bot.MossAlbedo);
                mat.SetShaderParameter("moss_normal", bot.MossNormal);
                FloraLodConfig.ApplyToFloraMaterial(mat, lodLevel, LodDebugEnabled);
                return mat;
            }

            _leafLod0Mat = BuildLeafMat(_leafLod0Mat, 0);
            _leafLod1Mat = BuildLeafMat(_leafLod1Mat, 1);
            _leafLod2Mat = BuildLeafMat(_leafLod2Mat, 2);
            _leafDetailMat = BuildLeafMat(_leafDetailMat, -1);
            _leafCloseUnderstoryMat = BuildLeafMat(_leafCloseUnderstoryMat, -2);

            _barkLod0Mat = BuildBarkMat(_barkLod0Mat, 0);
            _barkLod1Mat = BuildBarkMat(_barkLod1Mat, 1);
            _barkDetailMat = BuildBarkMat(_barkDetailMat, -1);
            _barkCloseUnderstoryMat = BuildBarkMat(_barkCloseUnderstoryMat, -2);
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
