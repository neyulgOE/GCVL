shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform sampler2D height_tex : filter_linear, repeat_disable;
uniform sampler2D soil_tex_a : filter_linear, repeat_disable;
uniform sampler2D soil_tex_b : filter_linear, repeat_disable;
uniform sampler2D climate_tex : filter_linear, repeat_disable;
uniform sampler2D canopy_coverage_tex : filter_linear, repeat_disable;
uniform sampler2D wind_dir_speed_tex : filter_linear, repeat_disable;
uniform sampler2D weather_dynamic_tex : filter_linear, repeat_disable;
uniform sampler2D fern_tex : source_color, filter_linear_mipmap, repeat_disable;

uniform vec2 world_size = vec2(9600.0, 5400.0);
uniform float global_wind_gust = 1.0;

varying vec2 v_uv;
varying vec3 v_tint;
varying float v_tip_t;

float hash12(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}

void vertex() {
	v_uv = UV;
	float tip_t = COLOR.a;
	v_tip_t = tip_t;

	vec3 inst_world = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	vec2 world_uv = clamp(inst_world.xz / world_size, vec2(0.0), vec2(1.0));

	float ground_h = textureLod(height_tex, world_uv, 0.0).r;
	vec4 sa = textureLod(soil_tex_a, world_uv, 0.0);
	vec4 sb = textureLod(soil_tex_b, world_uv, 0.0);
	vec4 cl = textureLod(climate_tex, world_uv, 0.0);
	float canopy = textureLod(canopy_coverage_tex, world_uv, 0.0).r;
	vec4 wd = textureLod(weather_dynamic_tex, world_uv, 0.0);
	vec4 w_data = textureLod(wind_dir_speed_tex, world_uv, 0.0);

	float moisture = cl.g;
	float river_mask = cl.b;
	float temp_c = cl.r * 53.0 - 15.0;
	float soil_depth = sb.b;

	// Lush fern understory thrives under forest canopy (canopy > 0.20) or moist riverbanks!
	float forest_niche = max(smoothstep(0.18, 0.52, canopy), smoothstep(0.06, 0.25, river_mask) * (1.0 - smoothstep(0.32, 0.48, river_mask)));
	float valid = step(0.8, ground_h)
	            * forest_niche
	            * smoothstep(0.28, 0.52, moisture)
	            * smoothstep(4.0, 11.0, temp_c)
	            * (1.0 - smoothstep(0.35, 0.65, sa.a)) // no arid desert
	            * smoothstep(0.10, 0.28, soil_depth);

	float cam_dist = length(CAMERA_POSITION_WORLD.xz - inst_world.xz);
	float dist_fade = 1.0 - smoothstep(38.0, 56.0, cam_dist);

	float rnd = hash12(floor(inst_world.xz * 1.5));
	float scale_h = mix(0.65, 1.38, rnd);
	float final_scale = valid * dist_fade;

	// Dappled rainforest yellow-green sunlight variation
	vec3 deep_fern = vec3(0.76, 0.90, 0.72);
	vec3 sunlit_fern = vec3(1.12, 1.18, 0.84);
	v_tint = mix(deep_fern, sunlit_fern, rnd * (1.0 - canopy * 0.45));
	v_tint = mix(v_tint, vec3(0.86, 0.92, 0.97), smoothstep(0.30, 0.70, wd.r) * 0.75);

	// Gentle elastic frond bounce in forest wind
	vec2 wind_dir = normalize(vec2(w_data.r * 2.0 - 1.0, w_data.g * 2.0 - 1.0) + vec2(0.0001));
	float wind_spd = w_data.b * 30.0 * global_wind_gust;
	float wave = sin(dot(inst_world.xz, wind_dir) * 0.26 - TIME * (1.5 + wind_spd * 0.12));
	float bend = wave * (0.08 + wind_spd * 0.012) * tip_t;

	VERTEX.y = VERTEX.y * scale_h * final_scale + ground_h - 0.08;
	VERTEX.xz = VERTEX.xz * scale_h * final_scale + wind_dir * bend * final_scale;
	NORMAL = vec3(0.0, 1.0, 0.0);
}

void fragment() {
	vec4 tex = texture(fern_tex, v_uv);
	ALPHA = tex.a;
	ALPHA_SCISSOR_THRESHOLD = 0.42;
	vec3 col = tex.rgb * v_tint;
	ALBEDO = col;
	ROUGHNESS = 0.82;
	SPECULAR = 0.16;
	BACKLIGHT = col * (0.56 * v_tip_t + 0.18);
}
