using System;
using Godot;
using PrimevalWorld.Core;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Flora
{
    /// <summary>
    /// Stage 3 Close-Up Overhaul: 30,000-clump GPU Grass Ring (radius 70m) snapped around the Camera.
    /// Zero per-frame CPU terrain queries: Vertex Shader samples HeightTex, SoilTexA/B, ClimateTex,
    /// CanopyTex & WeatherDynamicTex directly to place, size, color, wind-wave and fade grass smoothly.
    /// </summary>
    public partial class GpuGrassRing : MultiMeshInstance3D
    {
        private const int ClumpCount = 30000;
        private const float RadiusM = 70.0f;
        private const float SnapStepM = 2.0f;

        private ShaderMaterial? _grassMat;
        private ImageTexture? _heightTex;

        public override void _Ready()
        {
            BuildGrassRingMesh();
        }

        private void BuildGrassRingMesh()
        {
            // Build 1 grass clump mesh = 3 tapered, slightly curved blades (no boxes!)
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            for (int b = 0; b < 3; b++)
            {
                float ang = b * Mathf.Tau / 3.0f + 0.25f;
                Vector3 dir = new Vector3(MathF.Cos(ang), 0.0f, MathF.Sin(ang));
                Vector3 side = new Vector3(-dir.Z, 0.0f, dir.X);
                Vector3 root = dir * 0.08f;

                Vector3 bL = root - side * 0.07f;
                Vector3 bR = root + side * 0.07f;
                Vector3 mL = root + dir * 0.16f - side * 0.04f + new Vector3(0.0f, 0.52f, 0.0f);
                Vector3 mR = root + dir * 0.16f + side * 0.04f + new Vector3(0.0f, 0.52f, 0.0f);
                Vector3 tip = root + dir * 0.36f + new Vector3(0.0f, 1.0f, 0.0f);

                var cBot = new Color(0.55f, 0.62f, 0.45f, 0.0f);
                var cMid = new Color(0.82f, 0.88f, 0.72f, 0.48f);
                var cTip = new Color(1.0f, 1.0f, 0.92f, 1.0f);

                st.SetNormal(Vector3.Up);
                AddTri(st, bL, bR, mR, cBot, cBot, cMid);
                AddTri(st, bL, mR, mL, cBot, cMid, cMid);
                AddTri(st, mL, mR, tip, cMid, cMid, cTip);
            }

            var mesh = st.Commit();
            var mm = new MultiMesh
            {
                TransformFormat = MultiMesh.TransformFormatEnum.Transform3D,
                UseColors = false,
                Mesh = mesh,
                InstanceCount = ClumpCount,
            };

            var rng = new Random(777);
            for (int i = 0; i < ClumpCount; i++)
            {
                // Uniform disk distribution with slight center bias for dense foreground
                float r = MathF.Pow((float)rng.NextDouble(), 0.56f) * RadiusM;
                float a = (float)(rng.NextDouble() * Mathf.Tau);
                float lx = MathF.Cos(a) * r;
                float lz = MathF.Sin(a) * r;
                float yaw = (float)(rng.NextDouble() * Mathf.Tau);
                float s = 0.80f + (float)rng.NextDouble() * 0.55f;

                var xform = new Transform3D(Basis.Identity.Rotated(Vector3.Up, yaw).Scaled(new Vector3(s, s, s)), new Vector3(lx, 0.0f, lz));
                mm.SetInstanceTransform(i, xform);
            }

            Multimesh = mm;
            CustomAabb = new Aabb(new Vector3(-120f, -200f, -120f), new Vector3(240f, 1200f, 240f));
            CastShadow = ShadowCastingSetting.Off;

            var shader = GD.Load<Shader>("res://shaders/gpu_grass.gdshader");
            _grassMat = new ShaderMaterial { Shader = shader };
            MaterialOverride = _grassMat;
        }

        public void BindWorldTextures(
            ErosionPhysics erosion,
            ImageTexture soilA,
            ImageTexture soilB,
            ImageTexture climateTex,
            ImageTexture canopyTex,
            ImageTexture windTex)
        {
            // Export exact float heightmap (RF) for seamless grass placement at 0.85m eye level
            int w = WorldPhysicsConfig.VertW;
            int h = WorldPhysicsConfig.VertH;
            byte[] bytes = new byte[w * h * 4];
            Buffer.BlockCopy(erosion.HeightMap, 0, bytes, 0, bytes.Length);
            var hImg = Image.CreateFromData(w, h, false, Image.Format.Rf, bytes);
            _heightTex = ImageTexture.CreateFromImage(hImg);

            if (_grassMat != null)
            {
                _grassMat.SetShaderParameter("height_tex", _heightTex);
                _grassMat.SetShaderParameter("soil_tex_a", soilA);
                _grassMat.SetShaderParameter("soil_tex_b", soilB);
                _grassMat.SetShaderParameter("climate_tex", climateTex);
                _grassMat.SetShaderParameter("canopy_coverage_tex", canopyTex);
                _grassMat.SetShaderParameter("wind_dir_speed_tex", windTex);
            }
        }

        public void UpdateDynamicState(Vector3 cameraPos, ImageTexture weatherTex, float seasonPhase, float windGust)
        {
            // Snap ring origin to discrete 2m grid steps so blades never swim across terrain
            float sx = MathF.Floor(cameraPos.X / SnapStepM) * SnapStepM;
            float sz = MathF.Floor(cameraPos.Z / SnapStepM) * SnapStepM;
            Position = new Vector3(sx, 0.0f, sz);

            if (_grassMat != null)
            {
                _grassMat.SetShaderParameter("weather_dynamic_tex", weatherTex);
                _grassMat.SetShaderParameter("season_phase", seasonPhase);
                _grassMat.SetShaderParameter("global_wind_gust", windGust);
            }
        }

        private static void AddTri(SurfaceTool st, Vector3 a, Vector3 b, Vector3 c, Color ca, Color cb, Color cc)
        {
            st.SetColor(ca); st.AddVertex(a);
            st.SetColor(cb); st.AddVertex(b);
            st.SetColor(cc); st.AddVertex(c);
        }
    }
}
