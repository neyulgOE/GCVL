using System.Collections.Generic;
using Godot;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Terrain
{
    /// <summary>
    /// Builds the 16km x 16km Horizon Ocean Plane plus the 3 curvy sloped river ribbons
    /// (Eastern Main River, Curvy Tributary, and NW Glacial Meltwater River)
    /// and the SW Desert Turquoise Oasis water disc.
    /// </summary>
    public partial class WaterSurface : Node3D
    {
        private MeshInstance3D? _oceanMesh;
        private MeshInstance3D? _oasisMesh;
        private MeshInstance3D? _mainRiverMesh;
        private MeshInstance3D? _tributaryMesh;
        private MeshInstance3D? _nwRiverMesh;
        private ShaderMaterial? _oceanMaterial;
        private ShaderMaterial? _riverMaterial;

        public void BuildWater(WorldGenerator generator)
        {
            if (_oceanMaterial == null)
            {
                var waterShader = GD.Load<Shader>("res://shaders/water_river_ocean.gdshader");
                _oceanMaterial = new ShaderMaterial { Shader = waterShader };
                _oceanMaterial.SetShaderParameter("flow_speed", new Vector2(0.02f, 0.015f));
                _oceanMaterial.SetShaderParameter("shallow_color", new Color(0.10f, 0.68f, 0.72f, 0.78f));
                _oceanMaterial.SetShaderParameter("deep_color", new Color(0.03f, 0.16f, 0.30f, 0.96f));

                _riverMaterial = new ShaderMaterial { Shader = waterShader };
                _riverMaterial.SetShaderParameter("flow_speed", new Vector2(0.0f, 0.28f));
                _riverMaterial.SetShaderParameter("shallow_color", new Color(0.14f, 0.66f, 0.68f, 0.72f));
                _riverMaterial.SetShaderParameter("deep_color", new Color(0.06f, 0.34f, 0.48f, 0.88f));
            }

            BuildHorizonOceanPlane();
            BuildOasisWater(generator);
            BuildSplineRibbon(ref _mainRiverMesh, "MainRiverRibbon", generator.MainRiverNodes, _riverMaterial!);
            BuildSplineRibbon(ref _tributaryMesh, "TributaryRibbon", generator.TributaryNodes, _riverMaterial!);
            BuildSplineRibbon(ref _nwRiverMesh, "NwRiverRibbon", generator.NwRiverNodes, _riverMaterial!);
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

        private void BuildOasisWater(WorldGenerator generator)
        {
            _oasisMesh?.QueueFree();
            _oasisMesh = new MeshInstance3D
            {
                Name = "DesertOasisWater",
                CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
            };
            AddChild(_oasisMesh);

            var disc = new CylinderMesh
            {
                TopRadius = 62.0f,
                BottomRadius = 62.0f,
                Height = 0.08f,
                RadialSegments = 36,
                Rings = 2,
            };
            _oasisMesh.Mesh = disc;
            _oasisMesh.MaterialOverride = _riverMaterial;
            _oasisMesh.Position = new Vector3(generator.OasisCenter.X, 0.25f, generator.OasisCenter.Y);
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

                Vector2 perp = new Vector2(-node.Tangent.Y, node.Tangent.X);
                float ribbonHalfW = node.HalfWidth * 1.55f;
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
