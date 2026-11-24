using System;
using System.Collections.Generic;
using Godot;

namespace PrimevalWorld.Flora
{
    /// <summary>
    /// Phase 1 Multi-Variant Mesh Library (2-Surface PBR Bark/Moss + Botanical Foliage):
    /// - Shares morphological variant meshes cleanly across species families via GetCanonicalMeshKey()
    ///   so 4 distinct broadleaf variants & 3 conifer variants keep SceneTree nodes < 1,200!
    /// - Builds Hanging Moss Lianas (2 variants) and the upgraded 5-Species Dense Understory (0m..3.5m):
    ///   1) Lush Sword Fern (2 variants, 12-14 fronds, strong emerald backlight)
    ///   2) Giant Broadleaf Aroid / Elephant Ear (2 variants, 6-7 glossy arched blades)
    ///   3) Dense Understory Shrub (2 variants, 2-surface bark_moss + leafy volume)
    ///   4) Mossy Fallen Log (2 variants, sculpted trunk on bark_moss.gdshader)
    ///   5) Hanging Moss Liana Curtain (2 variants, draping 4-12m with gentle sway).
    /// </summary>
    public sealed class FloraMeshLibrary
    {
        public readonly struct MeshKey : IEquatable<MeshKey>
        {
            public readonly FloraSpeciesId CanonicalSpecies;
            public readonly byte Variant;

            public MeshKey(FloraSpeciesId canonicalSpecies, byte variant)
            {
                CanonicalSpecies = canonicalSpecies;
                Variant = variant;
            }

            public bool Equals(MeshKey other) => CanonicalSpecies == other.CanonicalSpecies && Variant == other.Variant;
            public override bool Equals(object? obj) => obj is MeshKey other && Equals(other);
            public override int GetHashCode() => ((int)CanonicalSpecies << 4) ^ Variant;
        }

        private readonly Dictionary<(FloraSpeciesId, int, int), ArrayMesh> _cache = new();

        public static MeshKey GetCanonicalMeshKey(FloraSpeciesId species, byte variant)
        {
            // Share morphological families cleanly to keep SceneTree nodes < 1,200 while rendering 3-4 distinct shapes!
            return species switch
            {
                FloraSpeciesId.PrimevalBanyanFig or FloraSpeciesId.SacredAncientHardwood or FloraSpeciesId.StarAppleCanopy =>
                    new MeshKey(FloraSpeciesId.SacredAncientHardwood, (byte)(variant & 3)),
                FloraSpeciesId.GinkgoAncientGold => new MeshKey(FloraSpeciesId.GinkgoAncientGold, (byte)(variant & 1)),
                FloraSpeciesId.CrimsonSteppeMaple => new MeshKey(FloraSpeciesId.CrimsonSteppeMaple, (byte)(variant & 1)),
                FloraSpeciesId.BorealSnowPine or FloraSpeciesId.SilverGlacierSpruce or FloraSpeciesId.GiantSequoiaReddawn =>
                    new MeshKey(FloraSpeciesId.BorealSnowPine, (byte)(variant % 3)),
                FloraSpeciesId.DragonBloodTree or FloraSpeciesId.SavannaUmbrellaAcacia =>
                    new MeshKey(FloraSpeciesId.DragonBloodTree, (byte)(variant & 1)),
                FloraSpeciesId.BaobabPrehistoric => new MeshKey(FloraSpeciesId.BaobabPrehistoric, (byte)(variant & 1)),
                FloraSpeciesId.WeepingRiverWillow => new MeshKey(FloraSpeciesId.WeepingRiverWillow, (byte)(variant & 1)),
                FloraSpeciesId.WeepingSilverBirch => new MeshKey(FloraSpeciesId.WeepingSilverBirch, (byte)(variant & 1)),
                FloraSpeciesId.ArborescentTreeFern => new MeshKey(FloraSpeciesId.ArborescentTreeFern, (byte)(variant & 1)),
                FloraSpeciesId.NipaWaterPalm => new MeshKey(FloraSpeciesId.NipaWaterPalm, (byte)(variant & 1)),
                FloraSpeciesId.LushSwordFern => new MeshKey(FloraSpeciesId.LushSwordFern, (byte)(variant & 1)),
                FloraSpeciesId.GiantElephantEar => new MeshKey(FloraSpeciesId.GiantElephantEar, (byte)(variant & 1)),
                FloraSpeciesId.LianaMossCurtain => new MeshKey(FloraSpeciesId.LianaMossCurtain, (byte)(variant & 1)),
                FloraSpeciesId.WildBerryBush or FloraSpeciesId.HawthornBerryShrub =>
                    new MeshKey(FloraSpeciesId.WildBerryBush, (byte)(variant & 1)),
                FloraSpeciesId.HollowFallenTrunk => new MeshKey(FloraSpeciesId.HollowFallenTrunk, (byte)(variant & 1)),
                _ => new MeshKey(species, 0),
            };
        }

