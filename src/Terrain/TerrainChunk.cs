using Godot;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Terrain
{
    public partial class TerrainChunk : MeshInstance3D
    {
        public void Build(
            WorldGenerator terrain,
            ClimateSimulator climate,
            SoilSimulator soil,
            int chunkX,
            int chunkZ,
            Material material)
        {
            float chunkSize = WorldGenerator.ChunkSizeMeters;
            int vertsPerSide = WorldGenerator.ChunkVerticesPerSide;
            float step = chunkSize / (vertsPerSide - 1);
            float originX = chunkX * chunkSize;
            float originZ = chunkZ * chunkSize;

            const float normalEps = 2.0f;

            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            for (int gz = 0; gz < vertsPerSide; gz++)
            {
                float worldZ = originZ + gz * step;
                for (int gx = 0; gx < vertsPerSide; gx++)
                {
                    float worldX = originX + gx * step;
                    float h = terrain.SampleHeight(worldX, worldZ);
                    float riverMask = terrain.SampleRiverMask(worldX, worldZ);
                    ClimateSample cs = climate.SampleClimate(worldX, worldZ);
                    SoilSample ss = soil.SampleSoil(worldX, worldZ);

                    float hL = terrain.SampleHeight(worldX - normalEps, worldZ);
                    float hR = terrain.SampleHeight(worldX + normalEps, worldZ);
                    float hD = terrain.SampleHeight(worldX, worldZ - normalEps);
                    float hU = terrain.SampleHeight(worldX, worldZ + normalEps);
                    Vector3 normal = new Vector3(hL - hR, 2.0f * normalEps, hD - hU).Normalized();

                    float tempNorm = Mathf.Clamp((cs.TemperatureC + 15.0f) / 53.0f, 0.0f, 1.0f);

                    st.SetNormal(normal);
                    st.SetUV(new Vector2(worldX / WorldGenerator.RegionWidthMeters, worldZ / WorldGenerator.RegionDepthMeters));
                    st.SetColor(new Color(riverMask, cs.Moisture, tempNorm, ss.SoilDepth));
                    st.AddVertex(new Vector3(gx * step, h, gz * step));
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
