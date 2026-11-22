using System.Collections.Generic;
using Godot;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Terrain
{
    public partial class TerrainManager : Node3D
    {
        private readonly List<TerrainChunk> _chunks = new();
        private ShaderMaterial? _terrainMaterial;

        public void BuildTerrain(WorldGenerator terrain, ClimateSimulator climate, SoilSimulator soil)
        {
            foreach (TerrainChunk chunk in _chunks)
            {
                chunk.QueueFree();
            }
            _chunks.Clear();

            if (_terrainMaterial == null)
            {
                var shader = GD.Load<Shader>("res://shaders/terrain_triplanar.gdshader");
                _terrainMaterial = new ShaderMaterial { Shader = shader };
            }

            _terrainMaterial.SetShaderParameter("soil_splat_tex", soil.BuildSoilSplatTexture());

            for (int cz = 0; cz < WorldGenerator.ChunksZ; cz++)
            {
                for (int cx = 0; cx < WorldGenerator.ChunksX; cx++)
                {
                    var chunk = new TerrainChunk { Name = $"Chunk_{cx}_{cz}" };
                    AddChild(chunk);
                    chunk.Build(terrain, climate, soil, cx, cz, _terrainMaterial);
                    _chunks.Add(chunk);
                }
            }
        }

        public void SetCanopyCoverageTexture(ImageTexture canopyTex)
        {
            _terrainMaterial?.SetShaderParameter("canopy_coverage_tex", canopyTex);
        }
    }
}
