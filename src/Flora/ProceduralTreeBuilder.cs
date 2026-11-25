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
    /// Phase 1 Realistic Multi-Variant Tree Builder (Godot 4.7 Forward+, RTX 4060):
    /// - 2-Surface ArrayMesh for LOD0 & LOD1:
    ///   * Surface 0 = PBR Bark & Moss (shaders/bark_moss.gdshader, full tangents, deep -0.85m roots)
    ///   * Surface 1 = Botanical Foliage (shaders/flora_wind.gdshader, 3D Canopy AO in UV2.x, per-branch wind phase in COLOR.r)
    /// - 1-Surface Puffy Volumetric LOD2 (~44-64 tris): overlapping rounded crown puffs with baked AO for lush rolling hill vistas.
    /// - 4 Distinct Broadleaf Variants (A: Emergent Buttress Giant, B: Gnarled Mid-Canopy, C: Forest Sapling, D: Columnar Rainforest Giant)
    /// - 3 Distinct Conifer Variants, 2 Weeping Riparian/Birch Variants, 2 Desert Variants (restricted strictly to arid zones), 2 Palm/Fern Variants.
    /// </summary>
    public static class ProceduralTreeBuilder
    {
        private const float GoldenAngleRad = 2.39996323f; // 137.508 deg

        public static ArrayMesh BuildTree(FloraSpeciesId species, AgeStage age, int seed, int lod = 0, int variant = 0)
        {
            var rng = new Random(seed * 7919 + (int)species * 131 + (int)age * 37 + variant * 911);

            float ageHeightMult = age switch { AgeStage.Young => 0.72f, AgeStage.Mature => 1.0f, _ => 1.24f };
            float ageSpreadMult = age switch { AgeStage.Young => 0.75f, AgeStage.Mature => 1.0f, _ => 1.28f };
            float ageRadiusMult = age switch { AgeStage.Young => 0.68f, AgeStage.Mature => 1.0f, _ => 1.34f };

            if (lod >= 2 && species != FloraSpeciesId.ArborescentTreeFern && species != FloraSpeciesId.NipaWaterPalm &&
                species != FloraSpeciesId.OasisDatePalm && species != FloraSpeciesId.CoastalPandanusScrewpine &&
                species != FloraSpeciesId.ColumnarEuphorbiaCactus)
            {
                var stLod2 = new SurfaceTool();
                stLod2.Begin(Mesh.PrimitiveType.Triangles);
                BuildPuffyFarLod2Tree(stLod2, species, variant, ageHeightMult, ageSpreadMult, ageRadiusMult);
                return stLod2.Commit();
            }

            if (species == FloraSpeciesId.ColumnarEuphorbiaCactus)
            {
                var cactusSt = new SurfaceTool();
                cactusSt.Begin(Mesh.PrimitiveType.Triangles);
                BuildColumnarCactus(cactusSt, rng, ageHeightMult, ageRadiusMult, ((variant % 2) + 2) % 2, lod);
                cactusSt.GenerateTangents();
                return cactusSt.Commit(); // Single Surface 0 using bark_moss.gdshader (style=6, moss=0)
            }

            var barkSt = new SurfaceTool();
            barkSt.Begin(Mesh.PrimitiveType.Triangles);
            var leafSt = new SurfaceTool();
            leafSt.Begin(Mesh.PrimitiveType.Triangles);

            switch (species)
            {
                case FloraSpeciesId.PrimevalBanyanFig:
                case FloraSpeciesId.SacredAncientHardwood:
                case FloraSpeciesId.StarAppleCanopy:
                case FloraSpeciesId.GinkgoAncientGold:
                case FloraSpeciesId.CrimsonSteppeMaple:
                case FloraSpeciesId.PrimevalBeechGold:
                case FloraSpeciesId.PrimevalMagnolia:
                {
                    int leafType = species switch
                    {
                        FloraSpeciesId.GinkgoAncientGold or FloraSpeciesId.PrimevalBeechGold => 2,
                        FloraSpeciesId.CrimsonSteppeMaple => 4,
                        FloraSpeciesId.PrimevalMagnolia => 14, // specialty_atlas_b (0,0) left half
                        _ => 0,
                    };
                    Rect2? subUv = species == FloraSpeciesId.PrimevalMagnolia
                        ? new Rect2(0.004f, 0.004f, 0.242f, 0.492f)
                        : null;
                    int barkStyle = (species == FloraSpeciesId.PrimevalBanyanFig || species == FloraSpeciesId.SacredAncientHardwood) ? 4 : 0;
                    float mossMult = (leafType == 0 || leafType == 14) ? 1.05f : 0.45f;
                    int v = ((variant % 4) + 4) % 4;
                    if (v == 0)
                        BuildBroadleafVariantA_ButtressGiant(barkSt, leafSt, rng, ageHeightMult, ageSpreadMult, ageRadiusMult,
                            leafType, mossMult, withPropRoots: species == FloraSpeciesId.PrimevalBanyanFig, lod, barkStyle, subUv);
                    else if (v == 1)
                        BuildBroadleafVariantB_GnarledMidCanopy(barkSt, leafSt, rng, ageHeightMult, ageSpreadMult, ageRadiusMult,
                            leafType, mossMult, lod, barkStyle, subUv);
                    else if (v == 2)
                        BuildBroadleafVariantC_ForestSapling(barkSt, leafSt, rng, ageHeightMult, ageSpreadMult, ageRadiusMult,
                            leafType, mossMult, lod, barkStyle, subUv);
                    else
                        BuildBroadleafVariantD_ColumnarGiant(barkSt, leafSt, rng, ageHeightMult, ageSpreadMult, ageRadiusMult,
                            leafType, mossMult, lod, barkStyle, subUv);
                    break;
                }

                case FloraSpeciesId.AraucariaMonkeyPuzzle:
                    BuildAraucaria(barkSt, leafSt, rng, ageHeightMult, ageSpreadMult, ageRadiusMult, lod);
                    break;

                case FloraSpeciesId.SwampBaldCypress:
                    BuildSwampBaldCypress(barkSt, leafSt, rng, ageHeightMult, ageSpreadMult, ageRadiusMult, lod);
                    break;

                case FloraSpeciesId.AncientSteppeOak:
                    BuildSteppeOak(barkSt, leafSt, rng, ageHeightMult, ageSpreadMult, ageRadiusMult, lod);
                    break;

                case FloraSpeciesId.CoastalMangroveStilt:
                    BuildCoastalMangrove(barkSt, leafSt, rng, ageHeightMult, ageSpreadMult, ageRadiusMult, lod);
                    break;

                case FloraSpeciesId.CoastalPandanusScrewpine:
                    BuildPandanus(barkSt, leafSt, rng, ageHeightMult, lod);
                    break;

                case FloraSpeciesId.BorealSnowPine:
                case FloraSpeciesId.SilverGlacierSpruce:
                case FloraSpeciesId.GiantSequoiaReddawn:
                case FloraSpeciesId.TwistedSubalpineLarch:
                    BuildConiferVariant(barkSt, leafSt, rng, ageHeightMult, ageSpreadMult, ageRadiusMult,
                        isSequoia: species == FloraSpeciesId.GiantSequoiaReddawn,
                        isLarch: species == FloraSpeciesId.TwistedSubalpineLarch,
                        variant: ((variant % 3) + 3) % 3, lod);
                    break;

                case FloraSpeciesId.WeepingRiverWillow:
                case FloraSpeciesId.WeepingSilverBirch:
                    BuildWeepingVariant(barkSt, leafSt, rng, ageHeightMult, ageSpreadMult, ageRadiusMult,
                        paleBark: species == FloraSpeciesId.WeepingSilverBirch,
                        leafType: species == FloraSpeciesId.WeepingSilverBirch ? 2 : 5,
                        subUv: species == FloraSpeciesId.WeepingRiverWillow ? new Rect2(0.004f, 0.004f, 0.325f, 0.992f) : null,
                        variant: ((variant % 2) + 2) % 2, lod);
                    break;

                case FloraSpeciesId.DragonBloodTree:
                case FloraSpeciesId.SavannaUmbrellaAcacia:
                    BuildDesertUmbrellaVariant(barkSt, leafSt, rng, ageHeightMult, ageSpreadMult, ageRadiusMult,
                        variant: ((variant % 2) + 2) % 2, lod);
                    break;

                case FloraSpeciesId.BaobabPrehistoric:
                    BuildBaobabVariant(barkSt, leafSt, rng, ageHeightMult, ageSpreadMult, ageRadiusMult,
                        variant: ((variant % 2) + 2) % 2, lod);
                    break;

                case FloraSpeciesId.ArborescentTreeFern:
                case FloraSpeciesId.NipaWaterPalm:
                case FloraSpeciesId.OasisDatePalm:
                    BuildColumnarPalmFernVariant(barkSt, leafSt, rng,
                        species == FloraSpeciesId.OasisDatePalm ? ageHeightMult * 1.48f : ageHeightMult,
                        isFern: species == FloraSpeciesId.ArborescentTreeFern,
                        variant: ((variant % 2) + 2) % 2, lod);
                    break;

                default:
                    BuildBroadleafVariantB_GnarledMidCanopy(barkSt, leafSt, rng, ageHeightMult, ageSpreadMult, ageRadiusMult, 0, 1.0f, lod);
                    break;
            }

            barkSt.GenerateTangents();
            var mesh = new ArrayMesh();
            barkSt.Commit(mesh); // Surface 0: PBR Bark + Moss (bark_moss.gdshader)
            leafSt.Commit(mesh); // Surface 1: Botanical Foliage (flora_wind.gdshader)
            return mesh;
        }

        // =========================================================================
        // BROADLEAF VARIANT A: Emergent Buttress Giant (Puffy Multi-Tiered Rounded Crown)
        // LOD0: ~1,900-2,300 tris | LOD1: ~420 tris
        // =========================================================================
        private static void BuildBroadleafVariantA_ButtressGiant(
            SurfaceTool barkSt, SurfaceTool leafSt, Random rng,
            float hMult, float sMult, float rMult, int leafType, float mossMult, bool withPropRoots, int lod, int barkStyle = 0, Rect2? uvSubRect = null)
        {
            var barkBot = new Color(0.40f, 0.34f, 0.28f, 0.0f);
            var barkTop = new Color(0.46f, 0.40f, 0.34f, 0.03f);
            float trunkH = 12.2f * hMult;
            float baseR = 1.25f * rMult;
            float topR = baseR * 0.46f;
            int sides = lod == 0 ? 8 : 5;

            // Organic 4-segment trunk extending down to -0.85m so roots never float on slopes
            Vector3 p0 = new Vector3(0.0f, -0.85f, 0.0f);
            Vector3 p1 = new Vector3(0.28f * sMult, trunkH * 0.33f, -0.20f * sMult);
            Vector3 p2 = new Vector3(-0.32f * sMult, trunkH * 0.68f, 0.26f * sMult);
            Vector3 p3 = new Vector3(0.18f * sMult, trunkH, -0.15f * sMult);
            AddTaperedCylinder(barkSt, p0, p1, baseR * 1.18f, baseR * 0.82f, sides, barkBot, barkBot, barkStyle, mossMult);
            AddTaperedCylinder(barkSt, p1, p2, baseR * 0.82f, baseR * 0.62f, sides - 1, barkBot, barkTop, barkStyle, mossMult);
            AddTaperedCylinder(barkSt, p2, p3, baseR * 0.62f, topR, Math.Max(4, sides - 2), barkTop, barkTop, barkStyle, mossMult);

            // 6 deep flared buttress root fins gripping down to -0.85m
            int buttresses = lod == 0 ? 6 : 4;
            for (int r = 0; r < buttresses; r++)
            {
                float a = r * Mathf.Tau / buttresses + (float)rng.NextDouble() * 0.28f;
                float reach = baseR * (2.35f + (r % 2) * 0.45f);
                Vector3 foot = new Vector3(MathF.Cos(a) * reach, -0.85f, MathF.Sin(a) * reach);
                Vector3 knee = new Vector3(MathF.Cos(a) * reach * 0.56f, trunkH * 0.14f, MathF.Sin(a) * reach * 0.56f);
                Vector3 join = new Vector3(MathF.Cos(a) * baseR * 0.48f, trunkH * 0.36f, MathF.Sin(a) * baseR * 0.48f);
                AddTaperedCylinder(barkSt, foot, knee, baseR * 0.40f, baseR * 0.28f, lod == 0 ? 5 : 4, barkBot, barkBot, barkStyle, mossMult);
                AddTaperedCylinder(barkSt, knee, join, baseR * 0.28f, baseR * 0.15f, 4, barkBot, barkTop, barkStyle, mossMult);
            }

            if (lod == 0 && withPropRoots)
            {
                for (int r = 0; r < 4; r++)
                {
                    float a = r * GoldenAngleRad + 0.4f;
                    float dist = 3.6f * sMult;
                    AddTaperedCylinder(barkSt, new Vector3(MathF.Cos(a) * dist, -0.65f, MathF.Sin(a) * dist),
                        p3 + new Vector3(MathF.Cos(a) * dist * 0.82f, -0.8f, MathF.Sin(a) * dist * 0.82f),
                        0.15f, 0.10f, 4, barkBot, barkTop, barkStyle, mossMult);
                }
            }

            Vector3 crownCenter = p3 + new Vector3(0.0f, 4.6f * hMult, 0.0f);
            float crownRad = 8.4f * sMult;
            float crownHalfH = 5.4f * hMult;
            int limbs = lod == 0 ? 5 : 4;
            float childR = topR * 0.62f;

            for (int i = 0; i < limbs; i++)
            {
                float azim = i * GoldenAngleRad + (float)rng.NextDouble() * 0.25f;
                float startFrac = 0.68f + (i / (float)limbs) * 0.32f;
                Vector3 bStart = p2.Lerp(p3, Math.Clamp((startFrac - 0.68f) / 0.32f, 0.0f, 1.0f));
                float elev = 0.34f + (i % 3) * 0.18f;
                Vector3 dir = new Vector3(MathF.Cos(azim) * MathF.Cos(elev), MathF.Sin(elev), MathF.Sin(azim) * MathF.Cos(elev)).Normalized();
                float len = (5.6f + (i % 2) * 2.1f) * sMult;
                Vector3 bMid = bStart + dir * (len * 0.55f) + Vector3.Up * (0.65f * hMult);
                Vector3 bEnd = bStart + dir * len + Vector3.Up * ((i % 2 == 0 ? 1.2f : -0.4f) * hMult);

                AddTaperedCylinder(barkSt, bStart, bMid, childR, childR * 0.66f, lod == 0 ? 6 : 4, barkTop, barkTop, barkStyle, mossMult);
                AddTaperedCylinder(barkSt, bMid, bEnd, childR * 0.66f, childR * 0.36f, lod == 0 ? 5 : 4, barkTop, barkTop, barkStyle, mossMult);

                float bPhase = (i * 0.19f) % 1.0f;
                if (lod == 0)
                {
                    for (int s = 0; s < 3; s++)
                    {
                        float sAz = azim + (s - 1) * 0.72f + (float)(rng.NextDouble() - 0.5) * 0.25f;
                        float sElev = 0.28f + s * 0.24f;
                        Vector3 sDir = new Vector3(MathF.Cos(sAz) * MathF.Cos(sElev), MathF.Sin(sElev), MathF.Sin(sAz) * MathF.Cos(sElev)).Normalized();
                        Vector3 sEnd = bEnd + sDir * (2.8f * sMult);
                        AddTaperedCylinder(barkSt, bEnd, sEnd, childR * 0.34f, childR * 0.14f, 4, barkTop, barkTop, barkStyle, mossMult);
                        AddPuffyFoliageDome(leafSt, sEnd, crownCenter, crownRad, crownHalfH, 2.15f * sMult, 5, leafType, rng, 0.14f, (bPhase + s * 0.27f) % 1.0f, uvSubRect);
                    }
                    AddPuffyFoliageDome(leafSt, bEnd + Vector3.Up * 1.1f, crownCenter, crownRad, crownHalfH, 2.35f * sMult, 4, leafType, rng, 0.14f, bPhase, uvSubRect);
                }
                else
                {
                    AddPuffyFoliageDome(leafSt, bEnd + Vector3.Up * 0.8f, crownCenter, crownRad, crownHalfH, 3.05f * sMult, 3, leafType, rng, 0.14f, bPhase, uvSubRect);
                }
            }

            AddPuffyFoliageDome(leafSt, crownCenter + Vector3.Up * (2.8f * hMult), crownCenter, crownRad, crownHalfH,
                (lod == 0 ? 3.1f : 3.4f) * sMult, lod == 0 ? 6 : 3, leafType, rng, 0.15f, 0.77f, uvSubRect);
        }

        // =========================================================================
        // BROADLEAF VARIANT B: Gnarled Mid-Canopy (S-Curved Trunk, Low Draping Limbs 36%-52%)
        // LOD0: ~1,650-2,000 tris | LOD1: ~390 tris
        // =========================================================================
        private static void BuildBroadleafVariantB_GnarledMidCanopy(
            SurfaceTool barkSt, SurfaceTool leafSt, Random rng,
            float hMult, float sMult, float rMult, int leafType, float mossMult, int lod, int barkStyle = 0, Rect2? uvSubRect = null)
        {
            var barkBot = new Color(0.38f, 0.31f, 0.24f, 0.0f);
            var barkTop = new Color(0.45f, 0.38f, 0.30f, 0.03f);
            float trunkH = 9.4f * hMult;
            float baseR = 0.82f * rMult;
            int sides = lod == 0 ? 7 : 5;

            Vector3 p0 = new Vector3(0.0f, -0.80f, 0.0f);
            Vector3 p1 = new Vector3(1.15f * sMult, trunkH * 0.34f, 0.55f * sMult);
            Vector3 p2 = new Vector3(-0.65f * sMult, trunkH * 0.72f, 1.05f * sMult);
            Vector3 p3 = new Vector3(0.45f * sMult, trunkH, 0.35f * sMult);
            AddTaperedCylinder(barkSt, p0, p1, baseR * 1.15f, baseR * 0.76f, sides, barkBot, barkBot, barkStyle, mossMult);
            AddTaperedCylinder(barkSt, p1, p2, baseR * 0.76f, baseR * 0.54f, sides - 1, barkBot, barkTop, barkStyle, mossMult);
            AddTaperedCylinder(barkSt, p2, p3, baseR * 0.54f, baseR * 0.34f, Math.Max(4, sides - 2), barkTop, barkTop, barkStyle, mossMult);

            for (int r = 0; r < (lod == 0 ? 4 : 3); r++)
            {
                float a = r * Mathf.Tau / 4.0f + 0.4f;
                AddTaperedCylinder(barkSt, new Vector3(MathF.Cos(a) * baseR * 2.1f, -0.80f, MathF.Sin(a) * baseR * 2.1f),
                    p0.Lerp(p1, 0.48f), baseR * 0.34f, baseR * 0.14f, 4, barkBot, barkBot, barkStyle, mossMult);
            }

            Vector3 crownCenter = p2.Lerp(p3, 0.6f) + new Vector3(0.0f, 2.2f * hMult, 0.0f);
            float crownRad = 6.8f * sMult;
            float crownHalfH = 5.2f * hMult;

            int limbs = lod == 0 ? 6 : 4;
            for (int i = 0; i < limbs; i++)
            {
                float azim = i * GoldenAngleRad + 0.6f;
                Vector3 anchor = i < 2 ? p1 : (i < 4 ? p2 : p3);
                float elev = i < 2 ? 0.16f : (0.36f + (i % 2) * 0.24f);
                Vector3 dir = new Vector3(MathF.Cos(azim) * MathF.Cos(elev), MathF.Sin(elev), MathF.Sin(azim) * MathF.Cos(elev)).Normalized();
                float len = (4.4f + (i % 3) * 1.15f) * sMult;
                Vector3 elbow = anchor + dir * (len * 0.55f) + new Vector3(0.0f, 0.8f * hMult, 0.0f);
                Vector3 bEnd = anchor + dir * len + new Vector3(0.0f, i < 2 ? -0.4f * hMult : 0.7f * hMult, 0.0f);

                float rB = baseR * (i < 2 ? 0.42f : 0.34f);
                AddTaperedCylinder(barkSt, anchor, elbow, rB, rB * 0.62f, lod == 0 ? 5 : 4, barkTop, barkTop, barkStyle, mossMult);
                AddTaperedCylinder(barkSt, elbow, bEnd, rB * 0.62f, rB * 0.30f, 4, barkTop, barkTop, barkStyle, mossMult);

                float bPhase = (i * 0.23f + 0.11f) % 1.0f;
                if (lod == 0)
                {
                    for (int s = 0; s < 2; s++)
                    {
                        float sAz = azim + (s == 0 ? -0.78f : 0.78f);
                        Vector3 sEnd = bEnd + new Vector3(MathF.Cos(sAz), 0.35f, MathF.Sin(sAz)).Normalized() * (2.2f * sMult);
                        AddTaperedCylinder(barkSt, bEnd, sEnd, rB * 0.28f, rB * 0.11f, 4, barkTop, barkTop, barkStyle, mossMult);
                        AddPuffyFoliageDome(leafSt, sEnd, crownCenter, crownRad, crownHalfH, 1.95f * sMult, 4, leafType, rng, 0.15f, (bPhase + s * 0.31f) % 1.0f, uvSubRect);
                    }
                    AddPuffyFoliageDome(leafSt, bEnd, crownCenter, crownRad, crownHalfH, 2.10f * sMult, 4, leafType, rng, 0.15f, bPhase, uvSubRect);
                }
                else
                {
                    AddPuffyFoliageDome(leafSt, bEnd, crownCenter, crownRad, crownHalfH, 2.75f * sMult, 3, leafType, rng, 0.15f, bPhase, uvSubRect);
                }
            }
            AddPuffyFoliageDome(leafSt, p3 + Vector3.Up * (2.4f * hMult), crownCenter, crownRad, crownHalfH, 2.45f * sMult, lod == 0 ? 5 : 3, leafType, rng, 0.16f, 0.88f, uvSubRect);
        }

        private static void BuildBroadleafVariantC_ForestSapling(
            SurfaceTool barkSt, SurfaceTool leafSt, Random rng,
            float hMult, float sMult, float rMult, int leafType, float mossMult, int lod, int barkStyle = 0, Rect2? uvSubRect = null)
        {
            var barkBot = new Color(0.39f, 0.33f, 0.26f, 0.0f);
            var barkTop = new Color(0.46f, 0.40f, 0.32f, 0.04f);
            float totalH = 11.2f * hMult;
            float baseR = 0.36f * rMult;
            int sides = lod == 0 ? 6 : 4;

            Vector3 p0 = new Vector3(0.0f, -0.75f, 0.0f);
            Vector3 p1 = new Vector3(0.22f, totalH * 0.45f, -0.18f);
            Vector3 p2 = new Vector3(-0.14f, totalH * 0.92f, 0.12f);
            AddTaperedCylinder(barkSt, p0, p1, baseR * 1.15f, baseR * 0.62f, sides, barkBot, barkTop, barkStyle, mossMult * 0.85f);
            AddTaperedCylinder(barkSt, p1, p2, baseR * 0.62f, baseR * 0.16f, Math.Max(4, sides - 1), barkTop, barkTop, barkStyle, mossMult * 0.85f);

            Vector3 crownCenter = new Vector3(0.0f, totalH * 0.58f, 0.0f);
            float crownRad = 3.8f * sMult;
            float crownHalfH = totalH * 0.42f;

            int tiers = lod == 0 ? 8 : 5;
            for (int t = 0; t < tiers; t++)
            {
                float frac = 0.27f + (t / (float)(tiers - 1)) * 0.66f;
                Vector3 anchor = frac < 0.45f ? p0.Lerp(p1, (frac + 0.06f) / 0.51f) : p1.Lerp(p2, (frac - 0.45f) / 0.47f);
                float tierR = (1.0f - MathF.Abs(frac - 0.52f) * 1.15f) * 3.1f * sMult;
                tierR = MathF.Max(1.1f * sMult, tierR);
                int bCnt = lod == 0 ? (t < tiers - 2 ? 3 : 2) : 2;
                for (int b = 0; b < bCnt; b++)
                {
                    float a = b * (Mathf.Tau / bCnt) + t * GoldenAngleRad;
                    Vector3 bEnd = anchor + new Vector3(MathF.Cos(a) * tierR, 0.65f * hMult, MathF.Sin(a) * tierR);
                    AddTaperedCylinder(barkSt, anchor, bEnd, baseR * 0.24f, baseR * 0.07f, 4, barkTop, barkTop, barkStyle, mossMult * 0.7f);
                    AddPuffyFoliageDome(leafSt, bEnd, crownCenter, crownRad, crownHalfH,
                        (lod == 0 ? 1.45f : 1.95f) * sMult, lod == 0 ? 3 : 2, leafType, rng, 0.17f, ((t * 0.17f + b * 0.33f) % 1.0f), uvSubRect);
                }
            }
            AddPuffyFoliageDome(leafSt, p2 + Vector3.Up * 0.8f, crownCenter, crownRad, crownHalfH, 1.85f * sMult, lod == 0 ? 4 : 2, leafType, rng, 0.18f, 0.55f, uvSubRect);
        }

        private static void BuildBroadleafVariantD_ColumnarGiant(
            SurfaceTool barkSt, SurfaceTool leafSt, Random rng,
            float hMult, float sMult, float rMult, int leafType, float mossMult, int lod, int barkStyle = 0, Rect2? uvSubRect = null)
        {
            var barkBot = new Color(0.36f, 0.30f, 0.24f, 0.0f);
            var barkTop = new Color(0.44f, 0.38f, 0.31f, 0.03f);
            float trunkH = 16.5f * hMult;
            float baseR = 1.05f * rMult;
            int sides = lod == 0 ? 8 : 5;

            Vector3 p0 = new Vector3(0.0f, -0.85f, 0.0f);
            Vector3 p1 = new Vector3(-0.18f, trunkH * 0.45f, 0.15f);
            Vector3 p2 = new Vector3(0.22f, trunkH, -0.10f);
            AddTaperedCylinder(barkSt, p0, p1, baseR * 1.15f, baseR * 0.76f, sides, barkBot, barkTop, barkStyle, mossMult);
            AddTaperedCylinder(barkSt, p1, p2, baseR * 0.76f, baseR * 0.48f, sides - 1, barkTop, barkTop, barkStyle, mossMult);

            for (int r = 0; r < (lod == 0 ? 5 : 3); r++)
            {
                float a = r * Mathf.Tau / 5.0f + 0.15f;
                AddTaperedCylinder(barkSt, new Vector3(MathF.Cos(a) * baseR * 2.15f, -0.85f, MathF.Sin(a) * baseR * 2.15f),
                    new Vector3(MathF.Cos(a) * baseR * 0.45f, trunkH * 0.22f, MathF.Sin(a) * baseR * 0.45f),
                    baseR * 0.35f, baseR * 0.14f, 4, barkBot, barkBot, barkStyle, mossMult);
            }

            if (lod == 0)
            {
                for (int k = 0; k < 4; k++)
                {
                    float fy = 0.32f + k * 0.14f;
                    float a = k * GoldenAngleRad + 0.9f;
                    Vector3 s0 = p0.Lerp(p2, fy);
                    Vector3 s1 = s0 + new Vector3(MathF.Cos(a) * 2.1f * sMult, 0.55f, MathF.Sin(a) * 2.1f * sMult);
                    AddTaperedCylinder(barkSt, s0, s1, baseR * 0.18f, baseR * 0.07f, 4, barkTop, barkTop, barkStyle, mossMult * 1.2f);
                    AddPuffyFoliageDome(leafSt, s1, s1 + Vector3.Up, 2.2f, 1.5f, 1.15f * sMult, 3, leafType, rng, 0.15f, (k * 0.27f) % 1.0f, uvSubRect);
                }
            }

            Vector3 crownCenter = p2 + new Vector3(0.0f, 3.8f * hMult, 0.0f);
            float crownRad = 8.2f * sMult;
            float crownHalfH = 4.6f * hMult;
            int limbs = lod == 0 ? 6 : 4;
            for (int i = 0; i < limbs; i++)
            {
                float a = i * GoldenAngleRad + 0.2f;
                float elev = 0.38f + (i % 2) * 0.24f;
                Vector3 dir = new Vector3(MathF.Cos(a) * MathF.Cos(elev), MathF.Sin(elev), MathF.Sin(a) * MathF.Cos(elev)).Normalized();
                Vector3 bEnd = p2 + dir * ((5.8f + (i % 2) * 1.6f) * sMult);
                AddTaperedCylinder(barkSt, p2, bEnd, baseR * 0.34f, baseR * 0.14f, lod == 0 ? 5 : 4, barkTop, barkTop, barkStyle, mossMult);

                float bPhase = (i * 0.17f) % 1.0f;
                if (lod == 0)
                {
                    Vector3 s1 = bEnd + new Vector3(MathF.Cos(a + 0.65f), 0.35f, MathF.Sin(a + 0.65f)).Normalized() * (2.5f * sMult);
                    Vector3 s2 = bEnd + new Vector3(MathF.Cos(a - 0.65f), 0.45f, MathF.Sin(a - 0.65f)).Normalized() * (2.5f * sMult);
                    AddTaperedCylinder(barkSt, bEnd, s1, baseR * 0.14f, baseR * 0.06f, 4, barkTop, barkTop, barkStyle, mossMult);
                    AddTaperedCylinder(barkSt, bEnd, s2, baseR * 0.14f, baseR * 0.06f, 4, barkTop, barkTop, barkStyle, mossMult);
                    AddPuffyFoliageDome(leafSt, s1, crownCenter, crownRad, crownHalfH, 2.05f * sMult, 4, leafType, rng, 0.14f, bPhase, uvSubRect);
                    AddPuffyFoliageDome(leafSt, s2, crownCenter, crownRad, crownHalfH, 2.05f * sMult, 4, leafType, rng, 0.14f, (bPhase + 0.33f) % 1.0f, uvSubRect);
                }
                else
                {
                    AddPuffyFoliageDome(leafSt, bEnd, crownCenter, crownRad, crownHalfH, 2.95f * sMult, 3, leafType, rng, 0.14f, bPhase, uvSubRect);
                }
            }
            AddPuffyFoliageDome(leafSt, crownCenter + Vector3.Up * (2.4f * hMult), crownCenter, crownRad, crownHalfH, 3.0f * sMult, lod == 0 ? 6 : 3, leafType, rng, 0.15f, 0.62f, uvSubRect);
        }

        // =========================================================================
        // CONIFER FAMILY (3 Variants: Classic Spire, Tall Redwood, Wind-Swept Alpine)
        // LOD0: ~1,550-2,050 tris | LOD1: ~400 tris
        // =========================================================================
        private static void BuildConiferVariant(
            SurfaceTool barkSt, SurfaceTool leafSt, Random rng,
            float hMult, float sMult, float rMult, bool isSequoia, bool isLarch, int variant, int lod)
        {
            var barkBot = isSequoia ? new Color(0.56f, 0.30f, 0.20f, 0.0f) : new Color(0.42f, 0.32f, 0.25f, 0.0f);
            var barkTop = isSequoia ? new Color(0.60f, 0.34f, 0.23f, 0.03f) : new Color(0.48f, 0.38f, 0.30f, 0.03f);
            float mossMult = isSequoia ? 0.85f : (isLarch ? 0.25f : 0.45f);
            int barkStyle = 5; // bark_sequoia_conifer seamless PBR
            int leafType = isLarch ? 8 : 1;
            Rect2? subUv = isLarch ? new Rect2(0.504f, 0.004f, 0.492f, 0.992f) : null;

            float totalH = (isSequoia ? 25.5f : (isLarch ? 12.6f : (variant == 1 ? 17.5f : 15.2f))) * hMult;
            float baseR = (isSequoia ? 1.20f : (isLarch ? 0.46f : (variant == 2 ? 0.56f : 0.48f))) * rMult;
            float leanX = (isLarch || variant == 2) ? 1.45f * sMult : (variant == 1 ? -0.45f : 0.20f);
            int sides = lod == 0 ? 7 : 5;

            Vector3 p0 = new Vector3(0.0f, -0.80f, 0.0f);
            Vector3 p1 = new Vector3(leanX * 0.42f, totalH * 0.50f, isLarch ? 0.55f : 0.15f);
            Vector3 p2 = new Vector3(leanX, totalH, isLarch ? -0.40f : -0.10f);
            AddTaperedCylinder(barkSt, p0, p1, baseR * 1.15f, baseR * 0.52f, sides, barkBot, barkTop, barkStyle, mossMult);
            AddTaperedCylinder(barkSt, p1, p2, baseR * 0.52f, 0.08f, Math.Max(4, sides - 1), barkTop, barkTop, barkStyle, mossMult);

            int tiers = lod == 0 ? (isSequoia ? 7 : (variant == 1 ? 7 : (variant == 2 ? 6 : 7))) : 5;
            float startFrac = isSequoia ? 0.34f : (variant == 1 ? 0.20f : (variant == 2 ? 0.34f : 0.24f));
            Vector3 crownCenter = new Vector3(leanX * 0.55f, totalH * 0.58f, 0.0f);
            float crownRad = (isSequoia ? 5.6f : (variant == 1 ? 3.5f : 4.4f)) * sMult;
            float crownHalfH = totalH * 0.44f;

            for (int t = 0; t < tiers; t++)
            {
                float frac = startFrac + (t / (float)(tiers - 1)) * (0.95f - startFrac);
                Vector3 anchor = frac < 0.50f ? p0.Lerp(p1, (frac + 0.05f) / 0.55f) : p1.Lerp(p2, (frac - 0.50f) / 0.50f);
                float tierRadius = (1.0f - (t / (float)tiers) * 0.78f) * (isSequoia ? 5.1f : (variant == 1 ? 3.2f : 4.0f)) * sMult;
                int bCount = lod == 0 ? (t < tiers - 2 ? 4 : 3) : 3;

                for (int b = 0; b < bCount; b++)
                {
                    float a = b * (Mathf.Tau / bCount) + t * GoldenAngleRad + (float)(rng.NextDouble() - 0.5) * 0.26f;
                    float droop = tierRadius * (variant == 2 ? 0.56f : 0.48f);
                    Vector3 bMid = anchor + new Vector3(MathF.Cos(a) * tierRadius * 0.52f, -droop * 0.72f, MathF.Sin(a) * tierRadius * 0.52f);
                    Vector3 bEnd = anchor + new Vector3(MathF.Cos(a) * tierRadius, -droop * 0.58f, MathF.Sin(a) * tierRadius);
                    if (lod == 0)
                    {
                        AddTaperedCylinder(barkSt, anchor, bMid, 0.095f * rMult, 0.055f * rMult, 4, barkTop, barkTop, barkStyle, mossMult);
                        AddTaperedCylinder(barkSt, bMid, bEnd, 0.055f * rMult, 0.025f, 4, barkTop, barkTop, barkStyle, mossMult);
                        AddPuffyFoliageDome(leafSt, bMid + Vector3.Down * 0.15f, crownCenter, crownRad, crownHalfH,
                            1.70f * sMult, 2, leafType, rng, 0.12f, ((t * 0.17f + b * 0.23f) % 1.0f), subUv);
                    }
                    else
                    {
                        AddTaperedCylinder(barkSt, anchor, bEnd, 0.09f * rMult, 0.03f, 4, barkTop, barkTop, barkStyle, mossMult);
                    }
                    AddPuffyFoliageDome(leafSt, bEnd, crownCenter, crownRad, crownHalfH,
                        (lod == 0 ? 1.90f : 2.35f) * sMult, 2, leafType, rng, 0.13f, ((t * 0.13f + b * 0.29f) % 1.0f), subUv);
                }
            }
            AddPuffyFoliageDome(leafSt, p2 + Vector3.Up * 0.5f, crownCenter, crownRad, crownHalfH, 1.85f * sMult, lod == 0 ? 3 : 2, leafType, rng, 0.14f, 0.41f, subUv);
        }

        // =========================================================================
        // 6 NEW UNIQUE PREHISTORIC TREE / PALM / CACTUS BUILDERS
        // =========================================================================
        private static void BuildSwampBaldCypress(
            SurfaceTool barkSt, SurfaceTool leafSt, Random rng, float hMult, float sMult, float rMult, int lod)
        {
            var barkBot = new Color(0.42f, 0.34f, 0.26f, 0.0f);
            var barkTop = new Color(0.48f, 0.40f, 0.32f, 0.03f);
            float totalH = 20.5f * hMult;
            float baseR = 1.38f * rMult;
            int sides = lod == 0 ? 8 : 5;
            Rect2 cypressUv = new Rect2(0.504f, 0.004f, 0.492f, 0.992f); // right half of leaf_araucaria_cypress.png

            // Deeply fluted swollen swamp base tapering cleanly upward
            Vector3 p0 = new Vector3(0f, -0.95f, 0f);
            Vector3 p1 = new Vector3(0.15f, totalH * 0.22f, -0.10f);
            Vector3 p2 = new Vector3(-0.12f, totalH * 0.65f, 0.14f);
            Vector3 p3 = new Vector3(0.08f, totalH * 0.96f, -0.06f);
            AddTaperedCylinder(barkSt, p0, p1, baseR * 1.48f, baseR * 0.72f, sides, barkBot, barkBot, 4, 1.25f);
            AddTaperedCylinder(barkSt, p1, p2, baseR * 0.72f, baseR * 0.42f, sides - 1, barkBot, barkTop, 4, 1.05f);
            AddTaperedCylinder(barkSt, p2, p3, baseR * 0.42f, baseR * 0.16f, Math.Max(4, sides - 2), barkTop, barkTop, 4, 0.85f);

            // Ring of 6-8 iconic aerial cypress knees protruding from the swamp mud!
            int knees = lod == 0 ? 7 : 4;
            for (int k = 0; k < knees; k++)
            {
                float a = k * Mathf.Tau / knees + (float)rng.NextDouble() * 0.35f;
                float dist = baseR * (1.8f + (k % 3) * 0.65f);
                float kh = 0.85f + (k % 3) * 0.38f;
                Vector3 kBase = new Vector3(MathF.Cos(a) * dist, -0.65f, MathF.Sin(a) * dist);
                Vector3 kTop = new Vector3(MathF.Cos(a) * (dist * 0.92f), kh, MathF.Sin(a) * (dist * 0.92f));
                AddTaperedCylinder(barkSt, kBase, kTop, 0.22f * rMult, 0.06f * rMult, 4, barkBot, barkBot, 4, 1.35f);
            }

            // Tiered horizontal feathery flat-topped swamp limbs
            Vector3 crownCenter = new Vector3(0f, totalH * 0.70f, 0f);
            float crownRad = 6.5f * sMult;
            float crownHalfH = totalH * 0.34f;
            int tiers = lod == 0 ? 6 : 4;
            for (int t = 0; t < tiers; t++)
            {
                float frac = 0.46f + (t / (float)(tiers - 1)) * 0.48f;
                Vector3 anchor = p1.Lerp(p3, (frac - 0.22f) / 0.74f);
                float rTier = (1.0f - MathF.Abs(frac - 0.74f) * 1.1f) * 5.4f * sMult;
                int bCnt = lod == 0 ? 4 : 3;
                for (int b = 0; b < bCnt; b++)
                {
                    float a = b * (Mathf.Tau / bCnt) + t * GoldenAngleRad;
                    Vector3 bEnd = anchor + new Vector3(MathF.Cos(a) * rTier, 0.35f * hMult, MathF.Sin(a) * rTier);
                    AddTaperedCylinder(barkSt, anchor, bEnd, 0.16f * rMult, 0.05f, 4, barkTop, barkTop, 4, 0.95f);
                    AddPuffyFoliageDome(leafSt, bEnd, crownCenter, crownRad, crownHalfH, (lod == 0 ? 2.1f : 2.6f) * sMult,
                        lod == 0 ? 3 : 2, 8, rng, 0.14f, ((t * 0.19f + b * 0.27f) % 1.0f), cypressUv);
                }
            }
            AddPuffyFoliageDome(leafSt, p3 + Vector3.Up * 0.9f, crownCenter, crownRad, crownHalfH, 2.5f * sMult, lod == 0 ? 4 : 2, 8, rng, 0.15f, 0.55f, cypressUv);
        }

        private static void BuildAraucaria(
            SurfaceTool barkSt, SurfaceTool leafSt, Random rng, float hMult, float sMult, float rMult, int lod)
        {
            var barkBot = new Color(0.52f, 0.30f, 0.22f, 0.0f);
            var barkTop = new Color(0.56f, 0.35f, 0.25f, 0.03f);
            float totalH = 26.5f * hMult;
            float baseR = 0.96f * rMult;
            int sides = lod == 0 ? 7 : 5;
            Rect2 arauUv = new Rect2(0.004f, 0.004f, 0.492f, 0.992f); // left half of leaf_araucaria_cypress.png

            // Tall straight prehistoric pillar (bark_sequoia_conifer)
            Vector3 p0 = new Vector3(0f, -0.85f, 0f);
            Vector3 p1 = new Vector3(0.12f, totalH * 0.52f, -0.10f);
            Vector3 p2 = new Vector3(-0.08f, totalH * 0.96f, 0.08f);
            AddTaperedCylinder(barkSt, p0, p1, baseR * 1.15f, baseR * 0.62f, sides, barkBot, barkTop, 5, 0.55f);
            AddTaperedCylinder(barkSt, p1, p2, baseR * 0.62f, baseR * 0.18f, Math.Max(4, sides - 1), barkTop, barkTop, 5, 0.35f);

            // 5-6 candelabra whorls of upward-curving branches!
            Vector3 crownCenter = new Vector3(0f, totalH * 0.74f, 0f);
            float crownRad = 7.2f * sMult;
            float crownHalfH = totalH * 0.28f;
            int whorls = lod == 0 ? 5 : 4;
            for (int w = 0; w < whorls; w++)
            {
                float frac = 0.54f + (w / (float)(whorls - 1)) * 0.42f;
                Vector3 anchor = p1.Lerp(p2, (frac - 0.52f) / 0.44f);
                float reach = (1.0f - w * 0.12f) * 6.2f * sMult;
                int limbs = lod == 0 ? 5 : 3;
                for (int b = 0; b < limbs; b++)
                {
                    float a = b * (Mathf.Tau / limbs) + w * 0.65f;
                    Vector3 bMid = anchor + new Vector3(MathF.Cos(a) * reach * 0.65f, -0.35f * hMult, MathF.Sin(a) * reach * 0.65f);
                    Vector3 bEnd = anchor + new Vector3(MathF.Cos(a) * reach, 1.45f * hMult, MathF.Sin(a) * reach);
                    AddTaperedCylinder(barkSt, anchor, bMid, 0.18f * rMult, 0.11f * rMult, 4, barkTop, barkTop, 5, 0.30f);
                    AddTaperedCylinder(barkSt, bMid, bEnd, 0.11f * rMult, 0.05f, 4, barkTop, barkTop, 5, 0.25f);
                    AddPuffyFoliageDome(leafSt, bEnd, crownCenter, crownRad, crownHalfH, (lod == 0 ? 2.15f : 2.65f) * sMult,
                        lod == 0 ? 3 : 2, 8, rng, 0.13f, ((w * 0.21f + b * 0.19f) % 1.0f), arauUv);
                }
            }
            AddPuffyFoliageDome(leafSt, p2 + Vector3.Up * 1.1f, crownCenter, crownRad, crownHalfH, 2.8f * sMult, lod == 0 ? 4 : 2, 8, rng, 0.13f, 0.62f, arauUv);
        }

        private static void BuildSteppeOak(
            SurfaceTool barkSt, SurfaceTool leafSt, Random rng, float hMult, float sMult, float rMult, int lod)
        {
            var barkBot = new Color(0.42f, 0.35f, 0.28f, 0.0f);
            var barkTop = new Color(0.48f, 0.41f, 0.33f, 0.03f);
            float trunkH = 6.2f * hMult;
            float baseR = 1.42f * rMult;
            int sides = lod == 0 ? 8 : 5;

            Vector3 p0 = new Vector3(0f, -0.85f, 0f);
            Vector3 p1 = new Vector3(0.25f, trunkH * 0.55f, -0.15f);
            Vector3 fork = new Vector3(-0.10f, trunkH, 0.12f);
            AddTaperedCylinder(barkSt, p0, p1, baseR * 1.24f, baseR * 0.88f, sides, barkBot, barkBot, 4, 0.55f);
            AddTaperedCylinder(barkSt, p1, fork, baseR * 0.88f, baseR * 0.68f, sides - 1, barkBot, barkTop, 4, 0.45f);

            // 5 massive spreading limbs at ~55 deg lifting an ultra-wide iconic landmark oak dome!
            Vector3 crownCenter = fork + new Vector3(0f, 4.4f * hMult, 0f);
            float crownRad = 10.2f * sMult;
            float crownHalfH = 5.4f * hMult;
            int limbs = lod == 0 ? 5 : 4;
            for (int i = 0; i < limbs; i++)
            {
                float a = i * GoldenAngleRad + 0.3f;
                Vector3 dir = new Vector3(MathF.Cos(a) * 0.82f, 0.57f, MathF.Sin(a) * 0.82f).Normalized();
                Vector3 bMid = fork + dir * (4.8f * sMult);
                Vector3 bEnd = fork + dir * (8.6f * sMult) + Vector3.Down * (0.6f * hMult);
                AddTaperedCylinder(barkSt, fork, bMid, baseR * 0.48f, baseR * 0.28f, 5, barkTop, barkTop, 4, 0.45f);
                AddTaperedCylinder(barkSt, bMid, bEnd, baseR * 0.28f, baseR * 0.12f, 4, barkTop, barkTop, 4, 0.35f);
                AddPuffyFoliageDome(leafSt, bMid + Vector3.Up * 1.6f, crownCenter, crownRad, crownHalfH, 2.8f * sMult, lod == 0 ? 4 : 2, 0, rng, 0.13f, (i * 0.21f) % 1.0f);
                AddPuffyFoliageDome(leafSt, bEnd + Vector3.Up * 0.8f, crownCenter, crownRad, crownHalfH, 3.1f * sMult, lod == 0 ? 4 : 2, 0, rng, 0.14f, (i * 0.21f + 0.4f) % 1.0f);
            }
            AddPuffyFoliageDome(leafSt, crownCenter + Vector3.Up * (2.6f * hMult), crownCenter, crownRad, crownHalfH, 3.8f * sMult, lod == 0 ? 5 : 3, 0, rng, 0.14f, 0.72f);
        }

        private static void BuildCoastalMangrove(
            SurfaceTool barkSt, SurfaceTool leafSt, Random rng, float hMult, float sMult, float rMult, int lod)
        {
            var barkBot = new Color(0.36f, 0.30f, 0.24f, 0.0f);
            var barkTop = new Color(0.44f, 0.37f, 0.30f, 0.03f);
            float trunkH = 5.4f * hMult;
            float baseR = 0.56f * rMult;

            // Intertwined arching stilt roots plunging into tidal mud (-0.90m)!
            int stilts = lod == 0 ? 9 : 5;
            for (int r = 0; r < stilts; r++)
            {
                float a = r * Mathf.Tau / stilts + (float)rng.NextDouble() * 0.25f;
                float reach = (1.65f + (r % 3) * 0.55f) * sMult;
                Vector3 join = new Vector3(MathF.Cos(a) * 0.22f, 1.35f + (r % 3) * 0.48f, MathF.Sin(a) * 0.22f);
                Vector3 arch = new Vector3(MathF.Cos(a) * reach * 0.65f, 0.75f + (r % 2) * 0.35f, MathF.Sin(a) * reach * 0.65f);
                Vector3 foot = new Vector3(MathF.Cos(a) * reach, -0.90f, MathF.Sin(a) * reach);
                AddTaperedCylinder(barkSt, join, arch, 0.11f * rMult, 0.09f * rMult, 4, barkTop, barkBot, 4, 0.65f);
                AddTaperedCylinder(barkSt, arch, foot, 0.09f * rMult, 0.06f * rMult, 4, barkBot, barkBot, 4, 0.85f);
            }

            Vector3 p0 = new Vector3(0f, 0.85f, 0f);
            Vector3 p1 = new Vector3(0.25f, trunkH, -0.20f);
            AddTaperedCylinder(barkSt, p0, p1, baseR * 0.92f, baseR * 0.45f, 6, barkBot, barkTop, 4, 0.60f);

            Vector3 crownCenter = p1 + new Vector3(0f, 2.2f * hMult, 0f);
            float crownRad = 5.4f * sMult;
            float crownHalfH = 2.8f * hMult;
            int limbs = lod == 0 ? 5 : 4;
            for (int i = 0; i < limbs; i++)
            {
                float a = i * GoldenAngleRad + 0.5f;
                Vector3 bEnd = p1 + new Vector3(MathF.Cos(a) * 3.6f * sMult, 1.6f * hMult, MathF.Sin(a) * 3.6f * sMult);
                AddTaperedCylinder(barkSt, p1, bEnd, baseR * 0.34f, baseR * 0.12f, 4, barkTop, barkTop, 4, 0.45f);
                AddPuffyFoliageDome(leafSt, bEnd, crownCenter, crownRad, crownHalfH, (lod == 0 ? 2.15f : 2.6f) * sMult, lod == 0 ? 4 : 2, 0, rng, 0.16f, (i * 0.19f) % 1.0f);
            }
            AddPuffyFoliageDome(leafSt, crownCenter + Vector3.Up * 1.1f, crownCenter, crownRad, crownHalfH, 2.5f * sMult, lod == 0 ? 4 : 2, 0, rng, 0.16f, 0.44f);
        }

        private static void BuildPandanus(
            SurfaceTool barkSt, SurfaceTool leafSt, Random rng, float hMult, int lod)
        {
            var barkCol = new Color(0.48f, 0.42f, 0.34f, 0.0f);
            float h = 4.2f * hMult;
            Rect2 pandanusUv = new Rect2(0.254f, 0.004f, 0.242f, 0.492f); // specialty_atlas_b (0,0) right half

            // Conical stilt root prop-cone
            for (int r = 0; r < 6; r++)
            {
                float a = r * Mathf.Tau / 6.0f + 0.2f;
                AddTaperedCylinder(barkSt, new Vector3(0f, 1.35f, 0f), new Vector3(MathF.Cos(a) * 1.15f, -0.55f, MathF.Sin(a) * 1.15f),
                    0.10f, 0.06f, 4, barkCol, barkCol, 0, 0.15f);
            }
            Vector3 fork = new Vector3(0f, h * 0.56f, 0f);
            AddTaperedCylinder(barkSt, new Vector3(0f, 0.65f, 0f), fork, 0.24f, 0.18f, 5, barkCol, barkCol, 0, 0.15f);

            // 3 Y-forked branches topped with spiral sword-leaf rosettes
            for (int b = 0; b < 3; b++)
            {
                float a = b * Mathf.Tau / 3.0f + 0.4f;
                Vector3 tip = fork + new Vector3(MathF.Cos(a) * 1.15f, h * 0.44f, MathF.Sin(a) * 1.15f);
                AddTaperedCylinder(barkSt, fork, tip, 0.14f, 0.09f, 4, barkCol, barkCol, 0, 0.12f);
                AddPuffyFoliageDome(leafSt, tip + Vector3.Up * 0.45f, tip, 2.2f, 1.4f, 1.35f * hMult, lod == 0 ? 3 : 2, 14, rng, 0.24f, (b * 0.31f) % 1.0f, pandanusUv);
            }
        }

        private static void BuildColumnarCactus(
            SurfaceTool st, Random rng, float hMult, float rMult, int variant, int lod)
        {
            float totalH = (variant == 0 ? 4.4f : 3.6f) * hMult;
            float baseR = 0.34f * rMult;

            void AddFlutedColumn(Vector3 pBot, Vector3 pTop, float rB, float rT)
            {
                Vector3 axis = (pTop - pBot).Normalized();
                if (axis.LengthSquared() < 0.001f) return;
                Vector3 refV = MathF.Abs(axis.Y) < 0.9f ? Vector3.Up : Vector3.Right;
                Vector3 t = axis.Cross(refV).Normalized();
                Vector3 bt = axis.Cross(t).Normalized();
                int ribs = lod == 0 ? 14 : 10; // alternating ridge/flute -> 7-ribbed cactus!
                var ringB = new Vector3[ribs];
                var ringT = new Vector3[ribs];
                var ringN = new Vector3[ribs];
                var colB = new Color[ribs];
                for (int i = 0; i < ribs; i++)
                {
                    float a = i * Mathf.Tau / ribs;
                    bool isFlute = (i & 1) == 1;
                    float mul = isFlute ? 0.78f : 1.06f;
                    Vector3 d = t * MathF.Cos(a) + bt * MathF.Sin(a);
                    ringB[i] = pBot + d * (rB * mul);
                    ringT[i] = pTop + d * (rT * mul);
                    ringN[i] = d;
                    // Darker AO inside cactus flutes for crisp desert sunlight definition!
                    colB[i] = isFlute ? new Color(0.18f, 0.34f, 0.14f, 0.0f) : new Color(0.32f, 0.54f, 0.25f, 0.0f);
                }
                Vector2 tag = new Vector2(6.0f, 0.0f); // bark_style = 6 (cactus), moss = 0
                for (int i = 0; i < ribs; i++)
                {
                    int nx = (i + 1) % ribs;
                    float u0 = i / (float)ribs, u1 = (i + 1) / (float)ribs;
                    void Emit(Vector3 p, Vector3 n, Color c, Vector2 uv) { st.SetNormal(n); st.SetColor(c); st.SetUV(uv); st.SetUV2(tag); st.AddVertex(p); }
                    Emit(ringB[i], ringN[i], colB[i], new Vector2(u0, 0f));
                    Emit(ringB[nx], ringN[nx], colB[nx], new Vector2(u1, 0f));
                    Emit(ringT[nx], ringN[nx], colB[nx], new Vector2(u1, 2f));
                    Emit(ringB[i], ringN[i], colB[i], new Vector2(u0, 0f));
                    Emit(ringT[nx], ringN[nx], colB[nx], new Vector2(u1, 2f));
                    Emit(ringT[i], ringN[i], colB[i], new Vector2(u0, 2f));
                }
            }

            AddFlutedColumn(new Vector3(0f, -0.45f, 0f), new Vector3(0f, totalH, 0f), baseR * 1.12f, baseR * 0.86f);
            int arms = variant == 0 ? 3 : 2;
            for (int aIdx = 0; aIdx < arms; aIdx++)
            {
                float ang = aIdx * (Mathf.Tau / arms) + (float)rng.NextDouble() * 0.4f;
                float startY = totalH * (0.36f + aIdx * 0.12f);
                float armReach = 0.82f + (aIdx % 2) * 0.22f;
                float armH = totalH * (0.38f + (aIdx % 2) * 0.14f);
                Vector3 root = new Vector3(0f, startY, 0f);
                Vector3 elbow = new Vector3(MathF.Cos(ang) * armReach, startY + 0.18f, MathF.Sin(ang) * armReach);
                Vector3 tip = new Vector3(MathF.Cos(ang) * armReach, startY + armH, MathF.Sin(ang) * armReach);
                AddFlutedColumn(root, elbow, baseR * 0.65f, baseR * 0.62f);
                AddFlutedColumn(elbow, tip, baseR * 0.68f, baseR * 0.56f);
            }
        }

        // =========================================================================
        // WEEPING RIPARIAN WILLOW & SILVER BIRCH (2 Variants)
        // =========================================================================
        private static void BuildWeepingVariant(
            SurfaceTool barkSt, SurfaceTool leafSt, Random rng,
            float hMult, float sMult, float rMult, bool paleBark, int leafType, Rect2? subUv, int variant, int lod)
        {
            var barkBot = paleBark ? new Color(0.92f, 0.91f, 0.88f, 0.0f) : new Color(0.38f, 0.32f, 0.24f, 0.0f);
            var barkTop = paleBark ? new Color(0.96f, 0.95f, 0.92f, 0.03f) : new Color(0.44f, 0.37f, 0.29f, 0.03f);
            int barkStyle = paleBark ? 2 : 0;
            float mossMult = paleBark ? 0.25f : 0.85f;

            float trunkH = (variant == 0 ? 6.8f : 7.8f) * hMult;
            float baseR = 0.54f * rMult;
            float lean = (variant == 0 ? 1.35f : 0.65f) * sMult;
            int sides = lod == 0 ? 7 : 5;

            Vector3 p0 = new Vector3(0.0f, -0.75f, 0.0f);
            Vector3 p1 = new Vector3(lean * 0.48f, trunkH * 0.50f, 0.25f * sMult);
            Vector3 p2 = new Vector3(lean, trunkH, 0.42f * sMult);
            AddTaperedCylinder(barkSt, p0, p1, baseR * 1.12f, baseR * 0.70f, sides, barkBot, barkTop, barkStyle, mossMult);
            AddTaperedCylinder(barkSt, p1, p2, baseR * 0.70f, baseR * 0.42f, Math.Max(4, sides - 1), barkTop, barkTop, barkStyle, mossMult);

            Vector3 crownCenter = p2 + new Vector3(0.0f, 2.0f * hMult, 0.0f);
            float crownRad = 5.4f * sMult;
            float crownHalfH = 4.2f * hMult;
            int boughs = lod == 0 ? 6 : 4;

            for (int i = 0; i < boughs; i++)
            {
                float azim = i * GoldenAngleRad + variant * 0.7f;
                Vector3 arch = p2 + new Vector3(MathF.Cos(azim) * 3.6f * sMult, 2.6f * hMult, MathF.Sin(azim) * 3.6f * sMult);
                Vector3 droop = arch + new Vector3(MathF.Cos(azim) * 1.1f * sMult, -2.4f * hMult, MathF.Sin(azim) * 1.1f * sMult);
                AddTaperedCylinder(barkSt, p2, arch, baseR * 0.34f, baseR * 0.14f, 4, barkTop, barkTop, barkStyle, mossMult);
                if (lod == 0)
                    AddTaperedCylinder(barkSt, arch, droop, baseR * 0.14f, baseR * 0.06f, 4, barkTop, barkTop, barkStyle, mossMult);

                float bp = (i * 0.19f) % 1.0f;
                AddPuffyFoliageDome(leafSt, arch + Vector3.Up * 0.4f, crownCenter, crownRad, crownHalfH, (lod == 0 ? 1.85f : 2.4f) * sMult, lod == 0 ? 4 : 2, leafType, rng, 0.18f, bp, subUv);
                AddPuffyFoliageDome(leafSt, droop, crownCenter, crownRad, crownHalfH, (lod == 0 ? 1.75f : 2.2f) * sMult, lod == 0 ? 4 : 2, leafType, rng, 0.20f, (bp + 0.42f) % 1.0f, subUv);
            }
            AddPuffyFoliageDome(leafSt, crownCenter + Vector3.Up * 1.8f, crownCenter, crownRad, crownHalfH, 2.2f * sMult, lod == 0 ? 5 : 3, leafType, rng, 0.16f, 0.73f, subUv);
        }

        private static void BuildDesertUmbrellaVariant(
            SurfaceTool barkSt, SurfaceTool leafSt, Random rng, float hMult, float sMult, float rMult, int variant, int lod)
        {
            var bark = new Color(0.50f, 0.38f, 0.28f, 0.0f);
            float trunkH = (variant == 0 ? 5.6f : 6.4f) * hMult;
            float baseR = 0.66f * rMult;
            int sides = lod == 0 ? 7 : 5;
            Rect2 acaciaUv = new Rect2(0.337f, 0.004f, 0.326f, 0.992f); // middle 1/3 of leaf_willow_acacia_berry.png

            Vector3 p0 = new Vector3(0.0f, -0.75f, 0.0f);
            Vector3 p1 = new Vector3(variant == 0 ? 0.35f : -0.45f, trunkH * 0.52f, 0.20f);
            Vector3 fork = new Vector3(variant == 0 ? -0.25f : 0.40f, trunkH, -0.15f);
            AddTaperedCylinder(barkSt, p0, p1, baseR * 1.10f, baseR * 0.72f, sides, bark, bark, 3, 0.05f);
            AddTaperedCylinder(barkSt, p1, fork, baseR * 0.72f, baseR * 0.50f, Math.Max(4, sides - 1), bark, bark, 3, 0.05f);

            Vector3 crownCenter = fork + new Vector3(0.0f, 2.9f * hMult, 0.0f);
            float crownRad = 6.2f * sMult;
            float crownHalfH = 2.2f * hMult;
            int limbs = lod == 0 ? 6 : 4;

            for (int i = 0; i < limbs; i++)
            {
                float a = i * GoldenAngleRad + variant * 0.5f;
                Vector3 bMid = fork + new Vector3(MathF.Cos(a) * 2.2f * sMult, 1.8f * hMult, MathF.Sin(a) * 2.2f * sMult);
                Vector3 bEnd = fork + new Vector3(MathF.Cos(a) * 4.4f * sMult, 2.9f * hMult, MathF.Sin(a) * 4.4f * sMult);
                AddTaperedCylinder(barkSt, fork, bMid, baseR * 0.34f, baseR * 0.20f, 4, bark, bark, 3, 0.05f);
                AddTaperedCylinder(barkSt, bMid, bEnd, baseR * 0.20f, baseR * 0.09f, 4, bark, bark, 3, 0.05f);
                AddPuffyFoliageDome(leafSt, bEnd, crownCenter, crownRad, crownHalfH, (lod == 0 ? 2.15f : 2.65f) * sMult, lod == 0 ? 4 : 2, leafType: 5, rng, 0.13f, (i * 0.21f) % 1.0f, acaciaUv);
            }
            AddPuffyFoliageDome(leafSt, crownCenter + Vector3.Up * 0.7f, crownCenter, crownRad, crownHalfH, 2.4f * sMult, lod == 0 ? 4 : 2, leafType: 5, rng, 0.13f, 0.55f, acaciaUv);
        }

        private static void BuildBaobabVariant(
            SurfaceTool barkSt, SurfaceTool leafSt, Random rng, float hMult, float sMult, float rMult, int variant, int lod)
        {
            var bark = new Color(0.55f, 0.43f, 0.33f, 0.0f);
            float h = (variant == 0 ? 9.8f : 11.2f) * hMult;
            float r = (variant == 0 ? 1.55f : 1.38f) * rMult;
            int sides = lod == 0 ? 9 : 5;
            Rect2 acaciaUv = new Rect2(0.337f, 0.004f, 0.326f, 0.992f);

            Vector3 p0 = new Vector3(0.0f, -0.80f, 0.0f);
            Vector3 mid = new Vector3(0.0f, h * 0.46f, 0.0f);
            Vector3 top = new Vector3(variant == 0 ? 0.2f : -0.3f, h, 0.0f);
            AddTaperedCylinder(barkSt, p0, mid, r * 1.08f, r * 1.24f, sides, bark, bark, 3, 0.04f);
            AddTaperedCylinder(barkSt, mid, top, r * 1.24f, r * 0.70f, sides, bark, bark, 3, 0.04f);

            Vector3 crownCenter = top + new Vector3(0.0f, 2.5f * hMult, 0.0f);
            float crownRad = 5.6f * sMult;
            float crownHalfH = 2.4f * hMult;
            int limbs = lod == 0 ? 5 : 4;
            for (int i = 0; i < limbs; i++)
            {
                float a = i * GoldenAngleRad + 0.3f + variant * 0.6f;
                Vector3 tip = top + new Vector3(MathF.Cos(a) * 3.8f * sMult, 2.6f * hMult, MathF.Sin(a) * 3.8f * sMult);
                AddTaperedCylinder(barkSt, top, tip, r * 0.26f, r * 0.10f, 5, bark, bark, 3, 0.04f);
                AddPuffyFoliageDome(leafSt, tip, crownCenter, crownRad, crownHalfH, (lod == 0 ? 2.05f : 2.55f) * sMult, lod == 0 ? 4 : 2, leafType: 5, rng, 0.13f, (i * 0.23f) % 1.0f, acaciaUv);
            }
        }

        // =========================================================================
        // COLUMNAR PALM & TREE FERN (2 Variants, 12-14 Gracefully Arched Fronds)
        // =========================================================================
        private static void BuildColumnarPalmFernVariant(
            SurfaceTool barkSt, SurfaceTool leafSt, Random rng, float hMult, bool isFern, int variant, int lod)
        {
            float h = (isFern ? (variant == 0 ? 3.6f : 4.4f) : (variant == 0 ? 6.4f : 7.8f)) * hMult;
            float lean = (isFern ? 0.45f : 1.15f) * (variant == 0 ? 1.0f : -0.8f);
            Vector3 p0 = new Vector3(0.0f, -0.55f, 0.0f);
            Vector3 p1 = new Vector3(lean * 0.35f, h * 0.48f, lean * 0.18f);
            Vector3 p2 = new Vector3(lean, h, lean * 0.36f);

            var cBot = new Color(0.38f, 0.30f, 0.22f, 0.0f);
            var cMid = new Color(0.42f, 0.33f, 0.24f, 0.26f);
            var cTop = new Color(0.45f, 0.36f, 0.26f, 0.42f);
            int sides = lod == 0 ? 6 : 4;
            AddTaperedCylinder(barkSt, p0, p1, isFern ? 0.22f : 0.28f, isFern ? 0.16f : 0.20f, sides, cBot, cMid, 0, isFern ? 1.1f : 0.6f);
            AddTaperedCylinder(barkSt, p1, p2, isFern ? 0.16f : 0.20f, isFern ? 0.11f : 0.13f, sides, cMid, cTop, 0, isFern ? 1.1f : 0.6f);

            int fronds = lod == 0 ? (isFern ? 12 : 14) : 7;
            float frondLen = (isFern ? 2.4f : 3.3f) * hMult;
            for (int f = 0; f < fronds; f++)
            {
                float ang = f * Mathf.Tau / fronds + (float)rng.NextDouble() * 0.12f;
                bool innerRing = (f % 2) == 0;
                Vector3 dir = new Vector3(MathF.Cos(ang), 0.0f, MathF.Sin(ang));
                Vector3 perp = new Vector3(-dir.Z, 0.0f, dir.X) * (isFern ? 0.62f : 0.78f);
                float lift = innerRing ? 0.95f : 0.50f;
                float drop = innerRing ? -0.25f : -0.85f;

                Vector3 seg1 = p2 + dir * (frondLen * 0.38f) + Vector3.Up * (lift * 0.85f);
                Vector3 seg2 = p2 + dir * (frondLen * 0.72f) + Vector3.Up * (lift * 0.45f);
                Vector3 tip = p2 + dir * frondLen + Vector3.Up * drop;

                float bp = (f / (float)fronds);
                var cRoot = new Color(bp, 1f, 1f, 0.42f);
                var cTip = new Color(bp, 1f, 1f, 0.56f);
                int lt = isFern ? 6 : 3;
                AddSprigQuad(leafSt, p2 - perp * 0.8f, p2 + perp * 0.8f, seg1 + perp, seg1 - perp, cRoot, cTip, Vector3.Up, lt, new Vector2(1.0f, 0.65f), 0.70f, 0.90f);
                AddSprigQuad(leafSt, seg1 - perp, seg1 + perp, seg2 + perp * 0.85f, seg2 - perp * 0.85f, cTip, cTip, (dir * 0.3f + Vector3.Up).Normalized(), lt, new Vector2(0.65f, 0.30f), 0.90f, 1.02f);
                AddSprigQuad(leafSt, seg2 - perp * 0.85f, seg2 + perp * 0.85f, tip + perp * 0.45f, tip - perp * 0.45f, cTip, cTip, (dir * 0.6f + Vector3.Up).Normalized(), lt, new Vector2(0.30f, 0.0f), 1.02f, 1.06f);
            }
        }

        // =========================================================================
        // PUFFY VOLUMETRIC LOD2 (450m - 1350m, ~48-64 tris): Billowing Rounded Crown Mass!
        // =========================================================================
        private static void BuildPuffyFarLod2Tree(
            SurfaceTool st, FloraSpeciesId sp, int variant, float hMult, float sMult, float rMult)
        {
            int leafType = sp switch
            {
                FloraSpeciesId.BorealSnowPine or FloraSpeciesId.SilverGlacierSpruce or FloraSpeciesId.GiantSequoiaReddawn => 1,
                FloraSpeciesId.GinkgoAncientGold or FloraSpeciesId.WeepingSilverBirch => 2,
                FloraSpeciesId.CrimsonSteppeMaple => 4,
                FloraSpeciesId.DragonBloodTree or FloraSpeciesId.SavannaUmbrellaAcacia or FloraSpeciesId.BaobabPrehistoric => 5,
                _ => 0,
            };
            bool isEmergent = sp == FloraSpeciesId.PrimevalBanyanFig || sp == FloraSpeciesId.SacredAncientHardwood || sp == FloraSpeciesId.GiantSequoiaReddawn;
            bool isConifer = leafType == 1;
            bool isUmbrella = leafType == 5;

            float totalH = (sp == FloraSpeciesId.GiantSequoiaReddawn ? 25.5f : (isEmergent ? 21.5f : (isConifer ? 15.5f : 12.8f))) * hMult;
            float trunkTopY = isConifer ? totalH * 0.84f : totalH * 0.58f;
            float baseR = (isEmergent ? 1.12f : (sp == FloraSpeciesId.BaobabPrehistoric ? 1.50f : 0.54f)) * rMult;

            var barkCol = sp == FloraSpeciesId.WeepingSilverBirch ? new Color(0.86f, 0.85f, 0.82f, 0.0f) : new Color(0.32f, 0.24f, 0.17f, 0.0f);
            AddTaperedCylinder(st, new Vector3(0.0f, -0.8f, 0.0f), new Vector3(0.0f, trunkTopY, 0.0f), baseR, baseR * 0.34f, 4, barkCol, barkCol, 0, 0.0f);

            float crownR = (isEmergent ? 7.6f : (isUmbrella ? 5.8f : (isConifer ? 3.8f : 5.2f))) * sMult;
            float crownHalfH = isConifer ? totalH * 0.40f : (isUmbrella ? 2.1f : totalH * 0.34f);
            Vector3 crownCenter = new Vector3(0.0f, isConifer ? totalH * 0.58f : totalH * 0.70f, 0.0f);

            // 4 overlapping billowy 3D crown lobes (each lobe = 3 crossed angled planes + domed cap -> 44-56 tris!)
            Vector3[] lobeOffsets = isConifer
                ? new[]
                {
                    new Vector3(0.0f, -crownHalfH * 0.44f, 0.0f),
                    new Vector3(0.0f, -crownHalfH * 0.04f, 0.0f),
                    new Vector3(0.0f, crownHalfH * 0.34f, 0.0f),
                    new Vector3(0.0f, crownHalfH * 0.64f, 0.0f),
                }
                : new[]
                {
                    new Vector3(0.0f, crownHalfH * 0.38f, 0.0f),
                    new Vector3(crownR * 0.44f, -crownHalfH * 0.12f, crownR * 0.24f),
                    new Vector3(-crownR * 0.44f, -crownHalfH * 0.08f, crownR * 0.20f),
                    new Vector3(0.06f * crownR, -crownHalfH * 0.14f, -crownR * 0.46f),
                };

            for (int l = 0; l < lobeOffsets.Length; l++)
            {
                Vector3 c = crownCenter + lobeOffsets[l];
                float rLobe = isConifer ? crownR * (1.06f - l * 0.22f) : crownR * (l == 0 ? 0.70f : 0.60f);
                float hLobe = isConifer ? crownHalfH * 0.38f : crownHalfH * (l == 0 ? 0.64f : 0.56f);
                float aoBot = Math.Clamp(0.54f + (l == 0 && !isConifer ? 0.18f : 0.0f) + (isConifer ? l * 0.10f : 0.0f), 0.54f, 0.86f);
                float aoTop = Math.Clamp(aoBot + 0.34f, 0.86f, 1.06f);
                var cWhite = new Color((l * 0.25f) % 1.0f, 1f, 1f, 0.12f);

                for (int p = 0; p < 3; p++)
                {
                    float a = p * (Mathf.Pi / 3.0f) + l * 0.72f + variant * 0.4f;
                    Vector3 right = new Vector3(MathF.Cos(a), 0.0f, MathF.Sin(a)) * rLobe;
                    Vector3 botL = c - right - Vector3.Up * hLobe;
                    Vector3 botR = c + right - Vector3.Up * hLobe;
                    Vector3 topR = c + right * (isConifer ? 0.32f : 0.88f) + Vector3.Up * hLobe;
                    Vector3 topL = c - right * (isConifer ? 0.32f : 0.88f) + Vector3.Up * hLobe;
                    Vector3 nrm = (c - crownCenter + new Vector3(-MathF.Sin(a) * 0.4f, 0.8f, MathF.Cos(a) * 0.4f)).Normalized();
                    AddSprigQuad(st, botL, botR, topR, topL, cWhite, cWhite, nrm, leafType, new Vector2(1.0f, 0.0f), aoBot, aoTop);
                }

                if (!isConifer)
                {
                    float rCap = rLobe * 0.84f;
                    float yCap = c.Y + hLobe * 0.36f;
                    Vector3 nTop = (c - crownCenter + Vector3.Up * 2.0f).Normalized();
                    AddSprigQuad(st,
                        new Vector3(c.X - rCap, yCap, c.Z - rCap),
                        new Vector3(c.X + rCap, yCap, c.Z - rCap),
                        new Vector3(c.X + rCap, yCap, c.Z + rCap),
                        new Vector3(c.X - rCap, yCap, c.Z + rCap),
                        cWhite, cWhite, nTop, leafType, new Vector2(1.0f, 0.0f), aoTop * 0.92f, aoTop);
                }
            }
        }

        // =========================================================================
        // 3D PUFFY FOLIAGE DOME BUILDER (Multi-Angle Curved Intersecting Sprigs)
        // =========================================================================
        private static void AddPuffyFoliageDome(
            SurfaceTool st,
            Vector3 pos,
            Vector3 crownCenter,
            float crownRadius,
            float crownHalfHeight,
            float domeRadius,
            int sprigCount,
            int leafType,
            Random rng,
            float windFlex,
            float branchPhase,
            Rect2? uvSubRect = null)
        {
            Vector3 radialN = (pos - crownCenter + new Vector3(0.0f, 1.35f, 0.0f)).Normalized();
            int totalPetals = Math.Max(4, sprigCount * 2);
            float baseYaw = (float)(rng.NextDouble() * Mathf.Tau);

            for (int i = 0; i < totalPetals; i++)
            {
                float a = baseYaw + i * (Mathf.Tau / totalPetals) + (float)(rng.NextDouble() - 0.5) * 0.28f;
                float innerLayerMul = (i % 3 == 0) ? 0.80f : 1.0f;

                float pitch = (i % 4) switch { 0 => 0.72f, 1 => 0.36f, 2 => 0.06f, _ => -0.18f };
                float w = domeRadius * 0.86f;
                float len = domeRadius * 1.54f;
                Vector3 dir = new Vector3(MathF.Cos(a) * MathF.Cos(pitch), MathF.Sin(pitch), MathF.Sin(a) * MathF.Cos(pitch)).Normalized();
                Vector3 side = new Vector3(-MathF.Sin(a), 0.0f, MathF.Cos(a)) * w;
                Vector3 archUp = Vector3.Up * (domeRadius * 0.28f);

                Vector3 root = pos - dir * (domeRadius * 0.22f) + new Vector3(0.0f, (i % 2 == 0 ? 0.16f : -0.16f) * domeRadius, 0.0f);
                Vector3 mid1 = root + dir * (len * 0.36f) + archUp * 0.85f;
                Vector3 mid2 = root + dir * (len * 0.70f) + archUp * 0.95f;
                Vector3 tip = root + dir * len - archUp * 0.24f;

                float aoRoot = ComputeCanopyAo(root, crownCenter, crownRadius, crownHalfHeight) * innerLayerMul;
                float aoM1 = ComputeCanopyAo(mid1, crownCenter, crownRadius, crownHalfHeight) * innerLayerMul;
                float aoM2 = ComputeCanopyAo(mid2, crownCenter, crownRadius, crownHalfHeight);
                float aoTip = ComputeCanopyAo(tip, crownCenter, crownRadius, crownHalfHeight);

                float bp = (branchPhase + i * 0.11f) % 1.0f;
                var cBot = new Color(bp, 1.0f, 1.0f, windFlex * 0.70f);
                var cTop = new Color(bp, 1.0f, 1.0f, windFlex);

                AddSprigQuad(st, root - side * 0.74f, root + side * 0.74f, mid1 + side, mid1 - side,
                    cBot, cTop, radialN, leafType, new Vector2(1.0f, 0.66f), aoRoot, aoM1, uvSubRect);
                AddSprigQuad(st, mid1 - side, mid1 + side, mid2 + side * 0.95f, mid2 - side * 0.95f,
                    cTop, cTop, (radialN + dir * 0.25f).Normalized(), leafType, new Vector2(0.66f, 0.32f), aoM1, aoM2, uvSubRect);
                AddSprigQuad(st, mid2 - side * 0.95f, mid2 + side * 0.95f, tip + side * 0.78f, tip - side * 0.78f,
                    cTop, cTop, (radialN + dir * 0.48f).Normalized(), leafType, new Vector2(0.32f, 0.0f), aoM2, aoTip, uvSubRect);
            }
        }

        private static float ComputeCanopyAo(Vector3 p, Vector3 crownCenter, float crownR, float crownHalfH)
        {
            float dx = p.X - crownCenter.X;
            float dz = p.Z - crownCenter.Z;
            float horizFrac = Math.Clamp(MathF.Sqrt(dx * dx + dz * dz) / MathF.Max(1.0f, crownR), 0.0f, 1.15f);
            float vertFrac = Math.Clamp((p.Y - (crownCenter.Y - crownHalfH)) / MathF.Max(1.5f, 2.0f * crownHalfH), 0.0f, 1.0f);

            float shell = horizFrac * horizFrac * (3.0f - 2.0f * Math.Clamp(horizFrac, 0.0f, 1.0f));
            return Math.Clamp(0.54f + 0.26f * shell + 0.26f * vertFrac, 0.54f, 1.06f);
        }

        private static void AddSprigQuad(
            SurfaceTool st, Vector3 p0, Vector3 p1, Vector3 p2, Vector3 p3,
            Color cBot, Color cTop, Vector3 radialNormal, int leafType, Vector2 vRange, float aoBot, float aoTop,
            Rect2? uvSubRect = null)
        {
            Rect2 r = uvSubRect ?? new Rect2(0.004f, 0.004f, 0.992f, 0.992f);
            float u0 = r.Position.X;
            float u1 = r.End.X;
            float vBot = r.Position.Y + vRange.X * r.Size.Y;
            float vTop = r.Position.Y + vRange.Y * r.Size.Y;

            Vector2 tagBot = new Vector2(Math.Clamp(aoBot, 0.52f, 1.08f), leafType);
            Vector2 tagTop = new Vector2(Math.Clamp(aoTop, 0.52f, 1.08f), leafType);
            Vector2 uv0 = new Vector2(u0, vBot);
            Vector2 uv1 = new Vector2(u1, vBot);
            Vector2 uv2 = new Vector2(u1, vTop);
            Vector2 uv3 = new Vector2(u0, vTop);

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
            Color cBot, Color cTop, int barkStyle, float mossMult)
        {
            Vector3 axis = (topCenter - botCenter).Normalized();
            if (axis.LengthSquared() < 0.001f) return;
            float segLen = botCenter.DistanceTo(topCenter);
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
            Vector2 barkTag = new Vector2(barkStyle, mossMult);
            float vRepeat = MathF.Max(1.0f, segLen * 0.45f);

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
                EmitBark(ringTop[next], ringNorm[next], cTop, new Vector2(u1, vRepeat));

                EmitBark(ringBot[i], ringNorm[i], cBot, new Vector2(u0, 0f));
                EmitBark(ringTop[next], ringNorm[next], cTop, new Vector2(u1, vRepeat));
                EmitBark(ringTop[i], ringNorm[i], cTop, new Vector2(u0, vRepeat));
            }
        }
    }
}
