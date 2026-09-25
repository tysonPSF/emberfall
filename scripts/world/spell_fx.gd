class_name SpellFx
extends Node3D
## What a spell looks like when it lands, and the glow in a caster's hands
## while they cast. Purely a picture: the rules already happened (World emits
## spell_fx, and online Net.broadcast_fx sends it to everyone who can see).
##
## A spell names its look with "fx": {"kind", "color"} in data/spells.json;
## without one it gets a sensible default for its type. Kinds:
##   burst   damage: a flash of sparks out from the chest
##   impact  a kick, bash or strike: a short white shock
##   heal    motes rising around the target
##   buff    a ring rising up the target, with sparkles
##   dot     embers or venom that linger and curl up
##   root    a ring of green at the feet, tendrils rising
##   gate    a column swirling up
##   taunt   a red pulse at the head

const DEFAULTS := {
	"damage": ["burst", "#b98cff"], "heal": ["heal", "#9cff8a"], "buff": ["buff", "#ffd66b"],
	"dot": ["dot", "#ff7a2a"], "root": ["root", "#6fd46f"], "gate": ["gate", "#7ab8ff"], "taunt": ["taunt", "#ff4a3a"],
}

static var _dot_texture: Texture2D


## World.spell_fx lands here, on every machine that draws.
static func play(caster: Entity, target: Entity, spell_id: String) -> void:
	if target == null or not is_instance_valid(target) or not target.is_inside_tree():
		return
	var s: Dictionary = GameData.spells.get(spell_id, {})
	var def: Array = DEFAULTS.get(str(s.get("type", "")), ["burst", "#ffffff"])
	if s.get("ability", false) and str(s.get("type", "")) == "damage":
		def = ["impact", "#fff4d8"]
	var fx: Dictionary = s.get("fx", {})
	var kind := str(fx.get("kind", def[0]))
	var color := Color.html(str(fx.get("color", def[1])))
	var node := SpellFx.new()
	target.add_child(node)
	node._build(kind, color, target)


## A glow and a few motes at the hands while an entity is casting; the HUD's
## entities call this every frame (it adds or removes the glow as needed).
static func update_cast(e: Entity) -> void:
	var glow := e.get_node_or_null("CastGlow") as Node3D
	var casting := not e.cast.is_empty() and not e.dead
	if casting and glow == null:
		var spell: Dictionary = GameData.spells.get(str(e.cast.get("spell", "")), {})
		var fx: Dictionary = spell.get("fx", {})
		var color := Color.html(str(fx.get("color", DEFAULTS.get(str(spell.get("type", "")), ["", "#d8c4ff"])[1])))
		glow = Node3D.new()
		glow.name = "CastGlow"
		glow.position = Vector3(0, 1.0, -0.3)
		e.add_child(glow)
		var light := OmniLight3D.new()
		light.light_color = color
		light.light_energy = 1.4
		light.omni_range = 3.0
		glow.add_child(light)
		var motes := _particles(18, 0.9, color, 0.07)
		motes.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
		motes.emission_sphere_radius = 0.25
		motes.direction = Vector3.UP
		motes.spread = 50.0
		motes.initial_velocity_min = 0.3
		motes.initial_velocity_max = 0.8
		motes.gravity = Vector3(0, 0.5, 0)
		motes.orbit_velocity_min = 0.4
		motes.orbit_velocity_max = 0.8
		motes.explosiveness = 0.0
		motes.one_shot = false
		glow.add_child(motes)
	elif not casting and glow != null:
		glow.queue_free()


