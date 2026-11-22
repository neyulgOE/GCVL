shader_type spatial;
render_mode blend_mix, depth_draw_always, cull_back, specular_schlick_ggx;

uniform sampler2D depth_tex : hint_depth_texture, repeat_disable, filter_nearest;
uniform sampler2D screen_tex : hint_screen_texture, repeat_disable, filter_linear_mipmap;

uniform vec2 flow_speed = vec2(0.025, 0.12);
uniform vec4 shallow_color : source_color = vec4(0.07, 0.48, 0.52, 0.84);
uniform vec4 deep_color : source_color = vec4(0.02, 0.11, 0.22, 0.98);
uniform vec3 foam_color : source_color = vec3(0.86, 0.92, 0.96);
uniform float wave_strength = 0.15;

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
	float cam_dist = length(CAMERA_POSITION_WORLD - wp);
	float vert_fade = 1.0 - smoothstep(250.0, 950.0, cam_dist);

	float w1 = sin(wp.x * 0.19 + TIME * 1.4) * cos(wp.z * 0.16 + TIME * 1.1);
	float w2 = noise2(wp.xz * 0.10 + flow_speed * TIME * 2.5) - 0.5;
	VERTEX.y += (w1 * 0.05 + w2 * 0.07) * vert_fade;
	v_world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	float cam_dist = length(CAMERA_POSITION_WORLD - v_world_pos);
	// Distance normal fade eliminates far-horizon aliasing speckles
	float ripple_fade = 1.0 - smoothstep(110.0, 620.0, cam_dist);

	float depth_raw = texture(depth_tex, SCREEN_UV).r;
	vec3 ndc = vec3(SCREEN_UV * 2.0 - 1.0, depth_raw);
	vec4 view_pos = INV_PROJECTION_MATRIX * vec4(ndc, 1.0);
	view_pos.xyz /= view_pos.w;
	float scene_depth = -view_pos.z;
	float surface_depth = -VERTEX.z;
	float water_depth = max(0.0, scene_depth - surface_depth);

	// Dual scrolling ripple normals (faded smoothly with distance)
	vec2 uv1 = v_world_pos.xz * 0.16 + flow_speed * TIME * 2.0;
	vec2 uv2 = v_world_pos.xz * 0.31 - flow_speed.yx * TIME * 1.4;
	float n1 = noise2(uv1);
	float n2 = noise2(uv2);
	float ripple = (n1 + n2) * 0.5;

	float eps = 0.09;
	float nx = (noise2(uv1 + vec2(eps, 0.0)) - n1) + (noise2(uv2 + vec2(eps, 0.0)) - n2);
	float nz = (noise2(uv1 + vec2(0.0, eps)) - n1) + (noise2(uv2 + vec2(0.0, eps)) - n2);
	vec3 ripple_normal = normalize(vec3(-nx * wave_strength * 7.5 * ripple_fade, 1.0, -nz * wave_strength * 7.5 * ripple_fade));
	NORMAL = normalize(mix(NORMAL, (VIEW_MATRIX * vec4(ripple_normal, 0.0)).xyz, 0.72));

	// Depth-based water absorption + refractive tint
	float depth_t = 1.0 - exp(-water_depth * 0.42);
	vec3 refracted = texture(screen_tex, SCREEN_UV + vec2(nx, nz) * 0.012 * ripple_fade).rgb;
	vec4 water_col = mix(shallow_color, deep_color, depth_t);
	vec3 body_col = mix(refracted * mix(vec3(0.84, 0.95, 0.92), vec3(0.32, 0.50, 0.60), depth_t), water_col.rgb, water_col.a);

	// Schlick Fresnel sky reflection (stronger at grazing horizon angles)
	float fresnel = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 4.2);
	vec3 sky_reflect = vec3(0.54, 0.68, 0.80);
	vec3 final_col = mix(body_col, sky_reflect, clamp(fresnel * 0.78, 0.0, 0.85));

	// Shoreline / riverbank white foam (only near shore)
	float foam_band = (1.0 - smoothstep(0.04, 0.85, water_depth)) * ripple_fade;
	float foam_noise = smoothstep(0.45, 0.76, ripple + foam_band * 0.40);
	float foam = foam_band * foam_noise;
	final_col = mix(final_col, foam_color, clamp(foam * 0.82, 0.0, 1.0));

	ALBEDO = final_col;
	ROUGHNESS = mix(0.04, 0.34, foam);
	SPECULAR = 0.85;
	ALPHA = clamp(smoothstep(0.0, 0.12, water_depth) * mix(0.80, 0.99, depth_t) + foam * 0.5, 0.25, 0.99);
}
