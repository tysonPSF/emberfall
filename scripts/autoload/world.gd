extends Node
## Authoritative game rules: object registry, combat, spells, XP, death, loot.
##
## Everything that changes game state goes through here. Player input only
## calls the request_* functions, passing ids rather than node references.
## On a client (see the Net autoload) every request_* is sent to the server
## instead, and the rules below run only there; clients render the results.

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
signal group_invited(from_name: String)  # "" closes the invite window
signal shot_fired(from: Entity, to: Entity, projectile: String)
signal spell_fx(caster: Entity, target: Entity, spell_id: String)  # a spell landed: for its look (SpellFx)  # a ranged attack, for the flight effect

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
const C_CHAT_SAY := Color(0.93, 0.93, 0.9)
const C_CHAT_SHOUT := Color(1.0, 0.5, 0.42)
const C_CHAT_OOC := Color(0.5, 0.95, 0.55)
const C_CHAT_TELL := Color(0.95, 0.6, 0.95)
const C_CHAT_GROUP := Color(0.55, 0.78, 1.0)
const SAY_RANGE := 45.0
const CHAT_MAX := 240
const CHAT_HELP := "Chat: just type to /say.  /shout (zone)  /ooc (everyone)  /tell <name> <msg>  /r <msg> (reply)  /who  /who all  /lfg  /random [max]  /loc  /camp\nGroups: /invite [name]  /accept  /decline  /g <msg>  /disband  /kick <name>  /makeleader <name>  /assist [name]  /follow  (F2-F6 target members)"
const GROUP_MAX := 6
const GROUP_XP_BONUS := 0.1  # per extra member who shares the kill
const LOOT_RIGHTS_SECONDS := 180.0
const INVITE_SECONDS := 60.0

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
const EQUIP_SLOTS: Array[String] = ["primary", "secondary", "range", "head", "neck", "arms", "hands", "chest", "waist", "legs", "feet", "ring1", "ring2"]
## Item "slot" values that fit more than one equipment slot.
const SLOT_FITS := {"ring": ["ring1", "ring2"]}

var objects: Dictionary = {}  # id -> Entity or Corpse
var next_id := 1
var local_player: Player = null
var zone: Zone = null
var tick_timer := 0.0
var merchant_stock: Dictionary = {}  # merchant npc id -> {item id: count} bought from players
var groups: Dictionary = {}  # group id -> {leader: player id, members: [player ids]}
var _next_group := 1
var _group_view_timer := 0.0


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


## The zone a node is in. A server runs several at once, each in its own
## physics world, so "where" always means "in which zone" first.
func zone_of(n: Node) -> Zone:
	while n != null and not (n is Zone):
		n = n.get_parent()
	return n as Zone


func cfg(key: String, default: Variant = null) -> Variant:
	return GameData.config.get(key, default)


func melee_range() -> float:
	return float(cfg("melee_range", 3.4))


# --- messages ---------------------------------------------------------------

## Sends a chat-log line to one player: this machine's own log, or over the
## network to theirs.
func say(to: Entity, text: String, color: Color = C_SYSTEM) -> void:
	if to == null:
		return
	if to == local_player:
		log_message.emit(text, color)
	elif to is Player:
		Net.send_say(to as Player, text, color)


## Fires one of the HUD signals above for one player's windows, here or on
## their own machine.
func _ui(p: Player, sig: StringName, args: Array = []) -> void:
	if p == null:
		return
	if p == local_player:
		emit_signal.callv([sig] + args)
	else:
		Net.send_ui(p, sig, args)


## On a client, sends a request to the server instead of running it here.
func _remote(method: StringName, args: Array) -> bool:
	if Net.is_authority():
		return false
	Net.send_request(method, args)
	return true


## Says something out loud: every player within earshot sees it.
func shout(from: Node3D, text: String, color: Color = C_NPC, radius := 60.0) -> void:
	for p in get_players():
		if p.distance_to(from) <= radius:
			say(p, text, color)


## "Sling Stone" -> "Sling Stones" (names already plural, like Rat Whiskers, stay).
static func plural(item_name: String) -> String:
	return item_name if item_name.ends_with("s") else item_name + "s"


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
	if not Net.is_authority():
		_client_timers(delta)
		return
	_group_view_timer += delta
	if _group_view_timer >= 0.2:
		_group_view_timer = 0.0
		_update_group_views()
		_update_threat()
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
		if obj is Player and is_instance_valid(obj):
			_update_stamina(obj, delta)
	tick_timer += delta
	if tick_timer >= float(cfg("tick_seconds", 6.0)):
		tick_timer = 0.0
		_regen_tick()


## A client runs no rules, but counts down its own cast bar and recast timers
## between the server's updates so they move smoothly.
func _client_timers(delta: float) -> void:
	var p := local_player
	if p == null:
		return
	if not p.cast.is_empty():
		p.cast["time"] = minf(float(p.cast["time"]) + delta, float(p.cast["total"]))
	for key: String in p.cooldowns.keys():
		p.cooldowns[key] = maxf(0.0, float(p.cooldowns[key]) - delta)


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
		if e is Player and Time.get_ticks_msec() >= int(e.get_meta("range_warn_at", 0)):
			e.set_meta("range_warn_at", Time.get_ticks_msec() + 2500)
			say(e, "Your target is too far away, get closer!", C_WARN)
		return
	if e.swing_timer > 0.0:
		return
	e.swing_timer = e.attack_delay
	e.sitting = false
	e.animate("attack")
	_notice_attacker(t, e)
	if t is Player:
		var avoided := _try_avoid(t as Player, e)
		if avoided != "":
			_avoid_msg(e, t as Player, avoided)
			return
	var chance := 0.72 + (e.level - t.level) * 0.04 - t.ac * 0.004
	if e is Player:  # weapon skill and offense against 80% of cap
		var p := e as Player
		chance += 0.12 * ((skill_frac(p, weapon_skill(p)) + skill_frac(p, "offense")) * 0.5 - _neutral())
		try_skill_up(p, weapon_skill(p), t)
		try_skill_up(p, "offense", t, 0.5)
	if t is Player:
		chance -= 0.12 * (skill_frac(t as Player, "defense") - _neutral())
		try_skill_up(t as Player, "defense", e, 0.5)
	chance = clampf(chance, 0.12, 0.95)
	var dmg := randi_range(e.dmg_min, e.dmg_max) if randf() < chance else 0
	if dmg > 0 and e is Player:
		dmg = maxi(1, dmg + roundi(dmg * 0.3 * (skill_frac(e as Player, weapon_skill(e as Player)) - _neutral())))
	_combat_msg(e, t, e.attack_verb, dmg)
	if dmg > 0:
		damage(t, dmg, e)
		_try_proc(e, t)


## Which players a living monster hates right now: the combat music follows it.
func _update_threat() -> void:
	var hated := {}
	for m in get_mobs():
		if not m.dead:
			for id: int in m.hate:
				hated[id] = true
	for p in get_players():
		p.threatened = hated.has(p.entity_id) and not p.dead


# --- skills -----------------------------------------------------------------

func _neutral() -> float:
	return float(GameData.skills["tuning"]["neutral"])


func skill_cap(p: Player, id: String) -> int:
	return GameData.skill_cap(p.char_class, id, p.level)


func skill_value(p: Player, id: String) -> int:
	return mini(int(p.skills.get(id, 0)), skill_cap(p, id))


## A skill as a share of its cap (0 when the class can't learn it). Effects
## are measured against the "neutral" share, where the base rules apply as is.
func skill_frac(p: Player, id: String) -> float:
	var cap := skill_cap(p, id)
	return 0.0 if cap <= 0 else float(skill_value(p, id)) / cap


## The skill a player's weapon trains (hand to hand when empty-handed).
func weapon_skill(p: Player) -> String:
	return str(GameData.item(p.equipment.get("primary", "")).get("skill", "hand_to_hand"))


## Using a skill may raise it, less likely the closer it is to the cap. Gray
## targets teach nothing, as in EQ; `rate` scales the chance for skills that
## would otherwise rise on every swing (offense, defense, the avoidances).
func try_skill_up(p: Player, id: String, against: Entity = null, rate := 1.0) -> void:
	if p == null or p.dead:
		return
	if against != null and against != p and con_of(p.level, against.level) == Con.GRAY:
		return
	var cap := skill_cap(p, id)
	var cur := skill_value(p, id)
	if cap <= 0 or cur >= cap:
		return
	var t: Dictionary = GameData.skills["tuning"]
	var chance := (float(t["up_base"]) * pow(1.0 - float(cur) / cap, float(t["up_curve"])) + float(t["up_floor"])) * rate
	if randf() < chance:
		p.skills[id] = cur + 1
		say(p, "You have become better at %s! (%d)" % [GameData.skill_name(id), cur + 1], C_XP)


## A spell from one of the schools can fizzle when the school skill is low:
## part of the mana is lost and the skill may still improve.
func _fizzles(p: Player, s: Dictionary) -> bool:
	var school := str(s.get("skill", ""))
	if s.get("ability", false) or not school in ["evocation", "alteration", "abjuration"]:
		return false
	var chance := maxf(0.0, 0.15 * (1.0 - skill_frac(p, school)))
	if randf() >= chance:
		return false
	p.mana -= int(s.get("mana", 0)) / 3
	say(p, "Your spell fizzles!", C_WARN)
	try_skill_up(p, school)
	p.stats_changed.emit()
	return true


