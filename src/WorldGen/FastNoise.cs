using System;
using System.Runtime.CompilerServices;

namespace PrimevalWorld.WorldGen
{
    /// <summary>
    /// Deterministic 2D procedural noise utilities (Value, Gradient, fBm, Ridged, Domain Warping).
    /// Zero-allocation inner loops suitable for multi-threaded terrain chunk generation.
    /// </summary>
    public static class FastNoise
    {
        [MethodImpl(MethodImplOptions.AggressiveInlining)]
        private static float Fade(float t) => t * t * t * (t * (t * 6.0f - 15.0f) + 10.0f);

        [MethodImpl(MethodImplOptions.AggressiveInlining)]
        private static float Lerp(float a, float b, float t) => a + t * (b - a);

        [MethodImpl(MethodImplOptions.AggressiveInlining)]
        public static float SmoothStep(float edge0, float edge1, float x)
        {
            float denom = edge1 - edge0;
            if (MathF.Abs(denom) < 1e-6f) return x >= edge1 ? 1.0f : 0.0f;
            float t = Math.Clamp((x - edge0) / denom, 0.0f, 1.0f);
            return t * t * (3.0f - 2.0f * t);
        }

        [MethodImpl(MethodImplOptions.AggressiveInlining)]
        private static int FastFloor(float x)
        {
            int xi = (int)x;
            return x < xi ? xi - 1 : xi;
        }

        [MethodImpl(MethodImplOptions.AggressiveInlining)]
        private static uint Hash2D(int ix, int iy, int seed)
        {
            unchecked
            {
                uint h = (uint)ix * 374761393u + (uint)iy * 668265263u + (uint)seed * 1442695041u;
                h = (h ^ (h >> 13)) * 1274126177u;
                return h ^ (h >> 16);
            }
        }

        [MethodImpl(MethodImplOptions.AggressiveInlining)]
        private static float GradDot(int ix, int iy, float fx, float fy, int seed)
        {
            uint h = Hash2D(ix, iy, seed) & 7u;
            return h switch
            {
                0 => fx + fy,
                1 => -fx + fy,
                2 => fx - fy,
                3 => -fx - fy,
                4 => fx * 1.4142135f,
                5 => -fx * 1.4142135f,
                6 => fy * 1.4142135f,
                _ => -fy * 1.4142135f,
            };
        }

        /// <summary>Gradient Perlin-style 2D noise in roughly [-1, 1].</summary>
        public static float GradientNoise2D(float x, float y, int seed)
        {
            int ix = FastFloor(x);
            int iy = FastFloor(y);
            float fx = x - ix;
            float fy = y - iy;

            float u = Fade(fx);
            float v = Fade(fy);

            float n00 = GradDot(ix, iy, fx, fy, seed);
            float n10 = GradDot(ix + 1, iy, fx - 1.0f, fy, seed);
            float n01 = GradDot(ix, iy + 1, fx, fy - 1.0f, seed);
            float n11 = GradDot(ix + 1, iy + 1, fx - 1.0f, fy - 1.0f, seed);

            float nx0 = Lerp(n00, n10, u);
            float nx1 = Lerp(n01, n11, u);
            return Lerp(nx0, nx1, v);
        }

        /// <summary>Normalized 2D fBm in [0, 1].</summary>
        public static float Fbm2D(float x, float y, int seed, int octaves = 5, float lacunarity = 2.04f, float gain = 0.5f)
        {
            float sum = 0.0f;
            float amp = 1.0f;
            float freq = 1.0f;
            float norm = 0.0f;

            for (int i = 0; i < octaves; i++)
            {
                sum += amp * GradientNoise2D(x * freq, y * freq, seed + i * 131);
                norm += amp;
                amp *= gain;
                freq *= lacunarity;
            }

            float normalized = sum / (norm * 0.85f);
            return Math.Clamp(0.5f + 0.5f * normalized, 0.0f, 1.0f);
        }

        /// <summary>Sharp alpine ridged multifractal noise in [0, 1].</summary>
        public static float RidgedFbm2D(float x, float y, int seed, int octaves = 5, float lacunarity = 2.12f, float gain = 0.5f)
        {
            float sum = 0.0f;
            float amp = 0.5f;
            float freq = 1.0f;
            float weight = 1.0f;

            for (int i = 0; i < octaves; i++)
            {
                float n = GradientNoise2D(x * freq, y * freq, seed + i * 257);
                float signal = 1.0f - MathF.Abs(n);
                signal = signal * signal * weight;
                weight = Math.Clamp(signal * 2.0f, 0.0f, 1.0f);
                sum += signal * amp;
                freq *= lacunarity;
                amp *= gain;
            }

            return Math.Clamp(sum * 1.25f, 0.0f, 1.0f);
        }
    }
}
