using System.Collections.Generic;
using Godot;
using PrimevalWorld.Core;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Terrain
{
    /// <summary>
    /// 4-Level LOD TerrainChunk (300m x 300m = 32x32 cells) with continuous world normals
    /// and a 24m perimeter Skirt Mesh to prevent seams between adjacent LOD levels.
    /// </summary>
    public partial class TerrainChunk : MeshInstance3D
    {
        private readonly ArrayMesh[] _lodMeshes = new ArrayMesh[4];
        private int _currentLod = -1;
        public Vector3 CenterWorld { get; private set; }
        public float MinH { get; private set; }
        public float MaxH { get; private set; }
        public bool IsCoastline { get; private set; }
        public int CurrentLod => _currentLod;

        private static readonly int[][] SharedLodIndices = BuildAllSharedLodIndices();

        private static int[][] BuildAllSharedLodIndices()
        {
            var result = new int[4][];
            int[] steps = { 1, 2, 4, 4 };
            for (int lod = 0; lod < 4; lod++)
            {
                int step = steps[lod];
                int n = WorldPhysicsConfig.CellsPerChunk / step + 1; // 33, 17, 9, 9 (no 4x4)
                var indices = new List<int>((n - 1) * (n - 1) * 6 + n * 4 * 6);

                // Main surface grid
                for (int gz = 0; gz < n - 1; gz++)
                {
                    for (int gx = 0; gx < n - 1; gx++)
                    {
                        int i0 = gz * n + gx;
                        int i1 = i0 + 1;
                        int i2 = i0 + n;
                        int i3 = i2 + 1;
                        indices.Add(i0); indices.Add(i1); indices.Add(i2);
                        indices.Add(i1); indices.Add(i3); indices.Add(i2);
                    }
                }

                // 4 Edge Skirts (base surface edge vertices followed by n*4 skirt-bottom vertices)
                int skirtBase = n * n;
                // North edge (gz=0, gx=0..n-1)
                for (int i = 0; i < n - 1; i++)
                {
                    int t0 = i, t1 = i + 1, b0 = skirtBase + i, b1 = skirtBase + i + 1;
                    indices.Add(t0); indices.Add(b0); indices.Add(t1);
                    indices.Add(t1); indices.Add(b0); indices.Add(b1);
                }
                // South edge (gz=n-1)
                int sOff = skirtBase + n;
                int sTop = (n - 1) * n;
                for (int i = 0; i < n - 1; i++)
                {
                    int t0 = sTop + i, t1 = sTop + i + 1, b0 = sOff + i, b1 = sOff + i + 1;
                    indices.Add(t0); indices.Add(t1); indices.Add(b0);
                    indices.Add(t1); indices.Add(b1); indices.Add(b0);
                }
                // West edge (gx=0)
                int wOff = skirtBase + 2 * n;
                for (int i = 0; i < n - 1; i++)
                {
                    int t0 = i * n, t1 = (i + 1) * n, b0 = wOff + i, b1 = wOff + i + 1;
                    indices.Add(t0); indices.Add(t1); indices.Add(b0);
                    indices.Add(t1); indices.Add(b1); indices.Add(b0);
                }
                // East edge (gx=n-1)
                int eOff = skirtBase + 3 * n;
                for (int i = 0; i < n - 1; i++)
                {
                    int t0 = i * n + (n - 1), t1 = (i + 1) * n + (n - 1), b0 = eOff + i, b1 = eOff + i + 1;
                    indices.Add(t0); indices.Add(b0); indices.Add(t1);
                    indices.Add(t1); indices.Add(b0); indices.Add(b1);
                }

                result[lod] = indices.ToArray();
            }
            return result;
        }

        public void Build(ErosionPhysics erosion, int chunkX, int chunkZ, Material material)
        {
            int cellsPerChunk = WorldPhysicsConfig.CellsPerChunk; // 32
            float cell = WorldPhysicsConfig.CellSize;            // 9.375m
            int startGx = chunkX * cellsPerChunk;
            int startGz = chunkZ * cellsPerChunk;
            float originX = startGx * cell;
            float originZ = startGz * cell;

            CenterWorld = new Vector3(
                originX + WorldPhysicsConfig.ChunkSize * 0.5f,
                erosion.HeightMap[(startGz + cellsPerChunk / 2) * WorldPhysicsConfig.VertW + (startGx + cellsPerChunk / 2)],
                originZ + WorldPhysicsConfig.ChunkSize * 0.5f
            );

            int[] steps = { 1, 2, 4, 4 };
            float minH = float.MaxValue;
            float maxH = float.MinValue;
            for (int lod = 0; lod < 4; lod++)
            {
                int step = steps[lod];
                int n = cellsPerChunk / step + 1;
                int totalVerts = n * n + 4 * n;

                var verts = new Vector3[totalVerts];
                var normals = new Vector3[totalVerts];
                var uvs = new Vector2[totalVerts];

                int vIdx = 0;
                for (int lz = 0; lz < n; lz++)
                {
                    int gz = startGz + lz * step;
                    float localZ = lz * step * cell;
                    float worldZ = originZ + localZ;
                    for (int lx = 0; lx < n; lx++)
                    {
                        int gx = startGx + lx * step;
                        float localX = lx * step * cell;
                        float worldX = originX + localX;
                        int gIdx = gz * WorldPhysicsConfig.VertW + gx;
                        float h = erosion.HeightMap[gIdx];
                        if (lod == 0)
                        {
                            if (h < minH) minH = h;
                            if (h > maxH) maxH = h;
                        }

                        verts[vIdx] = new Vector3(localX, h, localZ);
                        normals[vIdx] = erosion.NormalMap[gIdx];
                        uvs[vIdx] = new Vector2(worldX / WorldPhysicsConfig.WorldWidth, worldZ / WorldPhysicsConfig.WorldDepth);
                        vIdx++;
                    }
                }

                // Copy 4 perimeter skirts dropped by SkirtDepth
                float drop = WorldPhysicsConfig.SkirtDepth;
                // North
                for (int i = 0; i < n; i++) CopySkirt(i, vIdx++);
                // South
                int sTop = (n - 1) * n;
                for (int i = 0; i < n; i++) CopySkirt(sTop + i, vIdx++);
                // West
                for (int i = 0; i < n; i++) CopySkirt(i * n, vIdx++);
                // East
                for (int i = 0; i < n; i++) CopySkirt(i * n + (n - 1), vIdx++);

                void CopySkirt(int src, int dst)
                {
                    Vector3 p = verts[src];
                    verts[dst] = new Vector3(p.X, p.Y - drop, p.Z);
                    normals[dst] = normals[src];
                    uvs[dst] = uvs[src];
                }

                var arrays = new Godot.Collections.Array();
                arrays.Resize((int)Mesh.ArrayType.Max);
                arrays[(int)Mesh.ArrayType.Vertex] = verts;
                arrays[(int)Mesh.ArrayType.Normal] = normals;
                arrays[(int)Mesh.ArrayType.TexUV] = uvs;
                arrays[(int)Mesh.ArrayType.Index] = SharedLodIndices[lod];

                var mesh = new ArrayMesh();
                mesh.AddSurfaceFromArrays(Mesh.PrimitiveType.Triangles, arrays);
                _lodMeshes[lod] = mesh;
            }

            MinH = minH;
            MaxH = maxH;
            IsCoastline = minH < 2.5f && maxH > -2.5f;

            MaterialOverride = material;
            Position = new Vector3(originX, 0.0f, originZ);
            CastShadow = ShadowCastingSetting.On;
            SetLod(IsCoastline ? 1 : 2);
        }

        public void SetLod(int lod)
        {
            if (lod == _currentLod) return;
            _currentLod = lod;
            Mesh = _lodMeshes[lod];
        }
    }
}
