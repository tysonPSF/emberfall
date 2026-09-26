class_name Player
extends Entity
## The locally controlled character: input, camera, inventory, progression.
## Input never changes game state directly; it calls World.request_*, which is
## where networking will slot in later.

signal inventory_changed
signal leveled_up
signal quests_changed

const RUN_SPEED := 7.0
const SNEAK_SPEED := 0.5  # a sneaking rogue moves at half speed
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
var off_dmg_min := 0  # the off-hand weapon (Dual Wield); off_delay 0 = none there
var off_dmg_max := 0
var off_delay := 0.0
var off_verb: Array = ["hit", "hits"]
var off_swing_timer := 0.0
var _load_factor := 1.0  # encumbrance_speed(), refreshed a few times a second for movement
var _load_timer := 0.0
var attributes: Dictionary = {}  # totals from gear, for the character sheet
var deity := ""  # data/deities.json id, chosen at creation; "" for none
var xp := 0
var coin := 0
var pack := Pack.new()  # 8 general slots and the bags in them
var cursor: Dictionary = {}  # the entry picked up and being moved, EQ-style; {} when empty
var equipment: Dictionary = {}
var quests: Dictionary = {}  # quest id -> {active, completions}
var trade_npc_id := -1  # npc entity id while a trade window is open
var trade_items: Array = []  # entries offered in the open trade
var camp_left := 0.0  # seconds until a camp finishes; 0 when not camping
var service_npc_id := -1  # merchant or banker whose window is open
var service := ""  # "shop" or "bank" while service_npc_id is set
var bank: Array = []  # BANK_SLOTS entries ({} when empty); bags keep their contents
var bank_coin := 0
var factions: Dictionary = {}  # faction id -> standing, once it moves off the default
var hostile_npcs: Dictionary = {}  # npc entity ids this player chose to fight
var attack_confirm_id := -1  # npc awaiting a second Q before attacking
var attack_confirm_at := 0
var body_color := Color.WHITE
var is_local := true  # false for other people's players (a server's remote players, a client's mirrors)
var skills: Dictionary = {}  # skill id -> value; see data/skills.json
var group_id := 0  # server: the World.groups entry this player is in; 0 = none
var group: Array = []  # [{id, name, level, class, hp, max_hp, mana, max_mana, leader, zone}] for the group window
var follow_target: Node3D = null  # /follow: walk after this entity until you move yourself
var _asked_at: Dictionary = {}  # request name -> msec before which it isn't asked again
var stamina := 0.0  # drains while sprinting; World owns the rules
var max_stamina := 0
var sprinting := false
var threatened := false  # a monster has you on its hate list (the combat music follows this)
var stamina_idle := 0.0  # seconds left before stamina starts coming back

var camera_pivot: Node3D
var spring_arm: SpringArm3D
var camera: Camera3D
var zoom := 6.0
var pitch := -0.3
var mouse_looking := false
var _cursor_hud: Node = null  # cached HUD, asked each frame whether a window needs the cursor
var _autotest := "--autotest" in OS.get_cmdline_user_args() or Array(OS.get_cmdline_user_args()).any(func(a: String) -> bool: return a.begins_with("--nettest="))


func from_save(d: Dictionary) -> void:
	display_name = str(d.get("name", "Adventurer"))
	char_class = str(d.get("class", "warrior"))
	skills = (d.get("skills", {}) as Dictionary).duplicate()
	deity = str(d.get("deity", ""))
	level = int(d.get("level", 1))
	xp = int(d.get("xp", 0))
	coin = int(d.get("coin", 0))
	pack = Pack.from_save(d.get("pack"), d.get("inventory", []))
	if d.get("pack") == null:  # new characters, and those from before bags: a sack to start
		for g in Pack.GENERAL:
			if pack.slots[g].is_empty():
				pack.slots[g] = Pack.entry("small_sack")
				break
	quests = (d.get("quests", {}) as Dictionary).duplicate(true)
	bank = []
	for i in int(World.cfg("bank_slots", 16)):
		bank.append({})
	var saved_bank: Variant = d.get("bank")
	if saved_bank is Array:
		for i in mini((saved_bank as Array).size(), bank.size()):
			bank[i] = Pack.clean_entry(saved_bank[i])
	else:
		var old: Array = d.get("bank_items", [])
		for i in mini(old.size(), bank.size()):
			bank[i] = Pack.clean_entry({"item": old[i], "count": 1})
	for e: Variant in (d.get("trade_items", []) as Array) + ([d["cursor"]] if d.get("cursor") is Dictionary else []):
		var clean := Pack.clean_entry(e)  # a save mid-trade or mid-move: back in the pack
		if not clean.is_empty() and not pack.add_entry(clean):
			cursor = clean
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
	fill_skills()
	hp = clampi(int(d.get("hp", max_hp)), 1, max_hp)
	mana = clampi(int(d.get("mana", max_mana)), 0, max_mana)
	stamina = float(max_stamina)  # you arrive rested; it is not worth saving


