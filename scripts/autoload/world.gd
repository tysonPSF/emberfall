extends Node
## Authoritative game rules: object registry, combat, spells, XP, death, loot.
##
## Everything that changes game state goes through here. Player input only
## calls the request_* functions, passing ids rather than node references.
## When multiplayer arrives, those same functions become server RPCs and the
## rules below run only on the server; clients just render the results.

signal log_message(text: String, color: Color)
signal loot_opened(corpse: Corpse)
signal loot_changed(corpse: Corpse)
signal loot_closed(corpse: Corpse)  # null = close whatever is open
signal player_died(player: Player)
signal trade_opened(npc: Npc)
signal trade_changed
signal trade_closed
signal camped(player: Player)
signal service_opened(npc: Npc, kind: String)  # kind: "shop" or "bank"
signal service_changed
signal service_closed
signal zone_change(player: Player, zone_id: String, arrive: Vector2, face: Vector2)

enum Con { GRAY, GREEN, BLUE, WHITE, YELLOW, RED }

const CON_COLORS: Array[Color] = [
	Color(0.62, 0.62, 0.62), Color(0.35, 0.9, 0.35), Color(0.45, 0.62, 1.0),
	Color(1, 1, 1), Color(1, 0.9, 0.25), Color(1, 0.3, 0.25),
]
const CON_TEXT: Array[String] = [
	"it would not be worth your time.",
	"you could probably win this fight.",
	"looks like a reasonably safe opponent.",
	"looks like an even fight.",
	"looks like quite a gamble.",
	"what would you like your tombstone to say?",
]

const C_YOU_HIT := Color(1, 1, 1)
const C_HIT_YOU := Color(1, 0.42, 0.36)
const C_MISS := Color(0.68, 0.68, 0.68)
const C_SPELL := Color(0.55, 0.78, 1)
const C_XP := Color(1, 0.88, 0.35)
const C_LOOT := Color(0.55, 1, 0.55)
const C_WARN := Color(1, 0.62, 0.25)
const C_SYSTEM := Color(0.85, 0.85, 0.8)
const C_SAY := Color(0.9, 0.9, 0.9)
const C_NPC := Color(0.75, 0.9, 1.0)

const LOOT_RANGE := 6.0
const TALK_RANGE := 10.0
const TRADE_SLOTS := 4
## EQ faction tiers: lowest standing for each, and how that NPC regards you.
const STANDING_TIERS: Array = [
	[1100, "Ally", "regards you as an ally"], [750, "Warmly", "looks upon you warmly"],
	[500, "Kindly", "kindly considers you"], [100, "Amiable", "judges you amiably"],
	[-100, "Indifferent", "regards you indifferently"], [-500, "Apprehensive", "looks your way apprehensively"],
	[-750, "Dubious", "glowers at you dubiously"], [-1100, "Threatening", "glares at you threateningly"],
	[-99999, "Scowls", "scowls at you, ready to attack"],
]
const FACTION_MAX := 2000
const REFUSE_BELOW := -500  # Dubious or worse: townsfolk won't deal with you
const KOS_BELOW := -1100  # Scowls: guards attack on sight
const ATTACK_CONFIRM_MS := 5000
const CALL_FOR_HELP_RADIUS := 14.0
const EQUIP_SLOTS: Array[String] = ["primary", "head", "chest", "legs"]

var objects: Dictionary = {}  # id -> Entity or Corpse
var next_id := 1
var local_player: Player = null
var zone: Zone = null
var tick_timer := 0.0
var _range_warn_cooldown := 0.0
var merchant_stock: Dictionary = {}  # merchant npc id -> {item id: count} bought from players


# --- registry ---------------------------------------------------------------

func register(obj: Node3D) -> int:
	var id := next_id
	next_id += 1
	objects[id] = obj
	return id


func unregister(id: int) -> void:
	objects.erase(id)


func get_object(id: int) -> Node3D:
	var obj: Variant = objects.get(id)
	if obj != null and is_instance_valid(obj):
		return obj
	return null


func get_players() -> Array[Player]:
	var out: Array[Player] = []
	for obj: Node3D in objects.values():
		if obj is Player:
			out.append(obj)
	return out


func get_mobs() -> Array[Mob]:
	var out: Array[Mob] = []
	for obj: Node3D in objects.values():
		if obj is Mob:
			out.append(obj)
	return out


func cfg(key: String, default: Variant = null) -> Variant:
	return GameData.config.get(key, default)


func melee_range() -> float:
	return float(cfg("melee_range", 3.4))


# --- messages ---------------------------------------------------------------

## Sends a chat-log line to one entity. Only the local player has a log today;
## with networking this becomes "send to that player's connection".
func say(to: Entity, text: String, color: Color = C_SYSTEM) -> void:
	if to != null and to == local_player:
		log_message.emit(text, color)


## Says something out loud: every player within earshot sees it.
func shout(from: Node3D, text: String, color: Color = C_NPC, radius := 60.0) -> void:
	for p in get_players():
		if p.global_position.distance_to(from.global_position) <= radius:
			say(p, text, color)


static func cap(s: String) -> String:
	return s.substr(0, 1).to_upper() + s.substr(1)


static func format_coin(copper: int) -> String:
	var parts: PackedStringArray = []
	var amounts := [[copper / 1000, "platinum"], [(copper / 100) % 10, "gold"], [(copper / 10) % 10, "silver"], [copper % 10, "copper"]]
	for a: Array in amounts:
		if a[0] > 0:
			parts.append("%d %s" % [a[0], a[1]])
	return ", ".join(parts) if parts.size() > 0 else "0 copper"


# --- con ------------------------------------------------------------------

func con_of(viewer_level: int, other_level: int) -> int:
	var diff := other_level - viewer_level
	if diff >= 3:
		return Con.RED
	if diff >= 1:
		return Con.YELLOW
	if diff == 0:
		return Con.WHITE
	var gray_at := maxi(4, int(viewer_level * 0.4) + 2)
	var green_at := maxi(2, int(viewer_level * 0.2) + 1)
	if -diff >= gray_at:
		return Con.GRAY
	if -diff >= green_at:
		return Con.GREEN
	return Con.BLUE


# --- simulation -------------------------------------------------------------

