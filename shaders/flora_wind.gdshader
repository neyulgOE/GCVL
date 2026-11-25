shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled, diffuse_burley, specular_schlick_ggx, alpha_to_coverage;

uniform sampler2D wind_dir_speed_tex : filter_linear, repeat_disable;    // R=dir.x*0.5+0.5, G=dir.z*0.5+0.5, B=speed/30
uniform sampler2D weather_dynamic_tex : filter_linear, repeat_disable;   // R=SnowAccum, G=Wetness, B=Ice, A=CloudShadow

// 8 Single/Strip 1024x1024 RGBA8 botanical textures + 2 Specialty 2x2 Atlases
uniform sampler2D leaf_broadleaf_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D leaf_conifer_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D leaf_autumn_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D leaf_palm_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D flora_liana_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D leaf_araucaria_cypress_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D leaf_willow_acacia_berry_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D leaf_agave_bamboo_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D specialty_atlas_a_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D specialty_atlas_b_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D bark_tex : source_color, filter_linear_mipmap, repeat_enable;

uniform vec2 world_size = vec2(9600.0, 5400.0);
uniform float season_phase = 0.12;
uniform float global_wind_gust = 1.0;

// Unified LOD thresholds pushed from FloraLodConfig.cs
uniform int lod_level = 0;       // 0=LOD0, 1=LOD1, 2=LOD2, -1=L3..L6 Detail, -2=CloseUnderstory
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
uniform float close_understory_fade_start = 115.0;
uniform float close_understory_fade_end = 145.0;

varying vec3 v_color;
varying vec3 v_inst_tint;
varying float v_inst_seed;
varying vec3 v_world_normal;
varying float v_snow_accum;
varying vec2 v_uv;
varying float v_surf_tag;  // < -0.5: solid geo/herb, ~0.0: LOD2 woody bark, >= 0.25: leaf canopy_ao (0.50..1.10)
varying float v_sub_type;  // 0..15 texture selector (10..13 = Atlas-bucketed MultiMesh via INSTANCE_CUSTOM sub-UV!)
varying float v_local_y;
varying float v_inst_cam_dist;
varying float v_stem_flex;

vec2 hash21_v(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.xx + p3.yz) * p3.zy);
}

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
	vec3 world_origin = MODEL_MATRIX[3].xyz;
	float cam_dist = length(CAMERA_POSITION_WORLD - world_origin);
	v_inst_cam_dist = cam_dist;
	v_surf_tag = UV2.x;
	v_sub_type = UV2.y;
	v_local_y = VERTEX.y;

	// Atlas-bucketed MultiMesh (sub_type >= 9.5):
	//   INSTANCE_CUSTOM = vec4(u0, v0, uW, vH) sub-UV rect (with 0.004 mipmap gutter)
	//   COLOR.rgb = subtle organic instance tint (UseColors=true), COLOR.a = stem_flex * instance_flex
	bool is_atlas_bucket = (v_surf_tag >= 0.25 && v_sub_type >= 9.5 && v_sub_type < 13.5);
	float branch_phase = (v_surf_tag >= 0.25 && !is_atlas_bucket) ? COLOR.r * 6.28318 : fract(world_origin.x * 0.37 + world_origin.z * 0.71) * 6.28318;
	float stem_flex = COLOR.a;
	v_stem_flex = stem_flex;

	if (is_atlas_bucket) {
		v_uv = INSTANCE_CUSTOM.xy + UV * INSTANCE_CUSTOM.zw;
		v_inst_tint = clamp(COLOR.rgb, vec3(0.70), vec3(1.25));
		v_color = vec3(1.0);
		v_inst_seed = fract(world_origin.x * 0.13 + world_origin.z * 0.29);
	} else {
		v_uv = UV;
		v_color = v_surf_tag >= 0.25 ? vec3(1.0) : COLOR.rgb;
		// Keep subtle organic tint around 0.82..1.18 so flowers, berries & natural branch hues stay crisp!
		vec3 raw_tint = dot(INSTANCE_CUSTOM.rgb, vec3(1.0)) > 0.02 ? INSTANCE_CUSTOM.rgb : vec3(1.0);
		v_inst_tint = clamp(raw_tint, vec3(0.75), vec3(1.22));
		v_inst_seed = INSTANCE_CUSTOM.a;
	}

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

		if (!is_atlas_bucket) {
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
		}

		float phase = dot(world_origin.xz, local_wind_dir) * 0.16 + branch_phase;
		float freq = 1.2 + local_wind_speed * 0.12;

		vec2 sway = vec2(0.0);
		if (stem_flex < 0.015) {
			// Rigid shelf fungi, boulders, cactus
			sway = vec2(0.0);
		} else if (stem_flex >= 0.90) {
			// Gentle slow aquatic current / water-lily & sea-kelp wave
			float aq = sin(TIME * 1.15 + world_origin.x * 0.45 + world_origin.z * 0.35 + VERTEX.y * 0.9);
			float aq2 = cos(TIME * 0.85 + world_origin.z * 0.55);
			sway = vec2(aq, aq2) * (0.04 + clamp(VERTEX.y, 0.0, 2.0) * 0.08);
			VERTEX.y += aq * 0.015;
		} else if (stem_flex < 0.22) {
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
			sway = local_wind_dir * lean * (0.12 + local_wind_speed * 0.022) * stem_flex;
		}

		VERTEX.x += sway.x;
		VERTEX.z += sway.y;
	}
}

