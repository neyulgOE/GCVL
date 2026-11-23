using System;
using Godot;

namespace PrimevalWorld.Weather
{
    /// <summary>
    /// Stage 4: Camera-attached Local Weather VFX (Rain, Snow, Red Sandstorm) using lightweight GPUParticles3D.
    /// Automatically switches active particle emitters based on LiveWeatherSample at camera coordinates.
    /// </summary>
    public partial class LocalWeatherVfx : Node3D
    {
        private GpuParticles3D? _rainParticles;
        private GpuParticles3D? _snowParticles;
        private GpuParticles3D? _sandParticles;

        private ParticleProcessMaterial? _rainMat;
        private ParticleProcessMaterial? _snowMat;
        private ParticleProcessMaterial? _sandMat;

        public override void _Ready()
        {
            BuildEmitters();
        }

        private void BuildEmitters()
        {
            // 1. Rain Streaks
            _rainMat = new ParticleProcessMaterial
            {
                EmissionShape = ParticleProcessMaterial.EmissionShapeEnum.Box,
                EmissionBoxExtents = new Vector3(55.0f, 12.0f, 55.0f),
                Direction = new Vector3(0.2f, -1.0f, 0.1f),
                InitialVelocityMin = 24.0f,
                InitialVelocityMax = 32.0f,
                Gravity = new Vector3(0.0f, -18.0f, 0.0f),
                ScaleMin = 0.8f,
                ScaleMax = 1.2f,
            };
            var rainMesh = new BoxMesh { Size = new Vector3(0.06f, 2.2f, 0.06f) };
            var rainStdMat = new StandardMaterial3D
            {
                AlbedoColor = new Color(0.75f, 0.85f, 0.98f, 0.55f),
                Transparency = BaseMaterial3D.TransparencyEnum.Alpha,
                ShadingMode = BaseMaterial3D.ShadingModeEnum.Unshaded,
            };
            rainMesh.Material = rainStdMat;
            _rainParticles = new GpuParticles3D
            {
                Name = "LocalRain",
                Amount = 1400,
                Lifetime = 1.1f,
                ProcessMaterial = _rainMat,
                DrawPass1 = rainMesh,
                Emitting = false,
                CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
            };
            AddChild(_rainParticles);

            // 2. Snow Flakes
            _snowMat = new ParticleProcessMaterial
            {
                EmissionShape = ParticleProcessMaterial.EmissionShapeEnum.Box,
                EmissionBoxExtents = new Vector3(55.0f, 14.0f, 55.0f),
                Direction = new Vector3(0.4f, -1.0f, 0.2f),
                InitialVelocityMin = 4.0f,
                InitialVelocityMax = 8.0f,
                Gravity = new Vector3(0.0f, -1.8f, 0.0f),
                TurbulenceEnabled = true,
                TurbulenceNoiseStrength = 2.5f,
            };
            var snowMesh = new BoxMesh { Size = new Vector3(0.22f, 0.22f, 0.22f) };
            var snowStdMat = new StandardMaterial3D
            {
                AlbedoColor = new Color(0.95f, 0.97f, 1.0f, 0.82f),
                Transparency = BaseMaterial3D.TransparencyEnum.Alpha,
                ShadingMode = BaseMaterial3D.ShadingModeEnum.Unshaded,
            };
            snowMesh.Material = snowStdMat;
            _snowParticles = new GpuParticles3D
            {
                Name = "LocalSnow",
                Amount = 1100,
                Lifetime = 3.2f,
                ProcessMaterial = _snowMat,
                DrawPass1 = snowMesh,
                Emitting = false,
                CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
            };
            AddChild(_snowParticles);

            // 3. Red Desert Sandstorm
            _sandMat = new ParticleProcessMaterial
            {
                EmissionShape = ParticleProcessMaterial.EmissionShapeEnum.Box,
                EmissionBoxExtents = new Vector3(55.0f, 14.0f, 55.0f),
                Direction = new Vector3(1.0f, -0.05f, 0.5f),
                InitialVelocityMin = 14.0f,
                InitialVelocityMax = 24.0f,
                Gravity = new Vector3(0.0f, -0.4f, 0.0f),
            };
            var sandMesh = new BoxMesh { Size = new Vector3(0.45f, 0.14f, 0.45f) };
            var sandStdMat = new StandardMaterial3D
            {
                AlbedoColor = new Color(0.84f, 0.44f, 0.22f, 0.42f),
                Transparency = BaseMaterial3D.TransparencyEnum.Alpha,
                ShadingMode = BaseMaterial3D.ShadingModeEnum.Unshaded,
            };
            sandMesh.Material = sandStdMat;
            _sandParticles = new GpuParticles3D
            {
                Name = "LocalSandstorm",
                Amount = 900,
                Lifetime = 1.8f,
                ProcessMaterial = _sandMat,
                DrawPass1 = sandMesh,
                Emitting = false,
                CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
            };
            AddChild(_sandParticles);
        }

        public void UpdateForCamera(Vector3 camPos, in LiveWeatherSample sample)
        {
            Position = new Vector3(camPos.X, camPos.Y + 18.0f, camPos.Z);

            bool isRain = sample.RainIntensity > 0.10f && sample.LiveTempC > 0.5f;
            bool isSnow = sample.RainIntensity > 0.10f && sample.LiveTempC <= 0.5f;
            bool isSand = sample.ConditionLabel == "Bão cát đỏ";

            Vector3 windSlant = new Vector3(sample.WindDir.X * sample.LiveWindSpeed * 0.45f, -26.0f, sample.WindDir.Y * sample.LiveWindSpeed * 0.45f);
            if (_rainMat != null) _rainMat.Direction = windSlant.Normalized();
            if (_snowMat != null) _snowMat.Direction = new Vector3(sample.WindDir.X * sample.LiveWindSpeed * 0.3f, -5.0f, sample.WindDir.Y * sample.LiveWindSpeed * 0.3f).Normalized();
            if (_sandMat != null) _sandMat.Direction = new Vector3(sample.WindDir.X, -0.05f, sample.WindDir.Y).Normalized();

            if (_rainParticles != null)
            {
                _rainParticles.Emitting = isRain;
                _rainParticles.AmountRatio = Math.Clamp(sample.RainIntensity * 1.2f, 0.15f, 1.0f);
            }
            if (_snowParticles != null)
            {
                _snowParticles.Emitting = isSnow;
                _snowParticles.AmountRatio = Math.Clamp(sample.RainIntensity * 1.2f, 0.15f, 1.0f);
            }
            if (_sandParticles != null)
            {
                _sandParticles.Emitting = isSand;
                _sandParticles.AmountRatio = isSand ? 0.85f : 0.0f;
            }
        }
    }
}