func _physics_process(delta: float) -> void:
	_range_warn_cooldown = maxf(0.0, _range_warn_cooldown - delta)
	for obj: Node3D in objects.values():
		if obj is Entity and is_instance_valid(obj) and not obj.dead:
			_update_timers(obj, delta)
			_update_cast(obj, delta)
			_update_melee(obj)
		if obj is Player and (obj as Player).trade_npc_id >= 0:
			_check_trade(obj)
		if obj is Player and (obj as Player).service_npc_id >= 0:
			_check_service(obj)
		if obj is Player and (obj as Player).camp_left > 0.0:
			_update_camp(obj, delta)
	tick_timer += delta
	if tick_timer >= float(cfg("tick_seconds", 6.0)):
		tick_timer = 0.0
		_regen_tick()


func _update_timers(e: Entity, delta: float) -> void:
	e.swing_timer = maxf(0.0, e.swing_timer - delta)
	e.root_left = maxf(0.0, e.root_left - delta)
	for spell_id: String in e.cooldowns.keys():
		e.cooldowns[spell_id] -= delta
		if e.cooldowns[spell_id] <= 0.0:
			e.cooldowns.erase(spell_id)
	for spell_id: String in e.buffs.keys():
		e.buffs[spell_id]["left"] -= delta
		if e.buffs[spell_id]["left"] <= 0.0:
			e.buffs.erase(spell_id)
			say(e, str(GameData.spells[spell_id].get("fade_text", "Your %s spell has worn off." % GameData.spells[spell_id]["name"])), C_SPELL)
			e.recalc_stats()
	for dot: Dictionary in e.dots.duplicate():
		dot["next"] -= delta
		if dot["next"] > 0.0:
			continue
		dot["next"] = 3.0
		dot["ticks"] -= 1
		if dot["ticks"] <= 0:
			e.dots.erase(dot)
		var caster := get_object(dot["caster_id"]) as Entity
		say(caster, "%s has taken %d damage from your %s." % [cap(e.display_name), dot["damage"], GameData.spells[dot["spell"]]["name"]], C_SPELL)
		say(e, "You have taken %d points of damage." % dot["damage"], C_HIT_YOU)
		damage(e, int(dot["damage"]), caster)
		if e.dead:
			return


func _update_melee(e: Entity) -> void:
	if not e.auto_attack:
		return
	var t := e.valid_target_entity()
	if not can_attack(e, t):
		return
	if e.distance_to(t) > melee_range():
		if e == local_player and _range_warn_cooldown <= 0.0:
			_range_warn_cooldown = 2.5
			say(e, "Your target is too far away, get closer!", C_WARN)
		return
	if e.swing_timer > 0.0:
		return
	e.swing_timer = e.attack_delay
	e.sitting = false
	var chance := clampf(0.72 + (e.level - t.level) * 0.04 - t.ac * 0.004, 0.12, 0.95)
	var dmg := randi_range(e.dmg_min, e.dmg_max) if randf() < chance else 0
	e.animate("attack")
	_combat_msg(e, t, e.attack_verb, dmg)
	if dmg > 0:
		damage(t, dmg, e)


func _combat_msg(a: Entity, d: Entity, verb: Array, dmg: int) -> void:
	if a == local_player:
		if dmg > 0:
			say(a, "You %s %s for %d points of damage." % [verb[0], d.display_name, dmg], C_YOU_HIT)
		else:
			say(a, "You try to %s %s, but miss!" % [verb[0], d.display_name], C_MISS)
	elif d == local_player:
		if dmg > 0:
			say(d, "%s %s YOU for %d points of damage." % [cap(a.display_name), verb[1], dmg], C_HIT_YOU)
		else:
			say(d, "%s tries to %s YOU, but misses!" % [cap(a.display_name), verb[0]], C_MISS)


func damage(d: Entity, amount: int, src: Entity) -> void:
	if d.dead:
		return
	d.hp -= amount
	d.sitting = false
	if src != null:
		d.add_hate(src, float(amount))
	d.animate("hit")
	d.stats_changed.emit()
	if d.hp <= 0:
		kill(d, src)


func _regen_tick() -> void:
	var mult := float(cfg("regen_multiplier", 1.0))
	for obj: Node3D in objects.values():
		if not (obj is Entity) or obj.dead:
			continue
		var e := obj as Entity
		var hp_gain := e.hp_regen * (3 if e.sitting else 1)
		if e is Mob and not ((e as Mob).state in [Mob.State.COMBAT, Mob.State.FLEE]):
			hp_gain = maxi(hp_gain, e.max_hp / 8)
		var mana_gain := 0
		if e.max_mana > 0:
			mana_gain = e.mana_regen + (2 + e.level / 2 if e.sitting else 0)
		e.hp = mini(e.max_hp, e.hp + int(ceil(hp_gain * mult)))
		e.mana = mini(e.max_mana, e.mana + int(ceil(mana_gain * mult)))
		e.stats_changed.emit()


# --- death ----------------------------------------------------------------

func kill(d: Entity, killer: Entity) -> void:
	d.dead = true
	d.hp = 0
	d.dots.clear()
	d.buffs.clear()
	d.root_left = 0.0
	d.auto_attack = false
	d.cast = {}
	d.sitting = false
	for obj: Node3D in objects.values():
		if obj is Entity:
			obj.hate.erase(d.entity_id)
	if killer is Player and GameData.factions.has(d.faction):
		apply_faction(killer, GameData.factions[d.faction].get("on_kill", {}))
	if d is Npc:
		for pl in get_players():
			pl.hostile_npcs.erase(d.entity_id)
	if d is Mob:
		_kill_mob(d, killer)
	elif d is Player:
		_kill_player(d, killer)
	elif d is Npc:
		if local_player != null and local_player.distance_to(d) < 60.0:
			log_message.emit("%s has been slain by %s!" % [d.display_name, killer.display_name if killer != null else "unknown forces"], C_WARN)
		(d as Npc).on_killed()


func _kill_mob(mob: Mob, killer: Entity) -> void:
	if killer != null and killer == local_player:
		say(killer, "You have slain %s!" % mob.display_name, C_XP)
	elif local_player != null and local_player.global_position.distance_to(mob.global_position) < 40.0:
		var by := killer.display_name if killer != null else "unknown forces"
		log_message.emit("%s has been slain by %s!" % [cap(mob.display_name), by], C_SYSTEM)
	if killer is Player:
		award_xp(killer, mob)

	var entries: Array = []
	for entry: Dictionary in mob.data.get("loot", []):
		if randf() < float(entry["chance"]):
			entries.append({"item": entry["item"], "slot": ""})
	var coin_range: Array = mob.data.get("coin", [0, 0])
	var coin := randi_range(int(coin_range[0]), int(coin_range[1]))
	var empty := entries.is_empty() and coin == 0
	var decay := float(cfg("empty_corpse_decay_seconds" if empty else "mob_corpse_decay_seconds", 60))

	var corpse := Corpse.new()
	corpse.setup(mob.display_name, mob.look, entries, coin, decay)
	corpse.position = mob.global_position
	corpse.rotation.y = mob.rotation.y
	zone.add_child(corpse)

	for p in get_players():
		if p.target == mob:
			p.target = corpse
			p.auto_attack = false
	if mob.spawn_point != null:
		mob.spawn_point.on_mob_died()
	mob.queue_free()


