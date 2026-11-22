using Godot;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Terrain
{
    /// <summary>
    /// Builds both the coastal ocean plane (at sea level) and the sloped meandering
    /// river ribbon mesh that follows the carved river channel downhill to the bay.
    /// </summary>
    public partial class WaterSurface : Node3D
    {
        private MeshInstance3D? _oceanMesh;
        private MeshInstance3D? _riverMesh;
        private ShaderMaterial? _oceanMaterial;
        private ShaderMaterial? _riverMaterial;

        public void BuildWater(WorldGenerator generator)
        {
            if (_oceanMaterial == null)
            {
                var waterShader = GD.Load<Shader>("res://shaders/water_river_ocean.gdshader");
                _oceanMaterial = new ShaderMaterial { Shader = waterShader };
                _oceanMaterial.SetShaderParameter("flow_speed", new Vector2(0.03f, 0.02f));
                _oceanMaterial.SetShaderParameter("shallow_color", new Color(0.08f, 0.58f, 0.62f, 0.84f));
                _oceanMaterial.SetShaderParameter("deep_color", new Color(0.02f, 0.14f, 0.28f, 0.96f));

                _riverMaterial = new ShaderMaterial { Shader = waterShader };
                _riverMaterial.SetShaderParameter("flow_speed", new Vector2(0.0f, 0.22f));
                _riverMaterial.SetShaderParameter("shallow_color", new Color(0.10f, 0.52f, 0.56f, 0.82f));
                _riverMaterial.SetShaderParameter("deep_color", new Color(0.04f, 0.24f, 0.36f, 0.92f));
            }

            BuildOceanPlane();
            BuildRiverRibbon(generator);
        }

        private void BuildOceanPlane()
        {
            if (_oceanMesh == null)
            {
                _oceanMesh = new MeshInstance3D
                {
                    Name = "OceanPlane",
                    CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
                };
                AddChild(_oceanMesh);
            }

            var plane = new PlaneMesh
            {
                Size = new Vector2(WorldGenerator.RegionSizeMeters + 400.0f, WorldGenerator.RegionSizeMeters + 400.0f),
                SubdivideWidth = 48,
                SubdivideDepth = 48,
            };
            _oceanMesh.Mesh = plane;
            _oceanMesh.MaterialOverride = _oceanMaterial;
            _oceanMesh.Position = new Vector3(
                WorldGenerator.RegionSizeMeters * 0.5f,
                WorldGenerator.SeaLevel,
                WorldGenerator.RegionSizeMeters * 0.5f
            );
        }

        private void BuildRiverRibbon(WorldGenerator generator)
        {
            _riverMesh?.QueueFree();
            _riverMesh = new MeshInstance3D
            {
                Name = "RiverRibbon",
                CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
            };
            AddChild(_riverMesh);

            const int zSteps = 160;
            const int xSteps = 9;
            float maxZ = WorldGenerator.RegionSizeMeters * 0.88f;
            float dz = maxZ / zSteps;

            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            for (int iz = 0; iz <= zSteps; iz++)
            {
                float z = iz * dz;
                var (centerX, waterY, halfW) = generator.SampleRiverSpine(z);
                // Slightly wider than carved riverbed so water edges tuck cleanly into banks
                float ribbonHalfW = halfW * 1.38f;
                float vCoord = z * 0.04f;

                for (int ix = 0; ix < xSteps; ix++)
                {
                    float u = ix / (float)(xSteps - 1);
                    float x = centerX + (u - 0.5f) * 2.0f * ribbonHalfW;

                    st.SetNormal(Vector3.Up);
                    st.SetUV(new Vector2(u, vCoord));
                    st.AddVertex(new Vector3(x, waterY, z));
                }
            }

            for (int iz = 0; iz < zSteps; iz++)
            {
                for (int ix = 0; ix < xSteps - 1; ix++)
                {
                    int i0 = iz * xSteps + ix;
                    int i1 = i0 + 1;
                    int i2 = i0 + xSteps;
                    int i3 = i2 + 1;

                    st.AddIndex(i0);
                    st.AddIndex(i1);
                    st.AddIndex(i2);

                    st.AddIndex(i1);
                    st.AddIndex(i3);
                    st.AddIndex(i2);
                }
            }

            _riverMesh.Mesh = st.Commit();
            _riverMesh.MaterialOverride = _riverMaterial;
        }
    }
}
