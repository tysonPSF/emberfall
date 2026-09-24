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
const AIM_HEIGHT := 2.6  # metres above your feet the reticle rides, clearing both hat and nameplate
const AIM_CEILING := 0.2  # and never higher up the screen than this fraction of it

## Stats gear can carry besides ac/hp/mana and weapon damage.
const ATTRIBUTES: Array[String] = ["str", "sta", "agi", "wis", "int", "haste", "hp_regen", "mana_regen"]

var char_class := "warrior"
var attributes: Dictionary = {}  # totals from gear, for the character sheet
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
var is_local := true  # false for other people's players (a server's remote players, a client's mirrors)
var _asked_at: Dictionary = {}  # request name -> msec before which it isn't asked again
var stamina := 0.0  # drains while sprinting; World owns the rules
var max_stamina := 0
var sprinting := false
var stamina_idle := 0.0  # seconds left before stamina starts coming back

var camera_pivot: Node3D
var spring_arm: SpringArm3D
var camera: Camera3D
var zoom := 6.0
var pitch := -0.3
var mouse_looking := false
var _cursor_hud: Node = null  # cached HUD, asked each frame whether a window needs the cursor
var _autotest := "--autotest" in OS.get_cmdline_user_args()


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
	stamina = float(max_stamina)  # you arrive rested; it is not worth saving


## Asks that repeat every frame until the rules answer (sprint, stand up) go
## out at most a few times a second: on a server the answer takes a round
## trip, and a refusal (too winded to sprint) would otherwise be re-asked
## every single frame.
func _may_ask(what: String) -> bool:
	var now := Time.get_ticks_msec()
	if now < int(_asked_at.get(what, 0)):
		return false
	_asked_at[what] = now + 250
	return true


## Client: someone else's player, drawn as the server describes it.
func setup_remote(info: Dictionary) -> void:
	is_local = false
	entity_id = int(info["id"])
	display_name = str(info["name"])
	level = int(info["level"])
	char_class = str(info.get("class", "warrior"))
	faction = "players"
	max_hp = int(info["max_hp"])
	hp = int(info["hp"])
	look = info["look"]
	body_color = Color.html(GameData.classes[char_class]["color"])


## Client: our own player's state as the server holds it.
func apply_self(d: Dictionary) -> void:
	var bags_before := [inventory, equipment, coin, bank_items, bank_coin, trade_items]
	var quests_before := quests
	var level_before := level
	for key: String in ["level", "xp", "coin", "hp", "max_hp", "mana", "max_mana", "ac", "dmg_min", "dmg_max",
			"attack_delay", "attack_verb", "attributes", "inventory", "equipment", "spells", "quests", "factions",
			"bank_items", "bank_coin", "cast", "cooldowns", "buffs", "sitting", "auto_attack", "trade_npc_id",
			"trade_items", "service_npc_id", "service", "camp_left", "root_left", "stamina", "max_stamina", "sprinting"]:
		set(key, d[key])
	if bool(d["dead"]) != dead:
		dead = bool(d["dead"])
		if nameplate != null:
			nameplate.visible = not dead
	var t: Node3D = World.get_object(int(d["target"])) if int(d["target"]) >= 0 else null
	if t != target:
		target = t
	var lk: Dictionary = d["look"]
	if visual is CharacterModel and (lk.get("weapon") != look.get("weapon") or lk.get("offhand") != look.get("offhand")):
		(visual as CharacterModel).set_weapon(str(lk.get("weapon", "")))
		(visual as CharacterModel).set_offhand(str(lk.get("offhand", "")))
	look = lk
	if bags_before != [inventory, equipment, coin, bank_items, bank_coin, trade_items]:
		inventory_changed.emit()
	if quests_before != quests:
		quests_changed.emit()
	if level > level_before:
		leveled_up.emit()
	stats_changed.emit()


func to_save() -> Dictionary:
	var p := global_position
	return {
		"name": display_name, "class": char_class, "deity": deity, "level": level, "xp": xp, "coin": coin,
		"inventory": inventory + trade_items, "equipment": equipment, "quests": quests, "spells": spells, "bank_items": bank_items, "bank_coin": bank_coin, "factions": factions, "hp": maxi(hp, 1), "mana": mana,
		"position": [p.x, p.y, p.z],
	}


## Bag slots in use: one per item, except stackable items ("stack": n), which
## share a slot per n of the same kind.
func slots_used() -> int:
	var used := 0
	var counts := {}
	for item_id: String in inventory:
		var stack := int(GameData.item(item_id).get("stack", 1))
		if stack <= 1:
			used += 1
		else:
			counts[item_id] = [int(counts.get(item_id, [0])[0]) + 1, stack]
	for id: String in counts:
		used += ceili(float(counts[id][0]) / counts[id][1])
	return used