func _kill_player(p: Player, killer: Entity) -> void:
	p.hostile_npcs.clear()
	request_trade_cancel(p.entity_id)
	request_service_close(p.entity_id)
	say(p, "You have been slain by %s!" % killer.display_name if killer != null else "You have died.", C_HIT_YOU)
	var loss := int(p.xp_to_next() * float(cfg("death_xp_loss", 0.1)) * (1.0 + GameData.deity_bonus(p.deity, "xp_loss_pct") / 100.0))
	if loss > 0 and p.xp > 0:
		p.xp = maxi(0, p.xp - loss)
		say(p, "You have lost experience.", C_WARN)
	if cfg("corpse_runs", true) and (not p.inventory.is_empty() or not p.equipment.is_empty() or p.coin > 0):
		var entries: Array = []
		for slot: String in p.equipment:
			entries.append({"item": p.equipment[slot], "slot": slot})
		for item_id: String in p.inventory:
			entries.append({"item": item_id, "slot": ""})
		var corpse := Corpse.new()
		corpse.setup(p.display_name, p.look, entries, p.coin,
				float(cfg("player_corpse_decay_seconds", 3600)), p.display_name)
		corpse.position = p.global_position
		zone.add_child(corpse)
		p.equipment.clear()
		p.inventory.clear()
		p.coin = 0
		p.recalc_stats()
		p.inventory_changed.emit()
		say(p, "Your belongings remain on your corpse. Go back and loot it.", C_WARN)
	p.on_death()
	player_died.emit(p)
	get_tree().create_timer(float(cfg("respawn_delay", 4.0))).timeout.connect(p.respawn)


func award_xp(p: Player, mob: Mob) -> void:
	if con_of(p.level, mob.level) == Con.GRAY:
		return
	var base := float(cfg("xp_base", 10)) + mob.level * mob.level * float(cfg("xp_per_mob_level_sq", 5))
	var amount := int(base * float(cfg("xp_rate", 1.0)) * float(mob.data.get("xp_bonus", 1.0)))
	p.add_xp(amount)


# --- requests (the future network boundary) ---------------------------------

## Whether `a` may fight `t`. Townsfolk never fight each other; a player may
## fight an NPC only after choosing to (see request_toggle_attack), while mobs
## and NPCs may always fight back.
func can_attack(a: Entity, t: Entity) -> bool:
	if t == null or t == a or t.dead:
		return false
	if a is Npc and t is Npc:
		return false
	if t is Npc:
		return a is Mob or (a is Player and (a as Player).hostile_npcs.has(t.entity_id))
	if a is Npc:
		return true
	return t.faction != a.faction


func request_set_target(entity_id: int, target_id: int) -> void:
	var e := get_object(entity_id) as Entity
	if e != null:
		e.target = get_object(target_id) if target_id >= 0 else null


func request_toggle_attack(entity_id: int) -> void:
	var e := get_object(entity_id) as Entity
	if e == null or e.dead:
		return
	if e.auto_attack:
		e.auto_attack = false
		say(e, "Auto attack is off.")
		return
	var t := e.valid_target_entity()
	if e is Player and t is Npc and not can_attack(e, t):
		var p := e as Player
		if p.attack_confirm_id == t.entity_id and Time.get_ticks_msec() - p.attack_confirm_at < ATTACK_CONFIRM_MS:
			declare_hostile(p, t as Npc)
		else:
			p.attack_confirm_id = t.entity_id
			p.attack_confirm_at = Time.get_ticks_msec()
			var fname := faction_name(t.faction)
			say(e, "Attacking %s will anger %s. Press Q again to attack." % [t.display_name, fname], C_WARN)
			return
	if not can_attack(e, t):
		say(e, "You need to target something you can attack.", C_WARN)
		return
	e.auto_attack = true
	e.sitting = false
	say(e, "Auto attack is on.")


func request_sit(entity_id: int, sit: bool) -> void:
	var e := get_object(entity_id) as Entity
	if e == null or e.dead or e.sitting == sit:
		return
	if sit:
		if not e.cast.is_empty():
			return
		e.auto_attack = false
		say(e, "You sit down to rest.")
	e.sitting = sit


func request_consider(entity_id: int) -> void:
	var e := get_object(entity_id) as Entity
	if e == null:
		return
	var t := e.valid_target_entity()
	if t == null or t == e:
		say(e, "You must first select a target.", C_WARN)
		return
	if t is Player:
		say(e, "%s regards you as an ally." % t.display_name, C_SPELL)
		return
	var con := con_of(e.level, t.level)
	var attitude := "regards you indifferently"
	if e is Player and GameData.factions.has(t.faction):
		attitude = standing_tier(standing(e as Player, t.faction))[2]
	if t is Mob and ((t as Mob).aggressive or (e is Player and mob_kos(e as Player, t.faction))):
		attitude = "scowls at you, ready to attack"
	say(e, "%s %s -- %s" % [cap(t.display_name), attitude, CON_TEXT[con]], CON_COLORS[con])


func request_cast(entity_id: int, spell_id: String) -> void:
	var c := get_object(entity_id) as Entity
	if c == null or c.dead or not (spell_id in c.spells):
		return
	var s: Dictionary = GameData.spells[spell_id]
	if not c.cast.is_empty():
		return
	if c.cooldowns.has(spell_id):
		say(c, "You haven't recovered yet. %s is ready in %ds." % [s["name"], ceili(float(c.cooldowns[spell_id]))], C_WARN)
		return
	if c.mana < int(s.get("mana", 0)):
		say(c, "Insufficient Mana to cast this spell!", C_WARN)
		return
	var t := _resolve_spell_target(c, s)
	if t == null:
		say(c, "You must first select a target for this spell!", C_WARN)
		return
	if t != c and c.distance_to(t) > float(s.get("range", 0)):
		say(c, "Your target is out of range, get closer!", C_WARN)
		return
	c.sitting = false
	if float(s.get("cast_time", 0)) <= 0.0:
		_finish_spell(c, spell_id, t)
		return
	c.cast = {"spell": spell_id, "target_id": t.entity_id, "time": 0.0,
			"total": float(s["cast_time"]), "start_pos": c.global_position}
	say(c, "You begin casting %s." % s["name"], C_SPELL)


