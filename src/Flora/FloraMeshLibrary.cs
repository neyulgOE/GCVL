using System;
using System.Collections.Generic;
using Godot;

namespace PrimevalWorld.Flora
{
    /// <summary>
    /// 9-Morphology Procedural Low-Poly Mesh Library + Optional GLB Asset Loader.
    /// Attempts to load res://assets/models/flora/<species_id>.glb first, falling back to
    /// crisp, low-poly multi-silhouette ArrayMeshes with vertex-encoded wind weights (COLOR.a).
    /// </summary>
    public sealed class FloraMeshLibrary
    {
        private readonly Dictionary<FloraSpeciesId, Mesh> _cache = new();

        public Mesh GetMesh(FloraNicheProfile profile)
        {
            if (_cache.TryGetValue(profile.Id, out Mesh? existing))
                return existing;

            string glbPath = $"res://assets/models/flora/{profile.SpeciesKey}.glb";
            if (ResourceLoader.Exists(glbPath))
            {
                var packed = GD.Load<PackedScene>(glbPath);
                if (packed != null)
                {
                    using Node inst = packed.Instantiate();
                    if (FindFirstMesh(inst) is Mesh glbMesh)
                    {
                        _cache[profile.Id] = glbMesh;
                        return glbMesh;
                    }
                }
            }

            Mesh built = BuildProceduralMesh(profile);
            _cache[profile.Id] = built;
            return built;
        }

        private static Mesh? FindFirstMesh(Node node)
        {
            if (node is MeshInstance3D mi && mi.Mesh != null)
                return mi.Mesh;
            foreach (Node child in node.GetChildren())
            {
                if (FindFirstMesh(child) is Mesh m)
                    return m;
            }
            return null;
        }

        private static ArrayMesh BuildProceduralMesh(FloraNicheProfile p)
        {
            float flex = Math.Clamp(1.0f - p.WindStiffness, 0.04f, 1.0f);
            return p.Id switch
            {
                FloraSpeciesId.PrimevalBanyanFig => CreateBanyanEmergentMesh(flex),
                FloraSpeciesId.GiantSequoiaReddawn => CreateGiantSequoiaMesh(flex),
                FloraSpeciesId.SacredAncientHardwood => CreateBroadleafDomeMesh(flex, 1.15f),
                FloraSpeciesId.BaobabPrehistoric => CreateBaobabMesh(flex),
                FloraSpeciesId.StarAppleCanopy => CreateBroadleafDomeMesh(flex, 0.92f),
                FloraSpeciesId.WeepingRiverWillow => CreateWillowCloudMesh(flex),
                FloraSpeciesId.GinkgoAncientGold or FloraSpeciesId.CrimsonSteppeMaple => CreateAutumnCloudMesh(flex),
                FloraSpeciesId.BorealSnowPine or FloraSpeciesId.SilverGlacierSpruce => CreateSnowSpruceMesh(flex),
                FloraSpeciesId.KrummholzDwarfPine => CreateKrummholzMesh(flex),
                FloraSpeciesId.DragonBloodTree or FloraSpeciesId.SavannaUmbrellaAcacia => CreateDesertUmbrellaMesh(flex),
                FloraSpeciesId.ArborescentTreeFern or FloraSpeciesId.CycadPrehistoric => CreateTreeFernMesh(flex),
                FloraSpeciesId.NipaWaterPalm => CreatePalmMesh(flex),
                FloraSpeciesId.GiantBambooVau => CreateBambooClumpMesh(flex),
                FloraSpeciesId.WildBerryBush => CreateBerryBushMesh(flex),
                FloraSpeciesId.PampasPlumeTallgrass => CreateTallgrassMesh(flex),
                FloraSpeciesId.RedDesertAgave => CreateAgaveMesh(flex),
                FloraSpeciesId.WetMossPatch or FloraSpeciesId.ArcticReindeerMoss => CreateMossPatchMesh(),
                FloraSpeciesId.BiolumForestMushroom => CreateMushroomClusterMesh(),
                FloraSpeciesId.HollowFallenTrunk => CreateFallenTrunkMesh(),
                FloraSpeciesId.StreamClayDeposit => CreateClayDepositMesh(),
                FloraSpeciesId.ExposedCopperOre => CreateCopperOreMesh(),
                _ => CreateBoulderMesh(),
            };
        }