## Whether one more of this item fits in the bags.
func room_for(item_id: String) -> bool:
	var stack := int(GameData.item(item_id).get("stack", 1))
	if stack > 1 and inventory.count(item_id) % stack != 0:
		return true  # tops up a stack
	return slots_used() < int(World.cfg("inventory_slots", 24))


## Gear below its recommended level works at reduced strength, as in EQ:
## level / rec_level, but never less than half.
func item_effectiveness(item: Dictionary) -> float:
	var rec := int(item.get("rec_level", 0))
	return 1.0 if rec <= level else clampf(float(level) / rec, 0.5, 1.0)


func recalc_stats() -> void:
	var cls: Dictionary = GameData.classes[char_class]
	max_hp = int(cls["hp_base"]) + int(cls["hp_per_level"]) * (level - 1)
	max_mana = int(cls["mana_base"]) + int(cls["mana_per_level"]) * (level - 1)
	max_stamina = int(World.cfg("stamina_base", 100)) + int(World.cfg("stamina_per_level", 4)) * (level - 1)
	ac = int(cls["ac_base"]) + level
	var weapon_dmg := 2
	var weapon_model := ""
	var offhand_model := ""
	var attr := {}  # str, sta, agi, wis, int, haste, hp_regen, mana_regen from gear
	attack_delay = 3.0
	attack_verb = ["hit", "hits"]
	for slot: String in equipment:
		var item: Dictionary = GameData.item(equipment[slot])
		var eff := item_effectiveness(item)
		ac += roundi(int(item.get("ac", 0)) * eff)
		max_hp += roundi(int(item.get("hp", 0)) * eff)
		max_mana += roundi(int(item.get("mana", 0)) * eff)
		for stat: String in ATTRIBUTES:
			attr[stat] = int(attr.get(stat, 0)) + roundi(int(item.get(stat, 0)) * eff)
		if slot == "secondary":
			offhand_model = str(item.get("model", ""))
		if slot == "primary":
			weapon_dmg = maxi(1, roundi(int(item.get("dmg", 2)) * eff))
			weapon_model = str(item.get("model", ""))
			attack_delay = float(item.get("delay", 3.0))
			attack_verb = item.get("verb", ["hit", "hits"])
	var skill := float(cls["melee_skill"])
	dmg_min = 1 + level / 4 + int(attr.get("str", 0)) / 10
	dmg_max = maxi(dmg_min + 1, int((weapon_dmg * 2 + level) * skill) + int(attr.get("str", 0)) / 5)
	max_hp += int(attr.get("sta", 0))
	ac += int(attr.get("agi", 0)) / 2
	var caster_stat := str(cls.get("caster_stat", ""))
	if max_mana > 0 and caster_stat != "":
		max_mana += int(attr.get(caster_stat, 0))
	attack_delay /= 1.0 + minf(int(attr.get("haste", 0)), 40) / 100.0
	attributes = attr
	ac += buff_total("ac")
	max_hp += buff_total("hp")
	dmg_min += buff_total("dmg")
	dmg_max += buff_total("dmg")
	max_mana += int(max_mana * GameData.deity_bonus(deity, "mana_pct") / 100.0)
	dmg_min += int(GameData.deity_bonus(deity, "dmg"))
	dmg_max += int(GameData.deity_bonus(deity, "dmg"))
	hp_regen = int(cls["hp_regen"]) + level / 4 + int(GameData.deity_bonus(deity, "hp_regen")) + int(attr.get("hp_regen", 0))
	mana_regen = int(cls["mana_regen"]) + int(attr.get("mana_regen", 0))
	# Every lever that could lengthen a run lands in max_stamina, so nothing else
	# has to change to grant more. STA is the gear route: it is already the
	# endurance stat, so a stamina-heavy set both toughens you and lets you run
	# further, rather than gear carrying a second stat that means "wind".
	max_stamina += int(attr.get("sta", 0))
	max_stamina += buff_total("stamina")
	max_stamina += int(max_stamina * GameData.deity_bonus(deity, "stamina_pct") / 100.0)
	hp = mini(hp, max_hp)
	mana = mini(mana, max_mana)
	if visual is CharacterModel and (look.get("weapon") != weapon_model or look.get("offhand") != offhand_model):
		look["weapon"] = weapon_model
		look["offhand"] = offhand_model
		Net.broadcast_look(self)
	stamina = minf(stamina, float(max_stamina))
	if visual is CharacterModel:
		(visual as CharacterModel).set_weapon(weapon_model)
		(visual as CharacterModel).set_offhand(offhand_model)
		look["weapon"] = weapon_model
		look["offhand"] = offhand_model
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
	sprinting = false
	target = null
	visual.visible = false
	nameplate.visible = false