func request_interrupt(entity_id: int) -> void:
	var c := get_object(entity_id) as Entity
	if c != null and not c.cast.is_empty():
		c.cast = {}
		say(c, "Your spell is interrupted.", C_WARN)


func _resolve_spell_target(c: Entity, s: Dictionary) -> Entity:
	var t := c.valid_target_entity()
	match str(s.get("target", "enemy")):
		"self":
			return c
		"friendly":
			return t if t != null and t.faction == c.faction else c
		_:
			return t if can_attack(c, t) else null


func _update_cast(c: Entity, delta: float) -> void:
	if c.cast.is_empty():
		return
	var start: Vector3 = c.cast["start_pos"]
	if Vector2(c.global_position.x - start.x, c.global_position.z - start.z).length() > 0.3:
		request_interrupt(c.entity_id)
		return
	c.cast["time"] += delta
	if c.cast["time"] < c.cast["total"]:
		return
	var spell_id: String = c.cast["spell"]
	var s: Dictionary = GameData.spells[spell_id]
	var t := get_object(c.cast["target_id"]) as Entity
	c.cast = {}
	if t == null or t.dead:
		say(c, "Your target is gone.", C_WARN)
	elif t != c and c.distance_to(t) > float(s.get("range", 0)) + 2.0:
		say(c, "Your target is out of range, get closer!", C_WARN)
	elif c.mana < int(s.get("mana", 0)):
		say(c, "Insufficient Mana to cast this spell!", C_WARN)
	else:
		_finish_spell(c, spell_id, t)


func _finish_spell(c: Entity, spell_id: String, t: Entity) -> void:
	var s: Dictionary = GameData.spells[spell_id]
	c.mana -= int(s.get("mana", 0))
	c.cooldowns[spell_id] = float(s.get("recast", 0))
	var power := randi_range(int(s.get("min", 0)), int(s.get("max", 0))) + int(float(s.get("per_level", 0)) * (c.level - 1))
	match str(s["type"]):
		"damage":
			if s.get("ability", false):
				c.animate("attack")
				_combat_msg(c, t, s.get("verb", ["hit", "hits"]), power)
			else:
				say(c, "%s was hit by non-melee for %d points of damage." % [cap(t.display_name), power], C_SPELL)
				say(t, "You were hit by non-melee for %d points of damage." % power, C_HIT_YOU)
			damage(t, power, c)
		"heal":
			t.hp = mini(t.max_hp, t.hp + power)
			t.stats_changed.emit()
			say(t, "You feel better.", C_SPELL)
			if c != t:
				say(c, "You heal %s for %d hit points." % [t.display_name, power], C_SPELL)
			# Heal aggro: anything fighting the healed target now also hates the healer.
			for m in get_mobs():
				if m.hate.has(t.entity_id):
					m.add_hate(c, power * 0.5)
		"gate":
			for m in get_mobs():
				m.hate.erase(c.entity_id)
			c.global_position = zone.bind_point + Vector3.UP
			c.velocity = Vector3.ZERO
			say(c, "You feel yourself pulled back to your bind point.", C_SPELL)
		"buff":
			t.buffs[spell_id] = {"left": float(s.get("duration", 60)), "stats": s.get("stats", {})}
			t.recalc_stats()
			say(t, str(s.get("land_text", "You feel the effects of %s." % s["name"])), C_SPELL)
			if c != t:
				say(c, "You cast %s on %s." % [s["name"], t.display_name], C_SPELL)
		"dot":
			var per_tick := int(s.get("tick", 1)) + int(float(s.get("per_level", 0)) * (c.level - 1))
			t.dots = t.dots.filter(func(d: Dictionary) -> bool: return not (d["spell"] == spell_id and d["caster_id"] == c.entity_id))
			t.dots.append({"spell": spell_id, "caster_id": c.entity_id, "damage": per_tick, "ticks": int(s.get("ticks", 3)), "next": 3.0})
			say(c, "%s begins to smolder." % cap(t.display_name), C_SPELL)
			t.add_hate(c, float(per_tick))
		"root":
			t.root_left = float(s.get("duration", 10))
			say(c, "%s's feet adhere to the ground." % cap(t.display_name), C_SPELL)
			t.add_hate(c, 5.0)
		"taunt":
			var top := 0.0
			for v: float in t.hate.values():
				top = maxf(top, v)
			t.add_hate(c, top + 10.0 - float(t.hate.get(c.entity_id, 0.0)))
			say(c, "You taunt %s to ignore others and attack you!" % t.display_name, C_SPELL)
	c.stats_changed.emit()


func call_for_help(caller: Mob, enemy: Entity) -> void:
	for m in get_mobs():
		if m != caller and not m.dead and m.faction == caller.faction and m.hate.is_empty() \
				and m.global_position.distance_to(caller.global_position) <= CALL_FOR_HELP_RADIUS:
			m.add_hate(enemy, 1.0)


# --- loot & inventory -------------------------------------------------------

func request_loot_open(player_id: int, corpse_id: int) -> void:
	var p := get_object(player_id) as Player
	var c := get_object(corpse_id) as Corpse
	if p == null or c == null or p.dead:
		return
	if p.global_position.distance_to(c.global_position) > LOOT_RANGE:
		say(p, "You are too far away to loot that corpse.", C_WARN)
		return
	request_trade_cancel(player_id)
	if c.owner_name != "" and c.owner_name != p.display_name:
		say(p, "You may not loot this corpse.", C_WARN)
		return
	if c.coin > 0:
		p.coin += c.coin
		say(p, "You receive %s from the corpse." % format_coin(c.coin), C_LOOT)
		c.coin = 0
		p.inventory_changed.emit()
	if c.entries.is_empty():
		say(p, "The corpse is empty.")
		remove_corpse(c)
		return
	if p == local_player:
		loot_opened.emit(c)


