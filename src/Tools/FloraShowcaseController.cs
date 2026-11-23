using System;
using System.Collections.Generic;
using Godot;
using PrimevalWorld.Flora;

namespace PrimevalWorld.Tools
{
    /// <summary>
    /// Dedicated Close-Up Botanical Lab (scenes/FloraShowcase.tscn, ./run.sh --flora-test):
    /// 100m x 100m test ground + 5 representative prehistoric species x 3 ages (Young / Mature / Ancient) = 15 trees
    /// + 3 animal scale poles (0.85m Wolf, 1.65m Bison, 3.60m Mammoth) + live Sun/Wind/Seed/Wireframe controls.
    /// </summary>
    public partial class FloraShowcaseController : Node3D
    {
        private static readonly (FloraSpeciesId Id, string NameVi, Color Tint)[] ShowcaseSpecies =
        {
            (FloraSpeciesId.PrimevalBanyanFig, "Đa Cổ Thụ Nghìn Năm", new Color(0.16f, 0.34f, 0.12f)),
            (FloraSpeciesId.GinkgoAncientGold, "Bạch Quả Cổ Sinh Lá Vàng", new Color(0.86f, 0.66f, 0.14f)),
            (FloraSpeciesId.BorealSnowPine, "Thông Tuyết Phương Bắc", new Color(0.13f, 0.28f, 0.22f)),
            (FloraSpeciesId.DragonBloodTree, "Cây Máu Rồng Tán Ô", new Color(0.24f, 0.35f, 0.15f)),
            (FloraSpeciesId.ArborescentTreeFern, "Dương Xỉ Thân Gỗ & Dừa Nước", new Color(0.20f, 0.45f, 0.14f)),
        };

        private Camera3D? _cam;
        private DirectionalLight3D? _sun;
        private ShaderMaterial? _skyMat;
        private ShaderMaterial? _floraMat;
        private ShaderMaterial? _grassMat;
        private MultiMeshInstance3D? _grassMmi;
        private Node3D? _treesRoot;
        private Node3D? _markersRoot;
        private Label? _hudLabel;

        private ImageTexture? _windTex;
        private ImageTexture? _weatherTex;
        private BotanicalTextureGenerator.BotanicalTextures? _botTex;

        private readonly List<(Vector3 Pos, string Name, int Tris)> _treeRecords = new();

        private int _seed = 2026;
        private float _sunElevDeg = 32.0f;
        private float _sunAzimDeg = -135.0f;
        private float _windSpeed = 7.5f;
        private int _povMode = 0; // 0 = Wolf (0.85m), 1 = Mammoth (3.60m), 2 = Free Fly
        private float _yaw;
        private float _pitch = 0.08f;
        private bool _rotating;
        private bool _wireframe;
        private bool _showMarkersAndGrass = true;

        public override void _Ready()
        {
            _botTex = BotanicalTextureGenerator.EnsureAndLoadAll();
            SetupSkyAndLighting();
            BuildGround();
            BuildGrassPatch();
            BuildShowcaseTrees();
            BuildHud();
            TeleportToRow(0);
            PrintVerificationLog();
        }