func _build(kind: String, color: Color, target: Entity) -> void:
	var h := 1.0 * target.scale.y
	var life := 1.0
	match kind:
		"burst":
			position = Vector3(0, h, 0)
			var p := _particles(50, 0.65, color, 0.15)
			p.direction = Vector3.UP
			p.spread = 180.0
			p.initial_velocity_min = 2.5
			p.initial_velocity_max = 4.5
			p.gravity = Vector3(0, -3, 0)
			add_child(p)
			_flash(color, 3.5, 5.0, 0.4)
			life = 0.9
		"impact":
			position = Vector3(0, h * 0.9, 0)
			var p := _particles(14, 0.3, color, 0.18)
			p.spread = 180.0
			p.initial_velocity_min = 4.0
			p.initial_velocity_max = 6.0
			p.gravity = Vector3.ZERO
			add_child(p)
			_ring(color, 0.25, 1.1, 0.25, Vector3.ZERO, true)
			_flash(Color(1, 0.95, 0.85), 2.5, 3.0, 0.2)
			life = 0.5
		"heal":
			var p := _particles(44, 1.3, color, 0.13)
			p.emission_shape = CPUParticles3D.EMISSION_SHAPE_RING
			p.emission_ring_axis = Vector3.UP
			p.emission_ring_radius = 0.6
			p.emission_ring_inner_radius = 0.3
			p.emission_ring_height = 0.1
			p.position = Vector3(0, 0.1, 0)
			p.direction = Vector3.UP
			p.spread = 10.0
			p.initial_velocity_min = 1.4
			p.initial_velocity_max = 2.4
			p.gravity = Vector3.ZERO
			p.explosiveness = 0.3
			add_child(p)
			_flash(color, 1.8, 4.0, 0.9)
			life = 1.8
		"buff":
			_ring(color, 0.7, 0.9, 1.1, Vector3(0, 0.1, 0), false, h * 1.8)
			var p := _particles(20, 1.0, color, 0.1)
			p.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
			p.emission_sphere_radius = 0.7
			p.position = Vector3(0, h, 0)
			p.direction = Vector3.UP
			p.initial_velocity_min = 0.3
			p.initial_velocity_max = 0.9
			p.gravity = Vector3.ZERO
			p.explosiveness = 0.5
			add_child(p)
			_flash(color, 1.5, 3.5, 1.0)
			life = 1.6
		"dot":
			var p := _particles(40, 1.6, color, 0.13)
			p.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
			p.emission_sphere_radius = 0.45
			p.position = Vector3(0, h * 0.8, 0)
			p.direction = Vector3.UP
			p.spread = 30.0
			p.initial_velocity_min = 0.5
			p.initial_velocity_max = 1.3
			p.orbit_velocity_min = 0.3
			p.orbit_velocity_max = 0.6
			p.gravity = Vector3(0, 0.4, 0)
			p.explosiveness = 0.1
			add_child(p)
			_flash(color, 1.5, 3.0, 0.6)
			life = 2.2
		"root":
			_ring(color, 0.9, 0.6, 1.5, Vector3(0, 0.05, 0), false)
			var p := _particles(30, 1.2, color, 0.1)
			p.emission_shape = CPUParticles3D.EMISSION_SHAPE_RING
			p.emission_ring_axis = Vector3.UP
			p.emission_ring_radius = 0.8
			p.emission_ring_inner_radius = 0.6
			p.emission_ring_height = 0.05
			p.direction = Vector3.UP
			p.spread = 15.0
			p.initial_velocity_min = 0.6
			p.initial_velocity_max = 1.2
			p.gravity = Vector3(0, -0.4, 0)
			p.explosiveness = 0.4
			add_child(p)
			life = 1.8
		"gate":
			var p := _particles(60, 1.2, color, 0.12)
			p.emission_shape = CPUParticles3D.EMISSION_SHAPE_RING
			p.emission_ring_axis = Vector3.UP
			p.emission_ring_radius = 0.7
			p.emission_ring_inner_radius = 0.5
			p.emission_ring_height = 0.1
			p.direction = Vector3.UP
			p.spread = 5.0
			p.initial_velocity_min = 2.5
			p.initial_velocity_max = 4.0
			p.orbit_velocity_min = 1.0
			p.orbit_velocity_max = 1.4
			p.gravity = Vector3.ZERO
			p.explosiveness = 0.2
			add_child(p)
			_flash(color, 3.0, 5.0, 1.0)
			life = 1.8
		"taunt":
			_ring(color, 0.4, 1.4, 0.45, Vector3(0, h * 1.5, 0), true)
			_flash(color, 2.0, 3.0, 0.4)
			life = 0.7
	var t := get_tree().create_timer(life)
	t.timeout.connect(queue_free)


## A one-shot burst of glowing, fading sprites.
static func _particles(amount: int, lifetime: float, color: Color, size: float) -> CPUParticles3D:
	var p := CPUParticles3D.new()
	p.amount = amount
	p.lifetime = lifetime
	p.one_shot = true
	p.explosiveness = 1.0
	p.local_coords = false
	var quad := QuadMesh.new()
	quad.size = Vector2.ONE * size * 1.9
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA  # mixed, not added: added light washes out in daylight
	mat.vertex_color_use_as_albedo = true
	mat.albedo_texture = _dot()
	mat.no_depth_test = false
	quad.material = mat
	p.mesh = quad
	var ramp := Gradient.new()  # a bright core that settles to the spell's color and fades
	ramp.set_color(0, Color(color.lightened(0.55), 1.0))
	ramp.add_point(0.35, Color(color, 0.95))
	ramp.set_color(ramp.get_point_count() - 1, Color(color.darkened(0.1), 0.0))
	p.color_ramp = ramp
	var shrink := Curve.new()
	shrink.add_point(Vector2(0, 1))
	shrink.add_point(Vector2(1, 0.2))
	p.scale_amount_curve = shrink
	p.emitting = true
	return p


## A soft round spot, for every sprite.
static func _dot() -> Texture2D:
	if _dot_texture == null:
		var g := Gradient.new()
		g.set_color(0, Color(1, 1, 1, 1))
		g.set_color(1, Color(1, 1, 1, 0))
		var t := GradientTexture2D.new()
		t.gradient = g
		t.fill = GradientTexture2D.FILL_RADIAL
		t.fill_from = Vector2(0.5, 0.5)
		t.fill_to = Vector2(1.0, 0.5)
		t.width = 32
		t.height = 32
		_dot_texture = t
	return _dot_texture


## A glowing ring that grows (and rises, for a buff) as it fades.
func _ring(color: Color, radius: float, grow: float, time: float, at: Vector3, upright: bool, rise := 0.0) -> void:
	var ring := MeshInstance3D.new()
	var torus := TorusMesh.new()
	torus.inner_radius = radius * 0.8
	torus.outer_radius = radius
	torus.rings = 24
	torus.ring_segments = 6
	ring.mesh = torus
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.albedo_color = color.lightened(0.2)
	ring.material_override = mat
	ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	ring.position = at
	if upright:
		ring.rotation.x = PI / 2.0
		ring.top_level = true  # faces the same way whatever the target does
		ring.global_position = global_position + at
	add_child(ring)
	var tw := ring.create_tween().set_parallel(true)
	tw.tween_property(ring, "scale", Vector3.ONE * (1.0 + grow), time).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	tw.tween_property(mat, "albedo_color", Color(color, 0.0), time)
	if rise > 0.0:
		tw.tween_property(ring, "position:y", at.y + rise, time).set_trans(Tween.TRANS_SINE)


func _flash(color: Color, energy: float, reach: float, time: float) -> void:
	var light := OmniLight3D.new()
	light.light_color = color
	light.light_energy = energy
	light.omni_range = reach
	light.position = Vector3(0, 0.3, 0)
	add_child(light)
	light.create_tween().tween_property(light, "light_energy", 0.0, time)
