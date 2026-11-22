shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

varying vec3 v_world_pos;
varying vec3 v_world_normal;
varying vec4 v_masks; // r = riverMask, g = moisture, b = coastalMask

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

// Angular cellular rock fracture pattern (crisp crevices for cliffs)
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
}

void fragment() {
	float h = v_world_pos.y;
	vec3 wn = normalize(v_world_normal);
	float slope = 1.0 - clamp(wn.y, 0.0, 1.0);
	float river_mask = v_masks.r;
	float moisture = v_masks.g;

	vec3 tri_blend = pow(abs(wn), vec3(4.0));
	tri_blend /= max(dot(tri_blend, vec3(1.0)), 0.0001);

	float macro_var = fbm3(v_world_pos.xz * 0.022);
	float dry_patch = fbm3(v_world_pos.xz * 0.048 + vec2(17.3, 9.1));
	float micro_detail = triplanar_fbm(v_world_pos, tri_blend, 0.36);
	float cliff_cracks = triplanar_cracks(v_world_pos, tri_blend, 0.14);
	float strata = sin(v_world_pos.y * 1.45 + fbm3(v_world_pos.xz * 0.06) * 4.5) * 0.5 + 0.5;

	// Natural earthy Stone Age palette (no neon/plastic greens)
	vec3 reef_bed = vec3(0.11, 0.30, 0.29);
	vec3 sand_wet = vec3(0.32, 0.28, 0.21);
	vec3 sand_dry = vec3(0.58, 0.51, 0.38);
	vec3 soil_earth = vec3(0.24, 0.19, 0.13);
	vec3 grass_moss = vec3(0.11, 0.22, 0.09);
	vec3 grass_olive = vec3(0.22, 0.27, 0.12);
	vec3 grass_dry = vec3(0.32, 0.29, 0.16);
	vec3 rock_dark = vec3(0.13, 0.13, 0.14);
	vec3 rock_slate = vec3(0.25, 0.24, 0.22);
	vec3 snow_lit = vec3(0.84, 0.88, 0.93);

	// 1. Grass / moss / dry earth blend
	vec3 meadow = mix(grass_olive, grass_moss, clamp(moisture * 0.85 + macro_var * 0.25, 0.0, 1.0));
	meadow = mix(meadow, grass_dry, smoothstep(0.55, 0.88, dry_patch) * 0.55);
	meadow = mix(meadow, soil_earth, smoothstep(0.72, 0.96, dry_patch) * 0.38);
	meadow *= (0.78 + 0.42 * micro_detail);

	// 2. Coastal seabed -> wet sand -> dry beach -> meadow
	vec3 shore_col = mix(reef_bed, sand_wet, smoothstep(-2.0, 0.3, h));
	shore_col = mix(shore_col, sand_dry * (0.86 + 0.28 * micro_detail), smoothstep(0.2, 1.6, h));
	vec3 terrain_col = mix(shore_col, meadow, smoothstep(1.4, 4.8, h));

	// 3. Asymmetric riverbanks & wet pebble bars
	float river_bank = smoothstep(0.18, 0.78, river_mask);
	vec3 pebble_rock = mix(sand_wet, rock_slate * 0.80, cliff_cracks * 0.45 + micro_detail * 0.35);
	terrain_col = mix(terrain_col, pebble_rock, river_bank * 0.90);

	// 4. Steep slope -> sharp granite/slate cliff exposure (starts at ~24 deg)
	vec3 rock_col = mix(rock_dark, rock_slate, clamp(cliff_cracks * 0.65 + strata * 0.35, 0.0, 1.0));
	rock_col *= (0.76 + 0.46 * micro_detail);
	float rock_height_blend = (micro_detail - 0.5) * 0.07 + (macro_var - 0.5) * 0.05;
	float rock_weight = smoothstep(0.075, 0.185, slope + rock_height_blend);
	terrain_col = mix(terrain_col, rock_col, rock_weight);

	// 5. High-altitude alpine snow (height-blended, sheds cleanly off steep rock cliffs!)
	float snow_alt = smoothstep(42.0, 58.0, h + (macro_var - 0.5) * 10.0 + (micro_detail - 0.5) * 4.0);
	float snow_slope_mask = 1.0 - smoothstep(0.09, 0.22, slope + (cliff_cracks - 0.5) * 0.04);
	float snow_weight = snow_alt * snow_slope_mask;
	vec3 snow_col = snow_lit * (0.90 + 0.14 * micro_detail);
	terrain_col = mix(terrain_col, snow_col, snow_weight);

	// 6. Procedural Triplanar Normal Map Perturbation (eliminates plastic/clay look)
	float eps = 0.28;
	float h_center = mix(micro_detail, cliff_cracks * 0.7 + strata * 0.3, rock_weight);
	float h_dx = mix(triplanar_fbm(v_world_pos + vec3(eps, 0.0, 0.0), tri_blend, 0.36),
	                 triplanar_cracks(v_world_pos + vec3(eps, 0.0, 0.0), tri_blend, 0.14) * 0.7 + strata * 0.3, rock_weight);
	float h_dy = mix(triplanar_fbm(v_world_pos + vec3(0.0, eps, 0.0), tri_blend, 0.36),
	                 triplanar_cracks(v_world_pos + vec3(0.0, eps, 0.0), tri_blend, 0.14) * 0.7 + strata * 0.3, rock_weight);
	float h_dz = mix(triplanar_fbm(v_world_pos + vec3(0.0, 0.0, eps), tri_blend, 0.36),
	                 triplanar_cracks(v_world_pos + vec3(0.0, 0.0, eps), tri_blend, 0.14) * 0.7 + strata * 0.3, rock_weight);

	vec3 grad = vec3(h_dx - h_center, h_dy - h_center, h_dz - h_center) / eps;
	float bump_strength = mix(0.28, 0.68, rock_weight);
	bump_strength = mix(bump_strength, 0.22, snow_weight);

	// Distance fade on high-frequency bump to prevent far-distance shimmer
	float cam_dist = length(CAMERA_POSITION_WORLD - v_world_pos);
	float bump_fade = 1.0 - smoothstep(180.0, 750.0, cam_dist);
	vec3 perturbed_world_n = normalize(wn - grad * bump_strength * bump_fade);

	NORMAL = normalize((VIEW_MATRIX * vec4(perturbed_world_n, 0.0)).xyz);

	// PBR Roughness & Specular
	float roughness = mix(0.90, 0.76, rock_weight);
	roughness = mix(roughness, 0.36, river_bank * 0.75 + (1.0 - smoothstep(-0.5, 1.2, h)) * 0.6);
	roughness = mix(roughness, 0.86, snow_weight);

	ALBEDO = terrain_col;
	ROUGHNESS = roughness;
	SPECULAR = mix(0.28, 0.55, river_bank);
}
