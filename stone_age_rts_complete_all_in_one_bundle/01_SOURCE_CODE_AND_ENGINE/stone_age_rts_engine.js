// Bản độc lập tải từ thư mục 02_SLICED_SPRITES_128_PNG hoặc dùng trực tiếp trong file HTML All-in-One
const ASSET_URLS = window.STONE_AGE_ASSET_URLS || {};

    const IMAGES = {};
    let loadedCount = 0;
    const totalAssets = Object.keys(ASSET_URLS).length;

    function preloadAssets(onComplete) {
      for (const [key, dataUri] of Object.entries(ASSET_URLS)) {
        const img = new Image();
        img.onload = () => { if (++loadedCount === totalAssets) onComplete(); };
        img.onerror = () => { if (++loadedCount === totalAssets) onComplete(); };
        img.src = dataUri;
        IMAGES[key] = img;
      }
    }

    document.getElementById('uiIconMeat').src = ASSET_URLS.icon_meat;
    document.getElementById('uiIconBerry').src = ASSET_URLS.icon_berry;
    document.getElementById('uiIconFlint').src = ASSET_URLS.icon_flint;
    document.getElementById('uiIconWood').src = ASSET_URLS.icon_wood;
    document.getElementById('uiIconFire').src = ASSET_URLS.icon_fire;
    document.getElementById('minimapFrameImg').src = ASSET_URLS.minimap_ring;

    // =========================================================================
    // 1. MULTI-FRAME ANIMATION TABLE FOR ALL NPC ROLES & WILDLIFE
    // =========================================================================
    const ROLE_ANIM_FRAMES = {
      gatherer: {
        idle: ['gath_idle'],
        walk: ['gath_walk1', 'gath_idle', 'gath_walk2', 'gath_walk3'],
        walkBack: ['gath_walk_back', 'gath_carry_back'],
        work: ['gath_chop', 'gath_walk1', 'pioneer_build1', 'pioneer_build2'],
        carryWood: ['gath_carry_wood', 'gath_walk2'],
        carryBerry: ['gath_carry_berry', 'gath_carry_back']
      },
      woodcutter: {
        idle: ['gath_walk2'],
        walk: ['gath_walk1', 'gath_walk2', 'gath_walk3', 'gath_idle'],
        walkBack: ['gath_walk_back', 'gath_carry_wood'],
        work: ['pioneer_chop1', 'gath_chop', 'pioneer_chop2', 'gath_walk1'],
        carryWood: ['gath_carry_wood', 'gath_walk2'],
        carryBerry: ['gath_carry_berry', 'gath_carry_wood']
      },
      miner: {
        idle: ['gath_idle'],
        walk: ['gath_walk1', 'gath_walk3', 'gath_walk2'],
        walkBack: ['gath_walk_back'],
        work: ['gath_chop', 'pioneer_build1', 'gath_chop', 'pioneer_build2'],
        carryWood: ['gath_carry_wood', 'gath_walk1'],
        carryBerry: ['gath_carry_berry', 'gath_walk1']
      },
      warrior: {
        idle: ['war_idle', 'war_guard'],
        walk: ['war_walk1', 'war_idle', 'war_walk2', 'war_guard'],
        walkBack: ['war_walk1', 'war_walk2'],
        work: ['war_swing', 'war_smash', 'war_guard', 'war_idle'],
        carryWood: ['war_walk1', 'war_walk2'],
        carryBerry: ['war_walk1', 'war_walk2']
      },
      hunter: {
        idle: ['hunt_crouch', 'hunt_walk1'],
        walk: ['hunt_walk1', 'hunt_walk2', 'hunt_walk3', 'hunt_walk2'],
        walkBack: ['hunt_walk2', 'hunt_walk3'],
        work: ['hunt_thrust', 'hunt_lunge', 'hunt_throw', 'hunt_walk1'],
        carryWood: ['hunt_walk1', 'hunt_walk2'],
        carryBerry: ['hunt_walk1', 'hunt_walk2']
      },
      scout: {
        idle: ['scout_idle', 'scout_look'],
        walk: ['scout_run1', 'scout_run2', 'scout_idle', 'scout_run2'],
        walkBack: ['scout_run1', 'scout_run2'],
        work: ['scout_look', 'scout_horn', 'pioneer_build1', 'pioneer_build2'],
        carryWood: ['scout_run1', 'scout_run2'],
        carryBerry: ['scout_run1', 'scout_run2']
      },
      shaman: {
        idle: ['sha_torch', 'sha_idle'],
        walk: ['sha_walk1', 'sha_torch', 'sha_walk2', 'sha_idle'],
        walkBack: ['sha_walk1', 'sha_walk2'],
        work: ['sha_chant', 'sha_torch', 'sha_idle'],
        carryWood: ['sha_walk1', 'sha_walk2'],
        carryBerry: ['sha_walk1', 'sha_walk2']
      }
    };

    const WILDLIFE_ANIM_FRAMES = {
      boar: ['boar_1', 'boar_2', 'boar_3', 'boar_2'],
      bison: ['bison_1', 'bison_2', 'bison_3', 'bison_2'],
      mammoth: ['mammoth_1', 'mammoth_2', 'mammoth_3', 'mammoth_2'],
      smilodon: ['smilodon_1', 'smilodon_2', 'smilodon_3', 'smilodon_2']
    };

    // =========================================================================
    // 2. PROCEDURAL 200x200 WORLD GENERATOR
    // =========================================================================
    const MAP_W = 200;
    const MAP_H = 200;
    const TILE_PX = 48;
    const CAMP_POS = { x: 98.0, y: 97.5 };
    const HEARTH_POS = { x: 98.0, y: 99.0 };

    const BIOMES = { WATER: 0, SWAMP: 1, STEPPE: 2, FOREST: 3, HIGHLAND: 4, TUNDRA: 5 };
    const ECOTONES = { NONE: 0, SHORE: 1, WOODLAND: 2, FOOTHILL: 3, TAIGA: 4, MARSH: 5 };

    const stockpile = { meat: 145, berry: 210, flint: 85, wood: 320 };
    function updateStockpileUI() {
      document.getElementById('resMeat').textContent = Math.floor(stockpile.meat);
      document.getElementById('resBerry').textContent = Math.floor(stockpile.berry);
      document.getElementById('resFlint').textContent = Math.floor(stockpile.flint);
      document.getElementById('resWood').textContent = Math.floor(stockpile.wood);
    }

    function hash2(x, y) {
      let n = Math.sin(x * 127.1 + y * 311.7) * 43758.5453123;
      return n - Math.floor(n);
    }

    function smoothNoise(x, y) {
      const xi = Math.floor(x), yi = Math.floor(y);
      const xf = x - xi, yf = y - yi;
      const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
      const a = hash2(xi, yi), b = hash2(xi + 1, yi);
      const c = hash2(xi, yi + 1), d = hash2(xi + 1, yi + 1);
      return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
    }

    function fbm(x, y, octaves = 4, scale = 0.025) {
      let val = 0, amp = 0.5, freq = scale, maxAmp = 0;
      for (let i = 0; i < octaves; i++) {
        val += smoothNoise(x * freq, y * freq) * amp;
        maxAmp += amp;
        amp *= 0.5;
        freq *= 2.02;
      }
      return val / maxAmp;
    }

    function warpedFbm(x, y, scale = 0.018) {
      const qx = fbm(x + 15.3, y + 28.7, 3, scale) - 0.5;
      const qy = fbm(x + 73.1, y + 41.9, 3, scale) - 0.5;
      return fbm(x + qx * 20, y + qy * 20, 4, scale);
    }

    const world = [];
    const staticBuildings = [];
    const resourceNodes = [];
    const wildlifeList = [];
    const npcVillagers = [];
    const constructionSites = [];

    // Particle & Projectile Motion FX lists
    const vfxParticles = []; // Footstep dust, water ripples, wood chips, flint sparks, blood/berry puffs
    const projectiles = [];  // Thrown hunting spears in flight

    let autoTribeAI = true;
    let nextEntityId = 1;

    function spawnParticles(x, y, kind, count = 5) {
      for (let i = 0; i < count; i++) {
        const ang = Math.random() * Math.PI * 2;
        const spd = 0.015 + Math.random() * 0.045;
        vfxParticles.push({
          x,
          y,
          vx: Math.cos(ang) * spd,
          vy: Math.sin(ang) * spd - (kind === 'dust' ? 0.01 : 0.03),
          z: 0,
          vz: 0.04 + Math.random() * 0.05,
          kind, // 'dust', 'ripple', 'woodchip', 'spark', 'berry', 'hit'
          age: 0,
          maxAge: kind === 'ripple' ? 26 : (16 + Math.floor(Math.random() * 12))
        });
      }
    }

    function generateWorldData() {
      world.length = 0;
      staticBuildings.length = 0;
      resourceNodes.length = 0;
      wildlifeList.length = 0;
      npcVillagers.length = 0;
      constructionSites.length = 0;

      for (let y = 0; y < MAP_H; y++) {
        const row = [];
        const lat = y / (MAP_H - 1);
        for (let x = 0; x < MAP_W; x++) {
          const lon = x / (MAP_W - 1);
          const we = warpedFbm(x, y, 0.018);
          const wm = warpedFbm(x + 200, y + 200, 0.020);

          const distCenter = Math.hypot((x - 100) / MAP_W, (y - 100) / MAP_H);
          const centerFlat = Math.exp(-Math.pow(distCenter / 0.22, 2));
          const westHigh = Math.pow(Math.max(0, (0.36 - lon) / 0.36), 1.35) * 0.34;
          const northIce = Math.pow(Math.max(0, (0.32 - lat) / 0.32), 1.3) * 0.28;
          const eastHumid = Math.pow(Math.max(0, (lon - 0.48) / 0.52), 1.15) * 0.36;
          const coastWave = Math.sin(lon * Math.PI * 3.0) * 0.04;
          const southSea = Math.pow(Math.max(0, (lat - (0.78 + coastWave)) / 0.22), 1.25) * 0.68;

          let elev = we * 0.74 + 0.12 + westHigh + northIce - southSea;
          elev = elev * (1 - 0.58 * centerFlat) + 0.48 * (0.58 * centerFlat);
          elev = Math.max(0, Math.min(1, elev));

          let moist = wm * 0.70 + 0.14 + eastHumid - westHigh * 0.65 + southSea * 0.35;
          moist = Math.max(0, Math.min(1, moist));
          let tempC = 14 + (lat - 0.45) * 26 - northIce * 22 - Math.max(0, elev - 0.55) * 24;

          row.push({
            x, y, elev, moist, tempC,
            tier: 3,
            biome: BIOMES.STEPPE,
            ecotone: ECOTONES.NONE,
            cliffSouth: 0,
            isCliffEdge: false,
            isRamp: false,
            isFord: false,
            trail: null,
            gwDepth: Math.max(0, Math.min(1, (elev - moist * 0.45) * 1.4)),
            fow: 0,
            grassSeed: hash2(x * 3, y * 7)
          });
        }
        world.push(row);
      }

      const lakes = [
        [64, 34, 13.5, 10.5],
        [116, 96, 9.5, 8.5],
        [158, 118, 15.0, 12.5],
        [48, 126, 10.5, 8.5],
        [148, 44, 10.0, 8.0],
        [82, 112, 4.5, 3.8],
        [76, 62, 4.2, 3.5],
        [136, 72, 4.8, 4.0],
        [134, 146, 5.2, 4.2]
      ];
      for (const [lx, ly, rx, ry] of lakes) carveLake(lx, ly, rx, ry);

      carveStream(104, 2, 107, 96, 2.1, 5.0, 0.4);
      carveStream(107, 96, 106, 150, 2.2, 5.0, 1.8);
      carveStream(106, 150, 74, 194, 1.6, 3.5, 0.5);
      carveStream(106, 150, 108, 196, 2.0, 3.0, 1.2);
      carveStream(106, 150, 142, 192, 1.6, 4.0, 2.4);
      carveStream(64, 34, 105, 62, 1.35, 4.2, 0.7);
      carveStream(148, 44, 116, 96, 1.30, 4.8, 1.5);
      carveStream(48, 126, 106, 138, 1.35, 5.0, 2.1);
      carveStream(52, 78, 106, 86, 1.15, 3.8, 0.9);
      carveStream(120, 96, 158, 118, 1.40, 4.0, 1.1);
      carveStream(158, 118, 166, 186, 1.55, 4.5, 2.6);

      for (let y = 0; y < MAP_H; y++) {
        const lat = y / (MAP_H - 1);
        for (let x = 0; x < MAP_W; x++) {
          const lon = x / (MAP_W - 1);
          const t = world[y][x];
          if (t.elev < 0.26) {
            t.biome = BIOMES.WATER;
            t.tier = t.elev < 0.20 ? 0 : 1;
          } else {
            if (t.tempC < 1.5 && t.elev >= 0.42) t.biome = BIOMES.TUNDRA;
            else if (t.elev >= 0.63 && (t.moist < 0.52 || lon < 0.42)) t.biome = BIOMES.HIGHLAND;
            else if (t.elev < 0.43 && t.moist >= 0.58 && lat > 0.25) t.biome = BIOMES.SWAMP;
            else if (t.moist >= 0.53 && lon > 0.44) t.biome = BIOMES.FOREST;
            else t.biome = BIOMES.STEPPE;

            if (t.elev < 0.42) t.tier = 2;
            else if (t.elev < 0.62) t.tier = 3;
            else if (t.elev < 0.77) t.tier = 4;
            else t.tier = 5;
          }
        }
      }

      for (let y = 88; y <= 112; y++) {
        for (let x = 86; x <= 112; x++) {
          const d = Math.hypot(x - 98, y - 100);
          const t = world[y][x];
          if (d <= 10 && t.biome !== BIOMES.WATER) {
            t.biome = BIOMES.STEPPE;
            t.tier = 3;
            t.elev = 0.48;
          }
        }
      }

      for (let y = 1; y < MAP_H - 1; y++) {
        for (let x = 1; x < MAP_W - 1; x++) {
          const t = world[y][x];
          if (t.biome === BIOMES.WATER) continue;
          const southTier = world[y + 1][x].tier;
          t.cliffSouth = southTier >= 2 ? Math.max(0, t.tier - southTier) : 0;

          const minNb = Math.min(
            world[y - 1][x].tier, world[y + 1][x].tier,
            world[y][x - 1].tier, world[y][x + 1].tier
          );
          if (t.tier > minNb && minNb >= 2) {
            if (((x * 3 + y * 5) % 20) <= 2 && t.tier - minNb === 1) t.isRamp = true;
            else t.isCliffEdge = true;
          }

          let hasWater = false, hasForest = false, hasHigh = false, hasTundra = false, hasSwamp = false;
          for (let dy = -1; dy <= 1; dy++) {
            for (let dx = -1; dx <= 1; dx++) {
              const nb = world[y + dy][x + dx].biome;
              if (nb === BIOMES.WATER) hasWater = true;
              if (nb === BIOMES.FOREST) hasForest = true;
              if (nb === BIOMES.HIGHLAND) hasHigh = true;
              if (nb === BIOMES.TUNDRA) hasTundra = true;
              if (nb === BIOMES.SWAMP) hasSwamp = true;
            }
          }
          if (hasWater) t.ecotone = t.biome === BIOMES.SWAMP ? ECOTONES.MARSH : ECOTONES.SHORE;
          else if (t.biome === BIOMES.STEPPE) {
            if (hasHigh || t.isCliffEdge) t.ecotone = ECOTONES.FOOTHILL;
            else if (hasTundra) t.ecotone = ECOTONES.TAIGA;
            else if (hasForest) t.ecotone = ECOTONES.WOODLAND;
            else if (hasSwamp) t.ecotone = ECOTONES.MARSH;
          }
        }
      }

      populateTribeBuildingsResourcesAndNPCs();
      revealVisionAt(98, 100, 16);
    }

    function carveLake(cx, cy, rx, ry) {
      const pad = 6;
      for (let y = Math.max(2, Math.floor(cy - ry - pad)); y <= Math.min(MAP_H - 3, Math.ceil(cy + ry + pad)); y++) {
        for (let x = Math.max(2, Math.floor(cx - rx - pad)); x <= Math.min(MAP_W - 3, Math.ceil(cx + rx + pad)); x++) {
          const d = Math.hypot((x - cx) / rx, (y - cy) / ry) + (fbm(x * 1.4, y * 1.4, 2, 0.08) - 0.5) * 0.35;
          const t = world[y][x];
          if (d <= 0.72) { t.elev = 0.14; t.moist = 1.0; }
          else if (d <= 1.0) { t.elev = 0.23; t.moist = 1.0; }
          else if (d <= 1.35 && t.elev >= 0.26) { t.elev = Math.min(t.elev, 0.38 + (d - 1.0) * 0.3); }
        }
      }
    }

    function carveStream(sx, sy, ex, ey, halfW, amp, phase) {
      const steps = Math.ceil(Math.hypot(ex - sx, ey - sy) * 1.6);
      const len = Math.max(1, Math.hypot(ex - sx, ey - sy));
      const nx = -(ey - sy) / len, ny = (ex - sx) / len;
      for (let i = 0; i <= steps; i++) {
        const u = i / steps;
        const env = Math.sin(u * Math.PI);
        const wave = Math.sin(u * Math.PI * 3.5 + phase) * amp * env;
        const cx = sx + (ex - sx) * u + nx * wave;
        const cy = sy + (ey - sy) * u + ny * wave;
        const isFord = (i % 26 >= 11 && i % 26 <= 14) || (Math.abs(cy - 100) <= 2.5 && Math.abs(cx - 105) <= 5);
        const r = Math.ceil(halfW + 2);
        for (let dy = -r; dy <= r; dy++) {
          for (let dx = -r; dx <= r; dx++) {
            const px = Math.round(cx) + dx, py = Math.round(cy) + dy;
            if (px < 1 || px >= MAP_W - 1 || py < 1 || py >= MAP_H - 1) continue;
            const d = Math.hypot(px - cx, py - cy);
            const t = world[py][px];
            if (d <= halfW) {
              if (isFord || d >= halfW - 0.55) {
                t.elev = 0.23;
                if (isFord) t.isFord = true;
              } else {
                t.elev = 0.15;
              }
              t.moist = 1.0;
            }
          }
        }
      }
    }

    function populateTribeBuildingsResourcesAndNPCs() {
      staticBuildings.push(
        { id: nextEntityId++, type: 'shelter', x: 98.0, y: 97.2, scale: 2.35, label: 'Hang Đá Cội Nguồn (Kho Bộ Lạc)', isLight: true, lightRadius: 6.5 },
        { id: nextEntityId++, type: 'tipis', x: 94.2, y: 98.4, scale: 1.75, label: 'Lều Da Thú' },
        { id: nextEntityId++, type: 'racks', x: 102.5, y: 97.8, scale: 1.55, label: 'Giàn Phơi & Hun Khói' },
        { id: nextEntityId++, type: 'shrine', x: 94.5, y: 103.5, scale: 1.85, label: 'Đàn Tế Cự Thạch', isLight: true, lightRadius: 4.2 },
        { id: nextEntityId++, type: 'workshop', x: 100.5, y: 103.8, scale: 1.65, label: 'Xưởng Ghè Đá Lửa' },
        { id: nextEntityId++, type: 'palisade', x: 103.8, y: 101.8, scale: 1.85, label: 'Cổng Rào & Tháp Canh' },
        { id: nextEntityId++, type: 'cairn', x: 98.2, y: 103.4, scale: 0.95, label: 'Cột Đá Tập Kết' }
      );

      const starterResources = [
        { type: 'berries_red', resType: 'berry', name: 'Bụi Quả Mọng Đỏ', x: 93.0, y: 98.0, amount: 45, scale: 0.95 },
        { type: 'berries_red', resType: 'berry', name: 'Bụi Quả Mọng Đỏ', x: 93.8, y: 99.3, amount: 45, scale: 0.95 },
        { type: 'berries_dark', resType: 'berry', name: 'Bụi Quả Cơm Cháy', x: 92.6, y: 99.6, amount: 45, scale: 0.95 },
        { type: 'berries_gold', resType: 'berry', name: 'Bụi Mâm Xôi Vàng', x: 100.4, y: 101.2, amount: 45, scale: 0.92 },
        { type: 'mushroom_red', resType: 'berry', name: 'Nấm Đốm Cổ Đại', x: 94.2, y: 96.4, amount: 35, scale: 0.90 },
        { type: 'mushroom_red', resType: 'berry', name: 'Nấm Đốm Cổ Đại', x: 95.3, y: 96.4, amount: 35, scale: 0.90 },
        { type: 'tree_oak', resType: 'wood', name: 'Sồi Cổ Thụ', x: 92.5, y: 101.2, amount: 80, scale: 1.45 },
        { type: 'tree_oak', resType: 'wood', name: 'Sồi Cổ Thụ', x: 91.2, y: 97.5, amount: 80, scale: 1.45 },
        { type: 'tree_fern', resType: 'wood', name: 'Dương Xỉ Thân Gỗ', x: 96.5, y: 104.6, amount: 70, scale: 1.40 },
        { type: 'logs', resType: 'wood', name: 'Gỗ Khô Xếp Chồng', x: 93.5, y: 96.5, amount: 40, scale: 0.80 },
        { type: 'logs', resType: 'wood', name: 'Gỗ Khô Xếp Chồng', x: 101.2, y: 96.6, amount: 40, scale: 0.80 },
        { type: 'flint_node', resType: 'flint', name: 'Vỉa Đá Lửa Lộ Thiên', x: 90.8, y: 99.2, amount: 65, scale: 0.85 },
        { type: 'flint_node', resType: 'flint', name: 'Vỉa Đá Lửa Lộ Thiên', x: 101.8, y: 104.2, amount: 65, scale: 0.85 }
      ];
      for (const r of starterResources) {
        resourceNodes.push({ id: nextEntityId++, maxAmount: r.amount, hitShake: 0, ...r });
      }

      wildlifeList.push(
        { id: nextEntityId++, species: 'boar', type: 'boar_1', name: 'Lợn Lòi Tiền Sử', x: 104.8, y: 103.5, hp: 60, maxHp: 60, meat: 50, scale: 1.15, vx: 0, vy: 0, facing: -1, stridePhase: 0, isMoving: false, hitShake: 0 },
        { id: nextEntityId++, species: 'bison', type: 'bison_1', name: 'Bò Rừng Thảo Nguyên', x: 91.5, y: 104.2, hp: 90, maxHp: 90, meat: 80, scale: 1.25, vx: 0, vy: 0, facing: 1, stridePhase: 1.2, isMoving: false, hitShake: 0 }
      );

      const initialNpcs = [
        { name: 'Grok (Dân Hái Lượm)', role: 'gatherer', x: 96.5, y: 99.2, selected: true, defaultJob: 'forage' },
        { name: 'Ooga (Dân Hái Quả)', role: 'gatherer', x: 100.8, y: 99.4, selected: true, defaultJob: 'forage' },
        { name: 'Thag (Thợ Đốn Củi)', role: 'woodcutter', x: 95.2, y: 100.2, selected: true, defaultJob: 'chop' },
        { name: 'Bruk (Thợ Đập Đá)', role: 'miner', x: 98.4, y: 101.0, selected: false, defaultJob: 'mine' },
        { name: 'Korg (Chùy Xương)', role: 'warrior', x: 96.6, y: 96.8, selected: false, defaultJob: 'hunt' },
        { name: 'Atlatl (Thợ Săn Lao)', role: 'hunter', x: 102.4, y: 101.2, selected: false, defaultJob: 'hunt' },
        { name: 'Tala (Trinh Sát Mù)', role: 'scout', x: 99.6, y: 102.4, selected: false, defaultJob: 'scout', isLight: true, lightRadius: 5.5 },
        { name: 'Zog (Pháp Sư Lửa)', role: 'shaman', x: 95.2, y: 102.8, selected: false, defaultJob: 'tend_fire', isLight: true, lightRadius: 5.0 }
      ];

      for (const u of initialNpcs) {
        npcVillagers.push({
          id: nextEntityId++,
          name: u.name,
          role: u.role,
          type: 'gath_idle',
          x: u.x,
          y: u.y,
          vx: 0,
          vy: 0,
          facing: 1,         // 1 = right, -1 = left
          facingUp: false,   // true when walking northward (shows back frames)
          isMoving: false,
          stridePhase: Math.random() * Math.PI * 2,
          lastFootStepIdx: 0,
          actionSwingPhase: 0,
          scale: 1.08,
          selected: u.selected,
          defaultJob: u.defaultJob,
          state: 'IDLE',
          thoughtBubble: 'Đang chờ lệnh...',
          targetX: u.x,
          targetY: u.y,
          targetEntity: null,
          targetSite: null,
          carryType: null,
          carryAmount: 0,
          maxCarry: 10,
          hunger: 80 + Math.random() * 20,
          warmth: 85 + Math.random() * 15,
          workTimer: 0,
          idleTimer: 10 + Math.floor(Math.random() * 25),
          isLight: u.isLight || false,
          lightRadius: u.lightRadius || 0
        });
      }

      for (let y = 4; y < MAP_H - 4; y += 2) {
        for (let x = 4; x < MAP_W - 4; x += 2) {
          if (Math.hypot(x - 98, y - 100) < 11) continue;
          const t = world[y][x];
          if (t.biome === BIOMES.WATER) continue;
          const r = hash2(x * 19, y * 23);
          const grove = fbm(x, y, 3, 0.07);

          if ((t.biome === BIOMES.TUNDRA || t.biome === BIOMES.HIGHLAND) && t.isRamp && r < 0.08) {
            staticBuildings.push({ id: nextEntityId++, type: 'geyser', x: x + 0.5, y: y + 0.5, scale: 1.5, label: 'Suối Nước Nóng (+18°C)', isLight: true, lightRadius: 6.0 });
            continue;
          }
          if (t.ecotone === ECOTONES.FOOTHILL && t.gwDepth < 0.22 && r < 0.05) {
            staticBuildings.push({ id: nextEntityId++, type: 'spring', x: x + 0.5, y: y + 0.5, scale: 1.35, label: 'Mạch Nước Ngầm' });
            continue;
          }

          if (t.biome === BIOMES.FOREST && grove > 0.45 && r < 0.48) {
            resourceNodes.push({
              id: nextEntityId++,
              type: r < 0.24 ? 'tree_fern' : 'tree_oak',
              resType: 'wood',
              name: 'Cây Rừng Nguyên Sinh',
              x: x + (r - 0.5) * 0.5,
              y: y + 0.4,
              amount: 75,
              maxAmount: 75,
              hitShake: 0,
              scale: 1.35 + (r % 0.25)
            });
          } else if (t.biome === BIOMES.TUNDRA && grove > 0.52 && r < 0.24) {
            resourceNodes.push({
              id: nextEntityId++,
              type: 'tree_pine',
              resType: 'wood',
              name: 'Thông Tuyết Bắc Cực',
              x: x + 0.3,
              y: y + 0.4,
              amount: 65,
              maxAmount: 65,
              hitShake: 0,
              scale: 1.35
            });
          } else if (t.ecotone === ECOTONES.SHORE && r < 0.20) {
            resourceNodes.push({
              id: nextEntityId++,
              type: 'reeds',
              resType: 'wood',
              name: 'Bụi Sậy Ven Sông',
              x: x + 0.4,
              y: y + 0.4,
              amount: 35,
              maxAmount: 35,
              hitShake: 0,
              scale: 0.95
            });
          } else if (t.biome === BIOMES.STEPPE && r < 0.06) {
            resourceNodes.push({
              id: nextEntityId++,
              type: r < 0.03 ? 'berries_red' : 'grain',
              resType: 'berry',
              name: r < 0.03 ? 'Bụi Quả Mọng' : 'Lúa Mì Hoang Einkorn',
              x: x + 0.4,
              y: y + 0.4,
              amount: 45,
              maxAmount: 45,
              hitShake: 0,
              scale: 0.92
            });
          } else if (t.ecotone === ECOTONES.FOOTHILL && r > 0.94) {
            resourceNodes.push({
              id: nextEntityId++,
              type: 'flint_node',
              resType: 'flint',
              name: 'Mỏ Đá Lửa Chân Núi',
              x: x + 0.4,
              y: y + 0.4,
              amount: 80,
              maxAmount: 80,
              hitShake: 0,
              scale: 0.85
            });
          } else if (r > 0.985) {
            if (t.biome === BIOMES.TUNDRA) {
              wildlifeList.push({ id: nextEntityId++, species: 'mammoth', type: 'mammoth_1', name: 'Voi Ma Mút Lông Xù', x, y, hp: 180, maxHp: 180, meat: 160, scale: 1.45, vx: 0, vy: 0, facing: 1, stridePhase: 0, isMoving: false, hitShake: 0 });
            } else if (t.biome === BIOMES.STEPPE) {
              wildlifeList.push({ id: nextEntityId++, species: 'bison', type: 'bison_1', name: 'Bò Rừng Thảo Nguyên', x, y, hp: 90, maxHp: 90, meat: 80, scale: 1.25, vx: 0, vy: 0, facing: -1, stridePhase: 0, isMoving: false, hitShake: 0 });
            } else if (t.biome === BIOMES.HIGHLAND && Math.hypot(x - 98, y - 100) > 25) {
              wildlifeList.push({ id: nextEntityId++, species: 'smilodon', type: 'smilodon_1', name: 'Hổ Răng Kiếm', x, y, hp: 110, maxHp: 110, meat: 65, scale: 1.15, vx: 0, vy: 0, facing: 1, stridePhase: 0, isMoving: false, hitShake: 0 });
            }
          }
        }
      }
      renderNpcRosterPanel();
    }

    function revealVisionAt(cx, cy, radius) {
      const r2 = radius * radius;
      for (let y = Math.max(0, Math.floor(cy - radius)); y <= Math.min(MAP_H - 1, Math.ceil(cy + radius)); y++) {
        for (let x = Math.max(0, Math.floor(cx - radius)); x <= Math.min(MAP_W - 1, Math.ceil(cx + radius)); x++) {
          if ((x - cx) * (x - cx) + (y - cy) * (y - cy) <= r2) {
            world[y][x].fow = 2;
          }
        }
      }
    }

    // =========================================================================
    // 3. NPC & WILDLIFE MOTION KINEMATICS + FSM
    // =========================================================================
    function findNearestResource(npc, resTypeFilter = null, maxDist = 28) {
      let best = null, bestDist = maxDist;
      for (const node of resourceNodes) {
        if (node.amount <= 0) continue;
        if (resTypeFilter && node.resType !== resTypeFilter) continue;
        const tx = Math.floor(node.x), ty = Math.floor(node.y);
        if (!world[ty] || !world[ty][tx] || world[ty][tx].fow === 0) continue;
        const d = Math.hypot(node.x - npc.x, node.y - npc.y);
        if (d < bestDist) { bestDist = d; best = node; }
      }
      return best;
    }

    function findNearestWildlife(npc, maxDist = 22) {
      let best = null, bestDist = maxDist;
      for (const mob of wildlifeList) {
        if (mob.hp <= 0) continue;
        const tx = Math.floor(mob.x), ty = Math.floor(mob.y);
        if (!world[ty] || !world[ty][tx] || world[ty][tx].fow === 0) continue;
        const d = Math.hypot(mob.x - npc.x, mob.y - npc.y);
        if (d < bestDist) { bestDist = d; best = mob; }
      }
      return best;
    }

    function stepNpcTowards(npc, destX, destY, baseSpeed = 0.048) {
      const dx = destX - npc.x;
      const dy = destY - npc.y;
      const dist = Math.hypot(dx, dy);
      if (dist <= baseSpeed * 1.15) {
        npc.x = destX;
        npc.y = destY;
        npc.vx = 0;
        npc.vy = 0;
        npc.isMoving = false;
        return true;
      }

      const tx = Math.max(0, Math.min(MAP_W - 1, Math.floor(npc.x)));
      const ty = Math.max(0, Math.min(MAP_H - 1, Math.floor(npc.y)));
      const tile = world[ty][tx];

      let mult = 1.0;
      if (tile.trail === 'road' || tile.trail === 'bridge') mult = 1.50;
      else if (tile.biome === BIOMES.WATER) mult = 0.55;
      else if (tile.biome === BIOMES.SWAMP) mult = 0.68;

      const step = baseSpeed * mult;
      npc.vx = (dx / dist) * step;
      npc.vy = (dy / dist) * step;
      npc.x += npc.vx;
      npc.y += npc.vy;
      npc.isMoving = true;

      // Update directional facing & stride cycle phase
      if (Math.abs(npc.vx) > 0.004) {
        npc.facing = npc.vx < 0 ? -1 : 1;
      }
      npc.facingUp = (npc.vy < -0.025 && Math.abs(npc.vy) > Math.abs(npc.vx) * 0.85);
      npc.stridePhase += step * 5.2;

      // Trigger footstep dust or water splash on each foot strike (every PI radians)
      const stepIdx = Math.floor(npc.stridePhase / Math.PI);
      if (stepIdx !== npc.lastFootStepIdx) {
        npc.lastFootStepIdx = stepIdx;
        if (tile.biome === BIOMES.WATER && tile.trail !== 'bridge') {
          spawnParticles(npc.x, npc.y + 0.15, 'ripple', 1);
        } else {
          spawnParticles(npc.x - npc.vx * 2, npc.y + 0.15, 'dust', 2);
        }
      }

      revealVisionAt(npc.x, npc.y, npc.role === 'scout' ? 9 : 6);
      return false;
    }

    function selectCurrentAnimFrame(npc) {
      const bank = ROLE_ANIM_FRAMES[npc.role] || ROLE_ANIM_FRAMES.gatherer;
      if (npc.isMoving) {
        if (npc.carryAmount > 0) {
          const carryList = npc.carryType === 'wood' ? bank.carryWood : bank.carryBerry;
          const idx = Math.floor(npc.stridePhase / 1.4) % carryList.length;
          return carryList[idx];
        }
        if (npc.facingUp && bank.walkBack && bank.walkBack.length > 0) {
          const idx = Math.floor(npc.stridePhase / 1.4) % bank.walkBack.length;
          return bank.walkBack[idx];
        }
        const idx = Math.floor(npc.stridePhase / 1.25) % bank.walk.length;
        return bank.walk[idx];
      }
      if (npc.state === 'HARVESTING' || npc.state === 'BUILDING' || npc.state === 'HUNTING') {
        const idx = Math.floor(npc.actionSwingPhase / 1.3) % bank.work.length;
        return bank.work[idx];
      }
      const idleIdx = Math.floor((animTick + npc.id * 17) / 45) % bank.idle.length;
      return bank.idle[idleIdx];
    }

    function updateAllNpcsAndWildlife() {
      const isWinter = currentSeasonIdx === 3;

      // 1. Update Wildlife movement & multi-frame walk cycle
      for (const mob of wildlifeList) {
        if (mob.hp <= 0) continue;
        if (mob.hitShake > 0) mob.hitShake--;
        if (Math.random() < 0.025) {
          const ang = Math.random() * Math.PI * 2;
          mob.vx = Math.cos(ang) * 0.022;
          mob.vy = Math.sin(ang) * 0.022;
        } else if (Math.random() < 0.03) {
          mob.vx = 0;
          mob.vy = 0;
        }
        const spd = Math.hypot(mob.vx, mob.vy);
        mob.isMoving = spd > 0.002;
        if (mob.isMoving) {
          const nx = Math.max(4, Math.min(MAP_W - 5, mob.x + mob.vx));
          const ny = Math.max(4, Math.min(MAP_H - 5, mob.y + mob.vy));
          if (world[Math.floor(ny)][Math.floor(nx)].biome !== BIOMES.WATER) {
            mob.x = nx;
            mob.y = ny;
          }
          if (Math.abs(mob.vx) > 0.002) mob.facing = mob.vx < 0 ? 1 : -1;
          mob.stridePhase += spd * 6.0;
          const frames = WILDLIFE_ANIM_FRAMES[mob.species] || WILDLIFE_ANIM_FRAMES.boar;
          mob.type = frames[Math.floor(mob.stridePhase / 1.3) % frames.length];
        } else {
          const frames = WILDLIFE_ANIM_FRAMES[mob.species] || WILDLIFE_ANIM_FRAMES.boar;
          mob.type = frames[0];
        }
      }

      // 2. Decay resource node hit shake
      for (const r of resourceNodes) {
        if (r.hitShake > 0) r.hitShake--;
      }

      // 3. Update Flying Spear Projectiles
      for (let i = projectiles.length - 1; i >= 0; i--) {
        const p = projectiles[i];
        p.progress += 0.085;
        if (p.progress >= 1.0) {
          spawnParticles(p.tx, p.ty, 'hit', 6);
          projectiles.splice(i, 1);
        }
      }

      // 4. Update VFX Particles
      for (let i = vfxParticles.length - 1; i >= 0; i--) {
        const pt = vfxParticles[i];
        pt.age++;
        if (pt.age >= pt.maxAge) {
          vfxParticles.splice(i, 1);
          continue;
        }
        pt.x += pt.vx;
        pt.y += pt.vy;
        pt.z = Math.max(0, pt.z + pt.vz);
        pt.vz -= 0.006;
      }

      // 5. Update NPC Villagers FSM & Motion
      for (const npc of npcVillagers) {
        npc.hunger = Math.max(0, npc.hunger - 0.012);
        const distHearth = Math.hypot(npc.x - HEARTH_POS.x, npc.y - HEARTH_POS.y);
        if (distHearth <= 6.5) npc.warmth = Math.min(100, npc.warmth + 0.25);
        else npc.warmth = Math.max(0, npc.warmth - (isWinter ? 0.065 : 0.01));

        if ((npc.warmth < 25 || npc.hunger < 20) && npc.state !== 'WARMING_UP') {
          npc.state = 'WARMING_UP';
          npc.thoughtBubble = npc.warmth < 25 ? '🥶 Lạnh cóng! Chạy về lửa trại!' : '🍖 Đói bụng! Về hang ăn!';
        }

        switch (npc.state) {
          case 'WARMING_UP': {
            const arrived = stepNpcTowards(npc, HEARTH_POS.x + (npc.id % 3 - 1) * 1.1, HEARTH_POS.y + 0.6);
            if (arrived) {
              npc.warmth = Math.min(100, npc.warmth + 0.6);
              npc.hunger = Math.min(100, npc.hunger + 0.7);
              npc.thoughtBubble = '🔥 Đang sưởi ấm & ăn tại trại...';
              if (npc.warmth >= 92 && npc.hunger >= 90) {
                npc.state = 'IDLE';
                npc.thoughtBubble = 'Đã no ấm! Chờ lệnh Tù Trưởng';
              }
            }
            break;
          }

          case 'IDLE': {
            npc.isMoving = false;
            npc.idleTimer--;
            if (npc.idleTimer <= 0) {
              const openSite = constructionSites.find(s => !s.completed);
              if (openSite && autoTribeAI) {
                npc.targetSite = openSite;
                npc.state = 'BUILDING';
                npc.thoughtBubble = `🔨 Chạy đi xây ${openSite.label}...`;
                break;
              }

              if (autoTribeAI) {
                if (npc.defaultJob === 'forage') {
                  const bush = findNearestResource(npc, 'berry');
                  if (bush) { npc.targetEntity = bush; npc.state = 'HARVESTING'; npc.thoughtBubble = `🍒 Đi hái ${bush.name}`; break; }
                } else if (npc.defaultJob === 'chop') {
                  const tree = findNearestResource(npc, 'wood');
                  if (tree) { npc.targetEntity = tree; npc.state = 'HARVESTING'; npc.thoughtBubble = `🪓 Đi đốn ${tree.name}`; break; }
                } else if (npc.defaultJob === 'mine') {
                  const rock = findNearestResource(npc, 'flint');
                  if (rock) { npc.targetEntity = rock; npc.state = 'HARVESTING'; npc.thoughtBubble = `⛏️ Đi đập ${rock.name}`; break; }
                } else if (npc.defaultJob === 'hunt') {
                  const prey = findNearestWildlife(npc, 18);
                  if (prey) { npc.targetEntity = prey; npc.state = 'HUNTING'; npc.thoughtBubble = `🏹 Đi săn ${prey.name}`; break; }
                }
              }

              npc.targetX = Math.max(8, Math.min(MAP_W - 8, npc.x + (Math.random() - 0.5) * 6));
              npc.targetY = Math.max(8, Math.min(MAP_H - 8, npc.y + (Math.random() - 0.5) * 6));
              npc.state = 'WANDER';
              npc.thoughtBubble = '💭 Đi dạo quanh trại...';
            }
            break;
          }

          case 'WANDER': {
            const arrived = stepNpcTowards(npc, npc.targetX, npc.targetY, 0.032);
            if (arrived) {
              npc.state = 'IDLE';
              npc.idleTimer = 35 + Math.floor(Math.random() * 45);
              npc.thoughtBubble = 'Đứng quan sát quanh trại...';
            }
            break;
          }

          case 'MOVE_TO_TARGET': {
            const arrived = stepNpcTowards(npc, npc.targetX, npc.targetY, 0.056);
            if (arrived) {
              npc.state = 'IDLE';
              npc.idleTimer = 30;
              npc.thoughtBubble = 'Đã tới vị trí chỉ định!';
            }
            break;
          }

          case 'SCOUTING': {
            const arrived = stepNpcTowards(npc, npc.targetX, npc.targetY, 0.064);
            if (arrived) {
              staticBuildings.push({
                id: nextEntityId++,
                type: 'cairn',
                x: npc.x,
                y: npc.y,
                scale: 0.9,
                label: 'Cột Đá Trinh Sát'
              });
              bakeAllMapPreviewBuffers();
              npc.state = 'IDLE';
              npc.idleTimer = 30;
              npc.thoughtBubble = '🔦 Đã mở bản đồ & dựng cột đá!';
            }
            break;
          }

          case 'HARVESTING': {
            const node = npc.targetEntity;
            if (!node || node.amount <= 0) {
              if (npc.carryAmount > 0) {
                npc.state = 'RETURNING_DROP';
                npc.thoughtBubble = `🎒 Vác ${npc.carryAmount} đồ về Hang Đá`;
              } else {
                npc.state = 'IDLE';
                npc.idleTimer = 15;
              }
              break;
            }
            const arrived = stepNpcTowards(npc, node.x - 0.35, node.y + 0.25, 0.052);
            if (arrived) {
              npc.facing = node.x >= npc.x ? 1 : -1;
              npc.workTimer++;
              npc.actionSwingPhase += 0.22;
              const icon = node.resType === 'wood' ? '🪓' : (node.resType === 'flint' ? '⛏️' : '🍒');
              npc.thoughtBubble = `${icon} Đang khai thác (${npc.carryAmount}/${npc.maxCarry})...`;

              if (npc.workTimer % 16 === 0) {
                node.hitShake = 6; // Shake tree/bush/rock on impact!
                const pKind = node.resType === 'wood' ? 'woodchip' : (node.resType === 'flint' ? 'spark' : 'berry');
                spawnParticles(node.x, node.y, pKind, 5);

                const take = Math.min(2, node.amount, npc.maxCarry - npc.carryAmount);
                node.amount -= take;
                npc.carryType = node.resType;
                npc.carryAmount += take;
                if (node.amount <= 0) {
                  const idx = resourceNodes.indexOf(node);
                  if (idx !== -1) resourceNodes.splice(idx, 1);
                }
                if (npc.carryAmount >= npc.maxCarry || node.amount <= 0) {
                  npc.state = 'RETURNING_DROP';
                  npc.thoughtBubble = `🎒 Đầy túi (${npc.carryAmount})! Vác về Hang Đá`;
                }
              }
            }
            break;
          }

          case 'HUNTING': {
            const prey = npc.targetEntity;
            if (!prey || prey.hp <= 0) {
              if (npc.carryAmount > 0) {
                npc.state = 'RETURNING_DROP';
                npc.thoughtBubble = `🥩 Vác ${npc.carryAmount} Thịt về Hang Đá`;
              } else {
                npc.state = 'IDLE';
                npc.idleTimer = 20;
              }
              break;
            }
            const standRange = npc.role === 'hunter' ? 2.4 : 0.75;
            const distPrey = Math.hypot(prey.x - npc.x, prey.y - npc.y);
            if (distPrey > standRange) {
              stepNpcTowards(npc, prey.x, prey.y, 0.06);
            } else {
              npc.isMoving = false;
              npc.facing = prey.x >= npc.x ? 1 : -1;
              npc.workTimer++;
              npc.actionSwingPhase += 0.24;
              npc.thoughtBubble = `🏹 Đang tấn công ${prey.name} (HP: ${prey.hp})...`;
              if (npc.workTimer % 18 === 0) {
                if (npc.role === 'hunter') {
                  projectiles.push({ sx: npc.x, sy: npc.y - 0.4, tx: prey.x, ty: prey.y - 0.2, progress: 0 });
                } else {
                  spawnParticles(prey.x, prey.y, 'hit', 5);
                }
                prey.hitShake = 7;
                prey.hp -= (npc.role === 'warrior' || npc.role === 'hunter') ? 18 : 10;
                if (prey.hp <= 0) {
                  npc.carryType = 'meat';
                  npc.carryAmount = npc.maxCarry;
                  const idx = wildlifeList.indexOf(prey);
                  if (idx !== -1) wildlifeList.splice(idx, 1);
                  npc.state = 'RETURNING_DROP';
                  npc.thoughtBubble = `🥩 Đã hạ ${prey.name}! Vác thịt về kho`;
                }
              }
            }
            break;
          }

          case 'RETURNING_DROP': {
            const arrived = stepNpcTowards(npc, CAMP_POS.x, CAMP_POS.y + 0.8, 0.048);
            if (arrived) {
              if (npc.carryType && npc.carryAmount > 0) {
                stockpile[npc.carryType] = (stockpile[npc.carryType] || 0) + npc.carryAmount;
                updateStockpileUI();
              }
              npc.carryAmount = 0;
              npc.carryType = null;
              if (npc.targetEntity && npc.targetEntity.amount > 0) {
                npc.state = 'HARVESTING';
                npc.thoughtBubble = `Quay lại khai thác ${npc.targetEntity.name}`;
              } else {
                npc.state = 'IDLE';
                npc.idleTimer = 15;
                npc.thoughtBubble = 'Đã nộp vào kho! Chờ lệnh tiếp';
              }
            }
            break;
          }

          case 'BUILDING': {
            const site = npc.targetSite;
            if (!site || site.completed) {
              npc.state = 'IDLE';
              npc.idleTimer = 15;
              break;
            }
            const arrived = stepNpcTowards(npc, site.x + 0.5, site.y + 0.5, 0.056);
            if (arrived) {
              npc.actionSwingPhase += 0.25;
              site.progress = Math.min(100, site.progress + 2.5);
              if (Math.floor(site.progress) % 15 === 0) {
                spawnParticles(site.x + 0.5, site.y + 0.5, 'spark', 3);
              }
              npc.thoughtBubble = `🔨 Đang xây ${site.label} (${Math.floor(site.progress)}%)...`;
              if (site.progress >= 100) {
                site.completed = true;
                completeConstructionSite(site);
                npc.state = 'IDLE';
                npc.idleTimer = 15;
                npc.thoughtBubble = `✅ Đã xây xong ${site.label}!`;
              }
            }
            break;
          }
        }

        // Update current animation frame sprite key
        npc.type = selectCurrentAnimFrame(npc);
      }

      if (animTick % 30 === 0) {
        const idleCount = npcVillagers.filter(u => u.state === 'IDLE' || u.state === 'WANDER').length;
        document.getElementById('lblIdleCount').textContent = idleCount;
        renderNpcRosterPanel();
      }
    }

    function completeConstructionSite(site) {
      const t = world[site.y][site.x];
      if (site.kind === 'trail') {
        for (let dy = -1; dy <= 1; dy++) {
          for (let dx = -1; dx <= 1; dx++) {
            const ny = site.y + dy, nx = site.x + dx;
            if (ny >= 0 && ny < MAP_H && nx >= 0 && nx < MAP_W) {
              const nt = world[ny][nx];
              nt.trail = nt.biome === BIOMES.WATER ? 'bridge' : 'road';
            }
          }
        }
      } else if (site.kind === 'well') {
        staticBuildings.push({
          id: nextEntityId++,
          type: 'well',
          x: site.x + 0.5,
          y: site.y + 0.5,
          scale: 1.35,
          label: `Giếng Đá Nước Ngầm (${Math.round((1 - t.gwDepth) * 100)}%)`
        });
      } else if (site.kind === 'cairn') {
        staticBuildings.push({
          id: nextEntityId++,
          type: 'cairn',
          x: site.x + 0.5,
          y: site.y + 0.5,
          scale: 1.0,
          label: 'Cột Đá Chỉ Đường'
        });
      }
      bakeAllMapPreviewBuffers();
    }

    function renderNpcRosterPanel() {
      const grid = document.getElementById('npcRosterGrid');
      const selCount = npcVillagers.filter(u => u.selected).length;
      document.getElementById('lblSelectedCount').textContent = `Đang chọn: ${selCount}/${npcVillagers.length}`;

      grid.innerHTML = npcVillagers.map(u => {
        const borderCls = u.selected
          ? 'border-emerald-400 bg-emerald-950/60'
          : 'border-stone-700 bg-stone-900/70 hover:border-stone-500';
        return `
          <div data-npcid="${u.id}" class="npc-card cursor-pointer px-2 py-1 rounded border ${borderCls} flex items-center justify-between gap-1.5 transition">
            <div class="truncate">
              <div class="font-bold text-amber-200 truncate">${u.name}</div>
              <div class="text-[10px] text-stone-300 truncate">${u.thoughtBubble}</div>
            </div>
            <div class="text-right shrink-0 text-[10px]">
              <div class="text-emerald-300">No: ${Math.round(u.hunger)}%</div>
              <div class="text-orange-300">Ấm: ${Math.round(u.warmth)}%</div>
            </div>
          </div>
        `;
      }).join('');

      grid.querySelectorAll('.npc-card').forEach(card => {
        card.addEventListener('click', e => {
          const id = Number(card.getAttribute('data-npcid'));
          const npc = npcVillagers.find(n => n.id === id);
          if (!npc) return;
          if (!e.shiftKey) npcVillagers.forEach(n => { n.selected = false; });
          npc.selected = true;
          camera.x = npc.x * TILE_PX;
          camera.y = npc.y * TILE_PX;
          renderNpcRosterPanel();
        });
      });
    }

    // =========================================================================
    // 4. PRE-BAKED OFF-SCREEN 200x200 MAP PREVIEW BUFFERS
    // =========================================================================
    const offscreenBuffers = {
      terrain: document.createElement('canvas'),
      elevation: document.createElement('canvas'),
      groundwater: document.createElement('canvas'),
      thermal: document.createElement('canvas')
    };
    for (const c of Object.values(offscreenBuffers)) {
      c.width = MAP_W;
      c.height = MAP_H;
    }

    let currentSeasonIdx = 0;
    const SEASONS = [
      { name: 'Xuân Băng Tan (+7°C)', tempOffset: 0, freezeShallow: false },
      { name: 'Hạ Mưa Dông (+20°C)', tempOffset: 12, freezeShallow: false },
      { name: 'Thu Gió Chướng (+4°C)', tempOffset: -3, freezeShallow: false },
      { name: 'Đông Đại Hàn (-12°C • Đóng Băng Sông)', tempOffset: -18, freezeShallow: true }
    ];

    function getTileDisplayRGB(t, mode = 'terrain') {
      const season = SEASONS[currentSeasonIdx];
      const effTemp = t.tempC + season.tempOffset;

      if (mode === 'elevation') {
        const tierCols = [
          [22, 78, 99], [56, 189, 248], [92, 130, 82],
          [148, 172, 76], [140, 126, 106], [226, 236, 244]
        ];
        if (t.isRamp) return [250, 204, 21];
        if (t.isCliffEdge) return [28, 25, 23];
        return tierCols[t.tier] || [128, 128, 128];
      }

      if (mode === 'groundwater') {
        if (t.biome === BIOMES.WATER) return [2, 132, 199];
        const sat = 1.0 - t.gwDepth;
        return [
          Math.round(235 - sat * 195),
          Math.round(240 - sat * 85),
          Math.round(205 + sat * 45)
        ];
      }

      if (mode === 'thermal') {
        const norm = Math.max(0, Math.min(1, (effTemp + 25) / 60));
        if (norm < 0.5) {
          const u = norm * 2;
          return [Math.round(30 + u * 190), Math.round(90 + u * 150), 245];
        } else {
          const u = (norm - 0.5) * 2;
          return [245, Math.round(220 - u * 170), Math.round(180 - u * 150)];
        }
      }

      if (t.trail === 'bridge') return [175, 122, 70];
      if (t.trail === 'road') return [194, 158, 106];

      if (t.biome === BIOMES.WATER) {
        if (t.tier === 1 && season.freezeShallow && effTemp <= -1.0) {
          return [176, 228, 245];
        }
        return t.tier === 1 ? [74, 166, 194] : [34, 98, 138];
      }

      let r = 142, g = 168, b = 74;
      if (t.biome === BIOMES.FOREST) { r = 48; g = 98; b = 46; }
      else if (t.biome === BIOMES.TUNDRA) { r = 220; g = 232; b = 240; }
      else if (t.biome === BIOMES.HIGHLAND) { r = 128; g = 114; b = 98; }
      else if (t.biome === BIOMES.SWAMP) { r = 64; g = 92; b = 68; }

      if (t.ecotone === ECOTONES.SHORE) {
        r = Math.round(r * 0.38 + 198 * 0.62);
        g = Math.round(g * 0.38 + 182 * 0.62);
        b = Math.round(b * 0.38 + 138 * 0.62);
      } else if (t.ecotone === ECOTONES.WOODLAND) {
        r = Math.round(r * 0.5 + 96 * 0.5);
        g = Math.round(g * 0.5 + 134 * 0.5);
        b = Math.round(b * 0.5 + 58 * 0.5);
      } else if (t.ecotone === ECOTONES.FOOTHILL) {
        r = Math.round(r * 0.5 + 142 * 0.5);
        g = Math.round(g * 0.5 + 132 * 0.5);
        b = Math.round(b * 0.5 + 102 * 0.5);
      }

      const nwElev = (t.x > 0 && t.y > 0) ? world[t.y - 1][t.x - 1].elev : t.elev;
      const shade = Math.max(-28, Math.min(28, (t.elev - nwElev) * 170)) + (t.tier - 3) * 10;
      if (t.cliffSouth > 0) return [54, 48, 44];
      return [
        Math.max(0, Math.min(255, Math.round(r + shade))),
        Math.max(0, Math.min(255, Math.round(g + shade))),
        Math.max(0, Math.min(255, Math.round(b + shade)))
      ];
    }

    function bakeAllMapPreviewBuffers() {
      for (const mode of ['terrain', 'elevation', 'groundwater', 'thermal']) {
        const ctx = offscreenBuffers[mode].getContext('2d');
        const imgData = ctx.createImageData(MAP_W, MAP_H);
        const data = imgData.data;
        let idx = 0;
        for (let y = 0; y < MAP_H; y++) {
          for (let x = 0; x < MAP_W; x++) {
            const [r, g, b] = getTileDisplayRGB(world[y][x], mode);
            data[idx++] = r;
            data[idx++] = g;
            data[idx++] = b;
            data[idx++] = 255;
          }
        }
        ctx.putImageData(imgData, 0, 0);
      }
    }

    // =========================================================================
    // 5. SPLIT-BODY PROCEDURAL LEG-STRIDE & ACTION MOTION RENDERER
    // =========================================================================
    const mainCanvas = document.getElementById('gameViewport');
    const mainCtx = mainCanvas.getContext('2d');
    const miniCanvas = document.getElementById('minimapCanvas');
    const miniCtx = miniCanvas.getContext('2d');
    const fullWorldCanvas = document.getElementById('fullWorldCanvas');
    const fullWorldCtx = fullWorldCanvas.getContext('2d');

    const camera = { x: 98.0 * TILE_PX, y: 100.0 * TILE_PX };
    let minimapMode = 'terrain';
    let worldModalLayer = 'terrain';
    let activeTool = 'scout';
    let showElevationOverlayInViewport = false;
    let animTick = 0;

    let isBoxSelecting = false;
    let boxStartX = 0, boxStartY = 0, boxEndX = 0, boxEndY = 0;
    const orderPings = [];

    function resizeViewport() {
      mainCanvas.width = window.innerWidth;
      mainCanvas.height = window.innerHeight;
    }
    window.addEventListener('resize', resizeViewport);
    resizeViewport();

    /**
     * Renders an NPC or Wildlife unit with realistic Split-Body Leg-Walking Motion,
     * Directional Flip, Chopping/Mining Upper-Body Swing, and Squash-and-Stretch!
     */
    function drawAnimatedCharacterOrBeast(ctx, kind, obj, img, sx, sy, drawW, drawH) {
      const isMoving = obj.isMoving;
      const isWorking = (kind === 'npc' && (obj.state === 'HARVESTING' || obj.state === 'BUILDING' || obj.state === 'HUNTING'));
      const stride = obj.stridePhase || 0;
      const facing = obj.facing || 1;

      ctx.save();
      ctx.translate(sx, sy + 10);

      // Dynamic ground shadow scales with stride bounce
      const bounceLift = isMoving ? Math.abs(Math.sin(stride)) * 4.2 : 0;
      const shadowScale = 1.0 - (bounceLift / 32.0);
      ctx.fillStyle = 'rgba(12, 10, 8, 0.38)';
      ctx.beginPath();
      ctx.ellipse(0, -4, drawW * 0.34 * shadowScale, drawW * 0.15 * shadowScale, 0, 0, Math.PI * 2);
      ctx.fill();

      // Flip horizontally according to movement direction
      ctx.scale(facing, 1);

      if (isMoving && kind === 'npc') {
        // SPLIT-BODY WALK CYCLE KINEMATICS:
        // Upper torso (top 66% of sprite) leans forward and bobs with stride;
        // Left Leg (bottom 34%, left half) and Right Leg (bottom 34%, right half)
        // alternate stepping forward/back and lifting off the ground!
        const sw = img.naturalWidth;
        const sh = img.naturalHeight;
        const hipRatio = 0.65;
        const syHip = Math.floor(sh * hipRatio);
        const legH = sh - syHip;

        const legSwing = Math.sin(stride) * (drawW * 0.11);
        const leftLift = Math.max(0, Math.cos(stride)) * 3.8;
        const rightLift = Math.max(0, -Math.cos(stride)) * 3.8;
        const torsoLean = 0.08 + Math.sin(stride * 2) * 0.03;

        // 1. Draw Back/Right Leg slice
        ctx.save();
        ctx.translate(legSwing * 0.85, -rightLift - bounceLift * 0.3);
        ctx.rotate(-Math.sin(stride) * 0.10);
        ctx.drawImage(
          img,
          Math.floor(sw * 0.45), syHip, Math.floor(sw * 0.55), legH,
          -drawW * 0.05, -drawH * (1 - hipRatio), drawW * 0.55, drawH * (1 - hipRatio)
        );
        ctx.restore();

        // 2. Draw Front/Left Leg slice
        ctx.save();
        ctx.translate(-legSwing * 0.85, -leftLift - bounceLift * 0.3);
        ctx.rotate(Math.sin(stride) * 0.12);
        ctx.drawImage(
          img,
          0, syHip, Math.floor(sw * 0.55), legH,
          -drawW * 0.50, -drawH * (1 - hipRatio), drawW * 0.55, drawH * (1 - hipRatio)
        );
        ctx.restore();

        // 3. Draw Upper Torso + Head + Carried Item with stride bounce & forward lean
        ctx.save();
        ctx.translate(0, -drawH * (1 - hipRatio) - bounceLift);
        ctx.rotate(torsoLean);
        ctx.drawImage(
          img,
          0, 0, sw, syHip,
          -drawW / 2, -drawH * hipRatio, drawW, drawH * hipRatio + 2
        );
        ctx.restore();
      } else if (isMoving && kind === 'wildlife') {
        // Quadruped galloping / trotting motion (rocking pitch + front/hind leg shear)
        const pitch = Math.sin(stride) * 0.09;
        const stretchX = 1.0 + Math.sin(stride * 2) * 0.05;
        const stretchY = 1.0 - Math.sin(stride * 2) * 0.04;
        ctx.translate(0, -bounceLift);
        ctx.rotate(pitch);
        ctx.scale(stretchX, stretchY);
        ctx.drawImage(img, -drawW / 2, -drawH, drawW, drawH);
      } else if (isWorking) {
        // Rhythmic Chopping / Mining / Club-Swinging Motion!
        const swing = Math.sin(obj.actionSwingPhase);
        const chopAngle = swing > 0 ? swing * 0.28 : swing * 0.12;
        const squashY = 1.0 - Math.max(0, swing) * 0.07;
        ctx.scale(1.0 + Math.max(0, swing) * 0.05, squashY);
        ctx.rotate(chopAngle);
        ctx.drawImage(img, -drawW / 2, -drawH, drawW, drawH);
      } else {
        // Smooth Idle Breathing Motion
        const breathe = Math.sin(animTick * 0.07 + obj.id * 1.9);
        const scaleY = 1.0 + breathe * 0.025;
        const scaleX = 1.0 - breathe * 0.015;
        ctx.scale(scaleX, scaleY);
        ctx.drawImage(img, -drawW / 2, -drawH, drawW, drawH);
      }

      ctx.restore();
    }

    function renderMainViewport() {
      const vw = mainCanvas.width, vh = mainCanvas.height;
      mainCtx.fillStyle = '#100e0c';
      mainCtx.fillRect(0, 0, vw, vh);

      const startCol = Math.max(0, Math.floor((camera.x - vw / 2) / TILE_PX) - 1);
      const endCol = Math.min(MAP_W - 1, Math.ceil((camera.x + vw / 2) / TILE_PX) + 1);
      const startRow = Math.max(0, Math.floor((camera.y - vh / 2) / TILE_PX) - 1);
      const endRow = Math.min(MAP_H - 1, Math.ceil((camera.y + vh / 2) / TILE_PX) + 1);

      const offsetX = Math.round(vw / 2 - camera.x);
      const offsetY = Math.round(vh / 2 - camera.y);

      // PASS 1: Continuous Terrain Tiles
      for (let y = startRow; y <= endRow; y++) {
        for (let x = startCol; x <= endCol; x++) {
          const t = world[y][x];
          const px = x * TILE_PX + offsetX;
          const py = y * TILE_PX + offsetY;

          if (t.fow === 0) {
            mainCtx.fillStyle = '#0c0b0e';
            mainCtx.fillRect(px, py, TILE_PX + 1, TILE_PX + 1);
            continue;
          }

          const [r, g, b] = getTileDisplayRGB(t, showElevationOverlayInViewport ? 'elevation' : 'terrain');
          mainCtx.fillStyle = `rgb(${r},${g},${b})`;
          mainCtx.fillRect(px, py, TILE_PX + 1, TILE_PX + 1);

          if (!showElevationOverlayInViewport) {
            if (t.biome === BIOMES.STEPPE || t.biome === BIOMES.FOREST) {
              const gx = px + Math.floor(t.grassSeed * 32) + 6;
              const gy = py + Math.floor(((t.grassSeed * 97) % 1) * 32) + 8;
              mainCtx.fillStyle = t.biome === BIOMES.FOREST ? '#245224' : '#6e9438';
              mainCtx.fillRect(gx, gy, 3, 5);
              mainCtx.fillRect(gx + 3, gy + 2, 2, 3);
            }
            if (t.biome === BIOMES.WATER) {
              const waveShift = Math.sin(animTick * 0.05 + x * 0.7 + y * 0.5) * 3;
              mainCtx.fillStyle = t.tier === 1 ? 'rgba(186, 238, 252, 0.38)' : 'rgba(125, 211, 252, 0.22)';
              mainCtx.fillRect(px + 8 + waveShift, py + 16, 14, 2);
              mainCtx.fillRect(px + 22 - waveShift, py + 34, 10, 2);

              if (t.isFord || (t.tier === 1 && y >= 98 && y <= 102)) {
                mainCtx.fillStyle = '#9ca3af';
                mainCtx.beginPath();
                mainCtx.ellipse(px + 15, py + 18, 7, 5, 0, 0, Math.PI * 2);
                mainCtx.ellipse(px + 33, py + 30, 8, 5.5, 0.2, 0, 0, Math.PI * 2);
                mainCtx.fill();
              }
            }
            if (t.trail === 'road') {
              mainCtx.fillStyle = '#b48a5a';
              mainCtx.beginPath();
              mainCtx.ellipse(px + TILE_PX / 2, py + TILE_PX / 2, 16, 12, 0, 0, Math.PI * 2);
              mainCtx.fill();
            } else if (t.trail === 'bridge') {
              mainCtx.fillStyle = '#784b2a';
              mainCtx.fillRect(px + 4, py + 8, TILE_PX - 8, TILE_PX - 16);
            }
            if (t.cliffSouth > 0) {
              const wallH = Math.min(TILE_PX, 12 + t.cliffSouth * 6);
              const grad = mainCtx.createLinearGradient(px, py + TILE_PX - wallH, px, py + TILE_PX);
              grad.addColorStop(0, '#78716c');
              grad.addColorStop(0.35, '#44403c');
              grad.addColorStop(1, '#1c1917');
              mainCtx.fillStyle = grad;
              mainCtx.fillRect(px, py + TILE_PX - wallH, TILE_PX + 1, wallH);
            }
          }
        }
      }

      // PASS 1.5: Pending Construction Sites & Selected NPC Destination Lines
      for (const site of constructionSites) {
        if (site.completed) continue;
        const sx = (site.x + 0.5) * TILE_PX + offsetX;
        const sy = (site.y + 0.5) * TILE_PX + offsetY;
        mainCtx.strokeStyle = '#38bdf8';
        mainCtx.setLineDash([4, 4]);
        mainCtx.lineWidth = 2;
        mainCtx.strokeRect(sx - 20, sy - 20, 40, 40);
        mainCtx.setLineDash([]);
        mainCtx.fillStyle = 'rgba(12, 74, 110, 0.85)';
        mainCtx.fillRect(sx - 28, sy - 32, 56, 12);
        mainCtx.fillStyle = '#38bdf8';
        mainCtx.fillRect(sx - 28, sy - 32, 56 * (site.progress / 100), 12);
      }

      for (const npc of npcVillagers) {
        if (!npc.selected) continue;
        let destX = null, destY = null;
        if (npc.state === 'MOVE_TO_TARGET' || npc.state === 'SCOUTING') {
          destX = npc.targetX; destY = npc.targetY;
        } else if ((npc.state === 'HARVESTING' || npc.state === 'HUNTING') && npc.targetEntity) {
          destX = npc.targetEntity.x; destY = npc.targetEntity.y;
        } else if (npc.state === 'RETURNING_DROP') {
          destX = CAMP_POS.x; destY = CAMP_POS.y + 0.8;
        } else if (npc.state === 'BUILDING' && npc.targetSite) {
          destX = npc.targetSite.x + 0.5; destY = npc.targetSite.y + 0.5;
        }
        if (destX !== null) {
          mainCtx.save();
          mainCtx.strokeStyle = 'rgba(74, 222, 128, 0.65)';
          mainCtx.setLineDash([5, 5]);
          mainCtx.lineWidth = 1.8;
          mainCtx.beginPath();
          mainCtx.moveTo(npc.x * TILE_PX + offsetX, npc.y * TILE_PX + offsetY);
          mainCtx.lineTo(destX * TILE_PX + offsetX, destY * TILE_PX + offsetY);
          mainCtx.stroke();
          mainCtx.restore();
        }
      }

      // PASS 2: Y-Sorted Render List
      const renderList = [];
      for (const b of staticBuildings) renderList.push({ kind: 'building', obj: b, y: b.y });
      for (const r of resourceNodes) renderList.push({ kind: 'resource', obj: r, y: r.y });
      for (const w of wildlifeList) renderList.push({ kind: 'wildlife', obj: w, y: w.y });
      for (const n of npcVillagers) renderList.push({ kind: 'npc', obj: n, y: n.y });

      const visibleRenderList = renderList.filter(({ kind, obj }) => {
        const tx = Math.floor(obj.x), ty = Math.floor(obj.y);
        if (tx < startCol - 3 || tx > endCol + 3 || ty < startRow - 3 || ty > endRow + 3) return false;
        const tile = (world[ty] && world[ty][tx]) ? world[ty][tx] : null;
        if (!tile || tile.fow === 0) return false;
        if (kind === 'wildlife' && tile.fow !== 2) return false;
        return true;
      });
      visibleRenderList.sort((a, b) => a.y - b.y);

      for (const { kind, obj } of visibleRenderList) {
        const img = IMAGES[obj.type];
        if (!img) continue;
        const shakeX = obj.hitShake ? (Math.random() - 0.5) * 6 : 0;
        const sx = obj.x * TILE_PX + offsetX + shakeX;
        const sy = obj.y * TILE_PX + offsetY;
        const drawW = TILE_PX * (obj.scale || 1.0);
        const drawH = drawW * (img.naturalHeight / Math.max(1, img.naturalWidth));

        if (kind === 'npc' || kind === 'wildlife') {
          if (kind === 'npc' && obj.selected) {
            mainCtx.strokeStyle = '#4ade80';
            mainCtx.lineWidth = 2.5;
            mainCtx.beginPath();
            mainCtx.ellipse(sx, sy + 6, drawW * 0.42, drawW * 0.20, 0, 0, Math.PI * 2);
            mainCtx.stroke();
          }

          drawAnimatedCharacterOrBeast(mainCtx, kind, obj, img, sx, sy, drawW, drawH);

          // Overlay HUD bars & thought bubble
          if (kind === 'npc') {
            const barW = 36;
            mainCtx.fillStyle = 'rgba(0,0,0,0.75)';
            mainCtx.fillRect(sx - barW / 2, sy - drawH - 2, barW, 7);
            mainCtx.fillStyle = '#4ade80';
            mainCtx.fillRect(sx - barW / 2 + 1, sy - drawH - 1, (barW - 2) * (obj.hunger / 100), 2.5);
            mainCtx.fillStyle = '#fb923c';
            mainCtx.fillRect(sx - barW / 2 + 1, sy - drawH + 2, (barW - 2) * (obj.warmth / 100), 2.5);

            const tagText = obj.selected ? `${obj.name.split(' ')[0]}: ${obj.thoughtBubble}` : obj.name.split(' ')[0];
            mainCtx.font = 'bold 10.5px Inter, sans-serif';
            const tw = mainCtx.measureText(tagText).width;
            mainCtx.fillStyle = obj.selected ? 'rgba(6, 78, 59, 0.88)' : 'rgba(20, 18, 16, 0.75)';
            mainCtx.fillRect(sx - tw / 2 - 5, sy - drawH - 18, tw + 10, 15);
            mainCtx.fillStyle = obj.selected ? '#a7f3d0' : '#fed7aa';
            mainCtx.textAlign = 'center';
            mainCtx.fillText(tagText, sx, sy - drawH - 7);
          } else {
            const tag = `${obj.name} (${obj.hp}/${obj.maxHp})`;
            mainCtx.font = 'bold 10.5px Inter, sans-serif';
            const tw = mainCtx.measureText(tag).width;
            mainCtx.fillStyle = 'rgba(69, 10, 10, 0.82)';
            mainCtx.fillRect(sx - tw / 2 - 5, sy - drawH - 6, tw + 10, 15);
            mainCtx.fillStyle = '#fca5a5';
            mainCtx.textAlign = 'center';
            mainCtx.fillText(tag, sx, sy - drawH + 5);
          }
        } else {
          // Static buildings & swaying trees/flora
          mainCtx.save();
          mainCtx.fillStyle = 'rgba(12, 10, 8, 0.36)';
          mainCtx.beginPath();
          mainCtx.ellipse(sx, sy + 4, drawW * 0.34, drawW * 0.15, 0, 0, Math.PI * 2);
          mainCtx.fill();

          if (kind === 'resource' && obj.resType === 'wood') {
            // Subtle wind sway on trees
            const windSway = Math.sin(animTick * 0.04 + obj.x * 0.7) * 0.035;
            mainCtx.translate(sx, sy + 10);
            mainCtx.rotate(windSway);
            mainCtx.drawImage(img, -drawW / 2, -drawH, drawW, drawH);
          } else {
            mainCtx.drawImage(img, sx - drawW / 2, sy - drawH + 12, drawW, drawH);
          }

          if (obj.label) {
            mainCtx.font = 'bold 11px Inter, sans-serif';
            const tw = mainCtx.measureText(obj.label).width;
            mainCtx.fillStyle = 'rgba(20, 18, 16, 0.78)';
            mainCtx.fillRect(sx - tw / 2 - 5, sy - drawH - 4, tw + 10, 15);
            mainCtx.fillStyle = '#fde68a';
            mainCtx.textAlign = 'center';
            mainCtx.fillText(obj.label, sx, sy - drawH + 7);
          }
          mainCtx.restore();
        }
      }

      // PASS 2.5: Render Footstep Dust, Water Ripples, Wood Chips, Sparks & Flying Spears
      for (const pt of vfxParticles) {
        const px = pt.x * TILE_PX + offsetX;
        const py = pt.y * TILE_PX + offsetY - pt.z * TILE_PX;
        const alpha = 1.0 - pt.age / pt.maxAge;
        if (pt.kind === 'ripple') {
          mainCtx.strokeStyle = `rgba(186, 238, 252, ${alpha * 0.75})`;
          mainCtx.lineWidth = 1.5;
          mainCtx.beginPath();
          mainCtx.ellipse(px, py, 4 + pt.age * 0.65, 2 + pt.age * 0.35, 0, 0, Math.PI * 2);
          mainCtx.stroke();
        } else {
          if (pt.kind === 'dust') mainCtx.fillStyle = `rgba(198, 178, 142, ${alpha * 0.65})`;
          else if (pt.kind === 'woodchip') mainCtx.fillStyle = `rgba(217, 155, 82, ${alpha})`;
          else if (pt.kind === 'spark') mainCtx.fillStyle = `rgba(253, 224, 71, ${alpha})`;
          else if (pt.kind === 'berry') mainCtx.fillStyle = `rgba(244, 63, 94, ${alpha})`;
          else mainCtx.fillStyle = `rgba(239, 68, 68, ${alpha})`;
          mainCtx.fillRect(px - 2, py - 2, 4, 4);
        }
      }

      for (const proj of projectiles) {
        const u = proj.progress;
        const cx = (proj.sx + (proj.tx - proj.sx) * u) * TILE_PX + offsetX;
        const cy = (proj.sy + (proj.ty - proj.sy) * u) * TILE_PX + offsetY - Math.sin(u * Math.PI) * 28;
        const ang = Math.atan2(proj.ty - proj.sy, proj.tx - proj.sx);
        mainCtx.save();
        mainCtx.translate(cx, cy);
        mainCtx.rotate(ang);
        mainCtx.strokeStyle = '#d6a874';
        mainCtx.lineWidth = 2.5;
        mainCtx.beginPath();
        mainCtx.moveTo(-12, 0);
        mainCtx.lineTo(12, 0);
        mainCtx.stroke();
        mainCtx.fillStyle = '#94a3b8';
        mainCtx.beginPath();
        mainCtx.moveTo(14, 0);
        mainCtx.lineTo(8, -3);
        mainCtx.lineTo(8, 3);
        mainCtx.closePath();
        mainCtx.fill();
        mainCtx.restore();
      }

      // PASS 3: Radial Warm Campfire & Torch Lighting
      mainCtx.save();
      mainCtx.globalCompositeOperation = 'screen';
      for (const { obj } of visibleRenderList) {
        if (!obj.isLight) continue;
        const lx = obj.x * TILE_PX + offsetX;
        const ly = (obj.y - 0.5) * TILE_PX + offsetY;
        const flicker = 1.0 + Math.sin(animTick * 0.14 + obj.x) * 0.04;
        const rad = (obj.lightRadius || 5.0) * TILE_PX * flicker;
        const grad = mainCtx.createRadialGradient(lx, ly, rad * 0.05, lx, ly, rad);
        grad.addColorStop(0, 'rgba(255, 160, 64, 0.40)');
        grad.addColorStop(0.45, 'rgba(245, 118, 32, 0.16)');
        grad.addColorStop(1, 'rgba(0, 0, 0, 0)');
        mainCtx.fillStyle = grad;
        mainCtx.beginPath();
        mainCtx.arc(lx, ly, rad, 0, Math.PI * 2);
        mainCtx.fill();
      }
      mainCtx.restore();

      // PASS 4: Order Target Pings & Marquee Selection Box
      for (let i = orderPings.length - 1; i >= 0; i--) {
        const p = orderPings[i];
        p.age++;
        if (p.age > 28) { orderPings.splice(i, 1); continue; }
        const px = p.x * TILE_PX + offsetX;
        const py = p.y * TILE_PX + offsetY;
        mainCtx.strokeStyle = p.color;
        mainCtx.lineWidth = 2.2;
        mainCtx.beginPath();
        mainCtx.arc(px, py, 6 + p.age * 0.85, 0, Math.PI * 2);
        mainCtx.stroke();
      }

      if (isBoxSelecting) {
        const x0 = Math.min(boxStartX, boxEndX);
        const y0 = Math.min(boxStartY, boxEndY);
        const bw = Math.abs(boxEndX - boxStartX);
        const bh = Math.abs(boxEndY - boxStartY);
        mainCtx.fillStyle = 'rgba(74, 222, 128, 0.16)';
        mainCtx.fillRect(x0, y0, bw, bh);
        mainCtx.strokeStyle = '#4ade80';
        mainCtx.lineWidth = 1.8;
        mainCtx.strokeRect(x0, y0, bw, bh);
      }
    }

    function renderCircularMinimap() {
      const mw = miniCanvas.width, mh = miniCanvas.height;
      miniCtx.clearRect(0, 0, mw, mh);

      miniCtx.save();
      miniCtx.beginPath();
      miniCtx.arc(mw / 2, mh / 2, mw / 2 - 4, 0, Math.PI * 2);
      miniCtx.clip();

      const srcBuf = offscreenBuffers[minimapMode === 'hydrology' ? 'groundwater' : minimapMode];
      miniCtx.drawImage(srcBuf, 0, 0, mw, mh);

      const scaleX = mw / MAP_W, scaleY = mh / MAP_H;
      miniCtx.fillStyle = 'rgba(14, 18, 26, 0.42)';
      for (let y = 0; y < MAP_H; y += 2) {
        for (let x = 0; x < MAP_W; x += 2) {
          if (world[y][x].fow === 0) {
            miniCtx.fillRect(x * scaleX, y * scaleY, scaleX * 2.2, scaleY * 2.2);
          }
        }
      }

      miniCtx.fillStyle = '#fde047';
      miniCtx.beginPath();
      miniCtx.arc(CAMP_POS.x * scaleX, CAMP_POS.y * scaleY, 4.2, 0, Math.PI * 2);
      miniCtx.fill();

      for (const npc of npcVillagers) {
        miniCtx.fillStyle = npc.selected ? '#4ade80' : '#38bdf8';
        miniCtx.fillRect(npc.x * scaleX - 2, npc.y * scaleY - 2, 4, 4);
      }

      const camTileX = (camera.x / TILE_PX) * scaleX;
      const camTileY = (camera.y / TILE_PX) * scaleY;
      const boxW = (mainCanvas.width / TILE_PX) * scaleX;
      const boxH = (mainCanvas.height / TILE_PX) * scaleY;
      miniCtx.strokeStyle = '#fef08a';
      miniCtx.lineWidth = 1.8;
      miniCtx.strokeRect(camTileX - boxW / 2, camTileY - boxH / 2, boxW, boxH);

      miniCtx.restore();
    }

    function renderFullWorldModal() {
      const modal = document.getElementById('worldMapModal');
      if (modal.classList.contains('hidden')) return;

      const fw = fullWorldCanvas.width, fh = fullWorldCanvas.height;
      fullWorldCtx.imageSmoothingEnabled = false;
      fullWorldCtx.clearRect(0, 0, fw, fh);

      fullWorldCtx.drawImage(offscreenBuffers[worldModalLayer], 0, 0, fw, fh);

      const scale = fw / MAP_W;
      if (document.getElementById('chkShowFogModal').checked) {
        fullWorldCtx.fillStyle = 'rgba(10, 12, 18, 0.52)';
        for (let y = 0; y < MAP_H; y++) {
          for (let x = 0; x < MAP_W; x++) {
            if (world[y][x].fow === 0) {
              fullWorldCtx.fillRect(x * scale, y * scale, scale, scale);
            }
          }
        }
      }

      for (const npc of npcVillagers) {
        fullWorldCtx.fillStyle = npc.selected ? '#4ade80' : '#38bdf8';
        fullWorldCtx.beginPath();
        fullWorldCtx.arc(npc.x * scale, npc.y * scale, 4.5, 0, Math.PI * 2);
        fullWorldCtx.fill();
        fullWorldCtx.strokeStyle = '#000';
        fullWorldCtx.lineWidth = 1.2;
        fullWorldCtx.stroke();
      }

      fullWorldCtx.fillStyle = '#fde047';
      fullWorldCtx.beginPath();
      fullWorldCtx.arc(CAMP_POS.x * scale, CAMP_POS.y * scale, 6.5, 0, Math.PI * 2);
      fullWorldCtx.fill();

      const camX = (camera.x / TILE_PX) * scale;
      const camY = (camera.y / TILE_PX) * scale;
      const vw = (mainCanvas.width / TILE_PX) * scale;
      const vh = (mainCanvas.height / TILE_PX) * scale;
      fullWorldCtx.strokeStyle = '#facc15';
      fullWorldCtx.lineWidth = 2.5;
      fullWorldCtx.strokeRect(camX - vw / 2, camY - vh / 2, vw, vh);
    }

    // =========================================================================
    // 6. RTS SELECTION & CONTEXT-SENSITIVE COMMAND DISPATCHER
    // =========================================================================
    let isPanningCamera = false;
    let panStartX = 0, panStartY = 0, camStartX = 0, camStartY = 0;

    function screenToWorldTile(clientX, clientY) {
      const vw = mainCanvas.width, vh = mainCanvas.height;
      return {
        x: (clientX - vw / 2 + camera.x) / TILE_PX,
        y: (clientY - vh / 2 + camera.y) / TILE_PX
      };
    }

    function issueCommandToSelectedNpcs(worldX, worldY) {
      const selected = npcVillagers.filter(u => u.selected);
      const inspector = document.getElementById('txtInspector');
      if (selected.length === 0) {
        inspector.innerHTML = `<b class="text-rose-300">Chưa chọn NPC nào!</b> Hãy kéo chuột trái khoanh chọn dân hoặc nhấn <b>[A]</b> rồi mới giao việc.`;
        return;
      }

      const tx = Math.max(1, Math.min(MAP_W - 2, Math.floor(worldX)));
      const ty = Math.max(1, Math.min(MAP_H - 2, Math.floor(worldY)));
      const tile = world[ty][tx];

      if (activeTool === 'trail' || activeTool === 'well' || activeTool === 'disaster') {
        const labelMap = {
          trail: tile.biome === BIOMES.WATER ? 'Cầu Gỗ Vượt Sông' : 'Đường Mòn Đá Cuội',
          well: 'Giếng Đá Nước Ngầm',
          disaster: 'Cột Đá Chỉ Đường'
        };
        const site = {
          id: nextEntityId++,
          kind: activeTool === 'disaster' ? 'cairn' : activeTool,
          label: labelMap[activeTool],
          x: tx,
          y: ty,
          progress: 0,
          completed: false
        };
        constructionSites.push(site);
        selected.forEach(npc => {
          npc.targetSite = site;
          npc.state = 'BUILDING';
          npc.thoughtBubble = `🔨 Chạy tới xây ${site.label}...`;
        });
        orderPings.push({ x: worldX, y: worldY, color: '#facc15', age: 0 });
        inspector.innerHTML = `<b class="text-amber-300">Lệnh Xây Dựng:</b> Đã cử <b>${selected.length} dân</b> chạy bộ tới <b>(${tx}, ${ty})</b> thi công <b>${site.label}</b>!`;
        return;
      }

      const clickedMob = wildlifeList.find(m => Math.hypot(m.x - worldX, m.y - worldY) < 1.35);
      if (clickedMob) {
        selected.forEach(npc => {
          npc.targetEntity = clickedMob;
          npc.state = 'HUNTING';
          npc.thoughtBubble = `🏹 Được lệnh săn ${clickedMob.name}!`;
        });
        orderPings.push({ x: clickedMob.x, y: clickedMob.y, color: '#ef4444', age: 0 });
        inspector.innerHTML = `<b class="text-rose-300">Lệnh Săn Bắt:</b> Đã cử <b>${selected.length} dân</b> bao vây săn <b>${clickedMob.name}</b>!`;
        return;
      }

      const clickedRes = resourceNodes.find(r => Math.hypot(r.x - worldX, r.y - worldY) < 1.25);
      if (clickedRes) {
        selected.forEach(npc => {
          npc.targetEntity = clickedRes;
          npc.state = 'HARVESTING';
          npc.thoughtBubble = `🧺 Được lệnh khai thác ${clickedRes.name}!`;
        });
        orderPings.push({ x: clickedRes.x, y: clickedRes.y, color: '#4ade80', age: 0 });
        inspector.innerHTML = `<b class="text-emerald-300">Lệnh Thu Hoạch:</b> Đã cử <b>${selected.length} dân</b> chạy tới khai thác <b>${clickedRes.name}</b> (Trữ lượng: ${clickedRes.amount})!`;
        return;
      }

      if (Math.hypot(worldX - CAMP_POS.x, worldY - CAMP_POS.y) < 2.5) {
        selected.forEach(npc => {
          npc.state = npc.carryAmount > 0 ? 'RETURNING_DROP' : 'WARMING_UP';
          npc.thoughtBubble = '🏠 Chạy về Hang Đá Cội Nguồn!';
        });
        orderPings.push({ x: CAMP_POS.x, y: CAMP_POS.y, color: '#fb923c', age: 0 });
        inspector.innerHTML = `<b class="text-orange-300">Lệnh Về Trại:</b> Đã gọi <b>${selected.length} dân</b> quay về Hang Đá nộp tài nguyên và sưởi ấm.`;
        return;
      }

      const isBlindScout = tile.fow === 0;
      selected.forEach((npc, idx) => {
        const spreadX = (idx % 3 - 1) * 0.65;
        const spreadY = (Math.floor(idx / 3) - 0.5) * 0.65;
        npc.targetX = Math.max(2, Math.min(MAP_W - 3, worldX + spreadX));
        npc.targetY = Math.max(2, Math.min(MAP_H - 3, worldY + spreadY));
        npc.state = isBlindScout ? 'SCOUTING' : 'MOVE_TO_TARGET';
        npc.thoughtBubble = isBlindScout ? `🔦 Dò đường mù tới (${tx},${ty})!` : `👣 Bước đi tới (${tx},${ty})`;
      });
      orderPings.push({ x: worldX, y: worldY, color: '#38bdf8', age: 0 });
      inspector.innerHTML = isBlindScout
        ? `<b class="text-sky-300">Lệnh Dò Đường Mù:</b> Cử <b>${selected.length} dân</b> bước vào vùng sương mù <b>(${tx}, ${ty})</b> để mở bản đồ!`
        : `<b class="text-amber-200">Lệnh Di Chuyển:</b> Cử <b>${selected.length} dân</b> bước đi tới tọa độ <b>(${tx}, ${ty})</b>.`;
    }

    mainCanvas.addEventListener('mousedown', e => {
      if (e.button === 1 || (e.button === 0 && keysDown[' '])) {
        isPanningCamera = true;
        panStartX = e.clientX; panStartY = e.clientY;
        camStartX = camera.x; camStartY = camera.y;
        return;
      }
      if (e.button === 2) {
        const pt = screenToWorldTile(e.clientX, e.clientY);
        issueCommandToSelectedNpcs(pt.x, pt.y);
        return;
      }
      if (e.button === 0) {
        isBoxSelecting = true;
        boxStartX = e.clientX; boxStartY = e.clientY;
        boxEndX = e.clientX; boxEndY = e.clientY;
      }
    });

    window.addEventListener('mousemove', e => {
      const pt = screenToWorldTile(e.clientX, e.clientY);
      const tx = Math.max(0, Math.min(MAP_W - 1, Math.floor(pt.x)));
      const ty = Math.max(0, Math.min(MAP_H - 1, Math.floor(pt.y)));
      document.getElementById('lblTileCursor').textContent = `Ô: (${tx}, ${ty})`;

      if (isPanningCamera) {
        camera.x = Math.max(0, Math.min(MAP_W * TILE_PX, camStartX - (e.clientX - panStartX)));
        camera.y = Math.max(0, Math.min(MAP_H * TILE_PX, camStartY - (e.clientY - panStartY)));
        updateZoneHeader();
      } else if (isBoxSelecting) {
        boxEndX = e.clientX;
        boxEndY = e.clientY;
      }
    });

    window.addEventListener('mouseup', e => {
      if (isPanningCamera) { isPanningCamera = false; return; }
      if (isBoxSelecting && e.button === 0) {
        isBoxSelecting = false;
        const dist = Math.hypot(boxEndX - boxStartX, boxEndY - boxStartY);
        const vw = mainCanvas.width, vh = mainCanvas.height;
        const offsetX = Math.round(vw / 2 - camera.x);
        const offsetY = Math.round(vh / 2 - camera.y);

        if (dist >= 8) {
          const x0 = Math.min(boxStartX, boxEndX), x1 = Math.max(boxStartX, boxEndX);
          const y0 = Math.min(boxStartY, boxEndY), y1 = Math.max(boxStartY, boxEndY);
          const anyInBox = npcVillagers.some(npc => {
            const sx = npc.x * TILE_PX + offsetX, sy = npc.y * TILE_PX + offsetY;
            return sx >= x0 && sx <= x1 && sy >= y0 && sy <= y1;
          });
          if (anyInBox) {
            npcVillagers.forEach(npc => {
              const sx = npc.x * TILE_PX + offsetX, sy = npc.y * TILE_PX + offsetY;
              npc.selected = sx >= x0 && sx <= x1 && sy >= y0 && sy <= y1;
            });
          }
          renderNpcRosterPanel();
        } else {
          const pt = screenToWorldTile(e.clientX, e.clientY);
          const clickedNpc = npcVillagers.find(u => Math.hypot(u.x - pt.x, u.y - pt.y) < 0.9);
          if (clickedNpc) {
            if (!e.shiftKey) npcVillagers.forEach(u => { u.selected = false; });
            clickedNpc.selected = true;
            renderNpcRosterPanel();
          } else {
            issueCommandToSelectedNpcs(pt.x, pt.y);
          }
        }
      }
    });

    let isDraggingMinimap = false;
    function minimapEventToWorld(e) {
      const rect = miniCanvas.getBoundingClientRect();
      return {
        x: Math.max(2, Math.min(MAP_W - 3, ((e.clientX - rect.left) / rect.width) * MAP_W)),
        y: Math.max(2, Math.min(MAP_H - 3, ((e.clientY - rect.top) / rect.height) * MAP_H))
      };
    }
    miniCanvas.addEventListener('mousedown', e => {
      const pt = minimapEventToWorld(e);
      if (e.button === 2) {
        issueCommandToSelectedNpcs(pt.x, pt.y);
      } else {
        isDraggingMinimap = true;
        camera.x = pt.x * TILE_PX;
        camera.y = pt.y * TILE_PX;
        updateZoneHeader();
      }
    });
    window.addEventListener('mousemove', e => {
      if (isDraggingMinimap) {
        const pt = minimapEventToWorld(e);
        camera.x = pt.x * TILE_PX;
        camera.y = pt.y * TILE_PX;
        updateZoneHeader();
      }
    });
    window.addEventListener('mouseup', () => { isDraggingMinimap = false; });

    fullWorldCanvas.addEventListener('mousedown', e => {
      const rect = fullWorldCanvas.getBoundingClientRect();
      const tx = ((e.clientX - rect.left) / rect.width) * MAP_W;
      const ty = ((e.clientY - rect.top) / rect.height) * MAP_H;
      if (e.button === 2) {
        issueCommandToSelectedNpcs(tx, ty);
      } else {
        camera.x = tx * TILE_PX;
        camera.y = ty * TILE_PX;
        updateZoneHeader();
      }
      renderFullWorldModal();
    });

    function updateZoneHeader() {
      const tx = Math.max(0, Math.min(MAP_W - 1, Math.floor(camera.x / TILE_PX)));
      const ty = Math.max(0, Math.min(MAP_H - 1, Math.floor(camera.y / TILE_PX)));
      const t = world[ty][tx];
      const bNames = ['Sông / Hồ Lớn', 'Đầm Lầy Cổ Đại', 'Thảo Nguyên Cội Nguồn', 'Rừng Nguyên Sinh', 'Cao Nguyên Đá Cự Thạch', 'Lãnh Nguyên Băng Hà'];
      document.getElementById('lblZoneTitle').textContent = `${bNames[t.biome]} (Tier ${t.tier})`;
    }

    document.getElementById('btnSelectAllIdle').addEventListener('click', () => {
      let count = 0;
      npcVillagers.forEach(u => {
        const isIdle = u.state === 'IDLE' || u.state === 'WANDER';
        u.selected = isIdle;
        if (isIdle) count++;
      });
      if (count === 0) npcVillagers.forEach(u => { u.selected = true; });
      renderNpcRosterPanel();
    });

    document.getElementById('btnSelectAllTribe').addEventListener('click', () => {
      npcVillagers.forEach(u => { u.selected = true; });
      renderNpcRosterPanel();
    });

    document.getElementById('btnRecallCampfire').addEventListener('click', () => {
      npcVillagers.filter(u => u.selected).forEach(u => {
        u.state = 'WARMING_UP';
        u.thoughtBubble = '🔥 Được lệnh về Lửa Trại sưởi ấm!';
      });
      renderNpcRosterPanel();
    });

    document.getElementById('btnToggleAutoAI').addEventListener('click', e => {
      autoTribeAI = !autoTribeAI;
      e.target.textContent = `AI Tự Làm: ${autoTribeAI ? 'BẬT' : 'TẮT'}`;
      e.target.className = autoTribeAI
        ? 'px-2 py-0.5 rounded bg-emerald-800/90 hover:bg-emerald-700 text-emerald-100 text-[11px] font-semibold border border-emerald-500/50'
        : 'px-2 py-0.5 rounded bg-stone-700 hover:bg-stone-600 text-stone-200 text-[11px] font-semibold border border-stone-500/50';
    });

    document.querySelectorAll('.mm-mode-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.mm-mode-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        minimapMode = btn.getAttribute('data-mmode');
      });
    });

    document.querySelectorAll('.wlayer-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.wlayer-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        worldModalLayer = btn.getAttribute('data-wlayer');
        renderFullWorldModal();
      });
    });

    document.getElementById('chkShowFogModal').addEventListener('change', renderFullWorldModal);

    function setToolButton(id, toolName) {
      document.getElementById(id).addEventListener('click', () => {
        ['btnActScout', 'btnActTrail', 'btnActWell', 'btnActDisaster'].forEach(bid => {
          document.getElementById(bid).classList.remove('active');
        });
        document.getElementById(id).classList.add('active');
        activeTool = toolName;
      });
    }
    setToolButton('btnActScout', 'scout');
    setToolButton('btnActTrail', 'trail');
    setToolButton('btnActWell', 'well');
    setToolButton('btnActDisaster', 'disaster');

    document.getElementById('btnCenterHome').addEventListener('click', () => {
      camera.x = 98.0 * TILE_PX;
      camera.y = 100.0 * TILE_PX;
      updateZoneHeader();
    });

    function toggleWorldMapModal() {
      const modal = document.getElementById('worldMapModal');
      modal.classList.toggle('hidden');
      if (!modal.classList.contains('hidden')) renderFullWorldModal();
    }
    document.getElementById('btnToggleWorldMap').addEventListener('click', toggleWorldMapModal);
    document.getElementById('btnCloseWorldMap').addEventListener('click', toggleWorldMapModal);

    document.getElementById('btnToggleLayer').addEventListener('click', () => {
      showElevationOverlayInViewport = !showElevationOverlayInViewport;
    });

    document.getElementById('btnCycleSeason').addEventListener('click', () => {
      currentSeasonIdx = (currentSeasonIdx + 1) % SEASONS.length;
      const s = SEASONS[currentSeasonIdx];
      document.getElementById('lblCurrentSeason').textContent = s.name;
      const campTemp = (14.5 + s.tempOffset).toFixed(1);
      document.getElementById('lblTempHud').textContent = `${campTemp > 0 ? '+' : ''}${campTemp}°C (${campTemp < 0 ? 'Băng giá' : 'Ấm áp'})`;
      bakeAllMapPreviewBuffers();
      renderFullWorldModal();
    });

    const STANDALONE_CODE_SNIPPET = `/**
 * drawAnimatedCharacterOrBeast — Bộ Kết Xuất Chuyển Động Bước Đi Thực Tế (Split-Body Walk Cycle + Multi-Frame)
 * Thay thế hoàn toàn việc trượt ảnh tĩnh bằng:
 * 1. Đổi frame sprite theo quãng đường bước chân (idle, walk, carryWood, carryBerry, work/chop)
 * 2. Tách khớp Thân Trên (65%) và 2 Chân Dưới (35% Trái/Phải) bước lệch pha ±sin(stridePhase)
 * 3. Nghiêng người về phía trước khi chạy + nhấp nhô bước đi + tung bụi đất/sóng nước dưới bàn chân
 */
function drawAnimatedUnit(ctx, npc, img, sx, sy, drawW, drawH) {
  const stride = npc.stridePhase || 0;
  const facing = npc.facing || 1;
  const bounceLift = npc.isMoving ? Math.abs(Math.sin(stride)) * 4.2 : 0;

  ctx.save();
  ctx.translate(sx, sy + 10);
  ctx.scale(facing, 1); // Tự động lật mặt Trái / Phải theo hướng di chuyển

  if (npc.isMoving) {
    const sw = img.naturalWidth, sh = img.naturalHeight;
    const hipRatio = 0.65;
    const syHip = Math.floor(sh * hipRatio), legH = sh - syHip;
    const legSwing = Math.sin(stride) * (drawW * 0.11);
    const leftLift = Math.max(0, Math.cos(stride)) * 3.8;
    const rightLift = Math.max(0, -Math.cos(stride)) * 3.8;

    // Chân Phải & Chân Trái bước chéo ngược pha nhau
    ctx.save();
    ctx.translate(legSwing * 0.85, -rightLift - bounceLift * 0.3);
    ctx.rotate(-Math.sin(stride) * 0.10);
    ctx.drawImage(img, Math.floor(sw * 0.45), syHip, Math.floor(sw * 0.55), legH,
                  -drawW * 0.05, -drawH * (1 - hipRatio), drawW * 0.55, drawH * (1 - hipRatio));
    ctx.restore();

    ctx.save();
    ctx.translate(-legSwing * 0.85, -leftLift - bounceLift * 0.3);
    ctx.rotate(Math.sin(stride) * 0.12);
    ctx.drawImage(img, 0, syHip, Math.floor(sw * 0.55), legH,
                  -drawW * 0.50, -drawH * (1 - hipRatio), drawW * 0.55, drawH * (1 - hipRatio));
    ctx.restore();

    // Thân trên hơi đổ về phía trước theo quán tính bước chạy
    ctx.save();
    ctx.translate(0, -drawH * (1 - hipRatio) - bounceLift);
    ctx.rotate(0.08 + Math.sin(stride * 2) * 0.03);
    ctx.drawImage(img, 0, 0, sw, syHip, -drawW / 2, -drawH * hipRatio, drawW, drawH * hipRatio + 2);
    ctx.restore();
  } else {
    ctx.drawImage(img, -drawW / 2, -drawH, drawW, drawH);
  }
  ctx.restore();
}`;

    document.getElementById('codeBlockContent').textContent = STANDALONE_CODE_SNIPPET;
    document.getElementById('btnShowCodeModal').addEventListener('click', () => {
      document.getElementById('codeModal').classList.remove('hidden');
    });
    document.getElementById('btnCloseCodeModal').addEventListener('click', () => {
      document.getElementById('codeModal').classList.add('hidden');
    });
    document.getElementById('btnCopyCode').addEventListener('click', () => {
      const text = document.getElementById('codeBlockContent').textContent;
      try { navigator.clipboard.writeText(text); } catch (e) {}
      document.getElementById('btnCopyCode').textContent = 'Đã Sao Chép!';
      setTimeout(() => { document.getElementById('btnCopyCode').textContent = 'Sao Chép Code JS'; }, 1800);
    });

    const keysDown = {};
    window.addEventListener('keydown', e => {
      const k = e.key.toLowerCase();
      keysDown[k] = true;
      if (k === 'm') toggleWorldMapModal();
      else if (k === 'l') showElevationOverlayInViewport = !showElevationOverlayInViewport;
      else if (k === 'k') document.getElementById('codeModal').classList.toggle('hidden');
      else if (k === '1') document.getElementById('btnSelectAllIdle').click();
      else if (k === 'a' && e.ctrlKey) {
        e.preventDefault();
        document.getElementById('btnSelectAllTribe').click();
      }
    });
    window.addEventListener('keyup', e => { keysDown[e.key.toLowerCase()] = false; });

    function gameLoop() {
      animTick++;
      const panSpeed = 9;
      if (keysDown['w'] || keysDown['arrowup']) { camera.y = Math.max(0, camera.y - panSpeed); updateZoneHeader(); }
      if (keysDown['s'] || keysDown['arrowdown']) { camera.y = Math.min(MAP_H * TILE_PX, camera.y + panSpeed); updateZoneHeader(); }
      if (keysDown['a'] || keysDown['arrowleft']) { camera.x = Math.max(0, camera.x - panSpeed); updateZoneHeader(); }
      if (keysDown['d'] || keysDown['arrowright']) { camera.x = Math.min(MAP_W * TILE_PX, camera.x + panSpeed); updateZoneHeader(); }

      updateAllNpcsAndWildlife();
      renderMainViewport();
      renderCircularMinimap();
      requestAnimationFrame(gameLoop);
    }

    window.onload = () => {
      generateWorldData();
      bakeAllMapPreviewBuffers();
      preloadAssets(() => {
        requestAnimationFrame(gameLoop);
      });
    };