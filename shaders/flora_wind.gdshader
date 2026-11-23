shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform sampler2D wind_dir_speed_tex : filter_linear, repeat_disable; // R=dir.x*0.5+0.5, G=dir.z*0.5+0.5, B=speed/30
uniform sampler2D weather_dynamic_tex : filter_linear, repeat_disable; // R=SnowAccum, G=Wetness, B=Ice, A=CloudShadow
uniform sampler2D leaf_broadleaf_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D leaf_conifer_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D leaf_acacia_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D leaf_palm_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D bark_tex : source_color, filter_linear_mipmap, repeat_enable;

uniform vec2 world_size = vec2(9600.0, 5400.0);
uniform float season_phase = 0.15;
uniform float global_wind_gust = 1.0;
uniform float fade_start = 2400.0;
uniform float fade_end = 2900.0;
uniform bool enable_distance_fade = false;

varying vec3 v_color;
varying vec3 v_world_normal;
varying float v_snow_accum;
varying vec2 v_uv;
varying float v_is_leaf;
varying float v_leaf_type;

vec2 hash21_v(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.xx + p3.yz) * p3.zy);
}

void vertex() {
	v_color = COLOR.rgb;
	v_uv = UV;
	v_is_leaf = UV2.x;
	v_leaf_type = UV2.y;
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
	float twist_ang = (inst_rnd.x - 0.5) * 0.45 * clamp(VERTEX.y / 14.0, 0.0, 1.0);
	float c_tw = cos(twist_ang);
	float s_tw = sin(twist_ang);
	float rx = VERTEX.x * c_tw - VERTEX.z * s_tw;
	float rz = VERTEX.x * s_tw + VERTEX.z * c_tw;
	float aspect_var = 0.90 + inst_rnd.y * 0.22;
	VERTEX.x = rx * aspect_var;
	VERTEX.z = rz * aspect_var;

	// Permanent Wind Flagging on exposed windy ridges
	float flag_lean = smoothstep(10.0, 25.0, local_wind_speed) * clamp(VERTEX.y / 12.0, 0.0, 1.5) * 0.65;
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
	vec3 col = v_color;
	if (v_is_leaf > 0.5) {
		vec4 leaf_tex = texture(leaf_broadleaf_tex, v_uv);
		if (v_leaf_type > 0.5 && v_leaf_type < 1.5) {
			leaf_tex = texture(leaf_conifer_tex, v_uv);
		} else if (v_leaf_type >= 1.5 && v_leaf_type < 2.5) {
			leaf_tex = texture(leaf_acacia_tex, v_uv);
		} else if (v_leaf_type >= 2.5) {
			leaf_tex = texture(leaf_palm_tex, v_uv);
		}

		ALPHA = leaf_tex.a;
		ALPHA_SCISSOR_THRESHOLD = 0.44;
		// Subtle botanical tint around 1.0 so real leaf greens, ginkgo golds, and brown twigs stay natural!
		vec3 subtle_tint = mix(vec3(1.0), clamp(v_color * 1.45 + vec3(0.25), vec3(0.68), vec3(1.22)), 0.34);
		col = leaf_tex.rgb * subtle_tint;

		float spring_t = sin(clamp(season_phase / 0.25, 0.0, 1.0) * 3.14159);
		float autumn_t = sin(clamp((season_phase - 0.48) / 0.28, 0.0, 1.0) * 3.14159);
		float winter_t = smoothstep(0.72, 0.88, season_phase) * (1.0 - smoothstep(0.95, 1.0, season_phase));

		float warm_leaf = smoothstep(0.18, 0.55, col.r + col.g * 0.4 - col.b * 0.5);
		col = mix(col, col * vec3(1.05, 1.12, 0.92), spring_t * 0.25 * warm_leaf);
		col = mix(col, vec3(col.r * 1.15 + 0.12, col.g * 0.86 + 0.03, col.b * 0.68), autumn_t * 0.42 * warm_leaf);
		col = mix(col, col * vec3(0.72, 0.66, 0.62), winter_t * 0.36 * warm_leaf);

		float snow_dust = smoothstep(0.22, 0.62, v_snow_accum) * smoothstep(0.32, 0.72, v_world_normal.y);
		col = mix(col, vec3(0.88, 0.93, 0.98), snow_dust * 0.88);

		ALBEDO = col;
		ROUGHNESS = 0.85;
		SPECULAR = 0.14;
		BACKLIGHT = col * 0.48 * (1.0 - snow_dust * 0.6);
	} else {
		vec3 b_col = texture(bark_tex, v_uv).rgb;
		ALBEDO = col * mix(vec3(1.0), b_col * 1.35, 0.60);
		ROUGHNESS = 0.92;
		SPECULAR = 0.08;
		BACKLIGHT = col * 0.10;
	}
}
