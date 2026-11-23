using System;
using Godot;
using PrimevalWorld.Core;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Camera
{
    public enum CameraPovMode : byte
    {
        FreeFly = 0,
        PredatorWolf = 1,   // 0.85m
        PrehistoricBison = 2, // 1.65m
        WoollyMammoth = 3,  // 3.60m
    }

    /// <summary>
    /// Spectator Free Camera + 3-tier Ground-Hugging Animal POV Test Camera [V]:
    /// [0] Free Fly (max 1000 m/s), [1] Wolf/Predator (0.85m), [2] Bison (1.65m), [3] Mammoth (3.60m).
    /// Samples bilinear terrain height, slope limits, soil friction, and water depth directly from physics grids.
    /// </summary>
    public partial class SpectatorCamera : Camera3D
    {
        [Export] public float BaseSpeed = 160.0f;
        [Export] public float BoostMultiplier = 3.2f;
        [Export] public float LookSensitivity = 0.0045f;

        private ErosionPhysics? _erosion;
        private HydrologySolver? _hydrology;
        private SoilPedology? _soil;

        private float _yaw;
        private float _pitch;
        private bool _rotating;
        private Vector3 _velocity = Vector3.Zero;

        private CameraPovMode _povMode = CameraPovMode.FreeFly;
        private float _bobPhase;
        private float _verticalVel;
        private float _jumpOffset;
        private bool _isGrounded = true;

        public CameraPovMode PovMode => _povMode;
        public bool IsAnimalPov => _povMode != CameraPovMode.FreeFly;
        public float CurrentSpeed => BaseSpeed;
        public string MovementWarning { get; private set; } = "";

        public string PovLabel => _povMode switch
        {
            CameraPovMode.PredatorWolf => "Sói (0.85m)",
            CameraPovMode.PrehistoricBison => "Bò Rừng (1.65m)",
            CameraPovMode.WoollyMammoth => "Voi Ma Mút (3.60m)",
            _ => "Tự do",
        };

        public void AttachPhysics(ErosionPhysics erosion, HydrologySolver hydrology, SoilPedology soil)
        {
            _erosion = erosion;
            _hydrology = hydrology;
            _soil = soil;
        }

        public override void _Ready()
        {
            Far = WorldPhysicsConfig.CameraFar;
            Near = 0.5f;
            ResetToScenicOverlook();
        }

        public void ResetToScenicOverlook()
        {
            SetPovMode(CameraPovMode.FreeFly);
            TeleportTo(new Vector3(4800.0f, 2400.0f, 6500.0f), new Vector3(4800.0f, 40.0f, 2650.0f));
        }

        public void CyclePovMode()
        {
            SetPovMode((CameraPovMode)(((int)_povMode + 1) % 4));
        }

        public void SetPovMode(CameraPovMode mode)
        {
            _povMode = mode;
            _velocity = Vector3.Zero;
            _jumpOffset = 0.0f;
            _verticalVel = 0.0f;
            _isGrounded = true;
            MovementWarning = "";

            switch (mode)
            {
                case CameraPovMode.PredatorWolf:
                    Fov = 82.0f;
                    Near = 0.08f;
                    break;
                case CameraPovMode.PrehistoricBison:
                    Fov = 75.0f;
                    Near = 0.08f;
                    break;
                case CameraPovMode.WoollyMammoth:
                    Fov = 68.0f;
                    Near = 0.08f;
                    break;
                default:
                    Fov = 75.0f;
                    Near = 0.5f;
                    break;
            }

            if (mode != CameraPovMode.FreeFly)
            {
                float wx = Mathf.Clamp(Position.X, 15.0f, WorldPhysicsConfig.WorldWidth - 15.0f);
                float wz = Mathf.Clamp(Position.Z, 15.0f, WorldPhysicsConfig.WorldDepth - 15.0f);
                float h = _erosion?.SampleHeight(wx, wz) ?? 10.0f;
                Position = new Vector3(wx, MathF.Max(h, 0.0f) + GetEyeHeight(), wz);
                // Level pitch slightly when dropping down to eye level
                _pitch = Mathf.Clamp(_pitch, Mathf.DegToRad(-25.0f), Mathf.DegToRad(25.0f));
                Rotation = new Vector3(_pitch, _yaw, 0.0f);
            }
        }

        public void TeleportTo(Vector3 pos, Vector3 lookTarget)
        {
            Position = pos;
            LookAt(lookTarget, Vector3.Up);
            Vector3 rot = Rotation;
            _pitch = rot.X;
            _yaw = rot.Y;
            _velocity = Vector3.Zero;
            _jumpOffset = 0.0f;
            _verticalVel = 0.0f;
        }

        public override void _UnhandledInput(InputEvent @event)
        {
            if (@event is InputEventMouseButton mb)
            {
                if (mb.ButtonIndex == MouseButton.Right)
                {
                    _rotating = mb.Pressed;
                    Input.MouseMode = _rotating ? Input.MouseModeEnum.Captured : Input.MouseModeEnum.Visible;
                }
                else if (mb.Pressed && mb.ButtonIndex == MouseButton.WheelUp && _povMode == CameraPovMode.FreeFly)
                {
                    BaseSpeed = Mathf.Clamp(BaseSpeed * 1.18f, 15.0f, WorldPhysicsConfig.MaxFlySpeed);
                }
                else if (mb.Pressed && mb.ButtonIndex == MouseButton.WheelDown && _povMode == CameraPovMode.FreeFly)
                {
                    BaseSpeed = Mathf.Clamp(BaseSpeed / 1.18f, 15.0f, WorldPhysicsConfig.MaxFlySpeed);
                }
            }
            else if (@event is InputEventMouseMotion mm && _rotating)
            {
                _yaw -= mm.Relative.X * LookSensitivity;
                _pitch = Mathf.Clamp(_pitch - mm.Relative.Y * LookSensitivity, Mathf.DegToRad(-85.0f), Mathf.DegToRad(80.0f));
                Rotation = new Vector3(_pitch, _yaw, 0.0f);
            }
            else if (@event is InputEventKey key && key.Pressed && !key.Echo)
            {
                if (key.Keycode == Key.R)
                {
                    ResetToScenicOverlook();
                }
                else if (key.Keycode == Key.V)
                {
                    CyclePovMode();
                }
                else if (key.Keycode == Key.Space && IsAnimalPov && _isGrounded && _povMode != CameraPovMode.WoollyMammoth)
                {
                    _verticalVel = _povMode == CameraPovMode.PredatorWolf ? 6.2f : 4.8f;
                    _isGrounded = false;
                }
                else if (key.Keycode == Key.Escape)
                {
                    if (_rotating)
                    {
                        _rotating = false;
                        Input.MouseMode = Input.MouseModeEnum.Visible;
                    }
                    else
                    {
                        GetTree().Quit();
                    }
                }
            }
        }

        public override void _Process(double delta)
        {
            float dt = (float)delta;
            if (_povMode == CameraPovMode.FreeFly)
                ProcessFreeFly(dt);
            else
                ProcessAnimalPov(dt);
        }

        private void ProcessFreeFly(float dt)
        {
            MovementWarning = "";
            Vector3 inputDir = Vector3.Zero;
            Basis basis = GlobalTransform.Basis;
            Vector3 forward = -basis.Z;
            Vector3 right = basis.X;

            if (Input.IsKeyPressed(Key.W) || Input.IsKeyPressed(Key.Up)) inputDir += forward;
            if (Input.IsKeyPressed(Key.S) || Input.IsKeyPressed(Key.Down)) inputDir -= forward;
            if (Input.IsKeyPressed(Key.D) || Input.IsKeyPressed(Key.Right)) inputDir += right;
            if (Input.IsKeyPressed(Key.A) || Input.IsKeyPressed(Key.Left)) inputDir -= right;
            if (Input.IsKeyPressed(Key.E)) inputDir += Vector3.Up;
            if (Input.IsKeyPressed(Key.Q) || Input.IsKeyPressed(Key.C)) inputDir -= Vector3.Up;

            float targetSpeed = Mathf.Min(
                WorldPhysicsConfig.MaxFlySpeed,
                BaseSpeed * (Input.IsKeyPressed(Key.Shift) ? BoostMultiplier : 1.0f)
            );
            Vector3 targetVel = inputDir.LengthSquared() > 0.001f ? inputDir.Normalized() * targetSpeed : Vector3.Zero;

            _velocity = _velocity.Lerp(targetVel, 1.0f - Mathf.Exp(-10.0f * dt));
            Position += _velocity * dt;

            Position = new Vector3(
                Mathf.Clamp(Position.X, -2500.0f, WorldPhysicsConfig.WorldWidth + 2500.0f),
                Mathf.Clamp(Position.Y, 1.5f, 3500.0f),
                Mathf.Clamp(Position.Z, -2500.0f, WorldPhysicsConfig.WorldDepth + 2500.0f)
            );
        }

        private void ProcessAnimalPov(float dt)
        {
            if (_erosion == null) return;

            float eyeH = GetEyeHeight();
            GetAnimalStats(out float walkSpd, out float sprintSpd, out float maxSlope, out float bobFreq, out float bobAmp);

            Basis basis = GlobalTransform.Basis;
            Vector3 flatForward = new Vector3(-basis.Z.X, 0.0f, -basis.Z.Z).Normalized();
            Vector3 flatRight = new Vector3(basis.X.X, 0.0f, basis.X.Z).Normalized();

            Vector3 moveDir = Vector3.Zero;
            if (Input.IsKeyPressed(Key.W) || Input.IsKeyPressed(Key.Up)) moveDir += flatForward;
            if (Input.IsKeyPressed(Key.S) || Input.IsKeyPressed(Key.Down)) moveDir -= flatForward;
            if (Input.IsKeyPressed(Key.D) || Input.IsKeyPressed(Key.Right)) moveDir += flatRight;
            if (Input.IsKeyPressed(Key.A) || Input.IsKeyPressed(Key.Left)) moveDir -= flatRight;

            float baseMoveSpd = Input.IsKeyPressed(Key.Shift) ? sprintSpd : walkSpd;

            // Terrain response at current position
            float curH = _erosion.SampleHeight(Position.X, Position.Z);
            float curSlope = _erosion.SampleSlopeDeg(Position.X, Position.Z);
            float curWaterDepth = SampleWaterDepth(Position.X, Position.Z, curH);

            float terrainMult = 1.0f - Mathf.Clamp(curSlope / maxSlope, 0.0f, 1.0f) * 0.42f;
            if (curWaterDepth > 0.20f)
                terrainMult *= 0.62f;
            else if (_soil != null)
            {
                SoilSample ss = _soil.SampleSoil(Position.X, Position.Z);
                if (ss.WAridRed > 0.45f || ss.WCoastalSand > 0.45f)
                    terrainMult *= 0.82f; // Loose sand drag
            }

            Vector3 horizVel = moveDir.LengthSquared() > 0.001f
                ? moveDir.Normalized() * (baseMoveSpd * terrainMult)
                : Vector3.Zero;

            MovementWarning = "";
            float nextX = Mathf.Clamp(Position.X + horizVel.X * dt, 10.0f, WorldPhysicsConfig.WorldWidth - 10.0f);
            float nextZ = Mathf.Clamp(Position.Z + horizVel.Z * dt, 10.0f, WorldPhysicsConfig.WorldDepth - 10.0f);

            bool canMoveFull = CanStepTo(nextX, nextZ, curH, maxSlope, eyeH, out string warnFull);
            if (!canMoveFull && horizVel.LengthSquared() > 0.001f)
            {
                // Slide along X or Z if blocked
                bool canX = CanStepTo(nextX, Position.Z, curH, maxSlope, eyeH, out _);
                bool canZ = CanStepTo(Position.X, nextZ, curH, maxSlope, eyeH, out _);
                if (canX) nextZ = Position.Z;
                else if (canZ) nextX = Position.X;
                else { nextX = Position.X; nextZ = Position.Z; }
                MovementWarning = warnFull;
            }

            // Simple jump gravity
            if (!_isGrounded)
            {
                _verticalVel -= 18.0f * dt;
                _jumpOffset += _verticalVel * dt;
                if (_jumpOffset <= 0.0f)
                {
                    _jumpOffset = 0.0f;
                    _verticalVel = 0.0f;
                    _isGrounded = true;
                }
            }

            float finalGroundH = _erosion.SampleHeight(nextX, nextZ);
            float actualMove = new Vector2(nextX - Position.X, nextZ - Position.Z).Length();
            if (actualMove > 0.002f && _isGrounded)
                _bobPhase += actualMove * (bobFreq / MathF.Max(1.0f, walkSpd));

            float bobOffset = _isGrounded && actualMove > 0.002f ? MathF.Sin(_bobPhase) * bobAmp : 0.0f;
            float targetY = finalGroundH + eyeH + _jumpOffset + bobOffset;
            float smoothY = Mathf.Lerp(Position.Y, targetY, 1.0f - Mathf.Exp(-24.0f * dt));
            Position = new Vector3(nextX, smoothY, nextZ);
        }

        private bool CanStepTo(float x, float z, float curH, float maxSlope, float eyeH, out string warning)
        {
            warning = "";
            if (_erosion == null) return true;

            float nextH = _erosion.SampleHeight(x, z);
            float nextSlope = _erosion.SampleSlopeDeg(x, z);
            if (nextSlope > maxSlope && nextH > curH)
            {
                warning = $"Chặn: Vách quá dốc (>{maxSlope:0}°)";
                return false;
            }

            float waterDepth = SampleWaterDepth(x, z, nextH);
            if (waterDepth > eyeH * 0.60f)
            {
                warning = $"Chặn: Nước quá sâu (>{eyeH * 0.60f:0.0}m)";
                return false;
            }

            return true;
        }

        private float SampleWaterDepth(float wx, float wz, float groundH)
        {
            if (groundH < 0.0f) return -groundH;
            if (_hydrology != null)
            {
                int gx = Math.Clamp((int)(wx / WorldPhysicsConfig.CellSize), 0, WorldPhysicsConfig.VertW - 1);
                int gz = Math.Clamp((int)(wz / WorldPhysicsConfig.CellSize), 0, WorldPhysicsConfig.VertH - 1);
                int idx = gz * WorldPhysicsConfig.VertW + gx;
                if (_hydrology.HasInlandWater[idx])
                    return MathF.Max(0.0f, _hydrology.InlandWaterY[idx] - groundH);
            }
            return 0.0f;
        }

        private float GetEyeHeight() => _povMode switch
        {
            CameraPovMode.PredatorWolf => 0.85f,
            CameraPovMode.PrehistoricBison => 1.65f,
            CameraPovMode.WoollyMammoth => 3.60f,
            _ => 1.65f,
        };

        private void GetAnimalStats(out float walkSpd, out float sprintSpd, out float maxSlope, out float bobFreq, out float bobAmp)
        {
            switch (_povMode)
            {
                case CameraPovMode.PredatorWolf:
                    walkSpd = 7.0f; sprintSpd = 16.0f; maxSlope = 42.0f; bobFreq = 9.5f; bobAmp = 0.055f;
                    break;
                case CameraPovMode.PrehistoricBison:
                    walkSpd = 5.5f; sprintSpd = 12.0f; maxSlope = 36.0f; bobFreq = 7.0f; bobAmp = 0.070f;
                    break;
                default: // WoollyMammoth
                    walkSpd = 4.2f; sprintSpd = 8.5f; maxSlope = 28.0f; bobFreq = 4.5f; bobAmp = 0.110f;
                    break;
            }
        }
    }
}