func respawn() -> void:
	dead = false
	hp = max_hp
	mana = max_mana
	stamina = float(max_stamina)
	global_position = World.zone_of(self).bind_point + Vector3.UP
	velocity = Vector3.ZERO
	Net.teleport(self, global_position)
	visual.visible = zoom > 0.6 or not is_local
	nameplate.visible = true
	World.say(self, "You wake up at your bind point.", World.C_SYSTEM)
	stats_changed.emit()


# --- scene setup ------------------------------------------------------------

func _ready() -> void:
	var mirrored := look.duplicate()
	var weapon: String = GameData.item(equipment.get("primary", "")).get("model", "")
	if not mirrored.is_empty():
		weapon = str(mirrored.get("weapon", ""))
	build_body("humanoid", body_color, 1.0, GameData.classes[char_class].get("model", ""), weapon)
	if not mirrored.is_empty() and visual is CharacterModel:
		look = mirrored
		(visual as CharacterModel).set_offhand(str(look.get("offhand", "")))
	nameplate.text = display_name
	nameplate.modulate = Color(0.7, 0.85, 1.0)
	if not is_local:
		return
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
	if not is_local:
		return
	_update_mouse_look()
	spring_arm.spring_length = lerpf(spring_arm.spring_length, zoom, minf(1.0, delta * 10.0))
	camera_pivot.rotation.x = pitch
	visual.visible = not dead and zoom > 0.6


# --- input ------------------------------------------------------------------

func _unhandled_input(event: InputEvent) -> void:
	if not is_local:
		return
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		match mb.button_index:
			MOUSE_BUTTON_WHEEL_UP:
				if mb.pressed:
					zoom = maxf(0.0, zoom - 1.0)
			MOUSE_BUTTON_WHEEL_DOWN:
				if mb.pressed:
					zoom = minf(MAX_ZOOM, zoom + 1.0)
			MOUSE_BUTTON_RIGHT:
				if mb.pressed and mouse_looking:
					_crosshair_target()
			MOUSE_BUTTON_LEFT:
				if mb.pressed:
					if mouse_looking:
						_crosshair_attack()
					else:
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
	elif event.is_action_pressed("target_interact"):
		_cycle_interact()
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


## Mouselook is the normal state: the mouse turns you and the cursor stays hidden.
## The cursor comes back while a HUD window is open, while Alt is held, and when
## you are dead, so the menus and hotbar stay clickable.
##
## The autotest keeps the same logical state - crosshair, strafing, the lot - but
## never takes the real cursor, so a test run cannot hold the mouse hostage while
## someone is working.
func _update_mouse_look() -> void:
	var want := Controls.mouse_look and not dead and not Input.is_action_pressed("free_cursor") and not _hud_wants_cursor()
	if want == mouse_looking:
		return
	mouse_looking = want
	if _autotest:
		return
	if want:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	else:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		Input.warp_mouse(get_viewport().get_visible_rect().size * 0.5)


func _hud_wants_cursor() -> bool:
	if not is_instance_valid(_cursor_hud):
		_cursor_hud = get_tree().get_first_node_in_group("hud")
	return _cursor_hud != null and _cursor_hud.wants_cursor()


## Leaving the world (camp, quit) must not strand a hidden cursor. Entity's own
## _exit_tree unregisters us from World, so it has to run too.
func _exit_tree() -> void:
	super()
	if not is_local:
		return
	mouse_looking = false
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE


## Right click in mouselook: pick up whatever the crosshair is on as your target.
## Aiming and committing are separate, so you can size something up with C before
## you swing at it.
func _crosshair_target() -> void:
	var col := _pick(aim_point())
	if col is Entity:
		World.request_set_target(entity_id, (col as Entity).entity_id)
	elif col is Corpse:
		World.request_set_target(entity_id, (col as Corpse).object_id)


## Left click in mouselook: start swinging at the target you already picked.
## Clicking never turns auto attack back off - that stays Q's job - so hammering
## the button mid-fight cannot accidentally sheathe you.
func _crosshair_attack() -> void:
	if not auto_attack:
		World.request_toggle_attack(entity_id)


