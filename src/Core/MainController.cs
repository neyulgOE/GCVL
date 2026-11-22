using System.Diagnostics;
using Godot;
using PrimevalWorld.Camera;
using PrimevalWorld.Flora;
using PrimevalWorld.Terrain;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Core
{
    /// <summary>
    /// Root controller for Stage 1+2 (9.6 x 5.4 km, 4-Level Chunk LOD, Physical Erosion,
    /// Dynamic Hydrology, Atmosphere/Rain Shadow, 6-Soil Pedology & 6-Mode [M] Analysis Map).
    /// Press [F] to toggle optional preview flora (default OFF for clean geological/soil inspection).
    /// </summary>
    public partial class MainController : Node3D
    {
        private readonly TectonicContinentGen _tectonic = new TectonicContinentGen();
        private readonly ErosionPhysics _erosion = new ErosionPhysics();
        private readonly HydrologySolver _hydrology = new HydrologySolver();
        private readonly AtmosphereClimate _climate = new AtmosphereClimate();
        private readonly SoilPedology _soil = new SoilPedology();

        private TerrainChunkManager? _terrainMgr;
        private WaterSurface? _waterSurface;
        private FloraManager? _floraMgr;
        private SpectatorCamera? _camera;
        private Label? _telemetryLabel;

        private Control? _worldMapOverlay;
        private TextureRect? _worldMapRect;
        private Control? _cameraPin;
        private Label? _mapLegendLabel;

        private ImageTexture[] _mapTextures = new ImageTexture[6];
        private int _mapMode = 0;
        private int _seed = 2026;
        private bool _floraEnabled = false;
        private bool _floraBuiltForSeed = false;

        public override void _Ready()
        {
            SetupEnvironmentAndLighting();

            _terrainMgr = new TerrainChunkManager { Name = "TerrainChunkManager" };
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
            RegenerateWorld(_seed);
        }

        private void SetupEnvironmentAndLighting()
        {
            var horizonColor = new Color(0.60f, 0.72f, 0.84f);

            var skyMaterial = new ProceduralSkyMaterial
            {
                SkyTopColor = new Color(0.15f, 0.31f, 0.56f),
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
                FogDensity = 0.00055f,
                FogDepthBegin = 650.0f,
                FogDepthEnd = 13500.0f,
                FogAerialPerspective = 0.72f,
                SsaoEnabled = true,
                SsaoRadius = 3.2f,
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
                DirectionalShadowMaxDistance = 1400.0f,
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
                BgColor = new Color(0.05f, 0.08f, 0.12f, 0.84f),
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

            _telemetryLabel = new Label { Text = "Primeval Reach 9.6x5.4 km | Godot 4 Forward+" };
            _telemetryLabel.AddThemeFontSizeOverride("font_size", 14);
            vbox.AddChild(_telemetryLabel);

            var btnRow = new HBoxContainer();
            vbox.AddChild(btnRow);

            var newSeedBtn = new Button { Text = "Đổi Seed (G)" };
            newSeedBtn.Pressed += () => RegenerateWorld((int)(GD.Randi() % 90000 + 1000));
            btnRow.AddChild(newSeedBtn);

            var mapBtn = new Button { Text = "Bản đồ 6 Lớp (M)" };
            mapBtn.Pressed += ToggleWorldMap;
            btnRow.AddChild(mapBtn);

            var floraBtn = new Button { Text = "Bật/Tắt Cây (F)" };
            floraBtn.Pressed += ToggleFlora;
            btnRow.AddChild(floraBtn);

            var resetCamBtn = new Button { Text = "Toàn cảnh (R)" };
            resetCamBtn.Pressed += () => _camera?.ResetToScenicOverlook();
            btnRow.AddChild(resetCamBtn);

            var helpLabel = new Label
            {
                Text = "WASD: Bay | Chuột phải: Xoay | Q/E: Lên/Xuống | Shift+Cuộn: Max 1000m/s | 1-5: 5 Vùng | M: Bản đồ 6 lớp | F: Bật/Tắt cây | G: Đổi Seed",
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
                Color = new Color(0.02f, 0.04f, 0.07f, 0.82f),
                Visible = false,
            };
            backdrop.SetAnchorsPreset(Control.LayoutPreset.FullRect);
            mapLayer.AddChild(backdrop);
            _worldMapOverlay = backdrop;

            var centerBox = new PanelContainer { CustomMinimumSize = new Vector2(880, 560) };
            centerBox.SetAnchorsPreset(Control.LayoutPreset.Center);
            centerBox.OffsetLeft = -440;
            centerBox.OffsetRight = 440;
            centerBox.OffsetTop = -280;
            centerBox.OffsetBottom = 280;
            backdrop.AddChild(centerBox);

            var vbox = new VBoxContainer();
            centerBox.AddChild(vbox);

            var title = new Label
            {
                Text = "BẢN ĐỒ PHÂN TÍCH VẬT LÝ 9.6x5.4 KM (Click bản đồ để bay tới | Phím 1-6 đổi lớp | M để đóng)",
                HorizontalAlignment = HorizontalAlignment.Center,
            };
            title.AddThemeFontSizeOverride("font_size", 13);
            vbox.AddChild(title);

            var modeRow = new HBoxContainer { Alignment = BoxContainer.AlignmentMode.Center };
            vbox.AddChild(modeRow);
            string[] modeNames =
            {
                "1. Địa hình & Sông",
                "2. Nhiệt độ (°C)",
                "3. Mưa & Gió",
                "4. Độ ẩm & Lưu vực",
                "5. Thổ nhưỡng (6 Đất)",
                "6. Độ dốc & Xói mòn"
            };
            for (int i = 0; i < modeNames.Length; i++)
            {
                int idx = i;
                var btn = new Button { Text = modeNames[i] };
                btn.Pressed += () => SetMapMode(idx);
                modeRow.AddChild(btn);
            }

            _worldMapRect = new TextureRect
            {
                CustomMinimumSize = new Vector2(840, 472),
                StretchMode = TextureRect.StretchModeEnum.KeepAspectCentered,
            };
            _worldMapRect.GuiInput += OnWorldMapClick;
            vbox.AddChild(_worldMapRect);

            var pin = new ColorRect
            {
                Color = new Color(1.0f, 0.25f, 0.20f, 1.0f),
                CustomMinimumSize = new Vector2(10, 10),
                Size = new Vector2(10, 10),
                MouseFilter = Control.MouseFilterEnum.Ignore,
            };
            _worldMapRect.AddChild(pin);
            _cameraPin = pin;

            _mapLegendLabel = new Label
            {
                Text = "Lớp 1: Địa hình & Thủy văn",
                HorizontalAlignment = HorizontalAlignment.Center,
            };
            _mapLegendLabel.AddThemeFontSizeOverride("font_size", 12);
            vbox.AddChild(_mapLegendLabel);
        }

        private void SetMapMode(int mode)
        {
            _mapMode = mode;
            if (_worldMapRect != null && _mapTextures[mode] != null)
                _worldMapRect.Texture = _mapTextures[mode];

            if (_mapLegendLabel != null)
            {
                _mapLegendLabel.Text = mode switch
                {
                    0 => "Lớp 1: Địa hình Hillshade + Sông ngòi chảy dốc + Thềm san hô ngọc lam",
                    1 => "Lớp 2: Nhiệt độ bề mặt (-15°C Xanh băng -> +15°C Vàng -> +38°C Đỏ nóng)",
                    2 => "Lớp 3: Lượng mưa & Bóng mưa (Sườn đón gió xanh đậm vs Bóng mưa Tây-Nam khô vàng) + Mũi tên hướng Gió",
                    3 => "Lớp 4: Độ ẩm đất & Tích tụ dòng chảy D8 (Mạng lưới lưu vực & hành lang ven nước)",
                    4 => "Lớp 5: 6 Loại Đất (Xanh đậm: Phù sa | Xanh rêu: Đất rừng | Vàng: Thảo nguyên | Đỏ: Cát đỏ | Cát biển | Xám: Băng/Đá)",
                    _ => "Lớp 6: Độ dốc & Trầm tích Xói mòn (Kiểm tra Góc nghỉ Cát 32° vs Đất 40° vs Đá gốc 64°)",
                };
            }
        }

        private void OnWorldMapClick(InputEvent @event)
        {
            if (_worldMapRect == null || _camera == null) return;
            if (@event is InputEventMouseButton mb && mb.Pressed && mb.ButtonIndex == MouseButton.Left)
            {
                Vector2 size = _worldMapRect.Size;
                float nx = Mathf.Clamp(mb.Position.X / size.X, 0.0f, 1.0f);
                float nz = Mathf.Clamp(mb.Position.Y / size.Y, 0.0f, 1.0f);
                float wx = nx * WorldPhysicsConfig.WorldWidth;
                float wz = nz * WorldPhysicsConfig.WorldDepth;
                float h = Mathf.Max(15.0f, _erosion.SampleHeight(wx, wz));
                _camera.TeleportTo(new Vector3(wx, h + 160.0f, wz + 260.0f), new Vector3(wx, h, wz));
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

        private void ToggleFlora()
        {
            _floraEnabled = !_floraEnabled;
            if (_floraMgr == null) return;

            if (_floraEnabled && !_floraBuiltForSeed)
            {
                _floraMgr.BuildFlora(_erosion, _hydrology, _climate, _soil, _seed);
                _floraBuiltForSeed = true;
            }
            _floraMgr.Visible = _floraEnabled;
        }

        private void UpdateCameraPin()
        {
            if (_cameraPin == null || _worldMapRect == null || _camera == null) return;
            float nx = Mathf.Clamp(_camera.Position.X / WorldPhysicsConfig.WorldWidth, 0.0f, 1.0f);
            float nz = Mathf.Clamp(_camera.Position.Z / WorldPhysicsConfig.WorldDepth, 0.0f, 1.0f);
            _cameraPin.Position = new Vector2(nx * _worldMapRect.Size.X - 5.0f, nz * _worldMapRect.Size.Y - 5.0f);
        }

        private void RegenerateWorld(int seed)
        {
            _seed = seed;
            _floraBuiltForSeed = false;
            var sw = Stopwatch.StartNew();

            _tectonic.Generate(seed);
            _erosion.Solve(_tectonic, seed);
            _hydrology.Solve(_tectonic, _erosion);
            _climate.Simulate(_tectonic, _erosion, _hydrology, seed);
            _soil.Simulate(_tectonic, _erosion, _hydrology, _climate);

            sw.Stop();
            double physicsMs = sw.Elapsed.TotalMilliseconds;

            _terrainMgr?.BuildTerrain(_erosion, _hydrology, _climate, _soil);
            _waterSurface?.BuildWater(_hydrology);

            if (_floraMgr != null)
            {
                _floraMgr.ClearFlora();
                _terrainMgr?.SetCanopyCoverageTexture(_floraMgr.BuildEmptyCoverageTexture());
                if (_floraEnabled)
                {
                    _floraMgr.BuildFlora(_erosion, _hydrology, _climate, _soil, seed);
                    _floraBuiltForSeed = true;
                }
                _floraMgr.Visible = _floraEnabled;
            }

            _mapTextures = WorldMapVisualizer.BuildAllModes(_tectonic, _erosion, _hydrology, _climate, _soil);
            SetMapMode(_mapMode);

            if (_camera != null)
                _terrainMgr?.UpdateLod(_camera.Position);

            // Report comprehensive Stage 1+2 statistics
            int totalLand = System.Math.Max(1, _soil.TotalLandCells);
            GD.Print($"[World9.6x5.4km] Seed={seed} | PhysicsGen={physicsMs:0.0}ms | Temp=[{_climate.MinTempC:0.0}°C..{_climate.MaxTempC:0.0}°C] | MeanPrecip={_climate.MeanPrecip * 100f:0.0}% | " +
                     $"Chunks={_terrainMgr?.ChunkCount ?? 0} | Soil%: " +
                     $"Alluvial={_soil.LandSoilCounts[0] * 100f / totalLand:0.0}%, " +
                     $"ForestBrown={_soil.LandSoilCounts[1] * 100f / totalLand:0.0}%, " +
                     $"SteppeLoess={_soil.LandSoilCounts[2] * 100f / totalLand:0.0}%, " +
                     $"AridRed={_soil.LandSoilCounts[3] * 100f / totalLand:0.0}%, " +
                     $"CoastalSand={_soil.LandSoilCounts[4] * 100f / totalLand:0.0}%, " +
                     $"Permafrost/Rock={_soil.LandSoilCounts[5] * 100f / totalLand:0.0}%");
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
                    case Key.F:
                        ToggleFlora();
                        break;
                    case Key.Key1:
                        if (_worldMapOverlay?.Visible == true) SetMapMode(0);
                        else _camera?.TeleportTo(new Vector3(2650.0f, 540.0f, 2250.0f), new Vector3(2400.0f, 120.0f, 900.0f));
                        break;
                    case Key.Key2:
                        if (_worldMapOverlay?.Visible == true) SetMapMode(1);
                        else _camera?.TeleportTo(new Vector3(2350.0f, 340.0f, 4550.0f), new Vector3(2150.0f, 40.0f, 3450.0f));
                        break;
                    case Key.Key3:
                        if (_worldMapOverlay?.Visible == true) SetMapMode(2);
                        else _camera?.TeleportTo(new Vector3(6100.0f, 360.0f, 4750.0f), new Vector3(6400.0f, 30.0f, 3350.0f));
                        break;
                    case Key.Key4:
                        if (_worldMapOverlay?.Visible == true) SetMapMode(3);
                        else _camera?.TeleportTo(new Vector3(7150.0f, 380.0f, 2650.0f), new Vector3(6700.0f, 55.0f, 1550.0f));
                        break;
                    case Key.Key5:
                        if (_worldMapOverlay?.Visible == true) SetMapMode(4);
                        else _camera?.TeleportTo(new Vector3(7950.0f, 320.0f, 5150.0f), new Vector3(8650.0f, 25.0f, 4450.0f));
                        break;
                    case Key.Key6:
                        if (_worldMapOverlay?.Visible == true) SetMapMode(5);
                        break;
                }
            }
        }

        public override void _Process(double delta)
        {
            if (_camera != null)
            {
                _terrainMgr?.UpdateLod(_camera.Position);
            }

            if (_telemetryLabel != null && _camera != null)
            {
                Vector3 p = _camera.Position;
                float h = _erosion.SampleHeight(p.X, p.Z);
                float slope = _erosion.SampleSlopeDeg(p.X, p.Z);
                ClimateSample cs = _climate.SampleClimate(p.X, p.Z);
                SoilSample ss = _soil.SampleSoil(p.X, p.Z);
                int tris = _terrainMgr?.ActiveTriangleEstimate ?? 0;
                string floraStr = _floraEnabled ? $"Cây: {_floraMgr?.TotalInstanceCount ?? 0:N0}" : "Cây: Tắt [F]";

                _telemetryLabel.Text =
                    $"Primeval Reach 9.6x5.4 km | FPS: {Engine.GetFramesPerSecond():0} | Seed: {_seed} | Tris: {tris:N0} | {floraStr}\n" +
                    $"Cao độ: {h:0.0}m | Dốc: {slope:0.0}° | Nhiệt: {cs.TemperatureC:0.0}°C | Ẩm: {cs.Moisture * 100f:0}% | Mưa: {cs.Precipitation * 100f:0}% | Gió: {cs.WindSpeed:0.0}m/s | Đất: {FormatSoil(ss.DominantSoil)}";
            }

            if (_worldMapOverlay != null && _worldMapOverlay.Visible)
                UpdateCameraPin();
        }

        private static string FormatSoil(SoilType soil) => soil switch
        {
            SoilType.AlluvialLoam => "Phù sa/Mùn đen",
            SoilType.ForestBrownSoil => "Đất rừng nâu",
            SoilType.SteppeLoess => "Đất thảo nguyên",
            SoilType.AridRedSand => "Đất đỏ/Cát khô",
            SoilType.CoastalSand => "Cát biển mặn",
            _ => "Băng giá/Đá gốc",
        };
    }
}
