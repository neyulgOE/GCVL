using System.Collections.Generic;
using Godot;
using PrimevalWorld.Core;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Terrain
{
    /// <summary>
    /// Manages the 32x18 = 576 TerrainChunks (300m x 300m) with dynamic 4-level LOD switching.
    /// </summary>
    public partial class TerrainChunkManager : Node3D
    {
        private readonly List<TerrainChunk> _chunks = new(WorldPhysicsConfig.ChunksX * WorldPhysicsConfig.ChunksZ);
        private ShaderMaterial? _terrainMaterial;

        public int ChunkCount => _chunks.Count;
        public int ActiveTriangleEstimate { get; private set; }

        public void BuildTerrain(
            ErosionPhysics erosion,
            HydrologySolver hydrology,
            AtmosphereClimate climate,
            SoilPedology soil)
        {
            foreach (TerrainChunk chunk in _chunks)
                chunk.QueueFree();
            _chunks.Clear();

            if (_terrainMaterial == null)
            {
                var shader = GD.Load<Shader>("res://shaders/terrain_triplanar.gdshader");
                _terrainMaterial = new ShaderMaterial { Shader = shader };
            }

            var (soilA, soilB, climateTex) = soil.BuildGpuDataTextures(erosion, hydrology, climate);
            _terrainMaterial.SetShaderParameter("soil_tex_a", soilA);
            _terrainMaterial.SetShaderParameter("soil_tex_b", soilB);
            _terrainMaterial.SetShaderParameter("climate_tex", climateTex);

            for (int cz = 0; cz < WorldPhysicsConfig.ChunksZ; cz++)
            {
                for (int cx = 0; cx < WorldPhysicsConfig.ChunksX; cx++)
                {
                    var chunk = new TerrainChunk { Name = $"Chunk_{cx}_{cz}" };
                    AddChild(chunk);
                    chunk.Build(erosion, cx, cz, _terrainMaterial);
                    _chunks.Add(chunk);
                }
            }
        }

        public void SetCanopyCoverageTexture(ImageTexture canopyTex)
        {
            _terrainMaterial?.SetShaderParameter("canopy_coverage_tex", canopyTex);
        }

        public void UpdateLod(Vector3 cameraPos)
        {
            int tris = 0;
            for (int i = 0; i < _chunks.Count; i++)
            {
                TerrainChunk c = _chunks[i];
                float dx = cameraPos.X - c.CenterWorld.X;
                float dz = cameraPos.Z - c.CenterWorld.Z;
                float dy = (cameraPos.Y - c.CenterWorld.Y) * 0.25f;
                float dist = System.MathF.Sqrt(dx * dx + dz * dz + dy * dy);

                int lod = dist < WorldPhysicsConfig.Lod0Dist ? 0
                        : (dist < WorldPhysicsConfig.Lod1Dist ? 1
                        : (dist < WorldPhysicsConfig.Lod2Dist ? 2 : 3));

                if (c.IsCoastline && lod > 1)
                    lod = 1;

                c.SetLod(lod);
                tris += lod switch { 0 => 2048, 1 => 512, _ => 128 };
            }
            ActiveTriangleEstimate = tris;
        }
    }
}
