shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

uniform sampler2D biome_splat_tex : filter_linear, repeat_disable;

varying vec3 v_world_pos;
varying vec3 v_world_normal;
varying vec4 v_masks; // r = riverMask, g = moisture, b = coastalMask, a = forestDensity
varying vec2 v_world_uv;

float hash21(vec2 p) {
	p = fract(p * vec2(123.34, 456.21));
	p += dot(p, p + 45.32);
	return fract(p.x * p.y);
}

vec2 hash22(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.xx + p3.yz) * p3.zy);
}

float value_noise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	float a = hash21(i);
	float b = hash21(i + vec2(1.0, 0.0));
	float c = hash21(i + vec2(0.0, 1.0));
	float d = hash21(i + vec2(1.0, 1.0));
	return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

float fbm3(vec2 p) {
	float v = 0.0;
	float a = 0.5;
	for (int i = 0; i < 3; i++) {
		v += a * value_noise(p);
		p *= 2.09;
		a *= 0.5;
	}
	return v;
}

float rock_cracks(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	float min_d1 = 1.0;
	float min_d2 = 1.0;
	for (int y = -1; y <= 1; y++) {
		for (int x = -1; x <= 1; x++) {
			vec2 neighbor = vec2(float(x), float(y));
			vec2 pt = neighbor + hash22(i + neighbor) - f;
			float d = length(pt);
			if (d < min_d1) {
				min_d2 = min_d1;
				min_d1 = d;
			} else if (d < min_d2) {
				min_d2 = d;
			}
		}
	}
	return clamp((min_d2 - min_d1) * 2.2, 0.0, 1.0);
}

float triplanar_fbm(vec3 wp, vec3 blend, float scale) {
	float nx = fbm3(wp.zy * scale);
	float ny = fbm3(wp.xz * scale);
	float nz = fbm3(wp.xy * scale);
	return nx * blend.x + ny * blend.y + nz * blend.z;
}

float triplanar_cracks(vec3 wp, vec3 blend, float scale) {
	float nx = rock_cracks(wp.zy * scale);
	float ny = rock_cracks(wp.xz * scale);
	float nz = rock_cracks(wp.xy * scale);
	return nx * blend.x + ny * blend.y + nz * blend.z;
}

void vertex() {
	v_world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_world_normal = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
	v_masks = COLOR;
	v_world_uv = UV;
}

