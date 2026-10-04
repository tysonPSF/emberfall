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
var _move_speed := 0.0


func setup(id: String, d: Dictionary, sp: SpawnPoint) -> void:
	mob_id = id
	data = d
	spawn_point = sp
	var levels: Array = d["level"]
	level = randi_range(int(levels[0]), int(levels[1]))
	display_name = d["name"]
	faction = d["faction"]
	max_hp = int(d["hp_base"]) + int(d["hp_per_level"]) * (level - 1)
	if d.get("named", false):  # one rule for every named: a hard solo at its level (config named_health), then more for each player it faces
		max_hp = int(GameData.typical_hp(level) * float(World.cfg("named_health", 2.75)) * float(d.get("toughness", 1.0)))
	hp = max_hp
	dmg_min = int(d["dmg_min"])
	dmg_max = int(d["dmg_max"]) + level / 2
	attack_delay = float(d["attack_delay"])
	if d.get("named", false):  # and hits as hard as the rule says (config named_damage), keeping its own swing speed and spread
		var own := (dmg_min + dmg_max) * 0.5 / attack_delay
		var want := GameData.typical_dps(level) * float(World.cfg("named_damage", 1.25)) * float(d.get("toughness", 1.0))
		# its natural proc (a breath, a bolt, venom) is part of that: at most named_proc_share of it, its swings the rest
		var proc: Dictionary = d.get("proc", {})
		var s: Dictionary = GameData.spells.get(str(proc.get("spell", "")), {})
		var per_proc := 0.0
		if str(s.get("type", "")) == "damage":
			per_proc = (float(s.get("min", 0)) + float(s.get("max", 0))) * 0.5 + float(s.get("per_level", 0)) * (level - 1)
		elif str(s.get("type", "")) == "dot":
			per_proc = (float(s.get("tick", 0)) + float(s.get("per_level", 0)) * (level - 1)) * float(s.get("ticks", 1))
		if per_proc > 0.0:
			var share := want * float(World.cfg("named_proc_share", 0.3))
			var proc_dps := float(proc.get("chance", 0.0)) * per_proc / attack_delay
			if proc_dps > share:
				proc_chance = share * attack_delay / per_proc
				proc_dps = share
			want -= proc_dps
		var k := want / maxf(own, 0.01)
		dmg_min = maxi(1, roundi(dmg_min * k))
		dmg_max = maxi(dmg_min + 1, roundi(dmg_max * k))
	ac = int(d["ac"])
	attack_verb = d["verb"]
	hp_regen = int(d.get("hp_regen", maxi(1, level)))  # trolls knit fast, even mid-fight
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
	if not d.get("named", false) and sp != null and sp.zone != null and sp.zone.data.has("elite"):
		var e: Dictionary = sp.zone.data["elite"]  # group content: every ordinary monster here is past what one player can take
		make_elite(float(e.get("health", 3.5)), float(e.get("damage", 2.2)))
	solo_max_hp = max_hp
	solo_dmg = Vector2i(dmg_min, dmg_max)
	if d.get("named", false):
		_face(int(d.get("min_players", 1)))  # a group boss is never less than a group
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
	if data.has("block"):  # a web across a passage: players can't pass until it's torn down (on every machine: players move themselves)
		_add_barrier(data["block"])
	if Net.dedicated:
		set_process(false)  # _process only colors the nameplate for a local player; a server has none
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


## A wall on the BARRIER layer ([width, height] m, across the way it faces)
## that stops players, not monsters or the camera, and goes when this does.
## Its pick shape grows to match, so you can click the web anywhere.
func _add_barrier(size: Array) -> void:
	var w := float(size[0])
	var h := float(size[1])
	var wall := StaticBody3D.new()
	wall.collision_layer = Layers.BARRIER
	wall.collision_mask = 0
	var col := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(w, h, 0.8)
	col.shape = box
	col.position.y = h * 0.5
	wall.add_child(col)
	add_child(wall)
	for c in get_children():
		if c is CollisionShape3D and c.shape is CapsuleShape3D:
			var pick := BoxShape3D.new()
			pick.size = Vector3(w, h, 0.8)
			(c as CollisionShape3D).shape = pick
			(c as CollisionShape3D).position.y = h * 0.5
	body_height = h
	nameplate.position.y = h + 0.3


func _process(delta: float) -> void:
	_plate_timer -= delta
	if _plate_timer <= 0.0 and World.local_player != null:
		_plate_timer = 0.5
		nameplate.modulate = World.CON_COLORS[World.con_of(World.local_player.level, level)]


## A named monster grows with the fight: its health (and a little its damage)
## scale with how many players it faces, counted from its hate list with their
## groupmates close by (a healer standing back counts). It only ever grows
## during a fight, its wounds kept as a share of its health, and goes back to
## its own size when it resets.
var proc_chance := -1.0  # its natural proc's chance, when a rule has set it (named); else the data's
var solo_max_hp := 0
var solo_dmg := Vector2i.ZERO
var facing_players := 1
var _face_timer := 0.0


