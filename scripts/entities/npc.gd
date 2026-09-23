class_name Npc
extends Entity
## A townsperson from data/npcs.json: stands at its post, can be hailed, and
## answers keywords. Townsfolk can't be attacked; what they say and the quests
## they run are rules in the World autoload.
##
## NPCs with a "guard" block also keep the peace: when a mob is chasing a
## player near their post they shout, run it down and fight it with the same
## melee rules as everyone else, then walk back to their post.

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


func setup(id: String, name_override := "") -> void:
	npc_id = id
	data = GameData.npcs[id]
	display_name = name_override if name_override != "" else str(data["name"])
	level = int(data.get("level", 10))
	faction = "town"
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
	_post = global_position
	_post_yaw = rotation.y


## Turns to face whoever is talking to it for a while, then back to its post.
func greet(who: Entity) -> void:
	face_toward(who.global_position)
	_face_timer = 12.0


func _physics_process(delta: float) -> void:
	apply_gravity(delta)
	var move := Vector3.ZERO
	if not dead and not guard.is_empty():
		move = _guard_think(delta)
	var speed := float(guard.get("speed", 6.5))
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
func _guard_think(delta: float) -> Vector3:
	if auto_attack:
		var t := valid_target_entity()
		if t == null or _flat(t.global_position, _post) > float(guard.get("leash", 35.0)):
			auto_attack = false
			target = null
			return Vector3.ZERO
		face_toward(t.global_position)
		return _dir_to(t.global_position) if distance_to(t) > World.melee_range() * 0.7 else Vector3.ZERO
	if _flat(global_position, _post) > 0.8:
		var dir := _dir_to(_post)
		if _flat(global_position, _post) < 1.5:
			rotation.y = _post_yaw
		return dir
	_scan_timer -= delta
	if _scan_timer <= 0.0:
		_scan_timer = SCAN_SECONDS
		_look_for_trouble()
	return Vector3.ZERO


## Engages the nearest mob within reach that is chasing or fighting a player.
func _look_for_trouble() -> void:
	var radius := float(guard.get("radius", 22.0))
	var best: Mob = null
	var victim: Player = null
	for m in World.get_mobs():
		if m.dead or distance_to(m) > radius or not (m.state in [Mob.State.COMBAT, Mob.State.FLEE]):
			continue
		var t := m.top_hated()
		if t is Player and (best == null or distance_to(m) < distance_to(best)):
			best = m
			victim = t
	if best == null:
		return
	target = best
	auto_attack = true
	sitting = false
	_face_timer = 0.0
	var shouts: Array = guard.get("shouts", [])
	if not shouts.is_empty():
		var line := str(shouts[randi() % shouts.size()]).format({"name": victim.display_name, "mob": best.display_name})
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