## A caster who takes a hit may lose the spell; channeling holds it.
func _channel(p: Player) -> void:
	if skill_cap(p, "channeling") <= 0:
		p.cast = {}
		say(p, "Your spell is interrupted.", C_WARN)
		return
	try_skill_up(p, "channeling")
	if randf() < clampf(0.4 - 0.35 * skill_frac(p, "channeling"), 0.05, 0.4):
		p.cast = {}
		say(p, "Your spell is interrupted.", C_WARN)
	else:
		say(p, "You regain your concentration and continue your casting.", C_SPELL)


## Block (with a shield), parry (with a weapon) and dodge: a player's chance
## to avoid a swing outright. Returns the skill that did it, or "".
func _try_avoid(p: Player, attacker: Entity) -> String:
	var options := [["block", 0.1, GameData.item(p.equipment.get("secondary", "")).get("slot", "") == "secondary"],
			["parry", 0.08, p.equipment.has("primary")], ["dodge", 0.07, true]]
	for o: Array in options:
		if not o[2] or skill_cap(p, o[0]) <= 0:
			continue
		try_skill_up(p, o[0], attacker, 0.4)
		if randf() < float(o[1]) * skill_frac(p, o[0]):
			return o[0]
	return ""


func _avoid_msg(a: Entity, p: Player, how: String) -> void:
	say(p, "%s tries to %s YOU, but YOU %s!" % [cap(a.display_name), a.attack_verb[0], how], C_MISS)
	if a is Player:
		say(a, "You try to %s %s, but %s %ss!" % [a.attack_verb[0], p.display_name, p.display_name, how], C_MISS)


## The weapon an entity swings: a player's primary, or what a mob spawned holding.
static func weapon_item(e: Entity) -> Dictionary:
	if e is Player:
		return GameData.item((e as Player).equipment.get("primary", ""))
	if e is Mob:
		return GameData.item((e as Mob).gear.get("primary", ""))
	return {}


## A weapon's "proc": {spell, chance} sometimes fires its spell on a hit, free.
func _try_proc(e: Entity, t: Entity) -> void:
	var proc: Dictionary = weapon_item(e).get("proc", {})
	var natural := proc.is_empty() and e is Mob  # a monster's own: a spider's venom, a shaman's bolt
	if natural:
		proc = (e as Mob).data.get("proc", {})
	if proc.is_empty() or t.dead or randf() >= float(proc.get("chance", 0.0)):
		return
	var spell_id := str(proc["spell"])
	if not GameData.spells.has(spell_id):
		return
	if natural:
		say(t, str(proc.get("text", "%s's attack carries %s!")) % [cap(e.display_name), GameData.spells[spell_id]["name"]], C_HIT_YOU)
	else:
		say(e, "Your %s flares with power!" % weapon_item(e)["name"], C_SPELL)
	_finish_spell(e, spell_id, t, true)


## Right-clicking an equipped item with a "click": {spell, recast} casts that
## spell for free, then the item needs recast seconds to recharge.
func request_item_click(player_id: int, slot: String) -> void:
	if _remote(&"request_item_click", [player_id, slot]):
		return
	var p := get_object(player_id) as Player
	if p == null or p.dead or not p.equipment.has(slot):
		return
	var item_id: String = p.equipment[slot]
	var it := GameData.item(item_id)
	var click: Dictionary = it.get("click", {})
	if click.is_empty() or not GameData.spells.has(str(click["spell"])):
		say(p, "The %s has no effect you can use." % it["name"], C_WARN)
		return
	var key := "item:" + GameData.base_item(item_id)
	if p.cooldowns.has(key):
		say(p, "The %s is recharging. Ready in %ds." % [it["name"], ceili(float(p.cooldowns[key]))], C_WARN)
		return
	var s: Dictionary = GameData.spells[click["spell"]]
	var t := _resolve_spell_target(p, s)
	if t == null:
		say(p, "You must first select a target for that.", C_WARN)
		return
	if t != p and p.distance_to(t) > float(s.get("range", 0)):
		say(p, "Your target is out of range, get closer!", C_WARN)
		return
	p.cooldowns[key] = float(click.get("recast", 60))
	say(p, "You activate your %s." % it["name"], C_SPELL)
	_finish_spell(p, str(click["spell"]), t, true)


func _combat_msg(a: Entity, d: Entity, verb: Array, dmg: int) -> void:
	if a is Player:
		if dmg > 0:
			say(a, "You %s %s for %d points of damage." % [verb[0], d.display_name, dmg], C_YOU_HIT)
		else:
			say(a, "You try to %s %s, but miss!" % [verb[0], d.display_name], C_MISS)
	if d is Player:
		if dmg > 0:
			say(d, "%s %s YOU for %d points of damage." % [cap(a.display_name), verb[1], dmg], C_HIT_YOU)
		else:
			say(d, "%s tries to %s YOU, but misses!" % [cap(a.display_name), verb[0]], C_MISS)


func damage(d: Entity, amount: int, src: Entity) -> void:
	if d.dead:
		return
	d.hp -= amount
	d.sitting = false
	if d is Player and not d.cast.is_empty() and amount > 0 and src != d:
		_channel(d as Player)
	if d is Mob and src is Player:  # kill credit goes to whoever did the most
		var by: Dictionary = d.get_meta("damage_by", {})
		by[src.entity_id] = int(by.get(src.entity_id, 0)) + amount
		d.set_meta("damage_by", by)
	if src != null:
		d.add_hate(src, float(amount))
		_notice_attacker(d, src)
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
			var rest := float(2 + e.level / 2) if e.sitting else 0.0
			if e is Player and e.sitting and skill_cap(e as Player, "meditate") > 0:  # meditate: better rest
				rest *= 0.5 + 0.625 * skill_frac(e as Player, "meditate")
				if e.mana < e.max_mana:
					try_skill_up(e as Player, "meditate")
			mana_gain = e.mana_regen + int(round(rest))
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
	if killer is Player and GameData.factions.has(d.faction) and not (d is Mob):
		apply_faction(killer, GameData.factions[d.faction].get("on_kill", {}))  # mobs: the credited group, in _kill_mob
	if d is Npc:
		for pl in get_players():
			pl.hostile_npcs.erase(d.entity_id)
	if d is Mob:
		_kill_mob(d, killer)
	elif d is Player:
		_kill_player(d, killer)
	elif d is Npc:
		for p in get_players():
			if p.distance_to(d) < 60.0:
				say(p, "%s has been slain by %s!" % [d.display_name, killer.display_name if killer != null else "unknown forces"], C_WARN)
		(d as Npc).on_killed()


func _kill_mob(mob: Mob, killer: Entity) -> void:
	for p in get_players():
		if p == killer:
			say(p, "You have slain %s!" % mob.display_name, C_XP)
		elif p.distance_to(mob) < 40.0:
			var by := killer.display_name if killer != null else "unknown forces"
			say(p, "%s has been slain by %s!" % [cap(mob.display_name), by], C_SYSTEM)
	var credited := _kill_credit(mob, killer)
	_award_group(credited, mob)

	var entries: Array = []
	for slot: String in mob.gear:  # what it was wearing comes off with it
		entries.append({"item": mob.gear[slot], "slot": ""})
	for entry: Dictionary in mob.data.get("loot", []):
		if randf() < float(entry["chance"]):
			var n: Array = entry.get("count", [1, 1])  # a stack: a quiver's worth of arrows, say
			entries.append({"item": entry["item"], "slot": "", "count": randi_range(int(n[0]), int(n[1]))})
	var coin_range: Array = mob.data.get("coin", [0, 0])
	var coin := randi_range(int(coin_range[0]), int(coin_range[1]))
	var lodged: Dictionary = mob.get_meta("lodged_ammo", {})  # arrows and stones that hit and stayed in
	for ammo_id: String in lodged:
		entries.append({"item": ammo_id, "slot": "", "count": int(lodged[ammo_id])})
	var empty := entries.is_empty() and coin == 0
	var decay := float(cfg("empty_corpse_decay_seconds" if empty else "mob_corpse_decay_seconds", 60))

	var corpse := Corpse.new()
	corpse.setup(mob.display_name, mob.look, entries, coin, decay)
	corpse.position = mob.global_position
	corpse.rotation.y = mob.rotation.y
	if credited != null:
		corpse.rights = group_members(credited).map(func(m: Player) -> String: return m.display_name)
		corpse.rights_until = Time.get_ticks_msec() + int(LOOT_RIGHTS_SECONDS * 1000)
	zone_of(mob).add_child(corpse)

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
	if not p.cursor.is_empty():
		_stow(p)
	if cfg("corpse_runs", true) and (not p.pack.is_empty() or not p.equipment.is_empty() or p.coin > 0):
		var entries: Array = []
		for slot: String in p.equipment:
			entries.append({"item": p.equipment[slot], "slot": slot})
		for e: Dictionary in p.pack.slots:  # bags go on the corpse with their contents
			if not e.is_empty():
				var copy := e.duplicate(true)
				copy["slot"] = ""
				entries.append(copy)
		var corpse := Corpse.new()
		corpse.setup(p.display_name, p.look, entries, p.coin,
				float(cfg("player_corpse_decay_seconds", 3600)), p.display_name)
		corpse.position = p.global_position
		zone_of(p).add_child(corpse)
		p.equipment.clear()
		p.pack.clear()
		p.coin = 0
		p.recalc_stats()
		p.inventory_changed.emit()
		say(p, "Your belongings remain on your corpse. Go back and loot it.", C_WARN)
	p.on_death()
	_ui(p, &"player_died", [p])
	get_tree().create_timer(float(cfg("respawn_delay", 4.0))).timeout.connect(p.respawn)


