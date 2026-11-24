using System;
using Godot;
using PrimevalWorld.Core;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Terrain
{
    /// <summary>
    /// Builds the 48km x 48km Horizon Ocean Plane plus full-resolution (9.375m) Inland Rivers, Lakes & Wetland Pools.
    /// Encodes WaterVelocity (R), WaterDepth (G), WetlandMurkFactor (B), and ShorelineFeatherAlpha (A)
    /// to eliminate rectangular grid steps and shallow-water Z-fighting.
    /// </summary>
    public partial class WaterSurface : Node3D
    {
        private MeshInstance3D? _oceanMesh;
        private MeshInstance3D? _inlandWaterMesh;
        private ShaderMaterial? _oceanMaterial;
        private ShaderMaterial? _riverMaterial;

        public void BuildWater(HydrologySolver hydrology, ErosionPhysics? erosion = null)
        {
            if (_oceanMaterial == null)
            {
                var waterShader = GD.Load<Shader>("res://shaders/water_river_ocean.gdshader");
                _oceanMaterial = new ShaderMaterial { Shader = waterShader };
                _oceanMaterial.SetShaderParameter("flow_speed", new Vector2(0.02f, 0.015f));
                _oceanMaterial.SetShaderParameter("shallow_color", new Color(0.10f, 0.68f, 0.72f, 0.76f));
                _oceanMaterial.SetShaderParameter("deep_color", new Color(0.03f, 0.16f, 0.30f, 0.96f));

                _riverMaterial = new ShaderMaterial { Shader = waterShader };
                _riverMaterial.SetShaderParameter("flow_speed", new Vector2(0.05f, 0.26f));
                _riverMaterial.SetShaderParameter("shallow_color", new Color(0.13f, 0.29f, 0.22f, 0.78f));
                _riverMaterial.SetShaderParameter("deep_color", new Color(0.04f, 0.12f, 0.14f, 0.95f));
            }

            BuildHorizonOceanPlane();
            BuildInlandWaterMesh(hydrology, erosion);
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
                SubdivideWidth = 160,
                SubdivideDepth = 160,
            };
            _oceanMesh.Mesh = plane;
            _oceanMesh.MaterialOverride = _oceanMaterial;
            _oceanMesh.Position = new Vector3(
                WorldPhysicsConfig.WorldWidth * 0.5f,
                WorldPhysicsConfig.SeaLevel,
                WorldPhysicsConfig.WorldDepth * 0.5f
            );
        }

        private void BuildInlandWaterMesh(HydrologySolver hydrology, ErosionPhysics? erosion)
        {
            _inlandWaterMesh?.QueueFree();
            _inlandWaterMesh = new MeshInstance3D
            {
                Name = "InlandRiversAndLakes",
                CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
            };
            AddChild(_inlandWaterMesh);

            const float cellMeters = WorldPhysicsConfig.CellSize; // Full 9.375m resolution (no 18.75m blocky slabs!)
            int w = WorldPhysicsConfig.VertW;
            int h = WorldPhysicsConfig.VertH;
            float[]? heightMap = erosion?.HeightMap;

            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            bool hasAny = false;
            for (int gz = 0; gz < h - 1; gz++)
            {
                float z0 = gz * cellMeters;
                float z1 = z0 + cellMeters;
                for (int gx = 0; gx < w - 1; gx++)
                {
                    int i00 = gz * w + gx;
                    int i10 = i00 + 1;
                    int i01 = i00 + w;
                    int i11 = i01 + 1;

                    bool w00 = hydrology.HasInlandWater[i00] && hydrology.InlandWaterY[i00] > WorldPhysicsConfig.SeaLevel + 0.12f;
                    bool w10 = hydrology.HasInlandWater[i10] && hydrology.InlandWaterY[i10] > WorldPhysicsConfig.SeaLevel + 0.12f;
                    bool w01 = hydrology.HasInlandWater[i01] && hydrology.InlandWaterY[i01] > WorldPhysicsConfig.SeaLevel + 0.12f;
                    bool w11 = hydrology.HasInlandWater[i11] && hydrology.InlandWaterY[i11] > WorldPhysicsConfig.SeaLevel + 0.12f;
                    if (!w00 && !w10 && !w01 && !w11) continue;

                    float avgY = 0.0f;
                    int cnt = 0;
                    if (w00) { avgY += hydrology.InlandWaterY[i00]; cnt++; }
                    if (w10) { avgY += hydrology.InlandWaterY[i10]; cnt++; }
                    if (w01) { avgY += hydrology.InlandWaterY[i01]; cnt++; }
                    if (w11) { avgY += hydrology.InlandWaterY[i11]; cnt++; }
                    avgY /= cnt;

                    // Skip isolated 1-corner coastal cliff cells where a dry corner plunges below sea level
                    // (prevents hanging white water triangles jutting out of steep coastal headlands!)
                    if (heightMap != null && cnt <= 2)
                    {
                        float minTerrain = MathF.Min(MathF.Min(heightMap[i00], heightMap[i10]), MathF.Min(heightMap[i01], heightMap[i11]));
                        if (minTerrain < WorldPhysicsConfig.SeaLevel - 0.5f && avgY > WorldPhysicsConfig.SeaLevel + 1.5f)
                            continue;
                    }

                    float x0 = gx * cellMeters;
                    float x1 = x0 + cellMeters;

                    float DryY(int idx) => heightMap != null
                        ? MathF.Min(avgY - 0.22f, heightMap[idx] - 0.35f)
                        : avgY - 0.22f;

                    // Dry perimeter vertices tuck strictly below the bank/terrain with shoreAlpha = 0.0
                    Vector3 v00 = new Vector3(x0, w00 ? hydrology.InlandWaterY[i00] : DryY(i00), z0);
                    Vector3 v10 = new Vector3(x1, w10 ? hydrology.InlandWaterY[i10] : DryY(i10), z0);
                    Vector3 v01 = new Vector3(x0, w01 ? hydrology.InlandWaterY[i01] : DryY(i01), z1);
                    Vector3 v11 = new Vector3(x1, w11 ? hydrology.InlandWaterY[i11] : DryY(i11), z1);

                    Color MakeVertColor(int idx, bool wet) => new Color(
                        Math.Clamp(hydrology.WaterVelocityMap[idx] / 5.5f, 0.0f, 1.0f),
                        Math.Clamp(hydrology.WaterDepthMap[idx] / 6.5f, 0.0f, 1.0f),
                        Math.Clamp(hydrology.WetlandWaterFactor[idx], 0.0f, 1.0f),
                        wet ? Math.Clamp(hydrology.WaterDepthMap[idx] / 0.28f, 0.25f, 1.0f) : 0.0f
                    );

                    Color c00 = MakeVertColor(i00, w00);
                    Color c10 = MakeVertColor(i10, w10);
                    Color c01 = MakeVertColor(i01, w01);
                    Color c11 = MakeVertColor(i11, w11);

                    st.SetNormal(Vector3.Up);
                    if (w00 || w10 || w01)
                    {
                        hasAny = true;
                        st.SetColor(c00); st.SetUV(new Vector2(0, 0)); st.AddVertex(v00);
                        st.SetColor(c10); st.SetUV(new Vector2(1, 0)); st.AddVertex(v10);
                        st.SetColor(c01); st.SetUV(new Vector2(0, 1)); st.AddVertex(v01);
                    }
                    if (w10 || w11 || w01)
                    {
                        hasAny = true;
                        st.SetColor(c10); st.SetUV(new Vector2(1, 0)); st.AddVertex(v10);
                        st.SetColor(c11); st.SetUV(new Vector2(1, 1)); st.AddVertex(v11);
                        st.SetColor(c01); st.SetUV(new Vector2(0, 1)); st.AddVertex(v01);
                    }
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