## F2-F6: the 1st-5th other member of your group, or -1 for any other key.
func _group_key(event: InputEvent) -> int:
	for i in 5:
		if event.is_action_pressed("target_group_%d" % (i + 1)):
			return i
	return -1


func target_group_member(index: int) -> void:
	var others := group.filter(func(m: Dictionary) -> bool: return int(m["id"]) != entity_id)
	if index >= others.size():
		return
	var m: Dictionary = others[index]
	if World.get_object(int(m["id"])) == null:
		World.say(self, "%s is not in this zone." % m["name"], World.C_WARN)
		return
	World.request_set_target(entity_id, int(m["id"]))


## /follow: walk after your target (a groupmate, usually) until you move
## yourself, it leaves the zone, or it gets too far ahead.
func start_follow() -> void:
	var t := valid_target_entity()
	if t == null or t == self:
		World.say(self, "Target someone to follow.", World.C_WARN)
		return
	follow_target = t
	World.say(self, "You start following %s." % t.display_name, World.C_SYSTEM)


func stop_follow(why := "") -> void:
	if follow_target == null:
		return
	var name := (follow_target as Entity).display_name if is_instance_valid(follow_target) else "your target"
	follow_target = null
	World.say(self, why if why != "" else "You stop following %s." % name, World.C_SYSTEM)


func _follow_step() -> Vector3:
	var t := follow_target as Entity
	if not is_instance_valid(t) or t.dead or distance_to(t) > 100.0:
		stop_follow("You lose sight of whoever you were following.")
		return Vector3.ZERO
	if distance_to(t) < 3.0:
		return Vector3.ZERO
	face_toward(t.global_position)
	var d := t.global_position - global_position
	d.y = 0.0
	return d.normalized()


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
	var bags_before := [pack.slots.duplicate(true), equipment, coin, bank, bank_coin, trade_items, cursor]
	var quests_before := quests
	var level_before := level
	for key: String in ["level", "xp", "coin", "hp", "max_hp", "mana", "max_mana", "ac", "dmg_min", "dmg_max",
			"attack_delay", "attack_verb", "attributes", "equipment", "spells", "quests", "factions",
			"bank", "bank_coin", "cursor", "cast", "cooldowns", "buffs", "sitting", "auto_attack", "trade_npc_id",
			"trade_items", "service_npc_id", "service", "camp_left", "root_left", "dots", "stamina", "max_stamina", "sprinting",
			"group", "skills", "threatened", "sneaking", "snare_left"]:
		set(key, d[key])
	if bool(d.get("hidden", false)) != hidden:
		hidden = bool(d.get("hidden", false))
		show_hidden()
	if bool(d["dead"]) != dead:
		dead = bool(d["dead"])
		if nameplate != null:
			nameplate.visible = not dead
	var t: Node3D = World.get_object(int(d["target"])) if int(d["target"]) >= 0 else null
	if t != target:
		target = t
	var lk: Dictionary = d["look"]
	if visual is CharacterModel and (lk.get("weapon") != look.get("weapon") or lk.get("offhand") != look.get("offhand") or lk.get("worn") != look.get("worn") \
			or lk.get("tiers") != look.get("tiers")):
		(visual as CharacterModel).set_tiers(lk.get("tiers", {}))
		(visual as CharacterModel).set_weapon(str(lk.get("weapon", "")))
		(visual as CharacterModel).set_offhand(str(lk.get("offhand", "")))
		(visual as CharacterModel).set_worn(lk.get("worn", {}))
	look = lk
	pack.slots = (d["pack"] as Array).duplicate(true)
	if bags_before != [pack.slots, equipment, coin, bank, bank_coin, trade_items, cursor]:
		inventory_changed.emit()
	if quests_before != quests:
		quests_changed.emit()
	if level > level_before:
		leveled_up.emit()
	stats_changed.emit()


