shader_type spatial;
// A coat that shifts through the rainbow (June, Lanternhold's unicorn): bands
// of color run along the body and slowly drift, so she's never one color for
// long. Pale parts take the full rainbow; dark ones (hooves, eyes) keep theirs.

uniform vec4 albedo : source_color = vec4(1.0);
uniform float roughness = 0.5;
uniform float speed = 0.12;      // turns of the color wheel a second
uniform float bands = 0.9;       // how many rainbows fit along a meter of her
uniform float strength = 0.85;   // how much of the pale parts the rainbow takes
uniform float glow = 0.35;       // a soft shimmer of the same colors

varying vec3 local_pos;

void vertex() {
	local_pos = VERTEX;
}

vec3 hue(float h) {
	vec3 k = abs(fract(h + vec3(0.0, 2.0 / 3.0, 1.0 / 3.0)) * 6.0 - 3.0) - 1.0;
	return clamp(k, 0.0, 1.0);
}

void fragment() {
	float pale = smoothstep(0.35, 0.8, dot(albedo.rgb, vec3(0.299, 0.587, 0.114)));
	float h = TIME * speed + dot(local_pos, vec3(0.35, 0.55, 1.0)) * bands;
	vec3 rainbow = mix(vec3(1.0), hue(h), 0.75);  // pastel, not neon
	vec3 col = mix(albedo.rgb, albedo.rgb * rainbow, strength * pale);
	ALBEDO = col;
	ROUGHNESS = roughness;
	EMISSION = hue(h) * glow * pale;
}
