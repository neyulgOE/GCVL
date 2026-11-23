using System;
using System.Collections.Generic;
using Godot;

namespace PrimevalWorld.Flora
{
    /// <summary>
    /// 14-Architecture Procedural Low-Poly Mesh Library across 4 StemGroups + Optional GLB Asset Loader.
    /// Encodes stem_flexibility into COLOR.a:
    ///   - 0.00..0.18: Woody Branching Trunks (rigid trunk, subtle leaf flutter)
    ///   - 0.25..0.55: Columnar / Caudex / Culm (parabolic arc bending along WindVector)
    ///   - 0.65..1.00: Soft Tall Herbs / Reeds / Grass (spatial traveling wave)
    ///   - 0.00..0.02: Succulents, Moss, Mushrooms & Geology (virtually static)
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
            return p.Architecture switch
            {
                FloraArchitecture.ArchButtressBroadleaf => CreateButtressBroadleafMesh(p.Id == FloraSpeciesId.PrimevalBanyanFig),
                FloraArchitecture.ArchEmergentSequoia => CreateGiantSequoiaMesh(),
                FloraArchitecture.ArchCanopyBroadleaf => CreateCanopyBroadleafMesh(),
                FloraArchitecture.ArchWeepingTree => CreateWeepingTreeMesh(p.Id == FloraSpeciesId.WeepingSilverBirch),
                FloraArchitecture.ArchAlpineConifer => CreateAlpineConiferMesh(),
                FloraArchitecture.ArchSwollenBaobab => CreateBaobabMesh(),
                FloraArchitecture.ArchUmbrellaDesert => CreateUmbrellaDesertMesh(),
                FloraArchitecture.ArchKrummholz => CreateKrummholzMesh(),
                FloraArchitecture.ArchWoodyShrub => CreateWoodyShrubMesh(),
                FloraArchitecture.ArchColumnarPalmFern => CreateColumnarPalmFernMesh(p.Id == FloraSpeciesId.ArborescentTreeFern),
                FloraArchitecture.ArchCaudexCycad => CreateCaudexCycadMesh(),
                FloraArchitecture.ArchBambooCulm => CreateBambooCulmMesh(),
                FloraArchitecture.ArchSoftTallHerb => CreateSoftTallHerbMesh(p.Id),
                _ => CreateSucculentAndGroundMesh(p.Id),
            };
        }

        // 1. ArchButtressBroadleaf (~25m base height, wide spreading crown > trunk height)
        private static ArrayMesh CreateButtressBroadleafMesh(bool withPropRoots)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var barkBot = new Color(0.22f, 0.16f, 0.11f, 0.0f);
            var barkTop = new Color(0.28f, 0.21f, 0.14f, 0.02f);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 11.5f, 0.0f), 1.35f, 0.52f, 6, barkBot, barkTop);

            // 4 wide buttress root flanges
            for (int r = 0; r < 4; r++)
            {
                float a = r * Mathf.Tau / 4.0f + 0.2f;
                Vector3 foot = new Vector3(MathF.Cos(a) * 2.6f, 0.0f, MathF.Sin(a) * 2.6f);
                Vector3 join = new Vector3(MathF.Cos(a) * 0.65f, 4.2f, MathF.Sin(a) * 0.65f);
                AddTaperedCylinder(st, foot, join, 0.38f, 0.18f, 4, barkBot, barkTop);
            }
            if (withPropRoots)
            {
                for (int r = 0; r < 3; r++)
                {
                    float a = r * Mathf.Tau / 3.0f + 0.8f;
                    AddTaperedCylinder(st, new Vector3(MathF.Cos(a) * 3.8f, 0.0f, MathF.Sin(a) * 3.8f),
                        new Vector3(MathF.Cos(a) * 3.2f, 11.2f, MathF.Sin(a) * 3.2f), 0.16f, 0.12f, 4, barkBot, barkTop);
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
            float[] rads = { 7.8f, 6.2f, 6.0f, 5.8f, 5.6f };
            for (int i = 0; i < centers.Length; i++)
                AddFoliageCluster(st, centers[i], rads[i], 3.8f, 6, i * 0.5f,
                    new Color(0.45f, 0.52f, 0.42f, 0.08f), new Color(0.95f, 1.0f, 0.90f, 0.17f));
            st.GenerateNormals();
            return st.Commit();
        }

        // 2. ArchEmergentSequoia (~28m base height, tall redwood spire)
        private static ArrayMesh CreateGiantSequoiaMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 27.5f, 0.0f), 1.15f, 0.22f, 6,
                new Color(0.32f, 0.14f, 0.08f, 0.0f), new Color(0.38f, 0.18f, 0.10f, 0.04f));
            float[] tierY = { 14.5f, 18.5f, 22.4f, 26.0f };
            float[] tierR = { 6.0f, 5.0f, 3.8f, 2.5f };
            for (int t = 0; t < tierY.Length; t++)
            {
                AddJaggedPlate(st, new Vector3(0.0f, tierY[t], 0.0f), tierR[t], 2.9f, 6, t * 0.58f,
                    new Color(0.42f, 0.50f, 0.40f, 0.06f),
                    new Color(0.75f, 0.85f, 0.72f, 0.12f),
                    new Color(0.96f, 1.0f, 0.92f, 0.17f));
            }
            st.GenerateNormals();
            return st.Commit();
        }

        // 3. ArchCanopyBroadleaf (~14m base height, forked branches + cloud crown)
        private static ArrayMesh CreateCanopyBroadleafMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var barkBot = new Color(0.24f, 0.18f, 0.12f, 0.0f);
            var barkTop = new Color(0.30f, 0.23f, 0.16f, 0.02f);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 6.2f, 0.0f), 0.52f, 0.28f, 5, barkBot, barkTop);
            // 3 forked primary limbs
            for (int b = 0; b < 3; b++)
            {
                float a = b * Mathf.Tau / 3.0f + 0.3f;
                AddTaperedCylinder(st, new Vector3(0.0f, 5.5f, 0.0f),
                    new Vector3(MathF.Cos(a) * 2.4f, 9.2f, MathF.Sin(a) * 2.4f), 0.22f, 0.11f, 4, barkBot, barkTop);
            }
            Vector3[] clouds =
            {
                new Vector3(0.0f, 11.2f, 0.0f),
                new Vector3(2.8f, 9.6f, 1.5f),
                new Vector3(-2.6f, 9.8f, 1.7f),
                new Vector3(1.3f, 9.4f, -2.7f),
                new Vector3(-1.8f, 9.5f, -2.1f),
            };
            float[] rads = { 4.2f, 3.2f, 3.1f, 3.0f, 2.8f };
            for (int i = 0; i < clouds.Length; i++)
                AddFoliageCluster(st, clouds[i], rads[i], 2.4f, 6, i * 0.65f,
                    new Color(0.62f, 0.58f, 0.48f, 0.08f), new Color(1.0f, 0.96f, 0.88f, 0.17f));
            st.GenerateNormals();
            return st.Commit();
        }

        // 4. ArchWeepingTree (~12.5m base height, leaning trunk + drooping leaf curtains)
        private static ArrayMesh CreateWeepingTreeMesh(bool whiteBirchBark)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var barkBot = whiteBirchBark ? new Color(0.76f, 0.75f, 0.72f, 0.0f) : new Color(0.22f, 0.16f, 0.11f, 0.0f);
            var barkTop = whiteBirchBark ? new Color(0.84f, 0.83f, 0.80f, 0.02f) : new Color(0.28f, 0.21f, 0.14f, 0.02f);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.75f, 6.8f, 0.25f), 0.46f, 0.22f, 5, barkBot, barkTop);
            Vector3[] drapes =
            {
                new Vector3(0.75f, 8.8f, 0.25f),
                new Vector3(3.2f, 6.8f, 1.4f),
                new Vector3(-1.8f, 6.9f, 1.6f),
                new Vector3(1.5f, 6.5f, -2.4f),
                new Vector3(-1.2f, 6.7f, -1.7f),
            };
            for (int i = 0; i < drapes.Length; i++)
                AddFoliageCluster(st, drapes[i], i == 0 ? 3.8f : 2.8f, 4.1f, 6, i * 0.6f,
                    new Color(0.55f, 0.64f, 0.48f, 0.12f), new Color(0.95f, 1.0f, 0.88f, 0.18f));
            st.GenerateNormals();
            return st.Commit();
        }

        // 5. ArchAlpineConifer (~14m base height, 6 snow-dusted drooping tiers)
        private static ArrayMesh CreateAlpineConiferMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 13.8f, 0.0f), 0.42f, 0.08f, 5,
                new Color(0.18f, 0.12f, 0.09f, 0.0f), new Color(0.22f, 0.15f, 0.11f, 0.02f));
            float[] ys = { 3.2f, 5.4f, 7.6f, 9.6f, 11.4f, 13.1f };
            float[] rs = { 3.8f, 3.2f, 2.6f, 2.0f, 1.4f, 0.85f };
            for (int t = 0; t < ys.Length; t++)
            {
                Color snowRim = t >= 3 ? new Color(0.90f, 0.95f, 1.0f, 0.14f) : new Color(0.75f, 0.86f, 0.82f, 0.11f);
                AddJaggedPlate(st, new Vector3(0.0f, ys[t], 0.0f), rs[t], 2.5f, 6, t * 0.55f,
                    new Color(0.40f, 0.48f, 0.45f, 0.06f), new Color(0.68f, 0.78f, 0.74f, 0.10f), snowRim);
            }
            st.GenerateNormals();
            return st.Commit();
        }

        // 6. ArchSwollenBaobab (~14m base height, bottle-shaped trunk)
        private static ArrayMesh CreateBaobabMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var bark = new Color(0.44f, 0.31f, 0.22f, 0.0f);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 4.5f, 0.0f), 1.45f, 1.85f, 7, bark, bark);
            AddTaperedCylinder(st, new Vector3(0.0f, 4.5f, 0.0f), new Vector3(0.0f, 9.6f, 0.0f), 1.85f, 1.15f, 7, bark, bark);
            for (int b = 0; b < 4; b++)
            {
                float a = b * Mathf.Tau / 4.0f + 0.3f;
                Vector3 tip = new Vector3(MathF.Cos(a) * 3.6f, 12.2f, MathF.Sin(a) * 3.6f);
                AddTaperedCylinder(st, new Vector3(0.0f, 9.0f, 0.0f), tip, 0.42f, 0.16f, 4, bark, bark);
                AddFoliageCluster(st, tip + new Vector3(0.0f, 0.5f, 0.0f), 3.1f, 1.0f, 6, b * 0.7f,
                    new Color(0.56f, 0.62f, 0.40f, 0.08f), new Color(0.95f, 1.0f, 0.80f, 0.15f));
            }
            st.GenerateNormals();
            return st.Commit();
        }

        // 7. ArchUmbrellaDesert (~10.5m base height, Y-forked branches + flat umbrella canopy)
        private static ArrayMesh CreateUmbrellaDesertMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var bark = new Color(0.36f, 0.26f, 0.20f, 0.0f);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 5.4f, 0.0f), 0.68f, 0.36f, 6, bark, bark);
            for (int b = 0; b < 4; b++)
            {
                float a = b * Mathf.Tau / 4.0f;
                Vector3 tip = new Vector3(MathF.Cos(a) * 3.2f, 8.6f, MathF.Sin(a) * 3.2f);
                AddTaperedCylinder(st, new Vector3(0.0f, 5.0f, 0.0f), tip, 0.24f, 0.11f, 4, bark, bark);
            }
            AddFoliageCluster(st, new Vector3(0.0f, 9.1f, 0.0f), 6.2f, 1.05f, 7, 0.2f,
                new Color(0.52f, 0.58f, 0.42f, 0.08f), new Color(0.95f, 1.0f, 0.82f, 0.16f));
            st.GenerateNormals();
            return st.Commit();
        }

        // 8. ArchKrummholz (~1.6m base height, wind-twisted creeping pine)
        private static ArrayMesh CreateKrummholzMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var bark = new Color(0.22f, 0.15f, 0.11f, 0.0f);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(1.1f, 0.75f, 0.35f), 0.18f, 0.09f, 5, bark, bark);
            AddTaperedCylinder(st, new Vector3(1.1f, 0.75f, 0.35f), new Vector3(2.0f, 1.25f, 0.55f), 0.10f, 0.05f, 4, bark, bark);
            AddFoliageCluster(st, new Vector3(1.8f, 1.35f, 0.50f), 1.45f, 0.70f, 5, 0.2f,
                new Color(0.45f, 0.55f, 0.48f, 0.10f), new Color(0.86f, 0.94f, 0.90f, 0.18f));
            AddFoliageCluster(st, new Vector3(0.5f, 0.90f, -0.35f), 1.15f, 0.60f, 5, 1.1f,
                new Color(0.42f, 0.52f, 0.46f, 0.08f), new Color(0.84f, 0.92f, 0.88f, 0.16f));
            st.GenerateNormals();
            return st.Commit();
        }

        // 9. ArchWoodyShrub (~1.4m base height, 6 woody stems + irregular shrub clusters)
        private static ArrayMesh CreateWoodyShrubMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            var stemCol = new Color(0.28f, 0.20f, 0.14f, 0.0f);
            for (int b = 0; b < 5; b++)
            {
                float a = b * Mathf.Tau / 5.0f;
                Vector3 tip = new Vector3(MathF.Cos(a) * 0.65f, 1.05f, MathF.Sin(a) * 0.65f);
                AddTaperedCylinder(st, Vector3.Zero, tip, 0.06f, 0.03f, 4, stemCol, stemCol);
            }
            AddFoliageCluster(st, new Vector3(0.0f, 0.90f, 0.0f), 1.15f, 0.68f, 6, 0.1f,
                new Color(0.48f, 0.56f, 0.42f, 0.10f), new Color(0.95f, 1.0f, 0.88f, 0.20f));
            AddFoliageCluster(st, new Vector3(0.45f, 0.68f, 0.30f), 0.72f, 0.48f, 5, 0.9f,
                new Color(0.45f, 0.54f, 0.40f, 0.10f), new Color(0.95f, 1.0f, 0.88f, 0.20f));
            st.GenerateNormals();
            return st.Commit();
        }

        // 10. ArchColumnarPalmFern (Columnar ringed trunk + 8-10 radiating arched fronds, parabolic bend 0.25..0.55)
        private static ArrayMesh CreateColumnarPalmFernMesh(bool isTreeFern)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            float h = isTreeFern ? 3.4f : 5.8f;
            float lean = isTreeFern ? 0.20f : 0.45f;
            // Segmented columnar trunk so parabolic wind curve bends smoothly!
            Vector3 p0 = Vector3.Zero;
            Vector3 p1 = new Vector3(lean * 0.35f, h * 0.5f, lean * 0.1f);
            Vector3 p2 = new Vector3(lean, h, lean * 0.3f);
            AddTaperedCylinder(st, p0, p1, isTreeFern ? 0.22f : 0.26f, isTreeFern ? 0.17f : 0.20f, 5,
                new Color(0.32f, 0.24f, 0.16f, 0.0f), new Color(0.35f, 0.26f, 0.18f, 0.30f));
            AddTaperedCylinder(st, p1, p2, isTreeFern ? 0.17f : 0.20f, isTreeFern ? 0.12f : 0.14f, 5,
                new Color(0.35f, 0.26f, 0.18f, 0.30f), new Color(0.38f, 0.28f, 0.19f, 0.46f));

            int fronds = isTreeFern ? 8 : 9;
            float frondLen = isTreeFern ? 2.1f : 2.8f;
            for (int f = 0; f < fronds; f++)
            {
                float ang = f * Mathf.Tau / fronds;
                Vector3 dir = new Vector3(MathF.Cos(ang), 0.0f, MathF.Sin(ang));
                Vector3 perp = new Vector3(-dir.Z, 0.0f, dir.X);
                Vector3 mid = p2 + dir * (frondLen * 0.52f) + new Vector3(0.0f, 0.65f, 0.0f);
                Vector3 tip = p2 + dir * frondLen + new Vector3(0.0f, -0.45f, 0.0f);
                var cRoot = new Color(0.52f, 0.64f, 0.48f, 0.46f);
                var cMid = new Color(0.78f, 0.90f, 0.72f, 0.52f);
                var cTip = new Color(0.95f, 1.0f, 0.88f, 0.56f);
                AddTriangle(st, p2, mid + perp * 0.34f, mid - perp * 0.34f, cRoot, cMid, cMid);
                AddTriangle(st, mid + perp * 0.34f, tip, mid - perp * 0.34f, cMid, cTip, cMid);
            }
            st.GenerateNormals();
            return st.Commit();
        }

        // 11. ArchCaudexCycad (Short thick scaly caudex + stiff funnel rosette)
        private static ArrayMesh CreateCaudexCycadMesh()
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            AddTaperedCylinder(st, Vector3.Zero, new Vector3(0.0f, 1.15f, 0.0f), 0.36f, 0.28f, 6,
                new Color(0.22f, 0.16f, 0.12f, 0.0f), new Color(0.26f, 0.19f, 0.14f, 0.10f));
            Vector3 crown = new Vector3(0.0f, 1.10f, 0.0f);
            for (int f = 0; f < 8; f++)
            {
                float ang = f * Mathf.Tau / 8.0f;
                Vector3 dir = new Vector3(MathF.Cos(ang), 0.0f, MathF.Sin(ang));
                Vector3 perp = new Vector3(-dir.Z, 0.0f, dir.X);
                Vector3 tip = crown + dir * 1.45f + new Vector3(0.0f, 0.72f, 0.0f);
                AddTriangle(st, crown, tip + perp * 0.24f, tip - perp * 0.24f,
                    new Color(0.55f, 0.65f, 0.45f, 0.18f), new Color(0.92f, 1.0f, 0.82f, 0.36f), new Color(0.92f, 1.0f, 0.82f, 0.36f));
            }
            st.GenerateNormals();
            return st.Commit();
        }

        // 12. ArchBambooCulm (8 tall hollow jointed culms + arching tops, parabolic bend 0.25..0.55)
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
                AddFoliageCluster(st, t, 0.85f, 0.45f, 4, i * 0.8f, cMid, cTop);
            }
            st.GenerateNormals();
            return st.Commit();
        }

        // 13. ArchSoftTallHerb (Traveling spatial wave > 0.60)
        private static ArrayMesh CreateSoftTallHerbMesh(FloraSpeciesId id)
        {
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);
            if (id == FloraSpeciesId.GiantElephantEar)
            {
                // Succulent petioles + 4 giant heart-shaped leaves
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
                    AddTriangle(st, top - p * 0.42f, top + p * 0.42f, top + d * 0.85f - new Vector3(0, 0.25f, 0), leafBase, leafBase, leafTip);
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
                    AddTriangle(st, root - p, root + p, tip, bot, bot, top);
                }
            }
            st.GenerateNormals();
            return st.Commit();
        }

        // 14. ArchSucculentAndGround (Virtually static: 0.0..0.02)
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
                    Vector3 tip = d * r + new Vector3(0.0f, h, 0.0f);
                    AddTriangle(st, -p, p, tip, bot, bot, top);
                }
            }
            else if (id == FloraSpeciesId.EpiphyteBaseVine)
            {
                // Climbing vine wrap hugging tree base
                var c = new Color(0.60f, 0.72f, 0.48f, 0.05f);
                for (int i = 0; i < 4; i++)
                {
                    float a = i * Mathf.Tau / 4.0f;
                    AddFoliageCluster(st, new Vector3(MathF.Cos(a) * 0.45f, 0.55f + i * 0.28f, MathF.Sin(a) * 0.45f),
                        0.45f, 0.32f, 4, i * 0.6f, c, new Color(0.90f, 1.0f, 0.82f, 0.10f));
                }
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
                    AddJaggedPlate(st, off + new Vector3(0.0f, h, 0.0f), 0.18f, 0.14f, 5, i * 0.5f, cap, cap, cap);
                }
            }
            else if (id == FloraSpeciesId.HollowFallenTrunk)
            {
                var bark = new Color(0.68f, 0.60f, 0.50f, 0.0f);
                AddTaperedCylinder(st, new Vector3(-1.5f, 0.20f, 0.0f), new Vector3(1.5f, 0.26f, 0.12f), 0.32f, 0.22f, 6, bark, bark);
            }
            else if (id == FloraSpeciesId.WetMossPatch || id == FloraSpeciesId.ArcticReindeerMoss || id == FloraSpeciesId.StreamClayDeposit)
            {
                AddFoliageCluster(st, new Vector3(0.0f, 0.12f, 0.0f), 1.05f, 0.22f, 6, 0.3f,
                    new Color(0.60f, 0.65f, 0.55f, 0.0f), new Color(0.95f, 1.0f, 0.90f, 0.0f));
            }
            else
            {
                // Copper Ore & Boulder
                AddFoliageCluster(st, new Vector3(0.0f, 0.42f, 0.0f), 1.05f, 0.80f, 5, 0.6f,
                    new Color(0.55f, 0.58f, 0.55f, 0.0f), new Color(0.92f, 0.96f, 0.92f, 0.0f));
            }

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
