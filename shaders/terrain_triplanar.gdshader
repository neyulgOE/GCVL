shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

uniform sampler2D soil_splat_tex : filter_linear, repeat_disable;
uniform sampler2D canopy_coverage_tex : filter_linear, repeat_disable;

varying vec3 v_world_pos;
varying vec3 v_world_normal;
varying vec4 v_masks; // r = riverMask, g = moisture, b = tempNorm, a = soilDepth
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
	return mix(
		mix(hash21(i), hash21(i + vec2(1.0, 0.0)), u.x),
		mix(hash21(i + vec2(0.0, 1.0)), hash21(i + vec2(1.0, 1.0)), u.x),
		u.y
	);
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
	return fbm3(wp.zy * scale) * blend.x + fbm3(wp.xz * scale) * blend.y + fbm3(wp.xy * scale) * blend.z;
}

float triplanar_cracks(vec3 wp, vec3 blend, float scale) {
	return rock_cracks(wp.zy * scale) * blend.x + rock_cracks(wp.xz * scale) * blend.y + rock_cracks(wp.xy * scale) * blend.z;
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
	float temp_c = v_masks.b * 53.0 - 15.0;
	float soil_depth = v_masks.a;

	vec4 soil_w = texture(soil_splat_tex, clamp(v_world_uv, vec2(0.0), vec2(1.0)));
	float w_alluvial = soil_w.r;
	float w_steppe = soil_w.g;
	float w_arid = soil_w.b;
	float w_perma = soil_w.a;
	float canopy_cov = texture(canopy_coverage_tex, clamp(v_world_uv, vec2(0.0), vec2(1.0))).r;

	vec3 tri_blend = pow(abs(wn), vec3(4.0));
	tri_blend /= max(dot(tri_blend, vec3(1.0)), 0.0001);

	float macro_var = fbm3(v_world_pos.xz * 0.016);
	float micro_detail = triplanar_fbm(v_world_pos, tri_blend, 0.28);
	float cliff_cracks = triplanar_cracks(v_world_pos, tri_blend, 0.12);
	float strata = sin(v_world_pos.y * 1.35 + fbm3(v_world_pos.xz * 0.05) * 4.5) * 0.5 + 0.5;
	float sand_ripples = sin(v_world_pos.x * 0.85 + fbm3(v_world_pos.xz * 0.08) * 3.0) * 0.5 + 0.5;

	// Causal Soil Colors driven directly by SoilSimulator & ClimateSimulator
	vec3 col_alluvial = mix(vec3(0.11, 0.22, 0.08), vec3(0.06, 0.14, 0.045), moisture);
	vec3 col_steppe = mix(vec3(0.58, 0.39, 0.12), vec3(0.42, 0.34, 0.13), moisture);
	vec3 col_arid = mix(vec3(0.70, 0.35, 0.18), vec3(0.56, 0.28, 0.15), sand_ripples * 0.55 + macro_var * 0.45);
	vec3 col_tundra = mix(vec3(0.18, 0.22, 0.15), vec3(0.28, 0.29, 0.23), macro_var);

	float w_sum = max(w_alluvial + w_steppe + w_arid + w_perma * 0.4, 0.001);
	vec3 soil_col = (col_alluvial * w_alluvial + col_steppe * w_steppe + col_arid * w_arid + col_tundra * w_perma * 0.4) / w_sum;

	// Darken & moss-tint forest floor underneath actual Phase 1 canopy shade
	vec3 woodland_humus = vec3(0.042, 0.088, 0.032);
	soil_col = mix(soil_col, woodland_humus, smoothstep(0.22, 0.78, canopy_cov) * 0.84);
	soil_col *= (0.78 + 0.42 * micro_detail);

	// Coastal sand / shallow reef seabed
	vec3 reef_bed = vec3(0.14, 0.44, 0.42);
	vec3 coastal_sand = mix(vec3(0.62, 0.54, 0.38), vec3(0.70, 0.41, 0.23), w_arid);
	vec3 shore_col = mix(reef_bed, coastal_sand * (0.86 + 0.28 * micro_detail), smoothstep(-1.8, 1.4, h));
	vec3 terrain_col = mix(shore_col, soil_col, smoothstep(1.2, 4.4, h));

	// Riverbed wet gravel & sand
	float river_bank = smoothstep(0.20, 0.80, river_mask);
	vec3 river_pebble = mix(vec3(0.40, 0.36, 0.28), vec3(0.28, 0.26, 0.22), cliff_cracks * 0.45);
	terrain_col = mix(terrain_col, river_pebble, river_bank * 0.86);

	// Exposed Bedrock / Sandstone Cliffs where SoilDepth is eroded thin or slope is steep
	vec3 granite_rock = mix(vec3(0.14, 0.14, 0.16), vec3(0.27, 0.26, 0.25), cliff_cracks * 0.65 + strata * 0.35);
	vec3 sandstone_rock = mix(vec3(0.44, 0.25, 0.14), vec3(0.60, 0.38, 0.22), cliff_cracks * 0.55 + strata * 0.45);
	vec3 rock_col = mix(granite_rock, sandstone_rock, smoothstep(0.25, 0.70, w_arid)) * (0.76 + 0.44 * micro_detail);
	float rock_exposure = max(
		smoothstep(0.085, 0.21, slope + (micro_detail - 0.5) * 0.06),
		smoothstep(0.26, 0.06, soil_depth) * 0.85
	);
	terrain_col = mix(terrain_col, rock_col, rock_exposure);

	// Physical Temperature-driven Snow & Frost (Temperature < 0C, sheds off steep rock)
	float snow_temp = smoothstep(1.5, -4.5, temp_c + (macro_var - 0.5) * 2.5);
	float snow_slope_mask = 1.0 - smoothstep(0.10, 0.24, slope + (cliff_cracks - 0.5) * 0.04);
	float snow_weight = snow_temp * snow_slope_mask;
	vec3 snow_col = vec3(0.86, 0.90, 0.95) * (0.90 + 0.14 * micro_detail);
	terrain_col = mix(terrain_col, snow_col, snow_weight);

	// Procedural Triplanar Normal Perturbation
	float eps = 0.32;
	float h_center = mix(micro_detail, cliff_cracks * 0.7 + strata * 0.3, rock_exposure);
	float h_dx = mix(triplanar_fbm(v_world_pos + vec3(eps, 0.0, 0.0), tri_blend, 0.28),
	                 triplanar_cracks(v_world_pos + vec3(eps, 0.0, 0.0), tri_blend, 0.12) * 0.7 + strata * 0.3, rock_exposure);
	float h_dy = mix(triplanar_fbm(v_world_pos + vec3(0.0, eps, 0.0), tri_blend, 0.28),
	                 triplanar_cracks(v_world_pos + vec3(0.0, eps, 0.0), tri_blend, 0.12) * 0.7 + strata * 0.3, rock_exposure);
	float h_dz = mix(triplanar_fbm(v_world_pos + vec3(0.0, 0.0, eps), tri_blend, 0.28),
	                 triplanar_cracks(v_world_pos + vec3(0.0, 0.0, eps), tri_blend, 0.12) * 0.7 + strata * 0.3, rock_exposure);

	vec3 grad = vec3(h_dx - h_center, h_dy - h_center, h_dz - h_center) / eps;
	float bump_strength = mix(0.24, 0.62, rock_exposure);
	bump_strength = mix(bump_strength, 0.18, snow_weight);

	float cam_dist = length(CAMERA_POSITION_WORLD - v_world_pos);
	float bump_fade = 1.0 - smoothstep(220.0, 880.0, cam_dist);
	NORMAL = normalize((VIEW_MATRIX * vec4(normalize(wn - grad * bump_strength * bump_fade), 0.0)).xyz);

	float roughness = mix(0.90, 0.76, rock_exposure);
	roughness = mix(roughness, 0.38, river_bank * 0.70 + (1.0 - smoothstep(-0.5, 1.2, h)) * 0.55);
	roughness = mix(roughness, 0.86, snow_weight);

	ALBEDO = terrain_col;
	ROUGHNESS = roughness;
	SPECULAR = mix(0.28, 0.52, river_bank);
}
