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

const LEVELS := [5, 10, 15, 20, 25]
const MOBS := {  # typical even-level monsters, forced to the test level
	5: ["wild_boar", "gnoll_scout", "brigand_thug"],
	10: ["dire_wolf", "black_bear", "orc_raider"],
	15: ["mountain_ram", "sun_cultist", "stone_guardian"],
	20: ["salt_basilisk", "giant_frog", "river_troll"],
	25: ["river_croc", "water_elemental", "river_troll"],
}
const VARIANTS := [["warrior", ""], ["cleric", ""], ["wizard", ""], ["rogue", ""], ["magician", "earth"], ["magician", "fire"],
		["magician", "water"], ["magician", "air"], ["necromancer", "skeleton"]]
const FIGHTS := 2
const TIME_LIMIT := 150.0
const TRAVEL := 15.0  # seconds to find and pull the next one
const ARENA := Vector2(-110, 110)  # open ground in Greenmoor, far from the road and the guards

var test: Node  # the autotest node (for _wait and its zone)
var results: Array = []


func run(t: Node) -> void:
	test = t
	var p := World.local_player
	var z: Zone = test.get_parent().zone
	Engine.time_scale = 20.0
	Engine.physics_ticks_per_second = 120
	Engine.max_physics_steps_per_frame = 40
	await _clear_arena(z)
	var only := OS.get_environment("BALANCE_ONLY")  # e.g. "magician" while tuning one class
	for v: Array in VARIANTS:
		if only != "" and not str(v[0]) in only.split(","):
			continue
		for lvl: int in LEVELS:
			var row := {"class": v[0], "pet": v[1], "level": lvl, "fights": []}
			for mob_id: String in MOBS[lvl]:
				for k in FIGHTS:
					row["fights"].append(await _fight(p, z, str(v[0]), str(v[1]), lvl, mob_id))
			_summarize(row)
			results.append(row)
			print("balance: %-11s %-8s L%-2d  kill %5.1fs  hp lost %3d%%  mana used %3d%%  rest %5.1fs  deaths %d/%d  pet deaths %d  kills/level %4.1f  levels/hour %4.2f  hours/level %4.2f" % [
				v[0], v[1], lvl, row["kill_time"], roundi(row["hp_lost"] * 100), roundi(row["mana_used"] * 100), row["rest"], row["deaths"], row["fights"].size(),
				row["pet_deaths"], row["kills_per_level"], row["levels_per_hour"], 1.0 / maxf(row["levels_per_hour"], 0.001)])
	Engine.time_scale = 1.0
	Engine.physics_ticks_per_second = 60
	var f := FileAccess.open("user://balance.json", FileAccess.WRITE)
	f.store_string(JSON.stringify({"rows": results, "config": {"levels": LEVELS, "mobs": MOBS, "fights": FIGHTS}}, " "))
	f.close()
	print("balance: wrote %s" % ProjectSettings.globalize_path("user://balance.json"))


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
		if str(s["type"]) == "buff" and float(s.get("duration", 0)) >= 600 and str(s.get("target", "")) in ["self", "group"] and not s.get("meal", false):
			World._finish_spell(p, sid, p, true)
	if pet_kind != "":
		var summon := ""
		for sid: String in p.spells:
			if str(GameData.spells[sid].get("pet", "")) == pet_kind or (pet_kind == "skeleton" and str(GameData.spells[sid].get("pet", "")) in ["skeleton", "skeletal_knight"]):
				summon = sid  # the last (highest) one learned
		if summon != "":
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
		await test._wait(0.3)
	World.request_set_target(p.entity_id, mob.entity_id)
	if pet != null:
		World.request_pet(p.entity_id, "attack")
		await test._wait(1.5)  # the pet gets there first and takes the aggro
	mob.add_hate(pet if pet != null else p, 1.0)
	if cls in ["warrior", "rogue", "cleric"]:
		World.request_toggle_attack(p.entity_id)
	var t := 0.0
	var mana0 := p.mana
	var died := false
	while t < TIME_LIMIT and is_instance_valid(mob) and not mob.dead:
		if p.hp < p.max_hp * 0.05:  # as good as dead: stop before the real thing sends you to your bind point
			died = true
			break
		_decide(p, mob)
		if OS.get_environment("BALANCE_DEBUG") != "" and int(t * 4) % 20 == 0:
			var dbg_pet := World.get_object(p.pet_id) as Pet
			print("  t %.1f  you %d/%d  %s %d/%d  dist %.1f  state %d  mob target %s  pet %s" % [t, p.hp, p.max_hp, mob.mob_id, mob.hp, mob.max_hp,
					p.distance_to(mob), mob.state, mob.target.display_name if mob.target else "-",
					("%d/%d dist %.1f auto %s tgt %s" % [dbg_pet.hp, dbg_pet.max_hp, dbg_pet.distance_to(mob), dbg_pet.auto_attack, dbg_pet.target.display_name if dbg_pet.target else "-"]) if dbg_pet else "none"])
		await test._wait(0.25)
		t += 0.25
	died = died or p.dead
	if died and is_instance_valid(mob):
		mob.hate.clear()
	var out := {"mob": mob_id, "time": t, "won": is_instance_valid(mob) and mob.dead, "died": died,
			"hp_lost": 1.0 - float(p.hp) / p.max_hp if not died else 1.0,
			"mana_used": (float(mana0 - p.mana) / p.max_mana) if p.max_mana > 0 else 0.0,
			"pet_died": pet_kind != "" and World.get_object(p.pet_id) == null}
	out["rest"] = _rest_seconds(p, out)
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
	await test._wait(0.2)
	return out


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
	# the strongest damage it has ready: dots kept up, then direct damage and lifetaps
	var pick := ""
	var best := -1.0
	for sid: String in p.spells:
		var s: Dictionary = GameData.spells[sid]
		var kind := str(s["type"])
		if not kind in ["damage", "dot", "lifetap"] or str(s.get("target", "enemy")) != "enemy" or not _ready(p, sid):
			continue
		if s.has("requires") or s.get("from_behind", false) or s.get("requires_hidden", false):
			continue  # shield, piercing, behind, hidden: situational
		if p.distance_to(mob) > float(s.get("range", 0)) + 0.5:
			continue
		var value := 0.0
		if kind == "dot":
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


