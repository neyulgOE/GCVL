using System.Collections.Generic;
using Godot;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Terrain
{
    public partial class TerrainManager : Node3D
    {
        private readonly List<TerrainChunk> _chunks = new();
        private ShaderMaterial? _terrainMaterial;

        public void BuildTerrain(WorldGenerator generator)
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

            _terrainMaterial.SetShaderParameter("biome_splat_tex", generator.BuildBiomeSplatTexture());

            for (int cz = 0; cz < WorldGenerator.ChunksZ; cz++)
            {
                for (int cx = 0; cx < WorldGenerator.ChunksX; cx++)
                {
                    var chunk = new TerrainChunk { Name = $"Chunk_{cx}_{cz}" };
                    AddChild(chunk);
                    chunk.Build(generator, cx, cz, _terrainMaterial);
                    _chunks.Add(chunk);
                }
            }
        }
    }
}
