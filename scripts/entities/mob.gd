class_name Mob
extends Entity
## An NPC enemy. Idles and wanders near its spawn, aggros on players it can
## see (if aggressive), calls nearby friends for help, flees at low health,
## and walks home to reset if dragged too far.

enum State { IDLE, WANDER, COMBAT, FLEE, RETURN }

const FLEE_AT := 0.18
const STOP_FLEE_AT := 0.35

var mob_id := ""
var data: Dictionary = {}
var spawn_point: SpawnPoint
var home := Vector3.ZERO
var state := State.IDLE
var speed := 5.0
var aggressive := false
var aggro_radius := 0.0
var social := false
var flees := false
var wander_radius := 8.0
var shape := "humanoid"
var color := Color.WHITE
var body_scale := 1.0
var model_id := ""
var weapon_id := ""

var _think_timer := 0.0
var _scan_timer := 0.0
var _plate_timer := 0.0
var _wander_target := Vector3.ZERO


func setup(id: String, d: Dictionary, sp: SpawnPoint) -> void:
	mob_id = id
	data = d
	spawn_point = sp
	var levels: Array = d["level"]
	level = randi_range(int(levels[0]), int(levels[1]))
	display_name = d["name"]
	faction = d["faction"]
	max_hp = int(d["hp_base"]) + int(d["hp_per_level"]) * (level - 1)
	hp = max_hp
	dmg_min = int(d["dmg_min"])
	dmg_max = int(d["dmg_max"]) + level / 2
	attack_delay = float(d["attack_delay"])
	ac = int(d["ac"])
	attack_verb = d["verb"]
	hp_regen = maxi(1, level)
	speed = float(d["speed"])
	aggressive = d["aggressive"]
	aggro_radius = float(d["aggro_radius"])
	social = d["social"]
	flees = d["flees"]
	shape = d["shape"]
	color = Color.html(d["color"])
	body_scale = float(d["scale"])
	var model: Variant = d.get("model", "")
	model_id = str(model.pick_random()) if model is Array else str(model)
	weapon_id = str(d.get("weapon", ""))
	wander_radius = sp.wander_radius if sp != null else 0.0


func _ready() -> void:
	build_body(shape, color, body_scale, model_id, weapon_id)
	nameplate.text = display_name
	if data.has("spawn_anim"):
		animate(data["spawn_anim"])
	home = global_position
	_think_timer = randf_range(1.0, 5.0)


func _process(delta: float) -> void:
	_plate_timer -= delta
	if _plate_timer <= 0.0 and World.local_player != null:
		_plate_timer = 0.5
		nameplate.modulate = World.CON_COLORS[World.con_of(World.local_player.level, level)]


func add_hate(src: Entity, amount: float) -> void:
	if src == null or src == self or dead or src.dead:
		return
	var was_calm := hate.is_empty()
	hate[src.entity_id] = float(hate.get(src.entity_id, 0.0)) + amount
	if state != State.COMBAT and state != State.FLEE:
		state = State.COMBAT
	if was_calm and social:
		World.call_for_help(self, src)


func top_hated() -> Entity:
	var best: Entity = null
	var best_hate := -1.0
	for id: int in hate.keys():
		var e := World.get_object(id) as Entity
		if e == null or e.dead:
			hate.erase(id)
		elif hate[id] > best_hate:
			best_hate = hate[id]
			best = e
	return best


func _physics_process(delta: float) -> void:
	apply_gravity(delta)
	if dead:
		return
	_think_timer -= delta
	var move := Vector3.ZERO
	var move_speed := speed

	match state:
		State.IDLE:
			if _think_timer <= 0.0:
				_think_timer = randf_range(3.0, 9.0)
				if wander_radius > 0.0 and randf() < 0.6:
					var a := randf() * TAU
					var r := randf() * wander_radius
					_wander_target = home + Vector3(cos(a) * r, 0.0, sin(a) * r)
					state = State.WANDER
			_scan_for_aggro(delta)
		State.WANDER:
			move = _dir_to(_wander_target)
			move_speed = speed * 0.35
			if _flat_dist(_wander_target) < 0.8:
				state = State.IDLE
			_scan_for_aggro(delta)
		State.COMBAT:
			var t := top_hated()
			if t == null or _flat_dist(home) > float(World.cfg("mob_leash", 130.0)):
				_reset()
			elif flees and hp < max_hp * FLEE_AT:
				state = State.FLEE
				auto_attack = false
			else:
				target = t
				auto_attack = true
				face_toward(t.global_position)
				if distance_to(t) > World.melee_range() * 0.7:
					move = _dir_to(t.global_position)
		State.FLEE:
			var t := top_hated()
			if t == null or _flat_dist(home) > float(World.cfg("mob_leash", 130.0)):
				_reset()
			elif hp >= max_hp * STOP_FLEE_AT:
				state = State.COMBAT
			else:
				target = t
				move = -_dir_to(t.global_position)
				move_speed = speed * 0.55
		State.RETURN:
			move = _dir_to(home)
			if _flat_dist(home) < 1.0:
				state = State.IDLE
				hp = max_hp
				stats_changed.emit()

	if root_left > 0.0:
		move = Vector3.ZERO  # rooted: turns and swings, but can't walk
	if move != Vector3.ZERO:
		if state != State.COMBAT:
			face_toward(global_position + move)
		velocity.x = move.x * move_speed
		velocity.z = move.z * move_speed
	else:
		velocity.x = 0.0
		velocity.z = 0.0
	move_and_slide()


func _scan_for_aggro(delta: float) -> void:
	_scan_timer -= delta
	if _scan_timer > 0.0:
		return
	_scan_timer = 0.5
	for p in World.get_players():
		if p.dead or World.con_of(p.level, level) == World.Con.GRAY:
			continue
		# aggressive mobs attack anyone close; others only those their faction hates
		var radius := aggro_radius if aggressive else (12.0 if World.mob_kos(p, faction) else 0.0)
		if radius > 0.0 and distance_to(p) <= radius:
			add_hate(p, 1.0)
			return


func _reset() -> void:
	hate.clear()
	target = null
	auto_attack = false
	cast = {}
	state = State.RETURN


func _dir_to(pos: Vector3) -> Vector3:
	var d := pos - global_position
	d.y = 0.0
	return d.normalized() if d.length_squared() > 0.0001 else Vector3.ZERO


func _flat_dist(pos: Vector3) -> float:
	return Vector2(pos.x - global_position.x, pos.z - global_position.z).length()
