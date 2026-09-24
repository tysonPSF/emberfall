class_name Player
extends Entity
## The locally controlled character: input, camera, inventory, progression.
## Input never changes game state directly; it calls World.request_*, which is
## where networking will slot in later.

signal inventory_changed
signal leveled_up
signal quests_changed

const RUN_SPEED := 7.0
const BACK_SPEED := 4.0
const TURN_SPEED := 2.6
const JUMP_VELOCITY := 7.5
const MOUSE_SENS := 0.004
const MAX_ZOOM := 18.0

var char_class := "warrior"
var deity := ""  # data/deities.json id, chosen at creation; "" for none
var xp := 0
var coin := 0
var inventory: Array = []
var equipment: Dictionary = {}
var quests: Dictionary = {}  # quest id -> {active, completions}
var trade_npc_id := -1  # npc entity id while a trade window is open
var trade_items: Array = []  # items offered in the open trade
var camp_left := 0.0  # seconds until a camp finishes; 0 when not camping
var service_npc_id := -1  # merchant or banker whose window is open
var service := ""  # "shop" or "bank" while service_npc_id is set
var bank_items: Array = []
var bank_coin := 0
var factions: Dictionary = {}  # faction id -> standing, once it moves off the default
var hostile_npcs: Dictionary = {}  # npc entity ids this player chose to fight
var attack_confirm_id := -1  # npc awaiting a second Q before attacking
var attack_confirm_at := 0
var body_color := Color.WHITE

var camera_pivot: Node3D
var spring_arm: SpringArm3D
var camera: Camera3D
var zoom := 6.0
var pitch := -0.3
var mouse_looking := false
var _saved_mouse_pos := Vector2.ZERO


func from_save(d: Dictionary) -> void:
	display_name = str(d.get("name", "Adventurer"))
	char_class = str(d.get("class", "warrior"))
	deity = str(d.get("deity", ""))
	level = int(d.get("level", 1))
	xp = int(d.get("xp", 0))
	coin = int(d.get("coin", 0))
	inventory = (d.get("inventory", []) as Array).duplicate()
	quests = (d.get("quests", {}) as Dictionary).duplicate(true)
	bank_items = (d.get("bank_items", []) as Array).duplicate()
	bank_coin = int(d.get("bank_coin", 0))
	factions = (d.get("factions", {}) as Dictionary).duplicate()
	for k: String in factions:
		factions[k] = int(factions[k])
	var cls: Dictionary = GameData.classes[char_class]
	spells = (d.get("spells", cls["spells"]) as Array).filter(func(id: String) -> bool: return GameData.spells.has(id))
	if d.has("equipment"):
		equipment = (d["equipment"] as Dictionary).duplicate()
	else:
		equipment = (cls.get("starting_items", {}) as Dictionary).duplicate()
	faction = "players"
	body_color = Color.html(cls["color"])
	hp = 1 << 30
	mana = 1 << 30
	recalc_stats()
	hp = clampi(int(d.get("hp", max_hp)), 1, max_hp)
	mana = clampi(int(d.get("mana", max_mana)), 0, max_mana)


func to_save() -> Dictionary:
	var p := global_position
	return {
		"name": display_name, "class": char_class, "deity": deity, "level": level, "xp": xp, "coin": coin,
		"inventory": inventory + trade_items, "equipment": equipment, "quests": quests, "spells": spells, "bank_items": bank_items, "bank_coin": bank_coin, "factions": factions, "hp": maxi(hp, 1), "mana": mana,
		"position": [p.x, p.y, p.z],
	}


