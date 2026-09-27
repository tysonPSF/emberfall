shader_type spatial;
// Water for ponds (still) and rivers (flow_speed > 0: ripples run along
// UV.y, the ribbon's length in meters, so they follow every bend). Reads the depth behind the surface so it is clear
// and pale where shallow, dark where deep, with a light rim where it meets
// the shore. Small ripples bend the normal so the sky glints across it.

render_mode blend_mix, depth_draw_opaque, cull_disabled, specular_schlick_ggx;

uniform vec3 shallow : source_color = vec3(0.22, 0.42, 0.46);
uniform vec3 deep : source_color = vec3(0.05, 0.16, 0.24);
uniform vec3 sky : source_color = vec3(0.62, 0.74, 0.86);
uniform float murk = 0.9;  // meters of water until it looks fully deep
uniform float flow_speed = 0.0;  // meters per second downstream
uniform float lava = 0.0;  // 1: molten rock instead of water (Cinderpass): a glowing flow under a drifting dark crust
uniform sampler2D depth_tex : hint_depth_texture, filter_linear_mipmap;

void fragment() {
	float depth = texture(depth_tex, SCREEN_UV).r;
	vec4 behind = INV_PROJECTION_MATRIX * vec4(SCREEN_UV * 2.0 - 1.0, depth, 1.0);
	behind.xyz /= behind.w;
	float thick = max(VERTEX.z - behind.z, 0.0);
	float t = clamp(thick / murk, 0.0, 1.0);

	vec3 world = (INV_VIEW_MATRIX * vec4(VERTEX, 1.0)).xyz;
	vec2 ripple = vec2(
		sin(world.x * 1.7 + TIME * 1.1) + sin(world.z * 2.3 - TIME * 0.8) * 0.6,
		cos(world.z * 1.9 + TIME * 0.9) + cos(world.x * 2.6 + TIME * 1.3) * 0.6);
	if (flow_speed > 0.0) {
		float run = UV.y - TIME * flow_speed;
		ripple += vec2(sin(run * 2.1 + UV.x * 3.0), cos(run * 1.7 - UV.x * 5.0)) * 1.2;
	}
	vec3 n = normalize(vec3(ripple.x * 0.05, 1.0, ripple.y * 0.05));
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);

	float rim = 1.0 - smoothstep(0.0, 0.12, thick);
	// the sky shows in the water more the flatter you look across it
	float fresnel = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 3.0);
	vec3 water = mix(mix(shallow, deep, t), sky, 0.08 + fresnel * 0.5);
	ALBEDO = mix(water, vec3(0.6, 0.7, 0.66), rim * 0.35);
	ALPHA = (mix(0.7, 0.95, t) + rim * 0.2) * smoothstep(0.0, 0.03, thick);
	ROUGHNESS = 0.06;
	SPECULAR = 0.6;
	if (lava > 0.5) {
		float run = UV.y - TIME * max(flow_speed, 0.15);
		float cells = sin(run * 2.9 + UV.x * 4.3) * sin(world.x * 2.1 + run * 1.3) + sin(world.z * 2.4 - run * 1.9 + UV.x * 3.1) * 0.7
				+ sin(world.x * 5.3 - world.z * 4.1 + run * 2.0) * 0.25;
		float crust = smoothstep(0.0, 0.55, cells);  // dark plates of cooling rock riding the flow
		float pulse = 0.85 + 0.15 * sin(TIME * 1.7 + world.x * 0.3 + world.z * 0.2);
		vec3 hot = mix(vec3(0.85, 0.12, 0.01), vec3(1.0, 0.45, 0.06), smoothstep(-0.9, -0.1, cells));  // deep red where it's hottest, orange at the crust's edge
		ALBEDO = mix(hot * 0.35, vec3(0.06, 0.045, 0.04), crust);
		EMISSION = hot * (1.0 - crust) * 1.7 * pulse;
		ALPHA = 1.0;
		ROUGHNESS = mix(0.35, 0.9, crust);
		SPECULAR = 0.2;
	}
}