        private void SetupSkyAndLighting()
        {
            var skyShader = GD.Load<Shader>("res://shaders/procedural_sky_clouds.gdshader");
            _skyMat = new ShaderMaterial { Shader = skyShader };
            _skyMat.SetShaderParameter("day_t", 1.0f);
            _skyMat.SetShaderParameter("golden_t", 0.15f);
            _skyMat.SetShaderParameter("cloud_cover", 0.25f);

            var env = new Godot.Environment
            {
                BackgroundMode = Godot.Environment.BGMode.Sky,
                Sky = new Sky { SkyMaterial = _skyMat },
                AmbientLightSource = Godot.Environment.AmbientSource.Sky,
                AmbientLightSkyContribution = 0.90f,
                AmbientLightEnergy = 1.25f,
                TonemapMode = Godot.Environment.ToneMapper.Agx,
                TonemapExposure = 1.05f,
                SsaoEnabled = true,
                SsaoRadius = 2.2f,
                SsaoIntensity = 1.05f,
                SsilEnabled = false,
            };
            AddChild(new WorldEnvironment { Environment = env });

            _sun = new DirectionalLight3D
            {
                LightColor = new Color(1.0f, 0.94f, 0.86f),
                LightEnergy = 1.95f,
                ShadowEnabled = true,
                ShadowBlur = 1.1f,
                DirectionalShadowMode = DirectionalLight3D.ShadowMode.Parallel4Splits,
                DirectionalShadowSplit1 = 0.04f,
                DirectionalShadowMaxDistance = 240.0f,
            };
            AddChild(_sun);
            UpdateSunTransform();

            _cam = new Camera3D { Fov = 80.0f, Near = 0.08f, Far = 1200.0f };
            AddChild(_cam);
            _cam.Current = true;
        }

        private void BuildGround()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            const int n = 40;
            const float size = 120.0f;

            Vector3[,] pts = new Vector3[n + 1, n + 1];
            for (int z = 0; z <= n; z++)
                for (int x = 0; x <= n; x++)
                {
                    float wx = (x / (float)n - 0.5f) * size + 44.0f;
                    float wz = (z / (float)n - 0.5f) * size;
                    float y = SampleGroundHeight(wx, wz);
                    pts[x, z] = new Vector3(wx, y, wz);
                }

            var mat = new StandardMaterial3D
            {
                AlbedoColor = new Color(0.18f, 0.28f, 0.11f),
                Roughness = 0.90f,
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
                var cBot = new Color(0.15f, 0.26f, 0.09f, 0.0f);
                var cMid = new Color(0.22f, 0.42f, 0.13f, 0.48f);
                var cTip = new Color(0.32f, 0.54f, 0.16f, 1.0f);
                AddTri(st, root - side * 0.06f, root + side * 0.06f, root + dir * 0.16f + side * 0.04f + new Vector3(0, 0.48f, 0), cBot, cBot, cMid);
                AddTri(st, root - side * 0.06f, root + dir * 0.16f + side * 0.04f + new Vector3(0, 0.48f, 0), root + dir * 0.16f - side * 0.04f + new Vector3(0, 0.48f, 0), cBot, cMid, cMid);
                AddTri(st, root + dir * 0.16f - side * 0.04f + new Vector3(0, 0.48f, 0), root + dir * 0.16f + side * 0.04f + new Vector3(0, 0.48f, 0), root + dir * 0.34f + new Vector3(0, 0.92f, 0), cMid, cMid, cTip);
            }
            st.GenerateNormals();

            const int count = 12000;
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
                float gx = (float)(rng.NextDouble() * 110.0 - 11.0);
                float gz = (float)(rng.NextDouble() * 76.0 - 38.0);
                float gy = SampleGroundHeight(gx, gz);
                float s = 0.65f + (float)rng.NextDouble() * 0.65f;
                float yaw = (float)(rng.NextDouble() * Mathf.Tau);
                mm.SetInstanceTransform(i, new Transform3D(Basis.Identity.Rotated(Vector3.Up, yaw).Scaled(new Vector3(s, s, s)), new Vector3(gx, gy - 0.03f, gz)));
                float tintVar = 0.85f + (float)rng.NextDouble() * 0.30f;
                mm.SetInstanceColor(i, new Color(0.22f * tintVar, 0.42f * tintVar, 0.13f * tintVar));
            }

            _grassMat = new ShaderMaterial { Shader = GD.Load<Shader>("res://shaders/foliage_wind.gdshader") };
            EnsureWeatherWindTextures();
            _grassMat.SetShaderParameter("wind_dir_speed_tex", _windTex!);
            _grassMat.SetShaderParameter("weather_dynamic_tex", _weatherTex!);
            _grassMat.SetShaderParameter("bark_tex", _botTex!.BarkRoughTex);