## The player whose group earned a kill: the one who did the most damage,
## or the killer if no player hurt it at all.
func _kill_credit(mob: Mob, killer: Entity) -> Player:
	var best: Player = killer as Player
	var most := 0
	var by: Dictionary = mob.get_meta("damage_by", {})
	for id: int in by:
		var p := get_object(id) as Player
		if p != null and int(by[id]) > most:
			best = p
			most = int(by[id])
	return best


## EQ group experience: members in the kill's zone who are within level range
## of the group's highest share it, weighted by level, with a small bonus per
## extra member; nothing if the mob is gray to the highest. They also take the
## faction hits.
func _award_group(credited: Player, mob: Mob) -> void:
	if credited == null:
		return
	var here := zone_of(mob)
	var members := group_members(credited).filter(func(m: Player) -> bool: return zone_of(m) == here and not m.dead)
	if members.is_empty():
		members = [credited]
	var top := 0
	for m: Player in members:
		top = maxi(top, m.level)
	var eligible := members.filter(func(m: Player) -> bool: return top - m.level <= maxi(3, top / 3))
	if GameData.factions.has(mob.faction):
		for m: Player in eligible:
			apply_faction(m, GameData.factions[mob.faction].get("on_kill", {}))
	if con_of(top, mob.level) == Con.GRAY:
		return
	var base := float(cfg("xp_base", 10)) + mob.level * mob.level * float(cfg("xp_per_mob_level_sq", 5))
	var total := base * float(cfg("xp_rate", 1.0)) * float(mob.data.get("xp_bonus", 1.0)) * (1.0 + GROUP_XP_BONUS * (eligible.size() - 1))
	var level_sum := 0
	for m: Player in eligible:
		level_sum += m.level
	for m: Player in eligible:
		m.add_xp(maxi(1, int(total * m.level / level_sum)), eligible.size() > 1)


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
	if _remote(&"request_set_target", [entity_id, target_id]):
		return
	var e := get_object(entity_id) as Entity
	if e != null:
		e.target = get_object(target_id) if target_id >= 0 else null


func request_toggle_attack(entity_id: int) -> void:
	if _remote(&"request_toggle_attack", [entity_id]):
		return
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


## Fires the ranged weapon at the target, EQ style: a bow shoots arrows from
## the pack, a sling throws stones. Hit or miss, the target notices who did it,
## which is what pulling is: one mob comes to you from well outside melee range.
func request_ranged(player_id: int) -> void:
	if _remote(&"request_ranged", [player_id]):
		return
	var p := get_object(player_id) as Player
	if p == null or p.dead:
		return
	var weapon := GameData.item(str(p.equipment.get("range", "")))
	if weapon.is_empty():
		say(p, "You have no ranged weapon equipped.", C_WARN)
		return
	var t := p.valid_target_entity()
	if not can_attack(p, t):
		say(p, "You need to target something you can attack.", C_WARN)
		return
	if not p.cast.is_empty():
		say(p, "You can't do that while casting.", C_WARN)
		return
	if p.cooldowns.has("ranged"):
		return  # still nocking the next arrow
	if p.distance_to(t) > float(weapon.get("range", 30.0)):
		say(p, "Your target is out of range.", C_WARN)
		return
	if not in_sight(p, t):
		say(p, "You can't see your target from here.", C_WARN)
		return
	var ammo_id := ""
	if weapon.has("ammo"):
		ammo_id = _ammo_for(p, str(weapon["ammo"]))
		if ammo_id == "":
			say(p, "You are out of %s." % str(weapon.get("ammo_name", "ammunition")), C_WARN)
			return
		p.pack.remove(ammo_id, 1)
		p.inventory_changed.emit()
	var delay := float(weapon.get("delay", 3.0)) / (1.0 + minf(int(p.attributes.get("haste", 0)), 40) / 100.0)
	p.cooldowns["ranged"] = delay
	p.sitting = false
	p.animate("attack")
	var ammo := GameData.item(ammo_id)
	shot_fired.emit(p, t, str(ammo.get("projectile", weapon.get("projectile", "stone"))))
	Net.broadcast_shot(p, t, str(ammo.get("projectile", weapon.get("projectile", "stone"))))
	var skill := str(weapon.get("skill", "archery"))
	var chance := 0.72 + (p.level - t.level) * 0.04 - t.ac * 0.004
	chance += 0.12 * ((skill_frac(p, skill) + skill_frac(p, "offense")) * 0.5 - _neutral())
	try_skill_up(p, skill, t)
	if t is Player:
		chance -= 0.12 * (skill_frac(t as Player, "defense") - _neutral())
	chance = clampf(chance, 0.12, 0.95)
	var base := (int(weapon.get("dmg", 1)) + int(ammo.get("dmg", 0))) * p.item_effectiveness(weapon)
	var lo := 1 + p.level / 4
	var hi := maxi(lo + 1, int((base * 2.0 + p.level) * float(GameData.classes[p.char_class]["melee_skill"])) + int(p.attributes.get("str", 0)) / 5)
	var dmg := randi_range(lo, hi) if randf() < chance else 0
	if dmg > 0:
		dmg = maxi(1, dmg + roundi(dmg * 0.3 * (skill_frac(p, skill) - _neutral())))
	_combat_msg(p, t, weapon.get("verb", ["shoot", "shoots"]), dmg)
	if dmg > 0:
		if ammo_id != "" and t is Mob and randf() < float(cfg("ammo_recover_chance", 0.15)):
			var lodged: Dictionary = t.get_meta("lodged_ammo", {})  # stays in the mob; found on its corpse
			lodged[ammo_id] = int(lodged.get(ammo_id, 0)) + 1
			t.set_meta("lodged_ammo", lodged)
		damage(t, dmg, p)
	else:
		t.add_hate(p, 1.0)  # a miss still gets its attention
		_notice_attacker(t, p)


func has_shield(p: Player) -> bool:
	return bool(GameData.item(str(p.equipment.get("secondary", ""))).get("shield", false))


## Being attacked turns you toward it, so you can fight back at once: with
## nothing hostile targeted (nothing, yourself, a friend, a corpse), whoever
## swings, shoots or casts at you becomes your target. A fight you already
## picked keeps its target.
func _notice_attacker(d: Entity, a: Entity) -> void:
	if not (d is Player) or a == null or a == d or a.dead or d.dead:
		return
	var cur := d.valid_target_entity()
	if cur != null and cur != d and can_attack(d, cur):
		return
	d.target = a


## The first ammunition of a kind ("arrow", "stone") carried anywhere in the pack.
func _ammo_for(p: Player, kind: String) -> String:
	for e: Dictionary in p.pack.entries():
		if str(GameData.item(e["item"]).get("ammo_type", "")) == kind:
			return str(e["item"])
	return ""


## Whether terrain, trees or buildings stand between two entities (chest height).
func in_sight(a: Entity, b: Entity) -> bool:
	if zone_of(a) != zone_of(b):
		return false
	var q := PhysicsRayQueryParameters3D.create(a.global_position + Vector3.UP * 1.3, b.global_position + Vector3.UP * 0.6, Layers.WORLD)
	return a.get_world_3d().direct_space_state.intersect_ray(q).is_empty()


## Sprinting is a held state rather than a toggle: input asks for it every frame
## it wants it, and anything here can refuse or end it.
func request_sprint(entity_id: int, on: bool) -> void:
	if _remote(&"request_sprint", [entity_id, on]):
		return
	var p := get_object(entity_id) as Player
	if p == null or p.dead:
		return
	# You may run a burst down to nothing, but you cannot start again on fumes:
	# without this, holding Shift while spent re-engages the moment a sliver of
	# stamina returns, which stutters your speed and repeats the winded message.
	if on and (p.sitting or p.stamina < float(cfg("sprint_resume_at", 25.0))):
		return
	p.sprinting = on


## Drains while you run, and creeps back after you have been off it a moment.
## How long a run lasts is `max_stamina`, which recalc_stats builds from config,
## level, gear and deity - so lengthening it later is a data change, not a code
## one. The numbers live in data/config.json.
func _update_stamina(p: Player, delta: float) -> void:
	if p.dead:
		p.sprinting = false
		return
	if p.sprinting:
		p.stamina_idle = float(cfg("stamina_regen_delay", 1.5))
		p.stamina = maxf(0.0, p.stamina - float(cfg("sprint_drain", 20.0)) * delta)
		if p.stamina <= 0.0:
			p.sprinting = false
			say(p, "You are too winded to keep running.", C_WARN)
		return
	p.stamina_idle = maxf(0.0, p.stamina_idle - delta)
	if p.stamina_idle <= 0.0:
		var regen := float(cfg("stamina_regen", 8.0)) * delta
		p.stamina = minf(float(p.max_stamina), p.stamina + regen)


func request_sit(entity_id: int, sit: bool) -> void:
	if _remote(&"request_sit", [entity_id, sit]):
		return
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
	if _remote(&"request_consider", [entity_id]):
		return
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
	if _remote(&"request_cast", [entity_id, spell_id]):
		return
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
	if s.get("requires", "") == "shield" and c is Player and not has_shield(c as Player):
		say(c, "You need a shield equipped to %s." % str(s["name"]).to_lower(), C_WARN)
		return
	var t := _resolve_spell_target(c, s)
	if t == null:
		say(c, "You must first select a target for this spell!", C_WARN)
		return
	if t != c and c.distance_to(t) > float(s.get("range", 0)):
		say(c, "Your target is out of range, get closer!", C_WARN)
		return
	c.sitting = false
	if c is Player and _fizzles(c as Player, s):
		return
	if float(s.get("cast_time", 0)) <= 0.0:
		_finish_spell(c, spell_id, t)
		return
	c.cast = {"spell": spell_id, "target_id": t.entity_id, "time": 0.0,
			"total": float(s["cast_time"]), "start_pos": c.global_position}
	say(c, "You begin casting %s." % s["name"], C_SPELL)