        public static bool IsCloseUnderstorySpecies(FloraSpeciesId id) => id switch
        {
            FloraSpeciesId.LushSwordFern => true,
            FloraSpeciesId.GiantElephantEar => true,
            FloraSpeciesId.LianaMossCurtain => true,
            FloraSpeciesId.HollowFallenTrunk => true,
            FloraSpeciesId.WildBerryBush => true,
            FloraSpeciesId.HawthornBerryShrub => true,
            FloraSpeciesId.EpiphyteBaseVine => true,
            FloraSpeciesId.WetMossPatch => true,
            FloraSpeciesId.BiolumForestMushroom => true,
            _ => false,
        };

        public ArrayMesh GetMesh(
            FloraSpeciesId species,
            int variant,
            int lod,
            Material? barkMat,
            Material? leafMat)
        {
            FloraNicheProfile profile = FloraNicheDatabase.AllSpecies[(int)species];
            int clampedLod = profile.Layer <= FloraLayer.Canopy ? Math.Clamp(lod, 0, 2) : 0;
            var key = (species, variant, clampedLod);

            if (_cache.TryGetValue(key, out ArrayMesh? existing))
            {
                AssignSurfaceMaterials(existing, species, clampedLod, barkMat, leafMat);
                return existing;
            }

            ArrayMesh built = BuildProceduralMesh(profile, variant, clampedLod);
            AssignSurfaceMaterials(built, species, clampedLod, barkMat, leafMat);
            _cache[key] = built;
            return built;
        }

        public static void AssignSurfaceMaterials(ArrayMesh mesh, FloraSpeciesId species, int lod, Material? barkMat, Material? leafMat)
        {
            int surfCount = mesh.GetSurfaceCount();
            if (surfCount == 0) return;

            if (surfCount >= 2)
            {
                if (barkMat != null) mesh.SurfaceSetMaterial(0, barkMat);
                if (leafMat != null) mesh.SurfaceSetMaterial(1, leafMat);
            }
            else
            {
                // Single-surface meshes: Fallen Log uses bark_moss.gdshader; LOD2 & Herbs/Ferns/Lianas/Boulders use flora_wind.gdshader
                bool barkOnly = species == FloraSpeciesId.HollowFallenTrunk;
                Material? mat = barkOnly ? barkMat : leafMat;
                if (mat != null) mesh.SurfaceSetMaterial(0, mat);
            }
        }

        public static int GetTriangleCount(ArrayMesh mesh)
        {
            int total = 0;
            for (int s = 0; s < mesh.GetSurfaceCount(); s++)
                total += mesh.SurfaceGetArrayLen(s) / 3;
            return total;
        }

        private static ArrayMesh BuildProceduralMesh(FloraNicheProfile p, int variant, int lod)
        {
            if (p.Layer <= FloraLayer.Canopy || p.Id == FloraSpeciesId.ArborescentTreeFern || p.Id == FloraSpeciesId.NipaWaterPalm)
                return ProceduralTreeBuilder.BuildTree(p.Id, AgeStage.Mature, 2026, lod, variant);

            if (p.Id == FloraSpeciesId.LianaMossCurtain)
                return CreateLianaMossCurtainMesh(variant);
            if (p.Id == FloraSpeciesId.LushSwordFern)
                return CreateLushSwordFernMesh(variant);
            if (p.Id == FloraSpeciesId.GiantElephantEar)
                return CreateGiantBroadleafAroidMesh(variant);
            if (p.Id == FloraSpeciesId.HollowFallenTrunk)
                return CreateMossyFallenLogMesh(variant);

            return p.Architecture switch
            {
                FloraArchitecture.ArchKrummholz => CreateKrummholzMesh(),
                FloraArchitecture.ArchWoodyShrub => CreateDenseUnderstoryShrubMesh(variant),
                FloraArchitecture.ArchCaudexCycad => CreateCaudexCycadMesh(),
                FloraArchitecture.ArchBambooCulm => CreateBambooCulmMesh(),
                FloraArchitecture.ArchSoftTallHerb => CreateSoftTallHerbMesh(p.Id),
                _ => CreateSucculentAndGroundMesh(p.Id),
            };
        }

        // =========================================================================
        // 1. HANGING MOSS LIANA CURTAIN (2 Variants, Draping 4m-12m with Soft Sway)
        // =========================================================================
        private static ArrayMesh CreateLianaMossCurtainMesh(int variant)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var rng = new Random(8801 + variant * 137);