func recalc_stats() -> void:
	var cls: Dictionary = GameData.classes[char_class]
	max_hp = int(cls["hp_base"]) + int(cls["hp_per_level"]) * (level - 1)
	max_mana = int(cls["mana_base"]) + int(cls["mana_per_level"]) * (level - 1)
	ac = int(cls["ac_base"]) + level
	var weapon_dmg := 2
	var weapon_model := ""
	attack_delay = 3.0
	attack_verb = ["hit", "hits"]
	for slot: String in equipment:
		var item: Dictionary = GameData.items.get(equipment[slot], {})
		ac += int(item.get("ac", 0))
		max_hp += int(item.get("hp", 0))
		max_mana += int(item.get("mana", 0))
		if slot == "primary":
			weapon_dmg = int(item.get("dmg", 2))
			weapon_model = str(item.get("model", ""))
			attack_delay = float(item.get("delay", 3.0))
			attack_verb = item.get("verb", ["hit", "hits"])
	var skill := float(cls["melee_skill"])
	dmg_min = 1 + level / 4
	dmg_max = maxi(dmg_min + 1, int((weapon_dmg * 2 + level) * skill))
	ac += buff_total("ac")
	max_hp += buff_total("hp")
	dmg_min += buff_total("dmg")
	dmg_max += buff_total("dmg")
	max_mana += int(max_mana * GameData.deity_bonus(deity, "mana_pct") / 100.0)
	dmg_min += int(GameData.deity_bonus(deity, "dmg"))
	dmg_max += int(GameData.deity_bonus(deity, "dmg"))
	hp_regen = int(cls["hp_regen"]) + level / 4 + int(GameData.deity_bonus(deity, "hp_regen"))
	mana_regen = int(cls["mana_regen"])
	hp = mini(hp, max_hp)
	mana = mini(mana, max_mana)
	if visual is CharacterModel:
		(visual as CharacterModel).set_weapon(weapon_model)
		look["weapon"] = weapon_model
	stats_changed.emit()


func xp_to_next() -> int:
	return int(float(World.cfg("xp_per_level_sq", 100)) * level * level)


func add_xp(amount: int) -> void:
	var max_level := int(World.cfg("max_level", 10))
	if level >= max_level:
		return
	xp += amount
	World.say(self, "You gain experience!!", World.C_XP)
	while level < max_level and xp >= xp_to_next():
		xp -= xp_to_next()
		level += 1
		recalc_stats()
		World.say(self, "You have gained a level! Welcome to level %d!" % level, World.C_XP)
		for entry: Dictionary in World.class_spells(char_class):
			if entry["level"] == level:
				World.say(self, "Your guildmaster in Emberhold can now teach you %s." % GameData.spells[entry["spell"]]["name"], World.C_XP)
		leveled_up.emit()
	stats_changed.emit()


func on_death() -> void:
	sitting = false
	target = null
	visual.visible = false
	nameplate.visible = false


func respawn() -> void:
	dead = false
	hp = max_hp
	mana = max_mana
	global_position = World.zone.bind_point + Vector3.UP
	velocity = Vector3.ZERO
	visual.visible = zoom > 0.6
	nameplate.visible = true
	World.say(self, "You wake up at your bind point.", World.C_SYSTEM)
	stats_changed.emit()


# --- scene setup ------------------------------------------------------------

func _ready() -> void:
	var weapon: String = GameData.items.get(equipment.get("primary", ""), {}).get("model", "")
	build_body("humanoid", body_color, 1.0, GameData.classes[char_class].get("model", ""), weapon)
	nameplate.text = display_name
	nameplate.modulate = Color(0.7, 0.85, 1.0)
	World.local_player = self

	camera_pivot = Node3D.new()
	camera_pivot.position.y = 1.6
	add_child(camera_pivot)
	spring_arm = SpringArm3D.new()
	spring_arm.collision_mask = Layers.WORLD
	spring_arm.margin = 0.3
	var probe := SphereShape3D.new()
	probe.radius = 0.25
	spring_arm.shape = probe
	camera_pivot.add_child(spring_arm)
	camera = Camera3D.new()
	camera.fov = 70.0
	camera.far = 800.0
	spring_arm.add_child(camera)
	camera.make_current()


func _process(delta: float) -> void:
	spring_arm.spring_length = lerpf(spring_arm.spring_length, zoom, minf(1.0, delta * 10.0))
	camera_pivot.rotation.x = pitch
	visual.visible = not dead and zoom > 0.6