func request_interrupt(entity_id: int) -> void:
	if _remote(&"request_interrupt", [entity_id]):
		return
	var c := get_object(entity_id) as Entity
	if c != null and not c.cast.is_empty():
		c.cast = {}
		say(c, "Your spell is interrupted.", C_WARN)


func _resolve_spell_target(c: Entity, s: Dictionary) -> Entity:
	var t := c.valid_target_entity()
	match str(s.get("target", "enemy")):
		"self", "group":
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


## Lands a spell. Spells from gear (procs, clicks) cost no mana and leave the
## caster's own recast timer alone.
func _finish_spell(c: Entity, spell_id: String, t: Entity, from_item := false) -> void:
	var s: Dictionary = GameData.spells[spell_id]
	if not from_item:
		c.mana -= int(s.get("mana", 0))
		c.cooldowns[spell_id] = float(s.get("recast", 0))
	var power := randi_range(int(s.get("min", 0)), int(s.get("max", 0))) + int(float(s.get("per_level", 0)) * (c.level - 1))
	if c is Player and not from_item and s.has("skill"):
		var skill := str(s["skill"])
		if s.get("ability", false) and skill != "taunt":  # kick, bash, bind wound grow with the skill
			power = maxi(1, roundi(power * (0.6 + 0.5 * skill_frac(c as Player, skill))))
		try_skill_up(c as Player, skill, t if s.get("ability", false) and t != c else null)
	if str(s.get("target", "")) == "group" and c is Player:  # every member in range, the caster too
		for m: Player in group_members(c as Player):
			if not m.dead and (m == c or c.distance_to(m) <= float(s.get("range", 30))):
				_land(c, spell_id, m, s, power)
		return
	_land(c, spell_id, t, s, power)


## One spell's effect on one target.
func _land(c: Entity, spell_id: String, t: Entity, s: Dictionary, power: int) -> void:
	spell_fx.emit(c, t, spell_id)
	Net.broadcast_fx(c, t, spell_id)
	match str(s["type"]):
		"damage":
			if s.get("ability", false):
				c.animate(str(s.get("anim", "attack")))  # a kick, a bash, or a swing
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
			c.global_position = zone_of(c).bind_point + Vector3.UP
			c.velocity = Vector3.ZERO
			if c is Player:
				Net.teleport(c as Player, c.global_position)
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
			say(c, str(s.get("dot_text", "%s begins to smolder.")) % cap(t.display_name), C_SPELL)
			if s.has("land_text"):
				say(t, str(s["land_text"]), C_HIT_YOU)
			t.add_hate(c, float(per_tick))
		"root":
			t.root_left = float(s.get("duration", 10))
			say(c, "%s's feet adhere to the ground." % cap(t.display_name), C_SPELL)
			t.add_hate(c, 5.0)
		"taunt":
			if c is Player and randf() > 0.5 + 0.5 * skill_frac(c as Player, "taunt"):
				say(c, "Your taunt fails to get %s's attention." % t.display_name, C_WARN)
				return
			var top := 0.0
			for v: float in t.hate.values():
				top = maxf(top, v)
			t.add_hate(c, top + 10.0 - float(t.hate.get(c.entity_id, 0.0)))
			say(c, "You taunt %s to ignore others and attack you!" % t.display_name, C_SPELL)
	c.stats_changed.emit()


func call_for_help(caller: Mob, enemy: Entity) -> void:
	for m in get_mobs():
		if m != caller and not m.dead and m.faction == caller.faction and m.hate.is_empty() \
				and m.distance_to(caller) <= CALL_FOR_HELP_RADIUS:
			m.add_hate(enemy, 1.0)


# --- loot & inventory -------------------------------------------------------

func request_loot_open(player_id: int, corpse_id: int) -> void:
	if _remote(&"request_loot_open", [player_id, corpse_id]):
		return
	var p := get_object(player_id) as Player
	var c := get_object(corpse_id) as Corpse
	if p == null or c == null or p.dead:
		return
	if p.distance_to(c) > LOOT_RANGE:
		say(p, "You are too far away to loot that corpse.", C_WARN)
		return
	request_trade_cancel(player_id)
	if c.owner_name != "" and c.owner_name != p.display_name:
		say(p, "You may not loot this corpse.", C_WARN)
		return
	if not c.rights.is_empty() and Time.get_ticks_msec() < c.rights_until and not p.display_name in c.rights:
		say(p, "You may not loot this corpse yet.", C_WARN)
		return
	if c.coin > 0:
		_split_coin(p, c.coin)
		c.coin = 0
	if c.entries.is_empty():
		say(p, "The corpse is empty.")
		remove_corpse(c)
		return
	_ui(p, &"loot_opened", [c])


## Coin from a corpse is shared with the looter's group in the same zone; the
## looter keeps whatever doesn't divide evenly.
func _split_coin(p: Player, coin: int) -> void:
	var here := zone_of(p)
	var members := group_members(p).filter(func(m: Player) -> bool: return zone_of(m) == here)
	var share := coin / members.size()
	for m: Player in members:
		var amount := share + (coin % members.size() if m == p else 0)
		if amount <= 0:
			continue
		m.coin += amount
		if m == p:
			say(m, "You receive %s from the corpse%s." % [format_coin(amount), " (your split)" if members.size() > 1 else ""], C_LOOT)
		else:
			say(m, "You receive %s as your split." % format_coin(amount), C_LOOT)
		m.inventory_changed.emit()


func request_loot_item(player_id: int, corpse_id: int, index: int) -> bool:
	if _remote(&"request_loot_item", [player_id, corpse_id, index]):
		return false
	var p := get_object(player_id) as Player
	var c := get_object(corpse_id) as Corpse
	if p == null or c == null or index < 0 or index >= c.entries.size():
		return false
	if p.distance_to(c) > LOOT_RANGE:
		say(p, "You are too far away to loot that corpse.", C_WARN)
		return false
	var entry: Dictionary = c.entries[index]
	if c.owner_name == "" and not can_receive(p, entry["item"]):
		return false
	var slot: String = entry.get("slot", "")
	if slot != "" and not p.equipment.has(slot):
		p.equipment[slot] = entry["item"]
		p.recalc_stats()
	else:
		var loot := Pack.clean_entry(entry)
		if loot.has("contents") and entry.has("contents"):  # a dead player's bag keeps what was in it; a dropped one starts empty
			var inside: Array = loot["contents"]
			var carried: Array = entry["contents"]
			for i in mini(inside.size(), carried.size()):
				inside[i] = Pack.clean_entry(carried[i])
		if not p.pack.add_entry(loot):
			say(p, "Your inventory is full.", C_WARN)
			return false
	c.entries.remove_at(index)
	var n := int(entry.get("count", 1))
	say(p, "--You have looted %s.--" % ("a " + GameData.item_name(entry["item"]) if n <= 1 else "%d %s" % [n, plural(GameData.item_name(entry["item"]))]), C_LOOT)
	p.inventory_changed.emit()
	if c.entries.is_empty():
		remove_corpse(c)
	else:
		_ui(p, &"loot_changed", [c])
	return true


func request_loot_all(player_id: int, corpse_id: int) -> void:
	if _remote(&"request_loot_all", [player_id, corpse_id]):
		return
	var c := get_object(corpse_id) as Corpse
	while c != null and not c.is_queued_for_deletion() and not c.entries.is_empty():
		if not request_loot_item(player_id, corpse_id, 0):
			break


func request_loot_close(player_id: int) -> void:
	if _remote(&"request_loot_close", [player_id]):
		return
	_ui(get_object(player_id) as Player, &"loot_closed", [null])


func remove_corpse(c: Corpse) -> void:
	for p in get_players():
		_ui(p, &"loot_closed", [c])
	c.queue_free()


## Whether a player may take one more of this item: LORE items are one to a
## person, counting every quality of it anywhere they keep things.
func can_receive(p: Player, item_id: String, quiet := false) -> bool:
	if not GameData.item(item_id).get("lore", false):
		return true
	var base := GameData.base_item(item_id)
	for held: String in p.owned_item_ids():
		if GameData.base_item(held) == base:
			if not quiet:
				say(p, "You already have a %s. It is a lore item: one to a person." % GameData.item_name(held), C_WARN)
			return false
	return true


## Why this player can't wear an item (class or deity), or "" if they can.
func equip_block(p: Player, item_id: String) -> String:
	var it := GameData.item(item_id)
	var classes: Array = it.get("classes", [])
	if not classes.is_empty() and not p.char_class in classes:
		return "Your class cannot use the %s." % it["name"]
	var deities: Array = it.get("deities", [])
	if not deities.is_empty() and not p.deity in deities:
		return "Your deity forbids you to use the %s." % it["name"]
	return ""


## Shortcut (shift-click): wear the item at a place in the pack, swapping out
## whatever was in its slot.
func request_equip(player_id: int, place: String) -> void:
	if _remote(&"request_equip", [player_id, place]):
		return
	var p := get_object(player_id) as Player
	if p == null or p.dead or not p.cursor.is_empty():
		return
	var e := p.pack.get_at(place)
	if e.is_empty():
		return
	var item_id: String = e["item"]
	var slot := _equip_slot_for(p, item_id)
	if slot == "":
		return
	p.pack.set_at(place, {})
	if p.equipment.has(slot):
		p.pack.set_at(place, Pack.entry(p.equipment[slot]))
	p.equipment[slot] = item_id
	p.recalc_stats()
	p.inventory_changed.emit()


