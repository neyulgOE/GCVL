using System;
using Godot;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Flora
{
    /// <summary>
    /// 9 distinct prehistoric procedural ArrayMesh silhouettes covering all 6 ecological layers:
    /// 1. GiantSequoia (Emergent Layer 1)
    /// 2. PrimevalBroadleaf (Main Canopy Layer 2 - wide billowing crown, width > trunk height!)
    /// 3. AlpineConifer (Cold Canopy Layer 2 - snow-dusted drooping spruce tiers)
    /// 4. KrummholzDwarfPine (Treeline Understory Layer 3 - wind-twisted low pine)
    /// 5. AutumnDeciduous (Steppe Grove Layer 2 - cloud-crowned golden ginkgo / crimson maple)
    /// 6. PrehistoricDesertTree (Desert Canopy Layer 2 - swollen baobab / flat umbrella dragon-blood)
    /// 7. PalmAndTreeFern (Riparian & Sanctuary Understory Layer 3)
    /// 8. EcotoneShrub & ReedGrass (Layer 4 Shrub + Layer 5 Herb/Ground)
    /// 9. FallenLog & Boulder (Layer 6 Litter/Soil)
    /// </summary>
    public static class FloraMeshBuilder
    {
        /// <summary>1. GiantSequoia / Dawn Redwood (Emergent Layer 1, ~24m tall, ~82 tris).</summary>
        public static ArrayMesh CreateGiantSequoiaMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            // Tall reddish-brown buttressed trunk
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 22.0f, 0.0f), 1.05f, 0.22f, 6,
                new Color(0.28f, 0.14f, 0.09f, 0.0f), new Color(0.34f, 0.18f, 0.11f, 0.06f));

            float[] tierY = { 11.5f, 15.2f, 18.6f, 21.4f };
            float[] tierR = { 6.2f, 5.2f, 4.0f, 2.7f };
            for (int t = 0; t < tierY.Length; t++)
            {
                AddJaggedPlate(st, new Vector3(0.0f, tierY[t], 0.0f), tierR[t], 2.8f, 6, t * 0.58f,
                    new Color(0.05f, 0.14f, 0.05f, 0.08f),
                    new Color(0.11f, 0.27f, 0.10f, 0.18f),
                    new Color(0.16f, 0.34f, 0.13f, 0.22f));
            }

            st.GenerateNormals();
            return st.Commit();
        }

        /// <summary>2. PrimevalBroadleaf (Canopy Layer 2 - wide billowing crown ~13m wide x 10m tall, ~88 tris).</summary>
        public static ArrayMesh CreatePrimevalBroadleafMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            var barkBot = new Color(0.22f, 0.16f, 0.11f, 0.0f);
            var barkTop = new Color(0.27f, 0.20f, 0.14f, 0.04f);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 4.8f, 0.0f), 0.55f, 0.32f, 5, barkBot, barkTop);

            // Wide overlapping multi-cluster canopy (crown width > height for closed canopy!)
            Vector3[] centers =
            {
                new Vector3(0.0f, 7.6f, 0.0f),
                new Vector3(2.9f, 6.3f, 1.6f),
                new Vector3(-2.7f, 6.5f, 1.8f),
                new Vector3(0.3f, 6.2f, -3.0f),
            };
            Vector3[] radii =
            {
                new Vector3(4.6f, 2.5f, 4.4f),
                new Vector3(3.4f, 2.0f, 3.3f),
                new Vector3(3.3f, 2.0f, 3.3f),
                new Vector3(3.5f, 2.1f, 3.4f),
            };

            for (int i = 0; i < centers.Length; i++)
            {
                AddLowPolyCrown(st, centers[i], radii[i], 101 + i * 31,
                    new Color(0.07f, 0.19f, 0.06f, 0.12f),
                    new Color(0.18f, 0.36f, 0.12f, 0.26f));
            }

            st.GenerateNormals();
            return st.Commit();
        }

        /// <summary>3. AlpineConifer (Cold Canopy Layer 2 - snow-dusted drooping spruce, ~68 tris).</summary>
        public static ArrayMesh CreateAlpineConiferMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 10.5f, 0.0f), 0.36f, 0.08f, 5,
                new Color(0.18f, 0.13f, 0.10f, 0.0f), new Color(0.22f, 0.16f, 0.12f, 0.04f));

            const int tiers = 4;
            for (int t = 0; t < tiers; t++)
            {
                float frac = t / (float)(tiers - 1);
                float baseY = 2.2f + frac * 6.4f;
                float radius = 3.1f * (1.0f - frac * 0.56f);
                float height = 3.3f - frac * 0.9f;
                float windW = 0.08f + frac * 0.18f;

                // Cool blue-spruce green with frosty snow-dusted upper tips
                AddJaggedPlate(st, new Vector3(0.0f, baseY, 0.0f), radius, height, 6, t * 0.52f,
                    new Color(0.06f, 0.14f, 0.12f, windW * 0.5f),
                    new Color(0.14f, 0.26f, 0.22f, windW),
                    new Color(0.55f, 0.66f, 0.70f, windW * 1.1f));
            }

            st.GenerateNormals();
            return st.Commit();
        }

        /// <summary>4. KrummholzDwarfPine (Treeline Layer 3 - low wind-twisted pine clinging to rock, ~44 tris).</summary>
        public static ArrayMesh CreateKrummholzMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            AddTaperedCylinder(st, Vector3.Zero, new Vector3(1.1f, 1.8f, 0.4f), 0.24f, 0.10f, 5,
                new Color(0.20f, 0.15f, 0.11f, 0.0f), new Color(0.24f, 0.18f, 0.13f, 0.06f));

            AddLowPolyCrown(st, new Vector3(1.3f, 2.0f, 0.5f), new Vector3(2.2f, 0.95f, 1.7f), 317,
                new Color(0.07f, 0.16f, 0.11f, 0.08f),
                new Color(0.18f, 0.29f, 0.22f, 0.18f));
            AddLowPolyCrown(st, new Vector3(-0.4f, 1.4f, -0.3f), new Vector3(1.5f, 0.75f, 1.4f), 331,
                new Color(0.07f, 0.16f, 0.11f, 0.08f),
                new Color(0.18f, 0.29f, 0.22f, 0.18f));

            st.GenerateNormals();
            return st.Commit();
        }

        /// <summary>5. AutumnDeciduous (Autumn Steppes Layer 2 - cloud-like golden/crimson canopy, ~72 tris).</summary>
        public static ArrayMesh CreateAutumnDeciduousMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.15f, 4.6f, 0.0f), 0.42f, 0.20f, 5,
                new Color(0.24f, 0.17f, 0.12f, 0.0f), new Color(0.30f, 0.22f, 0.16f, 0.05f));

            // Warm neutral-gold base so MultiMesh.SetInstanceColor can shift between gold, amber & crimson!
            var dark = new Color(0.56f, 0.34f, 0.08f, 0.14f);
            var lit = new Color(0.95f, 0.74f, 0.22f, 0.28f);

            AddLowPolyCrown(st, new Vector3(0.0f, 7.2f, 0.0f), new Vector3(3.8f, 2.2f, 3.6f), 211, dark, lit);
            AddLowPolyCrown(st, new Vector3(2.1f, 5.8f, -1.3f), new Vector3(2.5f, 1.6f, 2.4f), 241, dark, lit);
            AddLowPolyCrown(st, new Vector3(-1.9f, 5.9f, 1.5f), new Vector3(2.5f, 1.6f, 2.4f), 271, dark, lit);

            st.GenerateNormals();
            return st.Commit();
        }

        /// <summary>6. PrehistoricDesertTree (Swollen Baobab / Dragon Blood umbrella tree, ~68 tris).</summary>
        public static ArrayMesh CreateDesertUmbrellaTreeMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 3.8f, 0.0f), 0.92f, 0.98f, 6,
                new Color(0.40f, 0.28f, 0.19f, 0.0f), new Color(0.44f, 0.31f, 0.21f, 0.02f));
            AddTaperedCylinder(st, new Vector3(0.0f, 3.7f, 0.0f), new Vector3(0.0f, 6.8f, 0.0f), 0.94f, 0.50f, 6,
                new Color(0.44f, 0.31f, 0.21f, 0.02f), new Color(0.42f, 0.30f, 0.20f, 0.04f));

            AddLowPolyCrown(st, new Vector3(0.0f, 7.9f, 0.0f), new Vector3(4.6f, 1.15f, 4.4f), 509,
                new Color(0.18f, 0.26f, 0.12f, 0.10f),
                new Color(0.32f, 0.42f, 0.18f, 0.22f));
            AddLowPolyCrown(st, new Vector3(2.4f, 7.3f, 1.3f), new Vector3(2.4f, 0.90f, 2.4f), 523,
                new Color(0.18f, 0.26f, 0.12f, 0.10f),
                new Color(0.32f, 0.42f, 0.18f, 0.22f));

            st.GenerateNormals();
            return st.Commit();
        }

        /// <summary>7a. Coastal & Oasis Palm (~54 tris).</summary>
        public static ArrayMesh CreatePalmMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            Vector3 p0 = Vector3.Zero;
            Vector3 p1 = new Vector3(0.45f, 3.8f, 0.25f);
            Vector3 p2 = new Vector3(1.25f, 7.6f, 0.45f);
            AddTaperedCylinder(st, p0, p1, 0.32f, 0.22f, 5, new Color(0.36f, 0.26f, 0.18f, 0.0f), new Color(0.38f, 0.28f, 0.19f, 0.06f));
            AddTaperedCylinder(st, p1, p2, 0.22f, 0.14f, 5, new Color(0.38f, 0.28f, 0.19f, 0.06f), new Color(0.34f, 0.25f, 0.16f, 0.16f));

            for (int f = 0; f < 6; f++)
            {
                float angle = f * (MathF.PI * 2.0f / 6.0f);
                AddArchingFrond(st, p2, angle, 3.2f, 1.0f, 0.48f,
                    new Color(0.11f, 0.30f, 0.09f, 0.16f), new Color(0.24f, 0.48f, 0.15f, 0.55f));
            }

            st.GenerateNormals();
            return st.Commit();
        }

        /// <summary>7b. Ancient Tree Fern / Cycad (Understory Layer 3, ~32 tris).</summary>
        public static ArrayMesh CreateTreeFernMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 1.2f, 0.0f), 0.22f, 0.16f, 5,
                new Color(0.22f, 0.16f, 0.11f, 0.0f), new Color(0.26f, 0.19f, 0.13f, 0.04f));

            for (int f = 0; f < 6; f++)
            {
                float angle = f * (MathF.PI * 2.0f / 6.0f) + (f % 2) * 0.22f;
                AddArchingFrond(st, new Vector3(0.0f, 1.15f, 0.0f), angle, 2.2f, 1.1f, 0.44f,
                    new Color(0.09f, 0.24f, 0.07f, 0.05f), new Color(0.20f, 0.44f, 0.13f, 0.65f));
            }

            st.GenerateNormals();
            return st.Commit();
        }

        /// <summary>8a. Ecotone Berry Shrub (Layer 4 Shrub, ~24 tris).</summary>
        public static ArrayMesh CreateShrubMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            AddLowPolyCrown(st, new Vector3(0.0f, 0.72f, 0.0f), new Vector3(1.45f, 0.92f, 1.45f), 701,
                new Color(0.10f, 0.22f, 0.07f, 0.10f), new Color(0.22f, 0.36f, 0.12f, 0.35f));

            st.GenerateNormals();
            return st.Commit();
        }

        /// <summary>8b. Meadow Grass / Riparian Reed Clump (Layer 5 Herb/Ground, ~18 tris).</summary>
        public static ArrayMesh CreateGrassClumpMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            const int blades = 6;
            for (int b = 0; b < blades; b++)
            {
                float angle = b * (MathF.PI * 2.0f / blades) + (b % 2) * 0.2f;
                float rOff = (b % 2) * 0.16f;
                Vector3 basePos = new Vector3(MathF.Cos(angle) * rOff, 0.0f, MathF.Sin(angle) * rOff);
                float h = 1.15f + (b % 3) * 0.30f;
                float lean = 0.38f + (b % 2) * 0.18f;

                Vector3 dir = new Vector3(MathF.Cos(angle), 0.0f, MathF.Sin(angle));
                Vector3 side = new Vector3(-dir.Z, 0.0f, dir.X) * 0.12f;

                Vector3 p0L = basePos - side;
                Vector3 p0R = basePos + side;
                Vector3 p1L = basePos + dir * (lean * 0.45f) + Vector3.Up * (h * 0.55f) - side * 0.55f;
                Vector3 p1R = basePos + dir * (lean * 0.45f) + Vector3.Up * (h * 0.55f) + side * 0.55f;
                Vector3 tip = basePos + dir * lean + Vector3.Up * h;

                var cRoot = new Color(0.12f, 0.22f, 0.08f, 0.0f);
                var cMid = new Color(0.24f, 0.34f, 0.12f, 0.45f);
                var cTip = new Color(0.36f, 0.44f, 0.18f, 1.0f);

                AddTriangle(st, p0L, p0R, p1R, cRoot, cRoot, cMid);
                AddTriangle(st, p0L, p1R, p1L, cRoot, cMid, cMid);
                AddTriangle(st, p1L, p1R, tip, cMid, cMid, cTip);
            }

            st.GenerateNormals();
            return st.Commit();
        }

        /// <summary>9a. Fallen Mossy Log (Layer 6 Litter/Soil, ~20 tris).</summary>
        public static ArrayMesh CreateFallenLogMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            AddTaperedCylinder(st, new Vector3(-1.8f, 0.20f, 0.0f), new Vector3(1.8f, 0.24f, 0.15f), 0.34f, 0.26f, 5,
                new Color(0.18f, 0.13f, 0.08f, 0.0f), new Color(0.14f, 0.24f, 0.09f, 0.0f));

            st.GenerateNormals();
            return st.Commit();
        }

        /// <summary>9b. Faceted Rock Boulder (Layer 6 Litter/Soil, ~24 tris).</summary>
        public static ArrayMesh CreateBoulderMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            AddLowPolyCrown(st, new Vector3(0.0f, 0.48f, 0.0f), new Vector3(1.30f, 0.88f, 1.12f), 911,
                new Color(0.18f, 0.17f, 0.16f, 0.0f), new Color(0.34f, 0.32f, 0.30f, 0.0f));

            st.GenerateNormals();
            return st.Commit();
        }

        // ----------------------------------------------------------------------
        // Low-Poly Geometry Primitives
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

        private static void AddJaggedPlate(
            SurfaceTool st, Vector3 baseCenter, float radius, float height, int lobes, float rotOffset,
            Color innerDark, Color outerTip, Color apexCol)
        {
            int pts = lobes * 2;
            Vector3 apex = baseCenter + Vector3.Up * height;
            Vector3 hub = baseCenter + Vector3.Up * (height * 0.15f);

            for (int i = 0; i < pts; i++)
            {
                int next = (i + 1) % pts;
                float a0 = rotOffset + i * (MathF.PI * 2.0f / pts);
                float a1 = rotOffset + next * (MathF.PI * 2.0f / pts);

                float r0 = (i % 2 == 0) ? radius : radius * 0.55f;
                float r1 = (next % 2 == 0) ? radius : radius * 0.55f;
                float droop0 = (i % 2 == 0) ? -0.32f : 0.12f;
                float droop1 = (next % 2 == 0) ? -0.32f : 0.12f;

                Vector3 v0 = baseCenter + new Vector3(MathF.Cos(a0) * r0, droop0, MathF.Sin(a0) * r0);
                Vector3 v1 = baseCenter + new Vector3(MathF.Cos(a1) * r1, droop1, MathF.Sin(a1) * r1);
                Color c0 = (i % 2 == 0) ? outerTip : innerDark;
                Color c1 = (next % 2 == 0) ? outerTip : innerDark;

                AddTriangle(st, v0, apex, v1, c0, apexCol, c1);
                AddTriangle(st, v0, v1, hub, c0, c1, innerDark);
            }
        }

        private static void AddLowPolyCrown(
            SurfaceTool st, Vector3 center, Vector3 radii, int seed, Color darkInner, Color litOuter)
        {
            const int sectors = 5;
            Vector3 SampleRing(float yNorm, float rScale, int s, float angleOff)
            {
                float theta = angleOff + s * (MathF.PI * 2.0f / sectors);
                Vector3 dir = new Vector3(MathF.Cos(theta) * rScale, yNorm, MathF.Sin(theta) * rScale);
                float n = FastNoise.GradientNoise2D(dir.X * 2.0f + dir.Y, dir.Z * 2.0f - dir.Y, seed);
                float disp = 0.85f + 0.28f * n;
                return center + new Vector3(dir.X * radii.X, dir.Y * radii.Y, dir.Z * radii.Z) * disp;
            }

            Vector3 topPole = center + new Vector3(0.0f, radii.Y * 0.92f, 0.0f);
            Vector3 botPole = center - new Vector3(0.0f, radii.Y * 0.72f, 0.0f);
            Color midCol = darkInner.Lerp(litOuter, 0.52f);

            for (int s = 0; s < sectors; s++)
            {
                int ns = (s + 1) % sectors;
                Vector3 u0 = SampleRing(0.32f, 0.92f, s, 0.0f);
                Vector3 u1 = SampleRing(0.32f, 0.92f, ns, 0.0f);
                Vector3 l0 = SampleRing(-0.28f, 0.96f, s, 0.45f);
                Vector3 l1 = SampleRing(-0.28f, 0.96f, ns, 0.45f);

                AddTriangle(st, topPole, u1, u0, litOuter, litOuter, litOuter);
                AddTriangle(st, u0, u1, l0, litOuter, litOuter, midCol);
                AddTriangle(st, u1, l1, l0, litOuter, midCol, midCol);
                AddTriangle(st, botPole, l0, l1, darkInner, midCol, midCol);
            }
        }

        private static void AddArchingFrond(
            SurfaceTool st, Vector3 origin, float angle, float length, float archHeight, float maxWidth,
            Color cBase, Color cTip)
        {
            Vector3 dir = new Vector3(MathF.Cos(angle), 0.0f, MathF.Sin(angle));
            Vector3 side = new Vector3(-dir.Z, 0.0f, dir.X);

            Vector3 mid = origin + dir * (length * 0.52f) + Vector3.Up * archHeight;
            Vector3 tip = origin + dir * length + Vector3.Up * (archHeight * 0.25f);
            Vector3 mL = mid - side * maxWidth;
            Vector3 mR = mid + side * maxWidth;
            Color cMid = cBase.Lerp(cTip, 0.5f);

            AddTriangle(st, origin - side * 0.06f, origin + side * 0.06f, mR, cBase, cBase, cMid);
            AddTriangle(st, origin - side * 0.06f, mR, mL, cBase, cMid, cMid);
            AddTriangle(st, mL, mR, tip, cMid, cMid, cTip);
        }
    }
}
