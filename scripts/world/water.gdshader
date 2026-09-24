shader_type spatial;
// Still water for ponds. Reads the depth behind the surface so it is clear
// and pale where shallow, dark where deep, with a light rim where it meets
// the shore. Small ripples bend the normal so the sky glints across it.

render_mode blend_mix, depth_draw_opaque, cull_disabled, specular_schlick_ggx;

uniform vec3 shallow : source_color = vec3(0.22, 0.42, 0.46);
uniform vec3 deep : source_color = vec3(0.05, 0.16, 0.24);
uniform vec3 sky : source_color = vec3(0.62, 0.74, 0.86);
uniform float murk = 0.9;  // meters of water until it looks fully deep
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
}
