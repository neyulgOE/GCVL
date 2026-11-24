shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled, diffuse_burley, specular_schlick_ggx, alpha_to_coverage;

uniform sampler2D wind_dir_speed_tex : filter_linear, repeat_disable; // R=dir.x*0.5+0.5, G=dir.z*0.5+0.5, B=speed/30
uniform sampler2D weather_dynamic_tex : filter_linear, repeat_disable; // R=SnowAccum, G=Wetness, B=Ice, A=CloudShadow
uniform sampler2D leaf_broadleaf_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D leaf_conifer_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D leaf_acacia_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D leaf_palm_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D bark_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D bark_pale_tex : source_color, filter_linear_mipmap, repeat_enable;

uniform vec2 world_size = vec2(9600.0, 5400.0);
uniform float season_phase = 0.12;
uniform float global_wind_gust = 1.0;

// Unified LOD thresholds pushed from FloraLodConfig.cs (no mismatched magic numbers!)
uniform int lod_level = 0;       // 0=LOD0, 1=LOD1, 2=LOD2, -1=L3..L6 Detail
uniform int lod_debug_mode = 0;  // 0=Normal, 1=LOD Debug View (Red/Yellow/Cyan)
uniform float lod0_end = 150.0;
uniform float lod1_start = 150.0;
uniform float lod1_end = 450.0;
uniform float lod2_start = 450.0;
uniform float transition_half_band = 15.0;
uniform float far_fade_start = 1100.0;
uniform float far_fade_end = 1350.0;
uniform float detail_fade_start = 310.0;
uniform float detail_fade_end = 400.0;
uniform float close_understory_fade_start = 75.0;
uniform float close_understory_fade_end = 100.0;

varying vec3 v_color;
varying vec3 v_inst_tint;
varying float v_inst_seed;
varying vec3 v_world_normal;
varying float v_snow_accum;
varying vec2 v_uv;
varying float v_surf_tag;  // < -0.5: solid herb/stone, ~0.0: woody bark, >= 0.25: leaf canopy_ao (0.54..1.06)
varying float v_sub_type;
varying float v_local_y;
varying float v_inst_cam_dist;

vec2 hash21_v(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.xx + p3.yz) * p3.zy);
}

// Ordered 4x4 Bayer threshold in (0.03125 .. 0.96875) for complementary zero-hole LOD crossfades
float bayer4x4(ivec2 p) {
	int idx = ((p.y & 3) << 2) + (p.x & 3);
	const float bayer[16] = float[16](
		 0.5 / 16.0,  8.5 / 16.0,  2.5 / 16.0, 10.5 / 16.0,
		12.5 / 16.0,  4.5 / 16.0, 14.5 / 16.0,  6.5 / 16.0,
		 3.5 / 16.0, 11.5 / 16.0,  1.5 / 16.0,  9.5 / 16.0,
		15.5 / 16.0,  7.5 / 16.0, 13.5 / 16.0,  5.5 / 16.0
	);
	return bayer[idx];
}

