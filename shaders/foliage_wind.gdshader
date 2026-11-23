shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform sampler2D wind_dir_speed_tex : filter_linear, repeat_disable; // R=dir.x*0.5+0.5, G=dir.z*0.5+0.5, B=speed/30
uniform sampler2D weather_dynamic_tex : filter_linear, repeat_disable; // R=SnowAccum, G=Wetness, B=Ice, A=CloudShadow
uniform vec2 world_size = vec2(9600.0, 5400.0);
uniform float season_phase = 0.15;
uniform float global_wind_gust = 1.0;
uniform float fade_start = 2400.0;
uniform float fade_end = 2900.0;
uniform bool enable_distance_fade = false;

varying vec3 v_color;
varying vec3 v_world_normal;
varying float v_snow_accum;

void vertex() {
	v_color = COLOR.rgb;
	float stem_flex = COLOR.a;

	vec3 world_origin = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	vec2 world_uv = clamp(world_origin.xz / world_size, vec2(0.0), vec2(1.0));
	vec4 w_data = textureLod(wind_dir_speed_tex, world_uv, 0.0);
	v_snow_accum = textureLod(weather_dynamic_tex, world_uv, 0.0).r;
	v_world_normal = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz + vec3(0.0, 0.0001, 0.0));

	vec2 local_wind_dir = normalize(vec2(w_data.r * 2.0 - 1.0, w_data.g * 2.0 - 1.0) + vec2(0.0001));
	float local_wind_speed = w_data.b * 30.0 * global_wind_gust;
	float phase = dot(world_origin.xz, local_wind_dir) * 0.16;
	float freq = 1.2 + local_wind_speed * 0.12;

	vec2 sway = vec2(0.0);
	if (stem_flex < 0.22) {
		// Group A (Woody Branching): rigid trunk, subtle high-frequency leaf flutter
		float flutter = sin(TIME * (freq * 1.9) + phase + VERTEX.x * 1.3 + VERTEX.z * 1.1);
		sway = local_wind_dir * flutter * (0.02 + local_wind_speed * 0.012) * stem_flex;
	} else if (stem_flex < 0.60) {
		// Group C (Columnar / Caudex / Culm): parabolic arc bending along WindVector
		float h_norm = clamp(VERTEX.y / 6.0, 0.0, 1.4);
		float arc = h_norm * h_norm;
		float gust = sin(TIME * freq + phase) * 0.55 + sin(TIME * freq * 2.1 + phase * 1.6) * 0.35;
		float lean = smoothstep(4.0, 24.0, local_wind_speed) * 0.65 + gust * 0.45;
		sway = local_wind_dir * lean * arc * (0.18 + local_wind_speed * 0.032) * stem_flex;
	} else {
		// Group D (Soft Tall Herbs / Reeds / Grass): traveling spatial wave across plains
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
	float spring_t = sin(clamp(season_phase / 0.25, 0.0, 1.0) * 3.14159);
	float autumn_t = sin(clamp((season_phase - 0.48) / 0.28, 0.0, 1.0) * 3.14159);
	float winter_t = smoothstep(0.72, 0.88, season_phase) * (1.0 - smoothstep(0.95, 1.0, season_phase));

	float warm_leaf = smoothstep(0.18, 0.55, col.r + col.g * 0.4 - col.b * 0.5);
	col = mix(col, col * vec3(1.06, 1.14, 0.92), spring_t * 0.32 * warm_leaf);
	col = mix(col, vec3(col.r * 1.18 + 0.16, col.g * 0.84 + 0.04, col.b * 0.65), autumn_t * 0.48 * warm_leaf);
	col = mix(col, col * vec3(0.68, 0.62, 0.58), winter_t * 0.42 * warm_leaf);

	float snow_dust = smoothstep(0.22, 0.62, v_snow_accum) * smoothstep(0.32, 0.72, v_world_normal.y);
	col = mix(col, vec3(0.88, 0.93, 0.98), snow_dust * 0.88);

	ALBEDO = col;
	ROUGHNESS = mix(0.82, 0.90, snow_dust);
	SPECULAR = 0.18;
	BACKLIGHT = col * 0.26 * (1.0 - snow_dust * 0.7);
}
