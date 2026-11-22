using Godot;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Terrain
{
    /// <summary>
    /// A single seamless 128m x 128m terrain chunk with analytic continuous normals
    /// across chunk boundaries and vertex-encoded ecological masks.
    /// </summary>
    public partial class TerrainChunk : MeshInstance3D
    {
        public void Build(WorldGenerator generator, int chunkX, int chunkZ, Material material)
        {
            float chunkSize = WorldGenerator.ChunkSizeMeters;
            int vertsPerSide = WorldGenerator.ChunkVerticesPerSide;
            float step = chunkSize / (vertsPerSide - 1);
            float originX = chunkX * chunkSize;
            float originZ = chunkZ * chunkSize;

            const float normalEps = 1.0f;

            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            for (int gz = 0; gz < vertsPerSide; gz++)
            {
                float worldZ = originZ + gz * step;
                for (int gx = 0; gx < vertsPerSide; gx++)
                {
                    float worldX = originX + gx * step;
                    TerrainSample sample = generator.SamplePoint(worldX, worldZ);

                    // Central-difference normal sampled from continuous world field
                    // so adjacent chunks share identical edge normals without seams.
                    float hL = generator.SampleHeight(worldX - normalEps, worldZ);
                    float hR = generator.SampleHeight(worldX + normalEps, worldZ);
                    float hD = generator.SampleHeight(worldX, worldZ - normalEps);
                    float hU = generator.SampleHeight(worldX, worldZ + normalEps);
                    Vector3 normal = new Vector3(hL - hR, 2.0f * normalEps, hD - hU).Normalized();

                    st.SetNormal(normal);
                    st.SetUV(new Vector2(worldX / WorldGenerator.RegionSizeMeters, worldZ / WorldGenerator.RegionSizeMeters));
                    st.SetColor(new Color(sample.RiverMask, sample.Moisture, sample.CoastalMask, sample.ForestDensity));
                    st.AddVertex(new Vector3(gx * step, sample.Height, gz * step));
                }
            }

            for (int gz = 0; gz < vertsPerSide - 1; gz++)
            {
                for (int gx = 0; gx < vertsPerSide - 1; gx++)
                {
                    int i0 = gz * vertsPerSide + gx;
                    int i1 = i0 + 1;
                    int i2 = i0 + vertsPerSide;
                    int i3 = i2 + 1;

                    // Counter-clockwise winding facing +Y
                    st.AddIndex(i0);
                    st.AddIndex(i1);
                    st.AddIndex(i2);

                    st.AddIndex(i1);
                    st.AddIndex(i3);
                    st.AddIndex(i2);
                }
            }

            Mesh = st.Commit();
            MaterialOverride = material;
            Position = new Vector3(originX, 0.0f, originZ);
            CastShadow = ShadowCastingSetting.On;
        }
    }
}
