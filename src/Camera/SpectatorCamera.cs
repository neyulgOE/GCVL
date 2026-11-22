using Godot;

namespace PrimevalWorld.Camera
{
    /// <summary>
    /// Smooth spectator Free Camera:
    /// WASD move, Q/E down/up, Shift boost, Right-mouse drag look, Scroll wheel adjusts fly speed.
    /// </summary>
    public partial class SpectatorCamera : Camera3D
    {
        [Export] public float BaseSpeed = 55.0f;
        [Export] public float BoostMultiplier = 2.8f;
        [Export] public float LookSensitivity = 0.0045f;

        private float _yaw;
        private float _pitch;
        private bool _rotating;
        private Vector3 _velocity = Vector3.Zero;

        public float CurrentSpeed => BaseSpeed;

        public override void _Ready()
        {
            ResetToScenicOverlook();
        }

        public void ResetToScenicOverlook()
        {
            // Scenic overlook looking across the meandering river valley toward the northern alpine peaks
            Position = new Vector3(310.0f, 78.0f, 820.0f);
            LookAt(new Vector3(540.0f, 18.0f, 320.0f), Vector3.Up);
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
                    BaseSpeed = Mathf.Clamp(BaseSpeed * 1.15f, 10.0f, 300.0f);
                }
                else if (mb.Pressed && mb.ButtonIndex == MouseButton.WheelDown)
                {
                    BaseSpeed = Mathf.Clamp(BaseSpeed / 1.15f, 10.0f, 300.0f);
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

            float targetSpeed = BaseSpeed * (Input.IsKeyPressed(Key.Shift) ? BoostMultiplier : 1.0f);
            Vector3 targetVel = inputDir.LengthSquared() > 0.001f ? inputDir.Normalized() * targetSpeed : Vector3.Zero;

            _velocity = _velocity.Lerp(targetVel, 1.0f - Mathf.Exp(-10.0f * dt));
            Position += _velocity * dt;

            // Keep camera slightly above minimum ocean floor
            Position = new Vector3(
                Mathf.Clamp(Position.X, -150.0f, 1174.0f),
                Mathf.Clamp(Position.Y, 1.5f, 450.0f),
                Mathf.Clamp(Position.Z, -150.0f, 1174.0f)
            );
        }
    }
}