# --- input ------------------------------------------------------------------

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		match mb.button_index:
			MOUSE_BUTTON_RIGHT:
				_set_mouse_look(mb.pressed)
			MOUSE_BUTTON_WHEEL_UP:
				if mb.pressed:
					zoom = maxf(0.0, zoom - 1.0)
			MOUSE_BUTTON_WHEEL_DOWN:
				if mb.pressed:
					zoom = minf(MAX_ZOOM, zoom + 1.0)
			MOUSE_BUTTON_LEFT:
				if mb.pressed:
					_click_select(mb.position, mb.double_click)
		return
	if event is InputEventMouseMotion and mouse_looking:
		var mm := event as InputEventMouseMotion
		rotate_y(-mm.relative.x * MOUSE_SENS)
		pitch = clampf(pitch - mm.relative.y * MOUSE_SENS, -1.3, 0.9)
		return

	if event.is_action_pressed("auto_attack"):
		World.request_toggle_attack(entity_id)
	elif event.is_action_pressed("target_next"):
		_cycle_target()
	elif event.is_action_pressed("target_self"):
		World.request_set_target(entity_id, entity_id)
	elif event.is_action_pressed("consider"):
		World.request_consider(entity_id)
	elif event.is_action_pressed("sit"):
		World.request_sit(entity_id, not sitting)
	elif event.is_action_pressed("hail"):
		World.request_hail(entity_id)
	elif event.is_action_pressed("trade"):
		World.request_interact(entity_id)
	elif event.is_action_pressed("loot"):
		if is_instance_valid(target) and target is Corpse:
			World.request_loot_open(entity_id, (target as Corpse).object_id)
	elif event.is_action_pressed("cancel"):
		if not cast.is_empty():
			World.request_interrupt(entity_id)
		else:
			World.request_set_target(entity_id, -1)
	else:
		for i in 8:
			if event.is_action_pressed("hotbar_%d" % (i + 1)) and i < spells.size():
				World.request_cast(entity_id, spells[i])
				break


func _set_mouse_look(on: bool) -> void:
	mouse_looking = on
	if on:
		_saved_mouse_pos = get_viewport().get_mouse_position()
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	else:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		Input.warp_mouse(_saved_mouse_pos)


func _click_select(screen_pos: Vector2, double_click: bool) -> void:
	var from := camera.project_ray_origin(screen_pos)
	var to := from + camera.project_ray_normal(screen_pos) * 250.0
	var query := PhysicsRayQueryParameters3D.create(from, to, Layers.WORLD | Layers.ENTITIES | Layers.CORPSES)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if hit.is_empty():
		return
	var col: Object = hit["collider"]
	if col is Entity:
		World.request_set_target(entity_id, (col as Entity).entity_id)
		if double_click and col is Npc:
			World.request_hail(entity_id)
	elif col is Corpse:
		World.request_set_target(entity_id, (col as Corpse).object_id)
		if double_click:
			World.request_loot_open(entity_id, (col as Corpse).object_id)


func _cycle_target() -> void:
	var candidates: Array[Mob] = []
	for m in World.get_mobs():
		if not m.dead and distance_to(m) < 45.0:
			candidates.append(m)
	if candidates.is_empty():
		return
	candidates.sort_custom(func(a: Mob, b: Mob) -> bool: return distance_to(a) < distance_to(b))
	var idx := candidates.find(target) + 1 if target is Mob else 0
	World.request_set_target(entity_id, candidates[idx % candidates.size()].entity_id)


func _physics_process(delta: float) -> void:
	apply_gravity(delta)
	if dead:
		velocity.x = 0.0
		velocity.z = 0.0
		move_and_slide()
		return
	var fwd := Input.get_axis("move_back", "move_forward")
	var side := Input.get_axis("turn_left", "turn_right")
	var strafe := 0.0
	if mouse_looking:
		strafe = side
	else:
		rotate_y(-side * TURN_SPEED * delta)
	var dir := -transform.basis.z * fwd + transform.basis.x * strafe
	dir.y = 0.0
	if dir.length() > 1.0:
		dir = dir.normalized()
	var spd := BACK_SPEED if fwd < 0.0 else RUN_SPEED * (1.0 + GameData.deity_bonus(deity, "run_speed_pct") / 100.0)
	if dir != Vector3.ZERO and sitting:
		World.request_sit(entity_id, false)
	velocity.x = dir.x * spd
	velocity.z = dir.z * spd
	if is_on_floor() and Input.is_action_just_pressed("jump"):
		velocity.y = JUMP_VELOCITY
	move_and_slide()
	if global_position.y < -60.0:
		global_position = World.zone.bind_point + Vector3.UP
		velocity = Vector3.ZERO
