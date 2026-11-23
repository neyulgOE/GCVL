using System;
using Godot;

namespace PrimevalWorld.Flora
{
    public enum AgeStage : byte
    {
        Young = 0,
        Mature = 1,
        Ancient = 2,
    }

    /// <summary>
    /// Biological Recursive Branching Tree Builder (Da Vinci Pipe Rule r_parent^2 = r1^2 + r2^2 + Golden Angle Phyllotaxis 137.5°).
    /// Produces organic curved trunks, primary/secondary branches with continuous bark UV,
    /// and compact Curved Leaf Sprigs with Radial Normals (zero giant flat squares!).
    /// </summary>
    public static class ProceduralTreeBuilder
    {
        private const float GoldenAngleRad = 2.39996323f; // 137.508°

        public static ArrayMesh BuildTree(FloraSpeciesId species, AgeStage age, int seed)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var rng = new Random(seed * 7919 + (int)species * 131 + (int)age * 37);

            float ageHeightMult = age switch { AgeStage.Young => 0.68f, AgeStage.Mature => 1.0f, _ => 1.24f };
            float ageSpreadMult = age switch { AgeStage.Young => 0.72f, AgeStage.Mature => 1.0f, _ => 1.30f };
            float ageRadiusMult = age switch { AgeStage.Young => 0.65f, AgeStage.Mature => 1.0f, _ => 1.38f };

            switch (species)
            {
                case FloraSpeciesId.PrimevalBanyanFig:
                case FloraSpeciesId.SacredAncientHardwood:
                    BuildButtressBroadleaf(st, rng, age, ageHeightMult, ageSpreadMult, ageRadiusMult, withPropRoots: species == FloraSpeciesId.PrimevalBanyanFig);
                    break;

                case FloraSpeciesId.GinkgoAncientGold:
                case FloraSpeciesId.CrimsonSteppeMaple:
                    BuildDeciduousTree(st, rng, ageHeightMult, ageSpreadMult, ageRadiusMult, leafType: 2);
                    break;
                case FloraSpeciesId.StarAppleCanopy:
                    BuildDeciduousTree(st, rng, ageHeightMult, ageSpreadMult, ageRadiusMult, leafType: 0);
                    break;

                case FloraSpeciesId.WeepingRiverWillow:
                case FloraSpeciesId.WeepingSilverBirch:
                    BuildWeepingTree(st, rng, ageHeightMult, ageSpreadMult, ageRadiusMult, species == FloraSpeciesId.WeepingSilverBirch);
                    break;

                case FloraSpeciesId.BorealSnowPine:
                case FloraSpeciesId.SilverGlacierSpruce:
                case FloraSpeciesId.GiantSequoiaReddawn:
                    BuildConiferTree(st, rng, ageHeightMult, ageSpreadMult, ageRadiusMult, isSequoia: species == FloraSpeciesId.GiantSequoiaReddawn);
                    break;

                case FloraSpeciesId.DragonBloodTree:
                case FloraSpeciesId.SavannaUmbrellaAcacia:
                    BuildUmbrellaTree(st, rng, ageHeightMult, ageSpreadMult, ageRadiusMult);
                    break;

                case FloraSpeciesId.BaobabPrehistoric:
                    BuildBaobabTree(st, rng, ageHeightMult, ageSpreadMult, ageRadiusMult);
                    break;

                case FloraSpeciesId.ArborescentTreeFern:
                case FloraSpeciesId.NipaWaterPalm:
                    BuildColumnarPalmFern(st, rng, ageHeightMult, isFern: species == FloraSpeciesId.ArborescentTreeFern);
                    break;

                default:
                    BuildDeciduousTree(st, rng, ageHeightMult, ageSpreadMult, ageRadiusMult, leafType: 0);
                    break;
            }

            return st.Commit();
        }

