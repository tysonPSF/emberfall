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
var gear: Dictionary = {}  # slot -> item id it spawned wearing; drops on death

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
	gear = World.roll_gear(d, level)
	for slot: String in gear:  # what it wears protects it; what it holds hits harder
		var it := GameData.item(gear[slot])
		ac += int(it.get("ac", 0))
		max_hp += int(it.get("hp", 0)) + int(it.get("sta", 0))
		if slot == "primary":
			dmg_max += int(it.get("dmg", 0)) / 2 + int(it.get("str", 0)) / 5
			attack_verb = it.get("verb", attack_verb)
	hp = max_hp
	var model: Variant = d.get("model", "")
	model_id = _pick_model(model if model is Array else [model])
	weapon_id = str(GameData.item(gear["primary"]).get("model", "")) if gear.has("primary") else str(d.get("weapon", ""))
	if d.has("gear"):
		worn_gear = gear.keys()
	wander_radius = sp.wander_radius if sp != null else 0.0


## Client: a mirror of a mob the server spawned. Nothing is rolled here; the
## body is drawn exactly as the server describes it.
func setup_remote(info: Dictionary) -> void:
	mob_id = str(info["mob_id"])
	data = GameData.mobs.get(mob_id, {})
	entity_id = int(info["id"])
	display_name = str(info["name"])
	level = int(info["level"])
	faction = str(data.get("faction", ""))
	max_hp = int(info["max_hp"])
	hp = int(info["hp"])
	shape = str(data.get("shape", "humanoid"))
	color = Color.html(str(data.get("color", "#ffffff")))
	body_scale = float(data.get("scale", 1.0))
	look = info["look"]
	model_id = str(look.get("model", ""))
	weapon_id = str(look.get("weapon", ""))
	worn_gear = look.get("gear")


## Shows gear it spawned with on its body, for the slots its model can wear
## ("wearable_slots" in models.json: a gnoll's head is its own, say).
func _wear_gear() -> void:
	var spec: Variant = GameData.models["characters"].get(model_id, "")
	var slots: Array = spec.get("wearable_slots", []) if spec is Dictionary else []
	var worn := {}
	for slot: String in gear:
		var wear := str(GameData.item(gear[slot]).get("wear", ""))
		if wear != "" and slot in slots:
			worn[slot] = wear
	if not worn.is_empty() and visual is CharacterModel:
		look["worn"] = worn
		(visual as CharacterModel).set_worn(worn)


## A body variant that can show everything this mob is wearing, if any can.
func _pick_model(choices: Array) -> String:
	var parts_of := func(id: Variant) -> Dictionary:
		var spec: Variant = GameData.models["characters"].get(str(id), "")
		return spec.get("gear_parts", {}) if spec is Dictionary else {}
	var showable := {}  # slots at least one variant can show
	for id: Variant in choices:
		showable.merge(parts_of.call(id))
	var fits := choices.filter(func(id: Variant) -> bool:
		var parts: Dictionary = parts_of.call(id)
		for slot: String in gear:
			if showable.has(slot) and not parts.has(slot):
				return false
		return true)
	return str((fits if not fits.is_empty() else choices).pick_random())


func _ready() -> void:
	var mirrored := look.duplicate()
	build_body(shape, color, body_scale, model_id, weapon_id)
	if not Net.is_authority():
		look = mirrored
		if visual is CharacterModel:
			(visual as CharacterModel).set_tiers(look.get("tiers", {}))
			(visual as CharacterModel).set_offhand(str(look.get("offhand", "")))
			(visual as CharacterModel).set_worn(look.get("worn", {}))
		nameplate.text = display_name
		return
	if visual is CharacterModel:
		look["tiers"] = GameData.gear_tiers(gear)  # a Masterwork drop shows before the kill
		(visual as CharacterModel).set_tiers(look["tiers"])
	_wear_gear()
	if gear.has("secondary") and visual is CharacterModel:
		var shield := str(GameData.item(gear["secondary"]).get("model", ""))
		look["offhand"] = shield
		(visual as CharacterModel).set_offhand(shield)
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


## Another living one of its kind (same faction: pups and scouts are both
## gnolls) close by. Nobody runs while their pack still stands; the last one
## left does.
func _kin_nearby() -> bool:
	for m in World.get_mobs():
		if m != self and not m.dead and m.faction == faction and m.distance_to(self) <= World.CALL_FOR_HELP_RADIUS:
			return true
	return false


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
	if not Net.is_authority():
		puppet(delta)
		return
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
					_wander_target = nav_snap(home + Vector3(cos(a) * r, 0.0, sin(a) * r))
					state = State.WANDER
			_scan_for_aggro(delta)
		State.WANDER:
			move = nav_dir(_wander_target, delta)
			move_speed = speed * 0.35
			if _flat_dist(_wander_target) < 0.8:
				state = State.IDLE
			_scan_for_aggro(delta)
		State.COMBAT:
			var t := top_hated()
			if t == null or _flat_dist(home) > float(World.cfg("mob_leash", 130.0)):
				_reset()
			elif flees and hp < max_hp * FLEE_AT and not _kin_nearby():
				state = State.FLEE
				auto_attack = false
			else:
				target = t
				auto_attack = true
				face_toward(t.global_position)
				if distance_to(t) > World.melee_range() * 0.7:
					move = nav_dir(t.global_position, delta)
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
			move = nav_dir(home, delta)
			if _flat_dist(home) < 1.0:
				state = State.IDLE
				hp = max_hp
				stats_changed.emit()

	if root_left > 0.0 or stun_left > 0.0:
		move = Vector3.ZERO  # rooted: turns and swings, but can't walk (stunned: not even swings)
	if snare_left > 0.0:
		move_speed *= 0.5
	if move != Vector3.ZERO:
		if state != State.COMBAT:
			face_toward(global_position + move)
		velocity.x = move.x * move_speed
		velocity.z = move.z * move_speed
	else:
		velocity.x = 0.0
		velocity.z = 0.0
		if is_on_floor():
			return  # standing still on the ground: no need to sweep the collision (most mobs, most of the time)
	move_and_slide()


func _scan_for_aggro(delta: float) -> void:
	_scan_timer -= delta
	if _scan_timer > 0.0:
		return
	_scan_timer = 0.5
	for p in World.get_players():
		if p.dead or p.hidden or World.con_of(p.level, level) == World.Con.GRAY:
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
