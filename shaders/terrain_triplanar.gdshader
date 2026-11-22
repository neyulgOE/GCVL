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
		p *= 2.07;
		a *= 0.5;
	}
	return v;
}

float triplanar_noise(vec3 wp, vec3 wn, float scale) {
	vec3 blend = pow(abs(wn), vec3(4.0));
	blend /= max(dot(blend, vec3(1.0)), 0.0001);
	float nx = fbm3(wp.zy * scale);
	float ny = fbm3(wp.xz * scale);
	float nz = fbm3(wp.xy * scale);
	return nx * blend.x + ny * blend.y + nz * blend.z;
}

void vertex() {
	v_world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_world_normal = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
	v_masks = COLOR;
}

void fragment() {
	float h = v_world_pos.y;
	float slope = 1.0 - clamp(v_world_normal.y, 0.0, 1.0);
	float river_mask = v_masks.r;
	float moisture = v_masks.g;

	// World-space procedural micro-detail (triplanar so cliffs never stretch)
	float macro_var = fbm3(v_world_pos.xz * 0.035);
	float micro_detail = triplanar_noise(v_world_pos, v_world_normal, 0.28);
	float strata = sin(v_world_pos.y * 1.35 + fbm3(v_world_pos.xz * 0.08) * 3.5) * 0.5 + 0.5;

	// Biome / material palette
	vec3 sand_wet = vec3(0.46, 0.41, 0.30);
	vec3 sand_dry = vec3(0.76, 0.67, 0.49);
	vec3 reef_bed = vec3(0.16, 0.42, 0.40);
	vec3 grass_lush = vec3(0.18, 0.36, 0.14);
	vec3 grass_dry = vec3(0.38, 0.43, 0.20);
	vec3 moss_riparian = vec3(0.14, 0.31, 0.13);
	vec3 rock_granite = mix(vec3(0.24, 0.23, 0.22), vec3(0.38, 0.35, 0.32), strata * 0.6 + micro_detail * 0.4);
	vec3 snow_color = vec3(0.88, 0.92, 0.96);

	// 1. Base meadow modulated by moisture & macro noise
	vec3 meadow = mix(grass_dry, grass_lush, clamp(moisture * 0.85 + macro_var * 0.35, 0.0, 1.0));
	meadow = mix(meadow, moss_riparian, smoothstep(0.55, 0.95, moisture) * 0.45);
	meadow *= (0.86 + 0.28 * micro_detail);

	// 2. Coastal beach & submerged seabed transition
	float above_sea = smoothstep(-2.5, 2.2, h);
	vec3 shore_col = mix(reef_bed, sand_dry, smoothstep(-1.4, 1.0, h));
	vec3 terrain_col = mix(shore_col, meadow, smoothstep(1.2, 4.2, h));

	// 3. Riverbed & pebble bank sand
	float river_bank = smoothstep(0.15, 0.78, river_mask);
	vec3 river_col = mix(sand_wet, rock_granite * 0.85, micro_detail * 0.45);
	terrain_col = mix(terrain_col, river_col, river_bank * 0.88);

	// 4. Steep slope -> triplanar stratified granite cliff rock
	float rock_weight = smoothstep(0.24, 0.46, slope + (macro_var - 0.5) * 0.12);
	terrain_col = mix(terrain_col, rock_granite, rock_weight);

	// 5. High-altitude alpine snow (sticks to flatter ridges, sheds off sheer cliffs)
	float snow_alt = smoothstep(46.0, 62.0, h + (macro_var - 0.5) * 8.0);
	float snow_slope_mask = 1.0 - smoothstep(0.32, 0.55, slope);
	float snow_weight = snow_alt * snow_slope_mask;
	terrain_col = mix(terrain_col, snow_color * (0.94 + 0.08 * micro_detail), snow_weight);

	// PBR roughness & normal perturbation
	float roughness = mix(0.88, 0.72, rock_weight);
	roughness = mix(roughness, 0.52, river_bank * 0.65);
	roughness = mix(roughness, 0.92, snow_weight);

	ALBEDO = terrain_col;
	ROUGHNESS = roughness;
	SPECULAR = mix(0.35, 0.15, snow_weight);

	// Subtle procedural micro-bump on normals
	vec3 bump_n = normalize(NORMAL + vec3(micro_detail - 0.5, 0.0, strata - 0.5) * mix(0.08, 0.22, rock_weight));
	NORMAL = bump_n;
}
