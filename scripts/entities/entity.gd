class_name Entity
extends CharacterBody3D
## Anything that fights: players and mobs. Holds combat stats and state; the
## rules that change that state live in the World autoload.

signal stats_changed

const GRAVITY := 22.0

var entity_id := -1
var display_name := ""
var level := 1
var faction := ""

var max_hp := 10
var hp := 10
var max_mana := 0
var mana := 0
var ac := 0
var dmg_min := 1
var dmg_max := 2
var attack_delay := 3.0
var attack_verb: Array = ["hit", "hits"]
var hp_regen := 1
var mana_regen := 0
var spells: Array = []

var dead := false
var sitting := false
var target: Node3D = null  # an Entity or a Corpse
var auto_attack := false
var swing_timer := 0.0
var cast: Dictionary = {}
var cooldowns: Dictionary = {}  # spell_id -> seconds left
var hate: Dictionary = {}  # entity_id -> float (used by mobs)
var buffs: Dictionary = {}  # spell_id -> {left, stats: {ac, hp, dmg}}
var dots: Array = []  # [{spell, caster_id, damage, ticks, next}]
var root_left := 0.0  # seconds this entity can't move

var body_height := 1.8
var visual: Node3D  # CharacterModel when the entity has a rigged model
var look: Dictionary = {}  # how to draw this entity; corpses copy it
var worn_gear: Variant = null  # slots whose gear parts show (mobs); null shows the model as authored
var nameplate: Label3D
var net_pos := Vector3.INF  # client: where the server last said this entity is
var net_rot := 0.0


func _init() -> void:
	collision_layer = Layers.ENTITIES
	collision_mask = Layers.WORLD
	floor_snap_length = 0.6


func _enter_tree() -> void:
	if entity_id < 0:
		entity_id = World.register(self)
	else:
		World.objects[entity_id] = self  # a client mirror, under the server's id


## Keeps its id, so moving between zones (out of one tree branch, into
## another) is still the same entity to the server and every client.
func _exit_tree() -> void:
	World.unregister(entity_id)


func valid_target_entity() -> Entity:
	if is_instance_valid(target) and target is Entity and not (target as Entity).dead:
		return target
	return null


## Infinitely far when in another zone: coordinates overlap between zones.
func distance_to(other: Node3D) -> float:
	if World.zone_of(self) != World.zone_of(other):
		return INF
	return global_position.distance_to(other.global_position)


func add_hate(_src: Entity, _amount: float) -> void:
	pass


## Recomputes stats that buffs change. Players rebuild everything; others
## have nothing buff-dependent yet.
func recalc_stats() -> void:
	pass


## Sum of one stat across active buffs.
func buff_total(stat: String) -> int:
	var total := 0
	for b: Dictionary in buffs.values():
		total += int(b["stats"].get(stat, 0))
	return total


func face_toward(pos: Vector3) -> void:
	var d := pos - global_position
	d.y = 0.0
	if d.length_squared() > 0.0001:
		rotation.y = atan2(-d.x, -d.z)