func to_save() -> Dictionary:
	var p := global_position
	return {
		"name": display_name, "class": char_class, "deity": deity, "skills": skills, "level": level, "xp": xp, "coin": coin,
		"pack": pack.to_save(), "trade_items": trade_items, "cursor": cursor, "equipment": equipment, "quests": quests, "spells": spells, "bank": bank, "bank_coin": bank_coin, "factions": factions, "hp": maxi(hp, 1), "mana": mana,
		"position": [p.x, p.y, p.z],
	}


## Whether one more of this item fits in the general slots and bags.
func room_for(item_id: String) -> bool:
	return pack.room_for(item_id) > 0


## Every item this character owns right now, one id per unit: carried, on the
## cursor, worn, banked and offered in a trade. (Lore checks, quest counts.)
func owned_item_ids() -> Array:
	var out: Array = pack.item_ids() + equipment.values()
	for e: Dictionary in bank + trade_items + [cursor]:
		if e.is_empty():
			continue
		for k in int(e.get("count", 1)):
			out.append(e["item"])
		for inner: Dictionary in e.get("contents", []):
			if not inner.is_empty():
				out.append(inner["item"])
	return out


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
	var off_weapon_dmg := 0
	var weapon_model := ""
	var offhand_model := ""
	var attr := {}  # str, sta, agi, wis, int, haste, hp_regen, mana_regen from gear
	attack_delay = 3.0
	attack_verb = ["hit", "hits"]
	off_delay = 0.0
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
			if item.has("dmg"):  # a weapon in the off hand (Dual Wield)
				off_weapon_dmg = maxi(1, roundi(int(item.get("dmg", 2)) * eff))
				off_delay = float(item.get("delay", 3.0))
				off_verb = item.get("verb", ["hit", "hits"])
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
	if off_weapon_dmg > 0:  # the off hand hits a little lighter than the main; buffs and deity count the same
		off_dmg_min = dmg_min
		off_dmg_max = maxi(off_dmg_min + 1, int((off_weapon_dmg * 2 + level) * skill * World.OFFHAND_DAMAGE) + int(attr.get("str", 0)) / 5
				+ buff_total("dmg") + int(GameData.deity_bonus(deity, "dmg")))
		off_delay /= 1.0 + minf(int(attr.get("haste", 0)), 40) / 100.0
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
	var worn := worn_gear_models()
	var tiers := GameData.gear_tiers(equipment)
	if visual is CharacterModel and (look.get("weapon") != weapon_model or look.get("offhand") != offhand_model or look.get("worn") != worn \
			or look.get("tiers", {}) != tiers):
		look["weapon"] = weapon_model
		look["offhand"] = offhand_model
		look["worn"] = worn
		look["tiers"] = tiers
		(visual as CharacterModel).set_tiers(tiers)
		(visual as CharacterModel).set_worn(worn)
		Net.broadcast_look(self)
	stamina = minf(stamina, float(max_stamina))
	if visual is CharacterModel:
		(visual as CharacterModel).set_weapon(weapon_model)
		(visual as CharacterModel).set_offhand(offhand_model)
		look["weapon"] = weapon_model
		look["offhand"] = offhand_model
	stats_changed.emit()


## {slot: gear model} for everything equipped that shows on the body.
func worn_gear_models() -> Dictionary:
	var out := {}
	for slot: String in equipment:
		var wear := str(GameData.item(equipment[slot]).get("wear", ""))
		if wear != "":
			out[slot] = wear
	return out