func request_loot_item(player_id: int, corpse_id: int, index: int) -> bool:
	var p := get_object(player_id) as Player
	var c := get_object(corpse_id) as Corpse
	if p == null or c == null or index < 0 or index >= c.entries.size():
		return false
	if p.global_position.distance_to(c.global_position) > LOOT_RANGE:
		say(p, "You are too far away to loot that corpse.", C_WARN)
		return false
	var entry: Dictionary = c.entries[index]
	var slot: String = entry.get("slot", "")
	if slot != "" and not p.equipment.has(slot):
		p.equipment[slot] = entry["item"]
		p.recalc_stats()
	elif p.inventory.size() >= int(cfg("inventory_slots", 24)):
		say(p, "Your inventory is full.", C_WARN)
		return false
	else:
		p.inventory.append(entry["item"])
	c.entries.remove_at(index)
	say(p, "--You have looted a %s.--" % GameData.item_name(entry["item"]), C_LOOT)
	p.inventory_changed.emit()
	if c.entries.is_empty():
		remove_corpse(c)
	elif p == local_player:
		loot_changed.emit(c)
	return true


func request_loot_all(player_id: int, corpse_id: int) -> void:
	var c := get_object(corpse_id) as Corpse
	while c != null and not c.is_queued_for_deletion() and not c.entries.is_empty():
		if not request_loot_item(player_id, corpse_id, 0):
			break


func request_loot_close(player_id: int) -> void:
	if get_object(player_id) == local_player:
		loot_closed.emit(null)


func remove_corpse(c: Corpse) -> void:
	loot_closed.emit(c)
	c.queue_free()


func request_equip(player_id: int, inv_index: int) -> void:
	var p := get_object(player_id) as Player
	if p == null or p.dead or inv_index < 0 or inv_index >= p.inventory.size():
		return
	var item_id: String = p.inventory[inv_index]
	var slot: String = GameData.items.get(item_id, {}).get("slot", "")
	if slot == "":
		say(p, "You cannot equip that.", C_WARN)
		return
	p.inventory.remove_at(inv_index)
	if p.equipment.has(slot):
		p.inventory.append(p.equipment[slot])
	p.equipment[slot] = item_id
	p.recalc_stats()
	p.inventory_changed.emit()


func request_unequip(player_id: int, slot: String) -> void:
	var p := get_object(player_id) as Player
	if p == null or p.dead or not p.equipment.has(slot):
		return
	if p.inventory.size() >= int(cfg("inventory_slots", 24)):
		say(p, "Your inventory is full.", C_WARN)
		return
	p.inventory.append(p.equipment[slot])
	p.equipment.erase(slot)
	p.recalc_stats()
	p.inventory_changed.emit()


# --- npcs & quests ----------------------------------------------------------

## Hails the player's target, which also turns in any quest it is waiting on.
func request_hail(player_id: int) -> void:
	var p := get_object(player_id) as Player
	if p == null or p.dead:
		return
	if not (p.valid_target_entity() is Npc):
		say(p, "Target someone to hail them.", C_WARN)
		return
	_talk(p, p.target as Npc, "hail")


## Says a keyword to the player's target, EQ style ("gnoll fangs").
func request_say(player_id: int, keyword: String) -> void:
	var p := get_object(player_id) as Player
	if p == null or p.dead:
		return
	if not (p.valid_target_entity() is Npc):
		say(p, "Target someone to talk to them.", C_WARN)
		return
	_talk(p, p.target as Npc, keyword)


func _talk(p: Player, npc: Npc, keyword: String) -> void:
	if p.distance_to(npc) > TALK_RANGE:
		say(p, "You are too far away to talk to %s." % npc.display_name, C_WARN)
		return
	var key := keyword.strip_edges().to_lower()
	npc.greet(p)
	say(p, "You say, '%s'" % ("Hail, %s" % npc.display_name if key == "hail" else cap(key)), C_SAY)
	if refuses(p, npc):
		_npc_say(p, npc, str(npc.data.get("refuse_faction", "I'll have nothing to do with the likes of you, {name}.")))
		return
	var lines: Dictionary = npc.data.get("dialogue", {})
	_npc_say(p, npc, str(lines.get(key, lines.get("unknown", "..."))))
	if key == "hail" and (npc.data.has("merchant") or npc.data.get("banker", false)):
		say(p, "(Press G to %s.)" % ("see %s's wares" % npc.display_name if npc.data.has("merchant") else "open your bank"), C_SYSTEM)
	if key == "hail" and npc.data.has("guildmaster") and npc.data["guildmaster"]["class"] == p.char_class:
		say(p, "(Press G to train with %s.)" % npc.display_name, C_SYSTEM)
	if key == "hail":
		for quest_id: String in p.quests:
			var q: Dictionary = GameData.quests.get(quest_id, {})
			if q.get("giver") == npc.npc_id and p.quests[quest_id].get("active", false) and quest_items_ready(p, quest_id):
				_npc_say(p, npc, str(q.get("ready_text", "Hand those over, {name}.")))
				say(p, "(Press G to open a trade with %s.)" % npc.display_name, C_SYSTEM)
	for quest_id: String in GameData.quests:
		var q: Dictionary = GameData.quests[quest_id]
		if q["giver"] == npc.npc_id and key == str(q["start_keyword"]):
			_accept_quest(p, quest_id)


func _npc_say(p: Player, npc: Npc, text: String) -> void:
	say(p, "%s says, '%s'" % [npc.display_name, text.format({"name": p.display_name})], C_NPC)


func _accept_quest(p: Player, quest_id: String) -> void:
	var q: Dictionary = GameData.quests[quest_id]
	var state: Dictionary = p.quests.get(quest_id, {})
	if state.get("active", false) or (int(state.get("completions", 0)) > 0 and not q.get("repeatable", false)):
		return
	p.quests[quest_id] = {"active": true, "completions": int(state.get("completions", 0))}
	say(p, str(q["accept_text"]), C_XP)
	p.quests_changed.emit()


## Trade window: the player offers up to TRADE_SLOTS items to an npc. Offered
## items leave the inventory while the window is open, so they can't be spent
## twice; whatever the npc doesn't take comes back.
func request_trade_open(player_id: int) -> void:
	var p := get_object(player_id) as Player
	if p == null or p.dead or p.trade_npc_id >= 0:
		return
	var npc := p.valid_target_entity() as Npc
	if npc == null:
		say(p, "Target someone to trade with them.", C_WARN)
		return
	if p.distance_to(npc) > TALK_RANGE:
		say(p, "You are too far away to trade with %s." % npc.display_name, C_WARN)
		return
	if refuses(p, npc):
		_npc_say(p, npc, str(npc.data.get("refuse_faction", "I'll have nothing to do with the likes of you, {name}.")))
		return
	request_loot_close(player_id)
	p.trade_npc_id = npc.entity_id
	p.trade_items = []
	npc.greet(p)
	if p == local_player:
		trade_opened.emit(npc)


