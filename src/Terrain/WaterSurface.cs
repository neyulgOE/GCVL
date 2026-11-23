using Godot;
using PrimevalWorld.Core;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Terrain
{
    /// <summary>
    /// Builds the 48km x 48km Horizon Ocean Plane plus sloped Inland Rivers & Lakes
    /// carrying WaterVelocity & WaterDepth in vertex Color for dynamic whitewater foam.
    /// </summary>
    public partial class WaterSurface : Node3D
    {
        private MeshInstance3D? _oceanMesh;
        private MeshInstance3D? _inlandWaterMesh;
        private ShaderMaterial? _oceanMaterial;
        private ShaderMaterial? _riverMaterial;

        public void BuildWater(HydrologySolver hydrology)
        {
            if (_oceanMaterial == null)
            {
                var waterShader = GD.Load<Shader>("res://shaders/water_river_ocean.gdshader");
                _oceanMaterial = new ShaderMaterial { Shader = waterShader };
                _oceanMaterial.SetShaderParameter("flow_speed", new Vector2(0.02f, 0.015f));
                _oceanMaterial.SetShaderParameter("shallow_color", new Color(0.10f, 0.70f, 0.74f, 0.78f));
                _oceanMaterial.SetShaderParameter("deep_color", new Color(0.03f, 0.16f, 0.30f, 0.96f));

                _riverMaterial = new ShaderMaterial { Shader = waterShader };
                _riverMaterial.SetShaderParameter("flow_speed", new Vector2(0.05f, 0.28f));
                _riverMaterial.SetShaderParameter("shallow_color", new Color(0.14f, 0.28f, 0.21f, 0.80f));
                _riverMaterial.SetShaderParameter("deep_color", new Color(0.04f, 0.11f, 0.13f, 0.95f));
            }

            BuildHorizonOceanPlane();
            BuildInlandWaterMesh(hydrology);
        }

        public void UpdateWeather(ImageTexture weatherTex, float riverSurgeOffset, float globalWindGust)
        {
            if (_oceanMaterial != null)
            {
                _oceanMaterial.SetShaderParameter("weather_dynamic_tex", weatherTex);
                _oceanMaterial.SetShaderParameter("global_wind_gust", globalWindGust);
            }
            if (_riverMaterial != null)
            {
                _riverMaterial.SetShaderParameter("weather_dynamic_tex", weatherTex);
                _riverMaterial.SetShaderParameter("river_surge_offset", riverSurgeOffset);
                _riverMaterial.SetShaderParameter("global_wind_gust", globalWindGust);
            }
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
                Size = new Vector2(WorldPhysicsConfig.HorizonOceanSize, WorldPhysicsConfig.HorizonOceanSize),
                SubdivideWidth = 128,
                SubdivideDepth = 128,
            };
            _oceanMesh.Mesh = plane;
            _oceanMesh.MaterialOverride = _oceanMaterial;
            _oceanMesh.Position = new Vector3(
                WorldPhysicsConfig.WorldWidth * 0.5f,
                WorldPhysicsConfig.SeaLevel,
                WorldPhysicsConfig.WorldDepth * 0.5f
            );
        }

        private void BuildInlandWaterMesh(HydrologySolver hydrology)
        {
            _inlandWaterMesh?.QueueFree();
            _inlandWaterMesh = new MeshInstance3D
            {
                Name = "InlandRiversAndLakes",
                CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
            };
            AddChild(_inlandWaterMesh);

            const int step = 2; // 18.75m water grid
            const float cellMeters = WorldPhysicsConfig.CellSize * step;
            int w = WorldPhysicsConfig.VertW;
            int h = WorldPhysicsConfig.VertH;

            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            bool hasAny = false;
            for (int gz = 0; gz < h - step; gz += step)
            {
                for (int gx = 0; gx < w - step; gx += step)
                {
                    int i00 = gz * w + gx;
                    int i10 = gz * w + (gx + step);
                    int i01 = (gz + step) * w + gx;
                    int i11 = (gz + step) * w + (gx + step);

                    bool w00 = hydrology.HasInlandWater[i00];
                    bool w10 = hydrology.HasInlandWater[i10];
                    bool w01 = hydrology.HasInlandWater[i01];
                    bool w11 = hydrology.HasInlandWater[i11];
                    if (!w00 && !w10 && !w01 && !w11) continue;
                    hasAny = true;

                    float avgY = 0.0f;
                    int cnt = 0;
                    if (w00) { avgY += hydrology.InlandWaterY[i00]; cnt++; }
                    if (w10) { avgY += hydrology.InlandWaterY[i10]; cnt++; }
                    if (w01) { avgY += hydrology.InlandWaterY[i01]; cnt++; }
                    if (w11) { avgY += hydrology.InlandWaterY[i11]; cnt++; }
                    avgY /= cnt;

                    float x0 = gx * WorldPhysicsConfig.CellSize;
                    float z0 = gz * WorldPhysicsConfig.CellSize;

                    Vector3 v00 = new Vector3(x0, w00 ? hydrology.InlandWaterY[i00] : avgY, z0);
                    Vector3 v10 = new Vector3(x0 + cellMeters, w10 ? hydrology.InlandWaterY[i10] : avgY, z0);
                    Vector3 v01 = new Vector3(x0, w01 ? hydrology.InlandWaterY[i01] : avgY, z0 + cellMeters);
                    Vector3 v11 = new Vector3(x0 + cellMeters, w11 ? hydrology.InlandWaterY[i11] : avgY, z0 + cellMeters);

                    Color c00 = new Color(Mathf.Clamp(hydrology.WaterVelocityMap[i00] / 5.5f, 0, 1), Mathf.Clamp(hydrology.WaterDepthMap[i00] / 6.5f, 0, 1), 0, 1);
                    Color c10 = new Color(Mathf.Clamp(hydrology.WaterVelocityMap[i10] / 5.5f, 0, 1), Mathf.Clamp(hydrology.WaterDepthMap[i10] / 6.5f, 0, 1), 0, 1);
                    Color c01 = new Color(Mathf.Clamp(hydrology.WaterVelocityMap[i01] / 5.5f, 0, 1), Mathf.Clamp(hydrology.WaterDepthMap[i01] / 6.5f, 0, 1), 0, 1);
                    Color c11 = new Color(Mathf.Clamp(hydrology.WaterVelocityMap[i11] / 5.5f, 0, 1), Mathf.Clamp(hydrology.WaterDepthMap[i11] / 6.5f, 0, 1), 0, 1);

                    st.SetNormal(Vector3.Up);
                    st.SetColor(c00); st.SetUV(new Vector2(0, 0)); st.AddVertex(v00);
                    st.SetColor(c10); st.SetUV(new Vector2(1, 0)); st.AddVertex(v10);
                    st.SetColor(c01); st.SetUV(new Vector2(0, 1)); st.AddVertex(v01);

                    st.SetColor(c10); st.SetUV(new Vector2(1, 0)); st.AddVertex(v10);
                    st.SetColor(c11); st.SetUV(new Vector2(1, 1)); st.AddVertex(v11);
                    st.SetColor(c01); st.SetUV(new Vector2(0, 1)); st.AddVertex(v01);
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
