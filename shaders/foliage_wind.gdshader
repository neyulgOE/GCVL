shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform float wind_speed = 1.65;
uniform float wind_strength = 0.22;
uniform float fade_start = 180.0;
uniform float fade_end = 260.0;
uniform bool enable_distance_fade = false;

varying vec3 v_color;
varying float v_cam_dist;

void vertex() {
	v_color = COLOR.rgb;
	// COLOR.a stores per-vertex wind weight (0 = anchored root/trunk, 1 = swaying tip)
	float wind_weight = COLOR.a;

	vec3 world_origin = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	v_cam_dist = length(CAMERA_POSITION_WORLD - world_origin);

	float phase = world_origin.x * 0.17 + world_origin.z * 0.23;
	float gust = sin(TIME * wind_speed + phase) * 0.65
	           + sin(TIME * wind_speed * 2.1 + phase * 1.9 + VERTEX.y * 0.8) * 0.35;

	VERTEX.x += gust * wind_strength * wind_weight;
	VERTEX.z += cos(TIME * wind_speed * 0.85 + phase * 1.3) * wind_strength * 0.6 * wind_weight;

	if (enable_distance_fade && v_cam_dist > fade_start) {
		float scale_fade = 1.0 - smoothstep(fade_start, fade_end, v_cam_dist);
		VERTEX *= scale_fade;
	}
}

void fragment() {
	ALBEDO = v_color;
	ROUGHNESS = 0.82;
	SPECULAR = 0.18;
	BACKLIGHT = v_color * 0.28;
}
