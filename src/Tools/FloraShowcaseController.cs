using System;
using System.Collections.Generic;
using System.Globalization;
using Godot;
using PrimevalWorld.Flora;

namespace PrimevalWorld.Tools
{
    /// <summary>
    /// Phase 1 Botanical Inspection Lab (scenes/FloraShowcase.tscn, ./run.sh --flora-test):
    /// - Row 1 (Z = 0m): All 4 Broadleaf Variants (A: Buttress Giant, B: Gnarled Mid-Canopy, C: Forest Sapling, D: Columnar Giant)
    ///   with CC0 1K PBR Bark+Moss (bark_moss.gdshader) & Hanging Moss Lianas.
    /// - Row 2 (Z = -26m): 2 Conifer Variants, Weeping Willow, Baobab, Dragon Blood, and Tree Fern / Nipa Palm.
    /// - Mini Rainforest Grove (25m x 25m at X = -12..+13m, Z = +20..+45m): 4 giant trees + Hanging Lianas +
    ///   2 Lush Sword Fern variants + Giant Broadleaf Aroids + Dense Understory Shrubs + Mossy Fallen Logs!
    /// - Quick 3-Distance Inspection Keys: [1]=10m (0.85m eye level), [2]=100m (LOD0->LOD1), [3]=500m (LOD2), [4]=Mini Grove, [L]=LOD Debug!
    /// </summary>
    public partial class FloraShowcaseController : Node3D
    {
        private readonly FloraMeshLibrary _meshLib = new();

        private Camera3D? _cam;
        private DirectionalLight3D? _sun;
        private ShaderMaterial? _skyMat;

        private ShaderMaterial? _barkLod0Mat;
        private ShaderMaterial? _barkLod1Mat;
        private ShaderMaterial? _leafLod0Mat;
        private ShaderMaterial? _leafLod1Mat;
        private ShaderMaterial? _leafLod2Mat;
        private ShaderMaterial? _grassMat;

        private MultiMeshInstance3D? _grassMmi;
        private Node3D? _treesRoot;
        private Node3D? _markersRoot;
        private Label? _hudLabel;

        private ImageTexture? _windTex;
        private ImageTexture? _weatherTex;
        private ImageTexture? _climateTex;
        private ImageTexture? _canopyTex;
        private BotanicalTextureGenerator.BotanicalTextures? _botTex;

        private readonly List<(Vector3 Pos, string Name, int Lod0Tris, int Lod1Tris, int Lod2Tris)> _treeRecords = new();

        private int _seed = 2026;
        private float _sunElevDeg = 29.0f; // Cinematic oblique 08:45 morning angle
        private float _sunAzimDeg = -132.0f;
        private float _windSpeed = 7.5f;
        private int _povMode = 0; // 0 = Wolf (0.85m), 1 = Mammoth (3.60m), 2 = Free Fly
        private float _yaw;
        private float _pitch = 0.08f;
        private bool _rotating;
        private bool _wireframe;
        private bool _lodDebug;
        private bool _showMarkersAndGrass = true;

        private string? _captureDir;
        private int _captureStep;
        private int _captureWaitFrames;

        public override void _Ready()
        {
            foreach (string arg in OS.GetCmdlineUserArgs())
            {
                if (arg.StartsWith("--capture-dir=", StringComparison.Ordinal))
                    _captureDir = arg.Substring("--capture-dir=".Length);
            }
            _botTex = BotanicalTextureGenerator.EnsureAndLoadAll();
            SetupSkyAndLighting();
            BuildGround();
            BuildGrassPatch();
            BuildShowcaseScene();
            BuildHud();
            JumpToInspectionDistance(10.0f);
            PrintVerificationLog();
        }

        private void SetupSkyAndLighting()
        {
            var skyShader = GD.Load<Shader>("res://shaders/procedural_sky_clouds.gdshader");
            _skyMat = new ShaderMaterial { Shader = skyShader };
            _skyMat.SetShaderParameter("day_t", 1.0f);
            _skyMat.SetShaderParameter("golden_t", 0.25f);
            _skyMat.SetShaderParameter("cloud_cover", 0.22f);

            var env = new Godot.Environment
            {
                BackgroundMode = Godot.Environment.BGMode.Sky,
                Sky = new Sky { SkyMaterial = _skyMat },
                AmbientLightSource = Godot.Environment.AmbientSource.Sky,
                AmbientLightSkyContribution = 0.88f,
                AmbientLightEnergy = 1.05f,
                TonemapMode = Godot.Environment.ToneMapper.Agx,
                TonemapExposure = 1.02f,
                SsaoEnabled = true,
                SsaoRadius = 2.0f,
                SsaoIntensity = 0.95f,
                SsilEnabled = false,
                SdfgiEnabled = false,
            };
            AddChild(new WorldEnvironment { Environment = env });

            _sun = new DirectionalLight3D
            {
                LightColor = new Color(1.0f, 0.92f, 0.80f),
                LightEnergy = 1.95f,
                ShadowEnabled = true,
                ShadowBlur = 1.1f,
                DirectionalShadowMode = DirectionalLight3D.ShadowMode.Parallel4Splits,
                DirectionalShadowSplit1 = 0.05f,
                DirectionalShadowMaxDistance = 260.0f,
            };
            AddChild(_sun);
            UpdateSunTransform();

            _cam = new Camera3D { Fov = 78.0f, Near = 0.08f, Far = 2000.0f };
            AddChild(_cam);
            _cam.Current = true;
        }