func _ready(p: Player, sid: String) -> bool:
	return not p.cooldowns.has(sid) and p.mana >= int(GameData.spells[sid].get("mana", 0))


## Seconds of sitting to be back to full health and mana, by the rules in
## World._regen_tick (a tick every tick_seconds; sitting triples health).
func _rest_seconds(p: Player, out: Dictionary) -> float:
	var tick := float(World.cfg("tick_seconds", 6.0))
	var hp_per := maxf(1.0, p.hp_regen * 3.0)
	var hp_need := float(out["hp_lost"]) * p.max_hp
	var mana_need := float(out["mana_used"]) * p.max_mana
	var rest := float(2 + p.level / 2)
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
		if slot == "" or slot == "range" or int(it.get("rec_level", 1)) > lvl:
			continue
		var classes: Array = it.get("classes", [])
		if not classes.is_empty() and not cls in classes:
			continue
		if slot == "secondary" and not (cls in ["warrior", "cleric"] and it.get("shield", false)):
			continue
		var score := float(it.get("ac", 0)) + float(it.get("hp", 0)) / 5.0 + float(it.get("mana", 0)) / 5.0
		for stat: String in ["str", "sta", "agi", "wis", "int"]:
			score += float(it.get(stat, 0))
		if slot == "primary":
			score = float(it.get("dmg", 0)) / float(it.get("delay", 3.0)) * 10.0 + float(it.get("int", 0)) + float(it.get("wis", 0))
			if cls == "rogue" and str(it.get("skill", "")) != "piercing":
				score *= 0.9
		var key := "ring1" if slot == "ring" else slot
		if score > float(score_of.get(key, -1.0)):
			score_of[key] = score
			best[key] = id
	return best
