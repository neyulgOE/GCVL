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
varying float v_wetland;
varying float v_shore_alpha;

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

float fbm2(vec2 p) {
	return noise2(p) * 0.65 + noise2(p * 2.13 + vec2(7.1, 3.4)) * 0.35;
}

void vertex() {
	vec3 wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_velocity = COLOR.r;
	v_wetland = COLOR.b;
	v_shore_alpha = COLOR.a;
	float cam_dist = length(CAMERA_POSITION_WORLD - wp);
	float vert_fade = 1.0 - smoothstep(350.0, 1400.0, cam_dist);

	float w1 = sin(wp.x * 0.14 + TIME * 1.4) * cos(wp.z * 0.12 + TIME * 1.1);
	float w2 = noise2(wp.xz * 0.08 + flow_speed * TIME * 2.5) - 0.5;
	float is_inland = step(0.15, wp.y);
	float calm_wetland = 1.0 - v_wetland * 0.72;
	VERTEX.y += is_inland * river_surge_offset * calm_wetland;
	VERTEX.y += (w1 * 0.045 + w2 * 0.07) * vert_fade * global_wind_gust * calm_wetland * v_shore_alpha;
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

	// Multi-frequency UV Domain Warping (1.0m - 6.0m) breaks 9.375m & 37.5m grid lines completely!
	vec2 warp_macro = vec2(
		fbm2(v_world_pos.xz * 0.038 + vec2(11.3, 4.7)) - 0.5,
		fbm2(v_world_pos.xz * 0.038 + vec2(29.1, 18.2)) - 0.5
	) * 11.5;
	vec2 warp_micro = vec2(
		noise2(v_world_pos.xz * 0.24 + vec2(3.1, 7.9)) - 0.5,
		noise2(v_world_pos.xz * 0.24 + vec2(15.4, 2.3)) - 0.5
	) * 2.4;
	vec2 warped_xz = v_world_pos.xz + warp_macro + warp_micro;
	vec2 warped_world_uv = clamp(warped_xz / world_size, vec2(0.0), vec2(1.0));

	float speed_mult = (1.0 + v_velocity * 2.2) * (1.0 - v_wetland * 0.65);
	vec2 uv1 = v_world_pos.xz * 0.14 + flow_speed * TIME * 2.0 * speed_mult;
	vec2 uv2 = v_world_pos.xz * 0.27 - flow_speed.yx * TIME * 1.4 * speed_mult;
	float n1 = noise2(uv1);
	float n2 = noise2(uv2);
	float ripple = (n1 + n2) * 0.5;

	float eps = 0.09;
	float nx = (noise2(uv1 + vec2(eps, 0.0)) - n1) + (noise2(uv2 + vec2(eps, 0.0)) - n2);
	float nz = (noise2(uv1 + vec2(0.0, eps)) - n1) + (noise2(uv2 + vec2(0.0, eps)) - n2);

	// Domain-warped ice contour + strict depth > 0.15m gate (eliminates coastal square ice & Z-fighting!)
	float surface_ice = texture(weather_dynamic_tex, warped_world_uv).b;
	float ice_grain = (fbm2(warped_xz * 0.22) - 0.5) * 0.22;
	float ice_depth_gate = smoothstep(0.16, 0.48, water_depth) * smoothstep(0.18, 0.65, v_shore_alpha);
	float ice_t = smoothstep(0.36, 0.76, surface_ice + ice_grain) * ice_depth_gate;

	float calm_factor = (1.0 - ice_t) * (1.0 - v_wetland * 0.55);
	vec3 ripple_normal = normalize(vec3(
		-nx * wave_strength * 7.0 * ripple_fade * global_wind_gust * calm_factor,
		1.0,
		-nz * wave_strength * 7.0 * ripple_fade * global_wind_gust * calm_factor
	));
	NORMAL = normalize(mix(NORMAL, (VIEW_MATRIX * vec4(ripple_normal, 0.0)).xyz, 0.72));

	float warped_depth = max(0.0, water_depth + (fbm2(warped_xz * 0.16) - 0.5) * 0.24 * clamp(water_depth * 2.0, 0.0, 1.0));
	float depth_t = 1.0 - exp(-warped_depth * 0.30);
	vec3 refracted = texture(screen_tex, SCREEN_UV + vec2(nx, nz) * 0.010 * ripple_fade * smoothstep(0.05, 0.45, water_depth)).rgb;

	// Murky green-brown wetland water vs clear turquoise/river water
	vec4 murk_shallow = vec4(0.14, 0.20, 0.09, 0.86);
	vec4 murk_deep = vec4(0.06, 0.10, 0.05, 0.96);
	vec4 sh_col = mix(shallow_color, murk_shallow, v_wetland);
	vec4 dp_col = mix(deep_color, murk_deep, v_wetland);

	vec4 water_col = mix(sh_col, dp_col, depth_t);
	vec3 tint_refract = mix(vec3(0.90, 0.98, 0.96), mix(vec3(0.45, 0.68, 0.78), vec3(0.38, 0.46, 0.26), v_wetland), depth_t);
	vec3 body_col = mix(refracted * tint_refract, water_col.rgb, water_col.a * smoothstep(0.03, 0.45, water_depth));
	body_col = mix(refracted, max(body_col, water_col.rgb * 0.76), smoothstep(0.02, 0.35, water_depth));

	float fresnel = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 4.0);
	vec3 sky_reflect = mix(vec3(0.56, 0.70, 0.82), vec3(0.38, 0.48, 0.44), v_wetland * 0.5);
	vec3 final_col = mix(body_col, sky_reflect, clamp(fresnel * 0.72 * smoothstep(0.04, 0.35, water_depth), 0.0, 0.82));

	// Organic domain-warped shoreline foam + fast-flowing rapids whitewater foam (subdued in calm marshes)
	float foam_band = smoothstep(0.04, 0.16, warped_depth) * (1.0 - smoothstep(0.22, 0.92, warped_depth)) * ripple_fade * (1.0 - v_wetland * 0.80);
	float rapids_foam = smoothstep(0.32, 0.78, v_velocity) * ripple_fade * 0.65 * (1.0 - v_wetland);
	float foam_noise = smoothstep(0.45, 0.76, ripple + fbm2(warped_xz * 0.35) * 0.35 + max(foam_band, rapids_foam) * 0.30);
	float foam = max(foam_band, rapids_foam) * foam_noise;
	final_col = mix(final_col, foam_color, clamp(foam * 0.80, 0.0, 1.0));

	// Natural irregular surface ice sheets & floes
	vec3 ice_col = mix(vec3(0.68, 0.84, 0.94), vec3(0.89, 0.95, 0.99), ripple * 0.6 + fbm2(warped_xz * 0.4) * 0.4);
	final_col = mix(final_col, ice_col, ice_t * 0.88);

	ALBEDO = final_col;
	ROUGHNESS = mix(mix(0.06, 0.36, max(foam, v_wetland * 0.45)), 0.58, ice_t);
	SPECULAR = mix(0.82, 0.45, v_wetland);

	// Smooth zero-Z-fighting shoreline depth fade (0.00 -> 0.25m fades cleanly to alpha 0.0!)
	float shore_fade = smoothstep(0.015, 0.25, water_depth) * smoothstep(0.0, 0.28, v_shore_alpha);
	ALPHA = clamp(max(shore_fade * mix(0.76, 0.98, depth_t) + foam * shore_fade * 0.42, ice_t * 0.92), 0.0, 0.98);
}