        private static void BuildButtressBroadleaf(
            SurfaceTool st, Random rng, AgeStage age, float hMult, float sMult, float rMult, bool withPropRoots)
        {
            var barkBot = new Color(0.28f, 0.21f, 0.14f, 0.0f);
            var barkTop = new Color(0.35f, 0.26f, 0.18f, 0.02f);

            float trunkH = 11.5f * hMult;
            float baseR = 1.05f * rMult;
            float topR = baseR * 0.48f;

            // Organic multi-segment curved trunk
            Vector3 p0 = Vector3.Zero;
            Vector3 p1 = new Vector3((float)(rng.NextDouble() - 0.5) * 0.8f, trunkH * 0.5f, (float)(rng.NextDouble() - 0.5) * 0.8f);
            Vector3 p2 = new Vector3((float)(rng.NextDouble() - 0.5) * 1.1f, trunkH, (float)(rng.NextDouble() - 0.5) * 1.1f);
            AddTaperedCylinder(st, p0, p1, baseR, (baseR + topR) * 0.52f, 7, barkBot, barkTop);
            AddTaperedCylinder(st, p1, p2, (baseR + topR) * 0.52f, topR, 6, barkBot, barkTop);

            // Buttress root flanges (stronger in Mature/Ancient)
            int buttresses = age == AgeStage.Young ? 3 : 5;
            for (int r = 0; r < buttresses; r++)
            {
                float a = r * Mathf.Tau / buttresses + (float)rng.NextDouble() * 0.35f;
                Vector3 foot = new Vector3(MathF.Cos(a) * (baseR * 2.15f), -0.15f, MathF.Sin(a) * (baseR * 2.15f));
                Vector3 join = new Vector3(MathF.Cos(a) * (baseR * 0.55f), trunkH * 0.34f, MathF.Sin(a) * (baseR * 0.55f));
                AddTaperedCylinder(st, foot, join, baseR * 0.36f, baseR * 0.16f, 4, barkBot, barkTop);
            }

            if (withPropRoots && age != AgeStage.Young)
            {
                for (int r = 0; r < 3; r++)
                {
                    float a = r * GoldenAngleRad + (float)rng.NextDouble();
                    float dist = 3.2f * sMult;
                    AddTaperedCylinder(st, new Vector3(MathF.Cos(a) * dist, -0.1f, MathF.Sin(a) * dist),
                        p2 + new Vector3(MathF.Cos(a) * dist * 0.85f, -1.2f, MathF.Sin(a) * dist * 0.85f),
                        0.15f, 0.10f, 4, barkBot, barkTop);
                }
            }

            // Recursive Phyllotaxis + Da Vinci primary & secondary branches
            Vector3 crownCenter = p2 + new Vector3(0.0f, 3.8f * hMult, 0.0f);
            int primaryCount = age == AgeStage.Young ? 4 : 5;
            float childR = topR / MathF.Sqrt(primaryCount * 0.72f);

            for (int i = 0; i < primaryCount; i++)
            {
                float azim = i * GoldenAngleRad + (float)rng.NextDouble() * 0.3f;
                float elev = 0.42f + (float)rng.NextDouble() * 0.30f;
                Vector3 dir = new Vector3(MathF.Cos(azim) * MathF.Cos(elev), MathF.Sin(elev), MathF.Sin(azim) * MathF.Cos(elev)).Normalized();
                float len = (5.8f + (float)rng.NextDouble() * 2.4f) * sMult;
                Vector3 bEnd = p2 + dir * len;
                AddTaperedCylinder(st, p2, bEnd, childR, childR * 0.55f, 5, barkTop, barkTop);

                // Secondary branches + compact curved leaf sprigs (1.25-1.55m, natural airy clusters)
                float subR = childR * 0.55f / 1.414f;
                for (int s = 0; s < 3; s++)
                {
                    float sAz = azim + (s - 1) * 0.85f + (float)(rng.NextDouble() - 0.5) * 0.3f;
                    Vector3 sDir = new Vector3(MathF.Cos(sAz), 0.35f + (float)rng.NextDouble() * 0.35f, MathF.Sin(sAz)).Normalized();
                    Vector3 sEnd = bEnd + sDir * (3.2f * sMult);
                    AddTaperedCylinder(st, bEnd, sEnd, subR, subR * 0.45f, 4, barkTop, barkTop);
                    AddCurvedLeafSprigCluster(st, sEnd, crownCenter, 1.35f * sMult, 2, leafType: 0, rng, 0.14f);
                }
                AddCurvedLeafSprigCluster(st, bEnd, crownCenter, 1.45f * sMult, 2, leafType: 0, rng, 0.14f);
            }
            AddCurvedLeafSprigCluster(st, crownCenter + Vector3.Up * 1.4f, crownCenter, 1.55f * sMult, 2, leafType: 0, rng, 0.15f);
        }

