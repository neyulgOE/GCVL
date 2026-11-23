using System;
using Godot;
using PrimevalWorld.WorldGen;

namespace PrimevalWorld.Flora
{
    public enum FloraLayer : byte
    {
        Emergent = 1,
        Canopy = 2,
        Understory = 3,
        Shrub = 4,
        HerbGround = 5,
        LitterSoil = 6,
    }

    public enum FloraMorphology : byte
    {
        BroadleafEmergentDome = 0,     // 1. Multi-cluster wide canopy (Banyan, Sacred Hardwood, Star Apple)
        SequoiaRedwoodSpire = 1,       // 2. Tall emergent redwood spire
        DeciduousCloudCrown = 2,       // 3. Cloud-crowned deciduous (Gold Ginkgo, Crimson Maple)
        SnowSpruceConifer = 3,         // 4. Drooping snow-dusted conifer tiers
        KrummholzDwarfPine = 4,        // 5. Wind-twisted low treeline pine
        PrehistoricDesertUmbrella = 5, // 6. Swollen baobab / flat umbrella dragon-blood & acacia
        PalmAndTreeFernRosette = 6,    // 7. Radiating fronds (Nipa/Oasis Palm, Tree Fern, Cycad)
        BambooShrubAgaveCluster = 7,   // 8. Bamboo culms / 3-stage Berry Bush / Pampas Grass / Red Agave
        GroundLitterGeology = 8,       // 9. Moss, Mushroom, Fallen Trunk, Clay, Copper Ore, Boulder
    }

    public enum FloraSpeciesId : byte
    {
        // Layer 1: Emergent (4)
        PrimevalBanyanFig = 0,
        GiantSequoiaReddawn = 1,
        SacredAncientHardwood = 2,
        BaobabPrehistoric = 3,

        // Layer 2: Canopy (8)
        StarAppleCanopy = 4,
        WeepingRiverWillow = 5,
        GinkgoAncientGold = 6,
        CrimsonSteppeMaple = 7,
        BorealSnowPine = 8,
        SilverGlacierSpruce = 9,
        DragonBloodTree = 10,
        SavannaUmbrellaAcacia = 11,

        // Layer 3: Understory (5)
        ArborescentTreeFern = 12,
        CycadPrehistoric = 13,
        GiantBambooVau = 14,
        NipaWaterPalm = 15,
        KrummholzDwarfPine = 16,

        // Layer 4: Shrub (3)
        WildBerryBush = 17,
        PampasPlumeTallgrass = 18,
        RedDesertAgave = 19,

        // Layer 5: Herb / Ground (3)
        WetMossPatch = 20,
        BiolumForestMushroom = 21,
        ArcticReindeerMoss = 22,

        // Layer 6: Litter / Soil / Geology (4)
        HollowFallenTrunk = 23,
        StreamClayDeposit = 24,
        ExposedCopperOre = 25,
        Boulder = 26,
    }

    /// <summary>
    /// Physical ecological niche profile for a prehistoric flora species.
    /// Zero hardcoded biome checks: suitability emerges continuously from Climate, Soil, Slope, Groundwater & Light.
    /// </summary>
    public sealed class FloraNicheProfile
    {
        public FloraSpeciesId Id { get; init; }
        public string SpeciesKey { get; init; } = "";
        public string DisplayName { get; init; } = "";
        public FloraLayer Layer { get; init; }
        public FloraMorphology Morphology { get; init; }

        public float IdealTempC { get; init; }
        public float TempToleranceC { get; init; }
        public float IdealMoisture { get; init; }
        public float MoistureTolerance { get; init; }
        public float MinGroundwater { get; init; }
        public float MaxWindSpeedMs { get; init; }
        public float MaxSlopeDeg { get; init; }
        public float MinSoilDepth { get; init; }
        public float SalinityTolerance { get; init; }

        // Affinity weights for [AlluvialLoam, ForestBrownSoil, SteppeLoess, AridRedSand, CoastalSand, PermafrostAndRock]
        public float[] SoilAffinity { get; init; } = new float[6];