func request_trade_add(player_id: int, inv_index: int) -> void:
	var p := get_object(player_id) as Player
	if p == null or p.trade_npc_id < 0 or inv_index < 0 or inv_index >= p.inventory.size():
		return
	if p.trade_items.size() >= TRADE_SLOTS:
		say(p, "The trade window is full.", C_WARN)
		return
	p.trade_items.append(p.inventory[inv_index])
	p.inventory.remove_at(inv_index)
	p.inventory_changed.emit()
	if p == local_player:
		trade_changed.emit()


func request_trade_remove(player_id: int, slot: int) -> void:
	var p := get_object(player_id) as Player
	if p == null or p.trade_npc_id < 0 or slot < 0 or slot >= p.trade_items.size():
		return
	p.inventory.append(p.trade_items[slot])
	p.trade_items.remove_at(slot)
	p.inventory_changed.emit()
	if p == local_player:
		trade_changed.emit()


func request_trade_give(player_id: int) -> void:
	var p := get_object(player_id) as Player
	if p == null or p.trade_npc_id < 0:
		return
	var npc := get_object(p.trade_npc_id) as Npc
	if npc == null or p.distance_to(npc) > TALK_RANGE:
		request_trade_cancel(player_id)
		return
	var offered: Array = p.trade_items
	p.trade_items = []
	var left := _npc_take_items(p, npc, offered)
	if not left.is_empty():
		var names := PackedStringArray()
		for item_id: String in left:
			var n := left.count(item_id)
			var label := GameData.item_name(item_id) + (" x%d" % n if n > 1 else "")
			if not label in names:
				names.append(label)
		say(p, "%s has no use for %s and hands %s back." % [npc.display_name, ", ".join(names), "it" if left.size() == 1 else "them"], C_SYSTEM)
		p.inventory.append_array(left)
	p.inventory_changed.emit()
	_close_trade(p)


func request_trade_cancel(player_id: int) -> void:
	var p := get_object(player_id) as Player
	if p == null or p.trade_npc_id < 0:
		return
	p.inventory.append_array(p.trade_items)
	p.trade_items = []
	p.inventory_changed.emit()
	_close_trade(p)


func _close_trade(p: Player) -> void:
	p.trade_npc_id = -1
	if p == local_player:
		trade_closed.emit()


func _check_trade(p: Player) -> void:
	var npc := get_object(p.trade_npc_id)
	if npc == null or p.distance_to(npc) > TALK_RANGE:
		say(p, "You moved too far away and the trade was canceled.", C_WARN)
		request_trade_cancel(p.entity_id)


## Hands offered items to an npc: each quest it runs takes every full set of
## what it wants (a quest you never asked about still counts, as in EQ).
## Returns the items nobody wanted.
func _npc_take_items(p: Player, npc: Npc, offered: Array) -> Array:
	var left := offered.duplicate()
	for quest_id: String in GameData.quests:
		var q: Dictionary = GameData.quests[quest_id]
		if q["giver"] != npc.npc_id:
			continue
		var wants: Dictionary = q["wants"]
		while _has_all(left, wants):
			var state: Dictionary = p.quests.get(quest_id, {})
			if int(state.get("completions", 0)) > 0 and not q.get("repeatable", false):
				break
			for item_id: String in wants:
				for k in int(wants[item_id]):
					left.erase(item_id)
			_complete_quest(p, npc, quest_id)
	return left


static func _has_all(items: Array, wants: Dictionary) -> bool:
	for item_id: String in wants:
		if items.count(item_id) < int(wants[item_id]):
			return false
	return true


func _complete_quest(p: Player, npc: Npc, quest_id: String) -> void:
	var q: Dictionary = GameData.quests[quest_id]
	var state: Dictionary = p.quests.get(quest_id, {})
	state["completions"] = int(state.get("completions", 0)) + 1
	state["active"] = bool(q.get("repeatable", false))
	p.quests[quest_id] = state
	_npc_say(p, npc, str(q["complete_text"]))
	var reward: Dictionary = q.get("reward", {})
	if int(reward.get("coin", 0)) > 0:
		p.coin += int(reward["coin"])
		say(p, "You receive %s." % format_coin(int(reward["coin"])), C_LOOT)
	var item_id := str(q.get("first_reward_item", ""))
	if state["completions"] == 1 and item_id != "":
		_npc_say(p, npc, str(q.get("first_complete_text", "Take this as well.")))
		p.inventory.append(item_id)  # the offered items just freed at least one slot
		say(p, "--You have received a %s.--" % GameData.item_name(item_id), C_LOOT)
	if int(reward.get("xp", 0)) > 0:
		p.add_xp(int(int(reward["xp"]) * float(cfg("xp_rate", 1.0))))
	apply_faction(p, q.get("faction", {}))
	p.quests_changed.emit()


## How many of each wanted item the player carries (bags plus an open trade),
## capped at what's wanted.
func quest_progress(p: Player, quest_id: String) -> Dictionary:
	var wants: Dictionary = GameData.quests[quest_id]["wants"]
	var out := {}
	for item_id: String in wants:
		out[item_id] = mini(p.inventory.count(item_id) + p.trade_items.count(item_id), int(wants[item_id]))
	return out


func quest_items_ready(p: Player, quest_id: String) -> bool:
	var wants: Dictionary = GameData.quests[quest_id]["wants"]
	var have := quest_progress(p, quest_id)
	for item_id: String in wants:
		if int(have[item_id]) < int(wants[item_id]):
			return false
	return true


# --- zones ------------------------------------------------------------------

## A player stepped into a zone line. Checks they really stand in it, closes
## anything open, and asks whoever owns zones (main today, a zone server later)
## to move them.
func request_zone_line(player_id: int, line_index: int) -> void:
	var p := get_object(player_id) as Player
	if p == null or p.dead or zone == null or zone.zone_line_at(p.global_position) != line_index:
		return
	var zl: Dictionary = zone.data["zone_lines"][line_index]
	request_trade_cancel(player_id)
	request_service_close(player_id)
	request_loot_close(player_id)
	p.auto_attack = false
	p.target = null
	p.sitting = false
	p.hostile_npcs.clear()
	if not p.cast.is_empty():
		request_interrupt(player_id)
	var face: Array = zl.get("arrive_face", zl["arrive"])
	zone_change.emit(p, str(zl["to"]), Vector2(zl["arrive"][0], zl["arrive"][1]), Vector2(face[0], face[1]))


