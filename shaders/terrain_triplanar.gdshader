shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

uniform sampler2D soil_tex_a : filter_linear, repeat_disable;    // R=Alluvial, G=ForestBrown, B=SteppeLoess, A=AridRedSand
uniform sampler2D soil_tex_b : filter_linear, repeat_disable;    // R=CoastalSand, G=PermafrostRock, B=SoilDepth, A=BedrockMask
uniform sampler2D climate_tex : filter_linear, repeat_disable;   // R=TempNorm, G=Moisture, B=RiverMask, A=FlowAccum
uniform sampler2D canopy_coverage_tex : filter_linear, repeat_disable;
uniform sampler2D weather_dynamic_tex : filter_linear, repeat_disable; // R=SnowAccum, G=Wetness, B=SurfaceIce, A=CloudShadow

varying vec3 v_world_pos;
varying vec3 v_world_normal;
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

vec3 safe_normalize(vec3 v) {
	float len2 = dot(v, v);
	return len2 > 1e-6 ? v * inversesqrt(len2) : vec3(0.0, 1.0, 0.0);
}

void vertex() {
	v_world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_world_normal = safe_normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
	v_world_uv = UV;
}

void fragment() {
	float h = v_world_pos.y;
	vec3 wn = safe_normalize(v_world_normal);
	float slope = 1.0 - clamp(wn.y, 0.0, 1.0);

	vec2 uv = clamp(v_world_uv, vec2(0.0), vec2(1.0));
	vec4 sa = texture(soil_tex_a, uv);
	vec4 sb = texture(soil_tex_b, uv);
	vec4 cl = texture(climate_tex, uv);
	float canopy_cov = texture(canopy_coverage_tex, uv).r;

	float w_alluvial = max(sa.r, 0.0);
	float w_forest = max(sa.g, 0.0);
	float w_steppe = max(sa.b, 0.0);
	float w_arid = max(sa.a, 0.0);
	float w_coastal = max(sb.r, 0.0);
	float w_perma = max(sb.g, 0.0);
	float soil_depth = clamp(sb.b, 0.0, 1.0);
	float bedrock_mask = clamp(sb.a, 0.0, 1.0);

	float temp_c = cl.r * 53.0 - 15.0;
	float moisture = clamp(cl.g, 0.0, 1.0);
	float river_mask = clamp(cl.b, 0.0, 1.0);

	vec3 tri_blend = pow(max(abs(wn), vec3(0.0001)), vec3(4.0));
	tri_blend /= max(dot(tri_blend, vec3(1.0)), 0.0001);

	float macro_var = fbm3(v_world_pos.xz * 0.008);
	float micro_detail = triplanar_fbm(v_world_pos, tri_blend, 0.18);
	float cliff_cracks = triplanar_cracks(v_world_pos, tri_blend, 0.07);
	float strata = sin(v_world_pos.y * 0.65 + fbm3(v_world_pos.xz * 0.02) * 4.5) * 0.5 + 0.5;
	float sand_ripples = sin((v_world_pos.x * 0.82 + v_world_pos.z * 0.57) * 0.45 + fbm3(v_world_pos.xz * 0.03) * 3.0) * 0.5 + 0.5;

	// 6 Physical Soil Colors (never near-black)
	vec3 c_alluvial = mix(vec3(0.13, 0.26, 0.08), vec3(0.09, 0.20, 0.06), moisture);
	vec3 c_forest = mix(vec3(0.18, 0.30, 0.10), vec3(0.13, 0.24, 0.08), moisture);
	vec3 c_steppe = mix(vec3(0.62, 0.43, 0.14), vec3(0.46, 0.35, 0.14), moisture);
	vec3 c_arid = mix(vec3(0.72, 0.36, 0.18), vec3(0.58, 0.29, 0.15), sand_ripples * 0.55 + macro_var * 0.45);
	vec3 c_coastal = vec3(0.68, 0.60, 0.42);
	vec3 c_tundra = mix(vec3(0.24, 0.27, 0.22), vec3(0.34, 0.35, 0.30), macro_var);

	float w_sum = max(w_alluvial + w_forest + w_steppe + w_arid + w_coastal + w_perma, 0.001);
	vec3 soil_col = (
		c_alluvial * w_alluvial +
		c_forest * w_forest +
		c_steppe * w_steppe +
		c_arid * w_arid +
		c_coastal * w_coastal +
		c_tundra * w_perma
	) / w_sum;

	// Woodland canopy humus darkening when Stage 3 flora coverage is present
	soil_col = mix(soil_col, vec3(0.06, 0.11, 0.04), smoothstep(0.20, 0.75, canopy_cov) * 0.80);
	soil_col *= (0.80 + 0.40 * micro_detail);

	// Shallow coral reef seabed -> coastal sand -> inland soil
	vec3 reef_bed = vec3(0.14, 0.48, 0.46);
	vec3 shore_col = mix(reef_bed, c_coastal * (0.86 + 0.28 * micro_detail), smoothstep(-3.5, 1.2, h));
	vec3 terrain_col = mix(shore_col, soil_col, smoothstep(2.0, 8.0, h));

	// Natural Point-Bar Sand/Gravel Bars along gentle meandering river bends + Wet riverbanks
	float river_bank = smoothstep(0.16, 0.72, river_mask);
	float gentle_bar = smoothstep(0.14, 0.04, slope) * smoothstep(0.12, 0.45, river_mask) * (1.0 - smoothstep(0.55, 0.85, river_mask));
	vec3 gravel_bar = mix(vec3(0.76, 0.71, 0.58), vec3(0.58, 0.54, 0.46), micro_detail * 0.65 + cliff_cracks * 0.35);
	vec3 river_pebble = mix(vec3(0.36, 0.32, 0.25), vec3(0.24, 0.22, 0.19), cliff_cracks * 0.45);
	terrain_col = mix(terrain_col, river_pebble, river_bank * 0.82);
	terrain_col = mix(terrain_col, gravel_bar, gentle_bar * 0.78);

	// Exposed Granite / Sandstone Cliffs (driven by Slope + SoilDepth + BedrockMask)
	vec3 granite_rock = mix(vec3(0.22, 0.23, 0.25), vec3(0.37, 0.36, 0.34), cliff_cracks * 0.65 + strata * 0.35);
	vec3 sandstone_rock = mix(vec3(0.45, 0.25, 0.14), vec3(0.62, 0.39, 0.22), cliff_cracks * 0.55 + strata * 0.45);
	vec3 rock_col = mix(granite_rock, sandstone_rock, smoothstep(0.20, 0.65, w_arid)) * (0.80 + 0.38 * micro_detail);

	float rock_exposure = max(
		smoothstep(0.085, 0.21, slope + (micro_detail - 0.5) * 0.06),
		max(smoothstep(0.22, 0.05, soil_depth) * 0.85, smoothstep(0.55, 0.92, bedrock_mask) * 0.65)
	);
	terrain_col = mix(terrain_col, rock_col, rock_exposure);

	// Dynamic Stage 4 Snow Accumulation + Permanent High-Altitude Frost (sheds off steep cliffs >42°)
	vec4 wd = texture(weather_dynamic_tex, uv);
	float dyn_snow = wd.r;
	float dyn_wetness = wd.g;
	float dyn_cloud_shadow = wd.a;

	float snow_temp = smoothstep(1.5, -5.0, temp_c + (macro_var - 0.5) * 2.5) * 0.45;
	float snow_signal = max(snow_temp, dyn_snow);
	float snow_slope_mask = 1.0 - smoothstep(0.11, 0.27, slope + (cliff_cracks - 0.5) * 0.04);
	float snow_weight = clamp(snow_signal * snow_slope_mask * smoothstep(-0.2, 2.5, h), 0.0, 1.0);
	vec3 snow_col = vec3(0.88, 0.92, 0.97) * (0.90 + 0.14 * micro_detail);
	terrain_col = mix(terrain_col, snow_col, snow_weight);

	// Wetness darkening & Cloud shadow pass
	terrain_col = mix(terrain_col, terrain_col * 0.62, dyn_wetness * (1.0 - snow_weight) * 0.65);
	terrain_col *= (1.0 - dyn_cloud_shadow * 0.36);

	// Procedural Triplanar Normal Perturbation
	float eps = 0.55;
	float h_center = mix(micro_detail, cliff_cracks * 0.7 + strata * 0.3, rock_exposure);
	float h_dx = mix(triplanar_fbm(v_world_pos + vec3(eps, 0.0, 0.0), tri_blend, 0.18),
	                 triplanar_cracks(v_world_pos + vec3(eps, 0.0, 0.0), tri_blend, 0.07) * 0.7 + strata * 0.3, rock_exposure);
	float h_dy = mix(triplanar_fbm(v_world_pos + vec3(0.0, eps, 0.0), tri_blend, 0.18),
	                 triplanar_cracks(v_world_pos + vec3(0.0, eps, 0.0), tri_blend, 0.07) * 0.7 + strata * 0.3, rock_exposure);
	float h_dz = mix(triplanar_fbm(v_world_pos + vec3(0.0, 0.0, eps), tri_blend, 0.18),
	                 triplanar_cracks(v_world_pos + vec3(0.0, 0.0, eps), tri_blend, 0.07) * 0.7 + strata * 0.3, rock_exposure);

	vec3 grad = clamp(vec3(h_dx - h_center, h_dy - h_center, h_dz - h_center) / eps, vec3(-1.5), vec3(1.5));
	float bump_strength = mix(0.28, 0.72, rock_exposure);
	bump_strength = mix(bump_strength, 0.20, snow_weight);

	float cam_dist = length(CAMERA_POSITION_WORLD - v_world_pos);
	float close_detail_fade = 1.0 - smoothstep(22.0, 68.0, cam_dist);
	// High-frequency close-up ground grain (soil litter, pebbles, rock grit at 0.35m..1.5m)
	float close_grain = triplanar_fbm(v_world_pos, tri_blend, 1.45) * 0.65 + triplanar_fbm(v_world_pos, tri_blend, 3.80) * 0.35;
	terrain_col *= mix(1.0, 0.78 + 0.44 * close_grain, close_detail_fade * (1.0 - snow_weight * 0.7));

	float bump_fade = 1.0 - smoothstep(350.0, 1800.0, cam_dist);
	float close_bump = (close_grain - 0.5) * 0.65 * close_detail_fade;
	vec3 bumped_world_n = safe_normalize(wn - grad * bump_strength * bump_fade + vec3(close_bump, 0.0, -close_bump));
	NORMAL = safe_normalize((VIEW_MATRIX * vec4(bumped_world_n, 0.0)).xyz);

	// Lock PBR roughness in [0.84..0.96] for dry soil/grass/rock (never plastic/mirror unless actively raining)
	float roughness = mix(0.92, 0.85, rock_exposure);
	roughness = mix(roughness, 0.68, river_bank * 0.60);
	roughness = mix(roughness, 0.56, smoothstep(0.15, 0.90, dyn_wetness));
	roughness = mix(roughness, 0.90, snow_weight);
	roughness = clamp(roughness, 0.52, 0.97);

	ALBEDO = terrain_col;
	ROUGHNESS = roughness;
	SPECULAR = mix(0.12, 0.34, max(river_bank * 0.5, dyn_wetness * 0.8));
}
