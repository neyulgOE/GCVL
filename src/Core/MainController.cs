using Godot;
using PrimevalWorld.Camera;
using PrimevalWorld.Flora;
using PrimevalWorld.Terrain;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Core
{
    /// <summary>
    /// Root scene controller for Primeval Reach (3x3 km Prehistoric Multi-Continent World):
    /// - 4 Continents / 5 Biomes
    /// - 45k-65k MultiMesh prehistoric flora & boulders
    /// - [M] High-res 2D Topographic World Map Overlay (click to teleport)
    /// - [1-5] Quick camera jump presets to each biome
    /// </summary>
    public partial class MainController : Node3D
    {
        private readonly WorldGenerator _worldGen = new WorldGenerator(2026);
        private TerrainManager? _terrainMgr;
        private WaterSurface? _waterSurface;
        private FloraManager? _floraMgr;
        private SpectatorCamera? _camera;
        private Label? _telemetryLabel;

        private Control? _worldMapOverlay;
        private TextureRect? _worldMapRect;
        private Control? _cameraPin;

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
            BuildWorldMapOverlay();
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
                FogDensity = 0.00095f,
                FogDepthBegin = 320.0f,
                FogDepthEnd = 6800.0f,
                FogAerialPerspective = 0.62f,
                SsaoEnabled = true,
                SsaoRadius = 2.6f,
                SsaoIntensity = 2.0f,
            };

            AddChild(new WorldEnvironment { Name = "WorldEnvironment", Environment = env });

            var sun = new DirectionalLight3D
            {
                Name = "SunLight",
                LightColor = new Color(1.0f, 0.90f, 0.76f),
                LightEnergy = 1.95f,
                ShadowEnabled = true,
                ShadowBlur = 1.2f,
                DirectionalShadowMode = DirectionalLight3D.ShadowMode.Parallel4Splits,
                DirectionalShadowMaxDistance = 1200.0f,
            };
            sun.RotationDegrees = new Vector3(-27.0f, -128.0f, 0.0f);
            AddChild(sun);
        }

        private void BuildCompactHud()
        {
            var hudLayer = new CanvasLayer { Name = "HudLayer" };
            AddChild(hudLayer);

            var panel = new PanelContainer { Position = new Vector2(14, 14) };
            var style = new StyleBoxFlat
            {
                BgColor = new Color(0.05f, 0.08f, 0.12f, 0.80f),
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

            _telemetryLabel = new Label { Text = "Primeval Reach | Godot 4 Forward+" };
            _telemetryLabel.AddThemeFontSizeOverride("font_size", 14);
            vbox.AddChild(_telemetryLabel);

            var btnRow = new HBoxContainer();
            vbox.AddChild(btnRow);

            var newSeedBtn = new Button { Text = "Đổi Seed (G)" };
            newSeedBtn.Pressed += () => RegenerateWorld((int)(GD.Randi() % 90000 + 1000));
            btnRow.AddChild(newSeedBtn);

            var mapBtn = new Button { Text = "Bản đồ (M)" };
            mapBtn.Pressed += ToggleWorldMap;
            btnRow.AddChild(mapBtn);

            var resetCamBtn = new Button { Text = "Toàn cảnh (R)" };
            resetCamBtn.Pressed += () => _camera?.ResetToScenicOverlook();
            btnRow.AddChild(resetCamBtn);

            var helpLabel = new Label
            {
                Text = "WASD: Bay | Chuột phải: Xoay | Q/E: Lên/Xuống | Shift: Nhanh | 1-5: Nhảy tới 5 Quần xã | M: Bản đồ | G: Đổi Seed",
            };
            helpLabel.SetAnchorsPreset(Control.LayoutPreset.BottomLeft);
            helpLabel.OffsetLeft = 16;
            helpLabel.OffsetBottom = -14;
            helpLabel.OffsetTop = -38;
            helpLabel.AddThemeFontSizeOverride("font_size", 13);
            hudLayer.AddChild(helpLabel);
        }

        private void BuildWorldMapOverlay()
        {
            var mapLayer = new CanvasLayer { Name = "WorldMapLayer" };
            AddChild(mapLayer);

            var backdrop = new ColorRect
            {
                Color = new Color(0.02f, 0.04f, 0.07f, 0.78f),
                Visible = false,
            };
            backdrop.SetAnchorsPreset(Control.LayoutPreset.FullRect);
            mapLayer.AddChild(backdrop);
            _worldMapOverlay = backdrop;

            var centerBox = new PanelContainer
            {
                CustomMinimumSize = new Vector2(760, 470),
            };
            centerBox.SetAnchorsPreset(Control.LayoutPreset.Center);
            centerBox.OffsetLeft = -380;
            centerBox.OffsetRight = 380;
            centerBox.OffsetTop = -235;
            centerBox.OffsetBottom = 235;
            backdrop.AddChild(centerBox);

            var vbox = new VBoxContainer();
            centerBox.AddChild(vbox);

            var title = new Label
            {
                Text = "BẢN ĐỒ THẾ GIỚI TIỀN SỬ PRIMEVAL REACH (Click vào bản đồ để bay tới | M để đóng)",
                HorizontalAlignment = HorizontalAlignment.Center,
            };
            title.AddThemeFontSizeOverride("font_size", 13);
            vbox.AddChild(title);

            _worldMapRect = new TextureRect
            {
                CustomMinimumSize = new Vector2(732, 400),
                StretchMode = TextureRect.StretchModeEnum.KeepAspectCentered,
            };
            _worldMapRect.GuiInput += OnWorldMapClick;
            vbox.AddChild(_worldMapRect);

            // Red pin indicating current camera XZ location
            var pin = new ColorRect
            {
                Color = new Color(1.0f, 0.25f, 0.20f, 1.0f),
                CustomMinimumSize = new Vector2(10, 10),
                Size = new Vector2(10, 10),
                MouseFilter = Control.MouseFilterEnum.Ignore,
            };
            _worldMapRect.AddChild(pin);
            _cameraPin = pin;

            var legend = new Label
            {
                Text = "[1] Băng giá Tây-Bắc  |  [2] Đất đỏ & Ốc đảo Tây-Nam  |  [3] Đại ngàn Trung/Đông  |  [4] Thảo nguyên Thu Đông-Bắc  |  [5] Đảo Bảo tồn",
                HorizontalAlignment = HorizontalAlignment.Center,
            };
            legend.AddThemeFontSizeOverride("font_size", 11);
            vbox.AddChild(legend);
        }

        private void OnWorldMapClick(InputEvent @event)
        {
            if (_worldMapRect == null || _camera == null) return;
            if (@event is InputEventMouseButton mb && mb.Pressed && mb.ButtonIndex == MouseButton.Left)
            {
                Vector2 size = _worldMapRect.Size;
                float nx = Mathf.Clamp(mb.Position.X / size.X, 0.0f, 1.0f);
                float nz = Mathf.Clamp(mb.Position.Y / size.Y, 0.0f, 1.0f);
                float wx = nx * WorldGenerator.RegionWidthMeters;
                float wz = nz * WorldGenerator.RegionDepthMeters;
                float h = Mathf.Max(8.0f, _worldGen.SampleHeight(wx, wz));
                _camera.TeleportTo(new Vector3(wx, h + 45.0f, wz + 70.0f), new Vector3(wx, h, wz));
                ToggleWorldMap();
            }
        }

        private void ToggleWorldMap()
        {
            if (_worldMapOverlay == null) return;
            _worldMapOverlay.Visible = !_worldMapOverlay.Visible;
            if (_worldMapOverlay.Visible)
            {
                Input.MouseMode = Input.MouseModeEnum.Visible;
                UpdateCameraPin();
            }
        }

        private void UpdateCameraPin()
        {
            if (_cameraPin == null || _worldMapRect == null || _camera == null) return;
            float nx = Mathf.Clamp(_camera.Position.X / WorldGenerator.RegionWidthMeters, 0.0f, 1.0f);
            float nz = Mathf.Clamp(_camera.Position.Z / WorldGenerator.RegionDepthMeters, 0.0f, 1.0f);
            _cameraPin.Position = new Vector2(nx * _worldMapRect.Size.X - 5.0f, nz * _worldMapRect.Size.Y - 5.0f);
        }

        private void RegenerateWorld(int seed)
        {
            _worldGen.SetSeed(seed);
            _terrainMgr?.BuildTerrain(_worldGen);
            _waterSurface?.BuildWater(_worldGen);
            _floraMgr?.BuildFlora(_worldGen);
            if (_worldMapRect != null)
            {
                _worldMapRect.Texture = _worldGen.BuildWorldMapTexture();
            }
        }

        public override void _UnhandledInput(InputEvent @event)
        {
            if (@event is InputEventKey key && key.Pressed && !key.Echo)
            {
                switch (key.Keycode)
                {
                    case Key.G:
                        RegenerateWorld((int)(GD.Randi() % 90000 + 1000));
                        break;
                    case Key.M:
                        ToggleWorldMap();
                        break;
                    case Key.Key1: // NW Glacial Alpine Massif & Fjords
                        _camera?.TeleportTo(new Vector3(1120.0f, 165.0f, 920.0f), new Vector3(960.0f, 45.0f, 320.0f));
                        break;
                    case Key.Key2: // SW Terracotta Desert & Turquoise Lagoon
                        _camera?.TeleportTo(new Vector3(920.0f, 110.0f, 1840.0f), new Vector3(880.0f, 16.0f, 1360.0f));
                        break;
                    case Key.Key3: // East Primeval Forest, Crescent Bay & Delta
                        _camera?.TeleportTo(new Vector3(2450.0f, 120.0f, 1880.0f), new Vector3(2560.0f, 12.0f, 1340.0f));
                        break;
                    case Key.Key4: // NE Autumn Steppes Plateau & Highland Lake
                        _camera?.TeleportTo(new Vector3(2840.0f, 118.0f, 1020.0f), new Vector3(2680.0f, 22.0f, 580.0f));
                        break;
                    case Key.Key5: // SE Sanctuary Archipelago
                        _camera?.TeleportTo(new Vector3(3180.0f, 105.0f, 1980.0f), new Vector3(3480.0f, 8.0f, 1720.0f));
                        break;
                }
            }
        }

        public override void _Process(double delta)
        {
            if (_telemetryLabel != null && _camera != null)
            {
                Vector3 p = _camera.Position;
                TerrainSample s = _worldGen.SamplePoint(p.X, p.Z);
                int floraCount = _floraMgr?.TotalInstanceCount ?? 0;
                _telemetryLabel.Text =
                    $"Primeval Reach (4 Lục địa | 3.8x2.0 km) | FPS: {Engine.GetFramesPerSecond():0} | Seed: {_worldGen.Seed} | Thực thể: {floraCount:N0}\n" +
                    $"Quần xã: {FormatBiomeName(s.Biome)} | X={p.X:0.0}m Y={p.Y:0.0}m Z={p.Z:0.0}m | Tốc độ: {_camera.CurrentSpeed:0} m/s";
            }

            if (_worldMapOverlay != null && _worldMapOverlay.Visible)
            {
                UpdateCameraPin();
            }
        }

        private static string FormatBiomeName(BiomeId biome) => biome switch
        {
            BiomeId.GlacialAlpine => "Núi băng Tây-Bắc",
            BiomeId.TerracottaDesert => "Hoang mạc Đất đỏ Tây-Nam",
            BiomeId.PrimevalForest => "Đại ngàn Nguyên sinh",
            BiomeId.AutumnSteppe => "Thảo nguyên Mùa thu Đông-Bắc",
            BiomeId.SanctuaryIsland => "Đảo Bảo tồn Đông-Nam",
            BiomeId.CoastalReef => "Thềm San hô Nông",
            _ => "Đại dương Sâu",
        };
    }
}