void vertex() {
	// For leaf cards (UV2.x >= 0.25), COLOR.r carries per-branch out-of-phase wind offset [0..1]!
	float branch_phase = UV2.x >= 0.25 ? COLOR.r * 6.28318 : 0.0;
	v_color = UV2.x >= 0.25 ? vec3(1.0) : COLOR.rgb;
	v_inst_tint = dot(INSTANCE_CUSTOM.rgb, vec3(1.0)) > 0.02 ? INSTANCE_CUSTOM.rgb : vec3(1.0);
	v_inst_seed = INSTANCE_CUSTOM.a;
	v_uv = UV;
	v_surf_tag = UV2.x;
	v_sub_type = UV2.y;
	v_local_y = VERTEX.y;
	float stem_flex = COLOR.a;

	// Exact per-instance world position (independent of cell center offset!)
	vec3 world_origin = MODEL_MATRIX[3].xyz;
	float cam_dist = length(CAMERA_POSITION_WORLD - world_origin);
	v_inst_cam_dist = cam_dist;

	// Early vertex collapse for instances in border cells that lie strictly outside this LOD's dither band
	bool culled_by_lod = false;
	if (lod_level == 0) {
		culled_by_lod = (cam_dist >= lod0_end + transition_half_band);
	} else if (lod_level == 1) {
		culled_by_lod = (cam_dist <= lod1_start - transition_half_band) || (cam_dist >= lod1_end + transition_half_band);
	} else if (lod_level == 2) {
		culled_by_lod = (cam_dist <= lod2_start - transition_half_band) || (cam_dist >= far_fade_end);
	} else if (lod_level == -2) {
		culled_by_lod = (cam_dist >= close_understory_fade_end);
	} else {
		culled_by_lod = (cam_dist >= detail_fade_end);
	}

	if (culled_by_lod) {
		VERTEX = vec3(0.0);
		v_snow_accum = 0.0;
		v_world_normal = vec3(0.0, 1.0, 0.0);
	} else {
		vec2 world_uv = clamp(world_origin.xz / world_size, vec2(0.0), vec2(1.0));
		vec4 w_data = textureLod(wind_dir_speed_tex, world_uv, 0.0);
		v_snow_accum = textureLod(weather_dynamic_tex, world_uv, 0.0).r;
		v_world_normal = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz + vec3(0.0, 0.0001, 0.0));

		vec2 local_wind_dir = normalize(vec2(w_data.r * 2.0 - 1.0, w_data.g * 2.0 - 1.0) + vec2(0.0001));
		float local_wind_speed = w_data.b * 30.0 * global_wind_gust;

		// Per-Instance Organic GPU Deformation
		vec2 inst_rnd = hash21_v(floor(world_origin.xz * 0.5));
		float twist_ang = (inst_rnd.x - 0.5) * 0.42 * clamp(VERTEX.y / 14.0, 0.0, 1.0);
		float c_tw = cos(twist_ang);
		float s_tw = sin(twist_ang);
		float rx = VERTEX.x * c_tw - VERTEX.z * s_tw;
		float rz = VERTEX.x * s_tw + VERTEX.z * c_tw;
		float aspect_var = 0.91 + inst_rnd.y * 0.20;
		VERTEX.x = rx * aspect_var;
		VERTEX.z = rz * aspect_var;

		float flag_lean = smoothstep(11.0, 26.0, local_wind_speed) * clamp(VERTEX.y / 12.0, 0.0, 1.4) * 0.55;
		VERTEX.xz += local_wind_dir * flag_lean;

		float phase = dot(world_origin.xz, local_wind_dir) * 0.16 + branch_phase;
		float freq = 1.2 + local_wind_speed * 0.12;

		vec2 sway = vec2(0.0);
		if (stem_flex < 0.22) {
			float flutter = sin(TIME * (freq * 1.9) + phase + VERTEX.x * 1.3 + VERTEX.z * 1.1);
			float cross_fl = cos(TIME * (freq * 1.45) + phase * 1.37);
			vec2 perp_dir = vec2(-local_wind_dir.y, local_wind_dir.x);
			sway = (local_wind_dir * flutter + perp_dir * cross_fl * 0.45) * (0.028 + local_wind_speed * 0.013) * stem_flex;
		} else if (stem_flex < 0.60) {
			float h_norm = clamp(VERTEX.y / 6.0, 0.0, 1.4);
			float arc = h_norm * h_norm;
			float gust = sin(TIME * freq + phase) * 0.55 + sin(TIME * freq * 2.1 + phase * 1.6) * 0.35;
			float lean = smoothstep(4.0, 24.0, local_wind_speed) * 0.65 + gust * 0.45;
			sway = local_wind_dir * lean * arc * (0.18 + local_wind_speed * 0.032) * stem_flex;
		} else {
			float wave = sin(dot(world_origin.xz + VERTEX.xz, local_wind_dir) * 0.28 - TIME * (freq * 1.35));
			float gust = sin(TIME * freq * 2.3 + phase) * 0.35;
			float lean = smoothstep(3.0, 22.0, local_wind_speed) * 0.55 + (wave * 0.75 + gust);
			sway = local_wind_dir * lean * (0.14 + local_wind_speed * 0.026) * stem_flex;
		}

		VERTEX.x += sway.x;
		VERTEX.z += sway.y;
	}
}