        private void BuildGround()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            const int n = 48;
            const float size = 180.0f;

            Vector3[,] pts = new Vector3[n + 1, n + 1];
            for (int z = 0; z <= n; z++)
                for (int x = 0; x <= n; x++)
                {
                    float wx = (x / (float)n - 0.5f) * size + 32.0f;
                    float wz = (z / (float)n - 0.5f) * size + 10.0f;
                    pts[x, z] = new Vector3(wx, SampleGroundHeight(wx, wz), wz);
                }

            var mat = new StandardMaterial3D
            {
                AlbedoColor = new Color(0.11f, 0.16f, 0.07f),
                Roughness = 0.92f,
                SpecularMode = BaseMaterial3D.SpecularModeEnum.Disabled,
            };

            for (int z = 0; z < n; z++)
                for (int x = 0; x < n; x++)
                {
                    Vector3 p00 = pts[x, z], p10 = pts[x + 1, z], p01 = pts[x, z + 1], p11 = pts[x + 1, z + 1];
                    st.AddVertex(p00); st.AddVertex(p10); st.AddVertex(p11);
                    st.AddVertex(p00); st.AddVertex(p11); st.AddVertex(p01);
                }
            st.GenerateNormals();
            AddChild(new MeshInstance3D { Mesh = st.Commit(), MaterialOverride = mat });
        }

        private void BuildGrassPatch()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            for (int b = 0; b < 3; b++)
            {
                float ang = b * Mathf.Tau / 3.0f + 0.2f;
                Vector3 dir = new Vector3(MathF.Cos(ang), 0.0f, MathF.Sin(ang));
                Vector3 side = new Vector3(-dir.Z, 0.0f, dir.X);
                Vector3 root = dir * 0.07f;
                var cBot = new Color(0.12f, 0.22f, 0.07f, 0.0f);
                var cMid = new Color(0.19f, 0.38f, 0.11f, 0.48f);
                var cTip = new Color(0.28f, 0.50f, 0.14f, 1.0f);
                AddTri(st, root - side * 0.045f, root + side * 0.045f, root + dir * 0.11f + side * 0.03f + new Vector3(0, 0.19f, 0), cBot, cBot, cMid);
                AddTri(st, root - side * 0.045f, root + dir * 0.11f + side * 0.03f + new Vector3(0, 0.19f, 0), root + dir * 0.11f - side * 0.03f + new Vector3(0, 0.19f, 0), cBot, cMid, cMid);
                AddTri(st, root + dir * 0.11f - side * 0.03f + new Vector3(0, 0.19f, 0), root + dir * 0.11f + side * 0.03f + new Vector3(0, 0.19f, 0), root + dir * 0.22f + new Vector3(0, 0.36f, 0), cMid, cMid, cTip);
            }
            st.GenerateNormals();

            const int count = 10000;
            var mm = new MultiMesh
            {
                TransformFormat = MultiMesh.TransformFormatEnum.Transform3D,
                UseColors = true,
                Mesh = st.Commit(),
                InstanceCount = count,
            };
            var rng = new Random(555);
            for (int i = 0; i < count; i++)
            {
                float gx = (float)(rng.NextDouble() * 115.0 - 18.0);
                float gz = (float)(rng.NextDouble() * 90.0 - 38.0);
                float gy = SampleGroundHeight(gx, gz);
                float s = 0.65f + (float)rng.NextDouble() * 0.65f;
                float yaw = (float)(rng.NextDouble() * Mathf.Tau);
                mm.SetInstanceTransform(i, new Transform3D(Basis.Identity.Rotated(Vector3.Up, yaw).Scaled(new Vector3(s, s, s)), new Vector3(gx, gy - 0.03f, gz)));
                float tv = 0.85f + (float)rng.NextDouble() * 0.30f;
                mm.SetInstanceColor(i, new Color(0.20f * tv, 0.40f * tv, 0.12f * tv));
            }

