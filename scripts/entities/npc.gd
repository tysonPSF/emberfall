class_name Npc
extends Entity
## A townsperson from data/npcs.json: stands at its post, can be hailed, and
## answers keywords. What they say, the quests they run, and whether a player
## may attack them (only after choosing to, at a faction cost) are rules in the
## World autoload.
##
## Anyone attacked fights back, chasing a little way from their post. NPCs with
## a "guard" block also keep the peace: they run down mobs chasing players,
## players who attack townsfolk, and players their faction wants dead (KOS),
## using the same melee rules as everyone else, then walk back to their post.
##
## A guard given a patrol (waypoints from the zone file) walks it back and
## forth at "walk_speed" instead of standing at a post, pausing at each end
## and stopping to talk when hailed. Guard options: "assist_standing" (only
## help players at least this well regarded by the guard's faction) and
## "hunt_radius" (attack any monster that comes this close).

const NAME_COLOR := Color(0.55, 0.85, 1.0)
const SCAN_SECONDS := 0.5
const RESPAWN_SECONDS := 120.0

var npc_id := ""
var data: Dictionary = {}
var guard: Dictionary = {}  # radius, leash, speed, shouts; empty for plain townsfolk
var _face_timer := 0.0
var _post := Vector3.ZERO
var _post_yaw := 0.0
var _scan_timer := 0.0
var patrol: Array[Vector3] = []  # waypoints walked end to end and back; empty for a post
var _leg := 1  # waypoint being walked to
var _leg_step := 1
var _pause := 0.0
var _anchor := Vector3.ZERO  # where the current fight began; the leash is measured from here


func setup(id: String, name_override := "") -> void:
	npc_id = id
	data = GameData.npcs[id]
	display_name = name_override if name_override != "" else str(data["name"])
	level = int(data.get("level", 10))
	faction = str(data.get("faction", "town"))
	guard = data.get("guard", {})
	var combat: Dictionary = data.get("combat", {})
	max_hp = int(combat.get("hp", 1000))
	hp = max_hp
	hp_regen = int(combat.get("hp_regen", 10))
	ac = int(combat.get("ac", 20))
	var dmg: Array = combat.get("dmg", [2, 6])
	dmg_min = int(dmg[0])
	dmg_max = int(dmg[1])
	attack_delay = float(combat.get("delay", 2.5))
	attack_verb = combat.get("verb", ["slash", "slashes"])


func _ready() -> void:
	build_body("humanoid", Color.WHITE, 1.0, str(data.get("model", "")), str(data.get("weapon", "")))
	nameplate.text = display_name
	nameplate.modulate = NAME_COLOR
	if data.has("title"):  # EQ-style second line: <Warrior Guildmaster>
		var title := Label3D.new()
		title.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		title.fixed_size = true
		title.pixel_size = nameplate.pixel_size
		title.font_size = 24
		title.outline_size = 6
		title.text = "<%s>" % data["title"]
		title.modulate = Color(0.78, 0.82, 0.9)
		title.offset = Vector2(0, -30)  # screen pixels below the name, at any distance
		title.visibility_range_end = nameplate.visibility_range_end
		nameplate.add_child(title)
	_post = global_position
	_post_yaw = rotation.y


## Turns to face whoever is talking to it for a while, then back to its post.
func greet(who: Entity) -> void:
	face_toward(who.global_position)
	_face_timer = 12.0


func _physics_process(delta: float) -> void:
	if not Net.is_authority():
		puppet(delta)
		return
	apply_gravity(delta)
	var move := Vector3.ZERO
	if not dead:
		move = _think(delta)
	var speed := float(guard.get("speed", 5.5))
	if not patrol.is_empty() and not auto_attack:
		speed = float(guard.get("walk_speed", 2.0))
	velocity.x = move.x * speed
	velocity.z = move.z * speed
	move_and_slide()
	if move != Vector3.ZERO and not auto_attack:
		face_toward(global_position + move)
	if _face_timer > 0.0 and not auto_attack:
		_face_timer -= delta
		if _face_timer <= 0.0:
			rotation.y = _post_yaw


## Returns the direction to walk this frame (zero to stand still).
func _think(delta: float) -> Vector3:
	if auto_attack:
		var t := valid_target_entity()
		if t == null or _flat(t.global_position, _anchor) > float(guard.get("leash", 20.0)):
			auto_attack = false
			target = null
			return Vector3.ZERO
		face_toward(t.global_position)
		return _dir_to(t.global_position) if distance_to(t) > World.melee_range() * 0.7 else Vector3.ZERO
	_scan_timer -= delta
	if not patrol.is_empty():
		if _scan_timer <= 0.0:
			_scan_timer = SCAN_SECONDS
			_look_for_trouble()
		return _walk_patrol(delta)
	if _flat(global_position, _post) > 0.8:
		var dir := _dir_to(_post)
		if _flat(global_position, _post) < 1.5:
			rotation.y = _post_yaw
		return dir
	if _scan_timer <= 0.0 and not guard.is_empty():
		_scan_timer = SCAN_SECONDS
		_look_for_trouble()
	return Vector3.ZERO


