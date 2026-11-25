shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

// Dedicated Surface 0 PBR Bark + Organic World-Space Moss Shader (4 Seamless 1K PBR Bark Sets + CC0 Moss)
// Synchronized 100% with FloraLodConfig.cs Bayer 4x4 LOD crossfade & [L] LOD Debug View.

uniform sampler2D bark_hardwood_albedo : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D bark_hardwood_normal : hint_normal, filter_linear_mipmap, repeat_enable;
uniform sampler2D bark_hardwood_roughness : filter_linear_mipmap, repeat_enable;

uniform sampler2D bark_conifer_albedo : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D bark_conifer_normal : hint_normal, filter_linear_mipmap, repeat_enable;
uniform sampler2D bark_conifer_roughness : filter_linear_mipmap, repeat_enable;

uniform sampler2D bark_ancient_mossy_albedo : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D bark_ancient_mossy_normal : hint_normal, filter_linear_mipmap, repeat_enable;
uniform sampler2D bark_ancient_mossy_roughness : filter_linear_mipmap, repeat_enable;

uniform sampler2D bark_sequoia_conifer_albedo : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D bark_sequoia_conifer_normal : hint_normal, filter_linear_mipmap, repeat_enable;
uniform sampler2D bark_sequoia_conifer_roughness : filter_linear_mipmap, repeat_enable;

uniform sampler2D moss_albedo : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D moss_normal : hint_normal, filter_linear_mipmap, repeat_enable;

uniform sampler2D wind_dir_speed_tex : filter_linear, repeat_disable;
uniform sampler2D weather_dynamic_tex : filter_linear, repeat_disable;
uniform sampler2D climate_tex : filter_linear, repeat_disable;
uniform sampler2D canopy_coverage_tex : filter_linear, repeat_disable;

uniform vec2 world_size = vec2(9600.0, 5400.0);
uniform float global_wind_gust = 1.0;

// Unified LOD thresholds pushed from FloraLodConfig.cs
uniform int lod_level = 0;       // 0=LOD0, 1=LOD1, 2=LOD2, -1=Detail, -2=CloseUnderstory
uniform int lod_debug_mode = 0;  // 0=Normal, 1=LOD Debug View
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
varying vec3 v_world_pos;
varying vec3 v_world_normal;
varying vec2 v_uv;
varying float v_bark_style;   // UV2.x: 0=Hardwood, 1=Conifer, 2=PaleBirch, 3=DryDesert, 4=AncientMossy, 5=SequoiaConifer, 6=ColumnarCactus
varying float v_moss_mult;    // UV2.y: moss multiplier (0.0=cactus/desert, 1.0=forest/log)
varying float v_local_y;
varying float v_snow_accum;
varying float v_site_moss;
varying float v_inst_cam_dist;

vec2 hash21_v(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.xx + p3.yz) * p3.zy);
}

