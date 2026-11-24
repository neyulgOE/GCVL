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

    public enum StemGroup : byte
    {
        WoodyBranching = 0,     // Nhóm 1: Thân gỗ lớn phân cành
        DwarfWoodyShrub = 1,    // Nhóm 2: Thân gỗ thấp & Bụi hóa gỗ
        ColumnarCaudexCulm = 2, // Nhóm 3: Thân cột, Thân cọc & Thân đốt
        HerbaceousGround = 3,   // Nhóm 4: Thân mềm, Thân thảo, Mọng nước, Dây leo & Thảm đáy
    }

    public enum FloraArchitecture : byte
    {
        ArchButtressBroadleaf = 0,  // 1. Đa cổ thụ, Đại thụ Thánh địa (22-32m)
        ArchEmergentSequoia = 1,    // 2. Tùng Hồng Thủy Sam (25-32m)
        ArchCanopyBroadleaf = 2,    // 3. Vú sữa, Bạch quả, Phong đỏ (11-18m)
        ArchWeepingTree = 3,        // 4. Liễu rủ, Bạch dương rủ (10-16m)
        ArchAlpineConifer = 4,      // 5. Thông tuyết, Vân sam bạc (11-18m)
        ArchSwollenBaobab = 5,      // 6. Bao báp cổ sinh (11-17m)
        ArchUmbrellaDesert = 6,     // 7. Cây Máu Rồng, Cổ thụ Xavan (8-14m)
        ArchKrummholz = 7,          // 8. Thông lùn sát tuyết (1.0-2.2m)
        ArchWoodyShrub = 8,         // 9. Bụi quả dại, Sơn tra, Quả tuyết, Gai khô (0.9-2.1m)
        ArchColumnarPalmFern = 9,   // 10. Cọ ốc đảo, Dừa nước, Dương xỉ thân gỗ (2.5-8.5m)
        ArchCaudexCycad = 10,       // 11. Tuế cổ đại (1.2-2.4m)
        ArchBambooCulm = 11,        // 12. Khóm Vầu khổng lồ (4.5-8.2m)
        ArchSoftTallHerb = 12,      // 13. Cỏ lau, Bãi sậy, Ráy tai voi, Cỏ lông vũ (0.35-1.8m)
        ArchSucculentAndGround = 13 // 14. Thùa gai, Sen đá, Trầu bà, Rêu, Nấm, Gỗ mục, Đất sét, Quặng, Đá
    }

    public enum FloraSpeciesId : byte
    {
        // Layer 1: Emergent (4) - WoodyBranching (22-32m)
        PrimevalBanyanFig = 0,
        GiantSequoiaReddawn = 1,
        SacredAncientHardwood = 2,
        BaobabPrehistoric = 3,

        // Layer 2: Canopy (9) - WoodyBranching (10-18m)
        StarAppleCanopy = 4,
        WeepingRiverWillow = 5,
        WeepingSilverBirch = 6,
        GinkgoAncientGold = 7,
        CrimsonSteppeMaple = 8,
        BorealSnowPine = 9,
        SilverGlacierSpruce = 10,
        DragonBloodTree = 11,
        SavannaUmbrellaAcacia = 12,

        // Layer 3: Understory (5) - ColumnarCaudexCulm + Krummholz (2.5-8.5m)
        ArborescentTreeFern = 13,
        CycadPrehistoric = 14,
        GiantBambooVau = 15,
        NipaWaterPalm = 16,
        KrummholzDwarfPine = 17,

        // Layer 4: Shrub (4) - DwarfWoodyShrub (0.9-2.2m)
        WildBerryBush = 18,
        HawthornBerryShrub = 19,
        SnowberryAlpineShrub = 20,
        AridThornScrub = 21,

        // Layer 5: Herb / Soft / Succulent / Vine (9) - HerbaceousGround (0.25-1.8m)
        PampasPlumeTallgrass = 22,
        RiverbankReedBed = 23,
        GiantElephantEar = 24,
        FeatherSteppeGrass = 25,
        RedDesertAgave = 26,
        RedRockSucculent = 27,
        EpiphyteBaseVine = 28,
        WetMossPatch = 29,
        BiolumForestMushroom = 30,
        ArcticReindeerMoss = 31,

        // Layer 6: Litter / Geology (4) - HerbaceousGround (0.3-1.6m)
        HollowFallenTrunk = 32,
        StreamClayDeposit = 33,
        ExposedCopperOre = 34,
        Boulder = 35,

        // Phase 1 Rainforest Understory & Hanging Liana Curtain (2)
        LianaMossCurtain = 36,
        LushSwordFern = 37,
    }

    /// <summary>
    /// Physical ecological niche profile for 36 prehistoric flora species across 4 StemGroups and 14 Architectures.
    /// Standardized 0.65x open-world scale: Emergent 22-32m, Canopy 10-18m, Columnar 2.5-8.5m, Shrub 0.9-2.2m, Herb 0.25-1.8m.
    /// </summary>
    public sealed class FloraNicheProfile
    {
        public FloraSpeciesId Id { get; init; }
        public string SpeciesKey { get; init; } = "";
        public string DisplayName { get; init; } = "";
        public FloraLayer Layer { get; init; }
        public StemGroup Stem { get; init; }
        public FloraArchitecture Architecture { get; init; }

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
        public float WindStiffness { get; init; }

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
            // ===================== LAYER 1: EMERGENT (22-32m, WoodyBranching) =====================
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.PrimevalBanyanFig, SpeciesKey = "primeval_banyan_fig", DisplayName = "Đa Cổ Thụ Nghìn Năm",
                Layer = FloraLayer.Emergent, Stem = StemGroup.WoodyBranching, Architecture = FloraArchitecture.ArchButtressBroadleaf,
                IdealTempC = 20.0f, TempToleranceC = 9.5f, IdealMoisture = 0.68f, MoistureTolerance = 0.30f,
                MinGroundwater = 0.04f, MaxWindSpeedMs = 18.5f, MaxSlopeDeg = 23.0f, MinSoilDepth = 0.30f, SalinityTolerance = 0.25f,
                SoilAffinity = new[] { 1.0f, 0.90f, 0.15f, 0.02f, 0.08f, 0.01f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 9.5f, HeightMinM = 22.0f, HeightMaxM = 29.0f, WindStiffness = 0.92f,
                BaseTint = new Color(0.84f, 0.98f, 0.82f), MapColor = new Color(0.06f, 0.26f, 0.08f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.GiantSequoiaReddawn, SpeciesKey = "giant_sequoia_reddawn", DisplayName = "Tùng Hồng Thủy Sam",
                Layer = FloraLayer.Emergent, Stem = StemGroup.WoodyBranching, Architecture = FloraArchitecture.ArchEmergentSequoia,
                IdealTempC = 14.5f, TempToleranceC = 6.5f, IdealMoisture = 0.65f, MoistureTolerance = 0.28f,
                MinGroundwater = 0.05f, MaxWindSpeedMs = 19.0f, MaxSlopeDeg = 26.0f, MinSoilDepth = 0.30f, SalinityTolerance = 0.18f,
                SoilAffinity = new[] { 0.80f, 1.0f, 0.35f, 0.02f, 0.05f, 0.08f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 7.2f, HeightMinM = 25.0f, HeightMaxM = 32.0f, WindStiffness = 0.93f,
                BaseTint = new Color(0.76f, 0.92f, 0.78f), MapColor = new Color(0.07f, 0.24f, 0.11f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.SacredAncientHardwood, SpeciesKey = "sacred_ancient_hardwood", DisplayName = "Đại Thụ Thánh Địa",
                Layer = FloraLayer.Emergent, Stem = StemGroup.WoodyBranching, Architecture = FloraArchitecture.ArchButtressBroadleaf,
                IdealTempC = 21.0f, TempToleranceC = 7.5f, IdealMoisture = 0.64f, MoistureTolerance = 0.30f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 18.0f, MaxSlopeDeg = 24.0f, MinSoilDepth = 0.30f, SalinityTolerance = 0.30f,
                SoilAffinity = new[] { 0.88f, 1.0f, 0.25f, 0.03f, 0.12f, 0.02f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 8.8f, HeightMinM = 21.0f, HeightMaxM = 28.0f, WindStiffness = 0.90f,
                BaseTint = new Color(0.90f, 1.04f, 0.84f), MapColor = new Color(0.09f, 0.30f, 0.10f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.BaobabPrehistoric, SpeciesKey = "baobab_prehistoric", DisplayName = "Bao Báp Cổ Sinh",
                Layer = FloraLayer.Emergent, Stem = StemGroup.WoodyBranching, Architecture = FloraArchitecture.ArchSwollenBaobab,
                IdealTempC = 29.0f, TempToleranceC = 7.5f, IdealMoisture = 0.24f, MoistureTolerance = 0.20f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 22.0f, MaxSlopeDeg = 20.0f, MinSoilDepth = 0.14f, SalinityTolerance = 0.35f,
                SoilAffinity = new[] { 0.15f, 0.20f, 0.45f, 1.0f, 0.30f, 0.08f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 7.5f, HeightMinM = 11.5f, HeightMaxM = 17.0f, WindStiffness = 0.94f,
                BaseTint = new Color(0.94f, 0.96f, 0.74f), MapColor = new Color(0.46f, 0.44f, 0.18f)
            },

            // ===================== LAYER 2: CANOPY (10-18m, WoodyBranching) =====================
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.StarAppleCanopy, SpeciesKey = "star_apple_canopy", DisplayName = "Vú Sữa Cổ Đại",
                Layer = FloraLayer.Canopy, Stem = StemGroup.WoodyBranching, Architecture = FloraArchitecture.ArchCanopyBroadleaf,
                IdealTempC = 20.5f, TempToleranceC = 8.0f, IdealMoisture = 0.58f, MoistureTolerance = 0.30f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 18.5f, MaxSlopeDeg = 26.0f, MinSoilDepth = 0.22f, SalinityTolerance = 0.28f,
                SoilAffinity = new[] { 0.88f, 1.0f, 0.32f, 0.04f, 0.12f, 0.03f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 5.6f, HeightMinM = 11.0f, HeightMaxM = 17.5f, WindStiffness = 0.88f,
                BaseTint = new Color(0.92f, 1.05f, 0.85f), MapColor = new Color(0.12f, 0.38f, 0.12f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.WeepingRiverWillow, SpeciesKey = "weeping_river_willow", DisplayName = "Liễu Rủ Ven Sông",
                Layer = FloraLayer.Canopy, Stem = StemGroup.WoodyBranching, Architecture = FloraArchitecture.ArchWeepingTree,
                IdealTempC = 17.0f, TempToleranceC = 9.5f, IdealMoisture = 0.72f, MoistureTolerance = 0.30f,
                MinGroundwater = 0.24f, MaxWindSpeedMs = 19.5f, MaxSlopeDeg = 22.0f, MinSoilDepth = 0.16f, SalinityTolerance = 0.35f,
                SoilAffinity = new[] { 1.0f, 0.75f, 0.35f, 0.15f, 0.25f, 0.05f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 5.4f, HeightMinM = 10.0f, HeightMaxM = 15.5f, WindStiffness = 0.82f,
                BaseTint = new Color(0.96f, 1.12f, 0.84f), MapColor = new Color(0.18f, 0.48f, 0.22f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.WeepingSilverBirch, SpeciesKey = "weeping_silver_birch", DisplayName = "Bạch Dương Rủ",
                Layer = FloraLayer.Canopy, Stem = StemGroup.WoodyBranching, Architecture = FloraArchitecture.ArchWeepingTree,
                IdealTempC = 10.0f, TempToleranceC = 7.5f, IdealMoisture = 0.48f, MoistureTolerance = 0.28f,
                MinGroundwater = 0.04f, MaxWindSpeedMs = 20.5f, MaxSlopeDeg = 26.0f, MinSoilDepth = 0.14f, SalinityTolerance = 0.20f,
                SoilAffinity = new[] { 0.65f, 0.85f, 0.95f, 0.04f, 0.06f, 0.28f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 4.8f, HeightMinM = 10.0f, HeightMaxM = 14.5f, WindStiffness = 0.84f,
                BaseTint = new Color(0.92f, 1.04f, 0.86f), MapColor = new Color(0.36f, 0.66f, 0.26f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.GinkgoAncientGold, SpeciesKey = "ginkgo_ancient_gold", DisplayName = "Bạch Quả Cổ Sinh",
                Layer = FloraLayer.Canopy, Stem = StemGroup.WoodyBranching, Architecture = FloraArchitecture.ArchCanopyBroadleaf,
                IdealTempC = 11.5f, TempToleranceC = 6.8f, IdealMoisture = 0.42f, MoistureTolerance = 0.26f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 20.5f, MaxSlopeDeg = 28.0f, MinSoilDepth = 0.16f, SalinityTolerance = 0.20f,
                SoilAffinity = new[] { 0.40f, 0.76f, 1.0f, 0.06f, 0.05f, 0.12f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 5.2f, HeightMinM = 11.0f, HeightMaxM = 17.0f, WindStiffness = 0.86f,
                BaseTint = new Color(0.96f, 1.06f, 0.84f), MapColor = new Color(0.46f, 0.68f, 0.20f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.CrimsonSteppeMaple, SpeciesKey = "crimson_steppe_maple", DisplayName = "Phong Cổ Thụ Thảo Nguyên",
                Layer = FloraLayer.Canopy, Stem = StemGroup.WoodyBranching, Architecture = FloraArchitecture.ArchCanopyBroadleaf,
                IdealTempC = 12.0f, TempToleranceC = 6.5f, IdealMoisture = 0.38f, MoistureTolerance = 0.26f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 21.0f, MaxSlopeDeg = 28.0f, MinSoilDepth = 0.15f, SalinityTolerance = 0.18f,
                SoilAffinity = new[] { 0.35f, 0.72f, 1.0f, 0.08f, 0.05f, 0.14f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 5.0f, HeightMinM = 10.0f, HeightMaxM = 15.5f, WindStiffness = 0.85f,
                BaseTint = new Color(0.88f, 0.98f, 0.82f), MapColor = new Color(0.32f, 0.58f, 0.20f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.BorealSnowPine, SpeciesKey = "boreal_snow_pine", DisplayName = "Thông Tuyết Phương Bắc",
                Layer = FloraLayer.Canopy, Stem = StemGroup.WoodyBranching, Architecture = FloraArchitecture.ArchAlpineConifer,
                IdealTempC = 1.5f, TempToleranceC = 6.5f, IdealMoisture = 0.50f, MoistureTolerance = 0.30f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 24.0f, MaxSlopeDeg = 32.0f, MinSoilDepth = 0.10f, SalinityTolerance = 0.22f,
                SoilAffinity = new[] { 0.30f, 0.65f, 0.55f, 0.01f, 0.04f, 1.0f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 4.2f, HeightMinM = 11.0f, HeightMaxM = 18.0f, WindStiffness = 0.88f,
                BaseTint = new Color(0.78f, 0.90f, 0.86f), MapColor = new Color(0.12f, 0.34f, 0.32f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.SilverGlacierSpruce, SpeciesKey = "silver_glacier_spruce", DisplayName = "Vân Sam Bạc Chắn Gió",
                Layer = FloraLayer.Canopy, Stem = StemGroup.WoodyBranching, Architecture = FloraArchitecture.ArchAlpineConifer,
                IdealTempC = -1.5f, TempToleranceC = 6.0f, IdealMoisture = 0.46f, MoistureTolerance = 0.30f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 26.0f, MaxSlopeDeg = 34.0f, MinSoilDepth = 0.08f, SalinityTolerance = 0.25f,
                SoilAffinity = new[] { 0.20f, 0.50f, 0.50f, 0.01f, 0.03f, 1.0f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 3.8f, HeightMinM = 10.0f, HeightMaxM = 16.0f, WindStiffness = 0.90f,
                BaseTint = new Color(0.92f, 1.02f, 1.04f), MapColor = new Color(0.22f, 0.44f, 0.45f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.DragonBloodTree, SpeciesKey = "dragon_blood_tree", DisplayName = "Cây Máu Rồng Tán Ô",
                Layer = FloraLayer.Canopy, Stem = StemGroup.WoodyBranching, Architecture = FloraArchitecture.ArchUmbrellaDesert,
                IdealTempC = 28.5f, TempToleranceC = 7.5f, IdealMoisture = 0.20f, MoistureTolerance = 0.18f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 25.0f, MaxSlopeDeg = 28.0f, MinSoilDepth = 0.08f, SalinityTolerance = 0.40f,
                SoilAffinity = new[] { 0.08f, 0.15f, 0.35f, 1.0f, 0.30f, 0.18f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 5.4f, HeightMinM = 8.0f, HeightMaxM = 12.5f, WindStiffness = 0.90f,
                BaseTint = new Color(0.90f, 0.94f, 0.72f), MapColor = new Color(0.42f, 0.46f, 0.18f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.SavannaUmbrellaAcacia, SpeciesKey = "savanna_umbrella_acacia", DisplayName = "Cổ Thụ Xavan Tán Rộng",
                Layer = FloraLayer.Canopy, Stem = StemGroup.WoodyBranching, Architecture = FloraArchitecture.ArchUmbrellaDesert,
                IdealTempC = 26.5f, TempToleranceC = 7.5f, IdealMoisture = 0.28f, MoistureTolerance = 0.20f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 23.0f, MaxSlopeDeg = 22.0f, MinSoilDepth = 0.14f, SalinityTolerance = 0.30f,
                SoilAffinity = new[] { 0.25f, 0.35f, 0.65f, 0.95f, 0.20f, 0.06f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 6.0f, HeightMinM = 8.5f, HeightMaxM = 14.0f, WindStiffness = 0.88f,
                BaseTint = new Color(0.96f, 1.00f, 0.74f), MapColor = new Color(0.48f, 0.48f, 0.16f)
            },

            // ===================== LAYER 3: COLUMNAR / CAUDEX / CULM + KRUMMHOLZ (2.5-8.5m) =====================
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.ArborescentTreeFern, SpeciesKey = "arborescent_tree_fern", DisplayName = "Dương Xỉ Thân Gỗ",
                Layer = FloraLayer.Understory, Stem = StemGroup.ColumnarCaudexCulm, Architecture = FloraArchitecture.ArchColumnarPalmFern,
                IdealTempC = 20.0f, TempToleranceC = 8.0f, IdealMoisture = 0.62f, MoistureTolerance = 0.28f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 15.0f, MaxSlopeDeg = 28.0f, MinSoilDepth = 0.16f, SalinityTolerance = 0.20f,
                SoilAffinity = new[] { 1.0f, 0.95f, 0.25f, 0.03f, 0.08f, 0.04f },
                LightMin = 0.03f, LightMax = 0.72f, CrownRadiusM = 2.2f, HeightMinM = 2.5f, HeightMaxM = 4.6f, WindStiffness = 0.56f,
                BaseTint = new Color(0.18f, 0.42f, 0.12f), MapColor = new Color(0.15f, 0.44f, 0.14f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.CycadPrehistoric, SpeciesKey = "cycad_prehistoric", DisplayName = "Tuế Cổ Đại",
                Layer = FloraLayer.Understory, Stem = StemGroup.ColumnarCaudexCulm, Architecture = FloraArchitecture.ArchCaudexCycad,
                IdealTempC = 22.0f, TempToleranceC = 8.5f, IdealMoisture = 0.50f, MoistureTolerance = 0.30f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 18.0f, MaxSlopeDeg = 30.0f, MinSoilDepth = 0.14f, SalinityTolerance = 0.35f,
                SoilAffinity = new[] { 0.75f, 0.95f, 0.45f, 0.20f, 0.25f, 0.06f },
                LightMin = 0.05f, LightMax = 0.85f, CrownRadiusM = 1.8f, HeightMinM = 1.4f, HeightMaxM = 2.6f, WindStiffness = 0.62f,
                BaseTint = new Color(0.16f, 0.36f, 0.11f), MapColor = new Color(0.16f, 0.38f, 0.13f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.GiantBambooVau, SpeciesKey = "giant_bamboo_vau", DisplayName = "Khóm Vầu Khổng Lồ",
                Layer = FloraLayer.Understory, Stem = StemGroup.ColumnarCaudexCulm, Architecture = FloraArchitecture.ArchBambooCulm,
                IdealTempC = 19.0f, TempToleranceC = 8.0f, IdealMoisture = 0.64f, MoistureTolerance = 0.28f,
                MinGroundwater = 0.10f, MaxWindSpeedMs = 17.0f, MaxSlopeDeg = 28.0f, MinSoilDepth = 0.18f, SalinityTolerance = 0.22f,
                SoilAffinity = new[] { 1.0f, 0.85f, 0.40f, 0.05f, 0.10f, 0.04f },
                LightMin = 0.10f, LightMax = 0.92f, CrownRadiusM = 2.1f, HeightMinM = 4.5f, HeightMaxM = 8.2f, WindStiffness = 0.50f,
                BaseTint = new Color(0.28f, 0.48f, 0.14f), MapColor = new Color(0.26f, 0.50f, 0.16f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.NipaWaterPalm, SpeciesKey = "nipa_water_palm", DisplayName = "Dừa Nước / Cọ Ốc Đảo",
                Layer = FloraLayer.Understory, Stem = StemGroup.ColumnarCaudexCulm, Architecture = FloraArchitecture.ArchColumnarPalmFern,
                IdealTempC = 25.0f, TempToleranceC = 8.5f, IdealMoisture = 0.58f, MoistureTolerance = 0.35f,
                MinGroundwater = 0.22f, MaxWindSpeedMs = 22.0f, MaxSlopeDeg = 20.0f, MinSoilDepth = 0.12f, SalinityTolerance = 0.95f,
                SoilAffinity = new[] { 0.90f, 0.45f, 0.15f, 0.40f, 1.0f, 0.02f },
                LightMin = 0.25f, LightMax = 1.0f, CrownRadiusM = 2.6f, HeightMinM = 4.0f, HeightMaxM = 8.0f, WindStiffness = 0.54f,
                BaseTint = new Color(0.20f, 0.46f, 0.16f), MapColor = new Color(0.12f, 0.62f, 0.34f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.KrummholzDwarfPine, SpeciesKey = "krummholz_dwarf_pine", DisplayName = "Thông Lùn Bò Sát Đá",
                Layer = FloraLayer.Understory, Stem = StemGroup.DwarfWoodyShrub, Architecture = FloraArchitecture.ArchKrummholz,
                IdealTempC = -3.0f, TempToleranceC = 6.5f, IdealMoisture = 0.44f, MoistureTolerance = 0.32f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 28.0f, MaxSlopeDeg = 42.0f, MinSoilDepth = 0.04f, SalinityTolerance = 0.30f,
                SoilAffinity = new[] { 0.10f, 0.35f, 0.40f, 0.02f, 0.05f, 1.0f },
                LightMin = 0.35f, LightMax = 1.0f, CrownRadiusM = 1.9f, HeightMinM = 1.0f, HeightMaxM = 2.2f, WindStiffness = 0.78f,
                BaseTint = new Color(0.14f, 0.25f, 0.19f), MapColor = new Color(0.18f, 0.36f, 0.30f)
            },

            // ===================== LAYER 4: SHRUB (0.9-2.2m, DwarfWoodyShrub) =====================
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.WildBerryBush, SpeciesKey = "wild_berry_bush", DisplayName = "Bụi Quả Dại",
                Layer = FloraLayer.Shrub, Stem = StemGroup.DwarfWoodyShrub, Architecture = FloraArchitecture.ArchWoodyShrub,
                IdealTempC = 16.0f, TempToleranceC = 10.5f, IdealMoisture = 0.52f, MoistureTolerance = 0.32f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 20.0f, MaxSlopeDeg = 32.0f, MinSoilDepth = 0.12f, SalinityTolerance = 0.30f,
                SoilAffinity = new[] { 0.85f, 1.0f, 0.75f, 0.08f, 0.20f, 0.18f },
                LightMin = 0.32f, LightMax = 0.95f, CrownRadiusM = 1.2f, HeightMinM = 0.9f, HeightMaxM = 1.9f, WindStiffness = 0.65f,
                BaseTint = new Color(0.24f, 0.42f, 0.15f), MapColor = new Color(0.32f, 0.52f, 0.18f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.HawthornBerryShrub, SpeciesKey = "hawthorn_berry_shrub", DisplayName = "Bụi Sơn Tra",
                Layer = FloraLayer.Shrub, Stem = StemGroup.DwarfWoodyShrub, Architecture = FloraArchitecture.ArchWoodyShrub,
                IdealTempC = 11.0f, TempToleranceC = 7.5f, IdealMoisture = 0.42f, MoistureTolerance = 0.28f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 22.0f, MaxSlopeDeg = 34.0f, MinSoilDepth = 0.10f, SalinityTolerance = 0.25f,
                SoilAffinity = new[] { 0.45f, 0.75f, 1.0f, 0.10f, 0.12f, 0.25f },
                LightMin = 0.38f, LightMax = 1.0f, CrownRadiusM = 1.2f, HeightMinM = 1.0f, HeightMaxM = 2.1f, WindStiffness = 0.68f,
                BaseTint = new Color(0.42f, 0.48f, 0.16f), MapColor = new Color(0.48f, 0.52f, 0.18f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.SnowberryAlpineShrub, SpeciesKey = "snowberry_alpine_shrub", DisplayName = "Bụi Quả Tuyết",
                Layer = FloraLayer.Shrub, Stem = StemGroup.DwarfWoodyShrub, Architecture = FloraArchitecture.ArchWoodyShrub,
                IdealTempC = 0.5f, TempToleranceC = 6.5f, IdealMoisture = 0.48f, MoistureTolerance = 0.30f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 26.0f, MaxSlopeDeg = 38.0f, MinSoilDepth = 0.06f, SalinityTolerance = 0.25f,
                SoilAffinity = new[] { 0.20f, 0.45f, 0.45f, 0.02f, 0.06f, 1.0f },
                LightMin = 0.28f, LightMax = 1.0f, CrownRadiusM = 1.0f, HeightMinM = 0.8f, HeightMaxM = 1.6f, WindStiffness = 0.70f,
                BaseTint = new Color(0.32f, 0.44f, 0.38f), MapColor = new Color(0.38f, 0.52f, 0.48f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.AridThornScrub, SpeciesKey = "arid_thorn_scrub", DisplayName = "Bụi Gai Khô",
                Layer = FloraLayer.Shrub, Stem = StemGroup.DwarfWoodyShrub, Architecture = FloraArchitecture.ArchWoodyShrub,
                IdealTempC = 28.0f, TempToleranceC = 8.0f, IdealMoisture = 0.16f, MoistureTolerance = 0.18f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 27.0f, MaxSlopeDeg = 36.0f, MinSoilDepth = 0.04f, SalinityTolerance = 0.55f,
                SoilAffinity = new[] { 0.06f, 0.12f, 0.40f, 1.0f, 0.45f, 0.18f },
                LightMin = 0.50f, LightMax = 1.0f, CrownRadiusM = 1.1f, HeightMinM = 0.8f, HeightMaxM = 1.8f, WindStiffness = 0.76f,
                BaseTint = new Color(0.42f, 0.38f, 0.22f), MapColor = new Color(0.54f, 0.44f, 0.22f)
            },

            // ===================== LAYER 5: HERB / SOFT / SUCCULENT / VINE (0.25-1.8m, HerbaceousGround) =====================
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.PampasPlumeTallgrass, SpeciesKey = "pampas_plume_tallgrass", DisplayName = "Cỏ Lau Bông Trắng",
                Layer = FloraLayer.HerbGround, Stem = StemGroup.HerbaceousGround, Architecture = FloraArchitecture.ArchSoftTallHerb,
                IdealTempC = 16.0f, TempToleranceC = 10.0f, IdealMoisture = 0.42f, MoistureTolerance = 0.30f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 24.0f, MaxSlopeDeg = 28.0f, MinSoilDepth = 0.10f, SalinityTolerance = 0.55f,
                SoilAffinity = new[] { 0.70f, 0.65f, 1.0f, 0.20f, 0.65f, 0.10f },
                LightMin = 0.45f, LightMax = 1.0f, CrownRadiusM = 1.0f, HeightMinM = 1.0f, HeightMaxM = 1.8f, WindStiffness = 0.15f,
                BaseTint = new Color(0.68f, 0.62f, 0.38f), MapColor = new Color(0.76f, 0.68f, 0.34f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.RiverbankReedBed, SpeciesKey = "riverbank_reed_bed", DisplayName = "Bãi Sậy Ven Sông",
                Layer = FloraLayer.HerbGround, Stem = StemGroup.HerbaceousGround, Architecture = FloraArchitecture.ArchSoftTallHerb,
                IdealTempC = 16.5f, TempToleranceC = 12.5f, IdealMoisture = 0.68f, MoistureTolerance = 0.30f,
                MinGroundwater = 0.16f, MaxWindSpeedMs = 23.0f, MaxSlopeDeg = 18.0f, MinSoilDepth = 0.08f, SalinityTolerance = 0.70f,
                SoilAffinity = new[] { 1.0f, 0.55f, 0.25f, 0.10f, 0.60f, 0.08f },
                LightMin = 0.20f, LightMax = 1.0f, CrownRadiusM = 0.9f, HeightMinM = 1.0f, HeightMaxM = 1.7f, WindStiffness = 0.14f,
                BaseTint = new Color(0.38f, 0.52f, 0.22f), MapColor = new Color(0.32f, 0.54f, 0.24f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.GiantElephantEar, SpeciesKey = "giant_elephant_ear", DisplayName = "Ráy Tai Voi",
                Layer = FloraLayer.HerbGround, Stem = StemGroup.HerbaceousGround, Architecture = FloraArchitecture.ArchSoftTallHerb,
                IdealTempC = 19.0f, TempToleranceC = 10.0f, IdealMoisture = 0.66f, MoistureTolerance = 0.28f,
                MinGroundwater = 0.12f, MaxWindSpeedMs = 17.0f, MaxSlopeDeg = 24.0f, MinSoilDepth = 0.10f, SalinityTolerance = 0.22f,
                SoilAffinity = new[] { 1.0f, 0.85f, 0.15f, 0.02f, 0.08f, 0.02f },
                LightMin = 0.04f, LightMax = 0.75f, CrownRadiusM = 1.1f, HeightMinM = 0.8f, HeightMaxM = 1.6f, WindStiffness = 0.24f,
                BaseTint = new Color(0.16f, 0.44f, 0.12f), MapColor = new Color(0.16f, 0.46f, 0.14f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.FeatherSteppeGrass, SpeciesKey = "feather_steppe_grass", DisplayName = "Cỏ Lông Vũ Thảo Nguyên",
                Layer = FloraLayer.HerbGround, Stem = StemGroup.HerbaceousGround, Architecture = FloraArchitecture.ArchSoftTallHerb,
                IdealTempC = 13.0f, TempToleranceC = 8.5f, IdealMoisture = 0.36f, MoistureTolerance = 0.26f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 26.0f, MaxSlopeDeg = 30.0f, MinSoilDepth = 0.08f, SalinityTolerance = 0.30f,
                SoilAffinity = new[] { 0.40f, 0.65f, 1.0f, 0.25f, 0.25f, 0.12f },
                LightMin = 0.48f, LightMax = 1.0f, CrownRadiusM = 0.8f, HeightMinM = 0.35f, HeightMaxM = 0.85f, WindStiffness = 0.12f,
                BaseTint = new Color(0.62f, 0.56f, 0.26f), MapColor = new Color(0.68f, 0.60f, 0.26f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.RedDesertAgave, SpeciesKey = "red_desert_agave", DisplayName = "Thùa Gai Khổng Lồ",
                Layer = FloraLayer.HerbGround, Stem = StemGroup.HerbaceousGround, Architecture = FloraArchitecture.ArchSucculentAndGround,
                IdealTempC = 28.0f, TempToleranceC = 8.5f, IdealMoisture = 0.18f, MoistureTolerance = 0.18f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 26.0f, MaxSlopeDeg = 34.0f, MinSoilDepth = 0.04f, SalinityTolerance = 0.50f,
                SoilAffinity = new[] { 0.05f, 0.10f, 0.35f, 1.0f, 0.35f, 0.15f },
                LightMin = 0.55f, LightMax = 1.0f, CrownRadiusM = 1.0f, HeightMinM = 0.7f, HeightMaxM = 1.4f, WindStiffness = 0.98f,
                BaseTint = new Color(0.32f, 0.40f, 0.20f), MapColor = new Color(0.56f, 0.42f, 0.18f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.RedRockSucculent, SpeciesKey = "red_rock_succulent", DisplayName = "Sen Đá Đất Đỏ",
                Layer = FloraLayer.HerbGround, Stem = StemGroup.HerbaceousGround, Architecture = FloraArchitecture.ArchSucculentAndGround,
                IdealTempC = 27.0f, TempToleranceC = 9.0f, IdealMoisture = 0.15f, MoistureTolerance = 0.18f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 28.0f, MaxSlopeDeg = 42.0f, MinSoilDepth = 0.02f, SalinityTolerance = 0.55f,
                SoilAffinity = new[] { 0.04f, 0.08f, 0.30f, 1.0f, 0.40f, 0.35f },
                LightMin = 0.55f, LightMax = 1.0f, CrownRadiusM = 0.6f, HeightMinM = 0.25f, HeightMaxM = 0.50f, WindStiffness = 0.99f,
                BaseTint = new Color(0.46f, 0.44f, 0.24f), MapColor = new Color(0.58f, 0.46f, 0.24f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.EpiphyteBaseVine, SpeciesKey = "epiphyte_base_vine", DisplayName = "Dây Trầu Bà Leo Gốc",
                Layer = FloraLayer.HerbGround, Stem = StemGroup.HerbaceousGround, Architecture = FloraArchitecture.ArchSucculentAndGround,
                IdealTempC = 21.0f, TempToleranceC = 8.0f, IdealMoisture = 0.68f, MoistureTolerance = 0.25f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 15.0f, MaxSlopeDeg = 25.0f, MinSoilDepth = 0.15f, SalinityTolerance = 0.15f,
                SoilAffinity = new[] { 1.0f, 0.95f, 0.18f, 0.01f, 0.05f, 0.02f },
                LightMin = 0.0f, LightMax = 0.45f, CrownRadiusM = 0.8f, HeightMinM = 1.1f, HeightMaxM = 1.8f, WindStiffness = 0.85f,
                BaseTint = new Color(0.14f, 0.38f, 0.10f), MapColor = new Color(0.12f, 0.38f, 0.10f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.WetMossPatch, SpeciesKey = "wet_moss_patch", DisplayName = "Thảm Rêu Ẩm",
                Layer = FloraLayer.HerbGround, Stem = StemGroup.HerbaceousGround, Architecture = FloraArchitecture.ArchSucculentAndGround,
                IdealTempC = 16.0f, TempToleranceC = 11.0f, IdealMoisture = 0.68f, MoistureTolerance = 0.28f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 18.0f, MaxSlopeDeg = 35.0f, MinSoilDepth = 0.05f, SalinityTolerance = 0.15f,
                SoilAffinity = new[] { 1.0f, 0.95f, 0.25f, 0.02f, 0.05f, 0.25f },
                LightMin = 0.0f, LightMax = 0.60f, CrownRadiusM = 1.0f, HeightMinM = 0.22f, HeightMaxM = 0.45f, WindStiffness = 0.99f,
                BaseTint = new Color(0.14f, 0.34f, 0.09f), MapColor = new Color(0.14f, 0.34f, 0.09f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.BiolumForestMushroom, SpeciesKey = "biolum_forest_mushroom", DisplayName = "Cụm Nấm Rừng",
                Layer = FloraLayer.HerbGround, Stem = StemGroup.HerbaceousGround, Architecture = FloraArchitecture.ArchSucculentAndGround,
                IdealTempC = 18.0f, TempToleranceC = 9.0f, IdealMoisture = 0.66f, MoistureTolerance = 0.26f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 14.0f, MaxSlopeDeg = 28.0f, MinSoilDepth = 0.10f, SalinityTolerance = 0.10f,
                SoilAffinity = new[] { 1.0f, 0.95f, 0.20f, 0.01f, 0.02f, 0.05f },
                LightMin = 0.0f, LightMax = 0.45f, CrownRadiusM = 0.6f, HeightMinM = 0.25f, HeightMaxM = 0.60f, WindStiffness = 0.99f,
                BaseTint = new Color(0.62f, 0.56f, 0.34f), MapColor = new Color(0.50f, 0.46f, 0.28f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.ArcticReindeerMoss, SpeciesKey = "arctic_reindeer_moss", DisplayName = "Rêu Tuần Lộc",
                Layer = FloraLayer.HerbGround, Stem = StemGroup.HerbaceousGround, Architecture = FloraArchitecture.ArchSucculentAndGround,
                IdealTempC = -2.0f, TempToleranceC = 7.5f, IdealMoisture = 0.46f, MoistureTolerance = 0.32f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 28.0f, MaxSlopeDeg = 36.0f, MinSoilDepth = 0.03f, SalinityTolerance = 0.25f,
                SoilAffinity = new[] { 0.15f, 0.35f, 0.40f, 0.02f, 0.05f, 1.0f },
                LightMin = 0.20f, LightMax = 1.0f, CrownRadiusM = 0.9f, HeightMinM = 0.22f, HeightMaxM = 0.45f, WindStiffness = 0.99f,
                BaseTint = new Color(0.58f, 0.62f, 0.54f), MapColor = new Color(0.58f, 0.62f, 0.54f)
            },

            // ===================== LAYER 6: LITTER / GEOLOGY (0.3-1.6m, HerbaceousGround) =====================
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.HollowFallenTrunk, SpeciesKey = "hollow_fallen_trunk", DisplayName = "Thân Gỗ Mục",
                Layer = FloraLayer.LitterSoil, Stem = StemGroup.HerbaceousGround, Architecture = FloraArchitecture.ArchSucculentAndGround,
                IdealTempC = 16.0f, TempToleranceC = 11.0f, IdealMoisture = 0.58f, MoistureTolerance = 0.30f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 22.0f, MaxSlopeDeg = 24.0f, MinSoilDepth = 0.14f, SalinityTolerance = 0.20f,
                SoilAffinity = new[] { 0.90f, 1.0f, 0.45f, 0.02f, 0.05f, 0.20f },
                LightMin = 0.0f, LightMax = 0.55f, CrownRadiusM = 1.5f, HeightMinM = 0.6f, HeightMaxM = 1.1f, WindStiffness = 1.0f,
                BaseTint = new Color(0.26f, 0.19f, 0.12f), MapColor = new Color(0.26f, 0.19f, 0.12f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.StreamClayDeposit, SpeciesKey = "stream_clay_deposit", DisplayName = "Đất Sét Ven Suối",
                Layer = FloraLayer.LitterSoil, Stem = StemGroup.HerbaceousGround, Architecture = FloraArchitecture.ArchSucculentAndGround,
                IdealTempC = 18.0f, TempToleranceC = 14.0f, IdealMoisture = 0.68f, MoistureTolerance = 0.32f,
                MinGroundwater = 0.35f, MaxWindSpeedMs = 26.0f, MaxSlopeDeg = 20.0f, MinSoilDepth = 0.10f, SalinityTolerance = 0.40f,
                SoilAffinity = new[] { 1.0f, 0.55f, 0.25f, 0.25f, 0.35f, 0.10f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 1.2f, HeightMinM = 0.35f, HeightMaxM = 0.70f, WindStiffness = 1.0f,
                BaseTint = new Color(0.42f, 0.34f, 0.26f), MapColor = new Color(0.42f, 0.34f, 0.26f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.ExposedCopperOre, SpeciesKey = "exposed_copper_ore", DisplayName = "Quặng Đồng Lộ Thiên",
                Layer = FloraLayer.LitterSoil, Stem = StemGroup.HerbaceousGround, Architecture = FloraArchitecture.ArchSucculentAndGround,
                IdealTempC = 12.0f, TempToleranceC = 22.0f, IdealMoisture = 0.38f, MoistureTolerance = 0.40f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 28.0f, MaxSlopeDeg = 55.0f, MinSoilDepth = 0.0f, SalinityTolerance = 0.50f,
                SoilAffinity = new[] { 0.10f, 0.20f, 0.35f, 0.55f, 0.10f, 1.0f },
                LightMin = 0.25f, LightMax = 1.0f, CrownRadiusM = 1.2f, HeightMinM = 0.7f, HeightMaxM = 1.5f, WindStiffness = 1.0f,
                BaseTint = new Color(0.28f, 0.54f, 0.44f), MapColor = new Color(0.28f, 0.54f, 0.44f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.Boulder, SpeciesKey = "boulder", DisplayName = "Đá Tảng",
                Layer = FloraLayer.LitterSoil, Stem = StemGroup.HerbaceousGround, Architecture = FloraArchitecture.ArchSucculentAndGround,
                IdealTempC = 12.0f, TempToleranceC = 24.0f, IdealMoisture = 0.35f, MoistureTolerance = 0.45f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 28.0f, MaxSlopeDeg = 55.0f, MinSoilDepth = 0.0f, SalinityTolerance = 0.80f,
                SoilAffinity = new[] { 0.25f, 0.35f, 0.50f, 0.70f, 0.35f, 1.0f },
                LightMin = 0.0f, LightMax = 1.0f, CrownRadiusM = 1.3f, HeightMinM = 0.7f, HeightMaxM = 1.7f, WindStiffness = 1.0f,
                BaseTint = new Color(0.42f, 0.41f, 0.39f), MapColor = new Color(0.42f, 0.41f, 0.39f)
            },

            // ===================== PHASE 1: HANGING MOSS LIANA & LUSH SWORD FERN =====================
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.LianaMossCurtain, SpeciesKey = "liana_moss_curtain", DisplayName = "Dây Leo Rủ Phủ Rêu",
                Layer = FloraLayer.HerbGround, Stem = StemGroup.HerbaceousGround, Architecture = FloraArchitecture.ArchSucculentAndGround,
                IdealTempC = 20.0f, TempToleranceC = 10.0f, IdealMoisture = 0.72f, MoistureTolerance = 0.25f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 18.0f, MaxSlopeDeg = 30.0f, MinSoilDepth = 0.10f, SalinityTolerance = 0.15f,
                SoilAffinity = new[] { 1.0f, 1.0f, 0.15f, 0.0f, 0.02f, 0.05f },
                LightMin = 0.0f, LightMax = 0.55f, CrownRadiusM = 1.2f, HeightMinM = 4.0f, HeightMaxM = 12.0f, WindStiffness = 0.35f,
                BaseTint = new Color(0.84f, 0.98f, 0.72f), MapColor = new Color(0.12f, 0.36f, 0.10f)
            },
            new FloraNicheProfile
            {
                Id = FloraSpeciesId.LushSwordFern, SpeciesKey = "lush_sword_fern", DisplayName = "Dương Xỉ Rừng Xòe Rộng",
                Layer = FloraLayer.HerbGround, Stem = StemGroup.HerbaceousGround, Architecture = FloraArchitecture.ArchSoftTallHerb,
                IdealTempC = 18.5f, TempToleranceC = 11.0f, IdealMoisture = 0.68f, MoistureTolerance = 0.28f,
                MinGroundwater = 0.0f, MaxWindSpeedMs = 19.0f, MaxSlopeDeg = 30.0f, MinSoilDepth = 0.10f, SalinityTolerance = 0.18f,
                SoilAffinity = new[] { 1.0f, 1.0f, 0.25f, 0.01f, 0.05f, 0.12f },
                LightMin = 0.0f, LightMax = 0.72f, CrownRadiusM = 1.4f, HeightMinM = 0.8f, HeightMaxM = 1.5f, WindStiffness = 0.30f,
                BaseTint = new Color(0.92f, 1.08f, 0.84f), MapColor = new Color(0.16f, 0.46f, 0.13f)
            },
        };
    }
}
