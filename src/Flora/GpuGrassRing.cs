using System;
using Godot;
using PrimevalWorld.Core;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Flora
{
    /// <summary>
    /// Dual-Layer Close-Up GPU Ground Foliage Ring snapped around the Camera:
    /// 1) 30,000-clump GPU Meadow/Steppe Grass Ring (radius 70m, tapered blades)
    /// 2) 9,000-clump GPU Rainforest Understory Fern Carpet (radius 56m, real leaf_palm_fern.png Alpha Cutout)
    /// Zero per-frame CPU terrain queries, scale=1.0 on MODEL_MATRIX, exact HeightTex match (Err=0.000m).
    /// </summary>
    public partial class GpuGrassRing : MultiMeshInstance3D
    {
        private const int GrassClumpCount = 30000;
        private const float GrassRadiusM = 70.0f;
        private const int FernClumpCount = 9000;
        private const float FernRadiusM = 56.0f;
        private const float SnapStepM = 2.0f;

        private ShaderMaterial? _grassMat;
        private ShaderMaterial? _fernMat;
        private MultiMeshInstance3D? _fernRing;
        private ImageTexture? _heightTex;

        public override void _Ready()
        {
            BuildGrassRingMesh();
            BuildFernCarpetRing();
        }

        private void BuildGrassRingMesh()
        {
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

            var mm = new MultiMesh
            {
                TransformFormat = MultiMesh.TransformFormatEnum.Transform3D,
                UseColors = false,
                Mesh = st.Commit(),
                InstanceCount = GrassClumpCount,
            };

            var rng = new Random(777);
            for (int i = 0; i < GrassClumpCount; i++)
            {
                float r = MathF.Pow((float)rng.NextDouble(), 0.56f) * GrassRadiusM;
                float a = (float)(rng.NextDouble() * Mathf.Tau);
                float lx = MathF.Cos(a) * r;
                float lz = MathF.Sin(a) * r;
                float yaw = (float)(rng.NextDouble() * Mathf.Tau);
                // Keep scale = 1.0 on MODEL_MATRIX so ground_h offset is never scaled!
                mm.SetInstanceTransform(i, new Transform3D(Basis.Identity.Rotated(Vector3.Up, yaw), new Vector3(lx, 0.0f, lz)));
            }

            Multimesh = mm;
            CustomAabb = new Aabb(new Vector3(-120f, -200f, -120f), new Vector3(240f, 1200f, 240f));
            CastShadow = ShadowCastingSetting.Off;

            _grassMat = new ShaderMaterial { Shader = GD.Load<Shader>("res://shaders/gpu_grass.gdshader") };
            MaterialOverride = _grassMat;
        }

        private void BuildFernCarpetRing()
        {
            // 1 fern clump = 2 gently arched crossed rosette planes using real leaf_palm_fern.png!
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            float r = 1.05f;
            float hMid = 0.62f;
            float hEdge = 0.24f;
            var cCenter = new Color(1f, 1f, 1f, 0.25f);
            var cEdge = new Color(1f, 1f, 1f, 0.95f);

            // Slightly domed horizontal rosette + 2 angled vertical fronds for 3D volume from 0.85m eye level!
            AddQuadUv(st, new Vector3(-r, hEdge, -r), new Vector3(r, hEdge, -r), new Vector3(r, hEdge, r), new Vector3(-r, hEdge, r),
                cEdge, cEdge, new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1));
            AddQuadUv(st, new Vector3(-r * 0.85f, 0.05f, 0f), new Vector3(r * 0.85f, 0.05f, 0f), new Vector3(r * 0.95f, hMid * 1.45f, 0.15f), new Vector3(-r * 0.95f, hMid * 1.45f, -0.15f),
                cCenter, cEdge, new Vector2(0, 1), new Vector2(1, 1), new Vector2(1, 0), new Vector2(0, 0));
            AddQuadUv(st, new Vector3(0f, 0.05f, -r * 0.85f), new Vector3(0f, 0.05f, r * 0.85f), new Vector3(0.15f, hMid * 1.45f, r * 0.95f), new Vector3(-0.15f, hMid * 1.45f, -r * 0.95f),
                cCenter, cEdge, new Vector2(0, 1), new Vector2(1, 1), new Vector2(1, 0), new Vector2(0, 0));

            var mm = new MultiMesh
            {
                TransformFormat = MultiMesh.TransformFormatEnum.Transform3D,
                UseColors = false,
                Mesh = st.Commit(),
                InstanceCount = FernClumpCount,
            };

            var rng = new Random(909);
            for (int i = 0; i < FernClumpCount; i++)
            {
                float rad = MathF.Pow((float)rng.NextDouble(), 0.55f) * FernRadiusM;
                float a = (float)(rng.NextDouble() * Mathf.Tau);
                float lx = MathF.Cos(a) * rad;
                float lz = MathF.Sin(a) * rad;
                float yaw = (float)(rng.NextDouble() * Mathf.Tau);
                mm.SetInstanceTransform(i, new Transform3D(Basis.Identity.Rotated(Vector3.Up, yaw), new Vector3(lx, 0.0f, lz)));
            }

            _fernMat = new ShaderMaterial { Shader = GD.Load<Shader>("res://shaders/gpu_fern_carpet.gdshader") };
            var bot = BotanicalTextureGenerator.EnsureAndLoadAll();
            _fernMat.SetShaderParameter("fern_tex", bot.PalmFernTex);

            _fernRing = new MultiMeshInstance3D
            {
                Name = "GpuFernCarpet",
                Multimesh = mm,
                MaterialOverride = _fernMat,
                CustomAabb = new Aabb(new Vector3(-100f, -200f, -100f), new Vector3(200f, 1200f, 200f)),
                CastShadow = ShadowCastingSetting.Off,
            };
            AddChild(_fernRing);
        }

        public void BindWorldTextures(
            ErosionPhysics erosion,
            ImageTexture soilA,
            ImageTexture soilB,
            ImageTexture climateTex,
            ImageTexture canopyTex,
            ImageTexture windTex)
        {
            int w = WorldPhysicsConfig.VertW;
            int h = WorldPhysicsConfig.VertH;
            byte[] bytes = new byte[w * h * 4];
            Buffer.BlockCopy(erosion.HeightMap, 0, bytes, 0, bytes.Length);
            var hImg = Image.CreateFromData(w, h, false, Image.Format.Rf, bytes);
            _heightTex = ImageTexture.CreateFromImage(hImg);

            void BindTo(ShaderMaterial? mat)
            {
                if (mat == null) return;
                mat.SetShaderParameter("height_tex", _heightTex);
                mat.SetShaderParameter("soil_tex_a", soilA);
                mat.SetShaderParameter("soil_tex_b", soilB);
                mat.SetShaderParameter("climate_tex", climateTex);
                mat.SetShaderParameter("canopy_coverage_tex", canopyTex);
                mat.SetShaderParameter("wind_dir_speed_tex", windTex);
            }
            BindTo(_grassMat);
            BindTo(_fernMat);

            float testX = 6350.0f, testZ = 3420.0f;
            float cpuH = erosion.SampleHeight(testX, testZ);
            float u = Math.Clamp(testX / WorldPhysicsConfig.WorldWidth, 0f, 1f) * (w - 1);
            float v = Math.Clamp(testZ / WorldPhysicsConfig.WorldDepth, 0f, 1f) * (h - 1);
            int x0 = Math.Clamp((int)u, 0, w - 2), z0 = Math.Clamp((int)v, 0, h - 2);
            float tx = u - x0, tz = v - z0;
            float g00 = hImg.GetPixel(x0, z0).R, g10 = hImg.GetPixel(x0 + 1, z0).R;
            float g01 = hImg.GetPixel(x0, z0 + 1).R, g11 = hImg.GetPixel(x0 + 1, z0 + 1).R;
            float gpuH = (g00 * (1 - tx) + g10 * tx) * (1 - tz) + (g01 * (1 - tx) + g11 * tx) * tz;
            GD.Print($"[GpuGrassVerify] Sample({testX:0},{testZ:0}): CPU={cpuH:0.000}m | HeightTex={gpuH:0.000}m | Err={MathF.Abs(cpuH - gpuH):0.0000}m | RingY=0.0m | Ferns={FernClumpCount:N0}");
        }

        public void UpdateDynamicState(Vector3 cameraPos, ImageTexture weatherTex, float seasonPhase, float windGust)
        {
            float sx = MathF.Floor(cameraPos.X / SnapStepM) * SnapStepM;
            float sz = MathF.Floor(cameraPos.Z / SnapStepM) * SnapStepM;
            Position = new Vector3(sx, 0.0f, sz);

            if (_grassMat != null)
            {
                _grassMat.SetShaderParameter("weather_dynamic_tex", weatherTex);
                _grassMat.SetShaderParameter("season_phase", seasonPhase);
                _grassMat.SetShaderParameter("global_wind_gust", windGust);
            }
            if (_fernMat != null)
            {
                _fernMat.SetShaderParameter("weather_dynamic_tex", weatherTex);
                _fernMat.SetShaderParameter("global_wind_gust", windGust);
            }
        }

        private static void AddTri(SurfaceTool st, Vector3 a, Vector3 b, Vector3 c, Color ca, Color cb, Color cc)
        {
            st.SetColor(ca); st.AddVertex(a);
            st.SetColor(cb); st.AddVertex(b);
            st.SetColor(cc); st.AddVertex(c);
        }

        private static void AddQuadUv(SurfaceTool st, Vector3 p0, Vector3 p1, Vector3 p2, Vector3 p3, Color c0, Color c1,
            Vector2 uv0, Vector2 uv1, Vector2 uv2, Vector2 uv3)
        {
            void Emit(Vector3 p, Color c, Vector2 uv) { st.SetNormal(Vector3.Up); st.SetColor(c); st.SetUV(uv); st.AddVertex(p); }
            Emit(p0, c0, uv0); Emit(p1, c0, uv1); Emit(p2, c1, uv2);
            Emit(p0, c0, uv0); Emit(p2, c1, uv2); Emit(p3, c1, uv3);
        }
    }
}
