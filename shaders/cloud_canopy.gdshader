shader_type spatial;
render_mode blend_mix, depth_draw_never, cull_disabled, unshaded;

uniform sampler2D weather_dynamic_tex : filter_linear, repeat_disable;
uniform vec2 world_size = vec2(9600.0, 5400.0);
uniform vec3 cloud_color : source_color = vec3(0.92, 0.94, 0.97);

varying vec2 v_world_uv;

float hash21(vec2 p) {
	p = fract(p * vec2(127.1, 311.7));
	p += dot(p, p + 34.23);
	return fract(p.x * p.y);
}

float noise2(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(
		mix(hash21(i), hash21(i + vec2(1.0, 0.0)), u.x),
		mix(hash21(i + vec2(0.0, 1.0)), hash21(i + vec2(1.0, 1.0)), u.x),
		u.y
	);
}

void vertex() {
	vec3 wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_world_uv = clamp(wp.xz / world_size, vec2(0.0), vec2(1.0));
}

void fragment() {
	float cloud_cov = texture(weather_dynamic_tex, v_world_uv).a;
	float wisp = noise2(v_world_uv * vec2(26.0, 15.0) + vec2(TIME * 0.015, TIME * 0.008));
	float alpha = smoothstep(0.28, 0.82, cloud_cov * (0.72 + 0.52 * wisp)) * 0.58;
	ALBEDO = mix(cloud_color, cloud_color * 0.62, smoothstep(0.55, 0.95, cloud_cov));
	ALPHA = alpha;
}