        public float LightMin { get; init; }
        public float LightMax { get; init; }
        public float CrownRadiusM { get; init; }
        public float HeightMinM { get; init; }
        public float HeightMaxM { get; init; }
        public float WindStiffness { get; init; } // 1.0 = rigid trunk, 0.1 = flexible grass/fern

        public Color BaseTint { get; init; }
        public Color MapColor { get; init; }

        public float EvaluateSuitability(
            in ClimateSample climate,
            in SoilSample soil,
            float slopeDeg,
            float groundwater,
            float groundLight)
        {
            if (slopeDeg > MaxSlopeDeg || soil.SoilDepth < MinSoilDepth || climate.WindSpeed > MaxWindSpeedMs)
                return 0.0f;
            if (groundwater < MinGroundwater)
                return 0.0f;
            if (groundLight < LightMin || groundLight > LightMax)
                return 0.0f;

            float tDiff = (climate.TemperatureC - IdealTempC) / MathF.Max(0.5f, TempToleranceC);
            float tScore = MathF.Exp(-tDiff * tDiff * 1.45f);
            if (tScore < 0.04f) return 0.0f;

            float mDiff = (climate.Moisture - IdealMoisture) / MathF.Max(0.05f, MoistureTolerance);
            float mScore = MathF.Exp(-mDiff * mDiff * 1.35f);
            if (mScore < 0.04f) return 0.0f;

            float salPenalty = soil.CoastalSalinity > SalinityTolerance
                ? MathF.Max(0.0f, 1.0f - (soil.CoastalSalinity - SalinityTolerance) * 2.6f)
                : 1.0f;
            if (salPenalty <= 0.02f) return 0.0f;

            float windScore = 1.0f - FastNoise.SmoothStep(MaxWindSpeedMs * 0.65f, MaxWindSpeedMs, climate.WindSpeed) * 0.45f;
            float slopeScore = 1.0f - FastNoise.SmoothStep(MaxSlopeDeg * 0.65f, MaxSlopeDeg, slopeDeg) * 0.35f;
            float depthScore = FastNoise.SmoothStep(MinSoilDepth * 0.8f, MinSoilDepth + 0.25f, soil.SoilDepth);

            float soilScore =
                soil.WAlluvial * SoilAffinity[0] +
                soil.WForestBrown * SoilAffinity[1] +
                soil.WSteppeLoess * SoilAffinity[2] +
                soil.WAridRed * SoilAffinity[3] +
                soil.WCoastalSand * SoilAffinity[4] +
                soil.WPermafrostRock * SoilAffinity[5];

            if (soilScore <= 0.03f) return 0.0f;

            return tScore * mScore * windScore * slopeScore * depthScore * soilScore * salPenalty;
        }
    }