## The equipment slot an item would go in (a free finger for a ring), or ""
## with the reason said if it can't be worn.
func _equip_slot_for(p: Player, item_id: String, wanted := "") -> String:
	var slot: String = GameData.item(item_id).get("slot", "")
	var fits: Array = SLOT_FITS.get(slot, [slot])
	if slot == "" or (wanted != "" and not wanted in fits):
		say(p, "That doesn't go there." if wanted != "" and slot != "" else "You cannot equip that.", C_WARN)
		return ""
	var why := equip_block(p, item_id)
	if why != "":
		say(p, why, C_WARN)
		return ""
	if wanted != "":
		return wanted
	for s: String in fits:  # a free finger if there is one
		if not p.equipment.has(s):
			return s
	return fits[0]


## EQ's cursor. With nothing held, clicking a place picks up what's there; with
## something held, it puts it down there, swapping with (or topping up) what
## was there. Places: "g:3" / "b:3:5" in the pack, "e:head" worn, "k:7" in the
## bank (bank window open), "t:2" in an open trade.
func request_click(player_id: int, place: String) -> void:
	if _remote(&"request_click", [player_id, place]):
		return
	var p := get_object(player_id) as Player
	if p == null or p.dead:
		return
	var kind := place.get_slice(":", 0)
	var here := _entry_at(p, place)
	if kind == "k" and _service_npc(p, "bank") == null or kind == "t" and p.trade_npc_id < 0:
		return
	if p.cursor.is_empty():
		if here.is_empty():
			return
		if kind == "t":
			if not p.pack.add_entry(here):  # a trade slot hands the item straight back
				p.cursor = here
			_set_entry_at(p, place, {})
			_compact_trade(p)
		else:
			p.cursor = here
			_set_entry_at(p, place, {})
		_after_move(p, place)
		return
	var held := p.cursor
	if kind == "e":
		if held.has("contents"):
			say(p, "You cannot equip that.", C_WARN)
			return
		var slot := _equip_slot_for(p, held["item"], place.get_slice(":", 1))
		if slot == "" or int(held["count"]) > 1:
			return
	elif kind == "g" or kind == "b":
		if not p.pack.fits(place, held):
			say(p, "A bag won't go inside another bag." if held.has("contents") else "That won't fit there.", C_WARN)
			return
	elif kind == "t":
		if held.has("contents") and not Pack._bag_empty(held):
			say(p, "Empty the bag first.", C_WARN)
			return
		if p.trade_items.size() >= TRADE_SLOTS:
			say(p, "The trade window is full.", C_WARN)
			return
		p.trade_items.append(held)
		p.cursor = {}
		_after_move(p, place)
		return
	# same stackable item: top up the stack in place
	var stack := Pack.stack_of(held["item"])
	if not here.is_empty() and here["item"] == held["item"] and stack > 1:
		var n := mini(int(held["count"]), stack - int(here["count"]))
		here["count"] = int(here["count"]) + n
		held["count"] = int(held["count"]) - n
		p.cursor = held if int(held["count"]) > 0 else {}
		_after_move(p, place)
		return
	_set_entry_at(p, place, held)
	p.cursor = here
	_after_move(p, place)


## Ctrl-click on a stack: pick up just one of it (again to take another).
func request_pick_one(player_id: int, place: String) -> void:
	if _remote(&"request_pick_one", [player_id, place]):
		return
	var p := get_object(player_id) as Player
	if p == null or p.dead or not (place.begins_with("g:") or place.begins_with("b:") or place.begins_with("k:")):
		return
	if place.begins_with("k:") and _service_npc(p, "bank") == null:
		return
	var here := _entry_at(p, place)
	if here.is_empty() or here.has("contents"):
		return
	if not p.cursor.is_empty() and (p.cursor["item"] != here["item"] or int(p.cursor["count"]) >= Pack.stack_of(here["item"])):
		return
	here["count"] = int(here["count"]) - 1
	if int(here["count"]) <= 0:
		_set_entry_at(p, place, {})
	if p.cursor.is_empty():
		p.cursor = Pack.entry(here["item"])
	else:
		p.cursor["count"] = int(p.cursor["count"]) + 1
	_after_move(p, place)


## Puts whatever is on the cursor back in the first free place (closing the
## inventory with something held). If nothing is free it stays held.
func request_stow_cursor(player_id: int) -> void:
	if _remote(&"request_stow_cursor", [player_id]):
		return
	var p := get_object(player_id) as Player
	if p != null and not p.cursor.is_empty():
		_stow(p)
		p.inventory_changed.emit()


## Drops whatever is on the cursor at the player's feet, EQ style. NO DROP
## items (or a bag holding one) stay on the cursor.
func request_drop(player_id: int) -> void:
	if _remote(&"request_drop", [player_id]):
		return
	var p := get_object(player_id) as Player
	var z := zone_of(p)
	if p == null or p.dead or p.cursor.is_empty() or z == null:
		return
	for e: Dictionary in [p.cursor] + (p.cursor.get("contents", []) as Array):
		if not e.is_empty() and GameData.item(str(e["item"])).get("no_drop", false):
			say(p, "You cannot drop %s: it is NO DROP." % GameData.item_name(str(e["item"])) if e == p.cursor
					else "You cannot drop a bag holding %s: it is NO DROP." % GameData.item_name(str(e["item"])), C_WARN)
			return
	var g := GroundItem.new()
	g.entry = p.cursor
	var at := p.global_position - p.global_basis.z * 1.2
	z.add_child(g)
	g.global_position = z.ground(at.x, at.z)
	g.rotation.y = randf() * TAU
	say(p, "You drop %s." % g.label_text(), C_SYSTEM)
	p.cursor = {}
	p.inventory_changed.emit()


## Picks a dropped item up: onto the cursor if it's free, else into the pack.
func request_pickup(player_id: int, ground_id: int) -> void:
	if _remote(&"request_pickup", [player_id, ground_id]):
		return
	var p := get_object(player_id) as Player
	var g := get_object(ground_id) as GroundItem
	if p == null or p.dead or g == null or g.is_queued_for_deletion():
		return
	if zone_of(g) != zone_of(p) or p.global_position.distance_to(g.global_position) > LOOT_RANGE:
		say(p, "You are too far away to pick that up.", C_WARN)
		return
	for e: Dictionary in [g.entry] + (g.entry.get("contents", []) as Array):
		if not e.is_empty() and not can_receive(p, str(e["item"])):
			return
	if p.cursor.is_empty():
		p.cursor = g.entry
	elif not p.pack.add_entry(g.entry):
		say(p, "You have no room to pick that up.", C_WARN)
		return
	say(p, "You pick up %s." % g.label_text(), C_LOOT)
	g.queue_free()
	p.inventory_changed.emit()


func _stow(p: Player) -> void:
	if p.pack.add_entry(p.cursor):
		p.cursor = {}
	else:
		say(p, "You have no room to put that away.", C_WARN)


func _entry_at(p: Player, place: String) -> Dictionary:
	var kind := place.get_slice(":", 0)
	var arg := place.get_slice(":", 1)
	match kind:
		"g", "b":
			return p.pack.get_at(place)
		"e":
			return Pack.entry(p.equipment[arg]) if p.equipment.has(arg) else {}
		"k":
			return p.bank[int(arg)] if int(arg) >= 0 and int(arg) < p.bank.size() else {}
		"t":
			return p.trade_items[int(arg)] if int(arg) >= 0 and int(arg) < p.trade_items.size() else {}
	return {}


func _set_entry_at(p: Player, place: String, e: Dictionary) -> void:
	var kind := place.get_slice(":", 0)
	var arg := place.get_slice(":", 1)
	match kind:
		"g", "b":
			p.pack.set_at(place, e)
		"e":
			if e.is_empty():
				p.equipment.erase(arg)
			else:
				p.equipment[arg] = e["item"]
		"k":
			if int(arg) >= 0 and int(arg) < p.bank.size():
				p.bank[int(arg)] = e
		"t":
			if int(arg) >= 0 and int(arg) < p.trade_items.size():
				p.trade_items[int(arg)] = e


func _compact_trade(p: Player) -> void:
	p.trade_items = p.trade_items.filter(func(e: Dictionary) -> bool: return not e.is_empty())


func _after_move(p: Player, place: String) -> void:
	if place.begins_with("e:"):
		p.recalc_stats()
	p.inventory_changed.emit()
	if place.begins_with("k:"):
		_ui(p, &"service_changed")
	if place.begins_with("t:"):
		_ui(p, &"trade_changed")


func request_unequip(player_id: int, slot: String) -> void:
	if _remote(&"request_unequip", [player_id, slot]):
		return
	var p := get_object(player_id) as Player
	if p == null or p.dead or not p.equipment.has(slot):
		return
	if not p.room_for(p.equipment[slot]):
		say(p, "Your inventory is full.", C_WARN)
		return
	p.pack.add(p.equipment[slot])
	p.equipment.erase(slot)
	p.recalc_stats()
	p.inventory_changed.emit()


## Gear a mob spawns wearing, from its "gear" list: [{slot, chance, table or
## item}], as {slot: item id with quality}. Tougher mobs roll better quality.
func roll_gear(mob_data: Dictionary, mob_level: int) -> Dictionary:
	var out := {}
	for entry: Dictionary in mob_data.get("gear", []):
		if randf() >= float(entry.get("chance", 1.0)):
			continue
		var item_id := str(entry.get("item", ""))
		if entry.has("table"):
			item_id = _pick_weighted(GameData.loot["tables"].get(entry["table"], {}))
		if item_id == "" or not GameData.items.has(item_id):
			continue
		# lore items are one of a kind: always exactly themselves
		var quality := "" if GameData.item(item_id).get("lore", false) else roll_quality(mob_level, bool(mob_data.get("named", false)))
		out[str(entry["slot"])] = item_id if quality == "" else "%s@%s" % [item_id, quality]
	return out


