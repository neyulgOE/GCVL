using Godot;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Terrain
{
    /// <summary>
    /// Builds an expansive 16km x 16km Horizon Ocean Plane that merges seamlessly into
    /// atmospheric fog (eliminating floating square borders) plus a variable-width
    /// sloped RiverRibbon mesh following the carved river valley.
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
                _oceanMaterial.SetShaderParameter("flow_speed", new Vector2(0.025f, 0.018f));
                _oceanMaterial.SetShaderParameter("shallow_color", new Color(0.07f, 0.48f, 0.52f, 0.85f));
                _oceanMaterial.SetShaderParameter("deep_color", new Color(0.02f, 0.11f, 0.22f, 0.98f));

                _riverMaterial = new ShaderMaterial { Shader = waterShader };
                _riverMaterial.SetShaderParameter("flow_speed", new Vector2(0.0f, 0.26f));
                _riverMaterial.SetShaderParameter("shallow_color", new Color(0.09f, 0.44f, 0.48f, 0.82f));
                _riverMaterial.SetShaderParameter("deep_color", new Color(0.03f, 0.20f, 0.30f, 0.94f));
            }

            BuildHorizonOceanPlane();
            BuildRiverRibbon(generator);
        }

        private void BuildHorizonOceanPlane()
        {
            if (_oceanMesh == null)
            {
                _oceanMesh = new MeshInstance3D
                {
                    Name = "HorizonOceanPlane",
                    CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
                };
                AddChild(_oceanMesh);
            }

            // 16km x 16km ocean plane extends well beyond fog horizon
            var plane = new PlaneMesh
            {
                Size = new Vector2(16384.0f, 16384.0f),
                SubdivideWidth = 96,
                SubdivideDepth = 96,
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

            const int zSteps = 180;
            const int xSteps = 9;
            float minZ = WorldGenerator.RegionSizeMeters * 0.06f;
            float maxZ = WorldGenerator.RegionSizeMeters * 0.84f;
            float dz = (maxZ - minZ) / zSteps;

            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            for (int iz = 0; iz <= zSteps; iz++)
            {
                float z = minZ + iz * dz;
                var (centerX, waterY, halfW, _) = generator.SampleRiverSpine(z);
                float ribbonHalfW = halfW * 1.42f;
                float vCoord = z * 0.045f;

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