    public static class FloraNicheDatabase
    {
        public static readonly FloraNicheProfile[] AllSpecies =
        {
            // ===================== LAYER 1: EMERGENT (4) =====================
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.PrimevalBanyanFig, SpeciesKey = "primeval_banyan_fig", DisplayName = "Đa Cổ Thụ Nghìn Năm",
                Layer = FloraLayer.Emergent, Morphology = FloraMorphology.BroadleafEmergentDome,
                IdealTempC = 23.0f, TempToleranceC = 7.0f, IdealMoisture = 0.72f, MoistureTolerance = 0.28f,
                MinGroundwater = 0.08f, MaxWindSpeedMs = 17.5f, MaxSlopeDeg = 22.0f, MinSoilDepth = 0.35f, SalinityTolerance = 0.25f,
                SoilAffinity = new[] { 1.0f, 0.90f, 0.15f, 0.02f, 0.08f, 0.01f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 11.5f, HeightMinM = 18.0f, HeightMaxM = 25.0f, WindStiffness = 0.88f,
                BaseTint = new Color(0.14f, 0.31f, 0.11f), MapColor = new Color(0.06f, 0.26f, 0.08f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.GiantSequoiaReddawn, SpeciesKey = "giant_sequoia_reddawn", DisplayName = "Tùng Hồng Thủy Sam",
                Layer = FloraLayer.Emergent, Morphology = FloraMorphology.SequoiaRedwoodSpire,
                IdealTempC = 14.5f, TempToleranceC = 6.5f, IdealMoisture = 0.65f, MoistureTolerance = 0.28f,
                MinGroundwater = 0.05f, MaxWindSpeedMs = 19.0f, MaxSlopeDeg = 26.0f, MinSoilDepth = 0.30f, SalinityTolerance = 0.18f,
                SoilAffinity = new[] { 0.80f, 1.0f, 0.35f, 0.02f, 0.05f, 0.08f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 8.5f, HeightMinM = 24.0f, HeightMaxM = 34.0f, WindStiffness = 0.90f,
                BaseTint = new Color(0.11f, 0.26f, 0.11f), MapColor = new Color(0.07f, 0.24f, 0.11f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.SacredAncientHardwood, SpeciesKey = "sacred_ancient_hardwood", DisplayName = "Đại Thụ Thánh Địa",
                Layer = FloraLayer.Emergent, Morphology = FloraMorphology.BroadleafEmergentDome,
                IdealTempC = 21.0f, TempToleranceC = 7.5f, IdealMoisture = 0.64f, MoistureTolerance = 0.30f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 18.0f, MaxSlopeDeg = 24.0f, MinSoilDepth = 0.30f, SalinityTolerance = 0.30f,
                SoilAffinity = new[] { 0.88f, 1.0f, 0.25f, 0.03f, 0.12f, 0.02f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 10.5f, HeightMinM = 17.0f, HeightMaxM = 23.0f, WindStiffness = 0.86f,
                BaseTint = new Color(0.16f, 0.34f, 0.12f), MapColor = new Color(0.09f, 0.30f, 0.10f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.BaobabPrehistoric, SpeciesKey = "baobab_prehistoric", DisplayName = "Bao Báp Cổ Sinh",
                Layer = FloraLayer.Emergent, Morphology = FloraMorphology.PrehistoricDesertUmbrella,
                IdealTempC = 29.0f, TempToleranceC = 7.5f, IdealMoisture = 0.24f, MoistureTolerance = 0.20f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 22.0f, MaxSlopeDeg = 20.0f, MinSoilDepth = 0.14f, SalinityTolerance = 0.35f,
                SoilAffinity = new[] { 0.15f, 0.20f, 0.45f, 1.0f, 0.30f, 0.08f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 10.0f, HeightMinM = 13.0f, HeightMaxM = 19.0f, WindStiffness = 0.92f,
                BaseTint = new Color(0.30f, 0.35f, 0.14f), MapColor = new Color(0.46f, 0.44f, 0.18f)
            },

            // ===================== LAYER 2: CANOPY (8) =====================
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.StarAppleCanopy, SpeciesKey = "star_apple_canopy", DisplayName = "Vú Sữa Cổ Đại",
                Layer = FloraLayer.Canopy, Morphology = FloraMorphology.BroadleafEmergentDome,
                IdealTempC = 20.5f, TempToleranceC = 8.0f, IdealMoisture = 0.58f, MoistureTolerance = 0.30f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 18.5f, MaxSlopeDeg = 26.0f, MinSoilDepth = 0.22f, SalinityTolerance = 0.28f,
                SoilAffinity = new[] { 0.88f, 1.0f, 0.32f, 0.04f, 0.12f, 0.03f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 7.2f, HeightMinM = 10.5f, HeightMaxM = 15.5f, WindStiffness = 0.78f,
                BaseTint = new Color(0.18f, 0.37f, 0.13f), MapColor = new Color(0.12f, 0.38f, 0.12f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.WeepingRiverWillow, SpeciesKey = "weeping_river_willow", DisplayName = "Liễu Rủ Ven Sông",
                Layer = FloraLayer.Canopy, Morphology = FloraMorphology.DeciduousCloudCrown,
                IdealTempC = 17.0f, TempToleranceC = 9.0f, IdealMoisture = 0.72f, MoistureTolerance = 0.28f,
                MinGroundwater = 0.28f, MaxWindSpeedMs = 19.0f, MaxSlopeDeg = 22.0f, MinSoilDepth = 0.18f, SalinityTolerance = 0.35f,
                SoilAffinity = new[] { 1.0f, 0.75f, 0.35f, 0.15f, 0.25f, 0.05f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 6.8f, HeightMinM = 9.0f, HeightMaxM = 14.0f, WindStiffness = 0.65f,
                BaseTint = new Color(0.24f, 0.44f, 0.16f), MapColor = new Color(0.18f, 0.48f, 0.22f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.GinkgoAncientGold, SpeciesKey = "ginkgo_ancient_gold", DisplayName = "Bạch Quả Cổ Sinh Lá Vàng",
                Layer = FloraLayer.Canopy, Morphology = FloraMorphology.DeciduousCloudCrown,
                IdealTempC = 11.0f, TempToleranceC = 6.2f, IdealMoisture = 0.42f, MoistureTolerance = 0.25f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 20.0f, MaxSlopeDeg = 28.0f, MinSoilDepth = 0.18f, SalinityTolerance = 0.20f,
                SoilAffinity = new[] { 0.45f, 0.78f, 1.0f, 0.06f, 0.05f, 0.10f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 6.6f, HeightMinM = 10.0f, HeightMaxM = 15.0f, WindStiffness = 0.74f,
                BaseTint = new Color(0.84f, 0.64f, 0.14f), MapColor = new Color(0.88f, 0.68f, 0.16f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.CrimsonSteppeMaple, SpeciesKey = "crimson_steppe_maple", DisplayName = "Phong Cổ Thụ Lá Đỏ Cam",
                Layer = FloraLayer.Canopy, Morphology = FloraMorphology.DeciduousCloudCrown,
                IdealTempC = 12.0f, TempToleranceC = 5.8f, IdealMoisture = 0.38f, MoistureTolerance = 0.24f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 20.5f, MaxSlopeDeg = 28.0f, MinSoilDepth = 0.16f, SalinityTolerance = 0.18f,
                SoilAffinity = new[] { 0.35f, 0.72f, 1.0f, 0.08f, 0.05f, 0.12f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 6.2f, HeightMinM = 9.0f, HeightMaxM = 13.5f, WindStiffness = 0.72f,
                BaseTint = new Color(0.80f, 0.30f, 0.11f), MapColor = new Color(0.82f, 0.32f, 0.12f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.BorealSnowPine, SpeciesKey = "boreal_snow_pine", DisplayName = "Thông Tuyết Phương Bắc",
                Layer = FloraLayer.Canopy, Morphology = FloraMorphology.SnowSpruceConifer,
                IdealTempC = 1.5f, TempToleranceC = 6.5f, IdealMoisture = 0.50f, MoistureTolerance = 0.30f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 24.0f, MaxSlopeDeg = 32.0f, MinSoilDepth = 0.10f, SalinityTolerance = 0.22f,
                SoilAffinity = new[] { 0.30f, 0.65f, 0.55f, 0.01f, 0.04f, 1.0f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 5.2f, HeightMinM = 10.0f, HeightMaxM = 16.5f, WindStiffness = 0.80f,
                BaseTint = new Color(0.11f, 0.24f, 0.18f), MapColor = new Color(0.12f, 0.34f, 0.32f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.SilverGlacierSpruce, SpeciesKey = "silver_glacier_spruce", DisplayName = "Vân Sam Bạc Chắn Gió",
                Layer = FloraLayer.Canopy, Morphology = FloraMorphology.SnowSpruceConifer,
                IdealTempC = -1.5f, TempToleranceC = 6.0f, IdealMoisture = 0.46f, MoistureTolerance = 0.30f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 26.0f, MaxSlopeDeg = 34.0f, MinSoilDepth = 0.08f, SalinityTolerance = 0.25f,
                SoilAffinity = new[] { 0.20f, 0.50f, 0.50f, 0.01f, 0.03f, 1.0f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 4.8f, HeightMinM = 9.0f, HeightMaxM = 14.5f, WindStiffness = 0.82f,
                BaseTint = new Color(0.22f, 0.34f, 0.31f), MapColor = new Color(0.22f, 0.44f, 0.45f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.DragonBloodTree, SpeciesKey = "dragon_blood_tree", DisplayName = "Cây Máu Rồng Tán Ô",
                Layer = FloraLayer.Canopy, Morphology = FloraMorphology.PrehistoricDesertUmbrella,
                IdealTempC = 28.5f, TempToleranceC = 7.5f, IdealMoisture = 0.20f, MoistureTolerance = 0.18f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 25.0f, MaxSlopeDeg = 28.0f, MinSoilDepth = 0.08f, SalinityTolerance = 0.40f,
                SoilAffinity = new[] { 0.08f, 0.15f, 0.35f, 1.0f, 0.30f, 0.18f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 6.8f, HeightMinM = 7.5f, HeightMaxM = 11.5f, WindStiffness = 0.88f,
                BaseTint = new Color(0.24f, 0.32f, 0.14f), MapColor = new Color(0.42f, 0.46f, 0.18f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.SavannaUmbrellaAcacia, SpeciesKey = "savanna_umbrella_acacia", DisplayName = "Cổ Thụ Xavan Tán Rộng",
                Layer = FloraLayer.Canopy, Morphology = FloraMorphology.PrehistoricDesertUmbrella,
                IdealTempC = 26.5f, TempToleranceC = 7.5f, IdealMoisture = 0.28f, MoistureTolerance = 0.20f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 23.0f, MaxSlopeDeg = 22.0f, MinSoilDepth = 0.14f, SalinityTolerance = 0.30f,
                SoilAffinity = new[] { 0.25f, 0.35f, 0.65f, 0.95f, 0.20f, 0.06f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 7.5f, HeightMinM = 8.0f, HeightMaxM = 12.5f, WindStiffness = 0.84f,
                BaseTint = new Color(0.32f, 0.38f, 0.14f), MapColor = new Color(0.48f, 0.48f, 0.16f)
            },

            // ===================== LAYER 3: UNDERSTORY (5) =====================
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.ArborescentTreeFern, SpeciesKey = "arborescent_tree_fern", DisplayName = "Dương Xỉ Thân Gỗ",
                Layer = FloraLayer.Understory, Morphology = FloraMorphology.PalmAndTreeFernRosette,
                IdealTempC = 20.0f, TempToleranceC = 8.0f, IdealMoisture = 0.62f, MoistureTolerance = 0.28f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 15.0f, MaxSlopeDeg = 28.0f, MinSoilDepth = 0.16f, SalinityTolerance = 0.20f,
                SoilAffinity = new[] { 1.0f, 0.95f, 0.25f, 0.03f, 0.08f, 0.04f },
                LightMin = 0.03f, LightMax = 0.72f, CrownRadiusM = 2.6f, HeightMinM = 3.2f, HeightMaxM = 5.4f, WindStiffness = 0.42f,
                BaseTint = new Color(0.18f, 0.42f, 0.12f), MapColor = new Color(0.15f, 0.44f, 0.14f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.CycadPrehistoric, SpeciesKey = "cycad_prehistoric", DisplayName = "Tuế Cổ Đại",
                Layer = FloraLayer.Understory, Morphology = FloraMorphology.PalmAndTreeFernRosette,
                IdealTempC = 22.0f, TempToleranceC = 8.5f, IdealMoisture = 0.50f, MoistureTolerance = 0.30f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 18.0f, MaxSlopeDeg = 30.0f, MinSoilDepth = 0.14f, SalinityTolerance = 0.35f,
                SoilAffinity = new[] { 0.75f, 0.95f, 0.45f, 0.20f, 0.25f, 0.06f },
                LightMin = 0.05f, LightMax = 0.85f, CrownRadiusM = 2.1f, HeightMinM = 2.2f, HeightMaxM = 3.8f, WindStiffness = 0.55f,
                BaseTint = new Color(0.16f, 0.36f, 0.11f), MapColor = new Color(0.16f, 0.38f, 0.13f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.GiantBambooVau, SpeciesKey = "giant_bamboo_vau", DisplayName = "Khóm Vầu",
                Layer = FloraLayer.Understory, Morphology = FloraMorphology.BambooShrubAgaveCluster,
                IdealTempC = 19.0f, TempToleranceC = 8.0f, IdealMoisture = 0.64f, MoistureTolerance = 0.28f,
                MinGroundwater = 0.12f, MaxWindSpeedMs = 17.0f, MaxSlopeDeg = 28.0f, MinSoilDepth = 0.18f, SalinityTolerance = 0.22f,
                SoilAffinity = new[] { 1.0f, 0.85f, 0.40f, 0.05f, 0.10f, 0.04f },
                LightMin = 0.10f, LightMax = 0.92f, CrownRadiusM = 2.3f, HeightMinM = 4.5f, HeightMaxM = 7.5f, WindStiffness = 0.35f,
                BaseTint = new Color(0.28f, 0.48f, 0.14f), MapColor = new Color(0.26f, 0.50f, 0.16f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.NipaWaterPalm, SpeciesKey = "nipa_water_palm", DisplayName = "Dừa Nước / Cọ Ốc Đảo",
                Layer = FloraLayer.Understory, Morphology = FloraMorphology.PalmAndTreeFernRosette,
                IdealTempC = 25.0f, TempToleranceC = 8.5f, IdealMoisture = 0.58f, MoistureTolerance = 0.35f,
                MinGroundwater = 0.25f, MaxWindSpeedMs = 22.0f, MaxSlopeDeg = 20.0f, MinSoilDepth = 0.12f, SalinityTolerance = 0.95f,
                SoilAffinity = new[] { 0.90f, 0.45f, 0.15f, 0.40f, 1.0f, 0.02f },
                LightMin = 0.25f, LightMax = 1.0f, CrownRadiusM = 3.2f, HeightMinM = 4.2f, HeightMaxM = 7.5f, WindStiffness = 0.45f,
                BaseTint = new Color(0.20f, 0.46f, 0.16f), MapColor = new Color(0.12f, 0.62f, 0.34f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.KrummholzDwarfPine, SpeciesKey = "krummholz_dwarf_pine", DisplayName = "Thông Lùn Bò Sát Đá",
                Layer = FloraLayer.Understory, Morphology = FloraMorphology.KrummholzDwarfPine,
                IdealTempC = -3.0f, TempToleranceC = 6.5f, IdealMoisture = 0.44f, MoistureTolerance = 0.32f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 28.0f, MaxSlopeDeg = 42.0f, MinSoilDepth = 0.04f, SalinityTolerance = 0.30f,
                SoilAffinity = new[] { 0.10f, 0.35f, 0.40f, 0.02f, 0.05f, 1.0f },
                LightMin = 0.35f, LightMax = 1.0f, CrownRadiusM = 2.4f, HeightMinM = 1.4f, HeightMaxM = 2.8f, WindStiffness = 0.72f,
                BaseTint = new Color(0.14f, 0.25f, 0.19f), MapColor = new Color(0.18f, 0.36f, 0.30f)
            },

            // ===================== LAYER 4: SHRUB (3) =====================
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.WildBerryBush, SpeciesKey = "wild_berry_bush", DisplayName = "Bụi Quả Dại",
                Layer = FloraLayer.Shrub, Morphology = FloraMorphology.BambooShrubAgaveCluster,
                IdealTempC = 15.0f, TempToleranceC = 10.5f, IdealMoisture = 0.50f, MoistureTolerance = 0.32f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 20.0f, MaxSlopeDeg = 32.0f, MinSoilDepth = 0.12f, SalinityTolerance = 0.30f,
                SoilAffinity = new[] { 0.85f, 1.0f, 0.75f, 0.08f, 0.20f, 0.18f },
                LightMin = 0.32f, LightMax = 0.95f, CrownRadiusM = 1.4f, HeightMinM = 1.1f, HeightMaxM = 2.1f, WindStiffness = 0.35f,
                BaseTint = new Color(0.24f, 0.42f, 0.15f), MapColor = new Color(0.32f, 0.52f, 0.18f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.PampasPlumeTallgrass, SpeciesKey = "pampas_plume_tallgrass", DisplayName = "Cỏ Lau Bông Trắng",
                Layer = FloraLayer.Shrub, Morphology = FloraMorphology.BambooShrubAgaveCluster,
                IdealTempC = 16.0f, TempToleranceC = 10.0f, IdealMoisture = 0.42f, MoistureTolerance = 0.30f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 24.0f, MaxSlopeDeg = 28.0f, MinSoilDepth = 0.10f, SalinityTolerance = 0.55f,
                SoilAffinity = new[] { 0.70f, 0.65f, 1.0f, 0.20f, 0.65f, 0.10f },
                LightMin = 0.45f, LightMax = 1.0f, CrownRadiusM = 1.2f, HeightMinM = 1.4f, HeightMaxM = 2.5f, WindStiffness = 0.14f,
                BaseTint = new Color(0.68f, 0.62f, 0.38f), MapColor = new Color(0.76f, 0.68f, 0.34f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.RedDesertAgave, SpeciesKey = "red_desert_agave", DisplayName = "Thùa Gai Hoang Mạc Đỏ",
                Layer = FloraLayer.Shrub, Morphology = FloraMorphology.BambooShrubAgaveCluster,
                IdealTempC = 28.0f, TempToleranceC = 8.5f, IdealMoisture = 0.18f, MoistureTolerance = 0.18f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 26.0f, MaxSlopeDeg = 34.0f, MinSoilDepth = 0.04f, SalinityTolerance = 0.50f,
                SoilAffinity = new[] { 0.05f, 0.10f, 0.35f, 1.0f, 0.35f, 0.15f },
                LightMin = 0.55f, LightMax = 1.0f, CrownRadiusM = 1.3f, HeightMinM = 1.0f, HeightMaxM = 1.9f, WindStiffness = 0.65f,
                BaseTint = new Color(0.32f, 0.40f, 0.20f), MapColor = new Color(0.56f, 0.42f, 0.18f)
            },

            // ===================== LAYER 5: HERB / GROUND (3) =====================
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.WetMossPatch, SpeciesKey = "wet_moss_patch", DisplayName = "Thảm Rêu Ẩm",
                Layer = FloraLayer.HerbGround, Morphology = FloraMorphology.GroundLitterGeology,
                IdealTempC = 16.0f, TempToleranceC = 11.0f, IdealMoisture = 0.68f, MoistureTolerance = 0.28f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 18.0f, MaxSlopeDeg = 35.0f, MinSoilDepth = 0.05f, SalinityTolerance = 0.15f,
                SoilAffinity = new[] { 1.0f, 0.95f, 0.25f, 0.02f, 0.05f, 0.25f },
                LightMin = 0.0f, LightMax = 0.60f, CrownRadiusM = 1.1f, HeightMinM = 0.25f, HeightMaxM = 0.55f, WindStiffness = 0.95f,
                BaseTint = new Color(0.14f, 0.34f, 0.09f), MapColor = new Color(0.14f, 0.34f, 0.09f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.BiolumForestMushroom, SpeciesKey = "biolum_forest_mushroom", DisplayName = "Cụm Nấm Rừng",
                Layer = FloraLayer.HerbGround, Morphology = FloraMorphology.GroundLitterGeology,
                IdealTempC = 18.0f, TempToleranceC = 9.0f, IdealMoisture = 0.66f, MoistureTolerance = 0.26f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 14.0f, MaxSlopeDeg = 28.0f, MinSoilDepth = 0.10f, SalinityTolerance = 0.10f,
                SoilAffinity = new[] { 1.0f, 0.95f, 0.20f, 0.01f, 0.02f, 0.05f },
                LightMin = 0.0f, LightMax = 0.45f, CrownRadiusM = 0.7f, HeightMinM = 0.35f, HeightMaxM = 0.75f, WindStiffness = 0.90f,
                BaseTint = new Color(0.62f, 0.56f, 0.34f), MapColor = new Color(0.50f, 0.46f, 0.28f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.ArcticReindeerMoss, SpeciesKey = "arctic_reindeer_moss", DisplayName = "Rêu Tuần Lộc",
                Layer = FloraLayer.HerbGround, Morphology = FloraMorphology.GroundLitterGeology,
                IdealTempC = -2.0f, TempToleranceC = 7.5f, IdealMoisture = 0.46f, MoistureTolerance = 0.32f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 28.0f, MaxSlopeDeg = 36.0f, MinSoilDepth = 0.03f, SalinityTolerance = 0.25f,
                SoilAffinity = new[] { 0.15f, 0.35f, 0.40f, 0.02f, 0.05f, 1.0f },
                LightMin = 0.20f, LightMax = 1.0f, CrownRadiusM = 1.0f, HeightMinM = 0.25f, HeightMaxM = 0.50f, WindStiffness = 0.95f,
                BaseTint = new Color(0.58f, 0.62f, 0.54f), MapColor = new Color(0.58f, 0.62f, 0.54f)
            },

            // ===================== LAYER 6: LITTER / SOIL / GEOLOGY (4) =====================
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.HollowFallenTrunk, SpeciesKey = "hollow_fallen_trunk", DisplayName = "Thân Gỗ Mục",
                Layer = FloraLayer.LitterSoil, Morphology = FloraMorphology.GroundLitterGeology,
                IdealTempC = 16.0f, TempToleranceC = 11.0f, IdealMoisture = 0.58f, MoistureTolerance = 0.30f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 22.0f, MaxSlopeDeg = 24.0f, MinSoilDepth = 0.14f, SalinityTolerance = 0.20f,
                SoilAffinity = new[] { 0.90f, 1.0f, 0.45f, 0.02f, 0.05f, 0.20f },
                LightMin = 0.0f, LightMax = 0.55f, CrownRadiusM = 2.0f, HeightMinM = 0.8f, HeightMaxM = 1.4f, WindStiffness = 1.0f,
                BaseTint = new Color(0.26f, 0.19f, 0.12f), MapColor = new Color(0.26f, 0.19f, 0.12f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.StreamClayDeposit, SpeciesKey = "stream_clay_deposit", DisplayName = "Đất Sét Ven Suối",
                Layer = FloraLayer.LitterSoil, Morphology = FloraMorphology.GroundLitterGeology,
                IdealTempC = 18.0f, TempToleranceC = 14.0f, IdealMoisture = 0.68f, MoistureTolerance = 0.32f,
                MinGroundwater = 0.35f, MaxWindSpeedMs = 26.0f, MaxSlopeDeg = 20.0f, MinSoilDepth = 0.10f, SalinityTolerance = 0.40f,
                SoilAffinity = new[] { 1.0f, 0.55f, 0.25f, 0.25f, 0.35f, 0.10f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 1.5f, HeightMinM = 0.45f, HeightMaxM = 0.85f, WindStiffness = 1.0f,
                BaseTint = new Color(0.42f, 0.34f, 0.26f), MapColor = new Color(0.42f, 0.34f, 0.26f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.ExposedCopperOre, SpeciesKey = "exposed_copper_ore", DisplayName = "Quặng Đồng Lộ Thiên",
                Layer = FloraLayer.LitterSoil, Morphology = FloraMorphology.GroundLitterGeology,
                IdealTempC = 12.0f, TempToleranceC = 22.0f, IdealMoisture = 0.38f, MoistureTolerance = 0.40f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 28.0f, MaxSlopeDeg = 55.0f, MinSoilDepth = 0.0f, SalinityTolerance = 0.50f,
                SoilAffinity = new[] { 0.10f, 0.20f, 0.35f, 0.55f, 0.10f, 1.0f },
                LightMin = 0.25f, LightMax = 1.0f, CrownRadiusM = 1.4f, HeightMinM = 0.9f, HeightMaxM = 1.8f, WindStiffness = 1.0f,
                BaseTint = new Color(0.28f, 0.54f, 0.44f), MapColor = new Color(0.28f, 0.54f, 0.44f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.Boulder, SpeciesKey = "boulder", DisplayName = "Đá Tảng",
                Layer = FloraLayer.LitterSoil, Morphology = FloraMorphology.GroundLitterGeology,
                IdealTempC = 12.0f, TempToleranceC = 24.0f, IdealMoisture = 0.35f, MoistureTolerance = 0.45f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 28.0f, MaxSlopeDeg = 55.0f, MinSoilDepth = 0.0f, SalinityTolerance = 0.80f,
                SoilAffinity = new[] { 0.25f, 0.35f, 0.50f, 0.70f, 0.35f, 1.0f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 1.6f, HeightMinM = 0.9f, HeightMaxM = 2.2f, WindStiffness = 1.0f,
                BaseTint = new Color(0.42f, 0.41f, 0.39f), MapColor = new Color(0.42f, 0.41f, 0.39f)
            },
        };
    }
}