## A quality tier id ("" for plain): a roll of 0-100 plus a bonus for the mob's
## level (and more for named mobs), read against the tiers' thresholds.
func roll_quality(mob_level: int, named: bool) -> String:
	var q: Dictionary = GameData.loot["quality"]
	var score := randf() * 100.0 + mob_level * float(q["per_level"]) + (float(q["named_bonus"]) if named else 0.0)
	for tier: Dictionary in q["tiers"]:
		if score < float(tier["below"]):
			return str(tier["id"])
	return ""


func _pick_weighted(table: Dictionary) -> String:
	var total := 0.0
	for id: String in table:
		total += float(table[id])
	var r := randf() * total
	for id: String in table:
		r -= float(table[id])
		if r <= 0.0:
			return id
	return ""


# --- npcs & quests ----------------------------------------------------------

## Hails the player's target, which also turns in any quest it is waiting on.
func request_hail(player_id: int) -> void:
	if _remote(&"request_hail", [player_id]):
		return
	var p := get_object(player_id) as Player
	if p == null or p.dead:
		return
	if not (p.valid_target_entity() is Npc):
		say(p, "Target someone to hail them.", C_WARN)
		return
	_talk(p, p.target as Npc, "hail")


## Says a keyword to the player's target, EQ style ("gnoll fangs").
func request_say(player_id: int, keyword: String) -> void:
	if _remote(&"request_say", [player_id, keyword]):
		return
	var p := get_object(player_id) as Player
	if p == null or p.dead:
		return
	if not (p.valid_target_entity() is Npc):
		say(p, "Target someone to talk to them.", C_WARN)
		return
	_talk(p, p.target as Npc, keyword)


# --- groups -----------------------------------------------------------------

## Everyone in p's group (p alone if ungrouped), online and anywhere.
func group_members(p: Player) -> Array:
	var g: Dictionary = groups.get(p.group_id, {})
	if g.is_empty():
		return [p]
	var out: Array = []
	for id: int in g["members"]:
		var m := get_object(id) as Player
		if m != null:
			out.append(m)
	return out


func _group_say(p: Player, text: String, color := C_CHAT_GROUP) -> void:
	for m: Player in group_members(p):
		say(m, text, color)


func _find_player(name: String) -> Player:
	for q in get_players():
		if q.display_name.to_lower() == name.to_lower():
			return q
	return null


## /invite: by name, or whoever you have targeted. The leader invites; anyone
## ungrouped may start a group this way.
func request_group_invite(player_id: int, name: String) -> void:
	if _remote(&"request_group_invite", [player_id, name]):
		return
	var p := get_object(player_id) as Player
	if p == null:
		return
	var t: Player = _find_player(name) if name != "" else p.valid_target_entity() as Player
	if t == null:
		say(p, "%s is not online." % name.capitalize() if name != "" else "Target a player, or /invite <name>.", C_WARN)
		return
	if t == p:
		say(p, "You can't invite yourself.", C_WARN)
		return
	var g: Dictionary = groups.get(p.group_id, {})
	if not g.is_empty() and g["leader"] != p.entity_id:
		say(p, "Only the group leader can invite.", C_WARN)
		return
	if not g.is_empty() and (g["members"] as Array).size() >= GROUP_MAX:
		say(p, "Your group is full.", C_WARN)
		return
	if t.group_id != 0:
		say(p, "%s is already in a group." % t.display_name, C_WARN)
		return
	t.set_meta("invite_from", p.entity_id)
	t.set_meta("invite_at", Time.get_ticks_msec())
	say(p, "You invite %s to join your group." % t.display_name, C_CHAT_GROUP)
	say(t, "%s invites you to join a group. Type /accept or /decline." % p.display_name, C_CHAT_GROUP)
	_ui(t, &"group_invited", [p.display_name])


func request_group_accept(player_id: int) -> void:
	if _remote(&"request_group_accept", [player_id]):
		return
	var p := get_object(player_id) as Player
	if p == null:
		return
	var inviter := get_object(int(p.get_meta("invite_from", -1))) as Player
	var fresh := Time.get_ticks_msec() - int(p.get_meta("invite_at", 0)) < INVITE_SECONDS * 1000
	if p.has_meta("invite_from"):
		p.remove_meta("invite_from")
	_ui(p, &"group_invited", [""])
	if inviter == null or not fresh:
		say(p, "You have no invitation to accept.", C_WARN)
		return
	if p.group_id != 0:
		say(p, "You are already in a group.", C_WARN)
		return
	if inviter.group_id == 0:
		var gid := _next_group
		_next_group += 1
		groups[gid] = {"leader": inviter.entity_id, "members": [inviter.entity_id]}
		inviter.group_id = gid
	var g: Dictionary = groups[inviter.group_id]
	if (g["members"] as Array).size() >= GROUP_MAX:
		say(p, "That group is full.", C_WARN)
		return
	(g["members"] as Array).append(p.entity_id)
	p.group_id = inviter.group_id
	_group_say(p, "%s has joined the group." % p.display_name)
	_update_group_views()


func request_group_decline(player_id: int) -> void:
	if _remote(&"request_group_decline", [player_id]):
		return
	var p := get_object(player_id) as Player
	if p == null:
		return
	var inviter := get_object(int(p.get_meta("invite_from", -1))) as Player
	if p.has_meta("invite_from"):
		p.remove_meta("invite_from")
	_ui(p, &"group_invited", [""])
	if inviter != null:
		say(inviter, "%s declines your invitation." % p.display_name, C_CHAT_GROUP)
	say(p, "You decline the invitation.", C_CHAT_GROUP)


## /disband: leave your group (it dissolves when one member is left).
func request_group_leave(player_id: int) -> void:
	if _remote(&"request_group_leave", [player_id]):
		return
	var p := get_object(player_id) as Player
	if p != null:
		if p.group_id == 0:
			say(p, "You are not in a group.", C_WARN)
			return
		leave_group(p, "%s has left the group." % p.display_name)


## /kick <name>: the leader removes a member.
func request_group_kick(player_id: int, name: String) -> void:
	if _remote(&"request_group_kick", [player_id, name]):
		return
	var p := get_object(player_id) as Player
	if p == null:
		return
	var t := _find_player(name)
	var g: Dictionary = groups.get(p.group_id, {})
	if g.is_empty() or g["leader"] != p.entity_id:
		say(p, "Only the group leader can remove members.", C_WARN)
		return
	if t == null or t.group_id != p.group_id or t == p:
		say(p, "%s is not in your group." % name.capitalize(), C_WARN)
		return
	leave_group(t, "%s has been removed from the group." % t.display_name)


## /makeleader <name>
func request_group_leader(player_id: int, name: String) -> void:
	if _remote(&"request_group_leader", [player_id, name]):
		return
	var p := get_object(player_id) as Player
	if p == null:
		return
	var t := _find_player(name)
	var g: Dictionary = groups.get(p.group_id, {})
	if g.is_empty() or g["leader"] != p.entity_id:
		say(p, "Only the group leader can pass on leadership.", C_WARN)
		return
	if t == null or t.group_id != p.group_id:
		say(p, "%s is not in your group." % name.capitalize(), C_WARN)
		return
	g["leader"] = t.entity_id
	_group_say(p, "%s is now the leader of the group." % t.display_name)
	_update_group_views()


## Takes a player out of their group (leaving, kicked, camping, disconnecting).
func leave_group(p: Player, announce := "") -> void:
	var g: Dictionary = groups.get(p.group_id, {})
	if g.is_empty():
		return
	if announce != "":
		_group_say(p, announce)
	(g["members"] as Array).erase(p.entity_id)
	var gid := p.group_id
	p.group_id = 0
	p.group = []
	var left: Array = g["members"]
	if left.size() <= 1:
		for id: int in left:
			var m := get_object(id) as Player
			if m != null:
				m.group_id = 0
				m.group = []
				say(m, "Your group has been disbanded.", C_CHAT_GROUP)
		groups.erase(gid)
	elif g["leader"] == p.entity_id:
		g["leader"] = left[0]
		var leader := get_object(int(left[0])) as Player
		if leader != null:
			_group_say(leader, "%s is now the leader of the group." % leader.display_name)
	_update_group_views()


## /assist: take the target of a groupmate (by name) or of your own target.
func request_assist(player_id: int, name: String) -> void:
	if _remote(&"request_assist", [player_id, name]):
		return
	var p := get_object(player_id) as Player
	if p == null:
		return
	var helper: Entity = _find_player(name) if name != "" else p.valid_target_entity()
	if helper == null or helper.distance_to(p) > 200.0:
		say(p, "Assist whom? Target someone or /assist <name>.", C_WARN)
		return
	var t := helper.valid_target_entity()
	if t == null:
		say(p, "%s has no target." % helper.display_name, C_WARN)
		return
	p.target = t
	say(p, "You are assisting %s: your target is now %s." % [helper.display_name, t.display_name], C_SYSTEM)


