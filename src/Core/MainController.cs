using Godot;
using PrimevalWorld.Camera;
using PrimevalWorld.Flora;
using PrimevalWorld.Terrain;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Core
{
    /// <summary>
    /// Root scene controller for Stage 2 (2x2 km Island + Sloped River + MultiMesh Flora).
    /// </summary>
    public partial class MainController : Node3D
    {
        private readonly WorldGenerator _worldGen = new WorldGenerator(2026);
        private TerrainManager? _terrainMgr;
        private WaterSurface? _waterSurface;
        private FloraManager? _floraMgr;
        private SpectatorCamera? _camera;
        private Label? _telemetryLabel;

        public override void _Ready()
        {
            SetupEnvironmentAndLighting();

            _terrainMgr = new TerrainManager { Name = "TerrainManager" };
            AddChild(_terrainMgr);

            _waterSurface = new WaterSurface { Name = "WaterSurface" };
            AddChild(_waterSurface);

            _floraMgr = new FloraManager { Name = "FloraManager" };
            AddChild(_floraMgr);

            _camera = new SpectatorCamera { Name = "SpectatorCamera" };
            AddChild(_camera);
            _camera.Current = true;

            BuildCompactHud();
            RegenerateWorld(_worldGen.Seed);
        }

        private void SetupEnvironmentAndLighting()
        {
            var horizonColor = new Color(0.62f, 0.72f, 0.82f);

            var skyMaterial = new ProceduralSkyMaterial
            {
                SkyTopColor = new Color(0.16f, 0.32f, 0.56f),
                SkyHorizonColor = horizonColor,
                GroundBottomColor = new Color(0.10f, 0.14f, 0.20f),
                GroundHorizonColor = horizonColor,
                SunAngleMax = 24.0f,
                SunCurve = 0.07f,
            };

            var sky = new Sky { SkyMaterial = skyMaterial };
            var env = new Environment
            {
                BackgroundMode = Environment.BGMode.Sky,
                Sky = sky,
                AmbientLightSource = Environment.AmbientSource.Sky,
                AmbientLightSkyContribution = 0.36f,
                TonemapMode = Environment.ToneMapper.Aces,
                TonemapExposure = 1.02f,
                FogEnabled = true,
                FogMode = Environment.FogModeEnum.Depth,
                FogLightColor = horizonColor,
                FogDensity = 0.0012f,
                FogDepthBegin = 260.0f,
                FogDepthEnd = 5200.0f,
                FogAerialPerspective = 0.65f,
                SsaoEnabled = true,
                SsaoRadius = 2.6f,
                SsaoIntensity = 2.1f,
            };

            var worldEnv = new WorldEnvironment
            {
                Name = "WorldEnvironment",
                Environment = env,
            };
            AddChild(worldEnv);

            var sun = new DirectionalLight3D
            {
                Name = "SunLight",
                LightColor = new Color(1.0f, 0.90f, 0.76f),
                LightEnergy = 1.95f,
                ShadowEnabled = true,
                ShadowBlur = 1.2f,
                DirectionalShadowMode = DirectionalLight3D.ShadowMode.Parallel4Splits,
                DirectionalShadowMaxDistance = 1100.0f,
            };
            sun.RotationDegrees = new Vector3(-26.0f, -128.0f, 0.0f);
            AddChild(sun);
        }

        private void BuildCompactHud()
        {
            var hudLayer = new CanvasLayer { Name = "HudLayer" };
            AddChild(hudLayer);

            var panel = new PanelContainer
            {
                Position = new Vector2(14, 14),
            };
            var style = new StyleBoxFlat
            {
                BgColor = new Color(0.05f, 0.08f, 0.12f, 0.78f),
                BorderColor = new Color(0.28f, 0.42f, 0.56f, 0.90f),
                BorderWidthLeft = 1,
                BorderWidthTop = 1,
                BorderWidthRight = 1,
                BorderWidthBottom = 1,
                CornerRadiusTopLeft = 6,
                CornerRadiusTopRight = 6,
                CornerRadiusBottomLeft = 6,
                CornerRadiusBottomRight = 6,
                ContentMarginLeft = 12,
                ContentMarginRight = 12,
                ContentMarginTop = 8,
                ContentMarginBottom = 8,
            };
            panel.AddThemeStyleboxOverride("panel", style);
            hudLayer.AddChild(panel);

            var vbox = new VBoxContainer();
            panel.AddChild(vbox);

            _telemetryLabel = new Label
            {
                Text = "Primeval Reach | Godot 4 Forward+",
            };
            _telemetryLabel.AddThemeFontSizeOverride("font_size", 14);
            vbox.AddChild(_telemetryLabel);

            var btnRow = new HBoxContainer();
            vbox.AddChild(btnRow);

            var newSeedBtn = new Button
            {
                Text = "Đổi Seed (G)",
            };
            newSeedBtn.Pressed += () => RegenerateWorld((int)(GD.Randi() % 90000 + 1000));
            btnRow.AddChild(newSeedBtn);

            var resetCamBtn = new Button
            {
                Text = "Reset Cam (R)",
            };
            resetCamBtn.Pressed += () => _camera?.ResetToScenicOverlook();
            btnRow.AddChild(resetCamBtn);

            var helpLabel = new Label
            {
                Text = "WASD: Bay | Chuột phải + kéo: Xoay | Q/E: Lên/Xuống | Shift: Bay nhanh | Cuộn chuột: Tốc độ | ESC: Thoát",
                Position = new Vector2(16, 868),
            };
            helpLabel.SetAnchorsPreset(Control.LayoutPreset.BottomLeft);
            helpLabel.OffsetLeft = 16;
            helpLabel.OffsetBottom = -14;
            helpLabel.OffsetTop = -38;
            helpLabel.AddThemeFontSizeOverride("font_size", 13);
            hudLayer.AddChild(helpLabel);
        }

        private void RegenerateWorld(int seed)
        {
            _worldGen.SetSeed(seed);
            _terrainMgr?.BuildTerrain(_worldGen);
            _waterSurface?.BuildWater(_worldGen);
            _floraMgr?.BuildFlora(_worldGen);
        }

        public override void _UnhandledInput(InputEvent @event)
        {
            if (@event is InputEventKey key && key.Pressed && !key.Echo && key.Keycode == Key.G)
            {
                RegenerateWorld((int)(GD.Randi() % 90000 + 1000));
            }
        }

        public override void _Process(double delta)
        {
            if (_telemetryLabel != null && _camera != null)
            {
                Vector3 p = _camera.Position;
                int floraCount = _floraMgr?.TotalInstanceCount ?? 0;
                _telemetryLabel.Text =
                    $"Primeval Reach (Chặng 2: 2x2 km) | FPS: {Engine.GetFramesPerSecond():0} | Seed: {_worldGen.Seed} | Thực vật/Đá: {floraCount:N0}\n" +
                    $"Vị trí: X={p.X:0.0}m  Y={p.Y:0.0}m  Z={p.Z:0.0}m | Tốc độ: {_camera.CurrentSpeed:0} m/s";
            }
        }
    }
}
