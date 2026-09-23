shader_type spatial;
// Ground clutter (grass, flowers, ferns...) drawn with MultiMesh. Samples the
// KayKit palette texture, multiplies by the per-instance color (grass takes
// the ground color it stands on), and sways the tops in the wind.

render_mode cull_disabled, depth_draw_opaque;

uniform sampler2D albedo_tex : source_color, filter_nearest;
uniform float sway = 0.0;  // meters of sway at 1 m height; 0 for rigid things

varying vec3 tint;

void vertex() {
	tint = COLOR.rgb;
	if (sway > 0.0) {
		vec3 world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
		float phase = TIME * 1.7 + world.x * 0.35 + world.z * 0.27;
		float gust = 0.6 + 0.4 * sin(TIME * 0.45 + world.x * 0.05);
		float bend = sway * gust * max(VERTEX.y, 0.0);
		VERTEX.x += sin(phase) * bend;
		VERTEX.z += cos(phase * 0.8) * bend * 0.6;
	}
}

void fragment() {
	ALBEDO = texture(albedo_tex, UV).rgb * tint;
	ROUGHNESS = 0.95;
	SPECULAR = 0.2;
}