        private static void BuildDeciduousTree(SurfaceTool st, Random rng, float hMult, float sMult, float rMult, int leafType)
        {
            var barkBot = new Color(0.32f, 0.25f, 0.18f, 0.0f);
            var barkTop = new Color(0.38f, 0.30f, 0.22f, 0.02f);

            float trunkH = 6.2f * hMult;
            float baseR = 0.48f * rMult;
            float topR = baseR * 0.54f;

            Vector3 p1 = new Vector3((float)(rng.NextDouble() - 0.5) * 0.5f, trunkH * 0.52f, (float)(rng.NextDouble() - 0.5) * 0.5f);
            Vector3 p2 = new Vector3((float)(rng.NextDouble() - 0.5) * 0.7f, trunkH, (float)(rng.NextDouble() - 0.5) * 0.7f);
            AddTaperedCylinder(st, Vector3.Zero, p1, baseR, (baseR + topR) * 0.52f, 6, barkBot, barkTop);
            AddTaperedCylinder(st, p1, p2, (baseR + topR) * 0.52f, topR, 5, barkBot, barkTop);

            Vector3 crownCenter = p2 + new Vector3(0.0f, 3.2f * hMult, 0.0f);
            const int branches = 5;
            float childR = topR / MathF.Sqrt(branches * 0.7f);

            for (int i = 0; i < branches; i++)
            {
                float azim = i * GoldenAngleRad + (float)rng.NextDouble() * 0.25f;
                float elev = 0.52f + (float)rng.NextDouble() * 0.35f;
                Vector3 dir = new Vector3(MathF.Cos(azim) * MathF.Cos(elev), MathF.Sin(elev), MathF.Sin(azim) * MathF.Cos(elev)).Normalized();
                Vector3 bEnd = p2 + dir * (4.4f * sMult);
                AddTaperedCylinder(st, p2, bEnd, childR, childR * 0.50f, 4, barkTop, barkTop);

                for (int s = 0; s < 2; s++)
                {
                    float sAz = azim + (s == 0 ? -0.65f : 0.65f);
                    Vector3 sEnd = bEnd + new Vector3(MathF.Cos(sAz), 0.45f, MathF.Sin(sAz)).Normalized() * (2.3f * sMult);
                    AddTaperedCylinder(st, bEnd, sEnd, childR * 0.45f, childR * 0.20f, 4, barkTop, barkTop);
                    AddCurvedLeafSprigCluster(st, sEnd, crownCenter, 1.65f * sMult, 2, leafType, rng, 0.15f);
                }
                AddCurvedLeafSprigCluster(st, bEnd, crownCenter, 1.75f * sMult, 2, leafType, rng, 0.15f);
            }
            AddCurvedLeafSprigCluster(st, crownCenter + Vector3.Up * 1.4f, crownCenter, 1.9f * sMult, 2, leafType, rng, 0.16f);
        }

        private static void BuildWeepingTree(SurfaceTool st, Random rng, float hMult, float sMult, float rMult, bool paleBark)
        {
            var barkBot = paleBark ? new Color(0.84f, 0.83f, 0.80f, 0.0f) : new Color(0.28f, 0.21f, 0.14f, 0.0f);
            var barkTop = paleBark ? new Color(0.90f, 0.89f, 0.86f, 0.02f) : new Color(0.34f, 0.26f, 0.18f, 0.02f);

            float trunkH = 6.5f * hMult;
            float baseR = 0.46f * rMult;
            Vector3 p2 = new Vector3(0.8f * sMult, trunkH, 0.3f * sMult);
            AddTaperedCylinder(st, Vector3.Zero, p2, baseR, baseR * 0.46f, 6, barkBot, barkTop);

            Vector3 crownCenter = p2 + new Vector3(0.0f, 2.4f * hMult, 0.0f);
            for (int i = 0; i < 5; i++)
            {
                float azim = i * GoldenAngleRad;
                Vector3 bEnd = p2 + new Vector3(MathF.Cos(azim) * 3.4f * sMult, 2.5f * hMult, MathF.Sin(azim) * 3.4f * sMult);
                AddTaperedCylinder(st, p2, bEnd, baseR * 0.32f, baseR * 0.12f, 4, barkTop, barkTop);
                AddCurvedLeafSprigCluster(st, bEnd + new Vector3(0, -0.8f, 0), crownCenter, 2.3f * sMult, 2, leafType: 0, rng, 0.17f);
            }
        }

