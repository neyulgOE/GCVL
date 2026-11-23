shader_type sky;

uniform vec3 sun_direction = vec3(0.3, 0.6, 0.4);
uniform float day_t = 1.0;
uniform float golden_t = 0.0;
uniform float cloud_cover = 0.25;

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

float fbm4(vec2 p) {
	float v = 0.0;
	float a = 0.5;
	for (int i = 0; i < 4; i++) {
		v += a * noise2(p);
		p *= 2.04;
		a *= 0.5;
	}
	return v;
}

void sky() {
	vec3 dir = normalize(EYEDIR);
	float up = clamp(dir.y, -1.0, 1.0);

	// Base sky gradient
	vec3 day_top = vec3(0.14, 0.34, 0.66);
	vec3 day_hor = vec3(0.60, 0.74, 0.86);
	vec3 golden_hor = vec3(0.90, 0.56, 0.34);
	vec3 night_top = vec3(0.03, 0.06, 0.14);
	vec3 night_hor = vec3(0.08, 0.13, 0.22);

	vec3 sky_top = mix(night_top, day_top, day_t);
	vec3 sky_hor = mix(night_hor, mix(day_hor, golden_hor, golden_t * 0.72), day_t);
	sky_top = mix(sky_top, vec3(0.32, 0.37, 0.42), cloud_cover * 0.55);
	sky_hor = mix(sky_hor, vec3(0.48, 0.52, 0.56), cloud_cover * 0.50);

	vec3 col = mix(sky_hor, sky_top, pow(max(up, 0.0), 0.52));

	// Sun disc & soft atmospheric glow
	float sun_dot = max(dot(dir, normalize(sun_direction)), 0.0);
	vec3 sun_col = mix(vec3(1.0, 0.62, 0.32), vec3(1.0, 0.96, 0.88), clamp(day_t * 1.2 - golden_t * 0.5, 0.0, 1.0));
	col += sun_col * pow(sun_dot, 18.0) * 0.38 * day_t * (1.0 - cloud_cover * 0.65);
	col += sun_col * smoothstep(0.9985, 0.9996, sun_dot) * 2.2 * day_t * (1.0 - cloud_cover * 0.8);

	// Seamless 360-degree spherical dome clouds (zero UV seams or straight cuts!)
	if (dir.y > 0.01) {
		vec2 dome_uv = dir.xz / (dir.y + 0.18);
		float n1 = fbm4(dome_uv * 1.35 + vec2(TIME * 0.008, TIME * 0.004));
		float n2 = fbm4(dome_uv * 2.75 - vec2(TIME * 0.012, -TIME * 0.005));
		float density = n1 * 0.68 + n2 * 0.32;

		float thresh = mix(0.62, 0.28, cloud_cover);
		float cloud_alpha = smoothstep(thresh, thresh + 0.26, density) * smoothstep(0.01, 0.18, dir.y);
		vec3 cloud_lit = mix(vec3(0.24, 0.28, 0.38), mix(vec3(0.96, 0.97, 0.99), vec3(0.98, 0.72, 0.52), golden_t * 0.65), day_t);
		vec3 cloud_shadow = mix(vec3(0.14, 0.17, 0.24), vec3(0.56, 0.60, 0.66), day_t);
		vec3 cloud_col = mix(cloud_shadow, cloud_lit, smoothstep(0.25, 0.80, n1) * (0.65 + 0.35 * sun_dot));

		col = mix(col, cloud_col, cloud_alpha * 0.92);
	}

	COLOR = col;
}