## Each member's copy of the group window: names, levels, health and mana.
func _update_group_views() -> void:
	for gid: int in groups:
		var g: Dictionary = groups[gid]
		var view: Array = []
		for id: int in g["members"]:
			var m := get_object(id) as Player
			if m == null:
				continue
			var z := zone_of(m)
			view.append({"id": id, "name": m.display_name, "level": m.level, "class": m.char_class,
					"hp": m.hp, "max_hp": m.max_hp, "mana": m.mana, "max_mana": m.max_mana,
					"leader": g["leader"] == id, "zone": z.zone_id if z != null else "", "dead": m.dead})
		for id: int in g["members"]:
			var m := get_object(id) as Player
			if m != null:
				m.group = view


# --- chat -------------------------------------------------------------------

## A line typed into the chat box: plain text is /say, anything starting with
## a slash is a command.
func request_chat(player_id: int, text: String) -> void:
	if _remote(&"request_chat", [player_id, text]):
		return
	var p := get_object(player_id) as Player
	if p == null:
		return
	text = text.strip_edges().left(CHAT_MAX)
	if text == "":
		return
	if not text.begins_with("/"):
		_chat_say(p, text)
		return
	var cmd := text.get_slice(" ", 0).to_lower()
	var rest := text.substr(cmd.length()).strip_edges()
	match cmd:
		"/say", "/s":
			_chat_say(p, rest)
		"/shout", "/sh":
			if rest != "":
				for q in get_players():
					if zone_of(q) == zone_of(p):
						say(q, "You shout, '%s'" % rest if q == p else "%s shouts, '%s'" % [p.display_name, rest], C_CHAT_SHOUT)
		"/ooc", "/o":
			if rest != "":
				for q in get_players():
					say(q, "You say out of character, '%s'" % rest if q == p else "%s says out of character, '%s'" % [p.display_name, rest], C_CHAT_OOC)
		"/tell", "/t", "/msg":
			_chat_tell(p, rest.get_slice(" ", 0), rest.substr(rest.get_slice(" ", 0).length()).strip_edges())
		"/reply", "/r":
			_chat_tell(p, str(p.get_meta("last_tell_from", "")), rest)
		"/who":
			_chat_who(p, rest.to_lower() == "all")
		"/lfg":
			p.set_meta("lfg", not p.get_meta("lfg", false))
			say(p, "You are now %s." % ("looking for a group" if p.get_meta("lfg") else "no longer looking for a group"), C_SYSTEM)
		"/random", "/roll":
			var top := maxi(1, int(rest)) if rest.is_valid_int() else 100
			var roll := randi_range(0, top)
			for q in get_players():
				if q.distance_to(p) <= SAY_RANGE:
					say(q, "**A Magic Die is rolled by %s. It could have been any number from 0 to %d, but this time it turned up a %d." % [p.display_name, top, roll], C_SYSTEM)
		"/loc":
			say(p, "Your location is %d, %d, %d in %s." % [roundi(p.global_position.x), roundi(p.global_position.y), roundi(p.global_position.z), zone_of(p).zone_name], C_SYSTEM)
		"/camp":
			request_camp(player_id)
		"/g", "/gsay", "/group":
			if p.group_id == 0:
				say(p, "You are not in a group.", C_WARN)
			elif rest != "":
				for m: Player in group_members(p):
					say(m, "You tell your party, '%s'" % rest if m == p else "%s tells the group, '%s'" % [p.display_name, rest], C_CHAT_GROUP)
		"/invite", "/inv":
			if rest == "" and p.has_meta("invite_from"):
				request_group_accept(player_id)
			else:
				request_group_invite(player_id, rest)
		"/accept", "/join":
			request_group_accept(player_id)
		"/decline":
			request_group_decline(player_id)
		"/disband", "/leave":
			request_group_leave(player_id)
		"/kick", "/remove":
			request_group_kick(player_id, rest)
		"/makeleader":
			request_group_leader(player_id, rest)
		"/assist", "/a":
			request_assist(player_id, rest)
		"/help", "/h":
			say(p, CHAT_HELP, C_SYSTEM)
		_:
			say(p, "That is not a valid command. Type /help for the list.", C_WARN)


## /say: everyone nearby hears it; a targeted NPC in range treats it as talk.
func _chat_say(p: Player, text: String) -> void:
	if text == "":
		return
	var npc := p.valid_target_entity() as Npc
	if npc != null and p.distance_to(npc) <= TALK_RANGE:
		_talk(p, npc, text)  # says it back to you, and the NPC answers
	else:
		say(p, "You say, '%s'" % text, C_CHAT_SAY)
	for q in get_players():
		if q != p and q.distance_to(p) <= SAY_RANGE:
			say(q, "%s says, '%s'" % [p.display_name, text], C_CHAT_SAY)


func _chat_tell(p: Player, to_name: String, text: String) -> void:
	if to_name == "" or text == "":
		say(p, "Tell whom what? /tell <name> <message>", C_WARN)
		return
	for q in get_players():
		if q.display_name.to_lower() == to_name.to_lower():
			say(q, "%s tells you, '%s'" % [p.display_name, text], C_CHAT_TELL)
			q.set_meta("last_tell_from", p.display_name)
			say(p, "You told %s, '%s'" % [q.display_name, text], C_CHAT_TELL)
			return
	say(p, "%s is not online at this time." % to_name.capitalize(), C_WARN)


## /who: players in your zone, or everywhere with /who all.
func _chat_who(p: Player, everywhere: bool) -> void:
	var here := zone_of(p)
	var lines: PackedStringArray = []
	for q in get_players():
		if everywhere or zone_of(q) == here:
			var cls := str(GameData.classes[q.char_class]["name"])
			lines.append("  [%d %s] %s (%s)%s" % [q.level, cls, q.display_name, zone_of(q).zone_name, "  LFG" if q.get_meta("lfg", false) else ""])
	lines.sort()
	say(p, "Players on %s:" % ("the server" if everywhere else here.zone_name), C_SYSTEM)
	for line in lines:
		say(p, line, C_SYSTEM)
	say(p, "There %s %d player%s %s." % ["is" if lines.size() == 1 else "are", lines.size(), "" if lines.size() == 1 else "s", "online" if everywhere else "in " + here.zone_name], C_SYSTEM)


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
	if key == "hail" and npc.data.has("outfitter"):
		_outfit(p, npc)
	if key == "hail":
		for quest_id: String in p.quests:
			var q: Dictionary = GameData.quests.get(quest_id, {})
			if q.get("giver") == npc.npc_id and p.quests[quest_id].get("active", false) and quest_items_ready(p, quest_id):
				_npc_say(p, npc, str(q.get("ready_text", "Hand those over, {name}.")))
				say(p, "(Press G to open a trade with %s.)" % npc.display_name, C_SYSTEM)
	for quest_id: String in GameData.quests:
		var q: Dictionary = GameData.quests[quest_id]
		if q["giver"] == npc.npc_id and key == str(q.get("start_keyword", "")):
			_accept_quest(p, quest_id)


## An outfitter (Warden Holt) rearms anyone who comes to them with no weapon,
## from their class's starting kit, filling only empty slots.
func _outfit(p: Player, npc: Npc) -> void:
	if p.equipment.has("primary"):
		return
	for item_id: String in p.pack.item_ids():
		if GameData.item(item_id).get("slot", "") == "primary":
			return
	var given: Array = []
	var kit: Dictionary = GameData.classes[p.char_class].get("starting_items", {})
	for slot: String in kit:
		if not p.equipment.has(slot):
			p.equipment[slot] = kit[slot]
			given.append(GameData.item_name(kit[slot]))
	if given.is_empty():
		return
	_npc_say(p, npc, str(npc.data["outfitter"]))
	say(p, "%s gives you: %s." % [npc.display_name, ", ".join(given)], C_LOOT)
	p.recalc_stats()
	p.inventory_changed.emit()


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
	if _remote(&"request_trade_open", [player_id]):
		return
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
	_ui(p, &"trade_opened", [npc])


## Whether this npc runs a quest you're on and carry everything for.
func _hand_in_waiting(p: Player, npc: Npc) -> bool:
	for quest_id: String in p.quests:
		var q: Dictionary = GameData.quests.get(quest_id, {})
		if q.get("giver") == npc.npc_id and p.quests[quest_id].get("active", false) and quest_items_ready(p, quest_id):
			return true
	return false


## EQ's way of giving: click an npc with an item on the cursor. Opens a trade
## with them (even a merchant) and puts the item in it.
func request_give(player_id: int, npc_id: int) -> void:
	if _remote(&"request_give", [player_id, npc_id]):
		return
	var p := get_object(player_id) as Player
	var npc := get_object(npc_id) as Npc
	if p == null or p.dead or npc == null or p.cursor.is_empty():
		return
	if p.trade_npc_id >= 0 and p.trade_npc_id != npc_id:
		request_trade_cancel(player_id)
	p.target = npc
	if p.trade_npc_id < 0:
		request_service_close(player_id)
		request_trade_open(player_id)
	if p.trade_npc_id == npc_id:
		request_click(player_id, "t:%d" % p.trade_items.size())


## Shortcut: offers the entry at a pack place (a whole stack) in the open trade.
func request_trade_add(player_id: int, place: String) -> void:
	if _remote(&"request_trade_add", [player_id, place]):
		return
	var p := get_object(player_id) as Player
	if p == null or p.trade_npc_id < 0 or not p.cursor.is_empty():
		return
	var e := p.pack.get_at(place)
	if e.is_empty():
		return
	if e.has("contents") and not Pack._bag_empty(e):
		say(p, "Empty the bag first.", C_WARN)
		return
	if p.trade_items.size() >= TRADE_SLOTS:
		say(p, "The trade window is full.", C_WARN)
		return
	p.trade_items.append(e)
	p.pack.set_at(place, {})
	p.inventory_changed.emit()
	_ui(p, &"trade_changed")


