using System;
using System.Collections.Generic;
using Godot;

namespace PrimevalWorld.Flora
{
    /// <summary>
    /// Stage 3 Close-Up Overhaul: 14-Architecture Mesh Library with Crossed Alpha-Cutout Leaf Cards,
    /// Radial Sphere Normals (no flat PS1 polygon facets), Bark UV2 separation & GLB loader.
    /// UV2.x = 0.0 -> Bark/Solid (uses bark_tex), UV2.x = 1.0 -> Alpha-Cutout Leaf Card (uses leaf_atlas_tex).
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
            if (node is MeshInstance3D mi && mi.Mesh != null) return mi.Mesh;
            foreach (Node child in node.GetChildren())
                if (FindFirstMesh(child) is Mesh m) return m;
            return null;
        }

        private static ArrayMesh BuildProceduralMesh(FloraNicheProfile p)
        {
            if (p.Layer <= FloraLayer.Canopy || p.Id == FloraSpeciesId.ArborescentTreeFern || p.Id == FloraSpeciesId.NipaWaterPalm)
                return ProceduralTreeBuilder.BuildTree(p.Id, AgeStage.Mature, 2026);

            return p.Architecture switch
            {
                FloraArchitecture.ArchKrummholz => CreateKrummholzMesh(),
                FloraArchitecture.ArchWoodyShrub => CreateWoodyShrubMesh(),
                FloraArchitecture.ArchCaudexCycad => CreateCaudexCycadMesh(),
                FloraArchitecture.ArchBambooCulm => CreateBambooCulmMesh(),
                FloraArchitecture.ArchSoftTallHerb => CreateSoftTallHerbMesh(p.Id),
                _ => CreateSucculentAndGroundMesh(p.Id),
            };
        }

        // Atlas quadrant UV rects: 0=Broadleaf, 1=Conifer, 2=Acacia, 3=PalmFern
        private static Rect2 GetQuadUv(int quadrant) => quadrant switch
        {
            1 => new Rect2(0.52f, 0.02f, 0.46f, 0.46f),
            2 => new Rect2(0.02f, 0.52f, 0.46f, 0.46f),
            3 => new Rect2(0.52f, 0.52f, 0.46f, 0.46f),
            _ => new Rect2(0.02f, 0.02f, 0.46f, 0.46f),
        };

        // 1. ArchButtressBroadleaf (~25m, furrowed buttress trunk + 30 crossed leaf cards)
        private static ArrayMesh CreateButtressBroadleafMesh(bool withPropRoots)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var barkBot = new Color(0.28f, 0.21f, 0.14f, 0.0f);
            var barkTop = new Color(0.34f, 0.26f, 0.18f, 0.02f);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 12.0f, 0.0f), 1.35f, 0.52f, 7, barkBot, barkTop);

            for (int r = 0; r < 4; r++)
            {
                float a = r * Mathf.Tau / 4.0f + 0.2f;
                AddTaperedCylinder(st, new Vector3(MathF.Cos(a) * 2.6f, 0.0f, MathF.Sin(a) * 2.6f),
                    new Vector3(MathF.Cos(a) * 0.65f, 4.4f, MathF.Sin(a) * 0.65f), 0.38f, 0.18f, 4, barkBot, barkTop);
            }
            if (withPropRoots)
            {
                for (int r = 0; r < 3; r++)
                {
                    float a = r * Mathf.Tau / 3.0f + 0.8f;
                    AddTaperedCylinder(st, new Vector3(MathF.Cos(a) * 3.8f, 0.0f, MathF.Sin(a) * 3.8f),
                        new Vector3(MathF.Cos(a) * 3.1f, 11.4f, MathF.Sin(a) * 3.1f), 0.16f, 0.12f, 4, barkBot, barkTop);
                }
            }

            Vector3[] centers =
            {
                new Vector3(0.0f, 16.5f, 0.0f),
                new Vector3(5.6f, 14.0f, 2.8f),
                new Vector3(-5.4f, 14.2f, 3.1f),
                new Vector3(2.8f, 13.6f, -5.5f),
                new Vector3(-3.8f, 13.8f, -4.4f),
            };
            float[] rads = { 7.6f, 6.0f, 5.8f, 5.6f, 5.4f };
            for (int i = 0; i < centers.Length; i++)
            {
                AddTaperedCylinder(st, new Vector3(0.0f, 10.5f, 0.0f), centers[i], 0.34f, 0.16f, 4, barkBot, barkTop);
                AddLeafCardCluster(st, centers[i], rads[i], 4.2f, 6, 0, i * 0.7f, 0.14f);
            }
            return st.Commit();
        }

        // 2. ArchEmergentSequoia (~28m redwood spire + layered conifer needle cards)
        private static ArrayMesh CreateGiantSequoiaMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 27.5f, 0.0f), 1.15f, 0.22f, 7,
                new Color(0.38f, 0.18f, 0.10f, 0.0f), new Color(0.42f, 0.22f, 0.13f, 0.04f));
            float[] tierY = { 14.5f, 18.5f, 22.4f, 26.0f };
            float[] tierR = { 6.0f, 5.0f, 3.8f, 2.5f };
            for (int t = 0; t < tierY.Length; t++)
                AddLeafCardCluster(st, new Vector3(0.0f, tierY[t], 0.0f), tierR[t], 2.8f, 7, 1, t * 0.6f, 0.14f);
            return st.Commit();
        }

        // 3. ArchCanopyBroadleaf (~14m, forked branches + 24 crossed broadleaf cards)
        private static ArrayMesh CreateCanopyBroadleafMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var barkBot = new Color(0.30f, 0.22f, 0.15f, 0.0f);
            var barkTop = new Color(0.36f, 0.27f, 0.18f, 0.02f);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 6.2f, 0.0f), 0.52f, 0.28f, 6, barkBot, barkTop);
            Vector3[] clouds =
            {
                new Vector3(0.0f, 11.2f, 0.0f),
                new Vector3(2.8f, 9.6f, 1.5f),
                new Vector3(-2.6f, 9.8f, 1.7f),
                new Vector3(1.3f, 9.4f, -2.7f),
                new Vector3(-1.8f, 9.5f, -2.1f),
            };
            float[] rads = { 4.3f, 3.3f, 3.2f, 3.1f, 2.9f };
            for (int i = 0; i < clouds.Length; i++)
            {
                AddTaperedCylinder(st, new Vector3(0.0f, 5.5f, 0.0f), clouds[i], 0.22f, 0.10f, 4, barkBot, barkTop);
                AddLeafCardCluster(st, clouds[i], rads[i], 2.7f, 5, 0, i * 0.65f, 0.15f);
            }
            return st.Commit();
        }

        // 4. ArchWeepingTree (~12.5m, leaning trunk + drooping leaf card curtains)
        private static ArrayMesh CreateWeepingTreeMesh(bool whiteBirchBark)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var barkBot = whiteBirchBark ? new Color(0.80f, 0.79f, 0.76f, 0.0f) : new Color(0.28f, 0.21f, 0.14f, 0.0f);
            var barkTop = whiteBirchBark ? new Color(0.88f, 0.87f, 0.84f, 0.02f) : new Color(0.34f, 0.26f, 0.18f, 0.02f);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.75f, 6.8f, 0.25f), 0.46f, 0.22f, 6, barkBot, barkTop);
            Vector3[] drapes =
            {
                new Vector3(0.75f, 8.8f, 0.25f),
                new Vector3(3.2f, 6.8f, 1.4f),
                new Vector3(-1.8f, 6.9f, 1.6f),
                new Vector3(1.5f, 6.5f, -2.4f),
                new Vector3(-1.2f, 6.7f, -1.7f),
            };
            for (int i = 0; i < drapes.Length; i++)
                AddLeafCardCluster(st, drapes[i], i == 0 ? 3.8f : 2.9f, 3.8f, 5, 0, i * 0.6f, 0.17f);
            return st.Commit();
        }

        // 5. ArchAlpineConifer (~14m, trunk + 6 tiers of conifer needle cards)
        private static ArrayMesh CreateAlpineConiferMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 13.8f, 0.0f), 0.42f, 0.08f, 6,
                new Color(0.24f, 0.16f, 0.12f, 0.0f), new Color(0.28f, 0.20f, 0.15f, 0.02f));
            float[] ys = { 3.4f, 5.6f, 7.8f, 9.8f, 11.6f, 13.1f };
            float[] rs = { 3.8f, 3.2f, 2.6f, 2.0f, 1.4f, 0.85f };
            for (int t = 0; t < ys.Length; t++)
                AddLeafCardCluster(st, new Vector3(0.0f, ys[t], 0.0f), rs[t], 1.8f, 5, 1, t * 0.55f, 0.14f);
            return st.Commit();
        }

        // 6. ArchSwollenBaobab (~14m, bottle trunk + acacia/baobab leaflet cards)
        private static ArrayMesh CreateBaobabMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var bark = new Color(0.48f, 0.35f, 0.25f, 0.0f);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 4.5f, 0.0f), 1.45f, 1.85f, 7, bark, bark);
            AddTaperedCylinder(st, new Vector3(0.0f, 4.5f, 0.0f), new Vector3(0.0f, 9.6f, 0.0f), 1.85f, 1.15f, 7, bark, bark);
            for (int b = 0; b < 4; b++)
            {
                float a = b * Mathf.Tau / 4.0f + 0.3f;
                Vector3 tip = new Vector3(MathF.Cos(a) * 3.6f, 12.2f, MathF.Sin(a) * 3.6f);
                AddTaperedCylinder(st, new Vector3(0.0f, 9.0f, 0.0f), tip, 0.42f, 0.16f, 4, bark, bark);
                AddLeafCardCluster(st, tip + new Vector3(0.0f, 0.5f, 0.0f), 3.1f, 1.3f, 5, 2, b * 0.7f, 0.14f);
            }
            return st.Commit();
        }

        // 7. ArchUmbrellaDesert (~10.5m, Y-forked branches + flat umbrella leaflet cards)
        private static ArrayMesh CreateUmbrellaDesertMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var bark = new Color(0.40f, 0.29f, 0.22f, 0.0f);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 5.4f, 0.0f), 0.68f, 0.36f, 6, bark, bark);
            for (int b = 0; b < 4; b++)
            {
                float a = b * Mathf.Tau / 4.0f;
                Vector3 tip = new Vector3(MathF.Cos(a) * 3.2f, 8.6f, MathF.Sin(a) * 3.2f);
                AddTaperedCylinder(st, new Vector3(0.0f, 5.0f, 0.0f), tip, 0.24f, 0.11f, 4, bark, bark);
            }
            AddLeafCardCluster(st, new Vector3(0.0f, 9.1f, 0.0f), 6.2f, 1.4f, 9, 2, 0.2f, 0.15f);
            return st.Commit();
        }

        // 8. ArchKrummholz (~1.6m wind-twisted pine + conifer needle cards)
        private static ArrayMesh CreateKrummholzMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var bark = new Color(0.28f, 0.20f, 0.14f, 0.0f);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(1.1f, 0.75f, 0.35f), 0.18f, 0.09f, 5, bark, bark);
            AddTaperedCylinder(st, new Vector3(1.1f, 0.75f, 0.35f), new Vector3(2.0f, 1.25f, 0.55f), 0.10f, 0.05f, 4, bark, bark);
            AddLeafCardCluster(st, new Vector3(1.8f, 1.35f, 0.50f), 1.45f, 0.75f, 5, 1, 0.2f, 0.16f);
            AddLeafCardCluster(st, new Vector3(0.5f, 0.90f, -0.35f), 1.15f, 0.65f, 4, 1, 1.1f, 0.15f);
            return st.Commit();
        }

        // 9. ArchWoodyShrub (~1.4m woody stems + crossed broadleaf cards)
        private static ArrayMesh CreateWoodyShrubMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var stemCol = new Color(0.32f, 0.24f, 0.16f, 0.0f);
            for (int b = 0; b < 5; b++)
            {
                float a = b * Mathf.Tau / 5.0f;
                AddTaperedCylinder(st, Vector3.Zero, new Vector3(MathF.Cos(a) * 0.65f, 1.05f, MathF.Sin(a) * 0.65f), 0.06f, 0.03f, 4, stemCol, stemCol);
            }
            AddLeafCardCluster(st, new Vector3(0.0f, 0.85f, 0.0f), 1.25f, 0.80f, 6, 0, 0.1f, 0.18f);
            return st.Commit();
        }

        // 10. ArchColumnarPalmFern (ringed trunk + 9 arched pinnate frond cards)
        private static ArrayMesh CreateColumnarPalmFernMesh(bool isTreeFern)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            float h = isTreeFern ? 3.4f : 5.8f;
            float lean = isTreeFern ? 0.20f : 0.45f;
            Vector3 p0 = Vector3.Zero;
            Vector3 p1 = new Vector3(lean * 0.35f, h * 0.5f, lean * 0.1f);
            Vector3 p2 = new Vector3(lean, h, lean * 0.3f);
            AddTaperedCylinder(st, p0, p1, isTreeFern ? 0.22f : 0.26f, isTreeFern ? 0.17f : 0.20f, 5,
                new Color(0.34f, 0.26f, 0.18f, 0.0f), new Color(0.38f, 0.29f, 0.20f, 0.30f));
            AddTaperedCylinder(st, p1, p2, isTreeFern ? 0.17f : 0.20f, isTreeFern ? 0.12f : 0.14f, 5,
                new Color(0.38f, 0.29f, 0.20f, 0.30f), new Color(0.40f, 0.31f, 0.21f, 0.46f));

            int fronds = isTreeFern ? 8 : 9;
            float frondLen = isTreeFern ? 2.1f : 2.8f;
            Rect2 uvR = GetQuadUv(3);
            for (int f = 0; f < fronds; f++)
            {
                float ang = f * Mathf.Tau / fronds;
                Vector3 dir = new Vector3(MathF.Cos(ang), 0.0f, MathF.Sin(ang));
                Vector3 perp = new Vector3(-dir.Z, 0.0f, dir.X) * 0.65f;
                Vector3 mid = p2 + dir * (frondLen * 0.52f) + new Vector3(0.0f, 0.62f, 0.0f);
                Vector3 tip = p2 + dir * frondLen + new Vector3(0.0f, -0.45f, 0.0f);
                var cRoot = new Color(0.75f, 0.85f, 0.70f, 0.46f);
                var cTip = new Color(1.0f, 1.0f, 0.94f, 0.56f);
                AddLeafQuad(st, p2 - perp, p2 + perp, mid + perp, mid - perp, cRoot, cTip, Vector3.Up, uvR);
                AddLeafQuad(st, mid - perp, mid + perp, tip + perp * 0.6f, tip - perp * 0.6f, cTip, cTip, (dir + Vector3.Up).Normalized(), uvR);
            }
            return st.Commit();
        }

        // 11. ArchCaudexCycad (scaly caudex + 8 stiff pinnate frond cards)
        private static ArrayMesh CreateCaudexCycadMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 1.15f, 0.0f), 0.36f, 0.28f, 6,
                new Color(0.28f, 0.20f, 0.14f, 0.0f), new Color(0.32f, 0.24f, 0.17f, 0.10f));
            Vector3 crown = new Vector3(0.0f, 1.10f, 0.0f);
            Rect2 uvR = GetQuadUv(3);
            for (int f = 0; f < 8; f++)
            {
                float ang = f * Mathf.Tau / 8.0f;
                Vector3 dir = new Vector3(MathF.Cos(ang), 0.0f, MathF.Sin(ang));
                Vector3 perp = new Vector3(-dir.Z, 0.0f, dir.X) * 0.38f;
                Vector3 tip = crown + dir * 1.45f + new Vector3(0.0f, 0.72f, 0.0f);
                AddLeafQuad(st, crown - perp, crown + perp, tip + perp * 0.5f, tip - perp * 0.5f,
                    new Color(0.75f, 0.85f, 0.68f, 0.18f), new Color(0.98f, 1.0f, 0.90f, 0.36f), (dir + Vector3.Up).Normalized(), uvR);
            }
            return st.Commit();
        }

        // 12. ArchBambooCulm (8 hollow jointed culms + fine leaflet cards)
        private static ArrayMesh CreateBambooCulmMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var cBot = new Color(0.55f, 0.70f, 0.42f, 0.0f);
            var cMid = new Color(0.70f, 0.84f, 0.52f, 0.32f);
            var cTop = new Color(0.88f, 0.98f, 0.68f, 0.54f);
            for (int i = 0; i < 8; i++)
            {
                float a = i * Mathf.Tau / 8.0f + 0.15f;
                float r = 0.28f + (i % 2) * 0.22f;
                Vector3 b = new Vector3(MathF.Cos(a) * r, 0.0f, MathF.Sin(a) * r);
                Vector3 m = new Vector3(MathF.Cos(a) * (r + 0.18f), 3.1f, MathF.Sin(a) * (r + 0.18f));
                Vector3 t = new Vector3(MathF.Cos(a) * (r + 0.65f), 5.8f + (i % 3) * 0.55f, MathF.Sin(a) * (r + 0.65f));
                AddTaperedCylinder(st, b, m, 0.08f, 0.06f, 4, cBot, cMid);
                AddTaperedCylinder(st, m, t, 0.06f, 0.03f, 4, cMid, cTop);
                AddLeafCardCluster(st, t, 0.95f, 0.55f, 2, 2, i * 0.8f, 0.52f);
            }
            return st.Commit();
        }

        // 13. ArchSoftTallHerb (Traveling spatial wave > 0.60)
        private static ArrayMesh CreateSoftTallHerbMesh(FloraSpeciesId id)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            if (id == FloraSpeciesId.GiantElephantEar)
            {
                var stem = new Color(0.45f, 0.65f, 0.35f, 0.20f);
                var leafBase = new Color(0.75f, 0.90f, 0.68f, 0.68f);
                var leafTip = new Color(0.95f, 1.0f, 0.88f, 0.86f);
                for (int i = 0; i < 4; i++)
                {
                    float a = i * Mathf.Tau / 4.0f + 0.4f;
                    Vector3 d = new Vector3(MathF.Cos(a), 0.0f, MathF.Sin(a));
                    Vector3 p = new Vector3(-d.Z, 0.0f, d.X);
                    Vector3 top = d * 0.55f + new Vector3(0.0f, 1.05f, 0.0f);
                    AddTaperedCylinder(st, Vector3.Zero, top, 0.06f, 0.04f, 4, new Color(0.4f, 0.6f, 0.3f, 0.0f), stem);
                    AddSolidTriangle(st, top - p * 0.42f, top + p * 0.42f, top + d * 0.85f - new Vector3(0, 0.25f, 0), leafBase, leafBase, leafTip);
                }
            }
            else
            {
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
            }
            return st.Commit();
        }

        // 14. ArchSucculentAndGround
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
                AddLeafCardCluster(st, new Vector3(0.0f, 0.95f, 0.0f), 0.95f, 0.85f, 4, 0, 0.3f, 0.08f);
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
                    AddTaperedCylinder(st, off, off + new Vector3(0.0f, h, 0.0f), 0.05f, 0.03f, 4, stem, stem);
                    AddSolidConeCap(st, off + new Vector3(0.0f, h, 0.0f), 0.18f, 0.14f, 5, i * 0.5f, cap);
                }
            }
            else if (id == FloraSpeciesId.HollowFallenTrunk)
            {
                var bark = new Color(0.68f, 0.60f, 0.50f, 0.0f);
                AddTaperedCylinder(st, new Vector3(-1.5f, 0.20f, 0.0f), new Vector3(1.5f, 0.26f, 0.12f), 0.32f, 0.22f, 6, bark, bark);
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

        // ===================== ALPHA-CUTOUT LEAF CARD & RADIAL NORMAL BUILDERS =====================
        private static void AddLeafCardCluster(
            SurfaceTool st, Vector3 center, float radius, float halfHeight, int cardPairs, int atlasQuad, float phase, float windFlex)
        {
            Rect2 uvR = GetQuadUv(atlasQuad);
            var colBot = new Color(0.76f, 0.80f, 0.72f, windFlex * 0.7f);
            var colTop = new Color(1.0f, 1.0f, 0.95f, windFlex);

            for (int i = 0; i < cardPairs; i++)
            {
                float a = i * Mathf.Tau / cardPairs + phase;
                float rOff = i == 0 ? 0.0f : radius * 0.42f;
                Vector3 cPos = center + new Vector3(MathF.Cos(a) * rOff, ((i % 3) - 1) * halfHeight * 0.28f, MathF.Sin(a) * rOff);
                float cardW = radius * (i == 0 ? 1.15f : 0.82f);
                float cardH = halfHeight * (i == 0 ? 1.05f : 0.86f);

                // Radial sphere normal pointing outward from cluster center!
                Vector3 radialN = (cPos - center + new Vector3(0.0f, halfHeight * 0.35f, 0.0f)).Normalized();
                Vector3 right = new Vector3(MathF.Cos(a + 0.4f), 0.0f, MathF.Sin(a + 0.4f)) * cardW;
                Vector3 up = new Vector3(0.0f, cardH, 0.0f);

                // Crossed Card A
                AddLeafQuad(st, cPos - right - up, cPos + right - up, cPos + right + up, cPos - right + up, colBot, colTop, radialN, uvR);
                // Crossed Card B (rotated ~70 deg around Y + tilted)
                Vector3 rightB = new Vector3(-right.Z, right.Y + cardH * 0.25f, right.X);
                AddLeafQuad(st, cPos - rightB - up, cPos + rightB - up, cPos + rightB + up, cPos - rightB + up, colBot, colTop, radialN, uvR);
            }
        }

        private static void AddLeafQuad(
            SurfaceTool st, Vector3 p0, Vector3 p1, Vector3 p2, Vector3 p3,
            Color cBot, Color cTop, Vector3 radialNormal, Rect2 uvRect)
        {
            Vector2 uv0 = new Vector2(uvRect.Position.X, uvRect.End.Y);
            Vector2 uv1 = new Vector2(uvRect.End.X, uvRect.End.Y);
            Vector2 uv2 = new Vector2(uvRect.End.X, uvRect.Position.Y);
            Vector2 uv3 = new Vector2(uvRect.Position.X, uvRect.Position.Y);
            Vector2 leafTag = new Vector2(1.0f, 0.0f); // UV2.x = 1 -> Leaf Atlas + Alpha Scissor

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
            Vector2 barkTag = new Vector2(0.0f, 0.0f); // UV2.x = 0 -> Bark / Solid

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

        private static void AddSolidTriangle(SurfaceTool st, Vector3 a, Vector3 b, Vector3 c, Color ca, Color cb, Color cc)
        {
            Vector3 n = (b - a).Cross(c - a).Normalized();
            if (n.LengthSquared() < 0.001f) n = Vector3.Up;
            Vector2 solidTag = new Vector2(0.0f, 0.0f);
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
            Vector3 apex = center + new Vector3(0.0f, halfHeight, 0.0f);
            Vector3 nadir = center - new Vector3(0.0f, halfHeight * 0.5f, 0.0f);
            Vector3[] ring = new Vector3[sides];
            for (int i = 0; i < sides; i++)
            {
                float a = i * Mathf.Tau / sides + phase;
                float rVar = radius * (0.86f + 0.22f * MathF.Sin(a * 3.0f + phase));
                ring[i] = center + new Vector3(MathF.Cos(a) * rVar, 0.0f, MathF.Sin(a) * rVar);
            }
            for (int i = 0; i < sides; i++)
            {
                int next = (i + 1) % sides;
                AddSolidTriangle(st, apex, ring[next], ring[i], topCol, botCol, botCol);
                AddSolidTriangle(st, nadir, ring[i], ring[next], botCol, botCol, botCol);
            }
        }
    }
}