void fragment() {
	float h = v_world_pos.y;
	vec3 wn = normalize(v_world_normal);
	float slope = 1.0 - clamp(wn.y, 0.0, 1.0);
	float river_mask = v_masks.r;
	float moisture = v_masks.g;

	vec4 splat = texture(biome_splat_tex, clamp(v_world_uv, vec2(0.0), vec2(1.0)));
	float w_autumn = splat.r;
	float w_desert = splat.g;
	float w_glacial = splat.b;
	float forest_cov = max(splat.a, v_masks.a);

	vec3 tri_blend = pow(abs(wn), vec3(4.0));
	tri_blend /= max(dot(tri_blend, vec3(1.0)), 0.0001);

	float macro_var = fbm3(v_world_pos.xz * 0.016);
	float dry_patch = fbm3(v_world_pos.xz * 0.038 + vec2(17.3, 9.1));
	float micro_detail = triplanar_fbm(v_world_pos, tri_blend, 0.30);
	float cliff_cracks = triplanar_cracks(v_world_pos, tri_blend, 0.12);
	float strata = sin(v_world_pos.y * 1.35 + fbm3(v_world_pos.xz * 0.05) * 4.5) * 0.5 + 0.5;

	// 1. Primeval Forest / Valley Base Palette
	vec3 grass_olive = vec3(0.20, 0.27, 0.11);
	vec3 grass_moss = vec3(0.09, 0.21, 0.08);
	vec3 woodland_humus = vec3(0.038, 0.082, 0.032); // Rich dark canopy floor
	vec3 base_meadow = mix(grass_olive, grass_moss, clamp(moisture * 0.8 + macro_var * 0.25, 0.0, 1.0));
	base_meadow = mix(base_meadow, vec3(0.29, 0.26, 0.14), smoothstep(0.58, 0.90, dry_patch) * 0.42);

	// 2. Autumn Steppes Plateau (Golden-Amber & Burnt-Orange Grass)
	vec3 autumn_gold = vec3(0.68, 0.43, 0.13);
	vec3 autumn_amber = vec3(0.54, 0.28, 0.09);
	vec3 autumn_col = mix(autumn_gold, autumn_amber, clamp(dry_patch * 0.75 + macro_var * 0.35, 0.0, 1.0));
	base_meadow = mix(base_meadow, autumn_col, smoothstep(0.20, 0.75, w_autumn));

	// 3. Terracotta Desert (Red-Ochre Sand Dunes + Oasis Emerald Rim)
	vec3 terracotta_sand = vec3(0.72, 0.36, 0.19);
	vec3 terracotta_ochre = vec3(0.56, 0.31, 0.17);
	vec3 desert_col = mix(terracotta_ochre, terracotta_sand, clamp(macro_var * 0.7 + micro_detail * 0.4, 0.0, 1.0));
	desert_col = mix(desert_col, vec3(0.12, 0.30, 0.11), smoothstep(0.55, 0.85, moisture) * 0.85); // Oasis green rim
	base_meadow = mix(base_meadow, desert_col, smoothstep(0.20, 0.75, w_desert));

	// 4. Glacial Tundra Lowlands
	vec3 tundra_col = mix(vec3(0.16, 0.22, 0.12), vec3(0.26, 0.28, 0.20), dry_patch);
	base_meadow = mix(base_meadow, tundra_col, smoothstep(0.25, 0.78, w_glacial) * (1.0 - smoothstep(0.35, 0.75, forest_cov) * 0.6));

	// Apply heavy woodland canopy darkening so dense forests form continuous dark-green masses from afar
	base_meadow = mix(base_meadow, woodland_humus, smoothstep(0.28, 0.76, forest_cov) * 0.86);
	base_meadow *= (0.78 + 0.42 * micro_detail);

	// 5. Shallow Reef Seabed -> Wet Sand -> Dry Beach
	vec3 reef_bed = vec3(0.14, 0.44, 0.42);
	vec3 sand_wet = vec3(0.38, 0.34, 0.25);
	vec3 sand_dry = mix(vec3(0.62, 0.54, 0.40), vec3(0.72, 0.42, 0.24), smoothstep(0.25, 0.75, w_desert));
	vec3 shore_col = mix(reef_bed, sand_wet, smoothstep(-2.2, 0.3, h));
	shore_col = mix(shore_col, sand_dry * (0.86 + 0.28 * micro_detail), smoothstep(0.2, 1.6, h));
	vec3 terrain_col = mix(shore_col, base_meadow, smoothstep(1.3, 4.4, h));

	// 6. Riverbeds & Pebble Bars (light natural gravel/sand so rivers never turn black)
	float river_bank = smoothstep(0.20, 0.80, river_mask);
	vec3 river_pebble = mix(vec3(0.42, 0.38, 0.30), vec3(0.30, 0.28, 0.24), cliff_cracks * 0.45);
	terrain_col = mix(terrain_col, river_pebble, river_bank * 0.88);

	// 7. Steep Slope -> Stratified Granite / Sandstone Cliff Exposure
	vec3 granite_rock = mix(vec3(0.13, 0.13, 0.15), vec3(0.26, 0.25, 0.24), cliff_cracks * 0.65 + strata * 0.35);
	vec3 sandstone_rock = mix(vec3(0.42, 0.24, 0.14), vec3(0.58, 0.37, 0.22), cliff_cracks * 0.60 + strata * 0.40);
	vec3 rock_col = mix(granite_rock, sandstone_rock, smoothstep(0.25, 0.75, w_desert));
	rock_col *= (0.76 + 0.44 * micro_detail);
	float rock_weight = smoothstep(0.075, 0.185, slope + (micro_detail - 0.5) * 0.06);
	terrain_col = mix(terrain_col, rock_col, rock_weight);

	// 8. Alpine Snow (confined primarily to Glacial NW peaks & highest ridges)
	float snow_alt = smoothstep(38.0, 56.0, h + (macro_var - 0.5) * 9.0) * smoothstep(0.15, 0.65, w_glacial + smoothstep(68.0, 95.0, h));
	float snow_slope_mask = 1.0 - smoothstep(0.09, 0.22, slope + (cliff_cracks - 0.5) * 0.04);
	float snow_weight = snow_alt * snow_slope_mask;
	vec3 snow_col = vec3(0.86, 0.90, 0.95) * (0.90 + 0.14 * micro_detail);
	terrain_col = mix(terrain_col, snow_col, snow_weight);

	// 9. Procedural Triplanar Normal Perturbation
	float eps = 0.32;
	float h_center = mix(micro_detail, cliff_cracks * 0.7 + strata * 0.3, rock_weight);
	float h_dx = mix(triplanar_fbm(v_world_pos + vec3(eps, 0.0, 0.0), tri_blend, 0.30),
	                 triplanar_cracks(v_world_pos + vec3(eps, 0.0, 0.0), tri_blend, 0.12) * 0.7 + strata * 0.3, rock_weight);
	float h_dy = mix(triplanar_fbm(v_world_pos + vec3(0.0, eps, 0.0), tri_blend, 0.30),
	                 triplanar_cracks(v_world_pos + vec3(0.0, eps, 0.0), tri_blend, 0.12) * 0.7 + strata * 0.3, rock_weight);
	float h_dz = mix(triplanar_fbm(v_world_pos + vec3(0.0, 0.0, eps), tri_blend, 0.30),
	                 triplanar_cracks(v_world_pos + vec3(0.0, 0.0, eps), tri_blend, 0.12) * 0.7 + strata * 0.3, rock_weight);

	vec3 grad = vec3(h_dx - h_center, h_dy - h_center, h_dz - h_center) / eps;
	float bump_strength = mix(0.26, 0.65, rock_weight);
	bump_strength = mix(bump_strength, 0.20, snow_weight);

	float cam_dist = length(CAMERA_POSITION_WORLD - v_world_pos);
	float bump_fade = 1.0 - smoothstep(220.0, 880.0, cam_dist);
	vec3 perturbed_world_n = normalize(wn - grad * bump_strength * bump_fade);

	NORMAL = normalize((VIEW_MATRIX * vec4(perturbed_world_n, 0.0)).xyz);

	float roughness = mix(0.90, 0.76, rock_weight);
	roughness = mix(roughness, 0.38, river_bank * 0.70 + (1.0 - smoothstep(-0.5, 1.2, h)) * 0.55);
	roughness = mix(roughness, 0.86, snow_weight);

	ALBEDO = terrain_col;
	ROUGHNESS = roughness;
	SPECULAR = mix(0.28, 0.52, river_bank);
}