func _face(n: int) -> void:
	facing_players = n
	var ratio := float(hp) / float(maxi(1, max_hp))
	max_hp = int(solo_max_hp * (1.0 + float(World.cfg("named_health_per_player", 0.8)) * (n - 1)))
	hp = clampi(roundi(ratio * max_hp), 1, max_hp)
	var dmg := 1.0 + float(World.cfg("named_damage_per_player", 0.08)) * (n - 1)
	dmg_min = roundi(solo_dmg.x * dmg)
	dmg_max = roundi(solo_dmg.y * dmg)


## The players this fight involves: whoever it hates (a pet's owner for the
## pet), and their groupmates within named_group_radius.
func players_faced() -> Array[Player]:
	var out: Array[Player] = []
	var reach := float(World.cfg("named_group_radius", 60))
	for id: int in hate:
		var e := World.get_object(id) as Entity
		var p: Player = (e as Pet).owner_player() if e is Pet else e as Player
		if p == null or p.dead:
			continue
		for q: Player in World.group_members(p):
			if not q.dead and not q in out and (q == p or q.distance_to(p) <= reach):
				out.append(q)
	return out


## An elite (a zone's "elite" {health, damage}: the gods' realms): health
## `health` times an ordinary monster's at its level (GameData.typical_hp) and
## damage a second `damage` times ordinary, keeping its own swing speed and
## spread, so it takes a group, as a named does but every one of them. Its
## experience grows with its health (World._award_group).
var elite := 1.0


func make_elite(health: float, damage: float) -> void:
	elite = health
	max_hp = int(GameData.typical_hp(level) * health)
	hp = max_hp
	var own := (dmg_min + dmg_max) * 0.5 / attack_delay
	var k := GameData.typical_dps(level) * damage / maxf(own, 0.01)
	dmg_min = maxi(1, roundi(dmg_min * k))
	dmg_max = maxi(dmg_min + 1, roundi(dmg_max * k))
	ac = maxi(ac, roundi(ac * 1.2))


func _check_facing(delta: float) -> void:
	_face_timer -= delta
	if _face_timer > 0.0 or hate.is_empty():
		return
	_face_timer = 1.0
	var faced := players_faced()
	var n := maxi(faced.size(), int(data.get("min_players", 1)))
	if n > facing_players:
		_face(n)
		for p in faced:
			World.say(p, "%s grows stronger to face you all." % display_name, World.C_WARN)
		stats_changed.emit()


func add_hate(src: Entity, amount: float) -> void:
	if src == null or src == self or dead or src.dead:
		return
	var was_calm := hate.is_empty()
	hate[src.entity_id] = float(hate.get(src.entity_id, 0.0)) + amount
	if state != State.COMBAT and state != State.FLEE:
		state = State.COMBAT
	if was_calm:
		animate("sfx:aggro")  # its challenge, as it comes for you
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
	if dead or data.get("inert", false):
		return  # a web hangs there: it doesn't move, notice anyone or fight back
	if data.get("named", false):
		_check_facing(delta)
	_think_timer -= delta
	var move := Vector3.ZERO
	var move_speed := speed

	if fear_left > 0.0:  # feared: runs from whoever scared it and doesn't fight
		var scary := World.get_object(feared_by) as Node3D
		auto_attack = false
		if scary != null:
			move = -_dir_to(scary.global_position)
			move_speed = speed * 0.7
	else:
		move = _think_state(delta)
		move_speed = _move_speed
	if root_left > 0.0 or stun_left > 0.0:
		move = Vector3.ZERO  # rooted: turns and swings, but can't walk (stunned: not even swings)
	if snare_left > 0.0:
		move_speed *= 0.5
	if swimming:
		move_speed *= SWIM_SLOW
	if move != Vector3.ZERO:
		face_toward(global_position + move)  # walking (a path around a rock, too) faces the way it goes; in reach, it faces its target
		velocity.x = move.x * move_speed
		velocity.z = move.z * move_speed
	else:
		velocity.x = 0.0
		velocity.z = 0.0
		if is_on_floor():
			return  # standing still on the ground: no need to sweep the collision (most mobs, most of the time)
	move_and_slide()


## What the mob does this frame in its current state; returns the step to take
## (and sets _move_speed).
func _think_state(delta: float) -> Vector3:
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

	_move_speed = move_speed
	return move


func _scan_for_aggro(delta: float) -> void:
	_scan_timer -= delta
	if _scan_timer > 0.0:
		return
	_scan_timer = 0.5
	for p in World.get_players():
		if p.dead or p.hidden or p.feigning or p.god_mode or World.con_of(p.level, level) == World.Con.GRAY:
			continue
		# aggressive mobs attack anyone close; others only those their faction hates
		var radius := aggro_radius if aggressive else (12.0 if World.mob_kos(p, faction) else 0.0)
		radius *= 1.0 + p.bonus("notice_pct") / 100.0  # a halfling is noticed later
		if radius > 0.0 and distance_to(p) <= radius:
			add_hate(p, 1.0)
			return


func _reset() -> void:
	if data.get("named", false) and facing_players != int(data.get("min_players", 1)):
		_face(int(data.get("min_players", 1)))  # back to its own size
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
