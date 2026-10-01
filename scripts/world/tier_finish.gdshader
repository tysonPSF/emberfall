shader_type spatial;
// A quality tier's finish (data/loot.json "finish") laid only on the metal of
// a weapon or a piece of armor: a blade, a club's spikes, plate. The parts
// with color of their own (wood, leather, cloth, gold) keep their natural look.
// Metal is told by its color: gray (little saturation) and not near black.
// CharacterModel._finished builds this from the mesh's own material.

uniform vec4 albedo_color : source_color = vec4(1.0);
uniform sampler2D albedo_tex : source_color, filter_linear_mipmap;
uniform bool has_tex = false;
uniform bool use_vertex = false;
uniform float rough_base = 1.0;
uniform vec4 tint : source_color = vec4(1.0);
uniform float metal_f = 0.0;
uniform float rough_f = -1.0;  // below 0: the material's own roughness
uniform float rim_f = 0.0;
uniform vec4 glow : source_color = vec4(0.0);
uniform float glow_energy = 0.0;
uniform float wash = 1.0;  // how strongly the tier's color washes into the metal: 1 on a weapon, less on worn plate

void fragment() {
	vec4 c = albedo_color;
	if (has_tex) {
		c *= texture(albedo_tex, UV);
	}
	if (use_vertex) {
		c *= COLOR;
	}
	float hi = max(c.r, max(c.g, c.b));
	float lo = min(c.r, min(c.g, c.b));
	float sat = hi > 0.001 ? (hi - lo) / hi : 0.0;
	float metal = (1.0 - smoothstep(0.16, 0.34, sat)) * smoothstep(0.08, 0.22, hi);
	ALBEDO = mix(c.rgb, c.rgb * tint.rgb, metal);
	// the tier's color washes into the metal itself (fine green, superior blue, masterwork violet), stronger the higher the tier
	ALBEDO = mix(ALBEDO, glow.rgb * max(hi, 0.5), metal * min(glow_energy * 4.0, 0.4) * wash);
	METALLIC = metal_f * metal;
	ROUGHNESS = mix(rough_base, rough_f < 0.0 ? rough_base : rough_f, metal);
	RIM = rim_f * metal;
	RIM_TINT = 0.3;
	EMISSION = glow.rgb * glow_energy * (1.0 + wash) * metal;
}
