using Godot;
using PrimevalWorld.Core;

namespace PrimevalWorld.Camera
{
    /// <summary>
    /// Smooth spectator Free Camera for the 9.6 x 5.4 km world:
    /// Far = 16,000m, max speed up to 1,000 m/s (Shift + Scroll wheel).
    /// </summary>
    public partial class SpectatorCamera : Camera3D
    {
        [Export] public float BaseSpeed = 160.0f;
        [Export] public float BoostMultiplier = 3.2f;
        [Export] public float LookSensitivity = 0.0045f;

        private float _yaw;
        private float _pitch;
        private bool _rotating;
        private Vector3 _velocity = Vector3.Zero;

        public float CurrentSpeed => BaseSpeed;

        public override void _Ready()
        {
            Far = WorldPhysicsConfig.CameraFar;
            ResetToScenicOverlook();
        }

        public void ResetToScenicOverlook()
        {
            // North (-Z: NW Glacial & NE Autumn) at top of screen; South (+Z: SW Desert & SE Sanctuary) at bottom
            TeleportTo(new Vector3(4800.0f, 2400.0f, 6500.0f), new Vector3(4800.0f, 40.0f, 2650.0f));
        }

        public void TeleportTo(Vector3 pos, Vector3 lookTarget)
        {
            Position = pos;
            LookAt(lookTarget, Vector3.Up);
            Vector3 rot = Rotation;
            _pitch = rot.X;
            _yaw = rot.Y;
            _velocity = Vector3.Zero;
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
                else if (mb.Pressed && mb.ButtonIndex == MouseButton.WheelUp)
                {
                    BaseSpeed = Mathf.Clamp(BaseSpeed * 1.18f, 15.0f, WorldPhysicsConfig.MaxFlySpeed);
                }
                else if (mb.Pressed && mb.ButtonIndex == MouseButton.WheelDown)
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
            Vector3 inputDir = Vector3.Zero;

            Basis basis = GlobalTransform.Basis;
            Vector3 forward = -basis.Z;
            Vector3 right = basis.X;

            if (Input.IsKeyPressed(Key.W) || Input.IsKeyPressed(Key.Up)) inputDir += forward;
            if (Input.IsKeyPressed(Key.S) || Input.IsKeyPressed(Key.Down)) inputDir -= forward;
            if (Input.IsKeyPressed(Key.D) || Input.IsKeyPressed(Key.Right)) inputDir += right;
            if (Input.IsKeyPressed(Key.A) || Input.IsKeyPressed(Key.Left)) inputDir -= right;
            if (Input.IsKeyPressed(Key.E) || Input.IsKeyPressed(Key.Space)) inputDir += Vector3.Up;
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
    }
}
