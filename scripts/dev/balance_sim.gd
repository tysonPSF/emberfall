extends RefCounted
## Balance simulator. Fights each class (and each pet choice) against typical
## monsters of its level, under the real World rules, sped up, and reports how
## long kills take, what they cost, how often you die, and what that makes a
## level. Run it from the autotest (headless is fine):
##   godot --headless --path . -- --autotest --only=balance
## Results: user://balance.json (and printed as a table).
##
## The player plays sensibly, not perfectly: long buffs up before the pull
## (and on the pet), the pet sent in first, a heal when low (clerics on
## themselves, lifetaps for necromancers, pet heals for pet classes), then the
## best damage it has off cooldown, dots kept up, and auto attack on. Skills sit
## at the neutral 80% of cap. Gear: the best merchant gear the class can wear
## at that level. Resting afterward is measured from the regeneration rules.

const LEVELS := [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
const MOBS := {  # typical even-level monsters, forced to the test level
	5: ["wild_boar", "gnoll_scout", "brigand_thug"],
	10: ["dire_wolf", "black_bear", "orc_raider"],
	15: ["mountain_ram", "sun_cultist", "stone_guardian"],
	20: ["salt_basilisk", "giant_frog", "river_troll"],
	25: ["river_croc", "water_elemental", "river_troll"],
	30: ["ash_drake", "magma_golem", "ember_cultist"],
	35: ["ember_giant", "glass_golem", "obsidian_drake"],
	40: ["grass_stalker", "thunderhoof", "barrow_wight"],
	45: ["sky_serpent", "tempest_elemental", "sky_pirate"],
	50: ["night_stalker", "shade", "morvaine_thrall"],
}
const VARIANTS := [["warrior", ""], ["cleric", ""], ["wizard", ""], ["rogue", ""], ["magician", "earth"], ["magician", "fire"],
		["magician", "water"], ["magician", "air"], ["necromancer", "skeleton"], ["shaman", "spirit_wolf"], ["ranger", "hawk"]]
const FIGHTS := 2  # a fight per monster (BALANCE_FIGHTS overrides it, for steadier numbers)
const TIME_LIMIT := 150.0
const DECIDE_EVERY := 0.25  # seconds of game time between the player's decisions
const TRAVEL := 15.0  # seconds to find and pull the next one
const ARENA := Vector2(-110, 110)  # open ground in Greenmoor, far from the road and the guards

var test: Node  # the autotest node (for _wait and its zone)
var results: Array = []
var _game_seconds := 0.0  # fight time simulated, and the real time it took: the speed actually reached
var _real_seconds := 0.0


func run(t: Node) -> void:
	test = t
	var p := World.local_player
	var z: Zone = test.get_parent().zone
	# game time runs `scale` times faster; physics steps stay 1/6 s of game
	# time whatever the speed, so the rules see the same fight (BALANCE_SCALE)
	var scale := float(OS.get_environment("BALANCE_SCALE")) if OS.get_environment("BALANCE_SCALE") != "" else 20.0
	Engine.time_scale = scale
	Engine.physics_ticks_per_second = roundi(scale * 6.0)
	Engine.max_physics_steps_per_frame = maxi(40, roundi(scale * 2.0))
	await _clear_arena(z)
	var only := OS.get_environment("BALANCE_ONLY")  # e.g. "magician" while tuning one class, or "magician:fire" for one pet
	for v: Array in VARIANTS:
		if only != "" and not str(v[0]) in only.split(",") and not "%s:%s" % [v[0], v[1]] in only.split(","):
			continue
		for lvl: int in LEVELS:
			if OS.get_environment("BALANCE_LEVELS") != "" and not str(lvl) in OS.get_environment("BALANCE_LEVELS").split(","):  # e.g. "30,35"
				continue
			var row := {"class": v[0], "pet": v[1], "level": lvl, "fights": []}
			for mob_id: String in (_named_near(lvl) if _named else MOBS[lvl]):
				for k in (int(OS.get_environment("BALANCE_FIGHTS")) if OS.get_environment("BALANCE_FIGHTS") != "" else FIGHTS):
					row["fights"].append(await _fight(p, z, str(v[0]), str(v[1]), lvl, mob_id))
			_summarize(row)
			results.append(row)
			print("balance: %-11s %-8s L%-2d  kill %5.1fs  hp lost %3d%%  mana used %3d%%  rest %5.1fs  deaths %d/%d  pet deaths %d  kills/level %4.1f  levels/hour %4.2f  hours/level %4.2f" % [
				v[0], v[1], lvl, row["kill_time"], roundi(row["hp_lost"] * 100), roundi(row["mana_used"] * 100), row["rest"], row["deaths"], row["fights"].size(),
				row["pet_deaths"], row["kills_per_level"], row["levels_per_hour"], 1.0 / maxf(row["levels_per_hour"], 0.001)])
	print("balance: fights ran at x%.0f (asked for x%.0f)" % [_game_seconds / maxf(_real_seconds, 0.001), Engine.time_scale])
	Engine.time_scale = 1.0
	Engine.physics_ticks_per_second = 60
	var out_path := OS.get_environment("BALANCE_OUT") if OS.get_environment("BALANCE_OUT") != "" else "user://balance.json"  # tools/balance.py gives each process its own
	var f := FileAccess.open(out_path, FileAccess.WRITE)
	f.store_string(JSON.stringify({"rows": results, "config": {"levels": LEVELS, "mobs": MOBS, "fights": FIGHTS}}, " "))
	f.close()
	print("balance: wrote %s" % ProjectSettings.globalize_path(out_path))


## BALANCE_NAMED: fight named monsters (each at the test level) instead of
## ordinary ones, alone, to see what a solo named costs; a longer time limit.
var _named := OS.get_environment("BALANCE_NAMED") != ""


## Three named monsters from levels lvl to lvl + 3 (none that need a group), the same every run.
func _named_near(lvl: int) -> Array:
	var ids: Array = GameData.mobs.keys().filter(func(id: String) -> bool:
		var d: Dictionary = GameData.mobs[id]
		return d.get("named", false) and int(d.get("min_players", 1)) <= 1 and d.has("level") and int(d["level"][0]) >= lvl and int(d["level"][0]) <= lvl + 3)
	ids.sort()
	var out: Array = []
	for k in 3:
		if not ids.is_empty():
			out.append(ids[(k * 7 + lvl) % ids.size()])
	return out


func _fight(p: Player, z: Zone, cls: String, pet_kind: String, lvl: int, mob_id: String) -> Dictionary:
	# the player, fresh
	World.dismiss_pet(p)
	p.char_class = cls
	p.level = lvl
	p.dead = false
	p.buffs.clear()
	p.dots.clear()
	p.cooldowns.clear()
	p.cast = {}
	p.auto_attack = false
	p.feigning = false
	p.spells = []
	for sid: String in GameData.spells:
		var need := int(GameData.spells[sid].get("classes", {}).get(cls, 999))
		if need <= lvl:
			p.spells.append(sid)
	p.equipment = _kit(cls, lvl)
	p.stat_points = {}  # the class's recommended starting stats, as most players will spend them
	var spread: Dictionary = GameData.classes[cls].get("stat_preset", {})
	for stat: String in spread:
		p.stat_points[stat] = int(spread[stat])
	if p.pack.count("crude_arrow") < 200:
		p.pack.add("crude_arrow", 200)  # enough for any fight
	p.skills = {}
	for sk: String in GameData.skills["skills"]:
		var cap := World.skill_cap(p, sk)
		if cap > 0:
			p.skills[sk] = roundi(cap * 0.8)
	p.recalc_stats()
	var home := z.ground(ARENA.x, ARENA.y) + Vector3.UP * 0.2
	p.global_position = home
	p.velocity = Vector3.ZERO
	# long buffs, on you and (after summoning) on the pet
	for sid: String in p.spells:
		var s: Dictionary = GameData.spells[sid]
		if str(s["type"]) == "buff" and float(s.get("duration", 0)) >= 600 and str(s.get("target", "")) in ["self", "group", "friendly"] and not s.get("meal", false):
			World._finish_spell(p, sid, p, true)
	var had_pet := false  # a shaman has no wolf before 20
	if pet_kind != "":
		var summon := ""
		for sid: String in p.spells:
			if str(GameData.spells[sid].get("pet", "")) == pet_kind or (pet_kind == "skeleton" and str(GameData.spells[sid].get("pet", "")) in ["skeleton", "skeletal_knight"]):
				summon = sid  # the last (highest) one learned
		if summon != "":
			had_pet = true
			World.summon_pet(p, summon)
			var pet := World.get_object(p.pet_id) as Pet
			for sid: String in p.spells:
				var s: Dictionary = GameData.spells[sid]
				if str(s["type"]) == "buff" and str(s.get("target", "")) == "pet" and float(s.get("duration", 0)) >= 600:
					World._finish_spell(p, sid, pet, true)
	p.hp = p.max_hp
	p.mana = p.max_mana
	p.recalc_stats()
	p.hp = p.max_hp
	p.mana = p.max_mana
	# the monster, at the test level, 14 m off
	var d: Dictionary = (GameData.mobs[mob_id] as Dictionary).duplicate(true)
	d["level"] = [lvl, lvl]
	d.erase("gear")  # its gear roll would make runs noisy; the base monster
	var mob := Mob.new()
	mob.setup(mob_id, d, null)
	mob.aggressive = false
	mob.position = z.ground(ARENA.x, ARENA.y - 10.0) + Vector3.UP * 0.2  # before it enters: that's the home it leashes to
	z.add_child(mob)
	var pet := World.get_object(p.pet_id) as Pet
	if pet != null:
		pet.global_position = home + Vector3(1.5, 0, -1.0)
		await _sim_wait(0.3)
	World.request_set_target(p.entity_id, mob.entity_id)
	if pet != null:
		World.request_pet(p.entity_id, "attack")
		await _sim_wait(1.5)  # the pet gets there first and takes the aggro
	if not is_instance_valid(pet):
		pet = null  # it can be gone already (or have won) by now
	if is_instance_valid(mob) and not mob.dead:
		mob.add_hate(pet if pet != null else p, 1.0)
	if cls in ["warrior", "rogue", "cleric", "ranger"]:
		World.request_toggle_attack(p.entity_id)
	# the fight runs on physics steps, counted in game time: a timer's wait
	# ends on the next frame, so a loop of timers under-counts, and more the
	# faster the sim runs (at 60x a 48 s fight read as 26 s)
	var step := Engine.time_scale / Engine.physics_ticks_per_second
	var t := 0.0
	var next_decision := 0.0
	var mana0 := p.mana
	var died := false
	var real0 := Time.get_ticks_msec()
	while t < (TIME_LIMIT * 3.0 if _named else TIME_LIMIT) and is_instance_valid(mob) and not mob.dead:
		if t >= next_decision:
			next_decision += DECIDE_EVERY
			if p.hp < p.max_hp * 0.05:  # as good as dead: stop before the real thing sends you to your bind point
				died = true
				break
			_decide(p, mob)
			if OS.get_environment("BALANCE_DEBUG") != "" and int(t * 4) % 20 == 0:
				var dbg_pet := World.get_object(p.pet_id) as Pet
				print("  t %.1f  you %d/%d  %s %d/%d  dist %.1f  state %d  mob target %s  pet %s" % [t, p.hp, p.max_hp, mob.mob_id, mob.hp, mob.max_hp,
						p.distance_to(mob), mob.state, mob.target.display_name if mob.target else "-",
						("%d/%d dist %.1f auto %s tgt %s" % [dbg_pet.hp, dbg_pet.max_hp, dbg_pet.distance_to(mob), dbg_pet.auto_attack, dbg_pet.target.display_name if dbg_pet.target else "-"]) if dbg_pet else "none"])
		await test.get_tree().physics_frame
		t += step
	_game_seconds += t
	_real_seconds += (Time.get_ticks_msec() - real0) / 1000.0
	died = died or p.dead
	if died and is_instance_valid(mob):
		mob.hate.clear()
	var out := {"mob": mob_id, "time": t, "won": is_instance_valid(mob) and mob.dead, "died": died,
			"hp_lost": 1.0 - float(p.hp) / p.max_hp if not died else 1.0,
			"mana_used": (float(mana0 - p.mana) / p.max_mana) if p.max_mana > 0 else 0.0,
			"pet_died": had_pet and World.get_object(p.pet_id) == null}
	out["rest"] = _rest_seconds(p, out)
	out["ac"] = p.ac
	out["max_hp"] = p.max_hp
	out["mob_ac"] = int(d.get("ac", 0))
	# clean up: the monster, its corpse, the pet
	if is_instance_valid(mob):
		mob.queue_free()
	for c in z.get_children():
		if c is Corpse:
			c.queue_free()
	World.dismiss_pet(p)
	p.dead = false
	p.hp = p.max_hp
	p.target = null
	p.auto_attack = false
	p.stat_points = {}
	await _sim_wait(0.2)
	return out


## Waits `seconds` of game time, counted in physics steps (a timer ends on a
## frame, so under load it overshoots: a pet's head start ran long).
func _sim_wait(seconds: float) -> void:
	var step := Engine.time_scale / Engine.physics_ticks_per_second
	var t := 0.0
	while t < seconds:
		await test.get_tree().physics_frame
		t += step


## An empty field: no spawners, no other monsters, and the guards stand still
## (they'd help, and the numbers are for a player on their own).
func _clear_arena(z: Zone) -> void:
	for n in z.get_children():
		if n is SpawnPoint or n is Mob:
			n.queue_free()
		elif n is Npc:
			n.set_physics_process(false)
	await test._wait(0.2)


## What the player does this moment.
func _decide(p: Player, mob: Mob) -> void:
	if not p.cast.is_empty():
		return
	var reach := World.melee_range() * 0.8
	if (mob.state == Mob.State.FLEE or mob.valid_target_entity() != null) and p.distance_to(mob) > reach \
			and (mob.state == Mob.State.FLEE or mob.valid_target_entity() == p):  # it runs, or can't reach you: chase it
		var z := World.zone_of(p)
		var to := mob.global_position - p.global_position
		to.y = 0.0
		var step := minf(to.length() - reach * 0.8, 7.0 * 0.25)
		var at := p.global_position + to.normalized() * step
		p.global_position = Vector3(at.x, z.surface_at(at.x, at.z) + 0.1, at.z)
	var pet := World.get_object(p.pet_id) as Pet
	var best_heal := func(target: String) -> String:
		var pick := ""
		var most := 0
		for sid: String in p.spells:
			var s: Dictionary = GameData.spells[sid]
			if str(s["type"]) == "heal" and str(s.get("target", "")) == target and _ready(p, sid) and int(s.get("max", 0)) > most:
				pick = sid
				most = int(s.get("max", 0))
		return pick
	if p.hp < p.max_hp * 0.5:
		var h: String = best_heal.call("friendly")
		if h == "":
			h = best_heal.call("self")
		if h == "":
			h = best_heal.call("group")
		if h != "":
			World.request_set_target(p.entity_id, p.entity_id)
			World.request_cast(p.entity_id, h)
			World.request_set_target(p.entity_id, mob.entity_id)
			return
	if pet != null and pet.hp < pet.max_hp * 0.4:
		var ph: String = best_heal.call("pet")
		if ph != "":
			World.request_cast(p.entity_id, ph)
			return
	World.request_set_target(p.entity_id, mob.entity_id)
	# a wizard roots it first, then keeps out of its reach and nukes
	if p.char_class == "wizard" and pet == null:
		if mob.root_left > 0.0 and p.distance_to(mob) < 7.0:
			var zz := World.zone_of(p)
			var away := p.global_position - mob.global_position
			away.y = 0.0
			var to := p.global_position + away.normalized() * 1.75
			p.global_position = Vector3(to.x, zz.surface_at(to.x, to.z) + 0.1, to.z)
		elif mob.root_left <= 0.0:
			var root := ""
			for sid: String in p.spells:
				var s: Dictionary = GameData.spells[sid]
				if str(s["type"]) == "root" and _ready(p, sid) and (root == "" or int(s.get("classes", {}).get("wizard", 0)) > int(GameData.spells[root].get("classes", {}).get("wizard", 0))):
					root = sid
			if root != "":
				World.request_cast(p.entity_id, root)
				return
	# a shaman slows first: the strongest slow it knows, whenever the foe isn't slowed
	if mob.slow_left <= 0.0:
		var slow := ""
		for sid: String in p.spells:
			var s: Dictionary = GameData.spells[sid]
			if str(s["type"]) == "slow" and _ready(p, sid) and (slow == "" or int(s.get("slow", 0)) > int(GameData.spells[slow].get("slow", 0))):
				slow = sid
		if slow != "" and p.distance_to(mob) <= float(GameData.spells[slow].get("range", 0)):
			World.request_cast(p.entity_id, slow)
			return
	# the strongest damage it has ready: dots kept up, then direct damage and lifetaps
	var pick := ""
	var best := -1.0
	for sid: String in p.spells:
		var s: Dictionary = GameData.spells[sid]
		var kind := str(s["type"])
		if not kind in ["damage", "dot", "lifetap", "shot"] or str(s.get("target", "enemy")) != "enemy" or not _ready(p, sid):
			continue
		if (s.has("requires") and not (str(s["requires"]) == "piercing" and GameData.item(str(p.equipment.get("primary", ""))).get("skill", "") == "piercing")) \
				or (s.get("from_behind", false) and not s.has("front_pct")) or s.get("requires_hidden", false):
			continue  # a shield, behind, hidden: situational (a rogue with a dagger stabs from the front)
		if p.distance_to(mob) > (World.ranged_reach(p) if kind == "shot" else float(s.get("range", 0))) + 0.5:
			continue
		var value := 0.0
		if kind == "shot":  # a bow shot's rough worth, times the ability's multiple
			var bow := GameData.item(str(p.equipment.get("range", "")))
			value = (float(bow.get("dmg", 0)) * 2.0 + p.level) * float(GameData.classes[p.char_class]["melee_skill"]) * 0.6 * float(s.get("shot_mult", 1.0)) * int(s.get("shots", 1))
		elif kind == "dot":
			if mob.dots.any(func(dd: Dictionary) -> bool: return dd["spell"] == sid and dd["caster_id"] == p.entity_id):
				continue
			value = (float(s.get("tick", 1)) + float(s.get("per_level", 0)) * (p.level - 1)) * int(s.get("ticks", 3))
		else:
			value = (float(s.get("min", 0)) + float(s.get("max", 0))) * 0.5 + float(s.get("per_level", 0)) * (p.level - 1)
		if value > best:
			best = value
			pick = sid
	if pick != "":
		World.request_cast(p.entity_id, pick)
	elif p.char_class == "ranger" and p.distance_to(mob) > World.melee_range() and not p.cooldowns.has("ranged"):
		World.request_ranged(p.entity_id)  # the bow while it closes


func _ready(p: Player, sid: String) -> bool:
	return World.spell_ready(p, sid) and p.mana >= int(GameData.spells[sid].get("mana", 0))


## Seconds of sitting to be back to full health and mana, by the rules in
## World._regen_tick (a tick every tick_seconds; sitting triples health).
func _rest_seconds(p: Player, out: Dictionary) -> float:
	var tick := float(World.cfg("tick_seconds", 6.0))
	var hp_per := maxf(1.0, p.hp_regen * 3.0)
	var hp_need := float(out["hp_lost"]) * p.max_hp
	var mana_need := float(out["mana_used"]) * p.max_mana
	var rest := World.sitting_mana(p.level)
	if World.skill_cap(p, "meditate") > 0:
		rest *= 0.5 + 0.625 * World.skill_frac(p, "meditate")
	var mana_per := maxf(1.0, p.mana_regen + roundf(rest))
	var need := maxf(ceilf(hp_need / hp_per), ceilf(mana_need / mana_per) if p.max_mana > 0 else 0.0)
	if bool(out["pet_died"]):  # summon a new one and buff it
		need += 2.0
	return need * tick


func _summarize(row: Dictionary) -> void:
	var fights: Array = row["fights"]
	var n := float(fights.size())
	var sum := func(key: String) -> float:
		var total := 0.0
		for f: Dictionary in fights:
			total += float(f[key]) if f[key] is float or f[key] is int else (1.0 if f[key] else 0.0)
		return total
	row["kill_time"] = sum.call("time") / n
	row["ac"] = int(sum.call("ac") / n)
	row["max_hp"] = int(sum.call("max_hp") / n)
	row["hp_lost"] = sum.call("hp_lost") / n
	row["mana_used"] = sum.call("mana_used") / n
	row["rest"] = sum.call("rest") / n
	row["deaths"] = int(sum.call("died"))
	row["wins"] = int(sum.call("won"))
	row["pet_deaths"] = int(sum.call("pet_died"))
	var lvl := int(row["level"])
	var per_kill := float(World.cfg("xp_base", 10)) + lvl * lvl * float(World.cfg("xp_per_mob_level_sq", 5))
	var to_level := float(World.cfg("xp_per_level_sq", 100)) * lvl * lvl
	row["kills_per_level"] = to_level / per_kill
	# a death costs a tenth of a level and a run back (call it five minutes)
	var death_rate := float(row["deaths"]) / n
	var cycle := float(row["kill_time"]) + float(row["rest"]) + TRAVEL + death_rate * 300.0
	var kills_per_hour := 3600.0 / cycle * (1.0 - death_rate)
	row["levels_per_hour"] = maxf(0.0, (kills_per_hour - death_rate * 3600.0 / cycle * row["kills_per_level"] * float(World.cfg("death_xp_loss", 0.1))) / row["kills_per_level"])


## The best merchant gear this class can use at this level, one piece a slot.
func _kit(cls: String, lvl: int) -> Dictionary:
	var sold := {}
	for npc_id: String in GameData.npcs:
		for id: Variant in GameData.npcs[npc_id].get("merchant", {}).get("sells", []):
			sold[str(id)] = true
	var best := {}
	var score_of := {}
	for id: String in sold:
		var it := GameData.item(id)
		var slot := str(it.get("slot", ""))
		if slot == "" or (slot == "range" and cls != "ranger") or int(it.get("rec_level", 1)) > lvl:
			continue
		var classes: Array = it.get("classes", [])
		if not classes.is_empty() and not cls in classes:
			continue
		if slot == "secondary" and not (cls in ["warrior", "cleric", "shaman"] and it.get("shield", false)):
			continue
		var score := float(it.get("ac", 0)) + float(it.get("hp", 0)) / 5.0 + float(it.get("mana", 0)) / 5.0
		for stat: String in ["str", "sta", "agi", "wis", "int"]:
			score += float(it.get(stat, 0))
		if slot == "primary" or slot == "range":
			score = float(it.get("dmg", 0)) / float(it.get("delay", 3.0)) * 10.0 + float(it.get("int", 0)) + float(it.get("wis", 0))
			if cls == "rogue" and str(it.get("skill", "")) != "piercing":
				score *= 0.9
		var key := "ring1" if slot == "ring" else slot
		if score > float(score_of.get(key, -1.0)):
			score_of[key] = score
			best[key] = id
	# rogues and rangers dual wield from 13: the best one-handed weapon in the off hand too
	if cls in ["rogue", "ranger"] and lvl >= int(GameData.skills["skills"]["dual_wield"].get("from", {}).get(cls, 99)):
		var off := ""
		var off_score := -1.0
		for id: String in sold:
			var it := GameData.item(id)
			if str(it.get("slot", "")) != "primary" or not str(it.get("skill", "")) in ["1h_slashing", "1h_blunt", "piercing"] or int(it.get("rec_level", 1)) > lvl:
				continue
			var classes: Array = it.get("classes", [])
			if not classes.is_empty() and not cls in classes:
				continue
			var sc := float(it.get("dmg", 0)) / float(it.get("delay", 3.0))
			if sc > off_score:
				off_score = sc
				off = id
		if off != "":
			best["secondary"] = off
	return best
