shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform sampler2D height_tex : filter_linear, repeat_disable;
uniform sampler2D soil_tex_a : filter_linear, repeat_disable;    // R=Alluvial, G=ForestBrown, B=SteppeLoess, A=AridRed
uniform sampler2D soil_tex_b : filter_linear, repeat_disable;    // R=CoastalSand, G=PermafrostRock, B=SoilDepth, A=BedrockMask
uniform sampler2D climate_tex : filter_linear, repeat_disable;   // R=TempNorm, G=Moisture, B=RiverMask, A=FlowAccum
uniform sampler2D canopy_coverage_tex : filter_linear, repeat_disable;
uniform sampler2D wind_dir_speed_tex : filter_linear, repeat_disable;
uniform sampler2D weather_dynamic_tex : filter_linear, repeat_disable;

uniform vec2 world_size = vec2(9600.0, 5400.0);
uniform float season_phase = 0.15;
uniform float global_wind_gust = 1.0;

varying vec3 v_color;
varying float v_tip_t;

float hash12(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}

void vertex() {
	// Instance origin in world space (snapped ring origin + instance local XZ)
	vec3 inst_world = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	vec2 world_uv = clamp(inst_world.xz / world_size, vec2(0.0), vec2(1.0));

	float ground_h = textureLod(height_tex, world_uv, 0.0).r;
	vec4 sa = textureLod(soil_tex_a, world_uv, 0.0);
	vec4 sb = textureLod(soil_tex_b, world_uv, 0.0);
	vec4 cl = textureLod(climate_tex, world_uv, 0.0);
	vec4 eco = textureLod(canopy_coverage_tex, world_uv, 0.0);
	float canopy = eco.r;
	float floodplain_mask = eco.g;
	float wetland_mask = eco.b;
	vec4 wd = textureLod(weather_dynamic_tex, world_uv, 0.0);
	vec4 w_data = textureLod(wind_dir_speed_tex, world_uv, 0.0);

	float w_alluvial = sa.r;
	float w_forest = sa.g;
	float w_steppe = sa.b;
	float w_arid = sa.a;
	float w_coastal = sb.r;
	float w_perma = sb.g;
	float soil_depth = sb.b;
	float bedrock_mask = sb.a;
	float moisture = cl.g;
	float river_mask = cl.b;
	float temp_c = cl.r * 53.0 - 15.0;

	// Approximate local slope from height_tex finite difference
	vec2 texel = 1.0 / vec2(1025.0, 577.0);
	float hR = textureLod(height_tex, world_uv + vec2(texel.x, 0.0), 0.0).r;
	float hU = textureLod(height_tex, world_uv + vec2(0.0, texel.y), 0.0).r;
	float slope_est = length(vec2(hR - ground_h, hU - ground_h)) / 9.375;

	// Hide grass under water, in rivers, on steep cliffs (>32° ~ tan 0.62), bare rock, or dry red sand
	float valid = step(0.65, ground_h)
	            * (1.0 - smoothstep(0.32, 0.55, river_mask))
	            * (1.0 - smoothstep(0.42, 0.65, slope_est))
	            * (1.0 - smoothstep(0.55, 0.85, bedrock_mask))
	            * (1.0 - smoothstep(0.42, 0.72, w_arid))
	            * (1.0 - smoothstep(0.55, 0.85, w_coastal))
	            * smoothstep(0.08, 0.25, soil_depth)
	            * smoothstep(-4.0, 2.0, temp_c);

	// Distance ring fade (50m -> 70m) so ring boundary never pops
	float cam_dist = length(CAMERA_POSITION_WORLD.xz - inst_world.xz);
	float dist_fade = 1.0 - smoothstep(48.0, 70.0, cam_dist);

	float rnd = hash12(floor(inst_world.xz * 2.0));
	float blade_h = mix(0.45, 1.05, rnd);
	blade_h = mix(blade_h, 0.38, smoothstep(0.35, 0.85, canopy)); // Shorter fern/shade grass under dense canopy
	blade_h *= (1.0 + floodplain_mask * 0.32 + wetland_mask * 0.38 + smoothstep(0.35, 0.85, w_steppe) * 0.25); // Lush tall floodplain/marsh/steppe grass!
	float final_scale = valid * dist_fade;

	// Ground Color Blending at root -> sunlit tip color
	vec3 c_alluvial = mix(vec3(0.15, 0.30, 0.09), vec3(0.11, 0.24, 0.07), moisture);
	vec3 c_forest = mix(vec3(0.17, 0.29, 0.10), vec3(0.12, 0.22, 0.07), moisture);
	vec3 c_steppe = mix(vec3(0.58, 0.43, 0.15), vec3(0.42, 0.35, 0.14), moisture);
	vec3 ground_col = (c_alluvial * w_alluvial + c_forest * w_forest + c_steppe * w_steppe + vec3(0.24, 0.27, 0.22) * w_perma)
	                / max(w_alluvial + w_forest + w_steppe + w_perma, 0.001);
	ground_col = mix(ground_col, vec3(0.16, 0.35, 0.10), floodplain_mask * 0.70);
	ground_col = mix(ground_col, vec3(0.06, 0.11, 0.04), smoothstep(0.20, 0.75, canopy) * 0.80);

	vec3 tip_lush = mix(vec3(0.24, 0.48, 0.13), vec3(0.16, 0.34, 0.10), canopy);
	vec3 tip_steppe = vec3(0.72, 0.56, 0.20);
	vec3 tip_col = mix(tip_lush, tip_steppe, smoothstep(0.28, 0.78, w_steppe) * (1.0 - floodplain_mask));

	// Autumn golden-brown tint + Winter snow dust on grass tips
	float autumn_t = sin(clamp((season_phase - 0.48) / 0.28, 0.0, 1.0) * 3.14159);
	tip_col = mix(tip_col, vec3(0.68, 0.48, 0.18), autumn_t * 0.45);
	tip_col = mix(tip_col, vec3(0.84, 0.90, 0.95), smoothstep(0.25, 0.65, wd.r) * 0.80);

	float tip_t = COLOR.a;
	v_tip_t = tip_t;
	v_color = mix(ground_col, tip_col * (0.85 + 0.30 * rnd), smoothstep(0.0, 0.85, tip_t));

	// Traveling wind wave
	vec2 wind_dir = normalize(vec2(w_data.r * 2.0 - 1.0, w_data.g * 2.0 - 1.0) + vec2(0.0001));
	float wind_spd = w_data.b * 30.0 * global_wind_gust;
	float wave = sin(dot(inst_world.xz, wind_dir) * 0.32 - TIME * (1.8 + wind_spd * 0.15));
	float bend = (smoothstep(3.0, 22.0, wind_spd) * 0.35 + wave * 0.35) * (0.15 + wind_spd * 0.018) * tip_t * tip_t;

	// Place vertex directly at ground_h - 0.08 (MODEL_MATRIX has scale=1.0 and Y=0.0, so no double-height!)
	float width_var = 0.85 + rnd * 0.40;
	VERTEX.y = VERTEX.y * blade_h * final_scale + ground_h - 0.08;
	VERTEX.xz = VERTEX.xz * width_var * final_scale + wind_dir * bend * final_scale;
	NORMAL = vec3(0.0, 1.0, 0.0);
}

void fragment() {
	ALBEDO = v_color;
	ROUGHNESS = 0.88;
	SPECULAR = 0.12;
	BACKLIGHT = v_color * (0.38 * v_tip_t);
}