## Any skill this class can learn but hasn't got yet starts partway to its cap
## (new characters, and characters from before skills existed).
func fill_skills() -> void:
	var start := float(GameData.skills["tuning"]["start_fraction"])
	for id: String in GameData.skills["skills"]:
		var cap := GameData.skill_cap(char_class, id, level)
		if cap > 0 and not skills.has(id):
			skills[id] = int(cap * start)
		elif skills.has(id):
			skills[id] = int(skills[id])


## Everything you carry, EverQuest-style: what you wear, what's in your pack
## (a good bag lightens what's inside it), what's on the cursor, and your coin.
func _load_speed() -> float:
	_load_timer -= get_physics_process_delta_time()
	if _load_timer <= 0.0:
		_load_timer = 0.3
		_load_factor = encumbrance_speed()
	return _load_factor


func carried_weight() -> float:
	var w := 0.0
	for slot: String in equipment:
		w += GameData.item_weight(str(equipment[slot]))
	for e: Dictionary in pack.slots:
		if e.is_empty():
			continue
		w += GameData.item_weight(str(e["item"])) * int(e.get("count", 1))
		if e.has("contents"):
			var inside := 0.0
			for c: Dictionary in e["contents"]:
				if not c.is_empty():
					inside += GameData.item_weight(str(c["item"])) * int(c.get("count", 1))
			w += inside * (1.0 - float(GameData.item(str(e["item"])).get("weight_reduction", 0.0)))
	if not cursor.is_empty():
		w += GameData.item_weight(str(cursor["item"])) * int(cursor.get("count", 1))
	return w + coin_weight()


## Coins weigh what the fewest coins for your purse would (1 platinum = 10 gold
## = 100 silver = 1000 copper): small change is light, a fortune is not. Bank it.
func coin_weight() -> float:
	var coins := coin / 1000 + (coin / 100) % 10 + (coin / 10) % 10 + coin % 10
	return coins * float(World.cfg("coin_weight", 0.1))


## How much you can carry before it slows you: grows with level and strength.
func carry_capacity() -> float:
	return float(World.cfg("carry_base", 40)) + level * float(World.cfg("carry_per_level", 2)) + int(attributes.get("str", 0)) * float(World.cfg("carry_per_str", 3))


## Your speed under your load: 1 up to capacity, then 10% slower for every 10%
## over, never below 40%.
func encumbrance_speed() -> float:
	var over := carried_weight() / maxf(carry_capacity(), 1.0)
	return 1.0 if over <= 1.0 else maxf(0.4, 1.0 - (over - 1.0))


func xp_to_next() -> int:
	return int(float(World.cfg("xp_per_level_sq", 100)) * level * level)


## Blessing of the Elders: every character is born with it and keeps it until
## config "elders_blessing.until_level"; it adds xp_pct to all experience.
func elders_blessing() -> bool:
	var b: Dictionary = World.cfg("elders_blessing", {})
	return not b.is_empty() and level < int(b.get("until_level", 10))


