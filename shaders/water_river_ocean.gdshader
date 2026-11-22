shader_type spatial;
render_mode blend_mix, depth_draw_always, cull_back, specular_schlick_ggx;

uniform sampler2D depth_tex : hint_depth_texture, repeat_disable, filter_nearest;
uniform sampler2D screen_tex : hint_screen_texture, repeat_disable, filter_linear_mipmap;

uniform vec2 flow_speed = vec2(0.03, 0.12);
uniform vec4 shallow_color : source_color = vec4(0.08, 0.58, 0.62, 0.82);
uniform vec4 deep_color : source_color = vec4(0.02, 0.15, 0.30, 0.96);
uniform vec3 foam_color : source_color = vec3(0.88, 0.94, 0.97);
uniform float wave_strength = 0.14;

varying vec3 v_world_pos;

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
	float w1 = sin(wp.x * 0.22 + TIME * 1.6) * cos(wp.z * 0.18 + TIME * 1.2);
	float w2 = noise2(wp.xz * 0.12 + flow_speed * TIME * 3.0) - 0.5;
	VERTEX.y += (w1 * 0.06 + w2 * 0.08);
	v_world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	// Reconstruct water depth from scene depth buffer (Godot 4 Forward+ Vulkan NDC)
	float depth_raw = texture(depth_tex, SCREEN_UV).r;
	vec3 ndc = vec3(SCREEN_UV * 2.0 - 1.0, depth_raw);
	vec4 view_pos = INV_PROJECTION_MATRIX * vec4(ndc, 1.0);
	view_pos.xyz /= view_pos.w;
	float scene_depth = -view_pos.z;
	float surface_depth = -VERTEX.z;
	float water_depth = max(0.0, scene_depth - surface_depth);

	// Dual scrolling ripple normals
	vec2 uv1 = v_world_pos.xz * 0.18 + flow_speed * TIME * 2.2;
	vec2 uv2 = v_world_pos.xz * 0.34 - flow_speed.yx * TIME * 1.5;
	float n1 = noise2(uv1);
	float n2 = noise2(uv2);
	float ripple = (n1 + n2) * 0.5;

	float eps = 0.08;
	float nx = (noise2(uv1 + vec2(eps, 0.0)) - n1) + (noise2(uv2 + vec2(eps, 0.0)) - n2);
	float nz = (noise2(uv1 + vec2(0.0, eps)) - n1) + (noise2(uv2 + vec2(0.0, eps)) - n2);
	vec3 ripple_normal = normalize(vec3(-nx * wave_strength * 8.0, 1.0, -nz * wave_strength * 8.0));
	NORMAL = normalize(mix(NORMAL, (VIEW_MATRIX * vec4(ripple_normal, 0.0)).xyz, 0.65));

	// Depth-based water absorption + refractive background tint
	float depth_t = 1.0 - exp(-water_depth * 0.38);
	vec3 refracted = texture(screen_tex, SCREEN_UV + vec2(nx, nz) * 0.015).rgb;
	vec4 water_col = mix(shallow_color, deep_color, depth_t);
	vec3 body_col = mix(refracted * mix(vec3(0.82, 0.96, 0.94), vec3(0.35, 0.55, 0.65), depth_t), water_col.rgb, water_col.a);

	// Schlick Fresnel sky reflection
	float fresnel = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 4.0);
	vec3 sky_reflect = vec3(0.56, 0.74, 0.90);
	vec3 final_col = mix(body_col, sky_reflect, fresnel * 0.65);

	// Shoreline / riverbank white foam
	float foam_band = 1.0 - smoothstep(0.05, 0.95, water_depth);
	float foam_noise = smoothstep(0.42, 0.78, ripple + foam_band * 0.45);
	float foam = foam_band * foam_noise;
	final_col = mix(final_col, foam_color, clamp(foam * 0.85, 0.0, 1.0));

	ALBEDO = final_col;
	ROUGHNESS = mix(0.06, 0.35, foam);
	SPECULAR = 0.85;
	ALPHA = clamp(smoothstep(0.0, 0.12, water_depth) * mix(0.78, 0.98, depth_t) + foam * 0.5, 0.25, 0.98);
}
