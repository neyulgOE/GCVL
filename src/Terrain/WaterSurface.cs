using Godot;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Terrain
{
    /// <summary>
    /// Builds the 16km x 16km Horizon Ocean Plane at SeaLevel (0.0m)
    /// plus an Inland Water Mesh covering all blueprint rivers, deltas, and highland lakes
    /// at their exact local bank-derived surface elevations.
    /// </summary>
    public partial class WaterSurface : Node3D
    {
        private MeshInstance3D? _oceanMesh;
        private MeshInstance3D? _inlandWaterMesh;
        private ShaderMaterial? _oceanMaterial;
        private ShaderMaterial? _riverMaterial;

        public void BuildWater(WorldGenerator generator)
        {
            if (_oceanMaterial == null)
            {
                var waterShader = GD.Load<Shader>("res://shaders/water_river_ocean.gdshader");
                _oceanMaterial = new ShaderMaterial { Shader = waterShader };
                _oceanMaterial.SetShaderParameter("flow_speed", new Vector2(0.02f, 0.015f));
                _oceanMaterial.SetShaderParameter("shallow_color", new Color(0.10f, 0.70f, 0.74f, 0.78f));
                _oceanMaterial.SetShaderParameter("deep_color", new Color(0.03f, 0.16f, 0.30f, 0.96f));

                _riverMaterial = new ShaderMaterial { Shader = waterShader };
                _riverMaterial.SetShaderParameter("flow_speed", new Vector2(0.05f, 0.24f));
                _riverMaterial.SetShaderParameter("shallow_color", new Color(0.14f, 0.68f, 0.70f, 0.72f));
                _riverMaterial.SetShaderParameter("deep_color", new Color(0.06f, 0.34f, 0.48f, 0.88f));
            }

            BuildHorizonOceanPlane();
            BuildInlandWaterMesh(generator);
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

            var plane = new PlaneMesh
            {
                Size = new Vector2(16384.0f, 16384.0f),
                SubdivideWidth = 96,
                SubdivideDepth = 96,
            };
            _oceanMesh.Mesh = plane;
            _oceanMesh.MaterialOverride = _oceanMaterial;
            _oceanMesh.Position = new Vector3(
                WorldGenerator.RegionWidthMeters * 0.5f,
                WorldGenerator.SeaLevel,
                WorldGenerator.RegionDepthMeters * 0.5f
            );
        }

        private void BuildInlandWaterMesh(WorldGenerator generator)
        {
            _inlandWaterMesh?.QueueFree();
            _inlandWaterMesh = new MeshInstance3D
            {
                Name = "InlandRiversAndLakes",
                CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
            };
            AddChild(_inlandWaterMesh);

            const int step = 2; // 8m water grid resolution matching rivers & lakes cleanly
            const float cellMeters = 4.0f * step;

            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            bool hasAny = false;
            for (int gz = 0; gz < WorldGenerator.GridDepth - step; gz += step)
            {
                for (int gx = 0; gx < WorldGenerator.GridWidth - step; gx += step)
                {
                    bool w00 = generator.HasInlandWaterAtCell(gx, gz);
                    bool w10 = generator.HasInlandWaterAtCell(gx + step, gz);
                    bool w01 = generator.HasInlandWaterAtCell(gx, gz + step);
                    bool w11 = generator.HasInlandWaterAtCell(gx + step, gz + step);

                    if (!w00 && !w10 && !w01 && !w11) continue;
                    hasAny = true;

                    float y00 = generator.GetInlandWaterYAtCell(gx, gz);
                    float y10 = generator.GetInlandWaterYAtCell(gx + step, gz);
                    float y01 = generator.GetInlandWaterYAtCell(gx, gz + step);
                    float y11 = generator.GetInlandWaterYAtCell(gx + step, gz + step);

                    // Use local average water Y for edges bordering dry banks
                    float avgY = 0.0f;
                    int cnt = 0;
                    if (w00) { avgY += y00; cnt++; }
                    if (w10) { avgY += y10; cnt++; }
                    if (w01) { avgY += y01; cnt++; }
                    if (w11) { avgY += y11; cnt++; }
                    avgY /= cnt;

                    float x0 = gx * 4.0f;
                    float z0 = gz * 4.0f;
                    Vector3 v00 = new Vector3(x0, w00 ? y00 : avgY, z0);
                    Vector3 v10 = new Vector3(x0 + cellMeters, w10 ? y10 : avgY, z0);
                    Vector3 v01 = new Vector3(x0, w01 ? y01 : avgY, z0 + cellMeters);
                    Vector3 v11 = new Vector3(x0 + cellMeters, w11 ? y11 : avgY, z0 + cellMeters);

                    st.SetNormal(Vector3.Up);
                    st.SetUV(new Vector2(0.0f, 0.0f)); st.AddVertex(v00);
                    st.SetUV(new Vector2(1.0f, 0.0f)); st.AddVertex(v10);
                    st.SetUV(new Vector2(0.0f, 1.0f)); st.AddVertex(v01);

                    st.SetUV(new Vector2(1.0f, 0.0f)); st.AddVertex(v10);
                    st.SetUV(new Vector2(1.0f, 1.0f)); st.AddVertex(v11);
                    st.SetUV(new Vector2(0.0f, 1.0f)); st.AddVertex(v01);
                }
            }

            if (hasAny)
            {
                _inlandWaterMesh.Mesh = st.Commit();
                _inlandWaterMesh.MaterialOverride = _riverMaterial;
            }
        }
    }
}
