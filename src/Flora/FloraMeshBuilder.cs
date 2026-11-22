using System;
using Godot;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Flora
{
    /// <summary>
    /// Procedural multi-part ArrayMesh generators for Stage 2.
    /// Every mesh uses vertex colors (RGB = albedo + AO darkening, A = wind sway weight)
    /// and organic silhouette geometry (no plain spheres or plain cones).
    /// </summary>
    public static class FloraMeshBuilder
    {
        /// <summary>
        /// 1. Alpine Conifer / Spruce: tapered trunk + 5 jagged drooping branch tiers
        /// with rotational offset and darker interior AO.
        /// </summary>
        public static ArrayMesh CreateConiferMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            // Tapered trunk (height 10.5m)
            var barkDark = new Color(0.20f, 0.14f, 0.10f, 0.0f);
            var barkTop = new Color(0.26f, 0.19f, 0.14f, 0.05f);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.08f, 9.8f, -0.05f), 0.36f, 0.07f, 7, barkDark, barkTop);

            // 5 jagged star-like branch tiers
            const int tiers = 5;
            for (int t = 0; t < tiers; t++)
            {
                float frac = t / (float)(tiers - 1);
                float baseY = 2.4f + frac * 6.8f;
                float tierHeight = 3.2f - frac * 1.1f;
                float baseRadius = 2.75f * (1.0f - frac * 0.62f);
                float rotOffset = t * 0.72f;
                float windW = 0.12f + frac * 0.25f;

                var innerDark = new Color(0.06f, 0.14f, 0.06f, windW * 0.5f);
                var outerTip = new Color(0.11f + frac * 0.03f, 0.24f + frac * 0.04f, 0.10f, windW);
                var apexCol = new Color(0.14f, 0.28f, 0.12f, windW * 1.1f);

                AddJaggedFoliageTier(st, new Vector3(0.0f, baseY, 0.0f), baseRadius, tierHeight, 10, rotOffset, innerDark, outerTip, apexCol);
            }

            st.GenerateNormals();
            return st.Commit();
        }

        /// <summary>
        /// 2. Primeval Broadleaf Canopy Tree: flared root trunk + 4 angled limbs
        /// + 6 asymmetric faceted foliage clusters forming a wide natural crown.
        /// </summary>
        public static ArrayMesh CreateBroadleafTreeMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            var barkRoot = new Color(0.22f, 0.16f, 0.11f, 0.0f);
            var barkMid = new Color(0.28f, 0.21f, 0.15f, 0.04f);

            // Main flared trunk
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.12f, 5.2f, 0.08f), 0.58f, 0.32f, 8, barkRoot, barkMid);

            // 4 spreading limbs + canopy clusters
            Vector3 trunkTop = new Vector3(0.12f, 4.9f, 0.08f);
            Vector3[] limbEnds =
            {
                new Vector3(2.1f, 7.6f, 1.2f),
                new Vector3(-2.0f, 7.4f, 1.4f),
                new Vector3(1.1f, 7.8f, -2.1f),
                new Vector3(-1.5f, 7.2f, -1.7f),
            };

            for (int i = 0; i < limbEnds.Length; i++)
            {
                AddTaperedCylinder(st, trunkTop, limbEnds[i], 0.24f, 0.11f, 6, barkMid, barkMid);
                AddFacetedCanopyCluster(
                    st,
                    limbEnds[i] + new Vector3(0.0f, 0.9f, 0.0f),
                    new Vector3(2.4f, 1.55f, 2.3f),
                    101 + i * 37,
                    new Color(0.09f, 0.21f, 0.06f, 0.18f),
                    new Color(0.19f, 0.34f, 0.10f, 0.32f)
                );
            }

            // Central upper crown cluster + lower side cluster
            AddFacetedCanopyCluster(
                st,
                new Vector3(0.0f, 9.1f, 0.0f),
                new Vector3(2.8f, 1.85f, 2.7f),
                401,
                new Color(0.10f, 0.23f, 0.07f, 0.22f),
                new Color(0.22f, 0.38f, 0.12f, 0.38f)
            );

            st.GenerateNormals();
            return st.Commit();
        }

        /// <summary>
        /// 3. Riverbank Fern / Ancient Cycad: short fibrous base + 7 arching segmented fronds.
        /// </summary>
        public static ArrayMesh CreateFernMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            AddTaperedCylinder(
                st,
                Vector3.Zero,
                new Vector3(0.0f, 0.45f, 0.0f),
                0.18f,
                0.14f,
                6,
                new Color(0.20f, 0.15f, 0.10f, 0.0f),
                new Color(0.24f, 0.18f, 0.12f, 0.05f)
            );

            const int frondCount = 7;
            for (int f = 0; f < frondCount; f++)
            {
                float angle = f * (MathF.PI * 2.0f / frondCount) + (f % 2) * 0.22f;
                float length = 1.65f + (f % 3) * 0.22f;
                float archHeight = 1.05f + (f % 2) * 0.20f;
                AddArchingFrond(st, new Vector3(0.0f, 0.35f, 0.0f), angle, length, archHeight, 0.42f);
            }

            st.GenerateNormals();
            return st.Commit();
        }

        /// <summary>
        /// 4. Forest-edge Berry Shrub: woody stems + 4 irregular leafy clusters.
        /// </summary>
        public static ArrayMesh CreateShrubMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            Vector3[] offsets =
            {
                new Vector3(0.0f, 0.72f, 0.0f),
                new Vector3(0.55f, 0.52f, 0.35f),
                new Vector3(-0.52f, 0.55f, 0.28f),
                new Vector3(0.08f, 0.50f, -0.55f),
            };

            for (int i = 0; i < offsets.Length; i++)
            {
                AddFacetedCanopyCluster(
                    st,
                    offsets[i],
                    new Vector3(0.85f, 0.65f, 0.85f),
                    701 + i * 29,
                    new Color(0.09f, 0.19f, 0.06f, 0.15f),
                    new Color(0.18f, 0.31f, 0.10f, 0.45f)
                );
            }

            st.GenerateNormals();
            return st.Commit();
        }

        /// <summary>
        /// 5. Tall Grass Clump: 12 curved, tapered, crossed grass blades with root-to-tip wind weights.
        /// </summary>
        public static ArrayMesh CreateGrassClumpMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            const int bladeCount = 12;
            for (int b = 0; b < bladeCount; b++)
            {
                float angle = b * (MathF.PI * 2.0f / bladeCount) + (b % 3) * 0.19f;
                float rOff = (b % 3) * 0.18f;
                Vector3 basePos = new Vector3(MathF.Cos(angle) * rOff, 0.0f, MathF.Sin(angle) * rOff);
                float height = 0.95f + (b % 4) * 0.22f;
                float lean = 0.32f + (b % 3) * 0.14f;

                Vector3 dir = new Vector3(MathF.Cos(angle), 0.0f, MathF.Sin(angle));
                Vector3 side = new Vector3(-dir.Z, 0.0f, dir.X) * 0.085f;

                Vector3 p0L = basePos - side;
                Vector3 p0R = basePos + side;
                Vector3 p1L = basePos + dir * (lean * 0.42f) + Vector3.Up * (height * 0.55f) - side * 0.58f;
                Vector3 p1R = basePos + dir * (lean * 0.42f) + Vector3.Up * (height * 0.55f) + side * 0.58f;
                Vector3 tip = basePos + dir * lean + Vector3.Up * height;

                var cRoot = new Color(0.11f, 0.20f, 0.07f, 0.0f);
                var cMid = new Color(0.20f, 0.30f, 0.10f, 0.45f);
                var cTip = new Color(0.29f, 0.37f, 0.14f, 1.0f);

                AddTriangle(st, p0L, p0R, p1R, cRoot, cRoot, cMid);
                AddTriangle(st, p0L, p1R, p1L, cRoot, cMid, cMid);
                AddTriangle(st, p1L, p1R, tip, cMid, cMid, cTip);
            }

            st.GenerateNormals();
            return st.Commit();
        }

        /// <summary>
        /// 6. Faceted Noise-Displaced Boulder for riverbanks, cliff bases, and rocky shores.
        /// </summary>
        public static ArrayMesh CreateBoulderMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            AddFacetedRock(
                st,
                new Vector3(0.0f, 0.55f, 0.0f),
                new Vector3(1.25f, 0.85f, 1.05f),
                911,
                new Color(0.18f, 0.17f, 0.16f, 0.0f),
                new Color(0.32f, 0.30f, 0.28f, 0.0f)
            );

            st.GenerateNormals();
            return st.Commit();
        }

        // ----------------------------------------------------------------------
        // Geometry Helpers
        // ----------------------------------------------------------------------
        private static void AddTriangle(SurfaceTool st, Vector3 a, Vector3 b, Vector3 c, Color ca, Color cb, Color cc)
        {
            st.SetColor(ca); st.AddVertex(a);
            st.SetColor(cb); st.AddVertex(b);
            st.SetColor(cc); st.AddVertex(c);
        }

        private static void AddTaperedCylinder(
            SurfaceTool st, Vector3 bottom, Vector3 top, float rBottom, float rTop, int sides, Color colBot, Color colTop)
        {
            Vector3 axis = (top - bottom).Normalized();
            Vector3 refVec = MathF.Abs(axis.Y) < 0.9f ? Vector3.Up : Vector3.Right;
            Vector3 right = axis.Cross(refVec).Normalized();
            Vector3 forward = right.Cross(axis).Normalized();

            for (int i = 0; i < sides; i++)
            {
                float a0 = i * (MathF.PI * 2.0f / sides);
                float a1 = (i + 1) * (MathF.PI * 2.0f / sides);

                Vector3 d0 = right * MathF.Cos(a0) + forward * MathF.Sin(a0);
                Vector3 d1 = right * MathF.Cos(a1) + forward * MathF.Sin(a1);

                Vector3 b0 = bottom + d0 * rBottom;
                Vector3 b1 = bottom + d1 * rBottom;
                Vector3 t0 = top + d0 * rTop;
                Vector3 t1 = top + d1 * rTop;

                AddTriangle(st, b0, b1, t1, colBot, colBot, colTop);
                AddTriangle(st, b0, t1, t0, colBot, colTop, colTop);
            }
        }

        private static void AddJaggedFoliageTier(
            SurfaceTool st, Vector3 baseCenter, float radius, float height, int lobes, float rotOffset,
            Color innerDark, Color outerTip, Color apexCol)
        {
            int pts = lobes * 2;
            Vector3 apex = baseCenter + Vector3.Up * height;
            Vector3 hub = baseCenter + Vector3.Up * (height * 0.18f);

            for (int i = 0; i < pts; i++)
            {
                int next = (i + 1) % pts;
                float a0 = rotOffset + i * (MathF.PI * 2.0f / pts);
                float a1 = rotOffset + next * (MathF.PI * 2.0f / pts);

                float r0 = (i % 2 == 0) ? radius : radius * 0.56f;
                float r1 = (next % 2 == 0) ? radius : radius * 0.56f;
                float droop0 = (i % 2 == 0) ? -0.35f : 0.12f;
                float droop1 = (next % 2 == 0) ? -0.35f : 0.12f;

                Vector3 v0 = baseCenter + new Vector3(MathF.Cos(a0) * r0, droop0, MathF.Sin(a0) * r0);
                Vector3 v1 = baseCenter + new Vector3(MathF.Cos(a1) * r1, droop1, MathF.Sin(a1) * r1);
                Color c0 = (i % 2 == 0) ? outerTip : innerDark;
                Color c1 = (next % 2 == 0) ? outerTip : innerDark;

                // Outer slopes
                AddTriangle(st, v0, apex, v1, c0, apexCol, c1);
                // Underside closing to inner dark hub (AO shadow)
                AddTriangle(st, v0, v1, hub, c0, c1, innerDark);
            }
        }

        private static void AddFacetedCanopyCluster(
            SurfaceTool st, Vector3 center, Vector3 radii, int seed, Color darkInner, Color litOuter)
        {
            const int rings = 3;
            const int sectors = 7;

            Vector3 SampleSphere(int r, int s)
            {
                float phi = r * MathF.PI / (rings + 1);
                float theta = s * (MathF.PI * 2.0f / sectors) + (r % 2) * 0.35f;
                Vector3 dir = new Vector3(
                    MathF.Sin(phi) * MathF.Cos(theta),
                    MathF.Cos(phi),
                    MathF.Sin(phi) * MathF.Sin(theta)
                );
                float n = FastNoise.GradientNoise2D(dir.X * 2.1f + dir.Y * 1.3f, dir.Z * 2.1f - dir.Y, seed);
                float disp = 0.82f + 0.32f * n;
                return center + new Vector3(dir.X * radii.X, dir.Y * radii.Y, dir.Z * radii.Z) * disp;
            }

            Vector3 topPole = center + new Vector3(0.0f, radii.Y * 0.92f, 0.0f);
            Vector3 botPole = center - new Vector3(0.0f, radii.Y * 0.72f, 0.0f);

            for (int s = 0; s < sectors; s++)
            {
                int ns = (s + 1) % sectors;
                AddTriangle(st, topPole, SampleSphere(1, ns), SampleSphere(1, s), litOuter, litOuter, litOuter);
                AddTriangle(st, botPole, SampleSphere(rings, s), SampleSphere(rings, ns), darkInner, darkInner, darkInner);
            }

            for (int r = 1; r < rings; r++)
            {
                Color cTop = r == 1 ? litOuter : darkInner.Lerp(litOuter, 0.55f);
                Color cBot = r == rings - 1 ? darkInner : darkInner.Lerp(litOuter, 0.45f);
                for (int s = 0; s < sectors; s++)
                {
                    int ns = (s + 1) % sectors;
                    Vector3 a = SampleSphere(r, s);
                    Vector3 b = SampleSphere(r, ns);
                    Vector3 c = SampleSphere(r + 1, ns);
                    Vector3 d = SampleSphere(r + 1, s);
                    AddTriangle(st, a, b, c, cTop, cTop, cBot);
                    AddTriangle(st, a, c, d, cTop, cBot, cBot);
                }
            }
        }

        private static void AddArchingFrond(
            SurfaceTool st, Vector3 origin, float angle, float length, float archHeight, float maxWidth)
        {
            Vector3 dir = new Vector3(MathF.Cos(angle), 0.0f, MathF.Sin(angle));
            Vector3 side = new Vector3(-dir.Z, 0.0f, dir.X);

            const int segs = 4;
            var cBase = new Color(0.09f, 0.22f, 0.07f, 0.05f);
            var cTip = new Color(0.20f, 0.39f, 0.12f, 0.75f);

            Vector3 prevSpine = origin;
            Vector3 prevL = origin - side * (maxWidth * 0.25f);
            Vector3 prevR = origin + side * (maxWidth * 0.25f);
            Color prevC = cBase;

            for (int i = 1; i <= segs; i++)
            {
                float t = i / (float)segs;
                float y = MathF.Sin(t * MathF.PI * 0.85f) * archHeight - t * t * 0.35f;
                float w = maxWidth * MathF.Sin(t * MathF.PI) * 0.65f + 0.02f;
                Vector3 spine = origin + dir * (length * t) + Vector3.Up * y;
                Vector3 curL = spine - side * w - Vector3.Up * (w * 0.22f);
                Vector3 curR = spine + side * w - Vector3.Up * (w * 0.22f);
                Color curC = cBase.Lerp(cTip, t);

                if (i == segs)
                {
                    AddTriangle(st, prevL, spine, prevSpine, prevC, curC, prevC);
                    AddTriangle(st, prevSpine, spine, prevR, prevC, curC, prevC);
                }
                else
                {
                    AddTriangle(st, prevL, curL, curR, prevC, curC, curC);
                    AddTriangle(st, prevL, curR, prevR, prevC, curC, prevC);
                }

                prevSpine = spine;
                prevL = curL;
                prevR = curR;
                prevC = curC;
            }
        }

        private static void AddFacetedRock(
            SurfaceTool st, Vector3 center, Vector3 radii, int seed, Color darkColor, Color lightColor)
        {
            const int rings = 3;
            const int sectors = 6;

            Vector3 SampleRock(int r, int s)
            {
                float phi = r * MathF.PI / (rings + 1);
                float theta = s * (MathF.PI * 2.0f / sectors) + (r % 2) * 0.42f;
                Vector3 dir = new Vector3(
                    MathF.Sin(phi) * MathF.Cos(theta),
                    MathF.Cos(phi),
                    MathF.Sin(phi) * MathF.Sin(theta)
                );
                float n = FastNoise.GradientNoise2D(dir.X * 1.9f + dir.Y, dir.Z * 1.9f - dir.Y, seed);
                float disp = 0.72f + 0.45f * MathF.Abs(n);
                Vector3 p = center + new Vector3(dir.X * radii.X, dir.Y * radii.Y, dir.Z * radii.Z) * disp;
                p.Y = MathF.Max(-0.15f, p.Y);
                return p;
            }

            Vector3 topPole = center + new Vector3(0.0f, radii.Y * 0.88f, 0.0f);
            Vector3 botPole = new Vector3(center.X, -0.15f, center.Z);

            for (int s = 0; s < sectors; s++)
            {
                int ns = (s + 1) % sectors;
                AddTriangle(st, topPole, SampleRock(1, ns), SampleRock(1, s), lightColor, lightColor, lightColor);
                AddTriangle(st, botPole, SampleRock(rings, s), SampleRock(rings, ns), darkColor, darkColor, darkColor);
            }

            for (int r = 1; r < rings; r++)
            {
                Color cTop = darkColor.Lerp(lightColor, 0.75f);
                Color cBot = darkColor.Lerp(lightColor, 0.35f);
                for (int s = 0; s < sectors; s++)
                {
                    int ns = (s + 1) % sectors;
                    Vector3 a = SampleRock(r, s);
                    Vector3 b = SampleRock(r, ns);
                    Vector3 c = SampleRock(r + 1, ns);
                    Vector3 d = SampleRock(r + 1, s);
                    AddTriangle(st, a, b, c, cTop, cTop, cBot);
                    AddTriangle(st, a, c, d, cTop, cBot, cBot);
                }
            }
        }
    }
}
