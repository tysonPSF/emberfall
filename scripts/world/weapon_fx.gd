class_name WeaponFx
extends Node3D
## A held weapon's own effect, from models.json "weapon_fx" {model: {...}}:
## "motes" a color: small glowing specks drifting up off it, as from the
## Living Roots' sap; "reach" how far up the weapon they rise from (meters,
## from the grip); "glow" a soft light of that color round it (energy).
## Only drawn where looks are (never on a dedicated server).


static func make(spec: Dictionary) -> Node3D:
	var root := WeaponFx.new()
	var color := Color.html(str(spec.get("motes", "#8aff5a")))
	var reach := float(spec.get("reach", 0.8))
	var p := GPUParticles3D.new()
	p.amount = int(spec.get("amount", 10))
	p.lifetime = 1.6
	p.local_coords = false  # left behind as the weapon moves, so a swing trails them
	var m := ParticleProcessMaterial.new()
	m.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	m.emission_box_extents = Vector3(0.06, reach * 0.5, 0.06)
	m.direction = Vector3(0, 1, 0)
	m.spread = 40.0
	m.initial_velocity_min = 0.05
	m.initial_velocity_max = 0.18
	m.gravity = Vector3(0, 0.12, 0)  # they drift up, as seeds and spores do
	m.scale_min = 0.6
	m.scale_max = 1.2
	var fade := Gradient.new()
	fade.set_color(0, Color(color, 0.0))
	fade.add_point(0.25, Color(color, 1.0))
	fade.set_color(fade.get_point_count() - 1, Color(color, 0.0))
	var ramp := GradientTexture1D.new()
	ramp.gradient = fade
	m.color_ramp = ramp
	p.process_material = m
	var quad := QuadMesh.new()
	quad.size = Vector2(0.035, 0.035)
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	mat.vertex_color_use_as_albedo = true
	mat.albedo_color = Color(1.4, 1.4, 1.4)
	quad.material = mat
	p.draw_pass_1 = quad
	p.position = Vector3(0, reach * 0.55, 0)
	p.visibility_aabb = AABB(Vector3(-1, -1, -1), Vector3(2, 3, 2))
	root.add_child(p)
	if spec.has("glow"):
		var light := OmniLight3D.new()
		light.light_color = color
		light.light_energy = float(spec["glow"])
		light.omni_range = 1.2
		light.position = Vector3(0, reach * 0.55, 0)
		light.distance_fade_enabled = true
		light.distance_fade_begin = 15.0
		light.distance_fade_length = 5.0
		root.add_child(light)
	return root