## The screen point the reticle sits on and every click raycasts through. In
## third person your own head is dead centre, so the reticle rides just above
## it, tracking the head rather than a fixed offset - that keeps the clearance
## right at every zoom and pitch. Zoomed into first person there is no body in
## the way and it drops back to the middle of the screen.
func aim_point() -> Vector2:
	var vp := get_viewport().get_visible_rect().size
	var centre := vp * 0.5
	if camera == null or not visual.visible:
		return centre
	var head := global_position + Vector3.UP * AIM_HEIGHT
	if camera.is_position_behind(head):
		return centre
	return Vector2(centre.x, clampf(camera.unproject_position(head).y, vp.y * AIM_CEILING, centre.y))


## Raycast into the scene from a screen point. Excludes the player's own body,
## which otherwise sits under the crosshair in third person.
func _pick(screen_pos: Vector2) -> Object:
	var from := camera.project_ray_origin(screen_pos)
	var to := from + camera.project_ray_normal(screen_pos) * 250.0
	var query := PhysicsRayQueryParameters3D.create(from, to, Layers.WORLD | Layers.ENTITIES | Layers.CORPSES)
	query.exclude = [get_rid()]
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	return hit["collider"] if not hit.is_empty() else null


func _click_select(screen_pos: Vector2, double_click: bool) -> void:
	var col := _pick(screen_pos)
	if col == null:
		return
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


## Cycles what you interact with rather than fight: townsfolk and corpses. Tab
## only ever walks the living mobs, so without this someone on the keyboard can
## kill a gnoll and then neither loot it nor hand the fangs in.
func _cycle_interact() -> void:
	var candidates: Array[Node3D] = []
	for obj: Variant in World.objects.values():
		if not is_instance_valid(obj) or obj == self:
			continue
		var wanted := obj is Corpse or (obj is Npc and not (obj as Npc).dead)
		if wanted and global_position.distance_to((obj as Node3D).global_position) < 45.0:
			candidates.append(obj)
	if candidates.is_empty():
		World.say(self, "There is nobody to talk to and nothing to loot nearby.", World.C_WARN)
		return
	candidates.sort_custom(func(a: Node3D, b: Node3D) -> bool:
		return global_position.distance_to(a.global_position) < global_position.distance_to(b.global_position))
	var idx := candidates.find(target) + 1 if target != null else 0
	var pick := candidates[idx % candidates.size()]
	var id: int = (pick as Corpse).object_id if pick is Corpse else (pick as Entity).entity_id
	World.request_set_target(entity_id, id)


func _physics_process(delta: float) -> void:
	if not is_local:
		if not Net.is_authority():
			puppet(delta)
		return  # a server's remote players move when their client says so
	apply_gravity(delta)
	if dead:
		velocity.x = 0.0
		velocity.z = 0.0
		move_and_slide()
		return
	var fwd := Input.get_axis("move_back", "move_forward")
	var strafe := Input.get_axis("move_left", "move_right")
	var turn := Input.get_axis("turn_left", "turn_right")  # arrow keys, for turning without the mouse
	if not Controls.mouse_look:
		turn = clampf(turn + strafe, -1.0, 1.0)  # keyboard scheme: A/D turn, as they did before mouselook
		strafe = 0.0
	if turn != 0.0:
		rotate_y(-turn * TURN_SPEED * delta)
	var dir := -transform.basis.z * fwd + transform.basis.x * strafe
	dir.y = 0.0
	if dir.length() > 1.0:
		dir = dir.normalized()
	var spd := BACK_SPEED if fwd < 0.0 else RUN_SPEED * (1.0 + GameData.deity_bonus(deity, "run_speed_pct") / 100.0)
	# Sprinting is forward-only, and asked for every frame rather than toggled:
	# World decides whether it is allowed and ends it when the wind runs out.
	var want_sprint := Input.is_action_pressed("sprint") and fwd > 0.0
	if want_sprint != sprinting and _may_ask("sprint"):
		World.request_sprint(entity_id, want_sprint)
	if sprinting:
		spd *= float(World.cfg("sprint_speed_mult", 1.55))
	if dir != Vector3.ZERO and sitting and _may_ask("stand"):
		World.request_sit(entity_id, false)
	velocity.x = dir.x * spd
	velocity.z = dir.z * spd
	if is_on_floor() and Input.is_action_just_pressed("jump"):
		velocity.y = JUMP_VELOCITY
	move_and_slide()
	if global_position.y < -60.0:
		global_position = World.zone_of(self).bind_point + Vector3.UP
		velocity = Vector3.ZERO
