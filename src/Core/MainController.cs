using System.Diagnostics;
using Godot;
using PrimevalWorld.Camera;
using PrimevalWorld.Flora;
using PrimevalWorld.Terrain;
using PrimevalWorld.Weather;
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
        private readonly SimulationClock _clock = new SimulationClock();
        private readonly DynamicWeatherSystem _weather = new DynamicWeatherSystem();

        private TerrainChunkManager? _terrainMgr;
        private WaterSurface? _waterSurface;
        private FloraManager? _floraMgr;
        private GpuGrassRing? _grassRing;
        private LocalWeatherVfx? _weatherVfx;
        private DirectionalLight3D? _sunLight;
        private ShaderMaterial? _skyShaderMat;
        private Environment? _worldEnv;
        private SpectatorCamera? _camera;
        private Label? _telemetryLabel;

        private Control? _worldMapOverlay;
        private TextureRect? _worldMapRect;
        private Control? _cameraPin;
        private Label? _mapLegendLabel;

        private ImageTexture[] _mapTextures = new ImageTexture[8];
        private float _radarRefreshAccum;
        private int _mapMode = 0;
        private int _seed = 2026;
        private bool _floraEnabled = true;
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

            _grassRing = new GpuGrassRing { Name = "GpuGrassRing" };
            AddChild(_grassRing);

            _weatherVfx = new LocalWeatherVfx { Name = "LocalWeatherVfx" };
            AddChild(_weatherVfx);

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

            var skyShader = GD.Load<Shader>("res://shaders/procedural_sky_clouds.gdshader");
            _skyShaderMat = new ShaderMaterial { Shader = skyShader };
            var sky = new Sky { SkyMaterial = _skyShaderMat };

            var env = new Environment
            {
                BackgroundMode = Environment.BGMode.Sky,
                Sky = sky,
                AmbientLightSource = Environment.AmbientSource.Sky,
                AmbientLightSkyContribution = 0.90f,
                AmbientLightEnergy = 1.25f,
                TonemapMode = Environment.ToneMapper.Agx,
                TonemapExposure = 1.05f,
                FogEnabled = true,
                FogMode = Environment.FogModeEnum.Depth,
                FogLightColor = horizonColor,
                FogDensity = 0.00045f,
                FogDepthBegin = 650.0f,
                FogDepthEnd = 13500.0f,
                FogAerialPerspective = 0.72f,
                SsaoEnabled = true,
                SsaoRadius = 2.4f,
                SsaoIntensity = 1.15f,
                SsilEnabled = false,
            };
            _worldEnv = env;

            AddChild(new WorldEnvironment { Name = "WorldEnvironment", Environment = env });

            var sun = new DirectionalLight3D
            {
                Name = "SunLight",
                LightColor = new Color(1.0f, 0.90f, 0.76f),
                LightEnergy = 1.95f,
                ShadowEnabled = true,
                ShadowBlur = 1.1f,
                DirectionalShadowMode = DirectionalLight3D.ShadowMode.Parallel4Splits,
                DirectionalShadowSplit1 = 0.04f,
                DirectionalShadowMaxDistance = 900.0f,
            };
            sun.RotationDegrees = new Vector3(-27.0f, -128.0f, 0.0f);
            AddChild(sun);
            _sunLight = sun;
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
                Text = "WASD: Bay/Đi | V: Góc nhìn Thú (0.85/1.65/3.6m) | 1-5: 5 Vùng | M: Bản đồ 8 lớp | F: Cây | Space: Dừng/Nhảy | [/]: Tốc độ | T:+3h | Y: Mùa | P: Thời tiết",
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
                Text = "BẢN ĐỒ PHÂN TÍCH VẬT LÝ & RADAR 9.6x5.4 KM (Click để bay tới | Phím 1-8 đổi lớp | M để đóng)",
                HorizontalAlignment = HorizontalAlignment.Center,
            };
            title.AddThemeFontSizeOverride("font_size", 13);
            vbox.AddChild(title);

            var modeRow = new HBoxContainer { Alignment = BoxContainer.AlignmentMode.Center };
            vbox.AddChild(modeRow);
            string[] modeNames =
            {
                "1. Địa hình",
                "2. Nhiệt độ",
                "3. Mưa & Gió",
                "4. Độ ẩm",
                "5. Thổ nhưỡng",
                "6. Độ dốc",
                "7. Thảo mộc",
                "8. Radar Bão"
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
                    5 => "Lớp 6: Độ dốc & Trầm tích Xói mòn (Kiểm tra Góc nghỉ Cát 32° vs Đất 40° vs Đá gốc 64°)",
                    6 => "Lớp 7: Hệ Sinh Thái & Tầng Tán Thảo Mộc (Đại ngàn xanh thẫm | Bạch quả/Phong vàng đỏ | Thông tuyết lam | Cọ ốc đảo ngọc)",
                    _ => "Lớp 8: Radar Thời Tiết & Tuyết Động 2 Hz (Mây bão trôi theo gió | Đẳng nhiệt 0°C xanh lơ | Tuyết phủ trắng)",
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
                ImageTexture canopyTex = _floraMgr.BuildFlora(_erosion, _hydrology, _climate, _soil, _seed);
                _terrainMgr?.SetCanopyCoverageTexture(canopyTex);
                if (_grassRing != null && _terrainMgr?.SoilATex != null && _terrainMgr.SoilBTex != null && _terrainMgr.ClimateTex != null && _floraMgr.WindDataTex != null)
                    _grassRing.BindWorldTextures(_erosion, _terrainMgr.SoilATex, _terrainMgr.SoilBTex, _terrainMgr.ClimateTex, canopyTex, _floraMgr.WindDataTex);
                _floraBuiltForSeed = true;
            }
            _floraMgr.Visible = _floraEnabled;
            if (_grassRing != null) _grassRing.Visible = _floraEnabled;
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
                ImageTexture emptyCov = _floraMgr.BuildEmptyCoverageTexture();
                _terrainMgr?.SetCanopyCoverageTexture(emptyCov);
                ImageTexture canopyTex = emptyCov;
                if (_floraEnabled)
                {
                    canopyTex = _floraMgr.BuildFlora(_erosion, _hydrology, _climate, _soil, seed);
                    _terrainMgr?.SetCanopyCoverageTexture(canopyTex);
                    _floraBuiltForSeed = true;
                }
                _floraMgr.Visible = _floraEnabled;

                if (_grassRing != null && _terrainMgr?.SoilATex != null && _terrainMgr.SoilBTex != null && _terrainMgr.ClimateTex != null && _floraMgr.WindDataTex != null)
                {
                    _grassRing.BindWorldTextures(_erosion, _terrainMgr.SoilATex, _terrainMgr.SoilBTex, _terrainMgr.ClimateTex, canopyTex, _floraMgr.WindDataTex);
                    _grassRing.Visible = _floraEnabled;
                }
            }

            _weather.Initialize(_erosion, _hydrology, _climate, _soil, seed);
            _weather.ForceImmediateStep(_clock);
            _camera?.AttachPhysics(_erosion, _hydrology, _soil);
            _terrainMgr?.SetWeatherTexture(_weather.WeatherDynamicTex);
            _waterSurface?.UpdateWeather(_weather.WeatherDynamicTex, _weather.SurfaceState.RiverSurgeOffset, _weather.GlobalWindGust);
            _floraMgr?.UpdateWeatherAndSeason(_weather.WeatherDynamicTex, _clock.SeasonPhase, _weather.GlobalWindGust);

            _mapTextures = WorldMapVisualizer.BuildAllModes(_tectonic, _erosion, _hydrology, _climate, _soil, _floraMgr?.Spawner, _weather);
            SetMapMode(_mapMode);

            if (_camera != null)
            {
                _terrainMgr?.UpdateLod(_camera.Position);
                if (_floraEnabled) _floraMgr?.UpdateStreaming(_camera.Position);
            }

            // Report comprehensive Stage 1+2+3 statistics
            int totalLand = System.Math.Max(1, _soil.TotalLandCells);
            GD.Print($"[World9.6x5.4km] Seed={seed} | PhysicsGen={physicsMs:0.0}ms | Temp=[{_climate.MinTempC:0.0}°C..{_climate.MaxTempC:0.0}°C] | MeanPrecip={_climate.MeanPrecip * 100f:0.0}% | " +
                     $"Chunks={_terrainMgr?.ChunkCount ?? 0} | ActiveTris={_terrainMgr?.ActiveTriangleEstimate ?? 0} | Soil%: " +
                     $"Alluvial={_soil.LandSoilCounts[0] * 100f / totalLand:0.0}%, " +
                     $"ForestBrown={_soil.LandSoilCounts[1] * 100f / totalLand:0.0}%, " +
                     $"SteppeLoess={_soil.LandSoilCounts[2] * 100f / totalLand:0.0}%, " +
                     $"AridRed={_soil.LandSoilCounts[3] * 100f / totalLand:0.0}%, " +
                     $"CoastalSand={_soil.LandSoilCounts[4] * 100f / totalLand:0.0}%, " +
                     $"Permafrost/Rock={_soil.LandSoilCounts[5] * 100f / totalLand:0.0}%");

            if (_floraMgr != null && _floraBuiltForSeed)
            {
                var spw = _floraMgr.Spawner;
                GD.Print($"[Flora6Layers] SpawnTime={spw.LastSpawnMs:0.0}ms | Total={spw.TotalInstances:N0} | " +
                         $"L1_Emergent={spw.LayerCounts[1]:N0}, L2_Canopy={spw.LayerCounts[2]:N0}, L3_Understory={spw.LayerCounts[3]:N0}, " +
                         $"L4_Shrub={spw.LayerCounts[4]:N0}, L5_Herb={spw.LayerCounts[5]:N0}, L6_Litter={spw.LayerCounts[6]:N0}");
                GD.Print($"[Flora4StemGroups] WoodyBranching={spw.StemGroupCounts[0]:N0} | DwarfWoodyShrub={spw.StemGroupCounts[1]:N0} | " +
                         $"ColumnarCaudexCulm={spw.StemGroupCounts[2]:N0} | HerbaceousGround={spw.StemGroupCounts[3]:N0}");
                var parts = new System.Text.StringBuilder("[FloraSpecies] ");
                for (int s = 0; s < FloraNicheDatabase.AllSpecies.Length; s++)
                {
                    if (spw.SpeciesCounts[s] > 0)
                        parts.Append($"{FloraNicheDatabase.AllSpecies[s].SpeciesKey}={spw.SpeciesCounts[s]:N0} | ");
                }
                GD.Print(parts.ToString());
            }

            float sumTempMin = _climate.MinTempC + 9.5f - 5.5f;
            float sumTempMax = _climate.MaxTempC + 9.5f + 5.5f;
            float winTempMin = _climate.MinTempC - 9.5f - 5.5f;
            float winTempMax = _climate.MaxTempC - 9.5f + 5.5f;
            GD.Print($"[Weather4D] Grid=256x144 (2Hz) | UpdateTime={_weather.LastUpdateMs:0.00}ms | " +
                     $"SummerRange=[{sumTempMin:0.0}°C..{sumTempMax:0.0}°C] | WinterRange=[{winTempMin:0.0}°C..{winTempMax:0.0}°C] | " +
                     $"SnowCover={_weather.SurfaceState.MeanSnowPercent:0.0}% | RiverSurge=+{_weather.SurfaceState.RiverSurgeOffset:0.00}m");
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
                        else TeleportCloseToGround(2420.0f, 1180.0f, 38.0f, new Vector3(2360.0f, 180.0f, 920.0f)); // NW Alpine & Krummholz
                        break;
                    case Key.Key2:
                        if (_worldMapOverlay?.Visible == true) SetMapMode(1);
                        else TeleportCloseToGround(2220.0f, 3550.0f, 26.0f, new Vector3(2150.0f, 20.0f, 3420.0f)); // SW Red Desert & Oasis Palms
                        break;
                    case Key.Key3:
                        if (_worldMapOverlay?.Visible == true) SetMapMode(2);
                        else TeleportCloseToGround(6350.0f, 3420.0f, 24.0f, new Vector3(6420.0f, 28.0f, 3260.0f)); // East Primeval Forest Edge & River
                        break;
                    case Key.Key4:
                        if (_worldMapOverlay?.Visible == true) SetMapMode(3);
                        else TeleportCloseToGround(6780.0f, 1620.0f, 28.0f, new Vector3(6680.0f, 52.0f, 1480.0f)); // NE Autumn Steppes
                        break;
                    case Key.Key5:
                        if (_worldMapOverlay?.Visible == true) SetMapMode(4);
                        else TeleportCloseToGround(8580.0f, 4540.0f, 22.0f, new Vector3(8660.0f, 16.0f, 4420.0f)); // SE Sanctuary Wetland & Nipa Palms
                        break;
                    case Key.Key6:
                        if (_worldMapOverlay?.Visible == true) SetMapMode(5);
                        break;
                    case Key.Key7:
                        if (_worldMapOverlay?.Visible == true) SetMapMode(6);
                        break;
                    case Key.Key8:
                        if (_worldMapOverlay?.Visible == true) SetMapMode(7);
                        break;
                    case Key.Space:
                        if (_camera == null || !_camera.IsAnimalPov)
                            _clock.TogglePause();
                        break;
                    case Key.Bracketleft:
                        _clock.StepSpeed(-1);
                        break;
                    case Key.Bracketright:
                        _clock.StepSpeed(1);
                        break;
                    case Key.T:
                        _clock.AddHours(3.0f);
                        _weather.ForceImmediateStep(_clock);
                        break;
                    case Key.Y:
                        _clock.AdvanceToNextSeason();
                        _weather.ForceImmediateStep(_clock);
                        break;
                    case Key.P:
                        _weather.OverrideMode = (WeatherOverrideMode)(((int)_weather.OverrideMode + 1) % 4);
                        _weather.ForceImmediateStep(_clock);
                        break;
                }
            }
        }

        public override void _Process(double delta)
        {
            float dt = (float)delta;
            _clock.Advance(dt);
            _weather.Update(dt, _clock);

            _waterSurface?.UpdateWeather(_weather.WeatherDynamicTex, _weather.SurfaceState.RiverSurgeOffset, _weather.GlobalWindGust);
            _floraMgr?.UpdateWeatherAndSeason(_weather.WeatherDynamicTex, _clock.SeasonPhase, _weather.GlobalWindGust);

            if (_camera != null)
            {
                _terrainMgr?.UpdateLod(_camera.Position);
                if (_floraEnabled)
                {
                    _floraMgr?.UpdateStreaming(_camera.Position);
                    _grassRing?.UpdateDynamicState(_camera.Position, _weather.WeatherDynamicTex, _clock.SeasonPhase, _weather.GlobalWindGust);
                }

                LiveWeatherSample liveW = _weather.SampleAt(_camera.Position.X, _camera.Position.Z);
                _weatherVfx?.UpdateForCamera(_camera.Position, liveW);
                UpdateSkyAndLighting(liveW);

                if (_telemetryLabel != null)
                {
                    Vector3 p = _camera.Position;
                    float h = _erosion.SampleHeight(p.X, p.Z);
                    float slope = _erosion.SampleSlopeDeg(p.X, p.Z);
                    SoilSample ss = _soil.SampleSoil(p.X, p.Z);
                    int tris = _terrainMgr?.ActiveTriangleEstimate ?? 0;
                    string domSp = _floraEnabled && _floraMgr != null ? _floraMgr.GetDominantSpeciesNameAt(p.X, p.Z) : "Tắt";
                    string floraStr = _floraEnabled
                        ? $"Cây: {_floraMgr?.TotalInstanceCount ?? 0:N0} (Hiện: {_floraMgr?.VisibleInstanceCount ?? 0:N0}) | Loài: {domSp}"
                        : "Cây: Tắt [F]";

                    int hh = (int)_clock.TimeOfDay;
                    int mm = (int)((_clock.TimeOfDay - hh) * 60.0f);
                    string speedStr = _clock.IsPaused ? "Dừng" : $"x{_clock.SpeedMultiplier:0}";
                    string warnStr = string.IsNullOrEmpty(_camera.MovementWarning) ? "" : $" | [!] {_camera.MovementWarning}";

                    _telemetryLabel.Text =
                        $"Primeval Reach 9.6x5.4 km | FPS: {Engine.GetFramesPerSecond():0} | Tris: {tris:N0} | Góc nhìn [V]: {_camera.PovLabel}{warnStr}\n" +
                        $"Ngày {_clock.DayOfYear + 1} | Mùa {_clock.SeasonNameVi} | {hh:00}:{mm:00} ({speedStr}) | {liveW.ConditionLabel} | Nhiệt: {liveW.LiveTempC:0.0}°C | Tuyết: {liveW.SnowAccum * 100f:0}% | Ẩm mặt: {liveW.Wetness * 100f:0}% | {floraStr}\n" +
                        $"Cao độ: {h:0.0}m | Dốc: {slope:0.0}° | Gió: {liveW.LiveWindSpeed:0.0}m/s | Mây: {liveW.CloudCover * 100f:0}% | Đất: {FormatSoil(ss.DominantSoil)}";
                }
            }

            if (_worldMapOverlay != null && _worldMapOverlay.Visible)
            {
                UpdateCameraPin();
                if (_mapMode == 7 && _mapTextures[7] != null)
                {
                    _radarRefreshAccum += dt;
                    if (_radarRefreshAccum >= 0.5f)
                    {
                        _radarRefreshAccum = 0.0f;
                        WorldMapVisualizer.RefreshWeatherRadarMap(_mapTextures[7], _erosion, _weather);
                    }
                }
            }
        }

        private void UpdateSkyAndLighting(in LiveWeatherSample liveW)
        {
            if (_sunLight == null || _skyShaderMat == null || _worldEnv == null) return;

            Vector3 sunDir = _clock.SunDirection;
            float elev = Mathf.Clamp(sunDir.Y, -1.0f, 1.0f);
            float dayT = Mathf.Clamp((elev + 0.08f) / 0.35f, 0.0f, 1.0f);
            float goldenT = Mathf.Clamp(1.0f - Mathf.Abs(elev - 0.12f) / 0.22f, 0.0f, 1.0f);
            float cloudDim = 1.0f - liveW.CloudCover * 0.45f;

            Vector3 activeDir = elev > 0.0f ? sunDir : new Vector3(-sunDir.X, Mathf.Max(0.22f, -sunDir.Y), -sunDir.Z).Normalized();
            _sunLight.LookAtFromPosition(activeDir * 100.0f, Vector3.Zero, Vector3.Up);
            _sunLight.DirectionalShadowMaxDistance = (_camera != null && _camera.IsAnimalPov) ? 260.0f : 900.0f;

            Color dayCol = new Color(1.0f, 0.94f, 0.86f);
            Color goldenCol = new Color(1.0f, 0.64f, 0.34f);
            Color moonCol = new Color(0.56f, 0.70f, 0.94f);
            _sunLight.LightColor = moonCol.Lerp(dayCol.Lerp(goldenCol, goldenT * 0.65f), dayT);
            _sunLight.LightEnergy = Mathf.Lerp(0.45f, 2.05f * cloudDim, dayT);

            _skyShaderMat.SetShaderParameter("sun_direction", sunDir);
            _skyShaderMat.SetShaderParameter("day_t", dayT);
            _skyShaderMat.SetShaderParameter("golden_t", goldenT);
            _skyShaderMat.SetShaderParameter("cloud_cover", liveW.CloudCover);

            Color dayHorizon = new Color(0.60f, 0.74f, 0.86f);
            Color goldenHorizon = new Color(0.90f, 0.56f, 0.34f);
            Color nightHorizon = new Color(0.08f, 0.13f, 0.22f);
            Color horizon = nightHorizon.Lerp(dayHorizon.Lerp(goldenHorizon, goldenT * 0.70f), dayT)
                                        .Lerp(new Color(0.48f, 0.52f, 0.56f), liveW.CloudCover * 0.50f);

            _worldEnv.FogLightColor = horizon;
            _worldEnv.FogDensity = 0.00045f + liveW.RainIntensity * 0.0014f + (liveW.ConditionLabel == "Bão cát đỏ" ? 0.0018f : 0.0f);
            _worldEnv.AmbientLightSkyContribution = Mathf.Lerp(0.85f, 0.92f, dayT);
        }

        private void TeleportCloseToGround(float wx, float wz, float heightAboveGround, Vector3 lookTarget)
        {
            float groundH = Mathf.Max(2.0f, _erosion.SampleHeight(wx, wz));
            _camera?.TeleportTo(new Vector3(wx, groundH + heightAboveGround, wz), new Vector3(lookTarget.X, groundH + 4.0f, lookTarget.Z));
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