            int strands = variant == 0 ? 5 : 4;
            for (int s = 0; s < strands; s++)
            {
                float a = s * Mathf.Tau / strands + (float)rng.NextDouble() * 0.45f;
                // Offset outward under the canopy boughs (1.6m..3.6m from trunk) so lianas drape as free curtains, not pasted onto bark!
                float rOff = 1.65f + (s % 3) * 0.85f;
                float topY = 9.0f + (float)rng.NextDouble() * 4.5f;
                float len = 5.2f + (float)rng.NextDouble() * 4.6f;
                float botY = MathF.Max(1.35f, topY - len);
                float width = 0.24f + (s % 2) * 0.12f;

                Vector3 sideA = new Vector3(-MathF.Sin(a), 0.0f, MathF.Cos(a)) * width;
                Vector3 sideB = new Vector3(MathF.Cos(a), 0.0f, MathF.Sin(a)) * width;
                Vector3 topPos = new Vector3(MathF.Cos(a) * rOff, topY, MathF.Sin(a) * rOff);

                const int segs = 4;
                for (int k = 0; k < segs; k++)
                {
                    float t0 = k / (float)segs;
                    float t1 = (k + 1) / (float)segs;
                    float y0 = Mathf.Lerp(topY, botY, t0);
                    float y1 = Mathf.Lerp(topY, botY, t1);
                    float bow0 = MathF.Sin(t0 * Mathf.Pi) * 0.48f;
                    float bow1 = MathF.Sin(t1 * Mathf.Pi) * 0.48f;

                    Vector3 c0 = new Vector3(topPos.X + sideB.X * bow0, y0, topPos.Z + sideB.Z * bow0);
                    Vector3 c1 = new Vector3(topPos.X + sideB.X * bow1, y1, topPos.Z + sideB.Z * bow1);

                    float bp = (s * 0.21f) % 1.0f;
                    var col0 = new Color(bp, 1f, 1f, 0.24f + t0 * 0.48f);
                    var col1 = new Color(bp, 1f, 1f, 0.24f + t1 * 0.48f);
                    // Crossed perpendicular ribbons so hanging moss curtains look volumetric from every camera angle!
                    AddLeafQuad(st, c0 - sideA, c0 + sideA, c1 + sideA * 0.82f, c1 - sideA * 0.82f,
                        col0, col1, Vector3.Up, new Rect2(0, t0, 1, t1 - t0), leafType: 6, aoBot: 0.74f, aoTop: 0.90f);
                    AddLeafQuad(st, c0 - sideB, c0 + sideB, c1 + sideB * 0.82f, c1 - sideB * 0.82f,
                        col0, col1, Vector3.Up, new Rect2(0, t0, 1, t1 - t0), leafType: 6, aoBot: 0.74f, aoTop: 0.90f);
                }
            }
            return st.Commit();
        }

        // =========================================================================
        // 2. LUSH SWORD FERN (2 Variants, 12-14 Curved Fronds in 2 Angled Rings, Backlit!)
        // =========================================================================
        private static ArrayMesh CreateLushSwordFernMesh(int variant)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var rng = new Random(4409 + variant * 97);

            int outerCount = variant == 0 ? 8 : 7;
            int innerCount = variant == 0 ? 6 : 5;

            void AddFrondRing(int count, float lenScale, float liftH, float endDrop, float widthM, float phaseOff)
            {
                for (int i = 0; i < count; i++)
                {
                    float a = i * Mathf.Tau / count + phaseOff + (float)(rng.NextDouble() - 0.5) * 0.18f;
                    Vector3 dir = new Vector3(MathF.Cos(a), 0.0f, MathF.Sin(a));
                    Vector3 perp = new Vector3(-dir.Z, 0.0f, dir.X) * widthM;
                    float len = lenScale * (0.88f + (float)rng.NextDouble() * 0.26f);

                    Vector3 root = new Vector3(0.0f, 0.06f, 0.0f) + dir * 0.08f;
                    Vector3 mid1 = root + dir * (len * 0.38f) + Vector3.Up * (liftH * 0.78f);
                    Vector3 mid2 = root + dir * (len * 0.74f) + Vector3.Up * liftH;
                    Vector3 tip = root + dir * len + Vector3.Up * (liftH - endDrop);

                    float bp = (i / (float)count + phaseOff) % 1.0f;
                    var c0 = new Color(bp, 1f, 1f, 0.15f);
                    var c1 = new Color(bp, 1f, 1f, 0.45f);
                    var c2 = new Color(bp, 1f, 1f, 0.78f);

                    AddLeafQuad(st, root - perp * 0.65f, root + perp * 0.65f, mid1 + perp, mid1 - perp,
                        c0, c1, Vector3.Up, new Rect2(0.0f, 0.62f, 1.0f, 0.38f), leafType: 6, aoBot: 0.62f, aoTop: 0.86f);
                    AddLeafQuad(st, mid1 - perp, mid1 + perp, mid2 + perp * 0.85f, mid2 - perp * 0.85f,
                        c1, c2, (dir * 0.25f + Vector3.Up).Normalized(), new Rect2(0.0f, 0.28f, 1.0f, 0.34f), leafType: 6, aoBot: 0.86f, aoTop: 1.00f);
                    AddLeafQuad(st, mid2 - perp * 0.85f, mid2 + perp * 0.85f, tip + perp * 0.40f, tip - perp * 0.40f,
                        c2, c2, (dir * 0.55f + Vector3.Up).Normalized(), new Rect2(0.0f, 0.0f, 1.0f, 0.28f), leafType: 6, aoBot: 1.00f, aoTop: 1.06f);
                }
            }