void fragment() {
	// Complementary Bayer 4x4 Screen-Door Dither Crossfade (zero popping, zero gap!)
	float dither = bayer4x4(ivec2(FRAGCOORD.xy));
	if (lod_level == 0) {
		float t01 = smoothstep(lod0_end - transition_half_band, lod0_end + transition_half_band, v_inst_cam_dist);
		if (t01 > dither) {
			discard;
		}
	} else if (lod_level == 1) {
		float t01 = smoothstep(lod1_start - transition_half_band, lod1_start + transition_half_band, v_inst_cam_dist);
		if (t01 <= dither) {
			discard;
		}
		float t12 = smoothstep(lod1_end - transition_half_band, lod1_end + transition_half_band, v_inst_cam_dist);
		if (t12 > dither) {
			discard;
		}
	} else if (lod_level == 2) {
		float t12 = smoothstep(lod2_start - transition_half_band, lod2_start + transition_half_band, v_inst_cam_dist);
		if (t12 <= dither) {
			discard;
		}
		float tfar = smoothstep(far_fade_start, far_fade_end, v_inst_cam_dist);
		if (tfar > dither) {
			discard;
		}
	} else if (lod_level == -2) {
		float tu = smoothstep(close_understory_fade_start, close_understory_fade_end, v_inst_cam_dist);
		if (tu > dither) {
			discard;
		}
	} else {
		float tdet = smoothstep(detail_fade_start, detail_fade_end, v_inst_cam_dist);
		if (tdet > dither) {
			discard;
		}
	}

	if (v_surf_tag >= 0.25) {
		// ===================== BOTANICAL LEAF CARD WITH BAKED 3D CANOPY AO =====================
		float canopy_ao = clamp(v_surf_tag, 0.50, 1.10);
		vec4 leaf_tex;
		bool is_ginkgo_birch = (v_sub_type >= 1.5 && v_sub_type < 2.5);
		bool is_palm_fern = (v_sub_type >= 2.5 && v_sub_type < 3.5);
		bool is_maple = (v_sub_type >= 3.5 && v_sub_type < 4.5);
		bool is_xeric = (v_sub_type >= 4.5 && v_sub_type < 5.5);
		bool is_lush_understory = (v_sub_type >= 5.5);

		if (v_sub_type > 0.5 && v_sub_type < 1.5) {
			leaf_tex = texture(leaf_conifer_tex, v_uv);
		} else if (is_ginkgo_birch || is_maple) {
			leaf_tex = texture(leaf_acacia_tex, v_uv);
		} else if (is_palm_fern || is_lush_understory) {
			leaf_tex = texture(leaf_palm_tex, v_uv);
		} else {
			leaf_tex = texture(leaf_broadleaf_tex, v_uv);
		}

		ALPHA = leaf_tex.a;
		ALPHA_SCISSOR_THRESHOLD = 0.44;

		float spring_t = sin(clamp(season_phase / 0.25, 0.0, 1.0) * 3.14159);
		float summer_t = sin(clamp((season_phase - 0.22) / 0.30, 0.0, 1.0) * 3.14159);
		float phase_jitter = (v_inst_seed - 0.5) * 0.04;
		float autumn_t = sin(clamp((season_phase + phase_jitter - 0.49) / 0.27, 0.0, 1.0) * 3.14159);
		float winter_t = smoothstep(0.73, 0.88, season_phase) * (1.0 - smoothstep(0.95, 1.0, season_phase));

		float lum = dot(leaf_tex.rgb, vec3(0.299, 0.587, 0.114));
		vec3 base_leaf = leaf_tex.rgb;

		if (is_ginkgo_birch || is_maple) {
			float is_twig = smoothstep(0.24, 0.11, lum);
			vec3 spring_summer_blade = is_ginkgo_birch
				? vec3(0.16, 0.39, 0.11) * (0.48 + lum * 1.18)
				: vec3(0.14, 0.35, 0.10) * (0.46 + lum * 1.15);
			if (v_inst_seed > 0.962) {
				spring_summer_blade = mix(spring_summer_blade, vec3(0.46, 0.52, 0.16) * (0.55 + lum), spring_t * 0.65);
			}
			vec3 green_deciduous = mix(spring_summer_blade, leaf_tex.rgb * 0.82, is_twig);

			vec3 autumn_target = is_maple
				? mix(vec3(0.76, 0.17, 0.08) * (0.45 + lum * 1.15), leaf_tex.rgb * 0.80, is_twig)
				: leaf_tex.rgb * vec3(1.04, 0.96, 0.84);

			base_leaf = mix(green_deciduous, autumn_target, autumn_t);
			base_leaf = mix(base_leaf, green_deciduous * vec3(0.74, 0.65, 0.52), winter_t * 0.72);
		} else if (is_xeric) {
			base_leaf = leaf_tex.rgb * vec3(1.12, 1.02, 0.76);
		} else {
			base_leaf = mix(base_leaf, base_leaf * vec3(1.06, 1.14, 0.92), spring_t * 0.24);
			base_leaf = mix(base_leaf, base_leaf * vec3(0.92, 0.98, 0.90), summer_t * 0.18);
			if (v_sub_type < 0.5) {
				base_leaf = mix(base_leaf, base_leaf * vec3(1.08, 0.96, 0.84), autumn_t * 0.18);
			}
		}

		vec3 col = base_leaf * v_inst_tint * v_color * canopy_ao;

		float snow_dust = smoothstep(0.22, 0.62, v_snow_accum) * smoothstep(0.28, 0.72, v_world_normal.y);
		col = mix(col, vec3(0.88, 0.93, 0.98) * (0.78 + 0.22 * canopy_ao), snow_dust * 0.88);

		vec3 vein_n = normalize(NORMAL + vec3(-dFdx(lum), -dFdy(lum), 0.0) * 1.40);
		NORMAL = vein_n;

		ALBEDO = col;
		ROUGHNESS = mix(is_lush_understory ? 0.62 : 0.74, 0.88, snow_dust);
		SPECULAR = is_lush_understory ? 0.28 : 0.22;
		float bl_strength = is_lush_understory ? 0.62 : 0.26;
		BACKLIGHT = col * (bl_strength * canopy_ao) * (1.0 - snow_dust * 0.65);
	} else if (v_surf_tag > -0.5) {
		// ===================== WOODY BARK =====================
		vec3 b_col = (v_sub_type > 0.5 && v_sub_type < 1.5)
			? texture(bark_pale_tex, v_uv).rgb
			: texture(bark_tex, v_uv).rgb;
		vec3 bark_final = v_color * mix(vec3(1.0), b_col * 1.38, 0.70);

		float moss_mask = 0.0;
		vec3 moss_col = mix(vec3(0.13, 0.26, 0.07), vec3(0.22, 0.36, 0.10), b_col.g);
		if (v_sub_type < 0.5) {
			float base_moss = smoothstep(3.8, 0.35, v_local_y) * 0.68;
			float limb_moss = smoothstep(0.30, 0.78, v_world_normal.y) * 0.62;
			moss_mask = clamp(max(base_moss, limb_moss) * smoothstep(0.10, 0.55, b_col.r), 0.0, 0.80);
			bark_final = mix(bark_final, moss_col, moss_mask);
		}

		float bark_snow = smoothstep(0.28, 0.68, v_snow_accum) * smoothstep(0.38, 0.80, v_world_normal.y);
		bark_final = mix(bark_final, vec3(0.88, 0.92, 0.97), bark_snow * 0.75);

		ALBEDO = bark_final;
		ROUGHNESS = 0.93;
		SPECULAR = 0.07;
		BACKLIGHT = moss_col * (0.10 * moss_mask);
	} else {
		// ===================== SOLID HERBS, REEDS, AGAVE, BOULDERS & MUSHROOMS =====================
		vec3 col = v_color * v_inst_tint;
		float autumn_t = sin(clamp((season_phase - 0.49) / 0.27, 0.0, 1.0) * 3.14159);
		float is_herb = step(0.10, COLOR.a);
		col = mix(col, col * vec3(1.12, 0.92, 0.72), autumn_t * 0.32 * is_herb);

		float snow_dust = smoothstep(0.24, 0.64, v_snow_accum) * smoothstep(0.30, 0.75, v_world_normal.y);
		col = mix(col, vec3(0.88, 0.93, 0.98), snow_dust * 0.85);

		ALBEDO = col;
		ROUGHNESS = 0.88;
		SPECULAR = 0.12;
		BACKLIGHT = col * (0.24 * is_herb);
	}

	// ===================== P0 LOD DEBUG VIEW OVERRIDE [L] =====================
	if (lod_debug_mode == 1) {
		vec3 dbg_col = vec3(0.32, 0.82, 0.42); // L3..L6 understory/detail flora
		if (lod_level == 0) {
			dbg_col = vec3(1.0, 0.15, 0.15); // LOD0 (0-150m): Vivid Red
		} else if (lod_level == 1) {
			dbg_col = vec3(1.0, 0.85, 0.10); // LOD1 (150-450m): Bright Yellow
		} else if (lod_level == 2) {
			dbg_col = vec3(0.15, 0.65, 1.00); // LOD2 (450-1350m): Cyan / Blue
		}
		float dbg_shade = v_surf_tag >= 0.25 ? clamp(v_surf_tag, 0.62, 1.05) : 0.78;
		ALBEDO = dbg_col * dbg_shade;
		ROUGHNESS = 0.86;
		SPECULAR = 0.06;
		BACKLIGHT = dbg_col * 0.20;
	}
}