float hash21(vec2 p) {
	p = fract(p * vec2(127.1, 311.7));
	p += dot(p, p + 34.23);
	return fract(p.x * p.y);
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
	v_color = COLOR.rgb;
	v_uv = UV;
	v_bark_style = UV2.x;
	v_moss_mult = UV2.y;
	v_local_y = VERTEX.y;
	float stem_flex = COLOR.a;

	vec3 world_origin = MODEL_MATRIX[3].xyz;
	float cam_dist = length(CAMERA_POSITION_WORLD - world_origin);
	v_inst_cam_dist = cam_dist;

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
		v_world_pos = world_origin;
		v_world_normal = vec3(0.0, 1.0, 0.0);
		v_snow_accum = 0.0;
		v_site_moss = 0.0;
	} else {
		vec2 world_uv = clamp(world_origin.xz / world_size, vec2(0.0), vec2(1.0));
		vec4 w_data = textureLod(wind_dir_speed_tex, world_uv, 0.0);
		v_snow_accum = textureLod(weather_dynamic_tex, world_uv, 0.0).r;
		float moisture = textureLod(climate_tex, world_uv, 0.0).g;
		float canopy_cov = textureLod(canopy_coverage_tex, world_uv, 0.0).r;
		v_site_moss = clamp(0.45 + moisture * 0.45 + canopy_cov * 0.40, 0.25, 1.25);

		vec2 local_wind_dir = normalize(vec2(w_data.r * 2.0 - 1.0, w_data.g * 2.0 - 1.0) + vec2(0.0001));
		float local_wind_speed = w_data.b * 30.0 * global_wind_gust;

		// Identical per-instance twist & aspect deformation as flora_wind.gdshader
		vec2 inst_rnd = hash21_v(floor(world_origin.xz * 0.5));
		float twist_ang = (inst_rnd.x - 0.5) * 0.42 * clamp(VERTEX.y / 14.0, 0.0, 1.0);
		float c_tw = cos(twist_ang);
		float s_tw = sin(twist_ang);
		float rx = VERTEX.x * c_tw - VERTEX.z * s_tw;
		float rz = VERTEX.x * s_tw + VERTEX.z * c_tw;
		float aspect_var = 0.91 + inst_rnd.y * 0.20;
		VERTEX.x = rx * aspect_var;
		VERTEX.z = rz * aspect_var;

		if (stem_flex > 0.005) {
			float flag_lean = smoothstep(11.0, 26.0, local_wind_speed) * clamp(VERTEX.y / 12.0, 0.0, 1.4) * 0.55;
			VERTEX.xz += local_wind_dir * flag_lean;
			float phase = dot(world_origin.xz, local_wind_dir) * 0.16;
			float freq = 1.2 + local_wind_speed * 0.12;
			float h_norm = clamp(VERTEX.y / 8.0, 0.0, 1.5);
			float sway_mag = sin(TIME * freq + phase) * (0.04 + local_wind_speed * 0.012) * stem_flex * h_norm;
			VERTEX.xz += local_wind_dir * sway_mag;
		}

		v_world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
		v_world_normal = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz + vec3(0.0, 0.0001, 0.0));
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

	vec3 bark_alb;
	vec3 bark_nrm;
	float bark_rgh;
	bool is_cactus = (v_bark_style >= 5.5);

	if (v_bark_style >= 3.5 && v_bark_style < 4.5) {
		// Primeval Ancient Mossy Giant Bark (Banyan, Sacred Hardwood, Steppe Oak, Bald Cypress, Mangrove)
		bark_alb = texture(bark_ancient_mossy_albedo, v_uv).rgb;
		bark_nrm = texture(bark_ancient_mossy_normal, v_uv).rgb;
		bark_rgh = texture(bark_ancient_mossy_roughness, v_uv).r;
	} else if (v_bark_style >= 4.5 && v_bark_style < 5.5) {
		// Sequoia / Araucaria / Boreal Conifer Red-Brown Furrowed Bark
		bark_alb = texture(bark_sequoia_conifer_albedo, v_uv).rgb;
		bark_nrm = texture(bark_sequoia_conifer_normal, v_uv).rgb;
		bark_rgh = texture(bark_sequoia_conifer_roughness, v_uv).r;
	} else if (v_bark_style >= 0.5 && v_bark_style < 1.5) {
		// Standard Conifer Bark
		bark_alb = texture(bark_conifer_albedo, v_uv).rgb;
		bark_nrm = texture(bark_conifer_normal, v_uv).rgb;
		bark_rgh = texture(bark_conifer_roughness, v_uv).r;
	} else if (v_bark_style >= 1.5 && v_bark_style < 2.5) {
		// Silver Birch Pale Bark with dark horizontal lenticel bands (procedural over hardwood normal)
		float lenticel = smoothstep(0.58, 0.78, value_noise(vec2(v_uv.x * 4.5, v_uv.y * 28.0)));
		bark_alb = mix(vec3(0.84, 0.82, 0.77), vec3(0.28, 0.25, 0.22), lenticel * 0.72);
		bark_nrm = texture(bark_hardwood_normal, v_uv).rgb;
		bark_rgh = max(texture(bark_hardwood_roughness, v_uv).r, 0.82);
	} else if (is_cactus) {
		// Columnar Euphorbia Cactus: waxy ribbed green succulent stem (moss_mult = 0)
		bark_alb = v_color * (0.85 + 0.15 * texture(bark_hardwood_roughness, v_uv).r);
		bark_nrm = texture(bark_hardwood_normal, v_uv * vec2(2.0, 0.5)).rgb;
		bark_rgh = 0.68;
	} else {
		// Mid-canopy Hardwood / Fallen Logs / Desert Bark
		bark_alb = texture(bark_hardwood_albedo, v_uv).rgb;
		bark_nrm = texture(bark_hardwood_normal, v_uv).rgb;
		bark_rgh = texture(bark_hardwood_roughness, v_uv).r;
	}

	vec3 final_albedo = is_cactus ? bark_alb : bark_alb * mix(vec3(1.0), v_color * 2.0, 0.36);
	vec3 final_normal = bark_nrm;

	float moss_weight = 0.0;
	vec3 moss_alb = vec3(0.18, 0.32, 0.11);
	if (v_moss_mult > 0.01 && !is_cactus) {
		vec2 moss_uv = v_world_pos.xz * 0.55 + vec2(v_world_pos.y * 0.35, -v_world_pos.y * 0.25);
		float moss_noise = value_noise(v_world_pos.xz * 0.78 + vec2(v_world_pos.y * 0.55)) * 0.65
		                 + value_noise(v_world_pos.xz * 2.25 - vec2(v_world_pos.y * 1.25)) * 0.35;

		float organic_climb_h = 3.85 + (moss_noise - 0.5) * 2.6;
		float base_moss = smoothstep(organic_climb_h, 0.35, v_local_y) * smoothstep(0.16, 0.56, moss_noise + 0.24);
		float upward_moss = smoothstep(0.18, 0.58, v_world_normal.y) * smoothstep(0.18, 0.56, moss_noise + 0.20);
		moss_weight = clamp(max(base_moss * 0.96, upward_moss * 0.98) * v_moss_mult * v_site_moss, 0.0, 0.95);

		vec3 moss_raw = texture(moss_albedo, moss_uv).rgb;
		moss_alb = clamp(moss_raw * vec3(0.86, 1.38, 0.54) + vec3(0.02, 0.06, 0.01), vec3(0.0), vec3(1.0));
		vec3 moss_nrm = texture(moss_normal, moss_uv).rgb;

		final_albedo = mix(final_albedo, moss_alb, moss_weight);
		final_normal = mix(final_normal, moss_nrm, moss_weight * 0.85);
	}

	float snow_dust = smoothstep(0.26, 0.65, v_snow_accum) * smoothstep(0.36, 0.78, v_world_normal.y);
	final_albedo = mix(final_albedo, vec3(0.86, 0.91, 0.96), snow_dust * 0.82);

	ALBEDO = final_albedo;
	NORMAL_MAP = final_normal;
	NORMAL_MAP_DEPTH = is_cactus ? 0.55 : 1.15;
	ROUGHNESS = is_cactus ? 0.68 : clamp(mix(max(bark_rgh, 0.82), 0.94, max(moss_weight, snow_dust)), 0.80, 0.97);
	SPECULAR = is_cactus ? 0.24 : 0.08;
	BACKLIGHT = moss_alb * (0.14 * moss_weight);

	if (lod_debug_mode == 1) {
		vec3 dbg_col = vec3(0.32, 0.82, 0.42);
		if (lod_level == 0) dbg_col = vec3(1.0, 0.15, 0.15);
		else if (lod_level == 1) dbg_col = vec3(1.0, 0.85, 0.10);
		else if (lod_level == 2) dbg_col = vec3(0.15, 0.65, 1.00);
		ALBEDO = dbg_col * 0.72;
		ROUGHNESS = 0.88;
		SPECULAR = 0.05;
		BACKLIGHT = vec3(0.0);
	}
}
