using System.Collections.Generic;
using Godot;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Terrain
{
    /// <summary>
    /// Manages the 8x8 grid of 128m TerrainChunks covering the 1x1 km vertical slice.
    /// </summary>
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

            int count = WorldGenerator.ChunksPerAxis;
            for (int cz = 0; cz < count; cz++)
            {
                for (int cx = 0; cx < count; cx++)
                {
                    var chunk = new TerrainChunk
                    {
                        Name = $"Chunk_{cx}_{cz}"
                    };
                    AddChild(chunk);
                    chunk.Build(generator, cx, cz, _terrainMaterial);
                    _chunks.Add(chunk);
                }
            }
        }
    }
}
