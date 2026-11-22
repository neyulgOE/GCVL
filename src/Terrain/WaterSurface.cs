using System.Collections.Generic;
using Godot;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Terrain
{
    /// <summary>
    /// Builds:
    /// - 16km x 16km Horizon Ocean Plane at SeaLevel (0.0m)
    /// - Highland Source Lake surface at the mountain foothills (+17.5m)
    /// - Sloped River Ribbon & Tributary Ribbon meshes following river splines downhill to the bay
    /// </summary>
    public partial class WaterSurface : Node3D
    {
        private MeshInstance3D? _oceanMesh;
        private MeshInstance3D? _lakeMesh;
        private MeshInstance3D? _riverMesh;
        private MeshInstance3D? _tributaryMesh;
        private ShaderMaterial? _oceanMaterial;
        private ShaderMaterial? _riverMaterial;

        public void BuildWater(WorldGenerator generator)
        {
            if (_oceanMaterial == null)
            {
                var waterShader = GD.Load<Shader>("res://shaders/water_river_ocean.gdshader");
                _oceanMaterial = new ShaderMaterial { Shader = waterShader };
                _oceanMaterial.SetShaderParameter("flow_speed", new Vector2(0.025f, 0.018f));
                _oceanMaterial.SetShaderParameter("shallow_color", new Color(0.07f, 0.48f, 0.52f, 0.85f));
                _oceanMaterial.SetShaderParameter("deep_color", new Color(0.02f, 0.11f, 0.22f, 0.98f));

                _riverMaterial = new ShaderMaterial { Shader = waterShader };
                _riverMaterial.SetShaderParameter("flow_speed", new Vector2(0.0f, 0.28f));
                _riverMaterial.SetShaderParameter("shallow_color", new Color(0.09f, 0.45f, 0.48f, 0.84f));
                _riverMaterial.SetShaderParameter("deep_color", new Color(0.03f, 0.20f, 0.30f, 0.94f));
            }

            BuildHorizonOceanPlane();
            BuildSourceLake(generator);
            BuildSplineRibbon(ref _riverMesh, "MainRiverRibbon", generator.MainRiverNodes, _riverMaterial!);
            BuildSplineRibbon(ref _tributaryMesh, "TributaryRibbon", generator.TributaryNodes, _riverMaterial!);
        }

        private void BuildHorizonOceanPlane()
        {
            if (_oceanMesh == null)
            {
                _oceanMesh = new MeshInstance3D
                {
                    Name = "HorizonOceanPlane",
                    CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
                };
                AddChild(_oceanMesh);
            }

            var plane = new PlaneMesh
            {
                Size = new Vector2(16384.0f, 16384.0f),
                SubdivideWidth = 96,
                SubdivideDepth = 96,
            };
            _oceanMesh.Mesh = plane;
            _oceanMesh.MaterialOverride = _oceanMaterial;
            _oceanMesh.Position = new Vector3(
                WorldGenerator.RegionSizeMeters * 0.5f,
                WorldGenerator.SeaLevel,
                WorldGenerator.RegionSizeMeters * 0.5f
            );
        }

        private void BuildSourceLake(WorldGenerator generator)
        {
            _lakeMesh?.QueueFree();
            _lakeMesh = new MeshInstance3D
            {
                Name = "SourceLakeSurface",
                CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
            };
            AddChild(_lakeMesh);

            float radius = generator.SourceLakeRadius * 1.45f;
            var disc = new CylinderMesh
            {
                TopRadius = radius,
                BottomRadius = radius,
                Height = 0.08f,
                RadialSegments = 48,
                Rings = 4,
            };
            _lakeMesh.Mesh = disc;
            _lakeMesh.MaterialOverride = _riverMaterial;
            _lakeMesh.Position = generator.SourceLakeCenter;
        }

        private void BuildSplineRibbon(ref MeshInstance3D? target, string nodeName, List<RiverNode> nodes, Material material)
        {
            target?.QueueFree();
            target = new MeshInstance3D
            {
                Name = nodeName,
                CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
            };
            AddChild(target);

            if (nodes.Count < 2) return;

            const int xSteps = 7;
            var st = new SurfaceTool();
            st.Begin(Mesh.PrimitiveType.Triangles);

            float cumulativeDist = 0.0f;
            for (int i = 0; i < nodes.Count; i++)
            {
                RiverNode node = nodes[i];
                if (i > 0)
                {
                    cumulativeDist += (node.Position - nodes[i - 1].Position).Length();
                }

                // Right-hand perpendicular vector in XZ plane
                Vector2 perp = new Vector2(-node.Tangent.Y, node.Tangent.X);
                float ribbonHalfW = node.HalfWidth * 1.65f;
                float vCoord = cumulativeDist * 0.04f;

                for (int ix = 0; ix < xSteps; ix++)
                {
                    float u = ix / (float)(xSteps - 1);
                    float offset = (u - 0.5f) * 2.0f * ribbonHalfW;
                    Vector3 vert = new Vector3(
                        node.Position.X + perp.X * offset,
                        node.Position.Y,
                        node.Position.Z + perp.Y * offset
                    );
                    st.SetNormal(Vector3.Up);
                    st.SetUV(new Vector2(u, vCoord));
                    st.AddVertex(vert);
                }
            }

            for (int i = 0; i < nodes.Count - 1; i++)
            {
                for (int ix = 0; ix < xSteps - 1; ix++)
                {
                    int i0 = i * xSteps + ix;
                    int i1 = i0 + 1;
                    int i2 = i0 + xSteps;
                    int i3 = i2 + 1;

                    st.AddIndex(i0);
                    st.AddIndex(i1);
                    st.AddIndex(i2);

                    st.AddIndex(i1);
                    st.AddIndex(i3);
                    st.AddIndex(i2);
                }
            }

            target.Mesh = st.Commit();
            target.MaterialOverride = material;
        }
    }
}