## Next step along the patrol: on to the next waypoint, turning back at either
## end after a pause, and standing still while talking to someone.
func _walk_patrol(delta: float) -> Vector3:
	if _face_timer > 0.0 or patrol.size() < 2:
		return Vector3.ZERO
	if _pause > 0.0:
		_pause -= delta
		return Vector3.ZERO
	var goal := patrol[_leg]
	if _flat(global_position, goal) < 1.0:
		if _leg + _leg_step < 0 or _leg + _leg_step >= patrol.size():
			_leg_step = -_leg_step
			_pause = float(guard.get("patrol_pause", 5.0))
		_leg += _leg_step
		return Vector3.ZERO
	return _dir_to(goal)


## Hit by someone: fight back (and a townsperson calls the guards).
func add_hate(src: Entity, _amount: float) -> void:
	if dead or src == null or src.dead or (auto_attack and valid_target_entity() != null):
		return
	if src is Player:
		(src as Player).hostile_npcs[entity_id] = true
	fight(src)
	World.call_guards(self, src)


## Turns on someone: targets and swings at them until they fall, flee past the
## leash, or it's knocked out.
func fight(who: Entity, shout := false) -> void:
	_engage(who)
	if shout and who is Player:
		var lines: Array = guard.get("shouts_player", ["Stop right there, {name}!"])
		World.shout(self, "%s shouts, '%s'" % [display_name, str(lines[randi() % lines.size()]).format({"name": who.display_name})])


func _engage(who: Entity) -> void:
	target = who
	auto_attack = true
	sitting = false
	_face_timer = 0.0
	_anchor = global_position if not patrol.is_empty() else _post


## Engages the nearest mob within reach that is chasing or fighting a player
## the guard is willing to help; failing that, a player to arrest; failing
## that, any monster inside the hunt radius.
func _look_for_trouble() -> void:
	var radius := float(guard.get("radius", 22.0))
	var best: Mob = null
	var victim: Player = null
	for m in World.get_mobs():
		if m.dead or distance_to(m) > radius or not (m.state in [Mob.State.COMBAT, Mob.State.FLEE]):
			continue
		var t := m.top_hated()
		if t is Player and _will_assist(t as Player) and (best == null or distance_to(m) < distance_to(best)):
			best = m
			victim = t
	if best != null:
		_engage(best)
		_shout("shouts", victim.display_name, best.display_name)
		return
	for p in World.get_players():  # players this faction wants dead, or who attacked townsfolk
		if p.dead or distance_to(p) > radius:
			continue
		if World.npc_kos(p, faction) or not p.hostile_npcs.is_empty():
			fight(p, true)
			return
	var hunt := float(guard.get("hunt_radius", 0.0))
	for m in World.get_mobs():
		if not m.dead and distance_to(m) <= hunt and (best == null or distance_to(m) < distance_to(best)):
			best = m
	if best != null:
		_engage(best)
		_shout("hunt_shouts", "", best.display_name)


func _will_assist(p: Player) -> bool:
	return not guard.has("assist_standing") or World.standing(p, faction) >= int(guard["assist_standing"])


func _shout(key: String, who: String, mob: String) -> void:
	var lines: Array = guard.get(key, [])
	if not lines.is_empty():
		var line := str(lines[randi() % lines.size()]).format({"name": who, "mob": mob})
		World.shout(self, "%s shouts, '%s'" % [display_name, line])


## Called by World.kill: falls, then returns to its post a while later.
func on_killed() -> void:
	target = null
	if visual is CharacterModel:
		(visual as CharacterModel).pose_dead()
	get_tree().create_timer(RESPAWN_SECONDS).timeout.connect(_return_to_post)


func _return_to_post() -> void:
	dead = false
	hp = max_hp
	global_position = _post
	rotation.y = _post_yaw
	_leg = 1
	_leg_step = 1
	visual.queue_free()
	visual = make_visual(look)
	add_child(visual)
	stats_changed.emit()


func _dir_to(pos: Vector3) -> Vector3:
	var d := pos - global_position
	d.y = 0.0
	return d.normalized() if d.length_squared() > 0.0001 else Vector3.ZERO


static func _flat(a: Vector3, b: Vector3) -> float:
	return Vector2(a.x, a.z).distance_to(Vector2(b.x, b.z))
