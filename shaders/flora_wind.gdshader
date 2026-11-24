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
uniform float fade_start = 1100.0;
uniform float fade_end = 1350.0;
uniform bool enable_distance_fade = false;

varying vec3 v_color;
varying vec3 v_inst_tint;
varying float v_inst_seed;
varying vec3 v_world_normal;
varying float v_snow_accum;
varying vec2 v_uv;
varying float v_surf_tag;  // < -0.5: solid herb/stone, ~0.0: woody bark, >= 0.25: leaf canopy_ao (0.54..1.06)
varying float v_sub_type;
varying float v_local_y;

vec2 hash21_v(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.xx + p3.yz) * p3.zy);
}

void vertex() {
	v_color = COLOR.rgb;
	v_inst_tint = dot(INSTANCE_CUSTOM.rgb, vec3(1.0)) > 0.02 ? INSTANCE_CUSTOM.rgb : vec3(1.0);
	v_inst_seed = INSTANCE_CUSTOM.a;
	v_uv = UV;
	v_surf_tag = UV2.x;
	v_sub_type = UV2.y;
	v_local_y = VERTEX.y;
	float stem_flex = COLOR.a;

	vec3 world_origin = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	vec2 world_uv = clamp(world_origin.xz / world_size, vec2(0.0), vec2(1.0));
	vec4 w_data = textureLod(wind_dir_speed_tex, world_uv, 0.0);
	v_snow_accum = textureLod(weather_dynamic_tex, world_uv, 0.0).r;
	v_world_normal = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz + vec3(0.0, 0.0001, 0.0));

	vec2 local_wind_dir = normalize(vec2(w_data.r * 2.0 - 1.0, w_data.g * 2.0 - 1.0) + vec2(0.0001));
	float local_wind_speed = w_data.b * 30.0 * global_wind_gust;

	// Per-Instance Organic GPU Deformation (0 extra VRAM: eliminates clone feeling!)
	vec2 inst_rnd = hash21_v(floor(world_origin.xz * 0.5));
	float twist_ang = (inst_rnd.x - 0.5) * 0.42 * clamp(VERTEX.y / 14.0, 0.0, 1.0);
	float c_tw = cos(twist_ang);
	float s_tw = sin(twist_ang);
	float rx = VERTEX.x * c_tw - VERTEX.z * s_tw;
	float rz = VERTEX.x * s_tw + VERTEX.z * c_tw;
	float aspect_var = 0.91 + inst_rnd.y * 0.20;
	VERTEX.x = rx * aspect_var;
	VERTEX.z = rz * aspect_var;

	// Permanent Wind Flagging on exposed windy ridges
	float flag_lean = smoothstep(11.0, 26.0, local_wind_speed) * clamp(VERTEX.y / 12.0, 0.0, 1.4) * 0.55;
	VERTEX.xz += local_wind_dir * flag_lean;

	float phase = dot(world_origin.xz, local_wind_dir) * 0.16;
	float freq = 1.2 + local_wind_speed * 0.12;

	vec2 sway = vec2(0.0);
	if (stem_flex < 0.22) {
		float flutter = sin(TIME * (freq * 1.9) + phase + VERTEX.x * 1.3 + VERTEX.z * 1.1);
		sway = local_wind_dir * flutter * (0.02 + local_wind_speed * 0.012) * stem_flex;
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

	if (enable_distance_fade) {
		float cam_dist = length(CAMERA_POSITION_WORLD - world_origin);
		if (cam_dist > fade_start) {
			float scale_fade = 1.0 - smoothstep(fade_start, fade_end, cam_dist);
			VERTEX *= max(scale_fade, 0.01);
		}
	}
}