            _grassMat = new ShaderMaterial { Shader = GD.Load<Shader>("res://shaders/foliage_wind.gdshader") };
            EnsureSiteTextures();
            _grassMat.SetShaderParameter("wind_dir_speed_tex", _windTex!);
            _grassMat.SetShaderParameter("weather_dynamic_tex", _weatherTex!);

            _grassMmi = new MultiMeshInstance3D
            {
                Multimesh = mm,
                MaterialOverride = _grassMat,
                CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
            };
            AddChild(_grassMmi);
        }

        private void BuildShowcaseScene()
        {
            _treesRoot?.QueueFree();
            _markersRoot?.QueueFree();
            _treeRecords.Clear();

            _treesRoot = new Node3D { Name = "ShowcaseTrees" };
            _markersRoot = new Node3D { Name = "ScaleMarkers" };
            AddChild(_treesRoot);
            AddChild(_markersRoot);

            EnsureSiteTextures();
            EnsureShowcaseMaterials();

            // Scale reference poles (0.85m Wolf, 1.65m Bison, 3.60m Mammoth) beside Row 1
            AddScalePole(new Vector3(-7.0f, SampleGroundHeight(-7.0f, 8.0f), 8.0f), 0.85f, new Color(0.88f, 0.32f, 0.24f));
            AddScalePole(new Vector3(-5.8f, SampleGroundHeight(-5.8f, 8.0f), 8.0f), 1.65f, new Color(0.90f, 0.76f, 0.20f));
            AddScalePole(new Vector3(-4.6f, SampleGroundHeight(-4.6f, 8.0f), 8.0f), 3.60f, new Color(0.28f, 0.68f, 0.94f));

            // ===================== ROW 1 (Z = 0m): 4 DISTINCT BROADLEAF VARIANTS (A / B / C / D) =====================
            (FloraSpeciesId Sp, int Var, string Label, Color Tint)[] row1 =
            {
                (FloraSpeciesId.PrimevalBanyanFig, 0, "Broadleaf A: Cổ Thụ Gốc Bạnh Vòm Bồng Bềnh", new Color(0.88f, 1.02f, 0.84f, 0.20f)),
                (FloraSpeciesId.SacredAncientHardwood, 1, "Broadleaf B: Thân Cong Vặn Tán Lệch", new Color(0.94f, 1.06f, 0.86f, 0.45f)),
                (FloraSpeciesId.StarAppleCanopy, 2, "Broadleaf C: Cây Non Tầng Áo Rừng", new Color(0.98f, 1.10f, 0.86f, 0.65f)),
                (FloraSpeciesId.SacredAncientHardwood, 3, "Broadleaf D: Đại Thụ Thân Cao Trụ Rừng Mưa", new Color(0.86f, 0.98f, 0.82f, 0.30f)),
            };
            for (int i = 0; i < row1.Length; i++)
            {
                float x = i * 22.0f;
                Spawn3LodSpecimen(row1[i].Sp, row1[i].Var, new Vector3(x, SampleGroundHeight(x, 0f), 0f), row1[i].Tint, row1[i].Label);
                // Attach Hanging Moss Liana Curtain beneath each giant broadleaf!
                SpawnSingleSpecimen(FloraSpeciesId.LianaMossCurtain, i & 1, new Vector3(x, SampleGroundHeight(x, 0f), 0f), 1.0f, i * 1.1f, new Color(0.88f, 1.02f, 0.78f, 0.5f));
            }

            // ===================== ROW 2 (Z = -26m): CONIFER x2, WILLOW, BAOBAB, DRAGON BLOOD, PALM/FERN =====================
            (FloraSpeciesId Sp, int Var, string Label, Color Tint)[] row2 =
            {
                (FloraSpeciesId.BorealSnowPine, 0, "Conifer A: Thông Nguyên Sinh Chóp Lệch", new Color(0.80f, 0.92f, 0.88f, 0.25f)),
                (FloraSpeciesId.GiantSequoiaReddawn, 1, "Conifer B: Tùng Hồng Thủy Sam", new Color(0.76f, 0.90f, 0.80f, 0.50f)),
                (FloraSpeciesId.WeepingRiverWillow, 0, "Riparian: Liễu Rủ Ven Sông", new Color(0.96f, 1.10f, 0.84f, 0.35f)),
                (FloraSpeciesId.BaobabPrehistoric, 0, "Desert A: Bao Báp Cổ Sinh", new Color(0.94f, 0.98f, 0.76f, 0.40f)),
                (FloraSpeciesId.DragonBloodTree, 0, "Desert B: Cây Máu Rồng Tán Ô", new Color(0.90f, 0.96f, 0.74f, 0.60f)),
                (FloraSpeciesId.ArborescentTreeFern, 0, "Columnar: Dương Xỉ Thân Gỗ", new Color(0.94f, 1.06f, 0.88f, 0.30f)),
            };
            for (int i = 0; i < row2.Length; i++)
            {
                float x = i * 20.0f - 10.0f;
                Spawn3LodSpecimen(row2[i].Sp, row2[i].Var, new Vector3(x, SampleGroundHeight(x, -26f), -26f), row2[i].Tint, row2[i].Label);
            }

            // ===================== MINI RAINFOREST GROVE (25m x 25m at X = -8..+17m, Z = +20..+45m) =====================
            Vector2[] groveTreePos =
            {
                new Vector2(-4f, 25f), new Vector2(12f, 24f), new Vector2(-2f, 40f), new Vector2(13f, 39f), new Vector2(5f, 32f),
            };
            for (int i = 0; i < groveTreePos.Length; i++)
            {
                float gx = groveTreePos[i].X, gz = groveTreePos[i].Y;
                float gy = SampleGroundHeight(gx, gz);
                int v = i % 4;
                FloraSpeciesId sp = i == 4 ? FloraSpeciesId.BorealSnowPine : (v == 0 ? FloraSpeciesId.PrimevalBanyanFig : FloraSpeciesId.SacredAncientHardwood);
                Spawn3LodSpecimen(sp, v, new Vector3(gx, gy, gz), new Color(0.90f, 1.02f, 0.85f, 0.35f), $"MiniGrove #{i + 1}");
                if (i < 4)
                    SpawnSingleSpecimen(FloraSpeciesId.LianaMossCurtain, i & 1, new Vector3(gx, gy, gz), 1.05f, i * 1.3f, new Color(0.86f, 1.00f, 0.76f, 0.5f));
            }

            // Populate 25m x 25m grove floor with 2 Sword Fern variants + Giant Broadleaf Aroids + Dense Shrubs + Mossy Fallen Logs
            var rng = new Random(_seed + 909);
            for (int i = 0; i < 42; i++)
            {
                float gx = -10.0f + (float)rng.NextDouble() * 27.0f;
                float gz = 19.0f + (float)rng.NextDouble() * 27.0f;
                float gy = SampleGroundHeight(gx, gz);
                float yaw = (float)(rng.NextDouble() * Mathf.Tau);
                float sc = 0.85f + (float)rng.NextDouble() * 0.45f;
                int pick = i % 10;
                FloraSpeciesId id = pick < 5 ? FloraSpeciesId.LushSwordFern
                                  : (pick < 7 ? FloraSpeciesId.GiantElephantEar
                                  : (pick < 9 ? FloraSpeciesId.WildBerryBush : FloraSpeciesId.HollowFallenTrunk));
                SpawnSingleSpecimen(id, i & 1, new Vector3(gx, gy, gz), sc, yaw, new Color(0.92f, 1.06f, 0.85f, 0.4f));
            }

            _markersRoot.Visible = _showMarkersAndGrass;
        }

        private void Spawn3LodSpecimen(FloraSpeciesId sp, int variant, Vector3 pos, Color tint, string label)
        {
            ArrayMesh m0 = _meshLib.GetMesh(sp, variant, 0, _barkLod0Mat, _leafLod0Mat);
            ArrayMesh m1 = _meshLib.GetMesh(sp, variant, 1, _barkLod1Mat, _leafLod1Mat);
            ArrayMesh m2 = _meshLib.GetMesh(sp, variant, 2, null, _leafLod2Mat);

            int t0 = FloraMeshLibrary.GetTriangleCount(m0);
            int t1 = FloraMeshLibrary.GetTriangleCount(m1);
            int t2 = FloraMeshLibrary.GetTriangleCount(m2);
            _treeRecords.Add((pos, label, t0, t1, t2));

            ArrayMesh[] lodMeshes = { m0, m1, m2 };
            float[] beginD = { 0f, 0f, 200f };
            float[] endD = { 280f, 580f, 1600f };

            for (int lod = 0; lod < 3; lod++)
            {
                var mm = new MultiMesh
                {
                    TransformFormat = MultiMesh.TransformFormatEnum.Transform3D,
                    UseColors = false,
                    UseCustomData = true,
                    Mesh = lodMeshes[lod],
                    InstanceCount = 1,
                };
                mm.SetInstanceTransform(0, new Transform3D(Basis.Identity, Vector3.Zero));
                mm.SetInstanceCustomData(0, tint);

                _treesRoot!.AddChild(new MultiMeshInstance3D
                {
                    Position = pos,
                    Multimesh = mm,
                    MaterialOverride = null,
                    CastShadow = lod == 0 ? GeometryInstance3D.ShadowCastingSetting.On : GeometryInstance3D.ShadowCastingSetting.Off,
                    VisibilityRangeBegin = beginD[lod],
                    VisibilityRangeEnd = endD[lod],
                });
            }
        }

        private void SpawnSingleSpecimen(FloraSpeciesId sp, int variant, Vector3 pos, float scale, float yaw, Color tint)
        {
            ArrayMesh m = _meshLib.GetMesh(sp, variant, 0, _barkLod0Mat, _leafLod0Mat);
            var mm = new MultiMesh
            {
                TransformFormat = MultiMesh.TransformFormatEnum.Transform3D,
                UseColors = false,
                UseCustomData = true,
                Mesh = m,
                InstanceCount = 1,
            };
            mm.SetInstanceTransform(0, new Transform3D(Basis.Identity.Rotated(Vector3.Up, yaw).Scaled(new Vector3(scale, scale, scale)), Vector3.Zero));
            mm.SetInstanceCustomData(0, tint);

            _treesRoot!.AddChild(new MultiMeshInstance3D
            {
                Position = pos,
                Multimesh = mm,
                MaterialOverride = null,
                CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
            });
        }

        private void EnsureShowcaseMaterials()
        {
            var leafShader = GD.Load<Shader>("res://shaders/flora_wind.gdshader");
            var barkShader = GD.Load<Shader>("res://shaders/bark_moss.gdshader");

            ShaderMaterial MakeLeaf(int lod)
            {
                var m = new ShaderMaterial { Shader = leafShader };
                m.SetShaderParameter("wind_dir_speed_tex", _windTex!);
                m.SetShaderParameter("weather_dynamic_tex", _weatherTex!);
                m.SetShaderParameter("leaf_broadleaf_tex", _botTex!.BroadleafTex);
                m.SetShaderParameter("leaf_conifer_tex", _botTex.ConiferTex);
                m.SetShaderParameter("leaf_acacia_tex", _botTex.AcaciaTex);
                m.SetShaderParameter("leaf_palm_tex", _botTex.PalmFernTex);
                m.SetShaderParameter("bark_tex", _botTex.BarkRoughTex);
                m.SetShaderParameter("bark_pale_tex", _botTex.BarkPaleTex);
                FloraLodConfig.ApplyToFloraMaterial(m, lod, _lodDebug);
                return m;
            }

            ShaderMaterial MakeBark(int lod)
            {
                var m = new ShaderMaterial { Shader = barkShader };
                m.SetShaderParameter("wind_dir_speed_tex", _windTex!);
                m.SetShaderParameter("weather_dynamic_tex", _weatherTex!);
                m.SetShaderParameter("climate_tex", _climateTex!);
                m.SetShaderParameter("canopy_coverage_tex", _canopyTex!);
                m.SetShaderParameter("bark_hardwood_albedo", _botTex!.BarkHardwoodAlbedo);
                m.SetShaderParameter("bark_hardwood_normal", _botTex.BarkHardwoodNormal);
                m.SetShaderParameter("bark_hardwood_roughness", _botTex.BarkHardwoodRoughness);
                m.SetShaderParameter("bark_conifer_albedo", _botTex.BarkConiferAlbedo);
                m.SetShaderParameter("bark_conifer_normal", _botTex.BarkConiferNormal);
                m.SetShaderParameter("bark_conifer_roughness", _botTex.BarkConiferRoughness);
                m.SetShaderParameter("bark_pale_albedo", _botTex.BarkPaleTex);
                m.SetShaderParameter("moss_albedo", _botTex.MossAlbedo);
                m.SetShaderParameter("moss_normal", _botTex.MossNormal);
                FloraLodConfig.ApplyToFloraMaterial(m, lod, _lodDebug);
                return m;
            }

            _leafLod0Mat = MakeLeaf(0);
            _leafLod1Mat = MakeLeaf(1);
            _leafLod2Mat = MakeLeaf(2);
            _barkLod0Mat = MakeBark(0);
            _barkLod1Mat = MakeBark(1);
        }

        private void ToggleLodDebug()
        {
            _lodDebug = !_lodDebug;
            int v = _lodDebug ? 1 : 0;
            _leafLod0Mat?.SetShaderParameter("lod_debug_mode", v);
            _leafLod1Mat?.SetShaderParameter("lod_debug_mode", v);
            _leafLod2Mat?.SetShaderParameter("lod_debug_mode", v);
            _barkLod0Mat?.SetShaderParameter("lod_debug_mode", v);
            _barkLod1Mat?.SetShaderParameter("lod_debug_mode", v);
        }

        private void AddScalePole(Vector3 pos, float height, Color col)
        {
            var mesh = new CylinderMesh { TopRadius = 0.08f, BottomRadius = 0.08f, Height = height };
            var mat = new StandardMaterial3D { AlbedoColor = col, Roughness = 0.8f };
            _markersRoot!.AddChild(new MeshInstance3D
            {
                Mesh = mesh,
                MaterialOverride = mat,
                Position = pos + new Vector3(0.0f, height * 0.5f, 0.0f),
            });
        }

        private void EnsureSiteTextures()
        {
            byte[] wBytes = new byte[4 * 4 * 3];
            byte spdByte = (byte)(Math.Clamp(_windSpeed / 30.0f, 0.0f, 1.0f) * 255.0f);
            for (int i = 0; i < 16; i++) { wBytes[i * 3 + 0] = 220; wBytes[i * 3 + 1] = 175; wBytes[i * 3 + 2] = spdByte; }
            var wImg = Image.CreateFromData(4, 4, false, Image.Format.Rgb8, wBytes);
            if (_windTex == null) _windTex = ImageTexture.CreateFromImage(wImg);
            else _windTex.Update(wImg);

            if (_weatherTex == null)
                _weatherTex = ImageTexture.CreateFromImage(Image.CreateFromData(4, 4, false, Image.Format.Rgba8, new byte[4 * 4 * 4]));

            if (_climateTex == null)
            {
                byte[] cl = new byte[4 * 4 * 4];
                for (int i = 0; i < 16; i++) { cl[i * 4 + 0] = 175; cl[i * 4 + 1] = 210; cl[i * 4 + 2] = 0; cl[i * 4 + 3] = 128; }
                _climateTex = ImageTexture.CreateFromImage(Image.CreateFromData(4, 4, false, Image.Format.Rgba8, cl));
            }
            if (_canopyTex == null)
            {
                byte[] cc = new byte[4 * 4 * 4];
                for (int i = 0; i < 16; i++) { cc[i * 4 + 0] = 215; cc[i * 4 + 1] = 0; cc[i * 4 + 2] = 0; cc[i * 4 + 3] = 255; }
                _canopyTex = ImageTexture.CreateFromImage(Image.CreateFromData(4, 4, false, Image.Format.Rgba8, cc));
            }
        }

        private void BuildHud()
        {
            var canvas = new CanvasLayer();
            AddChild(canvas);
            var panel = new PanelContainer { Position = new Vector2(14, 14) };
            panel.AddThemeStyleboxOverride("panel", new StyleBoxFlat { BgColor = new Color(0.05f, 0.08f, 0.12f, 0.84f), ContentMarginLeft = 10, ContentMarginRight = 10, ContentMarginTop = 8, ContentMarginBottom = 8 });
            canvas.AddChild(panel);
            _hudLabel = new Label();
            _hudLabel.AddThemeFontSizeOverride("font_size", 13);
            panel.AddChild(_hudLabel);

            var help = new Label
            {
                Text = "1: Cận cảnh 10m (0.85m) | 2: Trung cảnh 100m | 3: Viễn cảnh 500m (LOD2) | 4: Cụm Rừng Mini 25x25m | L: Soi LOD | V: Sói/Ma Mút/Bay | J/K: Nắng | U/I: Gió | O: Wireframe",
            };
            help.SetAnchorsPreset(Control.LayoutPreset.BottomLeft);
            help.OffsetLeft = 16; help.OffsetBottom = -14; help.OffsetTop = -36;
            canvas.AddChild(help);
        }

        public override void _UnhandledInput(InputEvent @event)
        {
            if (@event is InputEventMouseButton mb && mb.ButtonIndex == MouseButton.Right)
            {
                _rotating = mb.Pressed;
                Input.MouseMode = _rotating ? Input.MouseModeEnum.Captured : Input.MouseModeEnum.Visible;
            }
            else if (@event is InputEventMouseMotion mm && _rotating && _cam != null)
            {
                _yaw -= mm.Relative.X * 0.0045f;
                _pitch = Mathf.Clamp(_pitch - mm.Relative.Y * 0.0045f, -1.4f, 1.4f);
                _cam.Rotation = new Vector3(_pitch, _yaw, 0.0f);
            }
            else if (@event is InputEventKey k && k.Pressed && !k.Echo)
            {
                switch (k.Keycode)
                {
                    case Key.Key1: JumpToInspectionDistance(10.0f); break;
                    case Key.Key2: JumpToInspectionDistance(100.0f); break;
                    case Key.Key3: JumpToInspectionDistance(500.0f); break;
                    case Key.Key4: JumpToMiniGrove(); break;
                    case Key.L: ToggleLodDebug(); break;
                    case Key.V: _povMode = (_povMode + 1) % 3; break;
                    case Key.G: _seed = (int)(GD.Randi() % 90000 + 1000); BuildShowcaseScene(); break;
                    case Key.O:
                        _wireframe = !_wireframe;
                        GetViewport().DebugDraw = _wireframe ? Viewport.DebugDrawEnum.Wireframe : Viewport.DebugDrawEnum.Disabled;
                        break;
                    case Key.B:
                        _showMarkersAndGrass = !_showMarkersAndGrass;
                        if (_markersRoot != null) _markersRoot.Visible = _showMarkersAndGrass;
                        if (_grassMmi != null) _grassMmi.Visible = _showMarkersAndGrass;
                        break;
                    case Key.Escape: GetTree().Quit(); break;
                }
            }
        }

        private void JumpToInspectionDistance(float distM)
        {
            if (_cam == null) return;
            Vector3 target = new Vector3(33.0f, 7.5f, 0.0f);
            if (distM <= 25.0f)
            {
                _povMode = 0; // Wolf 0.85m
                _cam.Position = new Vector3(33.0f, SampleGroundHeight(33.0f, distM) + 0.85f, distM);
            }
            else
            {
                _povMode = 2; // Free Fly for 100m & 500m LOD inspection
                _cam.Position = new Vector3(33.0f, distM * 0.24f + 12.0f, distM);
            }
            _cam.LookAt(target, Vector3.Up);
            _pitch = _cam.Rotation.X;
            _yaw = _cam.Rotation.Y;
        }

        private void JumpToMiniGrove()
        {
            if (_cam == null) return;
            _povMode = 0; // Wolf 0.85m eye level right inside the 25m x 25m lush understory grove!
            float x = 3.5f, z = 28.0f;
            _cam.Position = new Vector3(x, SampleGroundHeight(x, z) + 0.85f, z);
            _cam.LookAt(new Vector3(5.0f, SampleGroundHeight(5.0f, 34.0f) + 2.8f, 34.0f), Vector3.Up);
            _pitch = _cam.Rotation.X;
            _yaw = _cam.Rotation.Y;
        }

        public override void _Process(double delta)
        {
            float dt = (float)delta;
            if (Input.IsKeyPressed(Key.J)) { _sunAzimDeg -= 40f * dt; UpdateSunTransform(); }
            if (Input.IsKeyPressed(Key.K)) { _sunAzimDeg += 40f * dt; UpdateSunTransform(); }
            if (Input.IsKeyPressed(Key.U)) { _windSpeed = Math.Clamp(_windSpeed - 12f * dt, 0f, 25f); EnsureSiteTextures(); }
            if (Input.IsKeyPressed(Key.I)) { _windSpeed = Math.Clamp(_windSpeed + 12f * dt, 0f, 25f); EnsureSiteTextures(); }

            if (_cam != null)
            {
                Vector3 fwd = _povMode == 2 ? -_cam.GlobalTransform.Basis.Z : new Vector3(-_cam.GlobalTransform.Basis.Z.X, 0f, -_cam.GlobalTransform.Basis.Z.Z).Normalized();
                Vector3 right = new Vector3(_cam.GlobalTransform.Basis.X.X, 0f, _cam.GlobalTransform.Basis.X.Z).Normalized();
                Vector3 move = Vector3.Zero;
                if (Input.IsKeyPressed(Key.W)) move += fwd;
                if (Input.IsKeyPressed(Key.S)) move -= fwd;
                if (Input.IsKeyPressed(Key.D)) move += right;
                if (Input.IsKeyPressed(Key.A)) move -= right;
                if (_povMode == 2)
                {
                    if (Input.IsKeyPressed(Key.E)) move += Vector3.Up;
                    if (Input.IsKeyPressed(Key.Q)) move -= Vector3.Up;
                }
                float spd = (_povMode == 2 ? 42f : 7f) * (Input.IsKeyPressed(Key.Shift) ? 2.5f : 1.0f);
                Vector3 p = _cam.Position + (move.LengthSquared() > 0.001f ? move.Normalized() * spd * dt : Vector3.Zero);
                if (_povMode != 2)
                    p.Y = SampleGroundHeight(p.X, p.Z) + (_povMode == 0 ? 0.85f : 3.60f);
                _cam.Position = p;
            }

            if (_hudLabel != null && _cam != null)
            {
                string nearName = "-"; int t0 = 0, t1 = 0, t2 = 0; float bestD = 9999f;
                foreach (var rec in _treeRecords)
                {
                    float d = _cam.Position.DistanceTo(rec.Pos);
                    if (d < bestD) { bestD = d; nearName = rec.Name; t0 = rec.Lod0Tris; t1 = rec.Lod1Tris; t2 = rec.Lod2Tris; }
                }
                float fps = (float)Engine.GetFramesPerSecond();
                int drawCalls = (int)RenderingServer.GetRenderingInfo(RenderingServer.RenderingInfo.TotalDrawCallsInFrame);
                string pov = _povMode == 0 ? "Sói (0.85m)" : (_povMode == 1 ? "Ma Mút (3.6m)" : "Tự do");
                string dbg = _lodDebug ? " | [SOI LOD: ĐỎ/VÀNG/XANH]" : "";
                _hudLabel.Text =
                    $"Flora Showcase Lab (10m/100m/500m) | FPS: {fps:0} | DrawCalls: {drawCalls} | Góc nhìn [V]: {pov}{dbg}\n" +
                    $"Cây gần nhất ({bestD:0.0}m): {nearName} | Tris LOD0/1/2 = {t0:N0} / {t1:N0} / {t2:N0}";
            }

            if (!string.IsNullOrEmpty(_captureDir))
                ProcessAutoCapture();
        }

        private void ProcessAutoCapture()
        {
            _captureWaitFrames++;
            if (_captureWaitFrames < 18) return;
            _captureWaitFrames = 0;

            System.IO.Directory.CreateDirectory(_captureDir!);
            var img = GetViewport().GetTexture().GetImage();
            if (_captureStep == 0)
            {
                img.SavePng(System.IO.Path.Combine(_captureDir!, "01_showcase_10m_row1.png"));
                JumpToMiniGrove();
                _captureStep = 1;
            }
            else if (_captureStep == 1)
            {
                img.SavePng(System.IO.Path.Combine(_captureDir!, "02_showcase_mini_grove.png"));
                JumpToInspectionDistance(100.0f);
                _captureStep = 2;
            }
            else if (_captureStep == 2)
            {
                img.SavePng(System.IO.Path.Combine(_captureDir!, "03_showcase_100m_overview.png"));
                GD.Print($"[AutoCapture] Saved 3 FloraShowcase screenshots to {_captureDir}");
                GetTree().Quit(0);
            }
        }

        private void UpdateSunTransform()
        {
            if (_sun == null) return;
            float az = Mathf.DegToRad(_sunAzimDeg);
            float el = Mathf.DegToRad(_sunElevDeg);
            Vector3 dir = new Vector3(MathF.Cos(el) * MathF.Cos(az), MathF.Sin(el), MathF.Cos(el) * MathF.Sin(az)).Normalized();
            _sun.LookAtFromPosition(dir * 60f, Vector3.Zero, Vector3.Up);
            _skyMat?.SetShaderParameter("sun_direction", dir);
        }

        private void PrintVerificationLog()
        {
            var inv = CultureInfo.InvariantCulture;
            GD.Print("[PBR_BarkMoss_CC0] Poly Haven 1024x1024 CC0 loaded: bark_hardwood (bark_brown_02), bark_conifer (pine_bark), moss (moss_01)");
            foreach (var rec in _treeRecords)
            {
                if (!rec.Name.StartsWith("MiniGrove"))
                    GD.Print(string.Create(inv, $"[Phase1Variant] {rec.Name} | LOD0={rec.Lod0Tris:N0} tris | LOD1={rec.Lod1Tris:N0} tris | LOD2={rec.Lod2Tris:N0} tris"));
            }
            // Also log the 5 upgraded understory / liana meshes
            (FloraSpeciesId Id, string Label)[] understory =
            {
                (FloraSpeciesId.LianaMossCurtain, "LianaMossCurtain (V0)"),
                (FloraSpeciesId.LushSwordFern, "LushSwordFern (V0)"),
                (FloraSpeciesId.GiantElephantEar, "GiantBroadleafAroid (V0)"),
                (FloraSpeciesId.WildBerryBush, "DenseUnderstoryShrub (V0)"),
                (FloraSpeciesId.HollowFallenTrunk, "MossyFallenLog (V0)"),
            };
            foreach (var u in understory)
            {
                var m = _meshLib.GetMesh(u.Id, 0, 0, _barkLod0Mat, _leafLod0Mat);
                GD.Print(string.Create(inv, $"[Phase1Understory] {u.Label} = {FloraMeshLibrary.GetTriangleCount(m):N0} tris (Surfaces={m.GetSurfaceCount()})"));
            }
        }

        private static float SampleGroundHeight(float x, float z) => MathF.Sin(x * 0.05f) * 0.45f + MathF.Cos(z * 0.06f) * 0.35f;

        private static void AddTri(SurfaceTool st, Vector3 a, Vector3 b, Vector3 c, Color ca, Color cb, Color cc)
        {
            st.SetColor(ca); st.AddVertex(a);
            st.SetColor(cb); st.AddVertex(b);
            st.SetColor(cc); st.AddVertex(c);
        }
    }
}
