shader_type spatial;
render_mode blend_mix, depth_draw_always, cull_back, specular_schlick_ggx;

uniform sampler2D depth_tex : hint_depth_texture, repeat_disable, filter_nearest;
uniform sampler2D screen_tex : hint_screen_texture, repeat_disable, filter_linear_mipmap;
uniform sampler2D weather_dynamic_tex : filter_linear, repeat_disable;

uniform vec2 world_size = vec2(9600.0, 5400.0);
uniform float river_surge_offset = 0.0;
uniform float global_wind_gust = 1.0;

uniform vec2 flow_speed = vec2(0.025, 0.12);
uniform vec4 shallow_color : source_color = vec4(0.12, 0.66, 0.70, 0.76);
uniform vec4 deep_color : source_color = vec4(0.04, 0.22, 0.38, 0.94);
uniform vec3 foam_color : source_color = vec3(0.88, 0.94, 0.98);
uniform float wave_strength = 0.14;

varying vec3 v_world_pos;
varying float v_velocity;

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
	v_velocity = COLOR.r;
	float cam_dist = length(CAMERA_POSITION_WORLD - wp);
	float vert_fade = 1.0 - smoothstep(350.0, 1400.0, cam_dist);

	float w1 = sin(wp.x * 0.14 + TIME * 1.4) * cos(wp.z * 0.12 + TIME * 1.1);
	float w2 = noise2(wp.xz * 0.08 + flow_speed * TIME * 2.5) - 0.5;
	float is_inland = step(0.15, wp.y);
	VERTEX.y += is_inland * river_surge_offset;
	VERTEX.y += (w1 * 0.05 + w2 * 0.08) * vert_fade * global_wind_gust;
	v_world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	float cam_dist = length(CAMERA_POSITION_WORLD - v_world_pos);
	float ripple_fade = 1.0 - smoothstep(220.0, 1200.0, cam_dist);

	float depth_raw = texture(depth_tex, SCREEN_UV).r;
	vec3 ndc = vec3(SCREEN_UV * 2.0 - 1.0, depth_raw);
	vec4 view_pos = INV_PROJECTION_MATRIX * vec4(ndc, 1.0);
	view_pos.xyz /= view_pos.w;
	float scene_depth = -view_pos.z;
	float surface_depth = -VERTEX.z;
	float water_depth = max(0.0, scene_depth - surface_depth);

	float speed_mult = 1.0 + v_velocity * 2.2;
	vec2 uv1 = v_world_pos.xz * 0.14 + flow_speed * TIME * 2.0 * speed_mult;
	vec2 uv2 = v_world_pos.xz * 0.27 - flow_speed.yx * TIME * 1.4 * speed_mult;
	float n1 = noise2(uv1);
	float n2 = noise2(uv2);
	float ripple = (n1 + n2) * 0.5;

	float eps = 0.09;
	float nx = (noise2(uv1 + vec2(eps, 0.0)) - n1) + (noise2(uv2 + vec2(eps, 0.0)) - n2);
	float nz = (noise2(uv1 + vec2(0.0, eps)) - n1) + (noise2(uv2 + vec2(0.0, eps)) - n2);

	vec2 world_uv = clamp(v_world_pos.xz / world_size, vec2(0.0), vec2(1.0));
	float surface_ice = texture(weather_dynamic_tex, world_uv).b;
	float ice_t = smoothstep(0.35, 0.78, surface_ice);

	vec3 ripple_normal = normalize(vec3(-nx * wave_strength * 7.0 * ripple_fade * global_wind_gust * (1.0 - ice_t), 1.0, -nz * wave_strength * 7.0 * ripple_fade * global_wind_gust * (1.0 - ice_t)));
	NORMAL = normalize(mix(NORMAL, (VIEW_MATRIX * vec4(ripple_normal, 0.0)).xyz, 0.72));

	float depth_t = 1.0 - exp(-water_depth * 0.28);
	vec3 refracted = texture(screen_tex, SCREEN_UV + vec2(nx, nz) * 0.012 * ripple_fade).rgb;
	vec4 water_col = mix(shallow_color, deep_color, depth_t);
	vec3 body_col = mix(refracted * mix(vec3(0.88, 0.98, 0.96), vec3(0.45, 0.68, 0.78), depth_t), water_col.rgb, water_col.a);
	body_col = max(body_col, water_col.rgb * 0.78);

	float fresnel = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 4.0);
	vec3 sky_reflect = vec3(0.56, 0.70, 0.82);
	vec3 final_col = mix(body_col, sky_reflect, clamp(fresnel * 0.78, 0.0, 0.85));

	// Shoreline foam + fast-flowing rapids whitewater foam
	float foam_band = (1.0 - smoothstep(0.06, 0.95, water_depth)) * ripple_fade;
	float rapids_foam = smoothstep(0.32, 0.78, v_velocity) * ripple_fade * 0.65;
	float foam_noise = smoothstep(0.46, 0.76, ripple + max(foam_band, rapids_foam) * 0.42);
	float foam = max(foam_band, rapids_foam) * foam_noise;
	final_col = mix(final_col, foam_color, clamp(foam * 0.82, 0.0, 1.0));

	// Frozen Lake / Stream Surface Ice
	vec3 ice_col = mix(vec3(0.68, 0.84, 0.94), vec3(0.88, 0.94, 0.98), ripple);
	final_col = mix(final_col, ice_col, ice_t * 0.88);

	ALBEDO = final_col;
	ROUGHNESS = mix(mix(0.05, 0.34, foam), 0.56, ice_t);
	SPECULAR = 0.85;
	ALPHA = clamp(max(smoothstep(0.0, 0.16, water_depth) * mix(0.76, 0.98, depth_t) + foam * 0.45, ice_t * 0.92), 0.25, 0.98);
}