# --- camping (logging out) --------------------------------------------------

## Starts camping: the player sits, and after camp_seconds without standing
## up they leave the world (main saves and shows the character screen).
func request_camp(player_id: int) -> void:
	var p := get_object(player_id) as Player
	if p == null or p.dead or p.camp_left > 0.0:
		return
	request_trade_cancel(player_id)
	request_service_close(player_id)
	request_loot_close(player_id)
	p.auto_attack = false
	request_sit(player_id, true)
	if not p.sitting:
		say(p, "You can't camp right now.", C_WARN)
		return
	p.camp_left = float(cfg("camp_seconds", 20.0))
	say(p, "It will take you about %d seconds to prepare your camp." % int(p.camp_left), C_SYSTEM)


func _update_camp(p: Player, delta: float) -> void:
	if p.dead or not p.sitting:
		p.camp_left = 0.0
		say(p, "You abandon your preparations to camp.", C_WARN)
		return
	p.camp_left -= delta
	if p.camp_left <= 0.0:
		p.camp_left = 0.0
		camped.emit(p)


# --- merchants & bank -------------------------------------------------------

## G on an npc: a merchant opens their shop, a banker the bank, anyone else
## the give window (quest turn-ins).
func request_interact(player_id: int) -> void:
	var p := get_object(player_id) as Player
	if p == null or p.dead:
		return
	var npc := p.valid_target_entity() as Npc
	if npc == null or not (npc.data.has("merchant") or npc.data.get("banker", false) or npc.data.has("guildmaster")):
		request_trade_open(player_id)
		return
	if npc.data.has("guildmaster") and npc.data["guildmaster"]["class"] != p.char_class:
		if p.distance_to(npc) <= TALK_RANGE:
			npc.greet(p)
			_npc_say(p, npc, str(npc.data["guildmaster"].get("refuse", "I can't teach you, {name}.")))
		return
	if p.distance_to(npc) > TALK_RANGE:
		say(p, "You are too far away from %s." % npc.display_name, C_WARN)
		return
	if refuses(p, npc):
		_npc_say(p, npc, str(npc.data.get("refuse_faction", "I'll have nothing to do with the likes of you, {name}.")))
		return
	request_trade_cancel(player_id)
	request_loot_close(player_id)
	request_service_close(player_id)
	p.service_npc_id = npc.entity_id
	p.service = "shop" if npc.data.has("merchant") else ("guild" if npc.data.has("guildmaster") else "bank")
	npc.greet(p)
	if p == local_player:
		service_opened.emit(npc, p.service)


func request_service_close(player_id: int) -> void:
	var p := get_object(player_id) as Player
	if p == null or p.service_npc_id < 0:
		return
	p.service_npc_id = -1
	p.service = ""
	if p == local_player:
		service_closed.emit()


## The npc whose shop or bank this player has open, if still in reach.
func _service_npc(p: Player, kind: String) -> Npc:
	if p.service != kind:
		return null
	var npc := get_object(p.service_npc_id) as Npc
	if npc == null or p.distance_to(npc) > TALK_RANGE:
		request_service_close(p.entity_id)
		return null
	return npc


func _check_service(p: Player) -> void:
	var npc := get_object(p.service_npc_id)
	if npc == null or p.distance_to(npc) > TALK_RANGE:
		say(p, "You walk away from %s." % (npc.display_name if npc != null else "the counter"), C_SYSTEM)
		request_service_close(p.entity_id)


static func item_value(item_id: String) -> int:
	return int(GameData.items.get(item_id, {}).get("value", 0))


## What a merchant pays for one of these.
static func sell_price(npc: Npc, item_id: String) -> int:
	var value := item_value(item_id)
	return 0 if value <= 0 else maxi(1, int(value * float(npc.data["merchant"].get("buy_rate", 0.25))))


## Everything a merchant offers: their own goods (always in stock) plus what
## players have sold them, as [{item, price, count (-1 = unlimited)}].
func merchant_wares(npc: Npc) -> Array:
	var out: Array = []
	for item_id: String in npc.data["merchant"].get("sells", []):
		out.append({"item": item_id, "price": item_value(item_id), "count": -1})
	var extra: Dictionary = merchant_stock.get(npc.npc_id, {})
	for item_id: String in extra:
		if not item_id in npc.data["merchant"].get("sells", []):
			out.append({"item": item_id, "price": item_value(item_id), "count": int(extra[item_id])})
	return out


func request_buy(player_id: int, item_id: String) -> void:
	var p := get_object(player_id) as Player
	if p == null:
		return
	var npc := _service_npc(p, "shop")
	if npc == null:
		return
	var sold_back: Dictionary = merchant_stock.get(npc.npc_id, {})
	var stocked: bool = item_id in npc.data["merchant"].get("sells", []) or int(sold_back.get(item_id, 0)) > 0
	var price := item_value(item_id)
	if not stocked or price <= 0:
		return
	if p.coin < price:
		say(p, "You can't afford the %s." % GameData.item_name(item_id), C_WARN)
		return
	if p.inventory.size() >= int(cfg("inventory_slots", 24)):
		say(p, "Your inventory is full.", C_WARN)
		return
	p.coin -= price
	p.inventory.append(item_id)
	if not item_id in npc.data["merchant"].get("sells", []):
		sold_back[item_id] = int(sold_back[item_id]) - 1
		if sold_back[item_id] <= 0:
			sold_back.erase(item_id)
	say(p, "You buy a %s for %s." % [GameData.item_name(item_id), format_coin(price)], C_LOOT)
	p.inventory_changed.emit()
	if p == local_player:
		service_changed.emit()


func request_sell(player_id: int, inv_index: int) -> void:
	var p := get_object(player_id) as Player
	if p == null or inv_index < 0 or inv_index >= p.inventory.size():
		return
	var npc := _service_npc(p, "shop")
	if npc == null:
		return
	var item_id: String = p.inventory[inv_index]
	var price := sell_price(npc, item_id)
	if price <= 0:
		say(p, "%s isn't interested in that." % npc.display_name, C_WARN)
		return
	p.inventory.remove_at(inv_index)
	p.coin += price
	var stock: Dictionary = merchant_stock.get_or_add(npc.npc_id, {})
	if not item_id in npc.data["merchant"].get("sells", []):
		stock[item_id] = int(stock.get(item_id, 0)) + 1
	say(p, "You sell a %s for %s." % [GameData.item_name(item_id), format_coin(price)], C_LOOT)
	p.inventory_changed.emit()
	if p == local_player:
		service_changed.emit()


