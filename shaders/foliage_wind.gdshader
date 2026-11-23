shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform sampler2D wind_dir_speed_tex : filter_linear, repeat_disable; // R=dir.x*0.5+0.5, G=dir.z*0.5+0.5, B=speed/30
uniform vec2 world_size = vec2(9600.0, 5400.0);
uniform float fade_start = 2400.0;
uniform float fade_end = 2900.0;
uniform bool enable_distance_fade = false;

varying vec3 v_color;

void vertex() {
	v_color = COLOR.rgb;
	float wind_weight = COLOR.a;

	vec3 world_origin = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	vec2 world_uv = clamp(world_origin.xz / world_size, vec2(0.0), vec2(1.0));
	vec4 w_data = textureLod(wind_dir_speed_tex, world_uv, 0.0);

	vec2 local_wind_dir = normalize(vec2(w_data.r * 2.0 - 1.0, w_data.g * 2.0 - 1.0) + vec2(0.0001));
	float local_wind_speed = w_data.b * 30.0;

	float phase = dot(world_origin.xz, local_wind_dir) * 0.14;
	float freq = 1.15 + local_wind_speed * 0.12;
	float gust = sin(TIME * freq + phase) * 0.65
	           + sin(TIME * freq * 2.05 + phase * 1.85 + VERTEX.y * 0.55) * 0.35;

	// Bend slightly along wind direction + oscillate with gust
	float steady_lean = smoothstep(5.0, 26.0, local_wind_speed) * 0.42;
	float amp = (0.04 + local_wind_speed * 0.022) * wind_weight;
	vec2 sway = local_wind_dir * (steady_lean + gust) * amp;

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
	ALBEDO = v_color;
	ROUGHNESS = 0.82;
	SPECULAR = 0.18;
	BACKLIGHT = v_color * 0.28;
}
