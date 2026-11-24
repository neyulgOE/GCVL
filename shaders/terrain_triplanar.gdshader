shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

uniform sampler2D soil_tex_a : filter_linear, repeat_disable;    // R=Alluvial, G=ForestBrown, B=SteppeLoess, A=AridRedSand
uniform sampler2D soil_tex_b : filter_linear, repeat_disable;    // R=CoastalSand, G=PermafrostRock, B=SoilDepth, A=BedrockMask
uniform sampler2D climate_tex : filter_linear, repeat_disable;   // R=TempNorm, G=Moisture, B=RiverMask, A=FlowAccum
uniform sampler2D canopy_coverage_tex : filter_linear, repeat_disable; // R=CanopyCov, G=FloodplainMask, B=WetlandMask, A=ForestMacroMask
uniform sampler2D weather_dynamic_tex : filter_linear, repeat_disable; // R=SnowAccum, G=Wetness, B=SurfaceIce, A=CloudShadow

uniform vec2 world_size = vec2(9600.0, 5400.0);
uniform float canopy_ground_blend_start = 1100.0;
uniform float canopy_ground_blend_end = 1350.0;

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
	return clamp((min_d2 - min_d1) * 2.4, 0.0, 1.0);
}

float triplanar_fbm(vec3 wp, vec3 blend, float scale) {
	return fbm3(wp.zy * scale) * blend.x + fbm3(wp.xz * scale) * blend.y + fbm3(wp.xy * scale) * blend.z;
}

float triplanar_cracks(vec3 wp, vec3 blend, float scale) {
	return rock_cracks(wp.zy * scale) * blend.x + rock_cracks(wp.xz * scale) * blend.y + rock_cracks(wp.xy * scale) * blend.z;
}

