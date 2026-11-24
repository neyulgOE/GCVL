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
    /// Biological Recursive Branching Tree Builder with 3-Tier LOD (LOD0 full, LOD1 mid, LOD2 far dome)
    /// and Baked 3D Canopy Ambient Occlusion (Canopy AO stored in UV2.x [0.52..1.08]).
    /// - UV2.x == 0.0: Woody Bark (UV2.y: 0=mossy forest bark, 1=pale birch bark, 2=dry desert/steppe bark)
    /// - UV2.x >= 0.50: Botanical Alpha-Cutout Leaf Sprig (UV2.x = CanopyAO, UV2.y = LeafType:
    ///   0=Evergreen Broadleaf, 1=Conifer, 2=Deciduous Ginkgo/Birch, 3=Palm/Fern/Moss, 4=Deciduous Maple, 5=Xeric Umbrella/Baobab)
    /// </summary>
    public static class ProceduralTreeBuilder
    {
        private const float GoldenAngleRad = 2.39996323f; // 137.508°

        public static ArrayMesh BuildTree(FloraSpeciesId species, AgeStage age, int seed, int lod = 0)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var rng = new Random(seed * 7919 + (int)species * 131 + (int)age * 37);

            float ageHeightMult = age switch { AgeStage.Young => 0.68f, AgeStage.Mature => 1.0f, _ => 1.24f };
            float ageSpreadMult = age switch { AgeStage.Young => 0.72f, AgeStage.Mature => 1.0f, _ => 1.30f };
            float ageRadiusMult = age switch { AgeStage.Young => 0.65f, AgeStage.Mature => 1.0f, _ => 1.38f };

            if (lod >= 2 && species != FloraSpeciesId.ArborescentTreeFern && species != FloraSpeciesId.NipaWaterPalm)
            {
                BuildFarLod2Tree(st, species, ageHeightMult, ageSpreadMult, ageRadiusMult);
                return st.Commit();
            }

            switch (species)
            {
                case FloraSpeciesId.PrimevalBanyanFig:
                case FloraSpeciesId.SacredAncientHardwood:
                    BuildButtressBroadleaf(st, rng, age, ageHeightMult, ageSpreadMult, ageRadiusMult,
                        withPropRoots: species == FloraSpeciesId.PrimevalBanyanFig, lod);
                    break;

                case FloraSpeciesId.GinkgoAncientGold:
                    BuildDeciduousTree(st, rng, ageHeightMult, ageSpreadMult, ageRadiusMult, leafType: 2, barkMode: 2, lod);
                    break;
                case FloraSpeciesId.CrimsonSteppeMaple:
                    BuildDeciduousTree(st, rng, ageHeightMult, ageSpreadMult, ageRadiusMult, leafType: 4, barkMode: 2, lod);
                    break;
                case FloraSpeciesId.StarAppleCanopy:
                    BuildDeciduousTree(st, rng, ageHeightMult, ageSpreadMult, ageRadiusMult, leafType: 0, barkMode: 0, lod);
                    break;

                case FloraSpeciesId.WeepingRiverWillow:
                    BuildWeepingTree(st, rng, ageHeightMult, ageSpreadMult, ageRadiusMult, paleBark: false, leafType: 0, lod);
                    break;
                case FloraSpeciesId.WeepingSilverBirch:
                    BuildWeepingTree(st, rng, ageHeightMult, ageSpreadMult, ageRadiusMult, paleBark: true, leafType: 2, lod);
                    break;

                case FloraSpeciesId.BorealSnowPine:
                case FloraSpeciesId.SilverGlacierSpruce:
                case FloraSpeciesId.GiantSequoiaReddawn:
                    BuildConiferTree(st, rng, ageHeightMult, ageSpreadMult, ageRadiusMult,
                        isSequoia: species == FloraSpeciesId.GiantSequoiaReddawn, lod);
                    break;

                case FloraSpeciesId.DragonBloodTree:
                case FloraSpeciesId.SavannaUmbrellaAcacia:
                    BuildUmbrellaTree(st, rng, ageHeightMult, ageSpreadMult, ageRadiusMult, lod);
                    break;

                case FloraSpeciesId.BaobabPrehistoric:
                    BuildBaobabTree(st, rng, ageHeightMult, ageSpreadMult, ageRadiusMult, lod);
                    break;

                case FloraSpeciesId.ArborescentTreeFern:
                case FloraSpeciesId.NipaWaterPalm:
                    BuildColumnarPalmFern(st, rng, ageHeightMult, isFern: species == FloraSpeciesId.ArborescentTreeFern, lod);
                    break;

                default:
                    BuildDeciduousTree(st, rng, ageHeightMult, ageSpreadMult, ageRadiusMult, leafType: 0, barkMode: 0, lod);
                    break;
            }

            return st.Commit();
        }

        // Ultra-light LOD2 (460m - 1350m): 18-22 tris volumetric canopy dome with baked 3D Canopy AO + trunk silhouette
        private static void BuildFarLod2Tree(SurfaceTool st, FloraSpeciesId sp, float hMult, float sMult, float rMult)
        {
            int leafType = sp switch
            {
                FloraSpeciesId.BorealSnowPine or FloraSpeciesId.SilverGlacierSpruce or FloraSpeciesId.GiantSequoiaReddawn => 1,
                FloraSpeciesId.GinkgoAncientGold or FloraSpeciesId.WeepingSilverBirch => 2,
                FloraSpeciesId.CrimsonSteppeMaple => 4,
                FloraSpeciesId.DragonBloodTree or FloraSpeciesId.SavannaUmbrellaAcacia or FloraSpeciesId.BaobabPrehistoric => 5,
                _ => 0,
            };
            int barkMode = sp == FloraSpeciesId.WeepingSilverBirch ? 1 : (leafType >= 2 ? 2 : 0);

            bool isEmergent = sp == FloraSpeciesId.PrimevalBanyanFig || sp == FloraSpeciesId.SacredAncientHardwood || sp == FloraSpeciesId.GiantSequoiaReddawn;
            bool isConifer = leafType == 1;
            bool isUmbrella = leafType == 5;

            float totalH = (sp == FloraSpeciesId.GiantSequoiaReddawn ? 25.0f : (isEmergent ? 21.0f : (isConifer ? 15.0f : 12.0f))) * hMult;
            float trunkTopY = isConifer ? totalH * 0.85f : totalH * 0.62f;
            float baseR = (isEmergent ? 1.05f : (sp == FloraSpeciesId.BaobabPrehistoric ? 1.45f : 0.50f)) * rMult;

            var barkCol = barkMode == 1 ? new Color(0.86f, 0.85f, 0.82f, 0.0f) : new Color(0.32f, 0.23f, 0.16f, 0.0f);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, trunkTopY, 0.0f), baseR, baseR * 0.35f, 4, barkCol, barkCol, barkMode);

            float crownR = (isEmergent ? 6.8f : (isUmbrella ? 5.6f : (isConifer ? 3.5f : 4.6f))) * sMult;
            float crownHalfH = (isConifer ? totalH * 0.38f : (isUmbrella ? 1.8f : totalH * 0.28f));
            Vector3 crownCenter = new Vector3(0.0f, isConifer ? totalH * 0.58f : totalH * 0.72f, 0.0f);

            // 3 crossed + tilted volumetric crown planes (6 triangles total for crown) with deep bottom AO -> sunlit top AO
            for (int i = 0; i < 3; i++)
            {
                float a = i * (Mathf.Pi / 3.0f) + 0.25f;
                Vector3 right = new Vector3(MathF.Cos(a), 0.0f, MathF.Sin(a)) * crownR;
                Vector3 tilt = new Vector3(-MathF.Sin(a), 0.0f, MathF.Cos(a)) * (crownR * 0.18f);
                Vector3 botL = crownCenter - right - new Vector3(0.0f, crownHalfH, 0.0f) - tilt;
                Vector3 botR = crownCenter + right - new Vector3(0.0f, crownHalfH, 0.0f) - tilt;
                Vector3 topR = crownCenter + right * (isConifer ? 0.35f : 0.92f) + new Vector3(0.0f, crownHalfH, 0.0f) + tilt;
                Vector3 topL = crownCenter - right * (isConifer ? 0.35f : 0.92f) + new Vector3(0.0f, crownHalfH, 0.0f) + tilt;

                Vector3 nrm = (new Vector3(-MathF.Sin(a), 0.65f, MathF.Cos(a))).Normalized();
                var cWhite = new Color(1f, 1f, 1f, 0.12f);
                AddSprigQuad(st, botL, botR, topR, topL, cWhite, cWhite, nrm, leafType, new Vector2(1.0f, 0.0f), aoBot: 0.56f, aoTop: 1.04f);
            }
        }

        private static void BuildButtressBroadleaf(
            SurfaceTool st, Random rng, AgeStage age, float hMult, float sMult, float rMult, bool withPropRoots, int lod)
        {
            var barkBot = new Color(0.28f, 0.21f, 0.14f, 0.0f);
            var barkTop = new Color(0.36f, 0.27f, 0.18f, 0.02f);

            float trunkH = 11.8f * hMult;
            float baseR = 1.18f * rMult;
            float topR = baseR * 0.50f;

            Vector3 p0 = Vector3.Zero;
            Vector3 p1 = new Vector3((float)(rng.NextDouble() - 0.5) * 0.85f, trunkH * 0.52f, (float)(rng.NextDouble() - 0.5) * 0.85f);
            Vector3 p2 = new Vector3((float)(rng.NextDouble() - 0.5) * 1.15f, trunkH, (float)(rng.NextDouble() - 0.5) * 1.15f);
            int cylSides = lod == 0 ? 7 : 5;
            AddTaperedCylinder(st, p0, p1, baseR, (baseR + topR) * 0.52f, cylSides, barkBot, barkTop, 0);
            AddTaperedCylinder(st, p1, p2, (baseR + topR) * 0.52f, topR, cylSides - 1, barkBot, barkTop, 0);

            int buttresses = lod == 0 ? (age == AgeStage.Young ? 3 : 5) : 3;
            for (int r = 0; r < buttresses; r++)
            {
                float a = r * Mathf.Tau / buttresses + (float)rng.NextDouble() * 0.35f;
                Vector3 foot = new Vector3(MathF.Cos(a) * (baseR * 2.25f), -0.15f, MathF.Sin(a) * (baseR * 2.25f));
                Vector3 join = new Vector3(MathF.Cos(a) * (baseR * 0.55f), trunkH * 0.36f, MathF.Sin(a) * (baseR * 0.55f));
                AddTaperedCylinder(st, foot, join, baseR * 0.38f, baseR * 0.16f, 4, barkBot, barkTop, 0);
            }

            if (lod == 0 && withPropRoots && age != AgeStage.Young)
            {
                for (int r = 0; r < 3; r++)
                {
                    float a = r * GoldenAngleRad + (float)rng.NextDouble();
                    float dist = 3.4f * sMult;
                    AddTaperedCylinder(st, new Vector3(MathF.Cos(a) * dist, -0.1f, MathF.Sin(a) * dist),
                        p2 + new Vector3(MathF.Cos(a) * dist * 0.82f, -0.6f, MathF.Sin(a) * dist * 0.82f),
                        0.16f, 0.11f, 4, barkBot, barkTop, 0);
                }
            }

            // Wide exposed primary limbs with airy gaps between sub-crowns so dark mossy branches show clearly!
            Vector3 crownCenter = p2 + new Vector3(0.0f, 4.4f * hMult, 0.0f);
            float crownRad = 7.4f * sMult;
            float crownHalfH = 4.6f * hMult;

            int primaryCount = age == AgeStage.Young ? 4 : 5;
            float childR = topR / MathF.Sqrt(primaryCount * 0.65f);

            for (int i = 0; i < primaryCount; i++)
            {
                float azim = i * GoldenAngleRad + (float)rng.NextDouble() * 0.28f;
                float elev = 0.38f + (i % 2) * 0.18f + (float)rng.NextDouble() * 0.16f;
                Vector3 dir = new Vector3(MathF.Cos(azim) * MathF.Cos(elev), MathF.Sin(elev), MathF.Sin(azim) * MathF.Cos(elev)).Normalized();
                float len = (6.2f + (float)rng.NextDouble() * 2.2f) * sMult;
                Vector3 bEnd = p2 + dir * len;
                AddTaperedCylinder(st, p2, bEnd, childR, childR * 0.54f, lod == 0 ? 5 : 4, barkTop, barkTop, 0);

                if (lod == 0)
                {
                    float subR = childR * 0.44f;
                    for (int s = 0; s < 2; s++)
                    {
                        float sAz = azim + (s == 0 ? -0.72f : 0.72f) + (float)(rng.NextDouble() - 0.5) * 0.25f;
                        Vector3 sDir = new Vector3(MathF.Cos(sAz), 0.38f + (float)rng.NextDouble() * 0.30f, MathF.Sin(sAz)).Normalized();
                        Vector3 sEnd = bEnd + sDir * (3.0f * sMult);
                        AddTaperedCylinder(st, bEnd, sEnd, subR, subR * 0.42f, 4, barkTop, barkTop, 0);
                        AddCurvedLeafSprigCluster(st, sEnd, crownCenter, crownRad, crownHalfH, 1.48f * sMult, 3, leafType: 0, rng, 0.14f);
                    }
                    AddCurvedLeafSprigCluster(st, bEnd + Vector3.Up * 0.5f, crownCenter, crownRad, crownHalfH, 1.55f * sMult, 2, leafType: 0, rng, 0.14f);

                    if (age != AgeStage.Young)
                    {
                        Vector3 midLimb = p2.Lerp(bEnd, 0.55f);
                        float drapeLen = (2.0f + (float)rng.NextDouble() * 1.6f) * hMult;
                        Vector3 side = new Vector3(-MathF.Sin(azim), 0.0f, MathF.Cos(azim)) * 0.52f;
                        var cDrape = new Color(0.82f, 0.92f, 0.72f, 0.38f);
                        AddSprigQuad(st, midLimb - side, midLimb + side, midLimb + side - Vector3.Up * drapeLen, midLimb - side - Vector3.Up * drapeLen,
                            cDrape, cDrape, Vector3.Up, leafType: 3, new Vector2(0.0f, 1.0f), aoBot: 0.62f, aoTop: 0.78f);
                    }
                }
                else
                {
                    AddCurvedLeafSprigCluster(st, bEnd + Vector3.Up * 0.6f, crownCenter, crownRad, crownHalfH, 2.25f * sMult, 2, leafType: 0, rng, 0.14f);
                }
            }
            AddCurvedLeafSprigCluster(st, crownCenter + Vector3.Up * (2.0f * hMult), crownCenter, crownRad, crownHalfH,
                (lod == 0 ? 1.85f : 2.35f) * sMult, lod == 0 ? 3 : 2, leafType: 0, rng, 0.15f);
        }

        private static void BuildDeciduousTree(
            SurfaceTool st, Random rng, float hMult, float sMult, float rMult, int leafType, int barkMode, int lod)
        {
            var barkBot = new Color(0.32f, 0.24f, 0.17f, 0.0f);
            var barkTop = new Color(0.39f, 0.30f, 0.22f, 0.02f);

            float trunkH = 6.4f * hMult;
            float baseR = 0.54f * rMult;
            float topR = baseR * 0.54f;

            Vector3 p1 = new Vector3((float)(rng.NextDouble() - 0.5) * 0.55f, trunkH * 0.52f, (float)(rng.NextDouble() - 0.5) * 0.55f);
            Vector3 p2 = new Vector3((float)(rng.NextDouble() - 0.5) * 0.75f, trunkH, (float)(rng.NextDouble() - 0.5) * 0.75f);
            AddTaperedCylinder(st, Vector3.Zero, p1, baseR, (baseR + topR) * 0.52f, lod == 0 ? 6 : 4, barkBot, barkTop, barkMode);
            AddTaperedCylinder(st, p1, p2, (baseR + topR) * 0.52f, topR, lod == 0 ? 5 : 4, barkBot, barkTop, barkMode);

            Vector3 crownCenter = p2 + new Vector3(0.0f, 3.6f * hMult, 0.0f);
            float crownRad = 5.0f * sMult;
            float crownHalfH = 3.8f * hMult;

            const int branches = 5;
            float childR = topR / MathF.Sqrt(branches * 0.65f);

            for (int i = 0; i < branches; i++)
            {
                float azim = i * GoldenAngleRad + (float)rng.NextDouble() * 0.25f;
                float elev = 0.46f + (i % 2) * 0.18f + (float)rng.NextDouble() * 0.18f;
                Vector3 dir = new Vector3(MathF.Cos(azim) * MathF.Cos(elev), MathF.Sin(elev), MathF.Sin(azim) * MathF.Cos(elev)).Normalized();
                Vector3 bEnd = p2 + dir * (4.5f * sMult);
                AddTaperedCylinder(st, p2, bEnd, childR, childR * 0.48f, 4, barkTop, barkTop, barkMode);

                if (lod == 0)
                {
                    for (int s = 0; s < 2; s++)
                    {
                        float sAz = azim + (s == 0 ? -0.68f : 0.68f);
                        Vector3 sEnd = bEnd + new Vector3(MathF.Cos(sAz), 0.44f, MathF.Sin(sAz)).Normalized() * (2.2f * sMult);
                        AddTaperedCylinder(st, bEnd, sEnd, childR * 0.46f, childR * 0.20f, 4, barkTop, barkTop, barkMode);
                        AddCurvedLeafSprigCluster(st, sEnd, crownCenter, crownRad, crownHalfH, 1.55f * sMult, 2, leafType, rng, 0.15f);
                    }
                    AddCurvedLeafSprigCluster(st, bEnd + Vector3.Up * 0.4f, crownCenter, crownRad, crownHalfH, 1.60f * sMult, 2, leafType, rng, 0.15f);
                }
                else
                {
                    AddCurvedLeafSprigCluster(st, bEnd + dir * (1.2f * sMult), crownCenter, crownRad, crownHalfH, 2.15f * sMult, 2, leafType, rng, 0.15f);
                }
            }
            AddCurvedLeafSprigCluster(st, crownCenter + Vector3.Up * (1.6f * hMult), crownCenter, crownRad, crownHalfH,
                (lod == 0 ? 1.80f : 2.25f) * sMult, 2, leafType, rng, 0.16f);
        }

        private static void BuildWeepingTree(
            SurfaceTool st, Random rng, float hMult, float sMult, float rMult, bool paleBark, int leafType, int lod)
        {
            var barkBot = paleBark ? new Color(0.88f, 0.87f, 0.84f, 0.0f) : new Color(0.29f, 0.22f, 0.15f, 0.0f);
            var barkTop = paleBark ? new Color(0.94f, 0.93f, 0.90f, 0.02f) : new Color(0.35f, 0.27f, 0.19f, 0.02f);
            int barkMode = paleBark ? 1 : 0;

            float trunkH = 6.6f * hMult;
            float baseR = 0.50f * rMult;
            Vector3 p1 = new Vector3(0.35f * sMult, trunkH * 0.5f, 0.12f * sMult);
            Vector3 p2 = new Vector3(0.85f * sMult, trunkH, 0.30f * sMult);
            AddTaperedCylinder(st, Vector3.Zero, p1, baseR, baseR * 0.68f, lod == 0 ? 6 : 4, barkBot, barkTop, barkMode);
            AddTaperedCylinder(st, p1, p2, baseR * 0.68f, baseR * 0.44f, 4, barkBot, barkTop, barkMode);

            Vector3 crownCenter = p2 + new Vector3(0.0f, 2.2f * hMult, 0.0f);
            float crownRad = 4.6f * sMult;
            float crownHalfH = 3.4f * hMult;

            for (int i = 0; i < 5; i++)
            {
                float azim = i * GoldenAngleRad;
                Vector3 bArch = p2 + new Vector3(MathF.Cos(azim) * 3.4f * sMult, 2.4f * hMult, MathF.Sin(azim) * 3.4f * sMult);
                AddTaperedCylinder(st, p2, bArch, baseR * 0.34f, baseR * 0.13f, 4, barkTop, barkTop, barkMode);
                if (lod == 0)
                {
                    Vector3 droop = bArch + new Vector3(MathF.Cos(azim) * 0.9f * sMult, -1.5f * hMult, MathF.Sin(azim) * 0.9f * sMult);
                    AddTaperedCylinder(st, bArch, droop, baseR * 0.13f, baseR * 0.06f, 3, barkTop, barkTop, barkMode);
                    AddCurvedLeafSprigCluster(st, droop, crownCenter, crownRad, crownHalfH, 1.85f * sMult, 3, leafType, rng, 0.18f);
                }
                else
                {
                    AddCurvedLeafSprigCluster(st, bArch + new Vector3(0, -0.8f, 0), crownCenter, crownRad, crownHalfH, 2.25f * sMult, 2, leafType, rng, 0.17f);
                }
            }
            AddCurvedLeafSprigCluster(st, crownCenter + Vector3.Up * 1.2f, crownCenter, crownRad, crownHalfH, 1.85f * sMult, 2, leafType, rng, 0.16f);
        }

        private static void BuildConiferTree(
            SurfaceTool st, Random rng, float hMult, float sMult, float rMult, bool isSequoia, int lod)
        {
            var barkBot = isSequoia ? new Color(0.40f, 0.19f, 0.11f, 0.0f) : new Color(0.25f, 0.18f, 0.13f, 0.0f);
            var barkTop = isSequoia ? new Color(0.45f, 0.23f, 0.14f, 0.03f) : new Color(0.30f, 0.21f, 0.15f, 0.03f);

            float totalH = (isSequoia ? 24.5f : 15.2f) * hMult;
            float baseR = (isSequoia ? 1.15f : 0.48f) * rMult;
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, totalH, 0.0f), baseR, 0.08f, lod == 0 ? 6 : 4, barkBot, barkTop, 2);

            int tiers = lod == 0 ? (isSequoia ? 5 : 6) : 4;
            float startFrac = isSequoia ? 0.46f : 0.24f;
            Vector3 crownCenter = new Vector3(0.0f, totalH * 0.60f, 0.0f);
            float crownRad = (isSequoia ? 5.2f : 3.8f) * sMult;
            float crownHalfH = totalH * 0.38f;

            for (int t = 0; t < tiers; t++)
            {
                float frac = startFrac + (t / (float)(tiers - 1)) * (0.94f - startFrac);
                float y = totalH * frac;
                float tierRadius = (1.0f - (t / (float)tiers) * 0.72f) * (isSequoia ? 4.9f : 3.6f) * sMult;
                int bCount = lod == 0 ? (t < tiers - 2 ? 4 : 3) : 3;
                for (int b = 0; b < bCount; b++)
                {
                    float a = b * (Mathf.Tau / bCount) + t * GoldenAngleRad;
                    Vector3 bStart = new Vector3(0.0f, y, 0.0f);
                    Vector3 bEnd = new Vector3(MathF.Cos(a) * tierRadius, y - tierRadius * 0.24f, MathF.Sin(a) * tierRadius);
                    if (lod == 0)
                        AddTaperedCylinder(st, bStart, bEnd, 0.12f * rMult, 0.04f, 4, barkTop, barkTop, 2);
                    AddCurvedLeafSprigCluster(st, bEnd, crownCenter, crownRad, crownHalfH,
                        (lod == 0 ? 1.75f : 2.20f) * sMult, lod == 0 ? 2 : 1, leafType: 1, rng, 0.13f);
                }
            }
            AddCurvedLeafSprigCluster(st, new Vector3(0.0f, totalH + 0.35f, 0.0f), crownCenter, crownRad, crownHalfH, 1.45f * sMult, 2, leafType: 1, rng, 0.14f);
        }

        private static void BuildUmbrellaTree(SurfaceTool st, Random rng, float hMult, float sMult, float rMult, int lod)
        {
            var bark = new Color(0.42f, 0.31f, 0.22f, 0.0f);
            float trunkH = 5.6f * hMult;
            float baseR = 0.65f * rMult;
            Vector3 fork = new Vector3((float)(rng.NextDouble() - 0.5) * 0.6f, trunkH, (float)(rng.NextDouble() - 0.5) * 0.6f);
            AddTaperedCylinder(st, Vector3.Zero, fork, baseR, baseR * 0.54f, lod == 0 ? 6 : 4, bark, bark, 2);

            Vector3 crownCenter = fork + new Vector3(0.0f, 2.8f * hMult, 0.0f);
            float crownRad = 5.6f * sMult;
            float crownHalfH = 1.9f * hMult;

            int limbs = lod == 0 ? 5 : 4;
            for (int i = 0; i < limbs; i++)
            {
                float a = i * GoldenAngleRad + (float)rng.NextDouble() * 0.2f;
                Vector3 bEnd = fork + new Vector3(MathF.Cos(a) * 4.0f * sMult, 2.8f * hMult, MathF.Sin(a) * 4.0f * sMult);
                AddTaperedCylinder(st, fork, bEnd, baseR * 0.36f, baseR * 0.13f, 4, bark, bark, 2);
                AddCurvedLeafSprigCluster(st, bEnd, crownCenter, crownRad, crownHalfH, (lod == 0 ? 2.15f : 2.65f) * sMult, 2, leafType: 5, rng, 0.13f);
            }
            AddCurvedLeafSprigCluster(st, crownCenter + Vector3.Up * 0.6f, crownCenter, crownRad, crownHalfH, 2.2f * sMult, 2, leafType: 5, rng, 0.14f);
        }

        private static void BuildBaobabTree(SurfaceTool st, Random rng, float hMult, float sMult, float rMult, int lod)
        {
            var bark = new Color(0.48f, 0.36f, 0.26f, 0.0f);
            float h = 9.6f * hMult;
            float r = 1.50f * rMult;
            Vector3 mid = new Vector3(0.0f, h * 0.48f, 0.0f);
            Vector3 top = new Vector3(0.0f, h, 0.0f);
            int sides = lod == 0 ? 7 : 5;
            AddTaperedCylinder(st, Vector3.Zero, mid, r, r * 1.26f, sides, bark, bark, 2);
            AddTaperedCylinder(st, mid, top, r * 1.26f, r * 0.72f, sides, bark, bark, 2);

            Vector3 crownCenter = top + new Vector3(0.0f, 2.3f * hMult, 0.0f);
            float crownRad = 5.2f * sMult;
            float crownHalfH = 2.0f * hMult;

            for (int i = 0; i < 4; i++)
            {
                float a = i * GoldenAngleRad + 0.3f;
                Vector3 tip = top + new Vector3(MathF.Cos(a) * 3.4f * sMult, 2.4f * hMult, MathF.Sin(a) * 3.4f * sMult);
                AddTaperedCylinder(st, top, tip, r * 0.26f, r * 0.10f, 4, bark, bark, 2);
                AddCurvedLeafSprigCluster(st, tip, crownCenter, crownRad, crownHalfH, (lod == 0 ? 2.0f : 2.5f) * sMult, 2, leafType: 5, rng, 0.13f);
            }
        }

        private static void BuildColumnarPalmFern(SurfaceTool st, Random rng, float hMult, bool isFern, int lod)
        {
            float h = (isFern ? 3.5f : 6.2f) * hMult;
            float lean = (isFern ? 0.35f : 0.75f);
            Vector3 p0 = Vector3.Zero;
            Vector3 p1 = new Vector3(lean * 0.35f, h * 0.5f, lean * 0.15f);
            Vector3 p2 = new Vector3(lean, h, lean * 0.35f);

            AddTaperedCylinder(st, p0, p1, isFern ? 0.20f : 0.25f, isFern ? 0.15f : 0.19f, 5,
                new Color(0.34f, 0.26f, 0.18f, 0.0f), new Color(0.38f, 0.29f, 0.20f, 0.30f), 2);
            AddTaperedCylinder(st, p1, p2, isFern ? 0.15f : 0.19f, isFern ? 0.10f : 0.13f, 5,
                new Color(0.38f, 0.29f, 0.20f, 0.30f), new Color(0.40f, 0.31f, 0.21f, 0.46f), 2);

            int fronds = lod == 0 ? (isFern ? 9 : 10) : 6;
            float frondLen = (isFern ? 2.2f : 3.0f) * hMult;
            for (int f = 0; f < fronds; f++)
            {
                float ang = f * Mathf.Tau / fronds + (float)rng.NextDouble() * 0.15f;
                Vector3 dir = new Vector3(MathF.Cos(ang), 0.0f, MathF.Sin(ang));
                Vector3 perp = new Vector3(-dir.Z, 0.0f, dir.X) * (isFern ? 0.58f : 0.72f);
                Vector3 mid = p2 + dir * (frondLen * 0.52f) + new Vector3(0.0f, 0.65f, 0.0f);
                Vector3 tip = p2 + dir * frondLen + new Vector3(0.0f, -0.55f, 0.0f);

                var cRoot = new Color(1f, 1f, 1f, 0.44f);
                var cTip = new Color(1f, 1f, 1f, 0.54f);
                AddSprigQuad(st, p2 - perp, p2 + perp, mid + perp, mid - perp, cRoot, cTip, Vector3.Up, 3, new Vector2(0.0f, 0.5f), aoBot: 0.72f, aoTop: 0.96f);
                AddSprigQuad(st, mid - perp, mid + perp, tip + perp * 0.6f, tip - perp * 0.6f, cTip, cTip, (dir + Vector3.Up).Normalized(), 3, new Vector2(0.5f, 1.0f), aoBot: 0.96f, aoTop: 1.05f);
            }
        }

        // 3D Domed Botanical Sprigs with Baked 3D Canopy Ambient Occlusion (35-45% darker interior/underside -> sunlit top!)
        private static void AddCurvedLeafSprigCluster(
            SurfaceTool st,
            Vector3 pos,
            Vector3 crownCenter,
            float crownRadius,
            float crownHalfHeight,
            float sprigRadius,
            int sprigCount,
            int leafType,
            Random rng,
            float windFlex)
        {
            Vector3 radialN = (pos - crownCenter + new Vector3(0.0f, 1.1f, 0.0f)).Normalized();
            int totalPetals = Math.Max(2, sprigCount + 1);
            float baseYaw = (float)(rng.NextDouble() * Mathf.Tau);

            for (int i = 0; i < totalPetals; i++)
            {
                float a = baseYaw + i * (Mathf.Tau / totalPetals) + (float)(rng.NextDouble() - 0.5) * 0.28f;
                float innerLayerMul = i == 0 ? 0.84f : 1.0f;

                float w = sprigRadius * 0.86f;
                float len = sprigRadius * 1.50f;
                Vector3 dir = new Vector3(MathF.Cos(a), 0.34f + (i % 2) * 0.28f, MathF.Sin(a)).Normalized();
                Vector3 side = new Vector3(-MathF.Sin(a), 0.0f, MathF.Cos(a)) * w;
                Vector3 archUp = Vector3.Up * (sprigRadius * 0.26f);

                Vector3 root = pos - dir * (sprigRadius * 0.22f);
                Vector3 mid = root + dir * (len * 0.52f) + archUp;
                Vector3 tip = root + dir * len - archUp * 0.28f;

                float aoRoot = ComputeCanopyAo(root, crownCenter, crownRadius, crownHalfHeight) * innerLayerMul;
                float aoMid = ComputeCanopyAo(mid, crownCenter, crownRadius, crownHalfHeight) * innerLayerMul;
                float aoTip = ComputeCanopyAo(tip, crownCenter, crownRadius, crownHalfHeight);

                var cBot = new Color(1.0f, 1.0f, 1.0f, windFlex * 0.70f);
                var cTop = new Color(1.0f, 1.0f, 1.0f, windFlex);

                AddSprigQuad(st, root - side * 0.76f, root + side * 0.76f, mid + side, mid - side,
                    cBot, cTop, radialN, leafType, new Vector2(1.0f, 0.48f), aoRoot, aoMid);
                AddSprigQuad(st, mid - side, mid + side, tip + side * 0.84f, tip - side * 0.84f,
                    cTop, cTop, (radialN + dir * 0.42f).Normalized(), leafType, new Vector2(0.48f, 0.0f), aoMid, aoTip);
            }
        }

        private static float ComputeCanopyAo(Vector3 p, Vector3 crownCenter, float crownR, float crownHalfH)
        {
            float dx = p.X - crownCenter.X;
            float dz = p.Z - crownCenter.Z;
            float horizFrac = Math.Clamp(MathF.Sqrt(dx * dx + dz * dz) / MathF.Max(1.0f, crownR), 0.0f, 1.15f);
            float vertFrac = Math.Clamp((p.Y - (crownCenter.Y - crownHalfH)) / MathF.Max(1.5f, 2.0f * crownHalfH), 0.0f, 1.0f);

            // Inner/lower canopy = 0.54 (46% shaded), outer/upper crown = 1.06 (sunlit crest)
            float shell = horizFrac * horizFrac * (3.0f - 2.0f * Math.Clamp(horizFrac, 0.0f, 1.0f));
            return Math.Clamp(0.54f + 0.26f * shell + 0.26f * vertFrac, 0.54f, 1.06f);
        }

        private static void AddSprigQuad(
            SurfaceTool st, Vector3 p0, Vector3 p1, Vector3 p2, Vector3 p3,
            Color cBot, Color cTop, Vector3 radialNormal, int leafType, Vector2 vRange, float aoBot, float aoTop)
        {
            Vector2 tagBot = new Vector2(Math.Clamp(aoBot, 0.52f, 1.08f), leafType);
            Vector2 tagTop = new Vector2(Math.Clamp(aoTop, 0.52f, 1.08f), leafType);
            Vector2 uv0 = new Vector2(0.0f, vRange.X);
            Vector2 uv1 = new Vector2(1.0f, vRange.X);
            Vector2 uv2 = new Vector2(1.0f, vRange.Y);
            Vector2 uv3 = new Vector2(0.0f, vRange.Y);

            void Emit(Vector3 p, Color c, Vector2 uv, Vector2 tag)
            {
                st.SetNormal(radialNormal);
                st.SetColor(c);
                st.SetUV(uv);
                st.SetUV2(tag);
                st.AddVertex(p);
            }

            Emit(p0, cBot, uv0, tagBot); Emit(p1, cBot, uv1, tagBot); Emit(p2, cTop, uv2, tagTop);
            Emit(p0, cBot, uv0, tagBot); Emit(p2, cTop, uv2, tagTop); Emit(p3, cTop, uv3, tagTop);
        }

        private static void AddTaperedCylinder(
            SurfaceTool st, Vector3 botCenter, Vector3 topCenter, float rBot, float rTop, int sides,
            Color cBot, Color cTop, int barkMode)
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
            Vector2 barkTag = new Vector2(0.0f, barkMode);

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