            _grassMmi = new MultiMeshInstance3D
            {
                Multimesh = mm,
                MaterialOverride = _grassMat,
                CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
            };
            AddChild(_grassMmi);
        }

        private void BuildShowcaseTrees()
        {
            _treesRoot?.QueueFree();
            _markersRoot?.QueueFree();
            _treeRecords.Clear();

            _treesRoot = new Node3D { Name = "ShowcaseTrees" };
            _markersRoot = new Node3D { Name = "ScaleMarkers" };
            AddChild(_treesRoot);
            AddChild(_markersRoot);

            EnsureWeatherWindTextures();
            _floraMat ??= new ShaderMaterial { Shader = GD.Load<Shader>("res://shaders/flora_wind.gdshader") };
            _floraMat.SetShaderParameter("wind_dir_speed_tex", _windTex!);
            _floraMat.SetShaderParameter("weather_dynamic_tex", _weatherTex!);
            _floraMat.SetShaderParameter("leaf_broadleaf_tex", _botTex!.BroadleafTex);
            _floraMat.SetShaderParameter("leaf_conifer_tex", _botTex.ConiferTex);
            _floraMat.SetShaderParameter("leaf_acacia_tex", _botTex.AcaciaTex);
            _floraMat.SetShaderParameter("leaf_palm_tex", _botTex.PalmFernTex);
            _floraMat.SetShaderParameter("bark_tex", _botTex.BarkRoughTex);

            AgeStage[] ages = { AgeStage.Young, AgeStage.Mature, AgeStage.Ancient };
            for (int row = 0; row < ShowcaseSpecies.Length; row++)
            {
                float x = row * 22.0f;
                var sp = ShowcaseSpecies[row];

                // Place 3 scale reference poles beside each row (0.85m Wolf, 1.65m Bison, 3.60m Mammoth)
                AddScalePole(new Vector3(x - 4.5f, SampleGroundHeight(x - 4.5f, 8.5f), 8.5f), 0.85f, new Color(0.85f, 0.35f, 0.25f));
                AddScalePole(new Vector3(x - 3.3f, SampleGroundHeight(x - 3.3f, 8.5f), 8.5f), 1.65f, new Color(0.85f, 0.72f, 0.22f));
                AddScalePole(new Vector3(x - 2.1f, SampleGroundHeight(x - 2.1f, 8.5f), 8.5f), 3.60f, new Color(0.32f, 0.68f, 0.90f));

                for (int col = 0; col < 3; col++)
                {
                    float z = (col - 1) * -14.0f; // +14 (Young), 0 (Mature), -14 (Ancient)
                    float y = SampleGroundHeight(x, z);
                    ArrayMesh mesh = ProceduralTreeBuilder.BuildTree(sp.Id, ages[col], _seed + row * 17 + col * 5);
                    int tris = mesh.GetSurfaceCount() > 0 ? mesh.SurfaceGetArrayLen(0) / 3 : 0;

                    var mm = new MultiMesh
                    {
                        TransformFormat = MultiMesh.TransformFormatEnum.Transform3D,
                        UseColors = true,
                        Mesh = mesh,
                        InstanceCount = 1,
                    };
                    mm.SetInstanceTransform(0, new Transform3D(Basis.Identity, new Vector3(x, y - 0.1f, z)));
                    mm.SetInstanceColor(0, sp.Tint);

                    var mmi = new MultiMeshInstance3D
                    {
                        Multimesh = mm,
                        MaterialOverride = _floraMat,
                        CastShadow = GeometryInstance3D.ShadowCastingSetting.On,
                    };
                    _treesRoot.AddChild(mmi);
                    _treeRecords.Add((new Vector3(x, y, z), $"{sp.NameVi} ({ages[col]})", tris));
                }
            }

            _markersRoot.Visible = _showMarkersAndGrass;
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

        private void EnsureWeatherWindTextures()
        {
            byte[] wBytes = new byte[4 * 4 * 3];
            byte spdByte = (byte)(Math.Clamp(_windSpeed / 30.0f, 0.0f, 1.0f) * 255.0f);
            for (int i = 0; i < 16; i++)
            {
                wBytes[i * 3 + 0] = 220; // wind X+
                wBytes[i * 3 + 1] = 175; // wind Z+
                wBytes[i * 3 + 2] = spdByte;
            }
            var wImg = Image.CreateFromData(4, 4, false, Image.Format.Rgb8, wBytes);
            if (_windTex == null) _windTex = ImageTexture.CreateFromImage(wImg);
            else _windTex.Update(wImg);

            if (_weatherTex == null)
            {
                byte[] dBytes = new byte[4 * 4 * 4];
                _weatherTex = ImageTexture.CreateFromImage(Image.CreateFromData(4, 4, false, Image.Format.Rgba8, dBytes));
            }
        }

        private void BuildHud()
        {
            var canvas = new CanvasLayer();
            AddChild(canvas);
            var panel = new PanelContainer { Position = new Vector2(14, 14) };
            panel.AddThemeStyleboxOverride("panel", new StyleBoxFlat { BgColor = new Color(0.05f, 0.08f, 0.12f, 0.82f), ContentMarginLeft = 10, ContentMarginRight = 10, ContentMarginTop = 8, ContentMarginBottom = 8 });
            canvas.AddChild(panel);
            _hudLabel = new Label();
            _hudLabel.AddThemeFontSizeOverride("font_size", 13);
            panel.AddChild(_hudLabel);

            var help = new Label
            {
                Text = "WASD: Đi | Chuột phải: Xoay | V: Sói(0.85m)/Ma Mút(3.6m)/Tự do | 1-5: 5 Loài | J/K: Xoay nắng | U/I: Gió | G: Đổi Seed | O: Wireframe | B: Mốc/Cỏ",
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
                    case Key.Key1: TeleportToRow(0); break;
                    case Key.Key2: TeleportToRow(1); break;
                    case Key.Key3: TeleportToRow(2); break;
                    case Key.Key4: TeleportToRow(3); break;
                    case Key.Key5: TeleportToRow(4); break;
                    case Key.V: _povMode = (_povMode + 1) % 3; break;
                    case Key.G: _seed = (int)(GD.Randi() % 90000 + 1000); BuildShowcaseTrees(); break;
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

        public override void _Process(double delta)
        {
            float dt = (float)delta;
            if (Input.IsKeyPressed(Key.J)) { _sunAzimDeg -= 40f * dt; UpdateSunTransform(); }
            if (Input.IsKeyPressed(Key.K)) { _sunAzimDeg += 40f * dt; UpdateSunTransform(); }
            if (Input.IsKeyPressed(Key.U)) { _windSpeed = Math.Clamp(_windSpeed - 12f * dt, 0f, 25f); EnsureWeatherWindTextures(); }
            if (Input.IsKeyPressed(Key.I)) { _windSpeed = Math.Clamp(_windSpeed + 12f * dt, 0f, 25f); EnsureWeatherWindTextures(); }

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
                float spd = (_povMode == 2 ? 22f : 8f) * (Input.IsKeyPressed(Key.Shift) ? 2.2f : 1.0f);
                Vector3 p = _cam.Position + (move.LengthSquared() > 0.001f ? move.Normalized() * spd * dt : Vector3.Zero);
                if (_povMode != 2)
                {
                    float eyeH = _povMode == 0 ? 0.85f : 3.60f;
                    p.Y = SampleGroundHeight(p.X, p.Z) + eyeH;
                }
                _cam.Position = p;
            }

            if (_hudLabel != null && _cam != null)
            {
                string nearName = "-"; int nearTris = 0; float bestD = 9999f;
                foreach (var rec in _treeRecords)
                {
                    float d = _cam.Position.DistanceTo(rec.Pos);
                    if (d < bestD) { bestD = d; nearName = rec.Name; nearTris = rec.Tris; }
                }
                float fps = (float)Engine.GetFramesPerSecond();
                float ms = fps > 1f ? 1000f / fps : 0f;
                int totalTris = (int)RenderingServer.GetRenderingInfo(RenderingServer.RenderingInfo.TotalPrimitivesInFrame);
                int drawCalls = (int)RenderingServer.GetRenderingInfo(RenderingServer.RenderingInfo.TotalDrawCallsInFrame);
                string pov = _povMode == 0 ? "Sói (0.85m)" : (_povMode == 1 ? "Voi Ma Mút (3.60m)" : "Tự do");
                float alphaPct = _botTex != null && _botTex.TransparentPercent.TryGetValue("assets/textures/flora/leaf_broadleaf.png", out float pct) ? pct : 0f;

                _hudLabel.Text =
                    $"Flora Showcase Lab | FPS: {fps:0} ({ms:0.1} ms) | Total Tris: {totalTris:N0} | DrawCalls: {drawCalls} | Góc nhìn [V]: {pov}\n" +
                    $"Cây gần nhất: {nearName} ({nearTris:N0} tris) | Alpha trong suốt lá: {alphaPct:0.0}% | Nắng: {_sunAzimDeg:0}° | Gió: {_windSpeed:0.0}m/s | Seed: {_seed}";
            }
        }

        private void TeleportToRow(int row)
        {
            if (_cam == null) return;
            float x = row * 22.0f;
            float z = 12.0f;
            float eye = _povMode == 1 ? 3.60f : 0.85f;
            _cam.Position = new Vector3(x, SampleGroundHeight(x, z) + eye, z);
            _cam.LookAt(new Vector3(x, SampleGroundHeight(x, 0f) + 5.5f, 0f), Vector3.Up);
            _pitch = _cam.Rotation.X;
            _yaw = _cam.Rotation.Y;
        }

        private void UpdateSunTransform()
        {
            if (_sun == null) return;
            float az = Mathf.DegToRad(_sunAzimDeg);
            float el = Mathf.DegToRad(_sunElevDeg);
            Vector3 dir = new Vector3(MathF.Cos(el) * MathF.Cos(az), MathF.Sin(el), MathF.Cos(el) * MathF.Sin(az)).Normalized();
            _sun.LookAtFromPosition(dir * 50f, Vector3.Zero, Vector3.Up);
            _skyMat?.SetShaderParameter("sun_direction", dir);
        }

        private void PrintVerificationLog()
        {
            if (_botTex != null)
            {
                foreach (var kv in _botTex.TransparentPercent)
                {
                    int border = _botTex.BorderOpaquePixels.TryGetValue(kv.Key, out int b) ? b : -1;
                    GD.Print($"[BotanicalPNG] {kv.Key} | 512x512 RGBA8 | Transparent={kv.Value:0.0}% | BorderOpaquePixels={border}");
                }
            }
            for (int i = 0; i < ShowcaseSpecies.Length; i++)
            {
                var r = _treeRecords[i * 3 + 1]; // Mature sample
                GD.Print($"[ShowcaseSpecies] {ShowcaseSpecies[i].Id} (Mature) = {r.Tris:N0} tris");
            }
        }

        private static float SampleGroundHeight(float x, float z) => MathF.Sin(x * 0.06f) * 0.6f + MathF.Cos(z * 0.08f) * 0.4f;

        private static void AddTri(SurfaceTool st, Vector3 a, Vector3 b, Vector3 c, Color ca, Color cb, Color cc)
        {
            st.SetColor(ca); st.AddVertex(a);
            st.SetColor(cb); st.AddVertex(b);
            st.SetColor(cc); st.AddVertex(c);
        }
    }
}