// Dual-frequency geological cliff relief: 6m-15m stepped rock strata + 0.7m-1.8m sharp fracture crevices
float cliff_height_field(vec3 wp, vec3 blend) {
	float warp = fbm3(wp.xz * 0.032 + vec2(wp.y * 0.015));
	float bed_phase = wp.y * 0.58 + wp.x * 0.06 - wp.z * 0.05 + warp * 5.2;
	float macro_strata = sin(bed_phase) * 0.5 + 0.5;
	macro_strata = smoothstep(0.18, 0.82, macro_strata) * 0.65 + pow(macro_strata, 3.0) * 0.35;
	float macro_blocks = triplanar_cracks(wp, blend, 0.095); // ~10.5m rock blocks & vertical joints
	float fine_fissures = triplanar_cracks(wp, blend, 0.62); // ~1.6m sharp rock cracks & ledges
	return macro_strata * 0.42 + macro_blocks * 0.34 + fine_fissures * 0.24;
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
	float slope = 1.0 - clamp(wn.y, 0.0, 1.0); // ~0.134 at 30°, ~0.412 at 54°

	// Domain-warped data UV (+-4.2m) eliminates 9.375m / 37.5m texel boundaries on soil, snow & shores!
	vec2 uv_warp = vec2(
		fbm3(v_world_pos.xz * 0.042 + vec2(5.2, 13.7)) - 0.5,
		fbm3(v_world_pos.xz * 0.042 + vec2(21.4, 8.9)) - 0.5
	) * vec2(8.5 / world_size.x, 8.5 / world_size.y);
	vec2 uv = clamp(v_world_uv + uv_warp, vec2(0.0), vec2(1.0));

	vec4 sa = texture(soil_tex_a, uv);
	vec4 sb = texture(soil_tex_b, uv);
	vec4 cl = texture(climate_tex, uv);
	vec4 eco = texture(canopy_coverage_tex, uv);

	float canopy_cov = eco.r;
	float floodplain_mask = eco.g;
	float wetland_mask = eco.b;

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

	float cam_dist = length(CAMERA_POSITION_WORLD - v_world_pos);
	float macro_var = fbm3(v_world_pos.xz * 0.008);
	float micro_detail = triplanar_fbm(v_world_pos, tri_blend, 0.18);
	float sand_ripples = sin((v_world_pos.x * 0.82 + v_world_pos.z * 0.57) * 0.45 + fbm3(v_world_pos.xz * 0.03) * 3.0) * 0.5 + 0.5;

	// 6 Physical Soil Colors + Floodplain Meadow & Wetland Peat-Moss enrichment
	vec3 c_alluvial = mix(vec3(0.15, 0.30, 0.09), vec3(0.11, 0.24, 0.07), moisture);
	vec3 c_forest = mix(vec3(0.17, 0.29, 0.10), vec3(0.12, 0.22, 0.07), moisture);
	vec3 c_steppe = mix(vec3(0.58, 0.43, 0.15), vec3(0.42, 0.35, 0.14), moisture);
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

	// Lush open Alluvial Floodplain meadow grass carpet vs damp mossy-peat Wetland floor
	vec3 meadow_lush = mix(vec3(0.16, 0.35, 0.10), vec3(0.23, 0.42, 0.12), macro_var);
	soil_col = mix(soil_col, meadow_lush, floodplain_mask * 0.72);
	vec3 wetland_peat = mix(vec3(0.09, 0.14, 0.06), vec3(0.15, 0.24, 0.08), micro_detail);
	soil_col = mix(soil_col, wetland_peat, wetland_mask * 0.78);

	// Synchronized via FloraLodConfig with LOD2 tree FarFade [1100m..1350m] so ground never darkens/pops early!
	float far_canopy_blend = smoothstep(canopy_ground_blend_start, canopy_ground_blend_end, cam_dist);
	float crown_dapple = fbm3(v_world_pos.xz * 0.095);
	vec3 near_humus = vec3(0.06, 0.11, 0.04);
	vec3 far_canopy_crown = mix(vec3(0.08, 0.18, 0.05), vec3(0.16, 0.31, 0.09), crown_dapple);
	vec3 canopy_ground_target = mix(near_humus, far_canopy_crown, far_canopy_blend);
	soil_col = mix(soil_col, canopy_ground_target, smoothstep(0.18, 0.72, canopy_cov) * mix(0.80, 0.92, far_canopy_blend));
	soil_col *= (0.82 + 0.36 * micro_detail);

	// Domain-warped shallow coral reef seabed -> coastal sand -> inland soil
	float h_warped = h + (micro_detail - 0.5) * 0.65;
	vec3 reef_bed = vec3(0.14, 0.48, 0.46);
	vec3 shore_col = mix(reef_bed, c_coastal * (0.86 + 0.28 * micro_detail), smoothstep(-3.5, 1.2, h_warped));
	vec3 terrain_col = mix(shore_col, soil_col, smoothstep(1.8, 7.8, h_warped));

	// Natural Point-Bar Sand/Gravel Bars along gentle meandering river bends + Wet riverbanks
	float river_bank = smoothstep(0.16, 0.72, river_mask) * (1.0 - wetland_mask * 0.65);
	float gentle_bar = smoothstep(0.12, 0.03, slope) * smoothstep(0.12, 0.44, river_mask) * (1.0 - smoothstep(0.55, 0.85, river_mask)) * (1.0 - wetland_mask * 0.80);
	float pebble_tex = triplanar_cracks(v_world_pos, tri_blend, 0.35);
	vec3 gravel_bar = mix(vec3(0.72, 0.67, 0.54), vec3(0.54, 0.50, 0.42), micro_detail * 0.6 + pebble_tex * 0.4);
	vec3 river_pebble = mix(vec3(0.34, 0.30, 0.24), vec3(0.22, 0.20, 0.17), pebble_tex * 0.5);
	terrain_col = mix(terrain_col, river_pebble, river_bank * 0.80);
	terrain_col = mix(terrain_col, gravel_bar, gentle_bar * 0.75);

	// Dual-Frequency Triplanar Cliffs (> 28-30°): macro sedimentary/granite strata + fine chiseled rock fissures + crevice AO
	float rock_exposure = max(
		smoothstep(0.095, 0.22, slope + (micro_detail - 0.5) * 0.05),
		max(smoothstep(0.20, 0.04, soil_depth) * 0.85, smoothstep(0.55, 0.92, bedrock_mask) * 0.65)
	);
	float cliff_h = cliff_height_field(v_world_pos, tri_blend);
	float fine_cracks = triplanar_cracks(v_world_pos, tri_blend, 0.62);
	float crevice_ao = mix(0.64, 1.12, smoothstep(0.08, 0.55, fine_cracks));

	vec3 granite_dark = vec3(0.19, 0.20, 0.22);
	vec3 granite_light = vec3(0.41, 0.40, 0.37);
	vec3 granite_rock = mix(granite_dark, granite_light, cliff_h) * crevice_ao;
	vec3 sandstone_rock = mix(vec3(0.42, 0.23, 0.13), vec3(0.66, 0.41, 0.23), cliff_h) * crevice_ao;
	vec3 rock_col = mix(granite_rock, sandstone_rock, smoothstep(0.20, 0.65, w_arid)) * (0.84 + 0.32 * micro_detail);
	terrain_col = mix(terrain_col, rock_col, rock_exposure);

	// Dynamic Stage 4 Snow Accumulation + High-Altitude Frost (sheds off steep cliffs >40°)
	vec4 wd = texture(weather_dynamic_tex, uv);
	float dyn_snow = wd.r;
	float dyn_wetness = wd.g;
	float dyn_cloud_shadow = wd.a;

	float snow_temp = smoothstep(1.5, -5.0, temp_c + (macro_var - 0.5) * 2.5) * 0.45;
	float snow_signal = max(snow_temp, dyn_snow);
	float snow_slope_mask = 1.0 - smoothstep(0.11, 0.26, slope + (cliff_h - 0.5) * 0.05);
	float snow_weight = clamp(snow_signal * snow_slope_mask * smoothstep(-0.2, 2.5, h_warped), 0.0, 1.0);
	vec3 snow_col = vec3(0.88, 0.92, 0.97) * (0.90 + 0.14 * micro_detail);
	terrain_col = mix(terrain_col, snow_col, snow_weight);

	// Wetness darkening & Cloud shadow pass
	terrain_col = mix(terrain_col, terrain_col * 0.64, max(dyn_wetness, wetland_mask * 0.55) * (1.0 - snow_weight) * 0.62);
	terrain_col *= (1.0 - dyn_cloud_shadow * 0.36);

	// Dual-Frequency Triplanar Normal Perturbation (eliminates flat gray polygon cliff facets!)
	float eps_m = 0.65;
	float h_c = mix(micro_detail, cliff_h, rock_exposure);
	float h_x = mix(triplanar_fbm(v_world_pos + vec3(eps_m, 0.0, 0.0), tri_blend, 0.18),
	                cliff_height_field(v_world_pos + vec3(eps_m, 0.0, 0.0), tri_blend), rock_exposure);
	float h_y = mix(triplanar_fbm(v_world_pos + vec3(0.0, eps_m, 0.0), tri_blend, 0.18),
	                cliff_height_field(v_world_pos + vec3(0.0, eps_m, 0.0), tri_blend), rock_exposure);
	float h_z = mix(triplanar_fbm(v_world_pos + vec3(0.0, 0.0, eps_m), tri_blend, 0.18),
	                cliff_height_field(v_world_pos + vec3(0.0, 0.0, eps_m), tri_blend), rock_exposure);
	vec3 grad_macro = clamp(vec3(h_x - h_c, h_y - h_c, h_z - h_c) / eps_m, vec3(-1.8), vec3(1.8));

	// Secondary fine cliff fracture normal within 550m
	float fine_cliff_fade = rock_exposure * (1.0 - smoothstep(180.0, 580.0, cam_dist));
	vec3 grad_fine = vec3(0.0);
	if (fine_cliff_fade > 0.02) {
		float ef = 0.18;
		float fc0 = fine_cracks;
		float fcx = triplanar_cracks(v_world_pos + vec3(ef, 0.0, 0.0), tri_blend, 0.62);
		float fcy = triplanar_cracks(v_world_pos + vec3(0.0, ef, 0.0), tri_blend, 0.62);
		float fcz = triplanar_cracks(v_world_pos + vec3(0.0, 0.0, ef), tri_blend, 0.62);
		grad_fine = clamp(vec3(fcx - fc0, fcy - fc0, fcz - fc0) / ef, vec3(-2.2), vec3(2.2)) * (0.48 * fine_cliff_fade);
	}

	float bump_strength = mix(0.28, 0.94, rock_exposure);
	bump_strength = mix(bump_strength, 0.22, snow_weight);

	// Far-distance canopy crown normal relief so splatted distant forest looks fluffy rather than flat
	float crown_bump = (crown_dapple - 0.5) * 0.45 * far_canopy_blend * smoothstep(0.25, 0.75, canopy_cov);

	float close_detail_fade = 1.0 - smoothstep(22.0, 68.0, cam_dist);
	float close_grain = triplanar_fbm(v_world_pos, tri_blend, 1.45) * 0.65 + triplanar_fbm(v_world_pos, tri_blend, 3.80) * 0.35;
	terrain_col *= mix(1.0, 0.80 + 0.40 * close_grain, close_detail_fade * (1.0 - snow_weight * 0.7));

	float bump_fade = 1.0 - smoothstep(650.0, 2800.0, cam_dist);
	float close_bump = (close_grain - 0.5) * 0.60 * close_detail_fade;
	vec3 bumped_world_n = safe_normalize(wn - (grad_macro * bump_strength * bump_fade + grad_fine) + vec3(close_bump + crown_bump, 0.0, -close_bump - crown_bump));
	NORMAL = safe_normalize((VIEW_MATRIX * vec4(bumped_world_n, 0.0)).xyz);

	// PBR roughness: matte organic soil/rock [0.83..0.96], damp sheen on marshes/wet banks
	float roughness = mix(0.92, 0.84, rock_exposure);
	roughness = mix(roughness, 0.64, max(river_bank * 0.60, wetland_mask * 0.65));
	roughness = mix(roughness, 0.56, smoothstep(0.15, 0.90, dyn_wetness));
	roughness = mix(roughness, 0.90, snow_weight);
	roughness = clamp(roughness, 0.52, 0.97);

	ALBEDO = terrain_col;
	ROUGHNESS = roughness;
	SPECULAR = mix(0.12, 0.34, max(max(river_bank * 0.5, wetland_mask * 0.55), dyn_wetness * 0.8));
}