            // Outer low-spreading ring hugging 0.15..0.55m + inner upright ring rising 0.85..1.45m
            AddFrondRing(outerCount, variant == 0 ? 1.55f : 1.35f, 0.48f, 0.28f, 0.44f, 0.0f);
            AddFrondRing(innerCount, variant == 0 ? 1.25f : 1.45f, 1.15f, 0.20f, 0.40f, 0.42f);
            return st.Commit();
        }

        // =========================================================================
        // 3. GIANT BROADLEAF AROID (Elephant Ear / Wild Banana, 2 Variants, 1.2m-2.4m)
        // =========================================================================
        private static ArrayMesh CreateGiantBroadleafAroidMesh(int variant)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            int leaves = variant == 0 ? 6 : 7;

            for (int i = 0; i < leaves; i++)
            {
                float a = i * Mathf.Tau / leaves + variant * 0.45f;
                Vector3 d = new Vector3(MathF.Cos(a), 0.0f, MathF.Sin(a));
                Vector3 p = new Vector3(-d.Z, 0.0f, d.X);
                float h = (variant == 0 ? 1.25f : 1.65f) + (i % 3) * 0.28f;
                float reach = 0.65f + (i % 2) * 0.22f;

                Vector3 petioleTop = d * reach + new Vector3(0.0f, h, 0.0f);
                AddTaperedCylinder(st, Vector3.Zero, petioleTop, 0.055f, 0.032f, 4,
                    new Color(0.22f, 0.42f, 0.14f, 0.0f), new Color(0.34f, 0.56f, 0.18f, 0.35f), 0, 0.0f);

                // Large arched glossy broadleaf blade (2 segments for natural organic curve!)
                float bladeW = 0.62f + (i % 2) * 0.14f;
                Vector3 bladeMid = petioleTop + d * 0.62f + Vector3.Up * 0.18f;
                Vector3 bladeTip = petioleTop + d * 1.28f - Vector3.Up * 0.24f;
                float bp = (i / (float)leaves);
                var cBase = new Color(bp, 1f, 1f, 0.42f);
                var cTip = new Color(bp, 1f, 1f, 0.78f);

                AddLeafQuad(st, petioleTop - p * (bladeW * 0.72f), petioleTop + p * (bladeW * 0.72f),
                    bladeMid + p * bladeW, bladeMid - p * bladeW, cBase, cTip, Vector3.Up,
                    new Rect2(0.0f, 0.45f, 1.0f, 0.55f), leafType: 0, aoBot: 0.78f, aoTop: 1.02f);
                AddLeafQuad(st, bladeMid - p * bladeW, bladeMid + p * bladeW,
                    bladeTip + p * (bladeW * 0.35f), bladeTip - p * (bladeW * 0.35f), cTip, cTip, (d * 0.4f + Vector3.Up).Normalized(),
                    new Rect2(0.0f, 0.0f, 1.0f, 0.45f), leafType: 0, aoBot: 1.02f, aoTop: 1.06f);
            }
            return st.Commit();
        }

        // =========================================================================
        // 4. DENSE UNDERSTORY SHRUB & LOW SAPLING (2 Variants, 1.0m-2.6m, 2-Surface)
        // =========================================================================
        private static ArrayMesh CreateDenseUnderstoryShrubMesh(int variant)
        {
            var barkSt = new SurfaceTool();
            barkSt.Begin(Mesh.PrimitiveType.Triangles);
            var leafSt = new SurfaceTool();
            leafSt.Begin(Mesh.PrimitiveType.Triangles);

            var stemCol = new Color(0.36f, 0.29f, 0.21f, 0.0f);
            int stems = variant == 0 ? 6 : 5;
            float maxH = variant == 0 ? 1.85f : 2.35f;

            for (int b = 0; b < stems; b++)
            {
                float a = b * Mathf.Tau / stems + variant * 0.5f;
                float r = (variant == 0 ? 0.95f : 0.78f) + (b % 2) * 0.25f;
                float h = maxH * (0.72f + (b % 3) * 0.14f);
                Vector3 tip = new Vector3(MathF.Cos(a) * r, h, MathF.Sin(a) * r);
                AddTaperedCylinder(barkSt, new Vector3(0f, -0.25f, 0f), tip, 0.07f, 0.025f, 4, stemCol, stemCol, 0, 0.85f);
                AddLeafCardCluster(leafSt, tip * 0.82f, 1.05f, 0.78f, 3, 0, a, 0.18f, (b * 0.19f) % 1.0f);
            }
            AddLeafCardCluster(leafSt, new Vector3(0.0f, maxH * 0.65f, 0.0f), 1.35f, 0.95f, 4, 0, 0.3f, 0.18f, 0.5f);

            barkSt.GenerateTangents();
            var mesh = new ArrayMesh();
            barkSt.Commit(mesh); // Surface 0: bark_moss.gdshader
            leafSt.Commit(mesh); // Surface 1: flora_wind.gdshader
            return mesh;
        }

        // =========================================================================
        // 5. MOSSY FALLEN LOG (2 Variants, Sculpted Trunk + Broken Stubs, bark_moss.gdshader!)
        // =========================================================================
        private static ArrayMesh CreateMossyFallenLogMesh(int variant)
        {
            var barkSt = new SurfaceTool();
            barkSt.Begin(Mesh.PrimitiveType.Triangles);
            var cBark = new Color(0.42f, 0.35f, 0.27f, 0.0f);

            float len = variant == 0 ? 4.8f : 6.2f;
            float rBase = variant == 0 ? 0.44f : 0.54f;
            Vector3 p0 = new Vector3(-len * 0.5f, rBase * 0.55f, 0.0f);
            Vector3 p1 = new Vector3(0.0f, rBase * 0.62f, variant == 0 ? 0.18f : -0.22f);
            Vector3 p2 = new Vector3(len * 0.5f, rBase * 0.48f, 0.08f);

            // UV2.y = 1.45 -> lush thick green moss blanket across the entire upward-facing top of the fallen log!
            AddTaperedCylinder(barkSt, p0, p1, rBase * 1.15f, rBase * 0.88f, 8, cBark, cBark, 0, 1.45f);
            AddTaperedCylinder(barkSt, p1, p2, rBase * 0.88f, rBase * 0.58f, 7, cBark, cBark, 0, 1.45f);

            // Broken branch stubs & flared uprooted base
            AddTaperedCylinder(barkSt, p0.Lerp(p1, 0.55f), p0.Lerp(p1, 0.55f) + new Vector3(0.4f, 0.65f, 0.55f),
                rBase * 0.34f, rBase * 0.14f, 5, cBark, cBark, 0, 1.35f);
            AddTaperedCylinder(barkSt, p1.Lerp(p2, 0.45f), p1.Lerp(p2, 0.45f) + new Vector3(-0.3f, 0.55f, -0.50f),
                rBase * 0.28f, rBase * 0.12f, 5, cBark, cBark, 0, 1.35f);

            barkSt.GenerateTangents();
            return barkSt.Commit(); // Single Surface 0 using bark_moss.gdshader!
        }

        // =========================================================================
        // REMAINING UNDERSTORY / GROUND ARCHITECTURES
        // =========================================================================
        private static ArrayMesh CreateKrummholzMesh()
        {
            var barkSt = new SurfaceTool();
            barkSt.Begin(Mesh.PrimitiveType.Triangles);
            var leafSt = new SurfaceTool();
            leafSt.Begin(Mesh.PrimitiveType.Triangles);
            var bark = new Color(0.34f, 0.26f, 0.20f, 0.0f);
            AddTaperedCylinder(barkSt, new Vector3(0f, -0.2f, 0f), new Vector3(1.1f, 0.75f, 0.35f), 0.18f, 0.09f, 5, bark, bark, 1, 0.35f);
            AddTaperedCylinder(barkSt, new Vector3(1.1f, 0.75f, 0.35f), new Vector3(2.0f, 1.25f, 0.55f), 0.10f, 0.05f, 4, bark, bark, 1, 0.35f);
            AddLeafCardCluster(leafSt, new Vector3(1.8f, 1.35f, 0.50f), 1.45f, 0.75f, 4, 1, 0.2f, 0.16f, 0.2f);
            AddLeafCardCluster(leafSt, new Vector3(0.5f, 0.90f, -0.35f), 1.15f, 0.65f, 3, 1, 1.1f, 0.15f, 0.7f);
            barkSt.GenerateTangents();
            var mesh = new ArrayMesh();
            barkSt.Commit(mesh);
            leafSt.Commit(mesh);
            return mesh;
        }

        private static ArrayMesh CreateCaudexCycadMesh()
        {
            var barkSt = new SurfaceTool();
            barkSt.Begin(Mesh.PrimitiveType.Triangles);
            var leafSt = new SurfaceTool();
            leafSt.Begin(Mesh.PrimitiveType.Triangles);
            AddTaperedCylinder(barkSt, new Vector3(0f, -0.25f, 0f), new Vector3(0.0f, 1.15f, 0.0f), 0.36f, 0.28f, 6,
                new Color(0.32f, 0.24f, 0.17f, 0.0f), new Color(0.36f, 0.28f, 0.20f, 0.10f), 0, 0.85f);
            Vector3 crown = new Vector3(0.0f, 1.10f, 0.0f);
            for (int f = 0; f < 10; f++)
            {
                float ang = f * Mathf.Tau / 10.0f;
                Vector3 dir = new Vector3(MathF.Cos(ang), 0.0f, MathF.Sin(ang));
                Vector3 perp = new Vector3(-dir.Z, 0.0f, dir.X) * 0.62f;
                Vector3 tip = crown + dir * 1.55f + new Vector3(0.0f, 0.78f, 0.0f);
                float bp = f / 10.0f;
                AddLeafQuad(leafSt, crown - perp, crown + perp, tip + perp, tip - perp,
                    new Color(bp, 1f, 1f, 0.18f), new Color(bp, 1f, 1f, 0.36f), (dir + Vector3.Up).Normalized(),
                    new Rect2(0, 0, 1, 1), leafType: 6, aoBot: 0.72f, aoTop: 1.02f);
            }
            barkSt.GenerateTangents();
            var mesh = new ArrayMesh();
            barkSt.Commit(mesh);
            leafSt.Commit(mesh);
            return mesh;
        }

        private static ArrayMesh CreateBambooCulmMesh()
        {
            var barkSt = new SurfaceTool();
            barkSt.Begin(Mesh.PrimitiveType.Triangles);
            var leafSt = new SurfaceTool();
            leafSt.Begin(Mesh.PrimitiveType.Triangles);
            var cBot = new Color(0.55f, 0.72f, 0.38f, 0.0f);
            var cMid = new Color(0.68f, 0.84f, 0.46f, 0.32f);
            var cTop = new Color(0.84f, 0.96f, 0.58f, 0.54f);
            for (int i = 0; i < 8; i++)
            {
                float a = i * Mathf.Tau / 8.0f + 0.15f;
                float r = 0.28f + (i % 2) * 0.22f;
                Vector3 b = new Vector3(MathF.Cos(a) * r, -0.2f, MathF.Sin(a) * r);
                Vector3 m = new Vector3(MathF.Cos(a) * (r + 0.18f), 3.1f, MathF.Sin(a) * (r + 0.18f));
                Vector3 t = new Vector3(MathF.Cos(a) * (r + 0.65f), 5.8f + (i % 3) * 0.55f, MathF.Sin(a) * (r + 0.65f));
                AddTaperedCylinder(barkSt, b, m, 0.08f, 0.06f, 4, cBot, cMid, 0, 0.15f);
                AddTaperedCylinder(barkSt, m, t, 0.06f, 0.03f, 4, cMid, cTop, 0, 0.10f);
                AddLeafCardCluster(leafSt, t, 0.98f, 0.58f, 2, 0, i * 0.8f, 0.52f, (i * 0.13f) % 1.0f);
            }
            barkSt.GenerateTangents();
            var mesh = new ArrayMesh();
            barkSt.Commit(mesh);
            leafSt.Commit(mesh);
            return mesh;
        }

        private static ArrayMesh CreateSoftTallHerbMesh(FloraSpeciesId id)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            int blades = id == FloraSpeciesId.FeatherSteppeGrass ? 7 : 6;
            float h = id == FloraSpeciesId.FeatherSteppeGrass ? 0.65f : 1.45f;
            var bot = new Color(0.62f, 0.60f, 0.46f, 0.0f);
            var top = new Color(1.0f, 0.98f, 0.92f, 0.92f);
            for (int b = 0; b < blades; b++)
            {
                float a = b * Mathf.Tau / blades;
                Vector3 d = new Vector3(MathF.Cos(a), 0.0f, MathF.Sin(a));
                Vector3 p = new Vector3(-d.Z, 0.0f, d.X) * 0.14f;
                Vector3 root = d * 0.12f;
                Vector3 tip = d * (id == FloraSpeciesId.RiverbankReedBed ? 0.25f : 0.65f) + new Vector3(0.0f, h, 0.0f);
                AddSolidTriangle(st, root - p, root + p, tip, bot, bot, top);
            }
            return st.Commit();
        }

        private static ArrayMesh CreateSucculentAndGroundMesh(FloraSpeciesId id)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            if (id == FloraSpeciesId.RedDesertAgave || id == FloraSpeciesId.RedRockSucculent)
            {
                int blades = id == FloraSpeciesId.RedRockSucculent ? 8 : 6;
                float r = id == FloraSpeciesId.RedRockSucculent ? 0.55f : 1.05f;
                float h = id == FloraSpeciesId.RedRockSucculent ? 0.35f : 1.05f;
                var bot = new Color(0.55f, 0.62f, 0.45f, 0.0f);
                var top = new Color(0.95f, 1.0f, 0.85f, 0.02f);
                for (int b = 0; b < blades; b++)
                {
                    float a = b * Mathf.Tau / blades;
                    Vector3 d = new Vector3(MathF.Cos(a), 0.0f, MathF.Sin(a));
                    Vector3 p = new Vector3(-d.Z, 0.0f, d.X) * (r * 0.20f);
                    AddSolidTriangle(st, -p, p, d * r + new Vector3(0.0f, h, 0.0f), bot, bot, top);
                }
            }
            else if (id == FloraSpeciesId.EpiphyteBaseVine)
            {
                AddLeafCardCluster(st, new Vector3(0.0f, 1.05f, 0.0f), 1.05f, 0.95f, 4, 0, 0.3f, 0.10f, 0.3f);
            }
            else if (id == FloraSpeciesId.BiolumForestMushroom)
            {
                var stem = new Color(0.85f, 0.82f, 0.72f, 0.0f);
                var cap = new Color(0.98f, 0.92f, 0.76f, 0.02f);
                for (int i = 0; i < 3; i++)
                {
                    float a = i * Mathf.Tau / 3.0f;
                    Vector3 off = new Vector3(MathF.Cos(a) * 0.20f, 0.0f, MathF.Sin(a) * 0.20f);
                    float h = 0.28f + (i == 0 ? 0.14f : 0.0f);
                    AddTaperedCylinder(st, off, off + new Vector3(0.0f, h, 0.0f), 0.05f, 0.03f, 4, stem, stem, 0, 0.0f);
                    AddSolidConeCap(st, off + new Vector3(0.0f, h, 0.0f), 0.18f, 0.14f, 5, i * 0.5f, cap);
                }
            }
            else if (id == FloraSpeciesId.WetMossPatch || id == FloraSpeciesId.ArcticReindeerMoss || id == FloraSpeciesId.StreamClayDeposit)
            {
                AddSolidBoulder(st, new Vector3(0.0f, 0.12f, 0.0f), 1.05f, 0.22f, 6, 0.3f,
                    new Color(0.60f, 0.65f, 0.55f, 0.0f), new Color(0.95f, 1.0f, 0.90f, 0.0f));
            }
            else
            {
                AddSolidBoulder(st, new Vector3(0.0f, 0.42f, 0.0f), 1.05f, 0.80f, 5, 0.6f,
                    new Color(0.55f, 0.58f, 0.55f, 0.0f), new Color(0.92f, 0.96f, 0.92f, 0.0f));
            }

            return st.Commit();
        }

        private static void AddLeafCardCluster(
            SurfaceTool st, Vector3 center, float radius, float halfHeight, int cardPairs, int leafType, float phase, float windFlex, float branchPhase)
        {
            var uvR = new Rect2(0, 0, 1, 1);
            var colBot = new Color(branchPhase, 1f, 1f, windFlex * 0.7f);
            var colTop = new Color(branchPhase, 1f, 1f, windFlex);

            for (int i = 0; i < cardPairs; i++)
            {
                float a = i * Mathf.Tau / cardPairs + phase;
                float rOff = i == 0 ? 0.0f : radius * 0.42f;
                Vector3 cPos = center + new Vector3(MathF.Cos(a) * rOff, ((i % 3) - 1) * halfHeight * 0.28f, MathF.Sin(a) * rOff);
                float cardW = radius * (i == 0 ? 1.12f : 0.82f);
                float cardH = halfHeight * (i == 0 ? 1.02f : 0.84f);

                Vector3 radialN = (cPos - center + new Vector3(0.0f, halfHeight * 0.35f, 0.0f)).Normalized();
                Vector3 right = new Vector3(MathF.Cos(a + 0.4f), 0.0f, MathF.Sin(a + 0.4f)) * cardW;
                Vector3 up = new Vector3(0.0f, cardH, 0.0f);

                AddLeafQuad(st, cPos - right - up, cPos + right - up, cPos + right + up, cPos - right + up, colBot, colTop, radialN, uvR, leafType, 0.68f, 1.02f);
                Vector3 rightB = new Vector3(-right.Z, right.Y + cardH * 0.25f, right.X);
                AddLeafQuad(st, cPos - rightB - up, cPos + rightB - up, cPos + rightB + up, cPos - rightB + up, colBot, colTop, radialN, uvR, leafType, 0.68f, 1.02f);
            }
        }

        private static void AddLeafQuad(
            SurfaceTool st, Vector3 p0, Vector3 p1, Vector3 p2, Vector3 p3,
            Color cBot, Color cTop, Vector3 radialNormal, Rect2 uvRect, int leafType, float aoBot, float aoTop)
        {
            Vector2 uv0 = new Vector2(uvRect.Position.X, uvRect.End.Y);
            Vector2 uv1 = new Vector2(uvRect.End.X, uvRect.End.Y);
            Vector2 uv2 = new Vector2(uvRect.End.X, uvRect.Position.Y);
            Vector2 uv3 = new Vector2(uvRect.Position.X, uvRect.Position.Y);
            Vector2 leafTagBot = new Vector2(Math.Clamp(aoBot, 0.52f, 1.08f), leafType);
            Vector2 leafTagTop = new Vector2(Math.Clamp(aoTop, 0.52f, 1.08f), leafType);

            void Emit(Vector3 p, Color c, Vector2 uv, Vector2 tag)
            {
                st.SetNormal(radialNormal);
                st.SetColor(c);
                st.SetUV(uv);
                st.SetUV2(tag);
                st.AddVertex(p);
            }

            Emit(p0, cBot, uv0, leafTagBot); Emit(p1, cBot, uv1, leafTagBot); Emit(p2, cTop, uv2, leafTagTop);
            Emit(p0, cBot, uv0, leafTagBot); Emit(p2, cTop, uv2, leafTagTop); Emit(p3, cTop, uv3, leafTagTop);
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
            float vRep = MathF.Max(1.0f, segLen * 0.45f);

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
                EmitBark(ringTop[next], ringNorm[next], cTop, new Vector2(u1, vRep));

                EmitBark(ringBot[i], ringNorm[i], cBot, new Vector2(u0, 0f));
                EmitBark(ringTop[next], ringNorm[next], cTop, new Vector2(u1, vRep));
                EmitBark(ringTop[i], ringNorm[i], cTop, new Vector2(u0, vRep));
            }
        }

        private static void AddSolidTriangle(SurfaceTool st, Vector3 a, Vector3 b, Vector3 c, Color ca, Color cb, Color cc)
        {
            Vector3 n = (b - a).Cross(c - a).Normalized();
            if (n.LengthSquared() < 0.001f) n = Vector3.Up;
            Vector2 solidTag = new Vector2(-1.0f, 0.0f);
            void Emit(Vector3 p, Color col) { st.SetNormal(n); st.SetColor(col); st.SetUV(Vector2.Zero); st.SetUV2(solidTag); st.AddVertex(p); }
            Emit(a, ca); Emit(b, cb); Emit(c, cc);
        }

        private static void AddSolidConeCap(SurfaceTool st, Vector3 center, float radius, float height, int sides, float phase, Color col)
        {
            Vector3 apex = center + new Vector3(0.0f, height, 0.0f);
            for (int i = 0; i < sides; i++)
            {
                float a0 = i * Mathf.Tau / sides + phase;
                float a1 = ((i + 1) % sides) * Mathf.Tau / sides + phase;
                AddSolidTriangle(st, apex, center + new Vector3(MathF.Cos(a1) * radius, 0f, MathF.Sin(a1) * radius),
                    center + new Vector3(MathF.Cos(a0) * radius, 0f, MathF.Sin(a0) * radius), col, col, col);
            }
        }

        private static void AddSolidBoulder(SurfaceTool st, Vector3 center, float radius, float halfHeight, int sides, float phase, Color botCol, Color topCol)
        {
            // Organic weathered rounded boulder (3-ring beveled dome + mossy top tint, eliminating sharp pyramid silhouette!)
            int n = Math.Max(7, sides);
            Vector3[] rBot = new Vector3[n];
            Vector3[] rMid = new Vector3[n];
            Vector3[] rTop = new Vector3[n];
            Color mossyTop = topCol.Lerp(new Color(0.24f, 0.34f, 0.18f, 0.0f), 0.45f);
            Vector3 capCenter = center + new Vector3(0.08f * radius, halfHeight * 0.92f, -0.06f * radius);

            for (int i = 0; i < n; i++)
            {
                float a = i * Mathf.Tau / n + phase;
                float lump = 0.84f + 0.20f * MathF.Sin(a * 2.0f + phase) + 0.12f * MathF.Cos(a * 3.0f - phase * 1.3f);
                float rM = radius * lump;
                float yOff = 0.14f * halfHeight * MathF.Sin(a * 3.0f + phase);
                rBot[i] = center + new Vector3(MathF.Cos(a) * rM * 0.92f, -halfHeight * 0.45f, MathF.Sin(a) * rM * 0.92f);
                rMid[i] = center + new Vector3(MathF.Cos(a) * rM * 1.04f, halfHeight * 0.18f + yOff * 0.5f, MathF.Sin(a) * rM * 1.04f);
                rTop[i] = center + new Vector3(MathF.Cos(a) * rM * 0.58f, halfHeight * 0.78f + yOff, MathF.Sin(a) * rM * 0.58f);
            }

            for (int i = 0; i < n; i++)
            {
                int next = (i + 1) % n;
                AddSolidTriangle(st, rBot[i], rMid[i], rMid[next], botCol, botCol, botCol);
                AddSolidTriangle(st, rBot[i], rMid[next], rBot[next], botCol, botCol, botCol);
                AddSolidTriangle(st, rMid[i], rTop[i], rTop[next], botCol, topCol, topCol);
                AddSolidTriangle(st, rMid[i], rTop[next], rMid[next], botCol, topCol, botCol);
                AddSolidTriangle(st, capCenter, rTop[next], rTop[i], mossyTop, topCol, topCol);
            }
        }
    }
}