        private static void BuildConiferTree(SurfaceTool st, Random rng, float hMult, float sMult, float rMult, bool isSequoia)
        {
            var barkBot = isSequoia ? new Color(0.38f, 0.18f, 0.10f, 0.0f) : new Color(0.24f, 0.17f, 0.12f, 0.0f);
            var barkTop = isSequoia ? new Color(0.42f, 0.22f, 0.13f, 0.03f) : new Color(0.28f, 0.20f, 0.15f, 0.03f);

            float totalH = (isSequoia ? 24.0f : 15.0f) * hMult;
            float baseR = (isSequoia ? 1.05f : 0.44f) * rMult;
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, totalH, 0.0f), baseR, 0.07f, 6, barkBot, barkTop);

            int tiers = isSequoia ? 5 : 6;
            float startFrac = isSequoia ? 0.48f : 0.24f;
            Vector3 crownCenter = new Vector3(0.0f, totalH * 0.62f, 0.0f);

            for (int t = 0; t < tiers; t++)
            {
                float frac = startFrac + (t / (float)(tiers - 1)) * (0.94f - startFrac);
                float y = totalH * frac;
                float tierRadius = (1.0f - (t / (float)tiers) * 0.72f) * (isSequoia ? 4.8f : 3.6f) * sMult;
                int bCount = t < tiers - 2 ? 4 : 3;
                for (int b = 0; b < bCount; b++)
                {
                    float a = b * (Mathf.Tau / bCount) + t * GoldenAngleRad;
                    // Drooping conifer branches
                    Vector3 bStart = new Vector3(0.0f, y, 0.0f);
                    Vector3 bEnd = new Vector3(MathF.Cos(a) * tierRadius, y - tierRadius * 0.25f, MathF.Sin(a) * tierRadius);
                    AddTaperedCylinder(st, bStart, bEnd, 0.11f * rMult, 0.04f, 4, barkTop, barkTop);
                    AddCurvedLeafSprigCluster(st, bEnd, crownCenter, 1.85f * sMult, 2, leafType: 1, rng, 0.14f);
                }
            }
            AddCurvedLeafSprigCluster(st, new Vector3(0.0f, totalH + 0.4f, 0.0f), crownCenter, 1.5f * sMult, 2, leafType: 1, rng, 0.15f);
        }

        private static void BuildUmbrellaTree(SurfaceTool st, Random rng, float hMult, float sMult, float rMult)
        {
            var bark = new Color(0.40f, 0.29f, 0.22f, 0.0f);
            float trunkH = 5.4f * hMult;
            float baseR = 0.62f * rMult;
            Vector3 fork = new Vector3((float)(rng.NextDouble() - 0.5) * 0.6f, trunkH, (float)(rng.NextDouble() - 0.5) * 0.6f);
            AddTaperedCylinder(st, Vector3.Zero, fork, baseR, baseR * 0.54f, 6, bark, bark);

            Vector3 crownCenter = fork + new Vector3(0.0f, 2.6f * hMult, 0.0f);
            for (int i = 0; i < 5; i++)
            {
                float a = i * GoldenAngleRad + (float)rng.NextDouble() * 0.2f;
                Vector3 bEnd = fork + new Vector3(MathF.Cos(a) * 3.8f * sMult, 2.8f * hMult, MathF.Sin(a) * 3.8f * sMult);
                AddTaperedCylinder(st, fork, bEnd, baseR * 0.34f, baseR * 0.12f, 4, bark, bark);
                AddCurvedLeafSprigCluster(st, bEnd, crownCenter, 2.4f * sMult, 2, leafType: 2, rng, 0.14f);
            }
        }

        private static void BuildBaobabTree(SurfaceTool st, Random rng, float hMult, float sMult, float rMult)
        {
            var bark = new Color(0.48f, 0.35f, 0.25f, 0.0f);
            float h = 9.5f * hMult;
            float r = 1.45f * rMult;
            Vector3 mid = new Vector3(0.0f, h * 0.48f, 0.0f);
            Vector3 top = new Vector3(0.0f, h, 0.0f);
            AddTaperedCylinder(st, Vector3.Zero, mid, r, r * 1.25f, 7, bark, bark);
            AddTaperedCylinder(st, mid, top, r * 1.25f, r * 0.72f, 7, bark, bark);

            Vector3 crownCenter = top + new Vector3(0.0f, 2.2f * hMult, 0.0f);
            for (int i = 0; i < 4; i++)
            {
                float a = i * GoldenAngleRad + 0.3f;
                Vector3 tip = top + new Vector3(MathF.Cos(a) * 3.2f * sMult, 2.4f * hMult, MathF.Sin(a) * 3.2f * sMult);
                AddTaperedCylinder(st, top, tip, r * 0.24f, r * 0.09f, 4, bark, bark);
                AddCurvedLeafSprigCluster(st, tip, crownCenter, 2.2f * sMult, 2, leafType: 2, rng, 0.14f);
            }
        }

        private static void BuildColumnarPalmFern(SurfaceTool st, Random rng, float hMult, bool isFern)
        {
            float h = (isFern ? 3.5f : 6.2f) * hMult;
            float lean = (isFern ? 0.35f : 0.75f);
            Vector3 p0 = Vector3.Zero;
            Vector3 p1 = new Vector3(lean * 0.35f, h * 0.5f, lean * 0.15f);
            Vector3 p2 = new Vector3(lean, h, lean * 0.35f);

            AddTaperedCylinder(st, p0, p1, isFern ? 0.20f : 0.24f, isFern ? 0.15f : 0.18f, 5,
                new Color(0.34f, 0.26f, 0.18f, 0.0f), new Color(0.38f, 0.29f, 0.20f, 0.30f));
            AddTaperedCylinder(st, p1, p2, isFern ? 0.15f : 0.18f, isFern ? 0.10f : 0.12f, 5,
                new Color(0.38f, 0.29f, 0.20f, 0.30f), new Color(0.40f, 0.31f, 0.21f, 0.46f));

            int fronds = isFern ? 9 : 10;
            float frondLen = (isFern ? 2.2f : 3.0f) * hMult;
            for (int f = 0; f < fronds; f++)
            {
                float ang = f * Mathf.Tau / fronds + (float)rng.NextDouble() * 0.15f;
                Vector3 dir = new Vector3(MathF.Cos(ang), 0.0f, MathF.Sin(ang));
                Vector3 perp = new Vector3(-dir.Z, 0.0f, dir.X) * (isFern ? 0.58f : 0.72f);
                Vector3 mid = p2 + dir * (frondLen * 0.52f) + new Vector3(0.0f, 0.65f, 0.0f);
                Vector3 tip = p2 + dir * frondLen + new Vector3(0.0f, -0.55f, 0.0f);

                var cRoot = new Color(0.75f, 0.85f, 0.70f, 0.44f);
                var cTip = new Color(1.0f, 1.0f, 0.94f, 0.54f);
                AddSprigQuad(st, p2 - perp, p2 + perp, mid + perp, mid - perp, cRoot, cTip, Vector3.Up, 3, new Vector2(0.0f, 0.5f));
                AddSprigQuad(st, mid - perp, mid + perp, tip + perp * 0.6f, tip - perp * 0.6f, cTip, cTip, (dir + Vector3.Up).Normalized(), 3, new Vector2(0.5f, 1.0f));
            }
        }

        // Compact Curved Leaf Sprigs (2 angled quads per sprig = subtle 3D arch, low overdraw!)
        private static void AddCurvedLeafSprigCluster(
            SurfaceTool st, Vector3 pos, Vector3 crownCenter, float radius, int sprigCount, int leafType, Random rng, float windFlex)
        {
            var cBot = new Color(0.78f, 0.84f, 0.74f, windFlex * 0.75f);
            var cTop = new Color(1.0f, 1.0f, 0.95f, windFlex);
            Vector3 radialN = (pos - crownCenter + new Vector3(0.0f, 1.0f, 0.0f)).Normalized();

            for (int i = 0; i < sprigCount; i++)
            {
                float a = (float)(rng.NextDouble() * Mathf.Tau);
                float tilt = 0.25f + (float)rng.NextDouble() * 0.45f;
                Vector3 right = new Vector3(MathF.Cos(a), 0.0f, MathF.Sin(a)) * radius;
                Vector3 fwd = new Vector3(-MathF.Sin(a), tilt, MathF.Cos(a)).Normalized() * (radius * 0.85f);
                Vector3 archUp = Vector3.Up * (radius * 0.22f);

                // Two-segment curved sprig (bends slightly downward at tips)
                Vector3 pL0 = pos - right - fwd;
                Vector3 pR0 = pos + right - fwd;
                Vector3 pLM = pos - right + archUp;
                Vector3 pRM = pos + right + archUp;
                Vector3 pL1 = pos - right + fwd - archUp * 0.4f;
                Vector3 pR1 = pos + right + fwd - archUp * 0.4f;

                AddSprigQuad(st, pL0, pR0, pRM, pLM, cBot, cTop, radialN, leafType, new Vector2(0.0f, 0.5f));
                AddSprigQuad(st, pLM, pRM, pR1, pL1, cTop, cBot, radialN, leafType, new Vector2(0.5f, 1.0f));
            }
        }

        private static void AddSprigQuad(
            SurfaceTool st, Vector3 p0, Vector3 p1, Vector3 p2, Vector3 p3,
            Color cBot, Color cTop, Vector3 radialNormal, int leafType, Vector2 vRange)
        {
            // UV2.x = 1.0 -> Leaf Alpha Cutout, UV2.y = leafType (0=Broadleaf, 1=Conifer, 2=Acacia, 3=PalmFern)
            Vector2 leafTag = new Vector2(1.0f, leafType);
            Vector2 uv0 = new Vector2(0.0f, vRange.X);
            Vector2 uv1 = new Vector2(1.0f, vRange.X);
            Vector2 uv2 = new Vector2(1.0f, vRange.Y);
            Vector2 uv3 = new Vector2(0.0f, vRange.Y);

            void Emit(Vector3 p, Color c, Vector2 uv)
            {
                st.SetNormal(radialNormal);
                st.SetColor(c);
                st.SetUV(uv);
                st.SetUV2(leafTag);
                st.AddVertex(p);
            }

            Emit(p0, cBot, uv0); Emit(p1, cBot, uv1); Emit(p2, cTop, uv2);
            Emit(p0, cBot, uv0); Emit(p2, cTop, uv2); Emit(p3, cTop, uv3);
        }

        private static void AddTaperedCylinder(
            SurfaceTool st, Vector3 botCenter, Vector3 topCenter, float rBot, float rTop, int sides,
            Color cBot, Color cTop)
        {
            Vector3 axis = (topCenter - botCenter).Normalized();
            if (axis.LengthSquared() < 0.001f) return;
            Vector3 refVec = MathF.Abs(axis.Y) < 0.9f ? Vector3.Up : Vector3.Right;
            Vector3 tangent = axis.Cross(refVec).Normalized();
            Vector3 bitangent = axis.Cross(tangent).Normalized();

            var ringBot = new Vector3[sides];
            var ringTop = new Vector3[sides];
            var ringNorm = new Vector3[sides];
            for (int i = 0; i < sides; i++)
            {
                float a = i * Mathf.Tau / sides;
                Vector3 dir = tangent * MathF.Cos(a) + bitangent * MathF.Sin(a);
                ringBot[i] = botCenter + dir * rBot;
                ringTop[i] = topCenter + dir * rTop;
                ringNorm[i] = dir;
            }
            Vector2 barkTag = new Vector2(0.0f, 0.0f);

            void EmitBark(Vector3 p, Vector3 n, Color c, Vector2 uv)
            {
                st.SetNormal(n);
                st.SetColor(c);
                st.SetUV(uv);
                st.SetUV2(barkTag);
                st.AddVertex(p);
            }

            for (int i = 0; i < sides; i++)
            {
                int next = (i + 1) % sides;
                float u0 = i / (float)sides;
                float u1 = (i + 1) / (float)sides;
                EmitBark(ringBot[i], ringNorm[i], cBot, new Vector2(u0, 0f));
                EmitBark(ringBot[next], ringNorm[next], cBot, new Vector2(u1, 0f));
                EmitBark(ringTop[next], ringNorm[next], cTop, new Vector2(u1, 2f));

                EmitBark(ringBot[i], ringNorm[i], cBot, new Vector2(u0, 0f));
                EmitBark(ringTop[next], ringNorm[next], cTop, new Vector2(u1, 2f));
                EmitBark(ringTop[i], ringNorm[i], cTop, new Vector2(u0, 2f));
            }
        }
    }
}