void fragment() {
	float dither = bayer4x4(ivec2(FRAGCOORD.xy));
	if (lod_level == 0) {
		float t01 = smoothstep(lod0_end - transition_half_band, lod0_end + transition_half_band, v_inst_cam_dist);
		if (t01 > dither) discard;
	} else if (lod_level == 1) {
		float t01 = smoothstep(lod1_start - transition_half_band, lod1_start + transition_half_band, v_inst_cam_dist);
		if (t01 <= dither) discard;
		float t12 = smoothstep(lod1_end - transition_half_band, lod1_end + transition_half_band, v_inst_cam_dist);
		if (t12 > dither) discard;
	} else if (lod_level == 2) {
		float t12 = smoothstep(lod2_start - transition_half_band, lod2_start + transition_half_band, v_inst_cam_dist);
		if (t12 <= dither) discard;
		float tfar = smoothstep(far_fade_start, far_fade_end, v_inst_cam_dist);
		if (tfar > dither) discard;
	} else if (lod_level == -2) {
		float tu = smoothstep(close_understory_fade_start, close_understory_fade_end, v_inst_cam_dist);
		if (tu > dither) discard;
	} else {
		float tdet = smoothstep(detail_fade_start, detail_fade_end, v_inst_cam_dist);
		if (tdet > dither) discard;
	}

	if (v_surf_tag >= 0.25) {
		float canopy_ao = clamp(v_surf_tag, 0.50, 1.10);
		vec4 leaf_tex;
		int st = int(floor(v_sub_type + 0.5));
		bool is_ginkgo_birch = (st == 2);
		bool is_maple = (st == 4);
		bool is_lush_understory = (st == 6 || st == 7 || st == 10 || st == 11);

		if (st == 1) {
			leaf_tex = texture(leaf_conifer_tex, v_uv);
		} else if (st == 2 || st == 4) {
			leaf_tex = texture(leaf_autumn_tex, v_uv);
		} else if (st == 3 || st == 6) {
			leaf_tex = texture(leaf_palm_tex, v_uv);
		} else if (st == 5 || st == 12) {
			leaf_tex = texture(leaf_willow_acacia_berry_tex, v_uv);
		} else if (st == 7) {
			leaf_tex = texture(flora_liana_tex, v_uv);
		} else if (st == 8) {
			leaf_tex = texture(leaf_araucaria_cypress_tex, v_uv);
		} else if (st == 9 || st == 13) {
			leaf_tex = texture(leaf_agave_bamboo_tex, v_uv);
		} else if (st == 10) {
			leaf_tex = texture(specialty_atlas_a_tex, v_uv);
		} else if (st == 11 || st == 14) {
			leaf_tex = texture(specialty_atlas_b_tex, v_uv);
		} else {
			leaf_tex = texture(leaf_broadleaf_tex, v_uv);
		}

		ALPHA = leaf_tex.a;
		ALPHA_SCISSOR_THRESHOLD = 0.42;

		float spring_t = sin(clamp(season_phase / 0.25, 0.0, 1.0) * 3.14159);
		float summer_t = sin(clamp((season_phase - 0.22) / 0.30, 0.0, 1.0) * 3.14159);
		float phase_jitter = (v_inst_seed - 0.5) * 0.04;
		float autumn_t = sin(clamp((season_phase + phase_jitter - 0.49) / 0.27, 0.0, 1.0) * 3.14159);
		float winter_t = smoothstep(0.73, 0.88, season_phase) * (1.0 - smoothstep(0.95, 1.0, season_phase));

		float lum = dot(leaf_tex.rgb, vec3(0.299, 0.587, 0.114));
		vec3 base_leaf = leaf_tex.rgb;

		if (is_ginkgo_birch || is_maple) {
			// Spring/Summer: lush deciduous green; Autumn: golden ginkgo/beech/birch or crimson maple!
			float is_twig = smoothstep(0.22, 0.10, lum);
			vec3 spring_summer_blade = is_ginkgo_birch
				? vec3(0.16, 0.40, 0.12) * (0.48 + lum * 1.18)
				: vec3(0.15, 0.36, 0.11) * (0.46 + lum * 1.15);
			vec3 green_deciduous = mix(spring_summer_blade, leaf_tex.rgb * 0.82, is_twig);
			vec3 autumn_target = is_maple
				? mix(vec3(0.78, 0.18, 0.08) * (0.46 + lum * 1.15), leaf_tex.rgb * 0.82, is_twig)
				: leaf_tex.rgb * vec3(1.04, 0.98, 0.86);
			base_leaf = mix(green_deciduous, autumn_target, autumn_t);
			base_leaf = mix(base_leaf, green_deciduous * vec3(0.74, 0.65, 0.52), winter_t * 0.70);
		} else if (st == 10 || st == 11) {
			// Preserve vibrant natural flower/lily/iris/heather colors; gently mute wildflowers in autumn/winter
			base_leaf = mix(base_leaf, base_leaf * vec3(1.06, 1.08, 0.98), spring_t * 0.16);
			base_leaf = mix(base_leaf, base_leaf * vec3(0.84, 0.78, 0.66), winter_t * 0.35);
		} else {
			base_leaf = mix(base_leaf, base_leaf * vec3(1.05, 1.10, 0.94), spring_t * 0.18);
			base_leaf = mix(base_leaf, base_leaf * vec3(0.94, 0.98, 0.92), summer_t * 0.14);
			if (st == 0 || st == 8) {
				base_leaf = mix(base_leaf, base_leaf * vec3(1.12, 0.96, 0.76), autumn_t * 0.22);
			}
		}

		vec3 col = base_leaf * v_inst_tint * v_color * canopy_ao;

		float snow_dust = smoothstep(0.24, 0.64, v_snow_accum) * smoothstep(0.28, 0.72, v_world_normal.y);
		if (v_stem_flex >= 0.90) snow_dust = 0.0; // No snow on floating lilies or underwater kelp
		col = mix(col, vec3(0.88, 0.93, 0.98) * (0.78 + 0.22 * canopy_ao), snow_dust * 0.85);

		vec3 vein_n = normalize(NORMAL + vec3(-dFdx(lum), -dFdy(lum), 0.0) * 1.25);
		NORMAL = vein_n;

		ALBEDO = col;
		ROUGHNESS = mix(is_lush_understory ? 0.64 : 0.74, 0.88, snow_dust);
		SPECULAR = is_lush_understory ? 0.26 : 0.20;
		float bl_strength = is_lush_understory ? 0.56 : 0.26;
		BACKLIGHT = col * (bl_strength * canopy_ao) * (1.0 - snow_dust * 0.65);
	} else if (v_surf_tag > -0.5) {
		// LOD2 Woody Bark
		vec3 b_col = texture(bark_tex, v_uv).rgb;
		vec3 bark_final = v_color * mix(vec3(1.0), b_col * 1.35, 0.65);
		float bark_snow = smoothstep(0.28, 0.68, v_snow_accum) * smoothstep(0.38, 0.80, v_world_normal.y);
		bark_final = mix(bark_final, vec3(0.88, 0.92, 0.97), bark_snow * 0.75);
		ALBEDO = bark_final;
		ROUGHNESS = 0.93;
		SPECULAR = 0.07;
	} else {
		// Solid geological deposits & boulders
		vec3 col = v_color * v_inst_tint;
		float snow_dust = smoothstep(0.24, 0.64, v_snow_accum) * smoothstep(0.30, 0.75, v_world_normal.y);
		col = mix(col, vec3(0.88, 0.93, 0.98), snow_dust * 0.85);
		ALBEDO = col;
		ROUGHNESS = 0.88;
		SPECULAR = 0.12;
	}

	if (lod_debug_mode == 1) {
		vec3 dbg_col = vec3(0.32, 0.82, 0.42);
		if (lod_level == 0) dbg_col = vec3(1.0, 0.15, 0.15);
		else if (lod_level == 1) dbg_col = vec3(1.0, 0.85, 0.10);
		else if (lod_level == 2) dbg_col = vec3(0.15, 0.65, 1.00);
		float dbg_shade = v_surf_tag >= 0.25 ? clamp(v_surf_tag, 0.62, 1.05) : 0.78;
		ALBEDO = dbg_col * dbg_shade;
		ROUGHNESS = 0.86;
		SPECULAR = 0.06;
		BACKLIGHT = dbg_col * 0.20;
	}
}