func request_bank_deposit(player_id: int, inv_index: int) -> void:
	var p := get_object(player_id) as Player
	if p == null or inv_index < 0 or inv_index >= p.inventory.size() or _service_npc(p, "bank") == null:
		return
	if p.bank_items.size() >= int(cfg("bank_slots", 16)):
		say(p, "Your bank is full.", C_WARN)
		return
	p.bank_items.append(p.inventory[inv_index])
	p.inventory.remove_at(inv_index)
	p.inventory_changed.emit()
	if p == local_player:
		service_changed.emit()


func request_bank_withdraw(player_id: int, bank_index: int) -> void:
	var p := get_object(player_id) as Player
	if p == null or bank_index < 0 or bank_index >= p.bank_items.size() or _service_npc(p, "bank") == null:
		return
	if p.inventory.size() >= int(cfg("inventory_slots", 24)):
		say(p, "Your inventory is full.", C_WARN)
		return
	p.inventory.append(p.bank_items[bank_index])
	p.bank_items.remove_at(bank_index)
	p.inventory_changed.emit()
	if p == local_player:
		service_changed.emit()


## Moves coin between purse and bank; positive deposits, negative withdraws.
func request_bank_coin(player_id: int, amount: int) -> void:
	var p := get_object(player_id) as Player
	if p == null or _service_npc(p, "bank") == null:
		return
	var moved := clampi(amount, -p.bank_coin, p.coin)
	if moved == 0:
		return
	p.coin -= moved
	p.bank_coin += moved
	say(p, "You %s %s." % ["deposit" if moved > 0 else "withdraw", format_coin(absi(moved))], C_LOOT)
	p.inventory_changed.emit()
	if p == local_player:
		service_changed.emit()


# --- guildmasters -----------------------------------------------------------

## Spells a class can learn, cheapest first: [{spell, level, cost}].
static func class_spells(class_id: String) -> Array:
	var out: Array = []
	for spell_id: String in GameData.spells:
		var s: Dictionary = GameData.spells[spell_id]
		if s.get("classes", {}).has(class_id):
			out.append({"spell": spell_id, "level": int(s["classes"][class_id]), "cost": int(s.get("cost", 0))})
	out.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return a["level"] < b["level"])
	return out


## Why this player can't learn a spell right now, or "" if they can.
func train_block(p: Player, spell_id: String) -> String:
	var s: Dictionary = GameData.spells.get(spell_id, {})
	var need: Variant = s.get("classes", {}).get(p.char_class)
	if need == null:
		return "Not for your class."
	if spell_id in p.spells:
		return "Known."
	if p.level < int(need):
		return "Requires level %d." % int(need)
	if p.coin < int(s.get("cost", 0)):
		return "You can't afford it."
	if p.spells.size() >= int(cfg("max_spells", 8)):
		return "You can't remember any more spells."
	return ""


func request_train(player_id: int, spell_id: String) -> void:
	var p := get_object(player_id) as Player
	if p == null:
		return
	var npc := _service_npc(p, "guild")
	if npc == null:
		return
	var why := train_block(p, spell_id)
	if why != "":
		say(p, why, C_WARN)
		return
	var s: Dictionary = GameData.spells[spell_id]
	p.coin -= int(s.get("cost", 0))
	p.spells.append(spell_id)
	say(p, "%s teaches you %s. (Key %d)" % [npc.display_name, s["name"], p.spells.size()], C_XP)
	p.inventory_changed.emit()
	p.stats_changed.emit()
	if p == local_player:
		service_changed.emit()


# --- faction ----------------------------------------------------------------

func faction_name(faction_id: String) -> String:
	return str(GameData.factions.get(faction_id, {}).get("name", faction_id))


## A player's standing with a faction (its default until it changes).
func standing(p: Player, faction_id: String) -> int:
	if not GameData.factions.has(faction_id):
		return 0
	return int(p.factions.get(faction_id, GameData.factions[faction_id].get("default", 0)))


## [min standing, label, how an NPC of that faction regards you]
static func standing_tier(value: int) -> Array:
	for tier: Array in STANDING_TIERS:
		if value >= tier[0]:
			return tier
	return STANDING_TIERS[-1]


## Shifts standings, e.g. {"watch": 5, "gnolls": -10}, with EQ's messages.
func apply_faction(p: Player, hits: Dictionary) -> void:
	for faction_id: String in hits:
		if not GameData.factions.has(faction_id):
			continue
		var before := standing(p, faction_id)
		var after := clampi(before + int(hits[faction_id]), -FACTION_MAX, FACTION_MAX)
		var name := faction_name(faction_id)
		if after == before:
			say(p, "Your faction standing with %s could not possibly get any %s." % [name, "better" if int(hits[faction_id]) > 0 else "worse"], C_SYSTEM)
			continue
		p.factions[faction_id] = after
		say(p, "Your faction standing with %s has gotten %s." % [name, "better" if after > before else "worse"], C_SYSTEM)
	p.stats_changed.emit()


## Townsfolk won't talk, trade or train with someone they think Dubious or worse.
func refuses(p: Player, npc: Npc) -> bool:
	return GameData.factions.has(npc.faction) and standing(p, npc.faction) < REFUSE_BELOW


## Whether mobs of this faction attack the player on sight (their "kos_at").
func mob_kos(p: Player, faction_id: String) -> bool:
	var f: Dictionary = GameData.factions.get(faction_id, {})
	return f.has("kos_at") and standing(p, faction_id) <= int(f["kos_at"])


## Whether an NPC faction's guards attack the player on sight.
func npc_kos(p: Player, faction_id: String) -> bool:
	return GameData.factions.has(faction_id) and standing(p, faction_id) < KOS_BELOW


## The player chose to attack an NPC: it fights back, guards come running,
## and the NPC's faction (and its friends) think less of them.
func declare_hostile(p: Player, npc: Npc) -> void:
	p.hostile_npcs[npc.entity_id] = true
	p.attack_confirm_id = -1
	apply_faction(p, GameData.factions.get(npc.faction, {}).get("on_attack", {}))
	npc.fight(p)
	call_guards(npc, p)


## Guards near a townsperson under attack join the fight.
func call_guards(victim: Npc, attacker: Entity) -> void:
	for obj: Node3D in objects.values():
		var n := obj as Npc
		if n != null and n != victim and not n.dead and not n.guard.is_empty() and not n.auto_attack \
				and n.distance_to(victim) < 45.0:
			n.fight(attacker, true)