func add_xp(amount: int, party := false) -> void:
	var max_level := int(World.cfg("max_level", 10))
	if level >= max_level:
		return
	if elders_blessing():
		amount = int(round(amount * (1.0 + float(World.cfg("elders_blessing", {}).get("xp_pct", 15)) / 100.0)))
	xp += amount
	World.say(self, "You gain party experience!!" if party else "You gain experience!!", World.C_XP)
	while level < max_level and xp >= xp_to_next():
		xp -= xp_to_next()
		level += 1
		recalc_stats()
		World.say(self, "You have gained a level! Welcome to level %d!" % level, World.C_XP)
		if level == int(World.cfg("elders_blessing", {}).get("until_level", 10)):
			World.say(self, "The Blessing of the Elders fades from you. The elders have seen you grown; the rest of the road is yours.", World.C_SPELL)
		for skill_id: String in GameData.skills.get("skills", {}):  # skills that open at this level (Dual Wield at 13)
			if int(GameData.skills["skills"][skill_id].get("from", {}).get(char_class, 0)) == level:
				World.say(self, "You have learned %s!" % GameData.skill_name(skill_id), World.C_XP)
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
		(visual as CharacterModel).set_tiers(look.get("tiers", {}))
		(visual as CharacterModel).set_offhand(str(look.get("offhand", "")))
	if visual is CharacterModel:
		if mirrored.is_empty():
			look["tiers"] = GameData.gear_tiers(equipment)
			(visual as CharacterModel).set_tiers(look["tiers"])
			look["worn"] = worn_gear_models()
			look["offhand"] = str(GameData.item(equipment.get("secondary", "")).get("model", ""))
			(visual as CharacterModel).set_offhand(look["offhand"])
		(visual as CharacterModel).set_worn(look.get("worn", {}))
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
	if Net.mode != "server":
		SpellFx.update_cast(self)  # a glow in the hands while casting, for everyone watching
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
					if mouse_looking and cursor.is_empty():
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
	elif event.is_action_pressed("ranged"):
		World.request_ranged(entity_id)
	elif event.is_action_pressed("target_next"):
		_cycle_target()
	elif event.is_action_pressed("target_interact"):
		_cycle_interact()
	elif event.is_action_pressed("target_self"):
		World.request_set_target(entity_id, entity_id)
	elif _group_key(event) >= 0:
		target_group_member(_group_key(event))
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


func _hud_typing() -> bool:
	if not is_instance_valid(_cursor_hud):
		_cursor_hud = get_tree().get_first_node_in_group("hud")
	return _cursor_hud != null and _cursor_hud.is_typing()


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
	elif col is GroundItem:
		World.request_pickup(entity_id, (col as GroundItem).object_id)


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
	if not cursor.is_empty():  # holding something: give it to the npc clicked, or drop it on the ground, as in EQ
		if col is Npc:
			World.request_give(entity_id, (col as Npc).entity_id)
		else:
			World.request_drop(entity_id)
		return
	if col == null:
		return
	if col is GroundItem:
		World.request_pickup(entity_id, (col as GroundItem).object_id)
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
	var typing := _hud_typing()  # keys typed into chat don't walk you around
	var fwd := 0.0 if typing else Input.get_axis("move_back", "move_forward")
	var strafe := 0.0 if typing else Input.get_axis("move_left", "move_right")
	var turn := 0.0 if typing else Input.get_axis("turn_left", "turn_right")  # arrow keys, for turning without the mouse
	if not Controls.mouse_look:
		turn = clampf(turn + strafe, -1.0, 1.0)  # keyboard scheme: A/D turn, as they did before mouselook
		strafe = 0.0
	if turn != 0.0:
		rotate_y(-turn * TURN_SPEED * delta)
	var dir := -transform.basis.z * fwd + transform.basis.x * strafe
	dir.y = 0.0
	if dir.length() > 1.0:
		dir = dir.normalized()
	if follow_target != null:
		if dir != Vector3.ZERO or turn != 0.0:
			stop_follow()  # taking the controls back
		else:
			dir = _follow_step()
	var spd := BACK_SPEED if fwd < 0.0 else RUN_SPEED * (1.0 + GameData.deity_bonus(deity, "run_speed_pct") / 100.0)
	# Sprinting is forward-only, and asked for every frame rather than toggled:
	# World decides whether it is allowed and ends it when the wind runs out.
	var want_sprint := Input.is_action_pressed("sprint") and fwd > 0.0
	if want_sprint != sprinting and _may_ask("sprint"):
		World.request_sprint(entity_id, want_sprint)
	if sprinting:
		spd *= float(World.cfg("sprint_speed_mult", 1.55))
	if sneaking:
		spd *= SNEAK_SPEED
	if snare_left > 0.0:
		spd *= 0.5
	spd *= _load_speed()
	if dir != Vector3.ZERO and sitting and _may_ask("stand"):
		World.request_sit(entity_id, false)
	velocity.x = dir.x * spd
	velocity.z = dir.z * spd
	if is_on_floor() and not typing and Input.is_action_just_pressed("jump"):
		velocity.y = JUMP_VELOCITY
	move_and_slide()
	if global_position.y < -60.0:
		global_position = World.zone_of(self).bind_point + Vector3.UP
		velocity = Vector3.ZERO