func apply_gravity(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= GRAVITY * delta


## Client: glides toward the server's latest position for this entity, and
## sets velocity from the motion so the walk and run animations follow.
func puppet(delta: float) -> void:
	if net_pos == Vector3.INF:
		return
	var before := global_position
	if global_position.distance_to(net_pos) > 12.0:
		global_position = net_pos
	else:
		global_position = global_position.lerp(net_pos, minf(1.0, delta * 10.0))
	rotation.y = lerp_angle(rotation.y, net_rot, minf(1.0, delta * 10.0))
	velocity = (global_position - before) / maxf(delta, 0.001)
	velocity.y = 0.0


## Client: dead, sitting and casting as the server reports them.
func set_net_flags(is_dead: bool, is_sitting: bool, is_casting: bool) -> void:
	sitting = is_sitting
	if is_casting and cast.is_empty():
		cast = {"spell": "", "time": 0.0, "total": 1.0}
	elif not is_casting:
		cast = {}
	if is_dead != dead:
		dead = is_dead
		if visual != null:
			visual.visible = not dead
		if nameplate != null:
			nameplate.visible = not dead


## Visual events from the rules ("attack", "hit", "spawn"). No-op for primitive art.
func animate(event: String) -> void:
	Net.broadcast_anim(self, event)
	if not (visual is CharacterModel):
		return
	var m := visual as CharacterModel
	match event:
		"attack":
			m.play_once("attack", 1.6)
		"hit":
			m.play_once("hit", 1.0, false)
		_:
			m.play_once(event)


func build_body(shape: String, color: Color, body_scale: float, model_id := "", weapon_id := "") -> void:
	look = {"shape": shape, "color": color.to_html(), "scale": body_scale, "model": model_id, "weapon": weapon_id}
	if worn_gear != null:
		look["gear"] = worn_gear
	var is_beetle := shape == "beetle"
	body_height = (0.95 if is_beetle else 1.85) * body_scale
	var capsule := CapsuleShape3D.new()
	capsule.radius = (0.55 if is_beetle else 0.38) * body_scale
	capsule.height = maxf(body_height, capsule.radius * 2.0)
	var col := CollisionShape3D.new()
	col.shape = capsule
	col.position.y = capsule.height * 0.5
	add_child(col)

	visual = make_visual(look)
	add_child(visual)

	nameplate = Label3D.new()
	nameplate.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	nameplate.fixed_size = true  # same on-screen size at any distance, like EQ
	nameplate.font_size = 32
	nameplate.pixel_size = 0.0009
	nameplate.outline_size = 8
	nameplate.position.y = body_height + 0.45
	nameplate.visibility_range_end = 70.0
	add_child(nameplate)


## Builds the visual described by a look dictionary: a rigged model if one is
## set, otherwise placeholder primitives.
static func make_visual(look_: Dictionary) -> Node3D:
	var body_scale := float(look_.get("scale", 1.0))
	if str(look_.get("model", "")) != "":
		var m := CharacterModel.new()
		m.setup(look_["model"], str(look_.get("weapon", "")), body_scale, look_.get("gear"))
		m.set_offhand(str(look_.get("offhand", "")))
		if look_.has("worn"):
			m.set_worn(look_["worn"])
		use_entity_layer(m)
		return m
	var shape := str(look_.get("shape", "humanoid"))
	var color := Color.html(str(look_.get("color", "ffffff")))
	var root := Node3D.new()
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.85
	var dark := StandardMaterial3D.new()
	dark.albedo_color = color.darkened(0.55)
	dark.roughness = 0.9
	match shape:
		"beetle":
			_part(root, _sphere(0.6), mat, Vector3(0, 0.45, 0.1), Vector3(1.0, 0.65, 1.35))
			_part(root, _sphere(0.28), dark, Vector3(0, 0.42, -0.72), Vector3.ONE)
		"skeleton":
			_part(root, _capsule(0.18, 1.3), mat, Vector3(0, 0.75, 0), Vector3.ONE)
			_part(root, _box(Vector3(0.6, 0.1, 0.18)), mat, Vector3(0, 1.3, 0), Vector3.ONE)
			_part(root, _sphere(0.22), mat, Vector3(0, 1.62, 0), Vector3.ONE)
			_part(root, _sphere(0.05), dark, Vector3(-0.08, 1.66, -0.19), Vector3.ONE)
			_part(root, _sphere(0.05), dark, Vector3(0.08, 1.66, -0.19), Vector3.ONE)
		_:
			_part(root, _capsule(0.35, 1.35), mat, Vector3(0, 0.72, 0), Vector3.ONE)
			_part(root, _sphere(0.24), mat, Vector3(0, 1.6, 0), Vector3.ONE)
			_part(root, _box(Vector3(0.3, 0.08, 0.12)), dark, Vector3(0, 1.63, -0.2), Vector3.ONE)
	root.scale = Vector3.ONE * body_scale
	use_entity_layer(root)
	return root


## Moves every mesh under `node` to the entity render layer, so ground decals
## (the target marker) don't paint characters' feet.
static func use_entity_layer(node: Node) -> void:
	for g in node.find_children("*", "GeometryInstance3D", true, false):
		(g as GeometryInstance3D).layers = Layers.RENDER_ENTITIES


static func _part(root: Node3D, mesh: Mesh, mat: Material, pos: Vector3, scl: Vector3) -> void:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = mat
	mi.position = pos
	mi.scale = scl
	root.add_child(mi)


static func _sphere(r: float) -> SphereMesh:
	var m := SphereMesh.new()
	m.radius = r
	m.height = r * 2.0
	return m


static func _capsule(r: float, h: float) -> CapsuleMesh:
	var m := CapsuleMesh.new()
	m.radius = r
	m.height = h
	return m


static func _box(size: Vector3) -> BoxMesh:
	var m := BoxMesh.new()
	m.size = size
	return m