void fragment() {
	if (v_surf_tag >= 0.25) {
		// ===================== BOTANICAL LEAF CARD WITH BAKED 3D CANOPY AO =====================
		float canopy_ao = clamp(v_surf_tag, 0.50, 1.10);
		vec4 leaf_tex;
		bool is_ginkgo_birch = (v_sub_type >= 1.5 && v_sub_type < 2.5);
		bool is_maple = (v_sub_type >= 3.5 && v_sub_type < 4.5);
		bool is_xeric = (v_sub_type >= 4.5);

		if (v_sub_type > 0.5 && v_sub_type < 1.5) {
			leaf_tex = texture(leaf_conifer_tex, v_uv);
		} else if (is_ginkgo_birch || is_maple) {
			leaf_tex = texture(leaf_acacia_tex, v_uv); // Real 1024x1024 fan/serrated leaf & twig silhouette
		} else if (v_sub_type >= 2.5 && v_sub_type < 3.5) {
			leaf_tex = texture(leaf_palm_tex, v_uv);
		} else {
			leaf_tex = texture(leaf_broadleaf_tex, v_uv);
		}

		ALPHA = leaf_tex.a;
		ALPHA_SCISSOR_THRESHOLD = 0.44;

		// Seasonal phenology:
		// Spring [0.00..0.25]: 88-92% fresh chlorophyll greens (<4% subtle young shoots)
		// Summer [0.25..0.50]: deep rich green
		// Autumn [0.50..0.75]: deciduous Ginkgo -> golden amber, Maple -> crimson-scarlet!
		// Winter [0.75..1.00]: muted russet/olive + snow accumulation on upper branches
		float spring_t = sin(clamp(season_phase / 0.25, 0.0, 1.0) * 3.14159);
		float summer_t = sin(clamp((season_phase - 0.22) / 0.30, 0.0, 1.0) * 3.14159);
		float phase_jitter = (v_inst_seed - 0.5) * 0.04;
		float autumn_t = sin(clamp((season_phase + phase_jitter - 0.49) / 0.27, 0.0, 1.0) * 3.14159);
		float winter_t = smoothstep(0.73, 0.88, season_phase) * (1.0 - smoothstep(0.95, 1.0, season_phase));

		float lum = dot(leaf_tex.rgb, vec3(0.299, 0.587, 0.114));
		vec3 base_leaf = leaf_tex.rgb;

		if (is_ginkgo_birch || is_maple) {
			// Preserve dark woody twig stems while synthesizing lush chlorophyll green leaf blades in Spring/Summer!
			float is_twig = smoothstep(0.24, 0.11, lum);
			vec3 spring_summer_blade = is_ginkgo_birch
				? vec3(0.16, 0.39, 0.11) * (0.48 + lum * 1.18)
				: vec3(0.14, 0.35, 0.10) * (0.46 + lum * 1.15);
			// <4% subtle warm young shoots in Spring
			if (v_inst_seed > 0.962) {
				spring_summer_blade = mix(spring_summer_blade, vec3(0.46, 0.52, 0.16) * (0.55 + lum), spring_t * 0.65);
			}
			vec3 green_deciduous = mix(spring_summer_blade, leaf_tex.rgb * 0.82, is_twig);

			// True Autumn color shift (ONLY active during Autumn / late-season!)
			vec3 autumn_target = is_maple
				? mix(vec3(0.76, 0.17, 0.08) * (0.45 + lum * 1.15), leaf_tex.rgb * 0.80, is_twig)
				: leaf_tex.rgb * vec3(1.04, 0.96, 0.84);

			base_leaf = mix(green_deciduous, autumn_target, autumn_t);
			base_leaf = mix(base_leaf, green_deciduous * vec3(0.74, 0.65, 0.52), winter_t * 0.72);
		} else if (is_xeric) {
			// Warm olive-savanna chlorophyll green year-round (never autumn orange!)
			base_leaf = leaf_tex.rgb * vec3(1.12, 1.02, 0.76);
		} else {
			// Evergreen broadleaf, conifer, palm/fern
			base_leaf = mix(base_leaf, base_leaf * vec3(1.06, 1.14, 0.92), spring_t * 0.24);
			base_leaf = mix(base_leaf, base_leaf * vec3(0.92, 0.98, 0.90), summer_t * 0.18);
			if (v_sub_type < 0.5) {
				base_leaf = mix(base_leaf, base_leaf * vec3(1.08, 0.96, 0.84), autumn_t * 0.18);
			}
		}

		// Apply per-instance hue multiplier + full 3D Canopy AO (35-45% darker inner/lower crown!)
		vec3 col = base_leaf * v_inst_tint * v_color * canopy_ao;

		float snow_dust = smoothstep(0.22, 0.62, v_snow_accum) * smoothstep(0.28, 0.72, v_world_normal.y);
		col = mix(col, vec3(0.88, 0.93, 0.98) * (0.78 + 0.22 * canopy_ao), snow_dust * 0.88);

		// Crisp 3D leaf vein normal relief
		vec3 vein_n = normalize(NORMAL + vec3(-dFdx(lum), -dFdy(lum), 0.0) * 1.40);
		NORMAL = vein_n;

		ALBEDO = col;
		ROUGHNESS = mix(0.74, 0.88, snow_dust);
		SPECULAR = 0.22;
		// Balanced backlight (0.25) weighted by canopy_ao so inner crown stays shaded instead of glowing flat!
		BACKLIGHT = col * (0.25 * canopy_ao) * (1.0 - snow_dust * 0.65);
	} else if (v_surf_tag > -0.5) {
		// ===================== WOODY BARK (TRUNKS, LIMBS, ROOTS, CULMS) =====================
		vec3 b_col = (v_sub_type > 0.5 && v_sub_type < 1.5)
			? texture(bark_pale_tex, v_uv).rgb
			: texture(bark_tex, v_uv).rgb;
		vec3 bark_final = v_color * mix(vec3(1.0), b_col * 1.38, 0.70);

		// Hoh Rainforest Mossy Bark only on humid forest trees (v_sub_type < 0.5)
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
}