func request_trade_remove(player_id: int, slot: int) -> void:
	if _remote(&"request_trade_remove", [player_id, slot]):
		return
	var p := get_object(player_id) as Player
	if p == null or p.trade_npc_id < 0 or slot < 0 or slot >= p.trade_items.size():
		return
	_return_to_pack(p, [p.trade_items[slot]])
	p.trade_items.remove_at(slot)
	p.inventory_changed.emit()
	_ui(p, &"trade_changed")


func request_trade_give(player_id: int) -> void:
	if _remote(&"request_trade_give", [player_id]):
		return
	var p := get_object(player_id) as Player
	if p == null or p.trade_npc_id < 0:
		return
	var npc := get_object(p.trade_npc_id) as Npc
	if npc == null or p.distance_to(npc) > TALK_RANGE:
		request_trade_cancel(player_id)
		return
	var offered: Array = []  # one id per unit: NPCs count items, not stacks
	for e: Dictionary in p.trade_items:
		for k in int(e.get("count", 1)):
			offered.append(e["item"])
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
		for quest_id: String in p.quests:  # meant for someone else's quest: say whose
			var q: Dictionary = GameData.quests.get(quest_id, {})
			if p.quests[quest_id].get("active", false) and q.get("giver") != npc.npc_id \
					and left.any(func(id: String) -> bool: return (q["wants"] as Dictionary).has(id)):
				say(p, "(%s: these are for %s.)" % [q["name"], GameData.npcs[q["giver"]]["name"]], C_XP)
		_return_to_pack(p, left.map(func(id: String) -> Dictionary: return Pack.entry(id)))
	p.inventory_changed.emit()
	_close_trade(p)


func request_trade_cancel(player_id: int) -> void:
	if _remote(&"request_trade_cancel", [player_id]):
		return
	var p := get_object(player_id) as Player
	if p == null or p.trade_npc_id < 0:
		return
	_return_to_pack(p, p.trade_items)
	p.trade_items = []
	p.inventory_changed.emit()
	_close_trade(p)


## Puts entries back in the pack; anything with nowhere to go ends up on the
## cursor (or, if that's taken, the first free bank slot is not an option: it
## stays in the trade list so nothing is ever lost).
func _return_to_pack(p: Player, back: Array) -> void:
	for e: Dictionary in back:
		if p.pack.add_entry(e):
			continue
		if p.cursor.is_empty():
			p.cursor = e
		else:
			p.trade_items.append(e)


func _close_trade(p: Player) -> void:
	p.trade_npc_id = -1
	_ui(p, &"trade_closed")


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
	if state["completions"] == 1 and item_id != "" and can_receive(p, item_id):
		_npc_say(p, npc, str(q.get("first_complete_text", "Take this as well.")))
		if not p.pack.add_entry(Pack.entry(item_id)):
			if p.cursor.is_empty():
				p.cursor = Pack.entry(item_id)  # no room: it comes to your hand, EQ-style
			else:
				p.trade_items.append(Pack.entry(item_id))  # held for you until there's room
		say(p, "--You have received a %s.--" % GameData.item_name(item_id), C_LOOT)
	if int(reward.get("xp", 0)) > 0:
		p.add_xp(int(int(reward["xp"]) * float(cfg("xp_rate", 1.0))))
	apply_faction(p, q.get("faction", {}))
	if q.has("next"):  # a quest line: the next step starts as this one ends
		_accept_quest(p, str(q["next"]))
	p.quests_changed.emit()


## How many of each wanted item the player carries (bags plus an open trade),
## capped at what's wanted.
func quest_progress(p: Player, quest_id: String) -> Dictionary:
	var wants: Dictionary = GameData.quests[quest_id]["wants"]
	var out := {}
	for item_id: String in wants:
		var in_trade := 0
		for e: Dictionary in p.trade_items:
			if e["item"] == item_id:
				in_trade += int(e.get("count", 1))
		out[item_id] = mini(p.pack.count(item_id) + in_trade, int(wants[item_id]))
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
	if _remote(&"request_zone_line", [player_id, line_index]):
		return
	var p := get_object(player_id) as Player
	var z := zone_of(p)
	if p == null or p.dead or z == null or z.zone_line_at(p.global_position) != line_index:
		return
	var zl: Dictionary = z.data["zone_lines"][line_index]
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
	if _remote(&"request_camp", [player_id]):
		return
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
	if _remote(&"request_interact", [player_id]):
		return
	var p := get_object(player_id) as Player
	if p == null or p.dead:
		return
	var npc := p.valid_target_entity() as Npc
	if npc == null or not (npc.data.has("merchant") or npc.data.get("banker", false) or npc.data.has("guildmaster")) \
			or _hand_in_waiting(p, npc):
		request_service_close(player_id)  # a merchant with a quest you're ready for trades instead of opening the shop
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
	_ui(p, &"service_opened", [npc, p.service])


func request_service_close(player_id: int) -> void:
	if _remote(&"request_service_close", [player_id]):
		return
	var p := get_object(player_id) as Player
	if p == null or p.service_npc_id < 0:
		return
	p.service_npc_id = -1
	p.service = ""
	_ui(p, &"service_closed")


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
	return int(GameData.item(item_id).get("value", 0))


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


## Buys one, or up to `count` of a stackable (shift-click buys a stack).
func request_buy(player_id: int, item_id: String, count := 1) -> void:
	if _remote(&"request_buy", [player_id, item_id, count]):
		return
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
	if not can_receive(p, item_id):
		return
	if not p.room_for(item_id):
		say(p, "Your inventory is full.", C_WARN)
		return
	count = clampi(count, 1, Pack.stack_of(item_id))
	count = mini(count, mini(p.coin / price, p.pack.room_for(item_id)))
	if not item_id in npc.data["merchant"].get("sells", []):
		count = mini(count, int(sold_back[item_id]))
		sold_back[item_id] = int(sold_back[item_id]) - count
		if sold_back[item_id] <= 0:
			sold_back.erase(item_id)
	p.coin -= price * count
	if bag_or_single(item_id):
		p.pack.add_entry(Pack.entry(item_id))
	else:
		p.pack.add(item_id, count)
	if count == 1:
		say(p, "You buy a %s for %s." % [GameData.item_name(item_id), format_coin(price)], C_LOOT)
	else:
		say(p, "You buy %d %s for %s." % [count, plural(GameData.item_name(item_id)), format_coin(price * count)], C_LOOT)
	p.inventory_changed.emit()
	_ui(p, &"service_changed")


static func bag_or_single(item_id: String) -> bool:
	return Pack.bag_size_of(item_id) > 0 or Pack.stack_of(item_id) == 1


## Sells the entry at a pack place, the whole stack at once.
func request_sell(player_id: int, place: String) -> void:
	if _remote(&"request_sell", [player_id, place]):
		return
	var p := get_object(player_id) as Player
	if p == null:
		return
	var npc := _service_npc(p, "shop")
	if npc == null:
		return
	var e := p.cursor if place == "cursor" else p.pack.get_at(place)  # "cursor": what you're holding
	if e.is_empty():
		return
	if e.has("contents") and not Pack._bag_empty(e):
		say(p, "Empty the bag before you sell it.", C_WARN)
		return
	var item_id: String = e["item"]
	var count := int(e["count"])
	var price := sell_price(npc, item_id) * count
	if price <= 0:
		say(p, "%s isn't interested in that." % npc.display_name, C_WARN)
		return
	if place == "cursor":
		p.cursor = {}
	else:
		p.pack.set_at(place, {})
	p.coin += price
	var stock: Dictionary = merchant_stock.get_or_add(npc.npc_id, {})
	if not item_id in npc.data["merchant"].get("sells", []) and not GameData.item(item_id).get("no_drop", false):
		stock[item_id] = int(stock.get(item_id, 0)) + count
	say(p, "You sell %s for %s." % ["a " + GameData.item_name(item_id) if count == 1 else "%d %s" % [count, GameData.item_name(item_id)], format_coin(price)], C_LOOT)
	p.inventory_changed.emit()
	_ui(p, &"service_changed")


## Shortcut: the entry at a pack place goes to the first empty bank slot.
func request_bank_deposit(player_id: int, place: String) -> void:
	if _remote(&"request_bank_deposit", [player_id, place]):
		return
	var p := get_object(player_id) as Player
	if p == null or _service_npc(p, "bank") == null:
		return
	var e := p.pack.get_at(place)
	var free := p.bank.find({})
	if e.is_empty():
		return
	if free < 0:
		say(p, "Your bank is full.", C_WARN)
		return
	p.bank[free] = e
	p.pack.set_at(place, {})
	p.inventory_changed.emit()
	_ui(p, &"service_changed")


func request_bank_withdraw(player_id: int, bank_index: int) -> void:
	if _remote(&"request_bank_withdraw", [player_id, bank_index]):
		return
	var p := get_object(player_id) as Player
	if p == null or bank_index < 0 or bank_index >= p.bank.size() or _service_npc(p, "bank") == null:
		return
	var e: Dictionary = p.bank[bank_index]
	if e.is_empty():
		return
	if not p.pack.add_entry(e):
		say(p, "Your inventory is full.", C_WARN)
		return
	p.bank[bank_index] = {}
	p.inventory_changed.emit()
	_ui(p, &"service_changed")


## Moves coin between purse and bank; positive deposits, negative withdraws.
func request_bank_coin(player_id: int, amount: int) -> void:
	if _remote(&"request_bank_coin", [player_id, amount]):
		return
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
	_ui(p, &"service_changed")


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
	if _remote(&"request_train", [player_id, spell_id]):
		return
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
	_ui(p, &"service_changed")


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
