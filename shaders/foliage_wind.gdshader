shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform float wind_speed = 1.65;
uniform float wind_strength = 0.22;
uniform vec2 wind_dir = vec2(0.82, 0.57);
uniform float fade_start = 160.0;
uniform float fade_end = 225.0;
uniform bool enable_distance_fade = false;

varying vec3 v_color;

void vertex() {
	v_color = COLOR.rgb;
	float wind_weight = COLOR.a;

	vec3 world_origin = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	float cam_dist = length(CAMERA_POSITION_WORLD - world_origin);

	float phase = dot(world_origin.xz, wind_dir) * 0.22;
	float gust = sin(TIME * wind_speed + phase) * 0.65
	           + sin(TIME * wind_speed * 2.1 + phase * 1.9 + VERTEX.y * 0.8) * 0.35;

	vec2 sway = wind_dir * gust * wind_strength * wind_weight;
	VERTEX.x += sway.x;
	VERTEX.z += sway.y;

	if (enable_distance_fade && cam_dist > fade_start) {
		float scale_fade = 1.0 - smoothstep(fade_start, fade_end, cam_dist);
		VERTEX *= scale_fade;
	}
}

void fragment() {
	ALBEDO = v_color;
	ROUGHNESS = 0.82;
	SPECULAR = 0.18;
	BACKLIGHT = v_color * 0.28;
}