        // 1A. Banyan Emergent with buttress roots & wide multi-cluster dome
        private static ArrayMesh CreateBanyanEmergentMesh(float flex)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var barkBot = new Color(0.22f, 0.16f, 0.11f, 0.0f);
            var barkTop = new Color(0.28f, 0.21f, 0.14f, 0.05f * flex);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 10.5f, 0.0f), 1.35f, 0.55f, 6, barkBot, barkTop);
            // 3 aerial prop roots
            for (int r = 0; r < 3; r++)
            {
                float a = r * Mathf.Tau / 3.0f;
                Vector3 basePos = new Vector3(MathF.Cos(a) * 2.2f, 0.0f, MathF.Sin(a) * 2.2f);
                Vector3 topPos = new Vector3(MathF.Cos(a) * 0.7f, 6.2f, MathF.Sin(a) * 0.7f);
                AddTaperedCylinder(st, basePos, topPos, 0.30f, 0.16f, 4, barkBot, barkTop);
            }
            Vector3[] centers =
            {
                new Vector3(0.0f, 14.5f, 0.0f),
                new Vector3(4.6f, 12.6f, 2.5f),
                new Vector3(-4.4f, 12.8f, 2.8f),
                new Vector3(2.4f, 12.2f, -4.5f),
                new Vector3(-3.2f, 12.5f, -3.6f),
            };
            float[] rads = { 6.6f, 5.2f, 5.0f, 4.9f, 4.7f };
            for (int i = 0; i < centers.Length; i++)
                AddFoliageCluster(st, centers[i], rads[i], 3.8f, 6, i * 0.5f,
                    new Color(0.45f, 0.52f, 0.42f, 0.22f * flex), new Color(0.95f, 1.0f, 0.90f, 0.42f * flex));
            st.GenerateNormals();
            return st.Commit();
        }

        // 1B. Broadleaf Dome (Sacred Hardwood / Star Apple)
        private static ArrayMesh CreateBroadleafDomeMesh(float flex, float scale)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var barkBot = new Color(0.22f, 0.16f, 0.11f, 0.0f);
            var barkTop = new Color(0.28f, 0.21f, 0.14f, 0.04f * flex);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 5.2f * scale, 0.0f), 0.55f * scale, 0.30f * scale, 5, barkBot, barkTop);
            Vector3[] centers =
            {
                new Vector3(0.0f, 8.0f * scale, 0.0f),
                new Vector3(3.0f * scale, 6.7f * scale, 1.6f * scale),
                new Vector3(-2.8f * scale, 6.9f * scale, 1.9f * scale),
                new Vector3(1.5f * scale, 6.5f * scale, -2.9f * scale),
                new Vector3(-2.1f * scale, 6.6f * scale, -2.2f * scale),
            };
            float[] rads = { 4.3f * scale, 3.3f * scale, 3.2f * scale, 3.1f * scale, 2.9f * scale };
            for (int i = 0; i < centers.Length; i++)
                AddFoliageCluster(st, centers[i], rads[i], 2.5f * scale, 6, i * 0.45f,
                    new Color(0.48f, 0.54f, 0.44f, 0.22f * flex), new Color(0.96f, 1.0f, 0.90f, 0.40f * flex));
            st.GenerateNormals();
            return st.Commit();
        }

        // 2. Giant Sequoia / Dawn Redwood Spire
        private static ArrayMesh CreateGiantSequoiaMesh(float flex)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 24.0f, 0.0f), 1.10f, 0.22f, 6,
                new Color(0.30f, 0.14f, 0.08f, 0.0f), new Color(0.36f, 0.18f, 0.11f, 0.08f * flex));
            float[] tierY = { 12.0f, 16.0f, 19.8f, 23.0f };
            float[] tierR = { 6.2f, 5.2f, 4.0f, 2.6f };
            for (int t = 0; t < tierY.Length; t++)
            {
                AddJaggedPlate(st, new Vector3(0.0f, tierY[t], 0.0f), tierR[t], 2.9f, 6, t * 0.58f,
                    new Color(0.42f, 0.50f, 0.40f, 0.15f * flex),
                    new Color(0.75f, 0.85f, 0.72f, 0.28f * flex),
                    new Color(0.96f, 1.0f, 0.92f, 0.36f * flex));
            }
            st.GenerateNormals();
            return st.Commit();
        }

        // 3A. Autumn Cloud-Crowned Deciduous (Ginkgo / Crimson Maple)
        private static ArrayMesh CreateAutumnCloudMesh(float flex)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 5.0f, 0.0f), 0.44f, 0.22f, 5,
                new Color(0.22f, 0.17f, 0.13f, 0.0f), new Color(0.28f, 0.22f, 0.17f, 0.05f * flex));
            Vector3[] clouds =
            {
                new Vector3(0.0f, 8.6f, 0.0f),
                new Vector3(2.4f, 7.2f, 1.3f),
                new Vector3(-2.3f, 7.4f, 1.5f),
                new Vector3(1.1f, 7.0f, -2.4f),
                new Vector3(-1.5f, 7.3f, -1.9f),
            };
            float[] rads = { 3.5f, 2.8f, 2.7f, 2.6f, 2.4f };
            for (int i = 0; i < clouds.Length; i++)
                AddFoliageCluster(st, clouds[i], rads[i], 2.2f, 6, i * 0.7f,
                    new Color(0.68f, 0.60f, 0.48f, 0.24f * flex), new Color(1.0f, 0.96f, 0.86f, 0.45f * flex));
            st.GenerateNormals();
            return st.Commit();
        }

        // 3B. Weeping River Willow
        private static ArrayMesh CreateWillowCloudMesh(float flex)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.2f, 5.2f, 0.0f), 0.50f, 0.25f, 5,
                new Color(0.21f, 0.16f, 0.11f, 0.0f), new Color(0.26f, 0.20f, 0.14f, 0.06f * flex));
            // Drooping tall curtain-like clusters
            Vector3[] drapes =
            {
                new Vector3(0.0f, 7.4f, 0.0f),
                new Vector3(2.6f, 5.8f, 1.4f),
                new Vector3(-2.5f, 5.9f, 1.6f),
                new Vector3(1.2f, 5.6f, -2.5f),
                new Vector3(-1.8f, 5.8f, -1.9f),
            };
            for (int i = 0; i < drapes.Length; i++)
                AddFoliageCluster(st, drapes[i], i == 0 ? 3.8f : 2.9f, 3.8f, 6, i * 0.6f,
                    new Color(0.55f, 0.64f, 0.48f, 0.35f * flex), new Color(0.95f, 1.0f, 0.88f, 0.65f * flex));
            st.GenerateNormals();
            return st.Commit();
        }

        // 4. Snow-Dusted Drooping Spruce Conifer (ONLY cold temps)
        private static ArrayMesh CreateSnowSpruceMesh(float flex)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 11.8f, 0.0f), 0.42f, 0.08f, 5,
                new Color(0.18f, 0.12f, 0.09f, 0.0f), new Color(0.22f, 0.15f, 0.11f, 0.06f * flex));
            float[] ys = { 3.2f, 5.4f, 7.6f, 9.6f, 11.4f };
            float[] rs = { 3.6f, 3.0f, 2.4f, 1.7f, 1.05f };
            for (int t = 0; t < ys.Length; t++)
            {
                Color snowRim = t >= 2 ? new Color(0.90f, 0.95f, 1.0f, 0.24f * flex) : new Color(0.75f, 0.86f, 0.82f, 0.20f * flex);
                AddJaggedPlate(st, new Vector3(0.0f, ys[t], 0.0f), rs[t], 2.5f, 6, t * 0.55f,
                    new Color(0.40f, 0.48f, 0.45f, 0.12f * flex),
                    new Color(0.68f, 0.78f, 0.74f, 0.22f * flex),
                    snowRim);
            }
            st.GenerateNormals();
            return st.Commit();
        }

        // 5. Krummholz Wind-Twisted Dwarf Pine
        private static ArrayMesh CreateKrummholzMesh(float flex)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var bark = new Color(0.22f, 0.15f, 0.11f, 0.0f);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(1.4f, 1.1f, 0.6f), 0.22f, 0.09f, 5, bark, bark);
            AddFoliageCluster(st, new Vector3(1.5f, 1.4f, 0.6f), 1.8f, 1.0f, 5, 0.2f,
                new Color(0.45f, 0.55f, 0.48f, 0.14f * flex), new Color(0.86f, 0.94f, 0.90f, 0.26f * flex));
            AddFoliageCluster(st, new Vector3(0.4f, 1.1f, -0.5f), 1.4f, 0.85f, 5, 1.1f,
                new Color(0.42f, 0.52f, 0.46f, 0.12f * flex), new Color(0.84f, 0.92f, 0.88f, 0.24f * flex));
            st.GenerateNormals();
            return st.Commit();
        }

        // 6A. Swollen Baobab
        private static ArrayMesh CreateBaobabMesh(float flex)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var bark = new Color(0.42f, 0.30f, 0.22f, 0.0f);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 8.2f, 0.0f), 1.65f, 1.15f, 7, bark, bark);
            for (int b = 0; b < 4; b++)
            {
                float a = b * Mathf.Tau / 4.0f + 0.3f;
                Vector3 tip = new Vector3(MathF.Cos(a) * 3.8f, 11.2f, MathF.Sin(a) * 3.8f);
                AddTaperedCylinder(st, new Vector3(0.0f, 7.6f, 0.0f), tip, 0.42f, 0.16f, 4, bark, bark);
                AddFoliageCluster(st, tip + new Vector3(0.0f, 0.6f, 0.0f), 3.4f, 1.1f, 6, b * 0.7f,
                    new Color(0.56f, 0.62f, 0.40f, 0.16f * flex), new Color(0.95f, 1.0f, 0.80f, 0.30f * flex));
            }
            st.GenerateNormals();
            return st.Commit();
        }

        // 6B. Flat-Topped Dragon Blood / Acacia Umbrella
        private static ArrayMesh CreateDesertUmbrellaMesh(float flex)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var bark = new Color(0.36f, 0.26f, 0.20f, 0.0f);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 5.2f, 0.0f), 0.72f, 0.40f, 6, bark, bark);
            for (int b = 0; b < 4; b++)
            {
                float a = b * Mathf.Tau / 4.0f;
                Vector3 tip = new Vector3(MathF.Cos(a) * 2.8f, 7.6f, MathF.Sin(a) * 2.8f);
                AddTaperedCylinder(st, new Vector3(0.0f, 4.8f, 0.0f), tip, 0.25f, 0.12f, 4, bark, bark);
            }
            AddFoliageCluster(st, new Vector3(0.0f, 8.0f, 0.0f), 5.6f, 1.15f, 7, 0.2f,
                new Color(0.52f, 0.58f, 0.42f, 0.18f * flex), new Color(0.95f, 1.0f, 0.82f, 0.34f * flex));
            st.GenerateNormals();
            return st.Commit();
        }

        // 7A. Tree Fern & Cycad Rosette
        private static ArrayMesh CreateTreeFernMesh(float flex)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 2.4f, 0.0f), 0.22f, 0.14f, 5,
                new Color(0.24f, 0.16f, 0.11f, 0.0f), new Color(0.26f, 0.18f, 0.12f, 0.10f * flex));
            for (int f = 0; f < 6; f++)
            {
                float ang = f * Mathf.Tau / 6.0f;
                Vector3 dir = new Vector3(MathF.Cos(ang), 0.0f, MathF.Sin(ang));
                Vector3 perp = new Vector3(-dir.Z, 0.0f, dir.X);
                Vector3 root = new Vector3(0.0f, 2.35f, 0.0f);
                Vector3 mid = root + dir * 1.15f + new Vector3(0.0f, 0.55f, 0.0f);
                Vector3 tip = root + dir * 2.25f + new Vector3(0.0f, -0.25f, 0.0f);
                var cRoot = new Color(0.52f, 0.65f, 0.46f, 0.18f * flex);
                var cMid = new Color(0.75f, 0.88f, 0.65f, 0.45f * flex);
                var cTip = new Color(0.95f, 1.0f, 0.86f, 0.72f * flex);
                AddTriangle(st, root, mid + perp * 0.36f, mid - perp * 0.36f, cRoot, cMid, cMid);
                AddTriangle(st, mid + perp * 0.36f, tip, mid - perp * 0.36f, cMid, cTip, cMid);
            }
            st.GenerateNormals();
            return st.Commit();
        }

        // 7B. Nipa / Oasis Water Palm
        private static ArrayMesh CreatePalmMesh(float flex)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.45f, 6.2f, 0.15f), 0.28f, 0.13f, 5,
                new Color(0.32f, 0.24f, 0.16f, 0.0f), new Color(0.36f, 0.27f, 0.18f, 0.15f * flex));
            Vector3 crown = new Vector3(0.45f, 6.1f, 0.15f);
            for (int f = 0; f < 6; f++)
            {
                float ang = f * Mathf.Tau / 6.0f;
                Vector3 dir = new Vector3(MathF.Cos(ang), 0.0f, MathF.Sin(ang));
                Vector3 perp = new Vector3(-dir.Z, 0.0f, dir.X);
                Vector3 mid = crown + dir * 1.65f + new Vector3(0.0f, 0.75f, 0.0f);
                Vector3 tip = crown + dir * 3.1f + new Vector3(0.0f, -0.45f, 0.0f);
                var cRoot = new Color(0.52f, 0.64f, 0.48f, 0.20f * flex);
                var cMid = new Color(0.78f, 0.90f, 0.72f, 0.48f * flex);
                var cTip = new Color(0.95f, 1.0f, 0.88f, 0.72f * flex);
                AddTriangle(st, crown, mid + perp * 0.42f, mid - perp * 0.42f, cRoot, cMid, cMid);
                AddTriangle(st, mid + perp * 0.42f, tip, mid - perp * 0.42f, cMid, cTip, cMid);
            }
            st.GenerateNormals();
            return st.Commit();
        }

        // 8A. Giant Bamboo Clump
        private static ArrayMesh CreateBambooClumpMesh(float flex)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var culmBot = new Color(0.55f, 0.70f, 0.42f, 0.0f);
            var culmTop = new Color(0.85f, 0.96f, 0.65f, 0.55f * flex);
            for (int i = 0; i < 4; i++)
            {
                float a = i * Mathf.Tau / 4.0f + 0.2f;
                Vector3 b = new Vector3(MathF.Cos(a) * 0.45f, 0.0f, MathF.Sin(a) * 0.45f);
                Vector3 t = new Vector3(MathF.Cos(a) * 0.95f, 5.5f + (i % 2) * 0.9f, MathF.Sin(a) * 0.95f);
                AddTaperedCylinder(st, b, t, 0.11f, 0.06f, 4, culmBot, culmTop);
                AddFoliageCluster(st, t, 1.15f, 0.75f, 4, i * 0.8f, culmBot, culmTop);
            }
            st.GenerateNormals();
            return st.Commit();
        }

        // 8B. Wild Berry Bush (supports 3-stage color tinting via MultiMesh InstanceColor!)
        private static ArrayMesh CreateBerryBushMesh(float flex)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            AddFoliageCluster(st, new Vector3(0.0f, 0.75f, 0.0f), 1.25f, 0.85f, 6, 0.1f,
                new Color(0.48f, 0.56f, 0.42f, 0.18f * flex), new Color(0.95f, 1.0f, 0.88f, 0.48f * flex));
            AddFoliageCluster(st, new Vector3(0.55f, 0.55f, 0.35f), 0.75f, 0.55f, 5, 0.9f,
                new Color(0.45f, 0.54f, 0.40f, 0.18f * flex), new Color(0.95f, 1.0f, 0.88f, 0.48f * flex));
            st.GenerateNormals();
            return st.Commit();
        }

        // 8C. Pampas Plume Tallgrass
        private static ArrayMesh CreateTallgrassMesh(float flex)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var bot = new Color(0.62f, 0.60f, 0.46f, 0.0f);
            var top = new Color(1.0f, 0.98f, 0.92f, 0.85f * flex);
            for (int b = 0; b < 5; b++)
            {
                float a = b * Mathf.Tau / 5.0f;
                Vector3 d = new Vector3(MathF.Cos(a), 0.0f, MathF.Sin(a));
                Vector3 p = new Vector3(-d.Z, 0.0f, d.X) * 0.18f;
                Vector3 root = d * 0.15f;
                Vector3 tip = d * 0.85f + new Vector3(0.0f, 1.85f, 0.0f);
                AddTriangle(st, root - p, root + p, tip, bot, bot, top);
            }
            st.GenerateNormals();
            return st.Commit();
        }

        // 8D. Red Desert Agave
        private static ArrayMesh CreateAgaveMesh(float flex)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var bot = new Color(0.55f, 0.62f, 0.45f, 0.0f);
            var top = new Color(0.95f, 1.0f, 0.85f, 0.28f * flex);
            for (int b = 0; b < 6; b++)
            {
                float a = b * Mathf.Tau / 6.0f;
                Vector3 d = new Vector3(MathF.Cos(a), 0.0f, MathF.Sin(a));
                Vector3 p = new Vector3(-d.Z, 0.0f, d.X) * 0.22f;
                Vector3 tip = d * 1.15f + new Vector3(0.0f, 1.15f, 0.0f);
                AddTriangle(st, -p, p, tip, bot, bot, top);
            }
            st.GenerateNormals();
            return st.Commit();
        }

        // 9A. Moss Patch
        private static ArrayMesh CreateMossPatchMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            AddFoliageCluster(st, new Vector3(0.0f, 0.12f, 0.0f), 1.15f, 0.24f, 6, 0.3f,
                new Color(0.55f, 0.65f, 0.50f, 0.0f), new Color(0.95f, 1.0f, 0.90f, 0.02f));
            st.GenerateNormals();
            return st.Commit();
        }

        // 9B. Forest Mushroom Cluster
        private static ArrayMesh CreateMushroomClusterMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var stem = new Color(0.85f, 0.82f, 0.72f, 0.0f);
            var cap = new Color(0.98f, 0.92f, 0.76f, 0.05f);
            for (int i = 0; i < 3; i++)
            {
                float a = i * Mathf.Tau / 3.0f;
                Vector3 off = new Vector3(MathF.Cos(a) * 0.22f, 0.0f, MathF.Sin(a) * 0.22f);
                float h = 0.32f + (i == 0 ? 0.18f : 0.0f);
                AddTaperedCylinder(st, off, off + new Vector3(0.0f, h, 0.0f), 0.06f, 0.04f, 4, stem, stem);
                AddJaggedPlate(st, off + new Vector3(0.0f, h, 0.0f), 0.22f, 0.16f, 5, i * 0.5f, cap, cap, cap);
            }
            st.GenerateNormals();
            return st.Commit();
        }

        // 9C. Hollow Fallen Trunk
        private static ArrayMesh CreateFallenTrunkMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var bark = new Color(0.68f, 0.60f, 0.50f, 0.0f);
            AddTaperedCylinder(st, new Vector3(-1.8f, 0.22f, 0.0f), new Vector3(1.8f, 0.28f, 0.15f), 0.36f, 0.26f, 6, bark, bark);
            st.GenerateNormals();
            return st.Commit();
        }

        // 9D. Stream Clay Deposit
        private static ArrayMesh CreateClayDepositMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            AddFoliageCluster(st, new Vector3(0.0f, 0.16f, 0.0f), 1.35f, 0.32f, 6, 0.4f,
                new Color(0.75f, 0.70f, 0.64f, 0.0f), new Color(0.95f, 0.90f, 0.85f, 0.0f));
            st.GenerateNormals();
            return st.Commit();
        }

        // 9E. Exposed Copper Ore
        private static ArrayMesh CreateCopperOreMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            AddFoliageCluster(st, new Vector3(0.0f, 0.48f, 0.0f), 1.05f, 0.95f, 5, 0.2f,
                new Color(0.45f, 0.55f, 0.50f, 0.0f), new Color(0.92f, 1.0f, 0.94f, 0.0f));
            st.GenerateNormals();
            return st.Commit();
        }

        // 9F. Boulder
        private static ArrayMesh CreateBoulderMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            AddFoliageCluster(st, new Vector3(0.0f, 0.45f, 0.0f), 1.25f, 0.85f, 5, 0.7f,
                new Color(0.58f, 0.58f, 0.58f, 0.0f), new Color(0.92f, 0.92f, 0.90f, 0.0f));
            st.GenerateNormals();
            return st.Commit();
        }

        // ===================== GEOMETRY HELPERS =====================
        private static void AddFoliageCluster(
            SurfaceTool st, Vector3 center, float radius, float halfHeight, int sides, float phase,
            Color bottomCol, Color topCol)
        {
            Vector3 apex = center + new Vector3(0.0f, halfHeight, 0.0f);
            Vector3 nadir = center - new Vector3(0.0f, halfHeight * 0.65f, 0.0f);
            Vector3[] ring = new Vector3[sides];
            for (int i = 0; i < sides; i++)
            {
                float a = i * Mathf.Tau / sides + phase;
                float rVar = radius * (0.86f + 0.22f * MathF.Sin(a * 3.0f + phase));
                ring[i] = center + new Vector3(MathF.Cos(a) * rVar, MathF.Sin(a * 2.0f) * halfHeight * 0.14f, MathF.Sin(a) * rVar);
            }
            Color midCol = bottomCol.Lerp(topCol, 0.55f);
            for (int i = 0; i < sides; i++)
            {
                int next = (i + 1) % sides;
                AddTriangle(st, apex, ring[next], ring[i], topCol, midCol, midCol);
                AddTriangle(st, nadir, ring[i], ring[next], bottomCol, midCol, midCol);
            }
        }

        private static void AddJaggedPlate(
            SurfaceTool st, Vector3 baseCenter, float radius, float height, int sides, float phase,
            Color botCol, Color midCol, Color topCol)
        {
            Vector3 apex = baseCenter + new Vector3(0.0f, height, 0.0f);
            Vector3 inner = baseCenter + new Vector3(0.0f, -0.35f, 0.0f);
            Vector3[] ring = new Vector3[sides];
            for (int i = 0; i < sides; i++)
            {
                float a = i * Mathf.Tau / sides + phase;
                float rVar = radius * (0.82f + 0.25f * MathF.Cos(i * 2.1f + phase));
                ring[i] = baseCenter + new Vector3(MathF.Cos(a) * rVar, -height * 0.20f, MathF.Sin(a) * rVar);
            }
            for (int i = 0; i < sides; i++)
            {
                int next = (i + 1) % sides;
                AddTriangle(st, apex, ring[next], ring[i], topCol, midCol, midCol);
                AddTriangle(st, inner, ring[i], ring[next], botCol, midCol, midCol);
            }
        }

        private static void AddTaperedCylinder(
            SurfaceTool st, Vector3 botCenter, Vector3 topCenter, float rBot, float rTop, int sides,
            Color cBot, Color cTop)
        {
            Vector3 axis = (topCenter - botCenter).Normalized();
            Vector3 refVec = MathF.Abs(axis.Y) < 0.9f ? Vector3.Up : Vector3.Right;
            Vector3 tangent = axis.Cross(refVec).Normalized();
            Vector3 bitangent = axis.Cross(tangent).Normalized();

            var ringBot = new Vector3[sides];
            var ringTop = new Vector3[sides];
            for (int i = 0; i < sides; i++)
            {
                float a = i * Mathf.Tau / sides;
                Vector3 dir = tangent * MathF.Cos(a) + bitangent * MathF.Sin(a);
                ringBot[i] = botCenter + dir * rBot;
                ringTop[i] = topCenter + dir * rTop;
            }
            for (int i = 0; i < sides; i++)
            {
                int next = (i + 1) % sides;
                AddTriangle(st, ringBot[i], ringBot[next], ringTop[next], cBot, cBot, cTop);
                AddTriangle(st, ringBot[i], ringTop[next], ringTop[i], cBot, cTop, cTop);
            }
        }

        private static void AddTriangle(SurfaceTool st, Vector3 a, Vector3 b, Vector3 c, Color ca, Color cb, Color cc)
        {
            st.SetColor(ca); st.AddVertex(a);
            st.SetColor(cb); st.AddVertex(b);
            st.SetColor(cc); st.AddVertex(c);
        }
    }
}
