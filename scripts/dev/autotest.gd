extends Node
## Scripted smoke test. Creates a throwaway wizard, then runs each section
## below in order, saving screenshots along the way. Run everything with:
##   godot --path . -- --autotest --shots=/some/dir
## or only some sections (each moves to the zone it needs first):
##   godot --path . -- --autotest --only=items,gear --shots=/some/dir

## [name, zone it runs in]
const SECTIONS := [
	["landmarks", "greenmoor"],
	["merrick", "greenmoor"],
	["quest", "greenmoor"],
	["combat", "greenmoor"],
	["items", "greenmoor"],
	["gear", "greenmoor"],
	["patrol", "greenmoor"],
	["creatures", "greenmoor"],
	["death", "greenmoor"],
	["guards", "greenmoor"],
	["emberhold", "greenmoor"],
	["merchants", "emberhold"],
	["guild", "emberhold"],
	["faction", "emberhold"],
	["kos", "greenmoor"],
	["root", "greenmoor"],
	["screens", "greenmoor"],
	["chat", "greenmoor"],
	["groupui", "greenmoor"],
	["groupchat", "greenmoor"],
	["bowdrops", "greenmoor"],
	["blessing", "greenmoor"],
	["spells_1115", "greenmoor"],
	["fx", "greenmoor"],
	["holt", "greenmoor"],
	["signface", "greenmoor"],
	["vale_patrol", "thornwood"],
	["bagbar", "greenmoor"],
	["debuffs", "greenmoor"],
	["invwindow", "greenmoor"],
	["wornlook", "greenmoor"],
	["itemwindow", "greenmoor"],
	["skills", "greenmoor"],
	["bags", "greenmoor"],
	["channels", "greenmoor"],
	["packquest", "emberhold"],
	["ranged", "greenmoor"],
	["hotbar", "greenmoor"],
	["reactions", "greenmoor"],
	["drop", "greenmoor"],
	["give", "emberhold"],
	["flee", "greenmoor"],
	["compare", "greenmoor"],
	["music", "greenmoor"],
	["tavern", "emberhold"],
	["cave", "greenmoor"],
	["edges", "greenmoor"],
	["thornwood", "thornwood"],
	["thornwood_mobs", "thornwood"],
	["tw_density", "thornwood"],
	["quest_repeat", "greenmoor"],
	["guard_levels", "greenmoor"],
	["bowshot", "greenmoor"],
	["buy_bundle", "thornwood"],
	["corwin_route", "greenmoor"],
	["remember_login", "greenmoor"],
	["night", "greenmoor"],
	["night_city", "emberhold"],
	["night_spawns", "greenmoor"],
	["hollowmere_border", "thornwood"],
	["hollowmere", "hollowmere"],
	["hollowmere_life", "hollowmere"],
	["hollowmere_perf", "hollowmere"],
	["night_isolate", "hollowmere"],
	["physics_isolate", "hollowmere"],
	["harrowfield_border", "greenmoor"],
	["harrowfield", "harrowfield"],
	["harrowfield_life", "harrowfield"],
	["sign_fit", "hollowmere"],
	["nav_bake", "greenmoor"],
	["nav_chase", "harrowfield"],
	["dual_wield", "greenmoor"],
	["rogue", "greenmoor"],
	["rogue_guild", "emberhold_tavern"],
	["venom_drop", "thornwood"],
	["sunward_border", "hollowmere"],
	["sunward", "sunward_steps"],
	["sunward_life", "sunward_steps"],
	["level20", "sunward_steps"],
	["lanternhold_border", "sunward_steps"],
	["lanternhold", "lanternhold"],
	["bash_stun", "greenmoor"],
	["pets", "greenmoor"],
	["necromancer", "greenmoor"],
	["pet_look", "greenmoor"],
	["crypt_door", "emberhold"],
	["crypt", "emberhold_crypt"],
	["tradeskills", "emberhold"],
	["crafters_emberhold", "emberhold"],
	["crafters_lanternhold", "lanternhold"],
	["crafters_rainhold", "rainhold"],
	["monsoon_borders", "greenmoor"],
	["rainhold", "rainhold"],
	["fishing", "rainhold"],
	["weeping_throat", "weeping_throat"],
	["throat_life", "weeping_throat"],
	["level25", "weeping_throat"],
	["bleach_border", "sunward_steps"],
	["bleach", "the_bleach"],
	["bleach_life", "the_bleach"],
	["encumbrance", "greenmoor"],
	["elowen", "thornwood"],
	["signs", "greenmoor"],
	["river", "thornwood"],
	["landmarks_tw", "thornwood"],
	["camp", "greenmoor"],
]

var shots_dir := ""
var only: PackedStringArray = []


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--shots="):
			shots_dir = a.substr(8)
		if a.begins_with("--only="):
			only = a.substr(7).split(",")
	World.log_message.connect(func(t: String, _c: Color) -> void: print("[log] ", t))
	_run()


func _run() -> void:
	await _setup()
	for s: Array in SECTIONS:
		if only.is_empty() or s[0] in only:
			await _ensure_zone(s[1])
			print("--- section: %s" % s[0])
			await call("_t_" + s[0])
	print("AUTOTEST DONE")
	get_tree().quit()


func _setup() -> void:
	var main := get_parent()
	await _wait(0.6)
	await _shot("0_title")
	for c in main.get_children():
		if c is CharCreate:
			(c as CharCreate).confirmed.emit({"name": "Tester", "class": "wizard", "deity": "wind", "zone": "greenmoor"})
	await _wait(2.0)
	var p := World.local_player
	print("player at ", p.global_position, " on_floor=", p.is_on_floor(), " mobs=", World.get_mobs().size())
	p.zoom = 3.5
	p.pitch = -0.2
	p.camera_pivot.rotation.y = PI  # look at the player's face
	await _wait(0.5)
	await _shot("1_spawn_front")
	World.request_sit(p.entity_id, true)
	await _wait(0.8)
	await _shot("1b_sit")
	World.request_sit(p.entity_id, false)
	p.camera_pivot.rotation.y = 0.0


func _t_landmarks() -> void:
	var main := get_parent()
	var p := World.local_player
	# landmark tour: overview of each, from the side facing the bind point
	var home := p.global_position
	for lm: Dictionary in main.zone.data.get("landmarks", []):
		var at: Vector3 = main.zone.ground(lm["pos"][0], lm["pos"][1])
		var away := Vector2(at.x, at.z).direction_to(Vector2(home.x, home.z)) * (16.0 if lm["type"] == "obelisk" else 26.0)
		if away == Vector2.ZERO:
			away = Vector2(0, 16)
		p.global_position = main.zone.ground(at.x + away.x, at.z + away.y) + Vector3.UP
		p.face_toward(at)
		p.zoom = 10.0
		p.pitch = -0.35
		await _wait(0.7)
		await _shot("1c_%s" % lm["type"])
		var close := away.normalized() * 13.0
		p.global_position = main.zone.ground(at.x + close.x, at.z + close.y) + Vector3.UP
		p.face_toward(at)
		p.pitch = -0.7
		p.zoom = 12.0
		await _wait(0.5)
		await _shot("1d_%s_close" % lm["type"])


func _t_merrick() -> void:
	var p := World.local_player
	# Merrick at the pond: hail, ask about the trout, then open his shop
	for obj: Node3D in World.objects.values():
		if obj is Npc and (obj as Npc).npc_id == "merrick":
			var merrick := obj as Npc
			p.global_position = merrick.global_position + (-merrick.global_transform.basis.z) * 4.0 + Vector3.UP * 0.5
			p.face_toward(merrick.global_position)
			p.zoom = 6.0
			p.pitch = -0.25
			World.request_set_target(p.entity_id, merrick.entity_id)
			World.request_hail(p.entity_id)
			World.request_say(p.entity_id, "trout")
			await _wait(0.7)
			await _shot("1d_merrick")
			World.request_interact(p.entity_id)
			await _wait(0.4)
			await _shot("1d_merrick_shop")
			World.request_service_close(p.entity_id)


func _t_quest() -> void:
	var main := get_parent()
	var p := World.local_player
	# quest: hail the warden, ask about fangs, bring four, turn them in
	var warden: Npc = null
	for obj: Node3D in World.objects.values():
		if obj is Npc and (obj as Npc).npc_id == "warden_holt":
			warden = obj
	var front := -warden.global_transform.basis.z
	p.global_position = warden.global_position + front * 3.5 + Vector3.UP * 0.5
	p.face_toward(warden.global_position)
	World.request_set_target(p.entity_id, warden.entity_id)
	p.zoom = 5.0
	p.pitch = -0.25
	p.camera_pivot.rotation.y = 0.5
	var kit := p.equipment.duplicate()
	p.equipment.clear()  # lost everything: the warden rearms you
	World.request_hail(p.entity_id)
	print("outfitted by warden: %s" % p.equipment)
	p.equipment = kit
	p.recalc_stats()
	World.request_say(p.entity_id, "gnoll fangs")
	await _wait(0.8)
	await _shot("1e_quest_given")
	p.pack.add("gnoll_fang", 4)  # one stack of four
	p.pack.add("rat_whiskers")
	p.inventory_changed.emit()
	World.request_hail(p.entity_id)  # he notices the fangs
	World.request_trade_open(p.entity_id)
	for k in 3:  # three fangs, one at a time off the stack, then into the trade
		World.request_pick_one(p.entity_id, _where(p, "gnoll_fang"))
	World.request_click(p.entity_id, "t:0")
	World.request_click(p.entity_id, _where(p, "rat_whiskers"))
	World.request_click(p.entity_id, "t:1")
	await _wait(0.4)
	await _shot("1f_quest_trade")
	print("trade offered: %s" % [p.trade_items.map(func(e: Dictionary) -> String: return "%s x%d" % [e["item"], e["count"]])])
	World.request_trade_give(p.entity_id)  # 3 fangs + whiskers: not enough, all handed back
	print("short give: fangs=%d whiskers=%d quests=%s" % [p.pack.count("gnoll_fang"), p.pack.count("rat_whiskers"), p.quests])
	World.request_trade_open(p.entity_id)
	World.request_trade_add(p.entity_id, _where(p, "gnoll_fang"))  # the whole stack
	World.request_trade_give(p.entity_id)
	print("quest after turn-in: %s coin=%d xp=%d has_sword=%s fangs=%d whiskers=%d" % [p.quests, p.coin, p.xp,
			p.pack.count("wardens_short_sword") > 0, p.pack.count("gnoll_fang"), p.pack.count("rat_whiskers")])
	await _wait(0.5)
	await _shot("1g_quest_done")
	p.pack.remove("rat_whiskers")
	main.hud._toggle_inventory()
	p.pack.remove("wardens_short_sword")
	p.camera_pivot.rotation.y = 0.0


func _t_combat() -> void:
	var main := get_parent()
	var p := World.local_player
	var home: Vector3 = main.zone.bind_point
	p.global_position = home
	p.zoom = 6.0
	p.pitch = -0.3
	await _wait(0.5)

	var mob := _nearest_mob(p, "gnoll_pup")
	print("nearest mob: %s lvl %d hp %d" % [mob.display_name, mob.level, mob.hp])
	p.global_position = mob.global_position + Vector3(0, 1, 7)
	p.face_toward(mob.global_position)
	await _wait(0.6)
	World.request_set_target(p.entity_id, mob.entity_id)
	World.request_consider(p.entity_id)
	World.request_cast(p.entity_id, "blast_of_frost")
	await _wait(1.0)
	await _shot("2a_casting")
	await _wait(1.2)
	await _shot("2_combat")

	if is_instance_valid(mob) and not mob.dead:
		mob.data = mob.data.duplicate(true)
		mob.data["loot"] = [{"item": "rusty_dagger", "chance": 1.0}, {"item": "gnoll_fang", "chance": 1.0}]
		mob.hp = 1
		p.mana = p.max_mana
		World.request_cast(p.entity_id, "blast_of_frost")
	await _wait(2.5)
	if is_instance_valid(p.target) and p.target is Corpse:
		p.global_position = p.target.global_position + Vector3(0, 1, 2)
		await _wait(0.3)
		World.request_loot_open(p.entity_id, (p.target as Corpse).object_id)
	await _wait(0.4)
	await _shot("3_loot")
	if is_instance_valid(p.target) and p.target is Corpse:
		World.request_loot_all(p.entity_id, (p.target as Corpse).object_id)


func _t_items() -> void:
	var main := get_parent()
	var p := World.local_player
	# item rules: class restrictions, two ring fingers, lore, recommended level, attributes
	var bag_before := p.pack.to_save()
	for id: String in ["rusty_short_sword", "tarnished_ring", "copper_band@fine", "leather_boots", "round_shield"]:
		p.pack.add(id)
	for id: String in ["rusty_short_sword", "tarnished_ring", "copper_band@fine", "leather_boots", "round_shield"]:
		World.request_equip(p.entity_id, _where(p, id))
	print("items: wizard sword blocked=%s rings=%s/%s boots=%s shield blocked=%s attrs=%s mana=%d" % [
			p.equipment.get("primary") != "rusty_short_sword", p.equipment.get("ring1"), p.equipment.get("ring2"),
			p.equipment.get("feet"), not p.equipment.has("secondary"), p.attributes, p.max_mana])
	var lore_free := World.can_receive(p, "wardens_short_sword", true)
	p.bank[0] = Pack.entry("wardens_short_sword")
	print("items: lore sword receivable without one=%s, with one banked=%s; cleaver effectiveness at level %d=%.2f" % [
			lore_free, World.can_receive(p, "wardens_short_sword", true), p.level, p.item_effectiveness(GameData.item("grubnaks_cleaver"))])
	p.bank[0] = {}
	var used_before := p.pack.entries().size()
	p.pack.add("bone_chips", 25)
	print("items: 25 bone chips use %d slots; room for a 26th=%s" % [p.pack.entries().size() - used_before, p.room_for("bone_chips")])
	p.pack.add("bonecarved_talisman")
	World.request_equip(p.entity_id, _where(p, "bonecarved_talisman"))
	p.hp = 3
	World.request_item_click(p.entity_id, "neck")
	var healed_to := p.hp
	World.request_item_click(p.entity_id, "neck")
	print("items: talisman click healed 3 -> %d, recharging=%s" % [healed_to, p.cooldowns.has("item:bonecarved_talisman")])
	p.equipment.erase("neck")
	var procs := 0
	var dummy := _nearest_mob(p, "large_rat")
	var dummy_hp := dummy.max_hp
	dummy.max_hp = 99999
	p.equipment["primary"] = "frost_etched_wand"
	for k in 200:
		dummy.hp = dummy.max_hp
		World._try_proc(p, dummy)
		procs += 1 if dummy.hp < dummy.max_hp else 0
	p.equipment["primary"] = "rusty_dagger"
	p.recalc_stats()
	dummy.max_hp = dummy_hp
	dummy.hp = dummy.max_hp
	dummy.hate.clear()
	print("items: frost wand proc fired %d/200 (10%% expected)" % procs)
	main.hud._toggle_inventory()
	await _wait(0.4)
	await _shot("4_inventory")
	main.hud._toggle_inventory()
	for slot: String in ["ring1", "ring2", "feet"]:
		p.equipment.erase(slot)
	p.pack = Pack.from_save(bag_before)
	p.recalc_stats()

	var skel := _nearest_mob(p, "decaying_skeleton")
	p.global_position = skel.global_position + Vector3(0, 1, 5)
	p.face_toward(skel.global_position)
	World.request_set_target(p.entity_id, skel.entity_id)
	World.request_toggle_attack(p.entity_id)
	World.request_cast(p.entity_id, "gate")
	World.request_interrupt(p.entity_id)
	p.camera_pivot.rotation.y = 2.4
	p.zoom = 7.0
	await _wait(1.6)
	await _shot("4b_skeleton_fight")
	p.camera_pivot.rotation.y = 0.0



func _t_gear() -> void:
	var main := get_parent()
	var p := World.local_player
	# gear: mobs spawn wearing what they drop; line some up fully geared
	for lvl: int in [1, 5]:
		var counts := {}
		for k in 1000:
			var q := World.roll_quality(lvl, false)
			counts[q] = int(counts.get(q, 0)) + 1
		print("quality at level %d: %s" % [lvl, counts])
	var lineup: Array[Mob] = []
	var ids := ["decaying_skeleton", "decaying_skeleton", "decaying_skeleton", "gnoll_scout", "gnoll_pup", "grubnak", "magus_rotfinger", "rhagg"]
	var here := p.global_position
	for i in ids.size():
		var d: Dictionary = (GameData.mobs[ids[i]] as Dictionary).duplicate(true)
		for g: Dictionary in d.get("gear", []):
			g["chance"] = 1.0 if i % 3 != 2 or g["slot"] == "primary" else 0.0
		d["aggressive"] = false
		var m := Mob.new()
		m.setup(ids[i], d, null)
		m.position = main.zone.ground(here.x - 10.5 + i * 3.0, here.z - 8.0) + Vector3.UP * 0.3
		m.rotation.y = 0.0
		main.zone.add_child(m)
		lineup.append(m)
		print("lineup %s wears %s as %s (ac %d, dmg %d-%d, %s)" % [ids[i], m.gear, m.model_id, m.ac, m.dmg_min, m.dmg_max, m.attack_verb[0]])
	p.face_toward(main.zone.ground(here.x, here.z - 8.0))
	p.camera_pivot.rotation.y = 0.0
	p.zoom = 9.0
	p.pitch = -0.2
	await _wait(1.2)
	await _shot("4e_gear_lineup")
	var fell_at := lineup[0].global_position
	World.damage(lineup[0], 9999, p)
	await _wait(0.5)
	p.global_position = fell_at + Vector3(0, 1, 2)
	for c: Node in main.zone.get_children():
		if c is Corpse and (c as Corpse).global_position.distance_to(fell_at) < 1.0:
			World.request_loot_open(p.entity_id, (c as Corpse).object_id)
	await _wait(0.4)
	await _shot("4f_gear_loot")
	World.request_loot_close(p.entity_id)
	for m in lineup.slice(1):
		World.damage(m, 9999, p)



func _t_patrol() -> void:
	var p := World.local_player
	# Guard Corwin walks the road, hunts monsters near him, and helps only friends of the Watch
	var corwin: Npc = null
	for obj: Node3D in World.objects.values():
		if obj is Npc and (obj as Npc).npc_id == "watch_patrol":
			corwin = obj
	var start := corwin.global_position
	await _wait(3.0)
	print("patrol: walked %.1f m in 3 s" % Npc._flat(start, corwin.global_position))
	var stray := _nearest_mob(p, "gnoll_pup")
	stray.global_position = corwin.global_position + Vector3(5, 0.5, 0)
	stray.home = stray.global_position
	await _wait(1.5)
	print("patrol hunt: stray pup engaged or slain = %s" % (not is_instance_valid(stray) or stray.dead or corwin.target == stray))
	if is_instance_valid(stray) and not stray.dead:
		World.damage(stray, 9999, p)
	await _wait(1.0)
	var chaser := _nearest_mob(p, "gnoll_pup")
	for standing: int in [0, 150]:
		p.factions["watch"] = standing
		corwin.auto_attack = false
		corwin.target = null
		p.global_position = corwin.global_position + Vector3(0, 1, 16)
		chaser.global_position = corwin.global_position + Vector3(0, 0.5, 14)
		chaser.home = chaser.global_position
		chaser.level = p.level
		chaser.add_hate(p, 10.0)
		await _wait(1.5)
		print("patrol assist at watch %d: %s" % [standing, is_instance_valid(chaser) and corwin.target == chaser])
		if not is_instance_valid(chaser) or chaser.dead:
			break
	p.global_position = corwin.global_position + Vector3(3, 1, 3)
	p.face_toward(corwin.global_position)
	await _wait(1.0)
	await _shot("4g_patrol")
	if is_instance_valid(chaser) and not chaser.dead:
		World.damage(chaser, 9999, p)
	p.factions.erase("watch")


func _t_creatures() -> void:
	var p := World.local_player
	for creature in ["large_rat", "fire_beetle", "gnoll_scout", "grubnak"]:
		var c := _nearest_mob(p, creature)
		if c == null:
			print("no %s up, skipping its shots" % creature)
			continue
		p.global_position = c.global_position + Vector3(0, 1, 3)
		p.face_toward(c.global_position)
		World.request_set_target(p.entity_id, c.entity_id)
		p.camera_pivot.rotation.y = 0.9
		p.zoom = 4.5
		await _wait(0.8)
		await _shot("4c_%s" % creature)
		World.damage(c, 9999, p)
		await _wait(1.6)
		await _shot("4d_%s_corpse" % creature)
	p.camera_pivot.rotation.y = 0.0


func _t_death() -> void:
	var p := World.local_player
	World.damage(p, 9999, _nearest_mob(p))
	await _wait(1.0)
	await _shot("5_dead")
	await _wait(4.5)
	print("respawned: dead=%s pos=%s carrying=%s equipment=%s" % [p.dead, p.global_position, p.pack.item_ids(), p.equipment])
	p.zoom = 0.0
	await _wait(0.6)
	await _shot("6_first_person")


func _t_guards() -> void:
	var main := get_parent()
	var p := World.local_player
	# guards at the pass: a gnoll chasing the player gets cut down
	var pup := _nearest_mob(p, "gnoll_pup")
	p.global_position = main.zone.ground(0, 158) + Vector3.UP
	pup.global_position = main.zone.ground(0, 146) + Vector3.UP
	pup.home = pup.global_position
	pup.add_hate(p, 5.0)
	p.face_toward(pup.global_position)
	p.zoom = 9.0
	p.pitch = -0.35
	p.camera_pivot.rotation.y = 2.6
	await _wait(1.6)
	await _shot("6b_guards_engage")
	for k in 16:
		if not is_instance_valid(pup) or pup.dead:
			break
		await _wait(0.5)
	print("guards vs pup: pup dead=%s player hp=%d" % [not is_instance_valid(pup) or pup.dead, p.hp])
	await _wait(3.0)
	var guards_home := true
	for obj: Node3D in World.objects.values():
		if obj is Npc and (obj as Npc).npc_id == "emberhold_guard":
			guards_home = guards_home and not (obj as Npc).auto_attack
	print("guards back on duty: %s" % guards_home)
	p.camera_pivot.rotation.y = 0.0


func _t_emberhold() -> void:
	var main := get_parent()
	var p := World.local_player
	# zone trip: Greenmoor's south pass into Emberhold and back
	p.zoom = 9.0
	p.pitch = -0.3
	p.global_position = main.zone.ground(0, 160) + Vector3.UP
	p.face_toward(main.zone.ground(0, 190))
	await _wait(0.8)
	await _shot("7_greenmoor_pass")
	p.global_position = main.zone.ground(0, 181) + Vector3.UP
	await _wait(2.5)
	print("zone after pass: %s at %s" % [main.zone.zone_id, p.global_position])
	await _shot("7b_emberhold_arrival")
	for view: Array in [[Vector2(-26, -30), Vector2(0, 0), 16.0, -0.55, "7c_emberhold_overview"],
			[Vector2(9, -9), Vector2(0, 0), 7.0, -0.3, "7d_hearth"],
			[Vector2(26, 30), Vector2(20, 21), 8.0, -0.35, "7e_market"],
			[Vector2(0, -80), Vector2(0, -56), 10.0, -0.25, "7f_gate_outside"]]:
		p.global_position = main.zone.ground(view[0].x, view[0].y) + Vector3.UP
		p.face_toward(main.zone.ground(view[1].x, view[1].y))
		p.zoom = view[2]
		p.pitch = view[3]
		await _wait(0.8)
		await _shot(view[4])
	for obj: Node3D in World.objects.values():
		if obj is Npc and (obj as Npc).npc_id == "keeper_maelin":
			p.global_position = obj.global_position + Vector3(3, 0.5, 3)
			World.request_set_target(p.entity_id, (obj as Npc).entity_id)
			World.request_hail(p.entity_id)
			World.request_say(p.entity_id, "emberfall")


func _t_merchants() -> void:
	var p := World.local_player
	# merchants and the bank
	p.coin = 1000
	p.pack.add("gnoll_fang", 3)
	p.pack.add("rat_whiskers")
	p.inventory_changed.emit()
	var npcs := {}
	for obj: Node3D in World.objects.values():
		if obj is Npc:
			npcs[(obj as Npc).npc_id] = obj
	var tovin: Npc = npcs["merchant_tovin"]
	p.global_position = tovin.global_position + (-tovin.global_transform.basis.z) * 4.5 + Vector3.UP * 0.5
	p.face_toward(tovin.global_position)
	p.zoom = 6.0
	p.pitch = -0.3
	World.request_set_target(p.entity_id, tovin.entity_id)
	World.request_hail(p.entity_id)
	World.request_interact(p.entity_id)
	var coin0 := p.coin
	World.request_pick_one(p.entity_id, _where(p, "gnoll_fang"))
	World.request_sell(p.entity_id, "cursor")  # one fang off the stack, sold from the cursor
	World.request_sell(p.entity_id, _where(p, "gnoll_fang"))  # then the rest of the stack
	World.request_buy(p.entity_id, "leather_cap")
	World.request_buy(p.entity_id, "gnoll_fang")  # buy one back from his stock
	print("shop: coin %d -> %d fangs=%d cap=%s stock=%s" % [coin0, p.coin, p.pack.count("gnoll_fang"), p.pack.count("leather_cap") > 0, World.merchant_stock])
	await _wait(0.5)
	await _shot("7h_shop")
	var odile: Npc = npcs["banker_odile"]
	p.global_position = odile.global_position + (-odile.global_transform.basis.z) * 2.5 + Vector3.UP * 0.5
	World.request_set_target(p.entity_id, odile.entity_id)
	World.request_interact(p.entity_id)
	World.request_bank_deposit(p.entity_id, _where(p, "rat_whiskers"))
	World.request_click(p.entity_id, _where(p, "leather_cap"))  # by cursor: pick up, put in bank slot 5
	World.request_click(p.entity_id, "k:5")
	World.request_bank_coin(p.entity_id, 500)
	var banked := p.bank.filter(func(e: Dictionary) -> bool: return not e.is_empty()).map(func(e: Dictionary) -> String: return e["item"])
	World.request_bank_withdraw(p.entity_id, 5)
	print("bank: items=%s coin=%d purse=%d cap_back=%s" % [banked, p.bank_coin, p.coin, p.pack.count("leather_cap") > 0])
	await _wait(0.5)
	await _shot("7i_bank")
	World.request_service_close(p.entity_id)


func _t_guild() -> void:
	var p := World.local_player
	var npcs := _npcs()
	# guildmaster: a level 6 wizard learns the wizard spells; the warrior trainer refuses
	p.level = 6
	p.recalc_stats()
	p.coin = 2000
	var coyle: Npc = npcs["gm_coyle"]
	p.global_position = coyle.global_position + (-coyle.global_transform.basis.z) * 2.5 + Vector3.UP * 0.5
	p.face_toward(coyle.global_position)
	World.request_set_target(p.entity_id, coyle.entity_id)
	World.request_hail(p.entity_id)
	World.request_interact(p.entity_id)
	for spell_id in ["burning_embers", "minor_shielding", "root", "fire_bolt", "smite"]:
		World.request_train(p.entity_id, spell_id)
	print("trained: %s coin=%d" % [p.spells, p.coin])
	await _wait(0.5)
	await _shot("7j_guild")
	World.request_service_close(p.entity_id)
	World.request_set_target(p.entity_id, npcs["gm_brask"].entity_id)
	p.global_position = npcs["gm_brask"].global_position + Vector3(0, 0.5, -2.5)
	World.request_interact(p.entity_id)
	World.request_set_target(p.entity_id, p.entity_id)
	var ac0 := p.ac
	World.request_cast(p.entity_id, "minor_shielding")
	await _wait(2.4)
	print("shielding: ac %d -> %d buffs=%s" % [ac0, p.ac, p.buffs.keys()])
	await _shot("7k_buffed")


func _t_faction() -> void:
	var p := World.local_player
	var npcs := _npcs()
	# faction: a disliked customer is refused; attacking a merchant needs two Qs and brings the guards
	print("standings: %s" % [GameData.factions.keys().map(func(f: String) -> String: return "%s=%d" % [f, World.standing(p, f)])])
	var tv: Npc = npcs["merchant_tovin"]
	p.global_position = tv.global_position + (-tv.global_transform.basis.z) * 4.5 + Vector3.UP * 0.5
	p.face_toward(tv.global_position)
	World.request_set_target(p.entity_id, tv.entity_id)
	p.factions["emberhold"] = -600
	World.request_interact(p.entity_id)
	print("refused shop: service=%s" % p.service)
	p.factions["emberhold"] = 100
	World.request_toggle_attack(p.entity_id)
	print("after one Q: attacking=%s" % p.auto_attack)
	World.request_toggle_attack(p.entity_id)
	print("after two Qs: attacking=%s hostile=%s watch=%d emberhold=%d" % [p.auto_attack, p.hostile_npcs.has(tv.entity_id), World.standing(p, "watch"), World.standing(p, "emberhold")])
	p.camera_pivot.rotation.y = PI  # look back past Tovin toward the plaza
	p.zoom = 11.0
	p.pitch = -0.45
	await _wait(1.0)
	var fighting := 0
	for obj: Node3D in World.objects.values():
		if obj is Npc and (obj as Npc).auto_attack:
			fighting += 1
	print("npcs fighting the player: %d" % fighting)
	await _shot("7m_attack_npc")
	for k in 30:
		if p.dead:
			break
		await _wait(0.5)
	print("player dead after attacking a merchant: %s" % p.dead)
	await _wait(5.0)
	p.camera_pivot.rotation.y = 0.0


func _t_kos() -> void:
	var main := get_parent()
	var p := World.local_player
	# gnolls who hate you attack on sight, even pups
	var gp := _nearest_mob(p, "gnoll_pup")
	gp.global_position = main.zone.ground(-40, 100) + Vector3.UP
	gp.home = gp.global_position
	gp.level = p.level  # gray mobs never aggro, so make it a fair fight
	p.global_position = main.zone.ground(-40, 108) + Vector3.UP
	p.factions["gnolls"] = -800
	World.request_set_target(p.entity_id, gp.entity_id)
	World.request_consider(p.entity_id)
	await _wait(1.5)
	print("kos pup: state=%s hates player=%s" % [Mob.State.keys()[gp.state], gp.top_hated() == p])
	World.damage(gp, 9999, p)
	p.factions["gnolls"] = -200


func _t_root() -> void:
	var main := get_parent()
	var p := World.local_player
	for spell_id in ["root", "burning_embers"]:
		if not spell_id in p.spells:
			p.spells.append(spell_id)
	# root and burn a gnoll pup
	var victim := _nearest_mob(p, "gnoll_pup")
	victim.global_position = main.zone.ground(40, 100) + Vector3.UP
	victim.home = victim.global_position
	victim.max_hp = 200  # tough enough to watch it burn
	victim.hp = 200
	p.global_position = main.zone.ground(40, 88) + Vector3.UP
	p.face_toward(victim.global_position)
	p.mana = p.max_mana
	World.request_set_target(p.entity_id, victim.entity_id)
	World.request_cast(p.entity_id, "root")
	await _wait(1.8)
	var hp0 := victim.hp
	World.request_cast(p.entity_id, "burning_embers")
	await _wait(5.5)
	print("root+dot: rooted=%s hp %d -> %s dots=%s" % [victim.root_left > 0.0 if is_instance_valid(victim) else "dead",
			hp0, victim.hp if is_instance_valid(victim) else "dead", victim.dots.size() if is_instance_valid(victim) else "-"])
	await _shot("7l_rooted")


func _t_camp() -> void:
	var main := get_parent()
	var p := World.local_player
	# camp out to the character screen, then continue back in
	GameData.config["camp_seconds"] = 2.0
	World.request_camp(p.entity_id)
	await _wait(1.0)
	await _shot("8_camping")
	await _wait(1.8)
	var title: CharCreate = null
	for c in main.get_children():
		if c is CharCreate:
			title = c
	print("after camp: title=%s player=%s" % [title != null, World.local_player])
	await _wait(0.3)
	await _shot("8b_character_screen")
	title.confirmed.emit(title.existing)
	await _wait(2.0)
	print("continued: zone=%s player=%s level=%d" % [main.zone.zone_id, World.local_player.display_name, World.local_player.level])
	await _shot("8c_continued")



## The online screens, drawn over the game: login, a character list, and the
## server character creator. Nothing connects; the list is filled by hand.
func _t_screens() -> void:
	var login := LoginScreen.new()
	login.address = "play.example.net"
	login.account = "tyson"
	login.offline_save = {"name": "Dragonchow", "class": "warrior", "level": 3}
	login.logged_in = true  # don't try to connect
	add_child(login)
	login._show_login()
	await _wait(0.3)
	await _shot("9a_login")
	login._on_characters([{"name": "Dragonchow", "class": "warrior", "level": 3, "zone": "greenmoor"},
			{"name": "Emberwise", "class": "wizard", "level": 6, "zone": "emberhold"}])
	login.offline_save = {"name": "Oldtimer", "class": "cleric", "level": 2}
	login._on_characters([{"name": "Dragonchow", "class": "warrior", "level": 3, "zone": "greenmoor"},
			{"name": "Emberwise", "class": "wizard", "level": 6, "zone": "emberhold"}])
	await _wait(0.3)
	await _shot("9b_characters")
	login._open_creator()
	await _wait(0.3)
	await _shot("9c_create_on_server")
	login.queue_free()
	await _wait(0.2)


## The chat line: typing doesn't walk you anywhere, plain text is /say, and
## saying a keyword to a targeted NPC works like clicking it.
func _t_chat() -> void:
	var main := get_parent()
	var p := World.local_player
	main.hud._open_chat("")
	var start := p.global_position
	Input.action_press("move_forward")
	await _wait(0.6)
	Input.action_release("move_forward")
	print("chat: typing=%s moved while typing %.2f m" % [main.hud.is_typing(), p.global_position.distance_to(start)])
	main.hud._chat.text_submitted.emit("/who")
	var warden: Npc = _npcs()["warden_holt"]
	p.global_position = warden.global_position + (-warden.global_transform.basis.z) * 3.0 + Vector3.UP * 0.5
	p.face_toward(warden.global_position)
	World.request_set_target(p.entity_id, warden.entity_id)
	p.quests.erase("fang_bounty")
	main.hud._open_chat("")
	main.hud._chat.text = "gnoll fangs"
	main.hud._chat.text_submitted.emit("gnoll fangs")
	await _wait(0.5)
	print("chat: typing after send=%s quest from saying it=%s" % [main.hud.is_typing(), p.quests.has("fang_bounty")])
	main.hud._open_chat("/")
	main.hud._chat.text = "/tell hello"
	await _wait(0.3)
	await _shot("9d_chat")
	main.hud._chat.text_submitted.emit("/tell hello")


## The group window and invite popup, drawn from sample data (a group needs
## a second player; the network test covers the rules).
func _t_groupui() -> void:
	var main := get_parent()
	var p := World.local_player
	p.group = [
		{"id": 9001, "name": "Nick", "level": 6, "class": "cleric", "hp": 40, "max_hp": 70, "mana": 55, "max_mana": 80, "leader": true, "zone": "greenmoor", "dead": false},
		{"id": p.entity_id, "name": p.display_name, "level": p.level, "class": p.char_class, "hp": p.hp, "max_hp": p.max_hp, "mana": p.mana, "max_mana": p.max_mana, "leader": false, "zone": "greenmoor", "dead": false},
		{"id": 9002, "name": "Dragonchow", "level": 3, "class": "warrior", "hp": 12, "max_hp": 52, "mana": 0, "max_mana": 0, "leader": false, "zone": "emberhold", "dead": false},
	]
	main.hud._on_group_invited("Nick")
	await _wait(0.4)
	await _shot("9e_group")
	main.hud._on_group_invited("")
	p.group = []


## Headgear shows on the character: each head piece in turn, then bare.
func _t_wornlook() -> void:
	var p := World.local_player
	var kit := p.equipment.duplicate()
	p.camera_pivot.rotation.y = PI  # face the camera
	p.zoom = 2.6
	p.pitch = -0.1
	for item: String in ["cloth_cap", "leather_cap@fine", "floppy_hat", "bone_helm", "iron_coif", ""]:
		if item == "":
			p.equipment.erase("head")
		else:
			p.equipment["head"] = item
		p.recalc_stats()
		await _wait(0.4)
		print("wornlook: %s -> look.worn %s tiers %s" % [item if item != "" else "(bare)", p.look.get("worn"), p.look.get("tiers", {})])
		await _shot("9f_worn_%s" % (item.get_slice("@", 0) if item != "" else "bare"))
	# whole outfits, front and back
	var outfits := {
		"cloth": {"head": "cloth_cap", "hands": "cloth_gloves", "arms": "cloth_sleeves", "feet": "worn_sandals", "legs": "patchwork_pants", "chest": "patchwork_tunic", "waist": "rope_belt"},
		"leather": {"head": "leather_cap", "hands": "leather_gloves", "arms": "leather_sleeves", "feet": "leather_boots", "legs": "leather_leggings", "chest": "studded_tunic", "waist": "leather_belt", "secondary": "round_shield"},
		"iron": {"head": "iron_coif", "hands": "iron_gauntlets", "feet": "iron_boots", "legs": "iron_greaves", "chest": "mangy_hide_vest", "secondary": "iron_kite_shield"},
	}
	p.zoom = 7.5
	p.pitch = -0.3
	for outfit: String in outfits:
		p.equipment = {"primary": "rusty_dagger"}
		p.equipment.merge(outfits[outfit])
		p.recalc_stats()
		for view: Array in [["front", PI], ["back", 0.6]]:
			p.camera_pivot.rotation.y = view[1]
			await _wait(0.4)
			await _shot("9g_outfit_%s_%s" % [outfit, view[0]])
		var shown := (p.visual as Node).find_children("Worn_*", "MeshInstance3D", true, false).map(func(n: Node) -> String: return str(n.name).substr(5))
		var hidden := (p.visual as Node).find_children("*", "MeshInstance3D", true, false).filter(func(n: Node) -> bool: return not (n as MeshInstance3D).visible).map(func(n: Node) -> String: return str(n.name))
		print("wornlook: %s outfit -> %s; parts %s, hiding %s" % [outfit, p.look.get("worn"), shown, hidden])
	p.equipment = {"primary": "rusty_dagger"}
	p.recalc_stats()
	await _wait(0.2)
	var left := (p.visual as Node).find_children("Worn_*", "MeshInstance3D", true, false).size()
	var still_hidden := (p.visual as Node).find_children("*", "MeshInstance3D", true, false).filter(func(n: Node) -> bool: return not (n as MeshInstance3D).visible).size()
	print("wornlook: stripped -> %d swapped parts left, %d body parts hidden" % [left, still_hidden])
	p.equipment = kit
	p.recalc_stats()
	p.camera_pivot.rotation.y = 0.0


## The item window: several kinds of item, right-click from the bags, and a
## linked item in chat that opens the window again when clicked.
func _t_itemwindow() -> void:
	var main := get_parent()
	var p := World.local_player
	var hud: Hud = main.hud
	p.equipment["neck"] = "bonecarved_talisman"
	p.recalc_stats()
	for id: String in ["cloth_cap", "studded_tunic", "iron_short_sword@fine", "round_shield", "gnoll_fang", "bonecarved_talisman"]:
		hud.show_item(id)
		await _wait(0.5)
		print("itemwindow: %s title=%s preview=%s use=%s" % [id, hud._item_title.text, hud._item_view_box.visible, hud._item_use.visible])
		await _shot("9h_item_%s" % id.replace("@", "_"))
	p.equipment.erase("neck")
	p.recalc_stats()
	hud._item_panel.visible = false
	p.pack.add("leather_boots@superior")
	p.inventory_changed.emit()
	hud._toggle_inventory()
	await _wait(0.3)
	var right := InputEventMouseButton.new()
	right.button_index = MOUSE_BUTTON_RIGHT
	right.pressed = true
	hud._slot_button(_where(p, "leather_boots@superior")).gui_input.emit(right)
	await _wait(0.4)
	print("itemwindow: right-click in bags opened %s" % hud._item_title.text)
	hud._item_link.pressed.emit()
	var typed: String = hud._chat.text
	hud._chat.text_submitted.emit(typed)
	await _wait(0.3)
	hud._item_panel.visible = false
	hud._toggle_inventory()
	hud._on_log_keyword("item:leather_boots@superior")
	await _wait(0.4)
	print("itemwindow: chat line %s; clicking the link opened %s" % [typed, hud._item_title.text])
	await _shot("9h_item_link")
	hud._item_panel.visible = false
	p.pack.remove("leather_boots@superior")


## Skills: starting values, skill-ups slowing toward the cap (and none from
## gray mobs), dodge, fizzles, channeling, meditate, and kick growing with
## skill. Rates are measured over many tries.
func _t_skills() -> void:
	var main := get_parent()
	var p := World.local_player
	print("skills: wizard L%d starts with %s" % [p.level, p.skills])
	var mob := _nearest_mob(p, "gnoll_pup")
	mob.level = p.level + 1
	var saved := p.skills.duplicate()
	World.log_message.disconnect(World.log_message.get_connections()[0]["callable"])  # quiet the flood
	p.skills["piercing"] = 0
	var ups := []
	for k in 400:
		World.try_skill_up(p, "piercing", mob)
		if k in [49, 99, 199, 399]:
			ups.append("%d swings: %d" % [k + 1, p.skills["piercing"]])
	print("skills: piercing from 0, cap %d -> %s" % [World.skill_cap(p, "piercing"), ", ".join(ups)])
	mob.level = 1
	p.level = 10
	p.skills["piercing"] = 0
	for k in 200:
		World.try_skill_up(p, "piercing", mob)
	print("skills: 200 swings on a gray mob raised piercing to %d" % p.skills["piercing"])
	p.level = 1
	mob.level = 2
	p.skills["dodge"] = World.skill_cap(p, "dodge")
	var dodged := 0
	for k in 2000:
		dodged += 1 if World._try_avoid(p, mob) == "dodge" else 0
	print("skills: dodge at cap avoided %d of 2000 swings (7%% expected)" % dodged)
	for level_evo: int in [0, World.skill_cap(p, "evocation")]:
		p.skills["evocation"] = level_evo
		var fizz := 0
		for k in 1000:
			p.mana = 1000
			p.skills["evocation"] = level_evo  # each fizzle may raise it; keep it pinned
			fizz += 1 if World._fizzles(p, GameData.spells["blast_of_frost"]) else 0
		print("skills: evocation %d fizzled %d of 1000 casts" % [level_evo, fizz])
	for ch: int in [0, World.skill_cap(p, "channeling")]:
		p.skills["channeling"] = ch
		var broken := 0
		for k in 500:
			p.skills["channeling"] = ch
			p.cast = {"spell": "blast_of_frost", "target_id": mob.entity_id, "time": 0.0, "total": 2.0, "start_pos": p.global_position}
			World._channel(p)
			broken += 1 if p.cast.is_empty() else 0
		print("skills: channeling %d lost %d of 500 spells to hits" % [ch, broken])
	p.cast = {}
	for med: int in [0, World.skill_cap(p, "meditate")]:
		p.skills["meditate"] = med
		p.sitting = true
		p.mana = 0
		World._regen_tick()
		print("skills: meditate %d restores %d mana per rest tick" % [med, p.mana])
	p.sitting = false
	p.char_class = "warrior"
	p.fill_skills()
	var dummy := _nearest_mob(p, "large_rat")
	dummy.max_hp = 99999
	for kick: int in [0, World.skill_cap(p, "kick")]:
		p.skills["kick"] = kick
		var total := 0
		for k in 300:
			dummy.hp = 99999
			p.skills["kick"] = kick
			World._finish_spell(p, "kick", dummy)
			p.cooldowns.clear()
			total += 99999 - dummy.hp
		print("skills: kick %d averages %.1f damage" % [kick, total / 300.0])
	dummy.hp = 1
	World.damage(dummy, 5, null)
	p.char_class = "wizard"
	p.skills = saved
	if not World.log_message.is_connected(main.hud.add_log):
		World.log_message.connect(main.hud.add_log)
	World.log_message.connect(func(t: String, _c: Color) -> void: print("[log] ", t))
	World.try_skill_up(p, "evocation", null, 100.0)
	main.hud._skills_panel.visible = true
	await _wait(0.8)
	await _shot("9i_skills")
	main.hud._skills_panel.visible = false


## EQ inventory: old saves move into bags, the cursor picks up and puts down,
## bags hold items but not bags, equipping by cursor, stowing on close, and a
## bag with its contents surviving a trip to your corpse.
func _t_bags() -> void:
	var main := get_parent()
	var p := World.local_player
	var hud: Hud = main.hud
	var old := Pack.from_save(null, ["gnoll_fang", "rusty_dagger", "cloth_cap", "leather_cap", "patchwork_pants", "worn_sandals",
			"cloth_gloves", "rope_belt", "bone_helm", "tarnished_ring", "iron_dagger", "oak_staff"])
	print("bags: an old 12-item save becomes %s" % [old.slots.map(func(e: Dictionary) -> String: return e.get("item", "-"))])
	print("bags: its backpack holds %s" % [(old.slots[7].get("contents", []) as Array).map(func(e: Dictionary) -> String: return e.get("item", "-"))])
	p.pack = Pack.new()
	p.pack.slots[0] = Pack.entry("small_sack")
	p.pack.add("leather_backpack")
	p.pack.add("iron_dagger")
	p.pack.add("leather_gloves")
	p.inventory_changed.emit()
	hud._toggle_inventory()
	await _wait(0.3)
	# a dagger into the sack: pick up, put down
	World.request_click(p.entity_id, _where(p, "iron_dagger"))
	World.request_click(p.entity_id, "b:0:2")
	print("bags: dagger now at %s, cursor empty=%s" % [_where(p, "iron_dagger"), p.cursor.is_empty()])
	# a bag into a bag is refused
	World.request_click(p.entity_id, _where(p, "leather_backpack"))
	World.request_click(p.entity_id, "b:0:0")
	print("bags: backpack into sack refused=%s (still held=%s)" % [p.pack.get_at("b:0:0").is_empty(), p.cursor.get("item", "")])
	World.request_click(p.entity_id, "g:5")
	# equip by cursor: gloves to the hands slot, and a bag won't go on your hands
	World.request_click(p.entity_id, _where(p, "leather_gloves"))
	World.request_click(p.entity_id, "e:hands")
	World.request_click(p.entity_id, _where(p, "leather_backpack"))
	World.request_click(p.entity_id, "e:hands")
	print("bags: hands=%s, bag refused as gloves=%s" % [p.equipment.get("hands", "-"), p.cursor.get("item", "") == "leather_backpack"])
	# closing the inventory with something held puts it away
	hud._toggle_inventory()
	await _wait(0.2)
	print("bags: stowed on close: cursor empty=%s, backpack at %s" % [p.cursor.is_empty(), _where(p, "leather_backpack")])
	hud._toggle_inventory()
	hud._toggle_bag(0)
	var pack_slot := int(_where(p, "leather_backpack").get_slice(":", 1))
	hud._toggle_bag(pack_slot)  # two bags open: side by side, left of the window, level with its bottom
	World.request_click(p.entity_id, "b:0:2")  # the dagger on the cursor, for the picture
	await _wait(0.4)
	print("bags: windows at %s; character window %s" % [hud._bag_windows.values().map(func(w: Control) -> String: return str(Rect2(w.position, w.size))), Rect2(hud._inv_panel.position, hud._inv_panel.size)])
	await _shot("9j_inventory")
	World.request_click(p.entity_id, "b:0:2")
	hud._toggle_bag(pack_slot)
	# a bag and its contents go to the corpse and come back whole
	p.pack.add("gnoll_fang", 5)
	var npcs := _npcs()
	var tovin: Npc = npcs.get("merchant_tovin")
	if tovin != null:
		print("bags: (in emberhold)")
	World.damage(p, 9999, _nearest_mob(p))
	await _wait(0.5)
	var corpse: Corpse = null
	for obj: Node3D in World.objects.values():
		if obj is Corpse and (obj as Corpse).owner_name == p.display_name:
			corpse = obj
	print("bags: corpse holds %s" % [corpse.entries.map(func(e: Dictionary) -> String: return "%s%s" % [e["item"], " (%d inside)" % (e["contents"] as Array).filter(func(c: Dictionary) -> bool: return not c.is_empty()).size() if e.has("contents") else ""])])
	await _wait(4.5)
	p.global_position = corpse.global_position + Vector3(0, 1, 1)
	await _wait(0.3)
	World.request_loot_open(p.entity_id, corpse.object_id)
	World.request_loot_all(p.entity_id, corpse.object_id)
	var sack := p.pack.get_at(_where(p, "small_sack"))
	print("bags: after looting: sack has %s; fangs %d; gloves worn=%s" % [(sack.get("contents", []) as Array).map(func(e: Dictionary) -> String: return e.get("item", "-")),
			p.pack.count("gnoll_fang"), p.equipment.get("hands", "-")])
	hud._toggle_inventory()

## Chat channels stick: /ooc, /t and /g carry over to plain lines, other
## commands leave the channel alone, /s goes back to say.
func _t_channels() -> void:
	var main := get_parent()
	var hud: Hud = main.hud
	for line in ["/ooc hello all", "still here", "/who", "/s", "back to say", "/t Nobody hi there", "are you there", "/g", "anyone?", "/say"]:
		hud._open_chat("")
		hud._chat.text = line
		hud._chat.text_submitted.emit(line)
		await _wait(0.1)
		print("channels: typed %-20s -> channel '%s' (%s)" % ["'%s'" % line, hud._chat_channel, hud._channel_label.text])
	hud._open_chat("/ooc ")
	hud._chat.text_submitted.emit("/ooc ")
	hud._open_chat("")
	await _wait(0.3)
	await _shot("9i_chat_channel")
	hud._chat.text_submitted.emit("")
	hud._set_channel("")


## The trail pack quest line, all three steps: Tovin (whiskers), Warden Holt
## in Greenmoor (cord + pelts), Tovin again (hide + beetle eyes).
func _t_packquest() -> void:
	var main := get_parent()
	var p := World.local_player
	var tovin: Npc = _npcs()["merchant_tovin"]
	_stand_by(p, tovin)
	World.request_say(p.entity_id, "proper pack")
	print("packquest: step 1 active=%s" % p.quests.get("trail_pack_cord", {}).get("active", false))
	# shift-click buying: a stack of sling stones and a sling, for the ranged section
	World.request_interact(p.entity_id)
	p.coin += 200
	var coin := p.coin
	World.request_buy(p.entity_id, "sling_stone", 20)
	World.request_buy(p.entity_id, "leather_sling")
	print("packquest: bought stones=%d sling=%d for %d copper" % [p.pack.count("sling_stone"), p.pack.count("leather_sling"), coin - p.coin])
	World.request_service_close(p.entity_id)
	p.pack.add("rat_whiskers", 4)
	await _hand_in(p, tovin, ["rat_whiskers"])
	print("packquest: after step 1 cord=%d step 2 active=%s" % [p.pack.count("braided_whisker_cord"), p.quests.get("trail_pack_hide", {}).get("active", false)])
	await _wait(0.3)
	await _shot("9j_packquest_log")
	await _ensure_zone("greenmoor")
	var holt: Npc = _npcs()["warden_holt"]
	_stand_by(p, holt)
	World.request_say(p.entity_id, "tovin")
	p.pack.add("blackpaw_pelt", 2)
	await _hand_in(p, holt, ["braided_whisker_cord", "blackpaw_pelt"])
	print("packquest: after step 2 hide=%d step 3 active=%s" % [p.pack.count("stitched_blackpaw_hide"), p.quests.get("trail_pack_clasp", {}).get("active", false)])
	await _ensure_zone("emberhold")
	tovin = _npcs()["merchant_tovin"]
	_stand_by(p, tovin)
	p.pack.add("beetle_eye", 2)
	await _hand_in(p, tovin, ["stitched_blackpaw_hide", "beetle_eye"])
	var place := _where(p, "tovins_trail_pack")
	print("packquest: done: pack at %s holds %d slots; quests %s" % [place, (p.pack.get_at(place).get("contents", []) as Array).size(),
			["trail_pack_cord", "trail_pack_hide", "trail_pack_clasp"].map(func(q: String) -> String: return "%s=%s" % [q, p.quests.get(q, {})])])
	main.hud._toggle_inventory()
	main.hud._toggle_bag(int(place.get_slice(":", 1)))
	await _wait(0.4)
	await _shot("9k_trail_pack")
	main.hud._toggle_bag(int(place.get_slice(":", 1)))
	main.hud._toggle_inventory()


func _stand_by(p: Player, npc: Npc) -> void:
	p.global_position = npc.global_position + (-npc.global_transform.basis.z) * 3.0 + Vector3.UP * 0.5
	p.face_toward(npc.global_position)
	World.request_set_target(p.entity_id, npc.entity_id)


## Hails, opens a trade, puts every stack of these items in, and gives.
func _hand_in(p: Player, npc: Npc, items: Array) -> void:
	World.request_hail(p.entity_id)
	World.request_trade_open(p.entity_id)
	for item_id: String in items:
		World.request_trade_add(p.entity_id, _where(p, item_id))
	await _wait(0.2)
	World.request_trade_give(p.entity_id)


## Ranged pulling: a sling (anyone may use one) fires at a gnoll pup out of
## melee range; hit or miss, the pup comes. Then the refusals: out of range,
## out of stones, a bow on a wizard.
func _t_ranged() -> void:
	var main := get_parent()
	var p := World.local_player
	if p.pack.count("leather_sling") == 0:
		p.pack.add("leather_sling")
		p.pack.add("sling_stone", 20)
	World.request_equip(p.entity_id, _where(p, "leather_sling"))
	print("ranged: range slot=%s, stones=%d" % [p.equipment.get("range", "-"), p.pack.count("sling_stone")])
	var mob := _nearest_mob(p, "gnoll_pup")
	var away := Vector3(mob.global_position.x - p.global_position.x, 0, mob.global_position.z - p.global_position.z).normalized()
	p.global_position = main.zone.ground(mob.global_position.x - away.x * 22.0, mob.global_position.z - away.z * 22.0) + Vector3.UP
	p.face_toward(mob.global_position)
	p.zoom = 7.0
	p.pitch = -0.25
	await _wait(0.5)
	World.request_set_target(p.entity_id, mob.entity_id)
	var dist := p.distance_to(mob)
	var skill := int(p.skills.get("throwing", 0))
	World.request_ranged(p.entity_id)
	await _wait(0.12)
	await _shot("9l_ranged_flight")
	World.request_ranged(p.entity_id)  # too soon: still reloading, nothing happens
	print("ranged: fired from %.1f m (sight %s); stones left %d; pup hates me=%s" % [dist, World.in_sight(p, mob), p.pack.count("sling_stone"), mob.hate.has(p.entity_id)])
	await _wait(2.5)
	print("ranged: pup is now %.1f m away (pulled from %.1f)" % [p.distance_to(mob), dist])
	await _shot("9m_ranged_pulled")
	for k in 8:
		if not is_instance_valid(mob) or mob.dead:
			break
		World.request_ranged(p.entity_id)
		await _wait(2.7)
	print("ranged: after more shots: stones %d, throwing %d -> %d, pup dead=%s" % [p.pack.count("sling_stone"), skill, int(p.skills.get("throwing", 0)), not is_instance_valid(mob) or mob.dead])
	var far := _nearest_mob(p, "fire_beetle")
	World.request_set_target(p.entity_id, far.entity_id)
	print("ranged: a beetle at %.1f m:" % p.distance_to(far))
	World.request_ranged(p.entity_id)
	var near := _nearest_mob(p)
	p.pack.remove("sling_stone", p.pack.count("sling_stone"))
	World.request_set_target(p.entity_id, near.entity_id)
	p.global_position = main.zone.ground(near.global_position.x + 12.0, near.global_position.z) + Vector3.UP
	await _wait(2.7)
	print("ranged: no stones left, %s at %.1f m:" % [near.display_name, p.distance_to(near)])
	World.request_ranged(p.entity_id)
	print("ranged: a bow on a wizard: '%s'" % World.equip_block(p, "hunting_shortbow"))
	# ammo that hits can lodge in the mob and turn up on its corpse
	var target := _nearest_mob(p, "large_rat")
	target.set_meta("lodged_ammo", {"sling_stone": 3})
	World.kill(target, p)
	var body: Corpse = null
	for obj: Variant in World.objects.values():
		if obj is Corpse and not (obj as Node).is_queued_for_deletion() and (obj as Corpse).display_name.begins_with(target.display_name):
			body = obj
	print("ranged: a rat with 3 stones in it leaves %s" % [body.entries.filter(func(e: Dictionary) -> bool: return e["item"] == "sling_stone") if body != null else "no corpse"])
	if body != null:
		p.global_position = body.global_position + Vector3(0, 1, 1)
		var before := p.pack.count("sling_stone")
		World.request_loot_open(p.entity_id, body.object_id)
		World.request_loot_all(p.entity_id, body.object_id)
		print("ranged: looted the rat: stones %d -> %d" % [before, p.pack.count("sling_stone")])
	p.equipment.erase("range")
	p.recalc_stats()


## The hotbar: a full row of spells on their gems, one cooling down, one out
## of mana's reach dimmed, auto attack glowing, the sling's reload sweeping.
func _t_hotbar() -> void:
	var main := get_parent()
	var p := World.local_player
	var hud: Hud = main.hud
	var known := p.spells.duplicate()
	p.spells = ["blast_of_frost", "gate", "burning_embers", "minor_shielding", "root", "fire_bolt", "hearthbond", "kick"]
	p.pack.add("leather_sling")
	p.pack.add("sling_stone", 20)
	World.request_equip(p.entity_id, _where(p, "leather_sling"))
	var mob := _nearest_mob(p, "gnoll_pup")
	p.global_position = main.zone.ground(mob.global_position.x + 16.0, mob.global_position.z) + Vector3.UP
	p.face_toward(mob.global_position)
	World.request_set_target(p.entity_id, mob.entity_id)
	p.mana = p.max_mana
	await _wait(0.3)
	World.request_cast(p.entity_id, "root")
	await _wait(2.5)
	World.request_ranged(p.entity_id)
	World.request_toggle_attack(p.entity_id)
	p.mana = 12  # enough for some spells, not all: the rest dim
	await _wait(0.4)
	print("hotbar: slots shown %d; usable %s; ranged sweep %.2f" % [hud._spell_slots.filter(func(x: HotSlot) -> bool: return x.visible).size(),
			hud._spell_slots.map(func(x: HotSlot) -> String: return "%s=%s%s" % [x.get_meta("spell", "-"), "on" if x.usable else "dim", " (%.1fs)" % x.seconds if x.sweep > 0.0 else ""]), hud._ranged_slot.sweep])
	await _shot("9n_hotbar")
	World.request_toggle_attack(p.entity_id)
	p.spells = known
	if not mob.dead:
		World.kill(mob, p)
	p.equipment.erase("range")
	p.recalc_stats()


## Bash needs a shield; being hit targets the attacker unless you're already
## fighting something else.
func _t_reactions() -> void:
	var main := get_parent()
	var p := World.local_player
	var known := p.spells.duplicate()
	var kit := p.equipment.duplicate()
	p.spells.append("bash")
	var mob := _nearest_mob(p, "gnoll_pup")
	p.global_position = main.zone.ground(mob.global_position.x + 2.0, mob.global_position.z) + Vector3.UP
	World.request_set_target(p.entity_id, mob.entity_id)
	p.equipment.erase("secondary")
	p.recalc_stats()
	World.request_cast(p.entity_id, "bash")
	print("reactions: bash without a shield: on cooldown=%s usable on hotbar=%s" % [p.cooldowns.has("bash"), get_parent().hud._spell_usable(GameData.spells["bash"], mob)])
	p.equipment["secondary"] = "round_shield"
	p.recalc_stats()
	World.request_cast(p.entity_id, "bash")
	print("reactions: bash with a round shield: on cooldown=%s" % p.cooldowns.has("bash"))
	# nothing targeted, a mob swings: it becomes the target
	World.request_set_target(p.entity_id, -1)
	var other := _nearest_mob(p, "large_rat")
	p.global_position = main.zone.ground(other.global_position.x + 2.0, other.global_position.z) + Vector3.UP
	other.add_hate(p, 5.0)
	await _wait(4.0)
	print("reactions: untargeted, hit by %s -> target is %s" % [other.display_name, p.target.display_name if p.target != null else "nothing"])
	# already fighting the pup: a second attacker doesn't steal the target
	World.request_set_target(p.entity_id, mob.entity_id)
	await _wait(3.0)
	print("reactions: fighting %s, also hit by %s -> target is still %s" % [mob.display_name, other.display_name, p.target.display_name if p.target != null else "nothing"])
	for m: Mob in [mob, other]:
		if not m.dead:
			World.kill(m, p)
	p.spells = known
	p.equipment = kit
	p.recalc_stats()


## Dropping: a stack, a sword (its model on the ground) and a bag with things
## in it go down and come back up; NO DROP stays on the cursor.
func _t_drop() -> void:
	var main := get_parent()
	var p := World.local_player
	p.global_position = main.zone.bind_point + Vector3(6, 1, 6)
	p.zoom = 5.0
	p.pitch = -0.45
	await _wait(0.4)
	p.pack.add("gnoll_fang", 5)
	p.pack.add("iron_short_sword")
	var sack := Pack.entry("small_sack")
	(sack["contents"] as Array)[0] = Pack.entry("rat_whiskers", 3)
	p.pack.add_entry(sack)
	var dropped: Array[GroundItem] = []
	var sack_place := ""
	for place: String in p.pack.places():
		if (p.pack.get_at(place).get("contents", []) as Array).any(func(e: Dictionary) -> bool: return e.get("item", "") == "rat_whiskers"):
			sack_place = place
	for id: String in ["gnoll_fang", "iron_short_sword", "small_sack"]:
		World.request_click(p.entity_id, sack_place if id == "small_sack" else _where(p, id))
		p.rotate_y(0.9)
		World.request_drop(p.entity_id)
		await _wait(0.1)
	for obj: Variant in World.objects.values():
		if obj is GroundItem:
			dropped.append(obj)
	print("drop: on the ground %s; cursor now %s; fangs carried %d, whiskers carried %d" % [dropped.map(func(g: GroundItem) -> String: return g.label_text()), p.cursor, p.pack.count("gnoll_fang"), p.pack.count("rat_whiskers")])
	await _wait(0.5)
	await _shot("9o_dropped")
	p.pack.add_entry(Pack.entry("braided_whisker_cord"))
	World.request_click(p.entity_id, _where(p, "braided_whisker_cord"))
	World.request_drop(p.entity_id)
	print("drop: NO DROP cord still on cursor=%s" % (p.cursor.get("item", "") == "braided_whisker_cord"))
	World.request_stow_cursor(p.entity_id)
	p.pack.remove("braided_whisker_cord")
	for g in dropped:
		World.request_pickup(p.entity_id, g.object_id)
		if not p.cursor.is_empty():
			World.request_stow_cursor(p.entity_id)
	await _wait(0.1)
	print("drop: picked up: fangs %d, sword %d, whiskers back in the sack %d; left on ground %d" % [p.pack.count("gnoll_fang"), p.pack.count("iron_short_sword"),
			p.pack.count("rat_whiskers"), World.objects.values().filter(func(o: Variant) -> bool: return o is GroundItem and not (o as Node).is_queued_for_deletion()).size()])
	p.pack.remove("gnoll_fang", 5)
	p.pack.remove("iron_short_sword")


## Handing quest items to a merchant the way a player does: G with nothing
## ready opens the shop, G with the whiskers ready opens a trade, and clicking
## Tovin with the whiskers on the cursor puts them in that trade.
func _t_give() -> void:
	var p := World.local_player
	var tovin: Npc = _npcs()["merchant_tovin"]
	_stand_by(p, tovin)
	p.quests.erase("trail_pack_cord")
	World.request_say(p.entity_id, "proper pack")
	World.request_interact(p.entity_id)
	print("give: G with nothing to hand in -> service '%s', trading=%s" % [p.service if p.service_npc_id >= 0 else "-", p.trade_npc_id >= 0])
	World.request_service_close(p.entity_id)
	p.pack.add("rat_whiskers", 4)
	World.request_interact(p.entity_id)
	print("give: G with the whiskers -> service '%s', trading with %s" % [p.service if p.service_npc_id >= 0 else "-", World.get_object(p.trade_npc_id).display_name if p.trade_npc_id >= 0 else "nobody"])
	World.request_trade_cancel(p.entity_id)
	World.request_set_target(p.entity_id, -1)
	World.request_click(p.entity_id, _where(p, "rat_whiskers"))
	World.request_give(p.entity_id, tovin.entity_id)
	print("give: clicked Tovin holding the whiskers -> trade holds %s, cursor %s" % [p.trade_items.map(func(e: Dictionary) -> String: return "%s x%d" % [e["item"], e["count"]]), p.cursor])
	World.request_trade_give(p.entity_id)
	print("give: after Give -> cord %d, step 2 active %s" % [p.pack.count("braided_whisker_cord"), p.quests.get("trail_pack_hide", {}).get("active", false)])
	# the mix-up: step 2's items offered to Tovin come back with a pointer to Holt
	p.pack.add("blackpaw_pelt", 3)
	World.request_click(p.entity_id, _where(p, "braided_whisker_cord"))
	World.request_give(p.entity_id, tovin.entity_id)
	World.request_trade_add(p.entity_id, _where(p, "blackpaw_pelt"))
	World.request_trade_give(p.entity_id)
	p.pack.remove("blackpaw_pelt", 3)
	# step 2 with a stack of 3 pelts: Holt takes 2 and hands one back
	await _ensure_zone("greenmoor")
	var holt: Npc = _npcs()["warden_holt"]
	_stand_by(p, holt)
	p.pack.add("blackpaw_pelt", 3)
	World.request_interact(p.entity_id)
	World.request_trade_add(p.entity_id, _where(p, "braided_whisker_cord"))
	World.request_trade_add(p.entity_id, _where(p, "blackpaw_pelt"))
	print("give: Holt's trade holds %s" % [p.trade_items.map(func(e: Dictionary) -> String: return "%s x%d" % [e["item"], e["count"]])])
	World.request_trade_give(p.entity_id)
	print("give: after Give -> hide %d, pelts back %d, cord %d" % [p.pack.count("stitched_blackpaw_hide"), p.pack.count("blackpaw_pelt"), p.pack.count("braided_whisker_cord")])
	p.pack.remove("blackpaw_pelt", p.pack.count("blackpaw_pelt"))
	p.pack.remove("stitched_blackpaw_hide")
	for q in ["trail_pack_cord", "trail_pack_hide", "trail_pack_clasp"]:
		p.quests.erase(q)


## Fleeing: a wounded gnoll with another gnoll nearby stands its ground; once
## it's the last of its kind around, it runs.
func _t_flee() -> void:
	var main := get_parent()
	var p := World.local_player
	var pup := _nearest_mob(p, "gnoll_pup")
	var kin: Array = World.get_mobs().filter(func(m: Mob) -> bool: return m != pup and not m.dead and m.faction == pup.faction and m.distance_to(pup) <= World.CALL_FOR_HELP_RADIUS)
	if kin.is_empty():  # make sure it has company for the first half
		for m in World.get_mobs():
			if m != pup and not m.dead and m.faction == pup.faction:
				m.global_position = pup.global_position + Vector3(3, 0, 0)
				kin = [m]
				break
	p.global_position = main.zone.ground(pup.global_position.x + 3.0, pup.global_position.z) + Vector3.UP
	pup.hp = int(pup.max_hp * 0.1)
	pup.add_hate(p, 1.0)
	await _wait(0.5)
	print("flee: wounded pup with %d gnoll(s) nearby -> %s" % [kin.size(), Mob.State.keys()[pup.state]])
	for m: Mob in World.get_mobs():
		if m != pup and not m.dead and m.faction == pup.faction and m.distance_to(pup) <= World.CALL_FOR_HELP_RADIUS:
			m.global_position = pup.global_position + Vector3(60, 0, 60)  # its pack wanders off
	await _wait(0.5)
	print("flee: last gnoll nearby -> %s" % Mob.State.keys()[pup.state])
	World.kill(pup, p)


## Comparing a carried item with what you wear: the item window lists the
## changes (gains green, losses red), weapons compare delay too.
func _t_compare() -> void:
	var main := get_parent()
	var p := World.local_player
	var hud: Hud = main.hud
	var kit := p.equipment.duplicate()
	p.equipment["primary"] = "rusty_short_sword"
	p.equipment["head"] = "cloth_cap"
	p.recalc_stats()
	for id: String in ["iron_short_sword@superior", "iron_coif", "cloth_cap@crude", "tarnished_ring"]:
		print("compare: %s -> %s" % [id, " / ".join(hud._compare_lines(id)).strip_edges()])
	hud._toggle_inventory()
	hud.show_item("iron_short_sword@superior")
	await _wait(0.4)
	await _shot("9p_compare")
	hud._item_panel.visible = false
	hud._toggle_inventory()
	p.equipment = kit
	p.recalc_stats()


## Zone music: Greenmoor's theme here, Emberhold's after zoning, looping; the
## volume setting reaches the Music bus and keeps the rest of settings.json.
func _t_music() -> void:
	var main := get_parent()
	var playing := func() -> String:
		var p: AudioStreamPlayer = Music._players[Music._active]
		return "%s (%.0fs, loop %s, playing %s)" % [Music._current, p.stream.get_length() if p.stream else 0.0, p.stream.loop if p.stream else false, p.playing]
	print("music: in %s -> %s" % [main.zone.zone_id, playing.call()])
	await _ensure_zone("emberhold")
	await _wait(2.5)
	print("music: in %s -> %s; the other player faded to %.0f dB" % [main.zone.zone_id, playing.call(), Music._players[1 - Music._active].volume_db])
	var before := Controls.music_volume
	var had: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(Controls.SETTINGS_PATH)) if FileAccess.file_exists(Controls.SETTINGS_PATH) else {}
	Controls.set_music_volume(0.3)
	var saved: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(Controls.SETTINGS_PATH))
	var kept := had.keys().filter(func(k: String) -> bool: return k != "music_volume" and saved.get(k) == had[k]).size()
	print("music: volume 30%% -> bus %.1f dB; other settings kept %d/%d" % [AudioServer.get_bus_volume_db(AudioServer.get_bus_index("Music")), kept, had.keys().filter(func(k: String) -> bool: return k != "music_volume").size()])
	main.hud._show_settings(true)
	await _wait(0.3)
	await _shot("9q_settings_music")
	main.hud._show_settings(false)
	Controls.set_music_volume(before)
	await _ensure_zone("greenmoor")
	# combat music: a monster's hate brings it in, and it gives way a few calm seconds after
	var p := World.local_player
	var bus_db := func(bus: String) -> float: return AudioServer.get_bus_volume_db(AudioServer.get_bus_index(bus))
	var rat := _nearest_mob(p, "large_rat")
	p.global_position = main.zone.ground(rat.global_position.x + 3.0, rat.global_position.z) + Vector3.UP
	rat.add_hate(p, 5.0)
	await _wait(0.2 + Music.COMBAT_IN / 2.0)  # halfway through the fade in: both loud, no dip
	print("music: mid-fade -> zone %.1f dB, combat %.1f dB (mix %.2f)" % [bus_db.call("MusicZone"), bus_db.call("MusicCombat"), Music._mix])
	await _wait(1.4)
	print("music: rat angry -> threatened %s, combat on %s, zone %.0f dB, combat %.0f dB" % [p.threatened, Music._in_combat, bus_db.call("MusicZone"), bus_db.call("MusicCombat")])
	World.kill(rat, p)
	await _wait(2.0)
	print("music: rat dead 2 s -> threatened %s, combat still on %s" % [p.threatened, Music._in_combat])
	await _wait(5.5)
	print("music: calm 7.5 s -> combat on %s, zone %.0f dB, combat %.0f dB, zone theme %s" % [Music._in_combat, bus_db.call("MusicZone"), bus_db.call("MusicCombat"), Music._current])


## The Ember and Anvil beside the houses, for comparing how they're built.
func _t_tavern() -> void:
	var main := get_parent()
	var p := World.local_player
	for view: Array in [[Vector2(4, 2), "front"], [Vector2(30, 2), "side"]]:
		p.global_position = main.zone.ground(view[0].x, view[0].y) + Vector3.UP
		p.face_toward(main.zone.ground(17, -16))
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 4.0
		p.pitch = -0.05
		await _wait(0.6)
		await _shot("9r_tavern_%s" % view[1])
	# walk up the ramp and through the door
	p.global_position = main.zone.ground(10.0, -6.5) + Vector3.UP
	for k in 240:
		if not is_instance_valid(main.zone) or main.zone.is_queued_for_deletion() or main.zone.zone_id != "emberhold":
			break
		var to := Vector3(10.67, p.global_position.y, -9.96) - p.global_position
		p.velocity = to.normalized() * 4.0
		p.global_position += to.normalized() * 4.0 * get_physics_process_delta_time()
		await get_tree().physics_frame
	await _wait(2.0)
	print("tavern: walked to the door -> now in %s" % main.zone.zone_id)


## The cave mouth at the foot of the western mountains: seen from the meadow,
## then walked into, to the dark at the back.
func _t_cave() -> void:
	var main := get_parent()
	var p := World.local_player
	var mouth: Vector3 = main.zone.ground(-150, -30)
	p.global_position = main.zone.ground(-132, -24) + Vector3.UP
	p.face_toward(mouth)
	p.camera_pivot.rotation.y = 0.0
	p.zoom = 5.0
	p.pitch = -0.1
	await _wait(0.8)
	await _shot("9s_cave_outside")
	p.global_position = main.zone.ground(-147.5, -30) + Vector3.UP
	var start := p.global_position
	for k in 200:
		p.velocity = Vector3(-4, 0, 0)
		p.move_and_slide()
		await get_tree().physics_frame
	print("cave: walked in from x %.1f to x %.1f (tunnel back at about -159), floor y %.2f vs mouth %.2f" % [start.x, p.global_position.x, p.global_position.y, mouth.y])
	p.face_toward(p.global_position + Vector3(-5, 0, 0))
	p.zoom = 2.5
	await _wait(0.5)
	await _shot("9s_cave_inside")


## Walks (and sprints, and jumps) into each edge of the zone: the mountains
## should stop you well inside it, never let you fall off the world.
func _t_edges() -> void:
	var main := get_parent()
	var p := World.local_player
	var half: float = main.zone.half
	for dir: Vector2 in [Vector2(0, -1), Vector2(1, 0), Vector2(-1, 0), Vector2(0.7, -0.7), Vector2(-0.7, -0.7), Vector2(0.7, 0.7)]:
		if main.zone._pass_factor(dir.x * (half - 10.0), dir.y * (half - 10.0)) < 0.5:
			continue  # a real pass (a zone line or a rockslide there): tested on its own
		p.global_position = main.zone.ground(dir.x * (half - 60.0), dir.y * (half - 60.0)) + Vector3.UP
		p.velocity = Vector3.ZERO
		await _wait(0.2)
		var lowest := p.global_position.y
		var furthest := 0.0
		for k in 1200:
			var move := Vector3(dir.x, 0, dir.y) * 9.0
			p.velocity.x = move.x
			p.velocity.z = move.z
			if k % 20 == 0 and p.is_on_floor():
				p.velocity.y = 6.0  # keep jumping
			p.velocity.y -= 20.0 * get_physics_process_delta_time()
			p.move_and_slide()
			await get_tree().physics_frame
			lowest = minf(lowest, p.global_position.y)
			furthest = maxf(furthest, maxf(absf(p.global_position.x), absf(p.global_position.z)))
		print("edges: toward %s -> got to %.1f of %.0f from the middle, height now %.1f (terrain there %.1f), lowest %.1f" % [dir, furthest, half,
				p.global_position.y, main.zone.height_at(p.global_position.x, p.global_position.z), lowest])


## Thornwood Vale: arrive from Greenmoor's north pass, look around the
## obelisk, along the roads, at the closed passes; then every edge holds.
func _t_thornwood() -> void:
	var main := get_parent()
	var p := World.local_player
	print("thornwood: arrived at %s, terrain %.1f; %d trees placed" % [p.global_position, main.zone.height_at(p.global_position.x, p.global_position.z),
			main.zone.find_children("*", "StaticBody3D", true, false).size()])
	for view: Array in [[Vector2(0, 222), Vector2(0, 190), "arrival"], [Vector2(20, 60), Vector2(-40, -40), "forest"],
			[Vector2(0, -200), Vector2(0, -232), "north_pass"], [Vector2(118, -30), Vector2(150, -55), "camp"]]:
		p.global_position = main.zone.ground(view[0].x, view[0].y) + Vector3.UP
		p.face_toward(main.zone.ground(view[1].x, view[1].y))
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 6.0
		p.pitch = -0.15
		await _wait(0.7)
		await _shot("9t_thornwood_%s" % view[2])
	await _t_edges()
	for pass_: Array in [[Vector2(-190, 40), Vector2(-1, 0)], [Vector2(190, -20), Vector2(1, 0)], [Vector2(0, -190), Vector2(0, -1)]]:
		p.global_position = main.zone.ground(pass_[0].x, pass_[0].y) + Vector3.UP
		for k in 900:
			p.velocity = Vector3(pass_[1].x, 0, pass_[1].y) * 9.0 + Vector3(0, p.velocity.y - 20.0 * get_physics_process_delta_time(), 0)
			if k % 20 == 0 and p.is_on_floor():
				p.velocity.y = 6.0
			p.move_and_slide()
			await get_tree().physics_frame
		print("thornwood: into the pass toward %s -> stopped at %s (edge 256), height %.1f" % [pass_[1], Vector2(p.global_position.x, p.global_position.z), p.global_position.y])


## Thornwood's monsters: what spawned, a spider's venom landing, an orc in
## its gear, and a look at each part of the vale.
func _t_thornwood_mobs() -> void:
	var main := get_parent()
	var p := World.local_player
	var counts := {}
	for m in World.get_mobs():
		counts[m.mob_id] = int(counts.get(m.mob_id, 0)) + 1
	print("thornwood_mobs: %d monsters: %s" % [World.get_mobs().size(), counts])
	var orc: Mob = _nearest_mob(p, "orc_raider")
	print("thornwood_mobs: an orc raider lvl %d wears %s, look %s" % [orc.level, orc.gear, orc.look.get("worn", {})])
	# stand a tough character by a spider and let it bite until the venom lands
	p.level = 20
	p.recalc_stats()
	p.hp = p.max_hp
	var spider: Mob = _nearest_mob(p, "thornback_spider")
	p.global_position = main.zone.ground(spider.global_position.x + 2.0, spider.global_position.z) + Vector3.UP
	spider.add_hate(p, 10.0)
	var venom := false
	for k in 60:
		await _wait(0.5)
		p.hp = p.max_hp
		if p.dots.any(func(d: Dictionary) -> bool: return d["spell"] == "thornback_venom"):
			venom = true
			break
	print("thornwood_mobs: spider venom landed on me: %s" % venom)
	for m in World.get_mobs():
		m.hate.erase(p.entity_id)
	for view: Array in [["wolf", "timber_wolf"], ["bear", "black_bear"], ["spider", "thornback_spider"], ["orc", "orc_raider"], ["knight", "skeleton_knight"]]:
		var m: Mob = _nearest_mob(p, view[1])
		if m == null:
			continue
		m.hate.clear()
		m.set_physics_process(false)  # hold still for the picture
		var to := Vector3(5, 0, 5)
		p.global_position = main.zone.ground(m.global_position.x + to.x, m.global_position.z + to.z) + Vector3.UP
		p.face_toward(m.global_position)
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 4.0
		p.pitch = -0.15
		await _wait(0.6)
		await _shot("9u_mob_%s" % view[0])
		m.set_physics_process(true)
	p.level = 1
	p.recalc_stats()


## Elowen: her talk, both quests handed in (G at a merchant with the goods
## opens a trade), the rewards.
func _t_elowen() -> void:
	var p := World.local_player
	var elowen: Npc = _npcs()["elowen"]
	_stand_by(p, elowen)
	for word in ["hail", "wolves", "worse", "watchtower", "wolf pelts", "spider silk"]:
		World.request_say(p.entity_id, word)
	print("elowen: quests taken %s" % [["thinning_the_pack", "silk_and_venom"].map(func(q: String) -> bool: return p.quests.get(q, {}).get("active", false))])
	p.pack.add("wolf_pelt", 4)
	World.request_interact(p.entity_id)
	print("elowen: G with 4 pelts -> trading %s" % (p.trade_npc_id == elowen.entity_id))
	World.request_trade_cancel(p.entity_id)
	await _hand_in(p, elowen, ["wolf_pelt"])
	p.pack.add("spider_silk", 3)
	p.pack.add("venom_sac", 1)
	await _hand_in(p, elowen, ["spider_silk", "venom_sac"])
	print("elowen: rewards: boots %d, gloves %d" % [p.pack.count("wolfhide_boots"), p.pack.count("silkweave_gloves")])
	World.request_interact(p.entity_id)
	print("elowen: G with nothing to give -> shop open %s" % (p.service_npc_id == elowen.entity_id and p.service == "shop"))
	World.request_service_close(p.entity_id)


## Which way each signpost board points, in every zone (compare with where
## the place it names actually is).
func _t_signs() -> void:
	for zone_id: String in ["greenmoor", "thornwood"]:
		await _ensure_zone(zone_id)
		var zone: Zone = get_parent().zone
		for post: Node3D in zone.find_children("*", "Node3D", true, false):
			var labels := post.find_children("*", "Label3D", false, false)
			if labels.is_empty():
				continue
			if labels.size() > 2:
				labels = labels.slice(0, labels.size(), 2)  # both faces of a board say the same thing
			var out := PackedStringArray()
			for l: Label3D in labels:
				var dir := (post.global_transform * l.position - post.global_position)
				dir.y = 0
				var compass := "E" if absf(dir.x) > absf(dir.z) and dir.x > 0 else ("W" if absf(dir.x) > absf(dir.z) else ("S" if dir.z > 0 else "N"))
				out.append("%s -> %s" % [l.text, compass])
			print("signs: %s at (%.0f, %.0f): %s" % [zone_id, post.global_position.x, post.global_position.z, ", ".join(out)])


## Thornwood's river: walk the road north over the bridge (never dropping into
## the water), then wade across the channel beside it; pictures of both.
func _t_river() -> void:
	var main := get_parent()
	var p := World.local_player
	for m in World.get_mobs():
		m.set_physics_process(false)  # nobody interrupts the survey
	p.global_position = main.zone.ground(-1.0, 130.0) + Vector3.UP
	var lowest := INF
	var dir := (Vector2(8, 80) - Vector2(-4, 150)).normalized()
	for k in 360:
		p.velocity = Vector3(dir.x, 0, dir.y) * 6.0 + Vector3(0, p.velocity.y - 20.0 * get_physics_process_delta_time(), 0)
		p.move_and_slide()
		await get_tree().physics_frame
		if absf(p.global_position.z - 106.0) < 8.0:
			lowest = minf(lowest, p.global_position.y)
	var level: float = main.zone._river_at(main.zone._rivers[0], 3.5, 106.0)[1]
	print("river: over the bridge from z 130 to %.0f; lowest on the crossing %.2f, water level %.2f" % [p.global_position.z, lowest, level])
	p.global_position = main.zone.ground(-30.0, 130.0) + Vector3.UP
	var deepest := INF
	for k in 360:
		p.velocity = Vector3(0, p.velocity.y - 20.0 * get_physics_process_delta_time(), -6.0)
		p.move_and_slide()
		await get_tree().physics_frame
		deepest = minf(deepest, p.global_position.y)
	print("river: waded across at x -30 to z %.0f; deepest %.2f (%.2f under the water)" % [p.global_position.z, deepest, level - deepest])
	for view: Array in [[Vector2(-18, 128), Vector2(3.5, 106), "bridge"], [Vector2(-60, 125), Vector2(-100, 100), "banks"]]:
		p.global_position = main.zone.ground(view[0].x, view[0].y) + Vector3.UP
		p.face_toward(main.zone.ground(view[1].x, view[1].y))
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 6.0
		p.pitch = -0.25
		await _wait(0.7)
		await _shot("9v_river_%s" % view[2])
	for m in World.get_mobs():
		m.set_physics_process(true)


## Thornwood's landmarks: the ruined watchtower, the spider nest, Elowen's cabin.
func _t_landmarks_tw() -> void:
	var main := get_parent()
	var p := World.local_player
	for m in World.get_mobs():
		m.set_physics_process(false)
	for view: Array in [[Vector2(-8, -158), Vector2(-24, -181), "watchtower", 9.0], [Vector2(-150, -92), Vector2(-165, -104), "nest", 7.0],
			[Vector2(-20, 192), Vector2(-38, 176), "cabin", 6.0]]:
		p.global_position = main.zone.ground(view[0].x, view[0].y) + Vector3.UP
		p.face_toward(main.zone.ground(view[1].x, view[1].y))
		p.camera_pivot.rotation.y = 0.0
		p.zoom = view[3]
		p.pitch = -0.2
		await _wait(0.8)
		await _shot("9w_%s" % view[2])
	for m in World.get_mobs():
		m.set_physics_process(true)


## Group chat's own window: hidden when solo, shown in a group; group lines
## land in it (and still in the main log), other chat doesn't; the Talk button
## switches the chat line to /g.
func _t_groupchat() -> void:
	var main := get_parent()
	var p := World.local_player
	var hud: Hud = main.hud
	hud._update_group()
	print("groupchat: solo -> window shown %s" % hud._group_log_panel.visible)
	p.group = [{"id": p.entity_id, "name": p.display_name, "level": p.level, "class": p.char_class, "hp": p.hp, "max_hp": p.max_hp, "mana": p.mana, "max_mana": p.max_mana, "leader": true, "zone": "greenmoor", "dead": false},
		{"id": 9002, "name": "Nick", "level": 8, "class": "cleric", "hp": 60, "max_hp": 70, "mana": 50, "max_mana": 80, "leader": false, "zone": "greenmoor", "dead": false}]
	hud._update_group()
	World.log_message.emit("Nick tells the group, 'pulling the bear, get ready'", World.C_CHAT_GROUP)
	World.log_message.emit("A black bear claws YOU for 9 points of damage.", World.C_HIT_YOU)
	World.log_message.emit("You tell your party, '{item:silkfangs_fang} dropped, anyone want it?'", World.C_CHAT_GROUP)
	World.log_message.emit("You say, 'hello'", World.C_CHAT_SAY)
	print("groupchat: grouped -> window shown %s; it holds %d lines: %s" % [hud._group_log_panel.visible, hud._group_log_lines, hud._group_log.get_parsed_text().replace("\n", " | ")])
	var talk: Button = hud._group_log_panel.find_children("*", "Button", true, false)[0]
	talk.pressed.emit()
	print("groupchat: Talk button -> channel '%s', typing %s" % [hud._chat_channel, hud.is_typing()])
	await _wait(0.4)
	await _shot("9x_group_chat")
	hud._chat.release_focus()
	hud._set_channel("")
	p.group = []
	hud._update_group()
	print("groupchat: left the group -> window shown %s" % hud._group_log_panel.visible)


## Bows drop: how often scouts and raiders roll one (2000 rolls each), and a
## scout killed with a bow and arrows on it leaves both on its corpse.
func _t_bowdrops() -> void:
	var main := get_parent()
	var p := World.local_player
	for mob_id: String in ["gnoll_scout", "orc_raider", "grolthar"]:
		var bows := {}
		for k in 2000:
			var g: Dictionary = World.roll_gear(GameData.mobs[mob_id], 10)
			if g.has("range"):
				var base := GameData.base_item(str(g["range"]))
				bows[base] = int(bows.get(base, 0)) + 1
		print("bowdrops: %s carries a bow %s in 2000 spawns" % [mob_id, bows])
	var scout := _nearest_mob(p, "gnoll_scout")
	scout.gear["range"] = "hunting_shortbow@fine"
	var loot: Array = scout.data["loot"].duplicate(true)
	for e: Dictionary in scout.data["loot"]:
		if e["item"] == "crude_arrow":
			e["chance"] = 1.0
	World.kill(scout, p)
	scout.data["loot"] = loot
	var body: Corpse = null
	for obj: Variant in World.objects.values():
		if obj is Corpse and not (obj as Node).is_queued_for_deletion() and (obj as Corpse).display_name.begins_with(scout.display_name):
			body = obj
	print("bowdrops: the scout's corpse holds %s" % [body.entries.map(func(e: Dictionary) -> String: return "%s x%d" % [e["item"], int(e.get("count", 1))])])
	p.global_position = body.global_position + Vector3(0, 1, 1)
	World.request_loot_open(p.entity_id, body.object_id)
	World.request_loot_all(p.entity_id, body.object_id)
	print("bowdrops: looted -> bow %d, arrows %d" % [p.pack.count("hunting_shortbow@fine"), p.pack.count("crude_arrow")])
	# a bag that drops as loot (not a dead player's) comes with all its slots
	var scout2 := _nearest_mob(p, "gnoll_scout")
	scout2.data["loot"].append({"item": "gnollhide_satchel", "chance": 1.0})
	World.kill(scout2, p)
	scout2.data["loot"].pop_back()
	for obj: Variant in World.objects.values():
		if obj is Corpse and not (obj as Node).is_queued_for_deletion() and (obj as Corpse).display_name.begins_with(scout2.display_name):
			p.global_position = (obj as Corpse).global_position + Vector3(0, 1, 1)
			World.request_loot_open(p.entity_id, (obj as Corpse).object_id)
			World.request_loot_all(p.entity_id, (obj as Corpse).object_id)
	var bag := p.pack.get_at(_where(p, "gnollhide_satchel"))
	print("bowdrops: looted satchel has %d slots (should be %d)" % [(bag.get("contents", []) as Array).size(), Pack.bag_size_of("gnollhide_satchel")])


## Blessing of the Elders: +15% experience below level 10, fading on reaching
## it; the buff window lists it with a timed buff, and moves aside for the
## inventory window.
func _t_blessing() -> void:
	var main := get_parent()
	var p := World.local_player
	var hud: Hud = main.hud
	var keep := [p.level, p.xp]
	p.level = 3
	p.xp = 0
	p.add_xp(100)
	print("blessing: level 3 gains 100 -> %d xp (blessed %s)" % [p.xp, p.elders_blessing()])
	p.spells.append("minor_shielding")
	p.buffs["minor_shielding"] = {"left": 1500.0, "stats": GameData.spells["minor_shielding"].get("stats", {})}
	p.buffs["courage"] = {"left": 42.0, "stats": GameData.spells["courage"].get("stats", {})}
	await _wait(0.4)
	var shown := hud._buff_rows.get_children().filter(func(c: Node) -> bool: return c.has_meta("spell")).map(func(c: Node) -> String:
		return "%s (%s)" % [c.get_meta("spell"), (c.find_child("left", true, false) as Label).text])
	print("blessing: buff window shows %s at %s" % [shown, hud._buff_panel.position])
	print("blessing: tooltips:\n%s\n--\n%s" % [hud._buff_tooltip("blessing_of_the_elders", -1.0), hud._buff_tooltip("courage", 42.0)])
	await _shot("9y_buffs")
	hud._toggle_inventory()
	await _wait(0.3)
	print("blessing: inventory open -> buff window right edge %.0f, inventory left edge %.0f" % [hud._buff_panel.position.x + hud._buff_panel.size.x, hud._inv_panel.position.x])
	await _shot("9y_buffs_inventory")
	hud._toggle_inventory()
	p.level = int(World.cfg("elders_blessing", {}).get("until_level", 10)) - 1
	p.xp = 0
	p.add_xp(p.xp_to_next() + 10)
	await _wait(0.3)
	var left := hud._buff_rows.get_children().filter(func(c: Node) -> bool: return c.has_meta("spell")).map(func(c: Node) -> String: return str(c.get_meta("spell")))
	print("blessing: reached level %d -> blessed %s; buffs shown %s" % [p.level, p.elders_blessing(), left])
	p.xp = 0
	p.add_xp(100)
	print("blessing: at level %d, 100 more -> %d xp (no blessing now; the cap is %d)" % [p.level, p.xp, int(World.cfg("max_level", 10))])
	p.level = 14
	p.xp = 0
	p.add_xp(p.xp_to_next() * 3)
	print("blessing: a level 14 with plenty of experience stops at level %d" % p.level)
	p.buffs.clear()
	p.level = keep[0]
	p.xp = keep[1]
	p.recalc_stats()


## The level 11-15 spells: each is taught at its level, then cast (on a mob,
## on the tester or the group) and checked for its effect.
func _t_spells_1115() -> void:
	var main := get_parent()
	var p := World.local_player
	var keep := {"level": p.level, "spells": p.spells.duplicate(), "equipment": p.equipment.duplicate(), "class": p.char_class}
	var ids := ["heroic_strike", "rally", "shield_wall", "healing", "blessed_armor", "circle_of_renewal", "hallowed_strike", "frost_lance", "emberstorm", "greater_shielding", "ice_comet"]
	for cls: String in ["warrior", "cleric", "wizard"]:
		var taught := World.class_spells(cls).filter(func(e: Dictionary) -> bool: return int(e["level"]) >= 11).map(func(e: Dictionary) -> String: return "%s@%d" % [e["spell"], e["level"]])
		print("spells_1115: %s learns %s" % [cls, taught])
	p.level = 15
	p.recalc_stats()
	p.spells = ids.duplicate()
	p.equipment["secondary"] = "round_shield"
	p.recalc_stats()
	for id: String in ids:
		p.skills[str(GameData.spells[id].get("skill", ""))] = 200  # never fizzle for the test
		var s: Dictionary = GameData.spells[id]
		var mob := _nearest_mob(p, "gnoll_pup")
		mob.hp = mob.max_hp
		p.global_position = main.zone.ground(mob.global_position.x + 2.0, mob.global_position.z) + Vector3.UP
		World.request_set_target(p.entity_id, mob.entity_id if s["target"] == "enemy" else p.entity_id)
		p.mana = p.max_mana
		p.hp = maxi(1, p.max_hp / 3)
		p.cooldowns.clear()
		var before := [mob.hp, p.hp, p.buffs.keys(), mob.dots.size()]
		World.request_cast(p.entity_id, id)
		await _wait(float(s.get("cast_time", 0)) + 0.3)
		var effect := ""
		match str(s["type"]):
			"damage":
				effect = "mob hp %d -> %s" % [before[0], str(mob.hp) if is_instance_valid(mob) and not mob.dead else "dead"]
			"heal":
				effect = "my hp %d -> %d" % [before[1], p.hp]
			"buff":
				effect = "buffed %s" % p.buffs.has(id)
			"dot":
				effect = "dots on mob %d -> %d" % [before[3], mob.dots.size() if is_instance_valid(mob) else -1]
		print("spells_1115: %s -> %s" % [id, effect])
		if is_instance_valid(mob):
			mob.hate.clear()
	p.buffs.clear()
	p.level = keep["level"]
	p.spells = keep["spells"]
	p.equipment = keep["equipment"]
	p.recalc_stats()


## Spell effects and ability moves, caught mid-flight: the casting glow, a
## frost nuke, a burn, a heal, a buff, a root, a gate; a kick and a bash.
func _t_fx() -> void:
	var main := get_parent()
	var p := World.local_player
	var keep := {"level": p.level, "spells": p.spells.duplicate(), "equipment": p.equipment.duplicate()}
	p.level = 15
	p.spells = ["blast_of_frost", "emberstorm", "healing", "blessed_armor", "root", "gate", "kick", "bash"]
	p.equipment["secondary"] = "round_shield"
	p.recalc_stats()
	for id: String in p.spells:
		p.skills[str(GameData.spells[id].get("skill", ""))] = 200
	var mob := _nearest_mob(p, "gnoll_pup")
	mob.set_physics_process(false)
	mob.max_hp = 9999
	mob.hp = 9999
	for shot: Array in [["blast_of_frost", 0.35, "frost"], ["emberstorm", 0.5, "burn"], ["root", 0.4, "root"], ["kick", 0.33, "kick"], ["bash", 0.3, "bash"],
			["healing", 0.5, "heal"], ["blessed_armor", 0.45, "buff"], ["gate", 0.35, "gate"]]:
		var id: String = shot[0]
		var s: Dictionary = GameData.spells[id]
		p.global_position = main.zone.ground(mob.global_position.x + 2.2, mob.global_position.z + 1.0) + Vector3.UP
		p.face_toward(mob.global_position)
		p.camera_pivot.rotation.y = 0.9
		p.zoom = 4.5
		p.pitch = -0.2
		World.request_set_target(p.entity_id, mob.entity_id if s["target"] == "enemy" else p.entity_id)
		p.mana = p.max_mana
		p.hp = p.max_hp / 2
		p.cooldowns.clear()
		World.request_cast(p.entity_id, id)
		if float(s.get("cast_time", 0)) > 0.0:
			await _wait(float(s["cast_time"]) * 0.5)
			if id == "blast_of_frost":
				await _shot("9z_fx_casting")
			await _wait(float(s["cast_time"]) * 0.5)
		await _wait(shot[1])
		await _shot("9z_fx_%s" % shot[2])
		await _wait(1.2)
	mob.set_physics_process(true)
	p.level = keep["level"]
	p.spells = keep["spells"]
	p.equipment = keep["equipment"]
	p.buffs.clear()
	p.recalc_stats()


## Warden Holt defends his post: an aggressive gnoll walking up gets cut down;
## a rat wandering by is left alone; afterwards he goes back to his spot.
func _t_holt() -> void:
	var main := get_parent()
	var holt: Npc = _npcs()["warden_holt"]
	var post := holt.global_position
	var p := World.local_player
	var place := func(m: Mob, dx: float, dz: float) -> void:
		m.global_position = main.zone.ground(post.x + dx, post.z + dz) + Vector3.UP * 0.5
		m.set_physics_process(false)
	var rat := _nearest_mob(holt, "large_rat")
	place.call(rat, 6.0, 3.0)
	var scout := _nearest_mob(holt, "gnoll_scout")
	place.call(scout, -9.0, 4.0)
	await _wait(3.0)
	print("holt: gnoll scout (aggressive) at %.0f m -> fighting it %s; rat (peaceful, calm) at %.0f m -> fighting it %s" % [
			holt.distance_to(scout), holt.target == scout, holt.distance_to(rat), holt.target == rat])
	scout.set_physics_process(true)
	for k in 40:
		await _wait(0.5)
		if not is_instance_valid(scout) or scout.dead:
			break
	# a peaceful pup, but chasing the tester past his post
	var pup := _nearest_mob(holt, "gnoll_pup")
	place.call(pup, 8.0, -6.0)
	p.global_position = main.zone.ground(post.x + 10.0, post.z - 7.0) + Vector3.UP
	pup.add_hate(p, 5.0)
	await _wait(3.0)
	print("holt: scout dead %s; a pup fighting someone at %.0f m -> fighting it %s" % [not is_instance_valid(scout) or scout.dead, holt.distance_to(pup), holt.target == pup])
	pup.set_physics_process(true)
	for k in 40:
		await _wait(0.5)
		if not is_instance_valid(pup) or pup.dead:
			break
	await _wait(6.0)
	print("holt: pup dead %s; rat still alive %s; Holt back at his post %s (%.1f m off)" % [not is_instance_valid(pup) or pup.dead, is_instance_valid(rat) and not rat.dead, holt.global_position.distance_to(post) < 1.5, holt.global_position.distance_to(post)])
	if is_instance_valid(rat):
		rat.set_physics_process(true)


## The signpost by the Emberhold pass, from the road on each side.
func _t_signface() -> void:
	var main := get_parent()
	var p := World.local_player
	for side: Array in [[Vector2(-1.5, 161.5), "south"], [Vector2(-1.5, 150.5), "north"]]:
		p.global_position = main.zone.ground(side[0].x, side[0].y) + Vector3.UP
		p.face_toward(main.zone.ground(4.5, 156.0))
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 0.0  # first person: nothing between the eye and the sign
		p.pitch = 0.12
		await _wait(0.5)
		await _shot("9za_sign_from_%s" % side[1])


## Sergeant Harlan walks Thornwood's south road over the bridge to the
## crossroads and back; a wolf chasing the tester near him gets cut down.
func _t_vale_patrol() -> void:
	var main := get_parent()
	var p := World.local_player
	var harlan: Npc = _npcs()["vale_patrol"]
	var lowest_on_bridge := INF
	var reached := 0.0
	for k in 110:  # most of a leg, watching him cross the bridge
		await _wait(0.5)
		var at := harlan.global_position
		reached = minf(reached, at.z) if reached != 0.0 else at.z
		if absf(at.z - 106.0) < 6.0:
			lowest_on_bridge = minf(lowest_on_bridge, at.y)
	var level: float = main.zone._river_at(main.zone._rivers[0], 3.5, 106.0)[1]
	print("vale_patrol: Harlan (level %d) walked from z 212 to z %.0f; on the bridge his lowest was %.2f (water %.2f)" % [harlan.level, reached, lowest_on_bridge, level])
	for k in 60:  # off the bridge (its railings would keep him from a wolf in the river)
		if harlan.global_position.z < 88.0:
			break
		await _wait(0.5)
	var wolf := _nearest_mob(harlan, "timber_wolf")
	var g: Vector3 = main.zone.ground(harlan.global_position.x + 6.0, harlan.global_position.z)
	p.global_position = g + Vector3.UP
	wolf.global_position = main.zone.ground(harlan.global_position.x + 12.0, harlan.global_position.z - 2.0) + Vector3.UP * 0.5
	wolf.add_hate(p, 5.0)
	p.hp = p.max_hp
	await _wait(3.0)
	print("vale_patrol: a wolf chasing me near him -> Harlan fighting it %s" % (harlan.target == wolf))
	for k in 30:
		await _wait(0.5)
		p.hp = p.max_hp
		if not is_instance_valid(wolf) or wolf.dead:
			break
	print("vale_patrol: wolf dead %s (hp %s); Harlan hp %d/%d" % [not is_instance_valid(wolf) or wolf.dead, str(wolf.hp) if is_instance_valid(wolf) else "-", harlan.hp, harlan.max_hp])


## The bag bar over the hotbar: bags with fill counts, free slots, a quest
## item marked, the sling's stones counted on the Ranged button, a loot note,
## and a peek inside a bag.
func _t_bagbar() -> void:
	var main := get_parent()
	var p := World.local_player
	var hud: Hud = main.hud
	p.pack.clear()
	var sack := Pack.entry("small_sack")
	for i in 4:
		(sack["contents"] as Array)[i] = Pack.entry(["rat_whiskers", "bone_chips", "beetle_eye", "gnoll_fang"][i], 3 + i)
	p.pack.slots[0] = sack
	p.pack.slots[1] = Pack.entry("leather_backpack")
	(p.pack.slots[1]["contents"] as Array)[0] = Pack.entry("iron_dagger")
	p.pack.slots[2] = Pack.entry("gnoll_fang", 2)
	p.pack.add("sling_stone", 42)
	p.pack.add("leather_sling")
	World.request_equip(p.entity_id, _where(p, "leather_sling"))
	p.quests["fang_bounty"] = {"active": true, "completions": 0}
	p.inventory_changed.emit()
	await _wait(0.3)
	var fills := []
	for g in Pack.GENERAL:
		var b := hud._bag_bar_slot(g)
		fills.append((b.find_child("fill", false, false) as Label).text)
	var fang := hud._slot_buttons["g:2"][1] as Button
	print("bagbar: fills %s, %s; fang marked %s: %s; ranged count '%s'" % [fills, hud._bag_free.text, (fang.get_child(2) as Label).visible,
			fang.tooltip_text.get_slice("Quest:", 1).strip_edges(), hud._ranged_slot.count_text])
	p.pack.add("wolf_pelt", 3)
	p.inventory_changed.emit()
	World.request_click(p.entity_id, "g:2")  # picking up and putting back is not new loot
	World.request_click(p.entity_id, "g:2")
	await _wait(0.2)
	print("bagbar: toasts now %s" % [hud._toasts.get_children().map(func(r: Node) -> String: return (r.get_child(1) as Label).text)])
	hud._peek_bag(0, hud._bag_bar_slot(0))
	await _wait(0.3)
	await _shot("9zb_bagbar")
	hud._peek_bag(-1, null)
	hud._toggle_bag(1)
	await _wait(0.3)
	print("bagbar: backpack opened from the bar at %s (bar top %.0f)" % [hud._bag_windows[1].position, hud._bag_bar.position.y])
	await _shot("9zb_bagbar_open")
	hud._toggle_bag(1)
	p.quests.erase("fang_bounty")
	p.equipment.erase("range")
	p.recalc_stats()


## The debuff window: a spider's venom and a root on the tester, listed under
## the buffs with time left; the venom's ticks name it in the log.
func _t_debuffs() -> void:
	var main := get_parent()
	var p := World.local_player
	var hud: Hud = main.hud
	p.level = 12
	p.recalc_stats()
	p.hp = p.max_hp
	var spider_data: Dictionary = GameData.mobs["thornback_spider"]
	var mob := _nearest_mob(p, "gnoll_pup")
	World._finish_spell(mob, "thornback_venom", p, true)  # as if a spider's bite landed it
	p.root_left = 12.0
	await _wait(3.5)
	var rows := hud._debuff_rows.get_children().filter(func(c: Node) -> bool: return c.has_meta("spell")).map(func(c: Node) -> String:
		return "%s (%s)" % [c.get_meta("spell"), (c.find_child("left", true, false) as Label).text])
	print("debuffs: window shown %s at %s under buffs at %s: %s" % [hud._debuff_panel.visible, hud._debuff_panel.position, hud._buff_panel.position, rows])
	print("debuffs: tooltip:\n%s" % hud._buff_tooltip("thornback_venom", 9.0))
	await _shot("9zc_debuffs")
	p.dots.clear()
	p.root_left = 0.0
	await _wait(0.3)
	print("debuffs: cured -> window shown %s" % hud._debuff_panel.visible)
	p.level = 1
	p.recalc_stats()


## Moves the tester through the zone line into this zone if it isn't there.
func _ensure_zone(zone_id: String) -> void:
	var main := get_parent()
	var p := World.local_player
	if main.zone.zone_id == zone_id:
		return
	if p.dead:
		await _wait(5.0)
	# step into the zone line that starts the shortest way there
	for hop in 5:
		if main.zone.zone_id == zone_id:
			break
		var next := _next_hop(main.zone.zone_id, zone_id)
		var line: Dictionary = {}
		for zl: Dictionary in main.zone.data.get("zone_lines", []):
			if zl["to"] == next:
				line = zl
		if line.is_empty():
			break
		p.global_position = main.zone.ground(line["pos"][0], line["pos"][1]) + Vector3.UP
		await _wait(2.5)
	print("zone: %s at %s" % [main.zone.zone_id, p.global_position])


## The first zone on the way from one zone to another, following zone lines.
func _next_hop(from: String, to: String) -> String:
	var came := {from: ""}
	var queue: Array = [from]
	while not queue.is_empty():
		var at: String = queue.pop_front()
		if at == to:
			break
		for zl: Dictionary in GameData.load_zone(at).get("zone_lines", []):
			var nxt := str(zl["to"])
			if not came.has(nxt):
				came[nxt] = at
				queue.append(nxt)
	if not came.has(to):
		return ""
	var step := to
	while came[step] != from:
		step = came[step]
	return step


## Where an item is in the pack ("g:2", "b:0:3"), or "".
func _where(p: Player, item_id: String) -> String:
	for place: String in p.pack.places():
		if p.pack.get_at(place).get("item", "") == item_id:
			return place
	return ""


func _npcs() -> Dictionary:
	var out := {}
	for obj: Node3D in World.objects.values():
		if obj is Npc:
			out[(obj as Npc).npc_id] = obj
	return out


func _nearest_mob(p: Entity, only_id := "") -> Mob:
	var best: Mob = null
	for m in World.get_mobs():
		if not m.dead and (only_id == "" or m.mob_id == only_id) and (best == null or p.distance_to(m) < p.distance_to(best)):
			best = m
	return best


func _wait(seconds: float) -> void:
	await get_tree().create_timer(seconds).timeout


func _shot(name_: String) -> void:
	if shots_dir == "":
		return
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png("%s/%s.png" % [shots_dir, name_])


## The character window stands on the bag bar (no General row of its own);
## the item tips and faction list fold away behind buttons.
func _t_invwindow() -> void:
	var main := get_parent()
	var hud: Hud = main.hud
	hud._toggle_inventory()
	await _wait(0.4)
	var inv: Control = hud._inv_panel
	print("invwindow: bottom %.0f, bag bar top %.0f; right %.0f, bar right %.0f; size %s" % [inv.position.y + inv.size.y, hud._bag_bar.position.y,
			inv.position.x + inv.size.x, hud._bag_bar.position.x + hud._bag_bar.size.x, inv.size])
	print("invwindow: tips shown %s, faction shown %s" % [hud._bag_hint.visible, hud._faction_label.visible])
	await _shot("9zd_inventory")
	hud._bag_hint.visible = true
	hud._faction_label.visible = true
	await _wait(0.3)
	print("invwindow: expanded size %s, top %.0f" % [inv.size, inv.position.y])
	await _shot("9zd_inventory_expanded")
	hud._bag_hint.visible = false
	hud._faction_label.visible = false
	hud._toggle_inventory()


## Thornwood's fuller spawns: every monster up and standing on the ground,
## and Sergeant Harlan finding something to fight along his road.
func _t_tw_density() -> void:
	var main := get_parent()
	var p := World.local_player
	var mobs := World.get_mobs()
	var off := 0
	for m in mobs:
		if absf(m.global_position.y - main.zone.height_at(m.global_position.x, m.global_position.z)) > 1.5:
			off += 1
	print("tw_density: %d monsters (%d spawn points), %d off the ground" % [mobs.size(), main.zone.find_children("*", "", true, false).filter(func(n: Node) -> bool: return n.get("respawn_time") != null).size(), off])
	p.global_position = main.zone.ground(-60, 230) + Vector3.UP  # out of the way
	var harlan: Npc = _npcs()["vale_patrol"]
	var fought := {}
	for k in 240:
		await _wait(0.5)
		if is_instance_valid(harlan.target) and harlan.target is Mob:
			fought[(harlan.target as Mob).entity_id] = (harlan.target as Mob).mob_id
	print("tw_density: in two minutes Harlan fought %s" % [fought.values()])


## A repeatable quest pays full experience the first time, half after.
func _t_quest_repeat() -> void:
	var p := World.local_player
	var holt: Npc = _npcs()["warden_holt"]
	p.level = 12
	p.xp = 0
	p.recalc_stats()
	p.quests.erase("fang_bounty")
	World._accept_quest(p, "fang_bounty")
	var gains: Array = []
	for k in 3:
		var before := p.xp
		World._complete_quest(p, holt, "fang_bounty")
		gains.append(p.xp - before)
	print("quest_repeat: fang bounty xp for turn-ins 1, 2, 3: %s (quest reward %d)" % [gains, int(GameData.quests["fang_bounty"]["reward"]["xp"])])
	p.quests.erase("fang_bounty")


## Every guard stands 15 levels over the level cap.
func _t_guard_levels() -> void:
	var levels := {}
	for npc: Npc in _npcs().values():
		if not npc.guard.is_empty():
			levels[npc.npc_id] = npc.level
	print("guard_levels: cap %d -> %s" % [int(World.cfg("max_level", 10)), levels])


## A bow shot shows the bow in the left hand, drawn, with the sword and shield
## put away until it's loosed; B opens every bag and Esc closes them.
func _t_bowshot() -> void:
	var main := get_parent()
	var p := World.local_player
	var hud: Hud = main.hud
	p.pack.clear()
	for g in 5:
		p.pack.slots[g] = Pack.entry(["small_sack", "worn_backpack", "gnollhide_satchel", "leather_backpack", "small_sack"][g])
	p.pack.add("crude_arrow", 20)
	p.equipment["range"] = "hunting_shortbow"  # warriors only; the tester is a wizard
	p.recalc_stats()
	p.inventory_changed.emit()
	var rat: Mob = _nearest_mob(p, "large_rat")
	for k in 12:  # somewhere around the rat with a clear line to it
		var off := Vector2.from_angle(k * TAU / 12.0) * 12.0
		p.global_position = main.zone.ground(rat.global_position.x + off.x, rat.global_position.z + off.y) + Vector3.UP
		await _wait(0.1)
		if World.in_sight(p, rat):
			break
	p.face_toward(rat.global_position)
	p.target = rat
	await _wait(0.4)
	var m := p.visual as CharacterModel
	World.request_ranged(p.entity_id)
	await _wait(0.45)
	var sword_hidden := m._held.values().all(func(h: Array) -> bool: return h[1] == null or not (h[1] as Node3D).visible)
	print("bowshot: mid-shot clip %s, bow shown %s, held gear hidden %s" % [m.anim.current_animation, m._ranged != null, sword_hidden])
	p.camera_pivot.rotation.y = -1.3  # from the side
	p.zoom = 4.0
	await _shot("9zf_bowshot_side")
	p.camera_pivot.rotation.y = 0.0
	await _wait(1.2)
	print("bowshot: after the shot, bow gone %s, held gear back %s" % [m._ranged == null,
			m._held.values().all(func(h: Array) -> bool: return h[1] == null or (h[1] as Node3D).visible)])
	rat.hate.clear()
	hud._toggle_all_bags()
	await _wait(0.3)
	var rects := hud._bag_windows.values().map(func(w: Control) -> Rect2: return Rect2(w.position, w.size))
	var overlap := false
	for i in rects.size():
		for j in range(i + 1, rects.size()):
			overlap = overlap or (rects[i] as Rect2).intersects(rects[j])
	print("bowshot: B opened %d bags, overlapping %s" % [hud._bag_windows.size(), overlap])
	await _shot("9zf_all_bags")
	var esc := InputEventKey.new()
	esc.keycode = KEY_ESCAPE
	esc.physical_keycode = KEY_ESCAPE
	esc.pressed = true
	Input.parse_input_event(esc)
	await _wait(0.2)
	print("bowshot: after Esc, %d bags open" % hud._bag_windows.size())


## A shop's "Buy 20" button beside ammunition.
func _t_buy_bundle() -> void:
	var main := get_parent()
	var p := World.local_player
	var hud: Hud = main.hud
	var elowen: Npc = _npcs()["elowen"]
	_stand_by(p, elowen)
	p.pack.clear()
	p.coin = 1000
	World.request_interact(p.entity_id)
	await _wait(0.3)
	var pressed := 0
	for row in hud._shop_list.get_children():
		if row is HBoxContainer:
			var name := ((row as HBoxContainer).get_child(0) as Button).text.get_slice("   ", 0)
			var bundle := (row as HBoxContainer).get_child(1) as Button
			if name in ["Crude Arrow", "Sling Stone"]:
				bundle.pressed.emit()
				pressed += 1
	await _wait(0.3)
	print("buy_bundle: pressed %d bundle buttons -> arrows %d, stones %d, coin %d left of 1000" % [pressed, p.pack.count("crude_arrow"), p.pack.count("sling_stone"), p.coin])
	await _shot("9zg_shop_bundle")
	World.request_service_close(p.entity_id)


## Guard Corwin walks the whole road: the Emberhold gate, around the obelisk's
## stones, past the outpost to the Thornwood pass, and back.
func _t_corwin_route() -> void:
	var p := World.local_player
	var corwin: Npc = _npcs()["watch_patrol"]
	p.global_position = Vector3(-60, p.global_position.y, 150)  # out of his way
	Engine.time_scale = 6.0
	var north := INF
	var closest_to_obelisk := INF
	var stuck := 0.0
	var last := corwin.global_position
	var turned_back := false
	for k in 400:
		await get_tree().create_timer(0.5, true, false, true).timeout  # real seconds: 3 game seconds each
		var at := corwin.global_position
		north = minf(north, at.z)
		if absf(at.z) < 15.0:
			closest_to_obelisk = minf(closest_to_obelisk, Vector2(at.x, at.z).length())
		stuck = stuck + 3.0 if at.distance_to(last) < 0.3 and corwin.target == null else 0.0
		if stuck > 12.0:
			print("corwin_route: STUCK at %s" % at)
			break
		last = at
		if north < -165.0 and at.z > -120.0:
			turned_back = true
			break
	Engine.time_scale = 1.0
	print("corwin_route: reached z %.0f (road ends at -192, zone line -177), nearest the obelisk %.1f m (stones at 7), heading back %s" % [north, closest_to_obelisk, turned_back])


## "Remember password" on the server login, against a throwaway local server:
##   godot --headless --path . -- --server --port=7791 --data=<tmp dir>
##   godot --path . -- --autotest --only=remember_login --login-port=7791
## Skipped without --login-port. Cleans its entry out of settings.json.
func _t_remember_login() -> void:
	var port := 0
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--login-port="):
			port = int(a.substr(13))
	if port == 0:
		print("remember_login: skipped (no --login-port)")
		return
	var address := "127.0.0.1:%d" % port
	var ls := LoginScreen.new()
	ls.address = address
	ls.account = "remtest"
	add_child(ls)
	await Net.connected_ok
	ls._pw_edit.text = "correct horse"
	ls._remember.button_pressed = true
	ls._login(true)
	await Net.characters_listed
	var saved: Dictionary = ls._remembered()
	print("remember_login: created and in; saved for this server %s, holds the password itself %s" % [saved.has("%s|remtest" % address),
			"correct horse" in FileAccess.get_file_as_string(Controls.SETTINGS_PATH)])
	Net.leave()
	ls.queue_free()
	await _wait(0.3)
	ls = LoginScreen.new()
	ls.address = address
	ls.account = "remtest"
	add_child(ls)
	await Net.connected_ok
	print("remember_login: back again -> field shows '%s', box ticked %s" % [ls._pw_edit.text, ls._remember.button_pressed])
	ls._login(false)
	await Net.characters_listed
	print("remember_login: logged in with the remembered password")
	ls._remember.button_pressed = false
	print("remember_login: unticked -> still saved %s" % ls._remembered().has("%s|remtest" % address))
	Net.leave()
	ls.queue_free()
	await _wait(0.3)


## Night and day: the sky at a few hours, looking across Greenmoor at the obelisk.
func _t_night() -> void:
	var main := get_parent()
	var p := World.local_player
	p.global_position = main.zone.ground(-14, 22) + Vector3.UP
	p.face_toward(main.zone.ground(0, 0))
	p.camera_pivot.rotation.y = 0.0
	p.zoom = 7.0
	p.pitch = -0.12
	for h: float in [12.0, 19.5, 20.5, 23.0, 5.5]:
		World.time_override = h
		await _wait(0.6)
		await _shot("9zh_night_%02d%02d" % [int(h), int((h - int(h)) * 60)])
	World.time_override = -1.0


## Emberhold after dark: lit windows and the guards' torches, then morning.
func _t_night_city() -> void:
	var main := get_parent()
	var p := World.local_player
	World.time_override = 23.0
	for view: Array in [[Vector2(0, -24), Vector2(0, -50), "gate"], [Vector2(22, -2), Vector2(34, -10), "houses"], [Vector2(-8, 8), Vector2(0, 0), "plaza"]]:
		p.global_position = main.zone.ground(view[0].x, view[0].y) + Vector3.UP
		p.face_toward(main.zone.ground(view[1].x, view[1].y))
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 6.0
		p.pitch = -0.1
		await _wait(1.3)
		await _shot("9zi_city_night_%s" % view[2])
	var lit := get_tree().get_nodes_in_group("night_lights").filter(func(n: Node) -> bool: return (n as Node3D).visible).size()
	var torches := 0
	for npc: Npc in _npcs().values():
		torches += 1 if npc._torch_light != null else 0
	p.global_position = main.zone.ground(0, -10) + Vector3.UP  # the middle of town, looking over it
	p.face_toward(main.zone.ground(0, 30))
	await _wait(2.0)
	var night_fps := Engine.get_frames_per_second()
	print("night_city: 23:00 -> %d night lights on, a guard with a torch: %s; %d fps" % [lit, torches > 0, night_fps])
	World.time_override = 12.0
	await _wait(1.3)
	lit = get_tree().get_nodes_in_group("night_lights").filter(func(n: Node) -> bool: return (n as Node3D).visible).size()
	torches = 0
	for npc: Npc in _npcs().values():
		torches += 1 if npc._torch_light != null else 0
	print("night_city: noon -> %d night lights on, guards with torches %d; %d fps" % [lit, torches, Engine.get_frames_per_second()])
	World.time_override = -1.0


## Night-only spawns: up after dark, gone at dawn unless they're in a fight.
func _t_night_spawns() -> void:
	var main := get_parent()
	var p := World.local_player
	var night: Array = main.zone.get_children().filter(func(n: Node) -> bool: return n is SpawnPoint and (n as SpawnPoint).when == "night")
	var up := func() -> int: return night.filter(func(sp: SpawnPoint) -> bool: return sp.mob != null and is_instance_valid(sp.mob)).size()
	World.time_override = 12.0
	await _wait(0.5)
	print("night_spawns: %d night spawn points; up at noon: %d" % [night.size(), up.call()])
	World.time_override = 23.0
	await _wait(0.5)
	print("night_spawns: up at 23:00: %d" % up.call())
	var fighter: Mob = (night[0] as SpawnPoint).mob
	fighter.add_hate(p, 5.0)
	World.time_override = 7.0
	await _wait(0.5)
	print("night_spawns: up at 7:00: %d (the one fighting stays: %s)" % [up.call(), is_instance_valid(fighter) and not fighter.is_queued_for_deletion()])
	fighter.hate.clear()
	fighter.state = Mob.State.IDLE
	await _wait(0.5)
	print("night_spawns: after the fight: %d" % up.call())
	World.time_override = -1.0


## The Thornwood-Hollowmere border, walked both ways (east and west zone lines).
func _t_hollowmere_border() -> void:
	var main := get_parent()
	var p := World.local_player
	for leg: Array in [["thornwood", Vector2(225, -20), Vector2(1, 0), "hollowmere"], ["hollowmere", Vector2(-193, -20), Vector2(-1, 0), "thornwood"]]:
		if main.zone.zone_id != leg[0]:
			print("hollowmere_border: expected to be in %s, in %s" % [leg[0], main.zone.zone_id])
			return
		p.global_position = main.zone.ground(leg[1].x, leg[1].y) + Vector3.UP
		for k in 400:
			if not is_instance_valid(main.zone) or main.zone.zone_id == leg[3]:
				break
			p.velocity = Vector3(leg[2].x, 0, leg[2].y) * 7.0 + Vector3(0, p.velocity.y - 20.0 * get_physics_process_delta_time(), 0)
			p.move_and_slide()
			await get_tree().physics_frame
		await _wait(1.5)
		while not is_instance_valid(main.zone) or main.zone.zone_id != leg[3]:
			await _wait(0.5)
			if k_timeout(main):
				break
		var z: Zone = main.zone
		print("hollowmere_border: walked %s from %s -> now in %s at %s (ground %.1f)" % [["east", "west"][0 if leg[2].x > 0 else 1], leg[0], z.zone_id,
				Vector2(p.global_position.x, p.global_position.z), z.height_at(p.global_position.x, p.global_position.z)])


var _patience := 0


func k_timeout(_main: Node) -> bool:
	_patience += 1
	return _patience > 40


## Hollowmere: the mere, the stilt village, the drowned ruins, the lizardfolk camp.
func _t_hollowmere() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	var lake: Dictionary = z._lakes[0]
	print("hollowmere: lake level %.1f; deck height at the village %.1f (ground there %.1f)" % [lake["level"], z.surface_at(100, -15), z.height_at(100, -15)])
	World.time_override = 11.0
	for view: Array in [[Vector2(-195, -20), Vector2(-120, -40), "arrival"], [Vector2(-150, -120), Vector2(0, 0), "mere"], [Vector2(150, -45), Vector2(100, -15), "village"],
			[Vector2(100, -15), Vector2(123, -15), "on_pier"], [Vector2(22, 138), Vector2(10, 112), "ruins"], [Vector2(-160, 62), Vector2(-170, 85), "camp"]]:
		p.global_position = Vector3(view[0].x, z.surface_at(view[0].x, view[0].y), view[0].y) + Vector3.UP
		p.face_toward(z.ground(view[1].x, view[1].y))
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 9.0
		p.pitch = -0.2
		await _wait(1.0)
		await _shot("9zj_hollowmere_%s" % view[2])
	var cam := Camera3D.new()  # a bird's-eye look at the whole mere
	get_tree().root.add_child(cam)
	cam.global_position = Vector3(0, 210, 190)
	cam.look_at(Vector3(0, 0, 10))
	cam.far = 1200.0
	cam.make_current()
	var env: Environment = (z.find_children("*", "WorldEnvironment", false, false)[0] as WorldEnvironment).environment
	env.fog_enabled = false  # the mist would hide it all from up here
	await _wait(1.0)
	await _shot("9zj_hollowmere_overview")
	env.fog_enabled = true
	cam.queue_free()
	await _wait(0.2)
	World.time_override = 22.5
	p.global_position = Vector3(150, z.surface_at(150, -45), -45) + Vector3.UP
	p.face_toward(z.ground(100, -15))
	await _wait(1.2)
	await _shot("9zj_hollowmere_village_night")
	World.time_override = -1.0


## Hollowmere's people and monsters: every kind spawns, the villagers stand on
## the pier, the three quests pay out, the drowned captain rises at night, and a
## look at each new creature in the world.
func _t_hollowmere_life() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	World.time_override = 12.0
	await _wait(0.5)
	var counts := {}
	for m in World.get_mobs():
		counts[m.mob_id] = int(counts.get(m.mob_id, 0)) + 1
	print("hollowmere_life: noon: %d monsters %s" % [World.get_mobs().size(), counts])
	var wet: Array = []
	for sp in z.get_children():
		if sp is SpawnPoint and z.water_level(sp.position.x, sp.position.z) > -INF:
			wet.append(Vector2(sp.position.x, sp.position.z))
	print("hollowmere_life: spawn points in the water: %s" % [wet])
	var npcs := _npcs()
	for id: String in ["hollow_elder", "hollow_netmaker", "mere_sentry"]:
		var n: Npc = npcs[id]
		print("hollowmere_life: %s at %s, standing %.1f above the lake bed (deck %.1f)" % [n.display_name, Vector2(n.global_position.x, n.global_position.z),
				n.global_position.y - z.height_at(n.global_position.x, n.global_position.z), z.surface_at(n.global_position.x, n.global_position.z)])
	# the quests
	p.level = 14
	p.recalc_stats()
	p.pack.clear()
	var tamsin: Npc = npcs["hollow_elder"]
	var brina: Npc = npcs["hollow_netmaker"]
	_stand_by(p, brina)
	World.request_say(p.entity_id, "hail")
	World.request_say(p.entity_id, "scales")
	p.pack.add("mirescale_scale", 4)
	await _hand_in(p, brina, ["mirescale_scale"])
	_stand_by(p, tamsin)
	for word in ["hail", "old snapjaw", "shell", "drowned", "bell"]:
		World.request_say(p.entity_id, word)
	p.pack.add("snapjaws_shell", 1)
	await _hand_in(p, tamsin, ["snapjaws_shell"])
	p.pack.add("drowned_bell", 1)
	p.pack.add("waterlogged_locket", 2)
	await _hand_in(p, tamsin, ["drowned_bell", "waterlogged_locket"])
	await _wait(0.3)
	print("hollowmere_life: rewards: sleeves %d, shield %d, pearl %d; quests done %s" % [p.pack.count("netmakers_sleeves"), p.pack.count("snapshell_shield"),
			p.pack.count("pearl_of_the_mere"), ["scales_for_the_nets", "old_snapjaw", "the_drowned_bell"].map(func(q: String) -> int: return int(p.quests.get(q, {}).get("completions", 0)))])
	# night: the drowned walk and their captain rises
	World.time_override = 23.0
	await _wait(0.6)
	var night := {}
	for m in World.get_mobs():
		if m.mob_id in ["drowned_fisher", "captain_maren"]:
			night[m.mob_id] = int(night.get(m.mob_id, 0)) + 1
	print("hollowmere_life: 23:00 -> %s" % night)
	await _shot("9zk_hollowmere_village_night2")
	# the creatures, each seen close up
	World.time_override = 12.0
	for id: String in ["mire_toad", "bog_leech", "snapping_turtle", "old_snapjaw", "mirescale_hunter", "mirescale_shaman", "ssrakka", "drowned_fisher"]:
		var m: Mob = _nearest_mob(p, id)
		if m == null:
			print("hollowmere_life: no %s found" % id)
			continue
		m.hate.clear()
		var at := m.global_position
		var from := at + Vector3(4.0, 0, 3.0)
		p.global_position = Vector3(from.x, z.surface_at(from.x, from.z), from.z) + Vector3.UP
		p.face_toward(at)
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 5.0
		p.pitch = -0.15
		m.set_physics_process(false)
		await _wait(0.8)
		await _shot("9zk_%s" % id)
		m.set_physics_process(true)
	World.time_override = -1.0


## How smooth Hollowmere runs: frame times standing still and walking, and
## what a height lookup costs now that lakes carve the ground.
func _t_hollowmere_perf() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	var t0 := Time.get_ticks_usec()
	for k in 5000:
		z.height_at(randf_range(-200, 200), randf_range(-200, 200))
	var per_height := float(Time.get_ticks_usec() - t0) / 5000.0
	t0 = Time.get_ticks_usec()
	for k in 5000:
		z.lake_distance(randf_range(-200, 200), randf_range(-200, 200))
	print("hollowmere_perf: height_at %.1f us, lake_distance %.1f us" % [per_height, float(Time.get_ticks_usec() - t0) / 5000.0])
	for spot: Array in [[Vector2(150, -45), Vector2(100, -15), "village"], [Vector2(-150, -120), Vector2(0, 0), "north shore"]]:
		p.global_position = Vector3(spot[0].x, z.surface_at(spot[0].x, spot[0].y), spot[0].y) + Vector3.UP
		p.face_toward(z.ground(spot[1].x, spot[1].y))
		await _wait(1.5)
		var worst := 0.0
		var total := 0.0
		for k in 120:
			var f0 := Time.get_ticks_usec()
			await get_tree().process_frame
			var ms := float(Time.get_ticks_usec() - f0) / 1000.0
			worst = maxf(worst, ms)
			total += ms
		print("hollowmere_perf: standing at the %s: %.1f ms a frame, worst %.1f ms, %d fps" % [spot[2], total / 120.0, worst, Engine.get_frames_per_second()])
	await _walk_stats("hollowmere_perf: walking east")


## Frame costs while walking east for 3 seconds: time, draw calls, objects, primitives, script and physics.
func _walk_stats(label: String) -> void:
	var p := World.local_player
	var worst := 0.0
	var total := 0.0
	var draws := 0.0
	var objs := 0.0
	var prims := 0.0
	var proc := 0.0
	var phys := 0.0
	for k in 360:
		var f0 := Time.get_ticks_usec()
		p.velocity = Vector3(9.0, p.velocity.y - 20.0 * get_physics_process_delta_time(), 0)
		p.move_and_slide()
		await get_tree().process_frame
		var ms := float(Time.get_ticks_usec() - f0) / 1000.0
		worst = maxf(worst, ms)
		total += ms
		draws += Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)
		objs += Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME)
		prims += Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)
		proc += Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0
		phys += Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0
	print("%s: %.1f ms a frame (worst %.1f); %d draw calls, %d objects, %dk triangles; process %.1f ms, physics %.1f ms" % [label, total / 360.0, worst,
			draws / 360.0, objs / 360.0, prims / 360.0 / 1000.0, proc / 360.0, phys / 360.0])


## What makes Hollowmere's night slow: measured with each night thing turned off in turn.
func _t_night_isolate() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	Engine.max_fps = 0
	var measure := func(label: String) -> void:
		await _wait(1.5)
		var f0 := Time.get_ticks_usec()
		for k in 180:
			await get_tree().process_frame
		print("night_isolate: %s: %.1f ms a frame (script %.1f ms, physics %.1f ms, %d draw calls, %d objects, %d lights... mobs %d)" % [label, float(Time.get_ticks_usec() - f0) / 180000.0,
				Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0, Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0,
				Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME), Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME),
				get_tree().root.find_children("*", "Light3D", true, false).filter(func(l: Node) -> bool: return (l as Light3D).is_visible_in_tree()).size(), World.get_mobs().size()])
	p.global_position = Vector3(-150, z.surface_at(-150, -120), -120) + Vector3.UP
	p.face_toward(z.ground(0, 0))
	World.time_override = 12.0
	await measure.call("noon")
	World.time_override = 23.0
	await measure.call("23:00")
	await measure.call("23:00 again")
	var cycle: DayNight = z.find_children("*", "DayNight", false, false)[0]
	cycle.moon.shadow_enabled = false
	cycle.set_process(false)
	await measure.call("23:00, no moon shadow")
	cycle.set_process(true)
	for n in get_tree().get_nodes_in_group("night_lights"):
		(n as Node3D).visible = false
	cycle.set_process(false)
	await measure.call("23:00, no moon shadow, night lights off")
	var night_mobs := 0
	for sp in z.get_children():
		if sp is SpawnPoint and (sp as SpawnPoint).when == "night" and sp.mob != null:
			sp.mob.visible = false
			night_mobs += 1
	await measure.call("... and %d night mobs hidden" % night_mobs)
	for m in World.get_mobs():
		m.visible = false
	await measure.call("... and every mob hidden")
	cycle.set_process(true)
	World.time_override = -1.0


## Whose physics is heavy in Hollowmere: switched off group by group.
func _t_physics_isolate() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	p.global_position = Vector3(-150, z.surface_at(-150, -120), -120) + Vector3.UP
	var measure := func(label: String) -> void:
		await _wait(1.0)
		var phys := 0.0
		for k in 120:
			await get_tree().physics_frame
			phys += Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0
		print("physics_isolate: %s: physics %.2f ms a tick" % [label, phys / 120.0])
	await measure.call("everything")
	for m in World.get_mobs():
		m.set_physics_process(false)
	await measure.call("mobs off")
	for n: Npc in _npcs().values():
		n.set_physics_process(false)
	await measure.call("mobs and npcs off")
	World.set_physics_process(false)
	await measure.call("... and World off")
	p.set_physics_process(false)
	await measure.call("... and the player off")
	World.set_physics_process(true)
	p.set_physics_process(true)
	for m in World.get_mobs():
		m.set_physics_process(true)
	for n: Npc in _npcs().values():
		n.set_physics_process(true)


## Harrowfield's borders, both walked both ways: Greenmoor's east edge, and
## Hollowmere's south edge.
func _t_harrowfield_border() -> void:
	var main := get_parent()
	var p := World.local_player
	for leg: Array in [["greenmoor", Vector2(170, 0), Vector2(1, 0), "harrowfield"], ["harrowfield", Vector2(0, -170), Vector2(0, -1), "hollowmere"],
			["hollowmere", Vector2(0, 202), Vector2(0, 1), "harrowfield"], ["harrowfield", Vector2(-170, 0), Vector2(-1, 0), "greenmoor"]]:
		if main.zone.zone_id != leg[0]:
			print("harrowfield_border: expected to be in %s, in %s" % [leg[0], main.zone.zone_id])
			return
		p.global_position = main.zone.ground(leg[1].x, leg[1].y) + Vector3.UP
		for k in 400:
			if not is_instance_valid(main.zone) or main.zone.zone_id == leg[3]:
				break
			p.velocity = Vector3(leg[2].x, 0, leg[2].y) * 7.0 + Vector3(0, p.velocity.y - 20.0 * get_physics_process_delta_time(), 0)
			p.move_and_slide()
			await get_tree().physics_frame
		await _wait(1.5)
		for k in 20:
			if is_instance_valid(main.zone) and main.zone.zone_id == leg[3]:
				break
			await _wait(0.5)
		var z: Zone = main.zone
		print("harrowfield_border: from %s -> now in %s at %s (on the ground: %s)" % [leg[0], z.zone_id, Vector2(p.global_position.x, p.global_position.z),
				absf(p.global_position.y - z.height_at(p.global_position.x, p.global_position.z)) < 1.5])


## Harrowfield: the hamlet, fields, windmill, orchard and the brigands' farm.
func _t_harrowfield() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	World.time_override = 11.0
	for view: Array in [[Vector2(-150, 0), Vector2(-40, 12), "arrival"], [Vector2(15, 0), Vector2(45, 25), "hamlet"], [Vector2(60, -60), Vector2(85, -30), "field"],
			[Vector2(-20, -90), Vector2(-50, -72), "windmill"], [Vector2(90, 90), Vector2(115, 115), "orchard"], [Vector2(-95, 80), Vector2(-122, 104), "hideout"]]:
		p.global_position = z.ground(view[0].x, view[0].y) + Vector3.UP
		p.face_toward(z.ground(view[1].x, view[1].y))
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 9.0
		p.pitch = -0.18
		await _wait(1.0)
		await _shot("9zl_harrowfield_%s" % view[2])
	World.time_override = 22.5
	p.global_position = z.ground(-20, 50) + Vector3.UP
	p.face_toward(z.ground(4, 74))
	await _wait(1.5)
	await _shot("9zl_harrowfield_field_night")
	World.time_override = -1.0


## Harrowfield's people and monsters: all spawn, the three quests pay out, the
## scarecrows walk at night.
func _t_harrowfield_life() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	World.time_override = 12.0
	await _wait(0.5)
	var counts := {}
	for m in World.get_mobs():
		counts[m.mob_id] = int(counts.get(m.mob_id, 0)) + 1
	print("harrowfield_life: noon: %d monsters %s" % [World.get_mobs().size(), counts])
	p.level = 8
	p.recalc_stats()
	p.pack.clear()
	var npcs := _npcs()
	var oswin: Npc = npcs["farmer_oswin"]
	var marta: Npc = npcs["widow_marta"]
	_stand_by(p, oswin)
	for word in ["hail", "boars", "tusks", "brigands", "ledger"]:
		World.request_say(p.entity_id, word)
	p.pack.add("boar_tusk", 4)
	await _hand_in(p, oswin, ["boar_tusk"])
	p.pack.add("garricks_ledger", 1)
	p.pack.add("brigand_armband", 2)
	await _hand_in(p, oswin, ["garricks_ledger", "brigand_armband"])
	_stand_by(p, marta)
	for word in ["hail", "scarecrows", "old tatters", "heart"]:
		World.request_say(p.entity_id, word)
	p.pack.add("straw_heart", 1)
	await _hand_in(p, marta, ["straw_heart"])
	await _wait(0.3)
	print("harrowfield_life: rewards: gloves %d, band %d, hat %d; quests done %s" % [p.pack.count("farmhands_gloves"), p.pack.count("harvest_band"),
			p.pack.count("tatters_hat"), ["tusks_for_oswin", "the_stolen_harvest", "old_tatters"].map(func(q: String) -> int: return int(p.quests.get(q, {}).get("completions", 0)))])
	World.time_override = 23.0
	await _wait(0.6)
	var night := {}
	for m in World.get_mobs():
		if m.mob_id in ["walking_scarecrow", "old_tatters"]:
			night[m.mob_id] = int(night.get(m.mob_id, 0)) + 1
	print("harrowfield_life: 23:00 -> %s" % night)
	World.time_override = 12.0
	for id: String in ["wild_boar", "old_bristleback", "brigand_cutpurse", "garrick_the_red"]:
		var m: Mob = _nearest_mob(p, id)
		if m == null:
			print("harrowfield_life: no %s found" % id)
			continue
		m.set_physics_process(false)
		var at := m.global_position
		p.global_position = z.ground(at.x + 4.0, at.z + 3.0) + Vector3.UP
		p.face_toward(at)
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 5.0
		p.pitch = -0.15
		await _wait(0.8)
		await _shot("9zm_%s" % id)
		m.set_physics_process(true)
	World.time_override = -1.0


## Signposts: long place names fit their boards, from both sides of the road.
func _t_sign_fit() -> void:
	var main := get_parent()
	var p := World.local_player
	World.time_override = 12.0
	for zone_id: String in ["hollowmere", "harrowfield"]:
		await _ensure_zone(zone_id)
		var z: Zone = main.zone
		for lm: Dictionary in z.data.get("landmarks", []):
			if lm["type"] != "signpost":
				continue
			var at := Vector2(lm["pos"][0], lm["pos"][1])
			for side: float in [1.0, -1.0]:
				var yaw := deg_to_rad(float(lm.get("yaw", 0.0)))
				var toward := Vector2(sin(yaw), cos(yaw)) * 3.2 * side + Vector2(cos(yaw), -sin(yaw)) * 0.4
				p.global_position = z.ground(at.x + toward.x, at.y + toward.y) + Vector3.UP
				p.face_toward(z.ground(at.x, at.y))
				p.camera_pivot.rotation.y = 0.0
				p.zoom = 0.0
				p.pitch = 0.08
				await _wait(0.6)
				await _shot("9zn_sign_%s_%d_%s" % [zone_id, int(at.x), "front" if side > 0 else "back"])
			break
	World.time_override = -1.0


## Navigation: every zone bakes its walkable map, and a path through
## Greenmoor's obelisk ring goes round the stones.
func _t_nav_bake() -> void:
	var main := get_parent()
	for zone_id: String in ["greenmoor", "thornwood", "hollowmere", "harrowfield", "emberhold"]:
		await _ensure_zone(zone_id)
		var z: Zone = main.zone
		for k in 120:
			if z.nav_ready:
				break
			await _wait(0.25)
		print("nav_bake: %s ready %s" % [zone_id, z.nav_ready])
		if zone_id == "greenmoor" and z.nav_ready:
			await _wait(0.3)
			var map := z.get_world_3d().navigation_map
			var a := z.ground(0, -14)
			var b := z.ground(0, 14)
			var path := NavigationServer3D.map_get_path(map, a, b, true)
			var nearest := INF
			var length := 0.0
			for i in path.size():
				nearest = minf(nearest, Vector2(path[i].x, path[i].z).length())
				if i > 0:
					length += path[i].distance_to(path[i - 1])
			print("nav_bake: path through the obelisk ring: %d points, %.1f m (straight 28 m), closest to the obelisk %.1f m" % [path.size(), length, nearest])
		if z.nav_ready:
			var map2 := z.get_world_3d().navigation_map
			var t0 := Time.get_ticks_usec()
			for k in 200:
				var a2 := z.ground(randf_range(-100, 100), randf_range(-100, 100))
				NavigationServer3D.map_get_path(map2, a2, a2 + Vector3(randf_range(-15, 15), 0, randf_range(-15, 15)), true)
			var short := float(Time.get_ticks_usec() - t0) / 200.0
			t0 = Time.get_ticks_usec()
			for k in 50:
				NavigationServer3D.map_get_path(map2, z.ground(randf_range(-100, 100), randf_range(-100, 100)), z.ground(randf_range(-100, 100), randf_range(-100, 100)), true)
			print("nav_bake: %s path query: %.0f us for a 15 m hop, %.0f us across the zone" % [zone_id, short, float(Time.get_ticks_usec() - t0) / 50.0])


## A boar outside a fenced field goes round to the gate to reach you inside,
## instead of pushing at the fence; the same chase with pathfinding off, to compare.
func _t_nav_chase() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	for k in 80:
		if z.nav_ready:
			break
		await _wait(0.25)
	p.level = 30
	p.recalc_stats()
	for on: bool in [true, false]:
		Entity.nav_enabled = on
		var boar: Mob = _nearest_mob(p, "wild_boar")
		for m in World.get_mobs():
			m.hate.clear()
		p.hp = p.max_hp
		p.global_position = z.ground(85, -30) + Vector3.UP  # the middle of the east field (gate on its north side)
		boar.global_position = z.ground(88, 2) + Vector3.UP  # outside its south fence
		boar.home = boar.global_position
		boar.state = Mob.State.IDLE
		await _wait(0.3)
		boar.add_hate(p, 50.0)
		var reached := -1.0
		for k in 60:
			await _wait(0.25)
			if is_instance_valid(boar) and boar.distance_to(p) <= World.melee_range() + 0.5:
				reached = k * 0.25
				break
		print("nav_chase: pathfinding %s: the boar %s" % ["on" if on else "off", ("reached you in %.1f s" % reached) if reached >= 0.0 else "never reached you in 15 s (stuck at %s)" % Vector2(boar.global_position.x, boar.global_position.z)])
		if is_instance_valid(boar):
			boar.hate.clear()
			boar.state = Mob.State.RETURN
	Entity.nav_enabled = true


## Dual Wield (warriors, 13) and Double Attack (15): a one-handed weapon goes
## in the off hand only once learned, a staff never; then half a minute of
## swings counted, with the skills fresh and then at their cap.
func _t_dual_wield() -> void:
	var p := World.local_player
	var saved_class := p.char_class
	p.char_class = "warrior"
	p.level = 12
	p.recalc_stats()
	p.pack.clear()
	p.equipment.clear()
	p.pack.add("iron_short_sword")
	p.pack.add("iron_dagger")
	p.pack.add("oak_staff")
	World.request_equip(p.entity_id, _where(p, "iron_short_sword"))
	var said: Array = []
	var listen := func(text: String, _c: Color) -> void: said.append(text)
	World.log_message.connect(listen)
	World.request_click(p.entity_id, _where(p, "iron_dagger"))  # onto the cursor
	World.request_click(p.entity_id, "e:secondary")
	print("dual_wield: level 12 -> off hand %s (%s)" % [p.equipment.get("secondary", "empty"), said.back()])
	p.level = 15
	p.recalc_stats()
	World.request_click(p.entity_id, "e:secondary")  # the dagger, still on the cursor
	print("dual_wield: level 15 -> off hand %s; sheet off hand %d-%d every %.1fs; skills open: dual wield cap %d, double attack cap %d" % [
			p.equipment.get("secondary", "empty"), p.off_dmg_min, p.off_dmg_max, p.off_delay, World.skill_cap(p, "dual_wield"), World.skill_cap(p, "double_attack")])
	World.request_click(p.entity_id, _where(p, "oak_staff"))
	World.request_click(p.entity_id, "e:secondary")
	print("dual_wield: a staff in the off hand -> off hand %s (%s)" % [p.equipment.get("secondary", "empty"), said.back()])
	World.request_stow_cursor(p.entity_id)
	var mob: Mob = _nearest_mob(p, "")
	for trained: bool in [false, true]:
		p.skills["dual_wield"] = World.skill_cap(p, "dual_wield") if trained else 0
		p.skills["double_attack"] = World.skill_cap(p, "double_attack") if trained else 0
		mob.level = 15
		mob.max_hp = 100000
		mob.hp = mob.max_hp
		mob.dmg_min = 0
		mob.dmg_max = 1
		p.hp = p.max_hp
		p.global_position = mob.global_position + Vector3(1.5, 0.5, 0)
		p.face_toward(mob.global_position)
		World.request_set_target(p.entity_id, mob.entity_id)
		said.clear()
		p.swing_timer = 0.0
		p.off_swing_timer = 0.0
		World.request_toggle_attack(p.entity_id)
		await _wait(30.0)
		World.request_toggle_attack(p.entity_id)
		var main := said.filter(func(t: String) -> bool: return t.begins_with("You slash") or t.begins_with("You try to slash")).size()
		var off := said.filter(func(t: String) -> bool: return t.begins_with("You pierce") or t.begins_with("You try to pierce")).size()
		print("dual_wield: 30 s, skills %s: %d main-hand swings (%.0f timers), %d off-hand swings (%.0f timers)" % [
				"at cap" if trained else "fresh", main, 30.0 / p.attack_delay, off, 30.0 / p.off_delay])
	World.log_message.disconnect(listen)
	mob.hate.clear()
	p.char_class = saved_class
	p.equipment.clear()
	p.level = 1
	p.recalc_stats()


## The rogue: hide and sneak past a gnoll scout, walking openly breaks it,
## backstab only from behind (and harder from the shadows), evade sheds anger,
## an envenomed blade poisons.
func _t_rogue() -> void:
	var p := World.local_player
	var saved_class := p.char_class
	p.char_class = "rogue"
	p.level = 5
	p.spells = ["backstab", "hide", "sneak", "evade", "envenom_blade", "rake", "bind_wound"]
	for sk: String in ["hide", "sneak", "backstab", "piercing", "offense"]:
		p.skills[sk] = World.skill_cap(p, sk)
	p.equipment.clear()
	p.pack.clear()
	p.pack.add("rusty_dagger")
	World.request_equip(p.entity_id, _where(p, "rusty_dagger"))
	p.recalc_stats()
	p.hp = p.max_hp
	var said: Array = []
	var listen := func(text: String, _c: Color) -> void: said.append(text)
	World.log_message.connect(listen)
	var scout: Mob = _nearest_mob(p, "gnoll_scout")
	for m in World.get_mobs():
		m.hate.clear()
	var out := Vector3(scout.global_position.x - 115.0, 0, scout.global_position.z + 100.0)  # away from the gnoll camp's middle
	out = out.normalized() if out.length() > 1.0 else Vector3(1, 0, 0)
	p.global_position = scout.global_position + out * 45.0 + Vector3.UP
	await _wait(0.5)
	for m in World.get_mobs():
		m.hate.clear()
	World.request_cast(p.entity_id, "sneak")
	World.request_cast(p.entity_id, "hide")
	await _wait(0.2)
	p.global_position = scout.global_position + Vector3(5, 0.5, 0)  # right up beside it, sneaking
	await _wait(3.0)
	print("rogue: hidden and sneaking 5 m from a gnoll scout for 3 s -> hidden %s, scout noticed me %s" % [p.hidden, scout.hate.has(p.entity_id)])
	await _shot("9zo_rogue_hidden")
	World.request_cast(p.entity_id, "sneak")  # stop sneaking...
	await _wait(0.1)
	p.global_position += Vector3(1.0, 0, 0)  # ...and step out
	await _wait(0.2)
	print("rogue: walked without sneaking -> hidden %s (%s)" % [p.hidden, said.filter(func(t: String) -> bool: return "hidden" in t).back()])
	scout.hate.clear()
	scout.set_physics_process(false)  # hold still while we walk round it
	var fwd := -scout.global_transform.basis.z
	fwd.y = 0.0
	fwd = fwd.normalized()
	p.global_position = scout.global_position + fwd * 2.0 + Vector3.UP * 0.3
	World.request_set_target(p.entity_id, scout.entity_id)
	World.request_cast(p.entity_id, "backstab")
	await _wait(0.2)
	print("rogue: backstab from the front -> %s" % said.back())
	scout.hate.clear()  # calm it again, as if we'd never been there
	scout.auto_attack = false
	scout.target = null
	scout.state = Mob.State.IDLE
	p.global_position = scout.global_position + fwd * 25.0 + Vector3.UP
	await _wait(2.5)
	World.request_cast(p.entity_id, "sneak")
	World.request_cast(p.entity_id, "hide")
	await _wait(0.2)
	p.global_position = scout.global_position - fwd * 2.0 + Vector3.UP * 0.3
	p.cooldowns.erase("backstab")
	said.clear()
	var hp_before := scout.hp
	World.request_cast(p.entity_id, "backstab")
	await _wait(0.2)
	print("rogue: backstab from behind, from hiding -> %s; %s (the scout lost %d hp)" % [said.filter(func(t: String) -> bool: return "shadows" in t).size() > 0, said.filter(func(t: String) -> bool: return "backstab" in t).back(), hp_before - scout.hp])
	scout.set_physics_process(true)
	scout.add_hate(p, 40.0)
	var anger := float(scout.hate.get(p.entity_id, 0.0))
	World.request_cast(p.entity_id, "evade")
	await _wait(0.2)
	print("rogue: evade -> the scout's anger at me %.0f -> %.0f" % [anger, float(scout.hate.get(p.entity_id, 0.0))])
	scout.max_hp = 5000
	scout.hp = 5000
	scout.dmg_max = 1
	World.request_cast(p.entity_id, "envenom_blade")
	World.request_set_target(p.entity_id, scout.entity_id)
	World.request_toggle_attack(p.entity_id)
	var poisoned := false
	for k in 60:
		await _wait(0.5)
		p.hp = p.max_hp
		if scout.dots.any(func(d: Dictionary) -> bool: return d["spell"] == "rogue_venom"):
			poisoned = true
			break
	World.request_toggle_attack(p.entity_id)
	print("rogue: envenom blade -> the scout poisoned while I fought it: %s" % poisoned)
	World.log_message.disconnect(listen)
	scout.hate.clear()
	p.hidden = false
	p.sneaking = false
	p.show_hidden()
	p.char_class = saved_class
	p.equipment.clear()
	p.level = 1
	p.recalc_stats()


## Vessa Nightwhisper in her corner of the tavern, and the four classes at character creation.
func _t_rogue_guild() -> void:
	var main := get_parent()
	var p := World.local_player
	var vessa: Npc = _npcs().get("gm_vessa")
	if vessa == null:
		print("rogue_guild: no Vessa in %s" % main.zone.zone_id)
		return
	p.global_position = vessa.global_position + Vector3(-4.0, 0.5, 2.5)
	p.face_toward(vessa.global_position)
	p.camera_pivot.rotation.y = 0.0
	p.zoom = 3.0
	World.request_set_target(p.entity_id, vessa.entity_id)
	World.request_hail(p.entity_id)
	await _wait(0.8)
	await _shot("9zp_vessa")
	var cc := CharCreate.new()
	main.add_child(cc)
	await _wait(0.6)
	await _shot("9zp_char_create")
	print("rogue_guild: Vessa at %s; character creation offers %s" % [vessa.global_position, GameData.classes.keys()])
	cc.queue_free()


## Thornback spiders drop venom sacs (the Silk and Venom quest): kill a lot and count.
func _t_venom_drop() -> void:
	var main := get_parent()
	var p := World.local_player
	p.level = 12
	p.recalc_stats()
	var kills := 0
	var sacs := 0
	var silk := 0
	for round_ in 40:
		var spider: Mob = _nearest_mob(p, "thornback_spider")
		if spider == null:
			await _wait(1.0)
			continue
		p.global_position = spider.global_position + Vector3(2, 0.5, 0)
		spider.add_hate(p, 1.0)
		var where := spider.global_position
		World.damage(spider, spider.hp + 10, p)
		kills += 1
		await _wait(0.1)
		for c in main.zone.get_children():
			if c is Corpse and not c.has_meta("counted") and (c as Corpse).global_position.distance_to(where) < 3.0:
				c.set_meta("counted", true)
				for e: Dictionary in (c as Corpse).entries:
					sacs += 1 if str(e.get("item", "")) == "venom_sac" else 0
					silk += 1 if str(e.get("item", "")) == "spider_silk" else 0
		for sp in main.zone.get_children():  # bring them back at once, for the next kill
			if sp is SpawnPoint and (sp as SpawnPoint).mob == null:
				(sp as SpawnPoint).spawn()
	print("venom_drop: %d thornback spiders killed -> %d venom sacs, %d spider silk on their corpses" % [kills, sacs, silk])


## The Hollowmere - Sunward Steps border, walked both ways.
func _t_sunward_border() -> void:
	var main := get_parent()
	var p := World.local_player
	for leg: Array in [["hollowmere", Vector2(200, 0), Vector2(1, 0), "sunward_steps"], ["sunward_steps", Vector2(-196, 0), Vector2(-1, 0), "hollowmere"]]:
		if main.zone.zone_id != leg[0]:
			print("sunward_border: expected to be in %s, in %s" % [leg[0], main.zone.zone_id])
			return
		p.global_position = main.zone.ground(leg[1].x, leg[1].y) + Vector3.UP
		for k in 400:
			if not is_instance_valid(main.zone) or main.zone.zone_id == leg[3]:
				break
			p.velocity = Vector3(leg[2].x, 0, leg[2].y) * 7.0 + Vector3(0, p.velocity.y - 20.0 * get_physics_process_delta_time(), 0)
			p.move_and_slide()
			await get_tree().physics_frame
		await _wait(1.5)
		for k in 20:
			if is_instance_valid(main.zone) and main.zone.zone_id == leg[3]:
				break
			await _wait(0.5)
		var z: Zone = main.zone
		print("sunward_border: from %s -> now in %s at %s (on the ground: %s)" % [leg[0], z.zone_id, Vector2(p.global_position.x, p.global_position.z),
				absf(p.global_position.y - z.height_at(p.global_position.x, p.global_position.z)) < 1.5])


## Sunward Steps: the terraces, the waystation, the shrines, the Great Temple.
func _t_sunward() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	World.time_override = 10.0
	print("sunward: terraces from %.1f m at the waystation to %.1f m at the Great Temple" % [z.height_at(-170, -30), z.height_at(152, 32)])
	for view: Array in [[Vector2(-192, 5), Vector2(-120, -5), "arrival"], [Vector2(-175, -10), Vector2(-178, -30), "waystation"], [Vector2(-80, 10), Vector2(40, 0), "terraces"],
			[Vector2(-27, 95), Vector2(-27, 62), "shrine"], [Vector2(152, 75), Vector2(152, 32), "temple"], [Vector2(-50, -85), Vector2(-72, -112), "graveyard"],
			[Vector2(18, 90), Vector2(18, 122), "cult"]]:
		p.global_position = z.ground(view[0].x, view[0].y) + Vector3.UP
		p.face_toward(z.ground(view[1].x, view[1].y))
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 10.0
		p.pitch = -0.2
		await _wait(1.0)
		await _shot("9zq_sunward_%s" % view[2])
	var cam := Camera3D.new()
	get_tree().root.add_child(cam)
	cam.global_position = Vector3(-60, 190, 230)
	cam.look_at(Vector3(20, 0, 0))
	cam.far = 1200.0
	cam.make_current()
	var env: Environment = (z.find_children("*", "WorldEnvironment", false, false)[0] as WorldEnvironment).environment
	env.fog_enabled = false
	await _wait(1.0)
	await _shot("9zq_sunward_overview")
	env.fog_enabled = true
	cam.queue_free()
	World.time_override = 22.5
	p.global_position = z.ground(152, 70) + Vector3.UP
	p.face_toward(z.ground(152, 32))
	await _wait(1.5)
	await _shot("9zq_sunward_temple_night")
	World.time_override = -1.0


## Sunward Steps' people and monsters: all spawn, the three quests pay out,
## Sahkrin and the dead rise at night.
func _t_sunward_life() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	World.time_override = 12.0
	await _wait(0.5)
	var counts := {}
	for m in World.get_mobs():
		counts[m.mob_id] = int(counts.get(m.mob_id, 0)) + 1
	print("sunward_life: noon: %d monsters %s" % [World.get_mobs().size(), counts])
	p.level = 18
	p.recalc_stats()
	p.pack.clear()
	var npcs := _npcs()
	var ysolde: Npc = npcs["pilgrim_mother"]
	var dov: Npc = npcs["quartermaster_dov"]
	_stand_by(p, ysolde)
	for word in ["hail", "pilgrims", "tokens", "pilgrims' rest", "sahkrin", "scarab"]:
		World.request_say(p.entity_id, word)
	p.pack.add("pilgrim_token", 4)
	await _hand_in(p, ysolde, ["pilgrim_token"])
	p.pack.add("sun_scarab", 1)
	await _hand_in(p, ysolde, ["sun_scarab"])
	_stand_by(p, dov)
	for word in ["hail", "cult", "hierophant"]:
		World.request_say(p.entity_id, word)
	p.pack.add("hierophants_mask", 1)
	p.pack.add("cult_sigil", 3)
	await _hand_in(p, dov, ["hierophants_mask", "cult_sigil"])
	await _wait(0.3)
	print("sunward_life: rewards: boots %d, pendant %d, sunbreaker %d; quests done %s" % [p.pack.count("pilgrims_boots"), p.pack.count("dawn_tusk_pendant"),
			p.pack.count("sunbreaker"), ["tokens_of_the_fallen", "the_unrisen", "the_false_sun"].map(func(q: String) -> int: return int(p.quests.get(q, {}).get("completions", 0)))])
	World.time_override = 23.0
	await _wait(0.6)
	var night := {}
	for m in World.get_mobs():
		if m.mob_id in ["sun_mummy", "mummy_priest"]:
			night[m.mob_id] = int(night.get(m.mob_id, 0)) + 1
	print("sunward_life: 23:00 -> %s" % night)
	World.time_override = 12.0
	for id: String in ["mountain_ram", "sunhawk", "stone_guardian", "stone_colossus", "sun_cultist", "cult_hierophant"]:
		var m: Mob = _nearest_mob(p, id)
		if m == null:
			print("sunward_life: no %s found" % id)
			continue
		m.set_physics_process(false)
		var at := m.global_position
		p.global_position = z.ground(at.x + 4.0, at.z + 3.0) + Vector3.UP
		p.face_toward(at)
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 5.0
		p.pitch = -0.15
		await _wait(0.8)
		await _shot("9zr_%s" % id)
		m.set_physics_process(true)
	World.time_override = -1.0


## The new abilities for levels 16-20, each checked for what it does.
func _t_level20() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	var saved_class := p.char_class
	var said: Array = []
	var listen := func(text: String, _c: Color) -> void: said.append(text)
	World.log_message.connect(listen)
	var target: Mob = _nearest_mob(p, "mountain_ram")
	var ready := func(cls: String, spells: Array) -> void:
		p.char_class = cls
		p.level = 20
		p.spells = spells
		p.cooldowns.clear()
		p.buffs.clear()
		p.recalc_stats()
		p.hp = p.max_hp
		p.mana = p.max_mana
		for sk: String in GameData.skills["skills"]:
			if World.skill_cap(p, sk) > 0:
				p.skills[sk] = World.skill_cap(p, sk)
		for m in World.get_mobs():
			m.hate.clear()
		target.max_hp = 100000
		target.hp = target.max_hp
		p.global_position = target.global_position + Vector3(2.0, 0.5, 0)
		World.request_set_target(p.entity_id, target.entity_id)
	# warrior
	await ready.call("warrior", ["provoke", "defensive_stance", "cleave"])
	var other: Mob = null  # a second foe right beside the target, for the area abilities
	for m in World.get_mobs():
		if m != target and not m.dead and (other == null or m.distance_to(target) < other.distance_to(target)):
			other = m
	other.set_physics_process(false)
	other.global_position = target.global_position + Vector3(0, 0.3, 2.0)
	other.max_hp = 100000
	other.hp = other.max_hp
	World.request_cast(p.entity_id, "provoke")
	var ac0 := p.ac
	World.request_cast(p.entity_id, "defensive_stance")
	var ac1 := p.ac
	said.clear()
	World.request_cast(p.entity_id, "cleave")
	await _wait(0.3)
	print("level20: warrior: provoke turned %d; defensive stance AC %d -> %d; cleave splashed %s" % [World.get_mobs().filter(func(m: Mob) -> bool: return m.hate.has(p.entity_id)).size(),
			ac0, ac1, said.filter(func(t: String) -> bool: return "caught in the cleave" in t).size() > 0])
	# cleric
	await ready.call("cleric", ["greater_healing", "divine_aura", "sunfire"])
	p.hp = 1
	World.request_set_target(p.entity_id, p.entity_id)
	World.request_cast(p.entity_id, "greater_healing")
	await _wait(3.4)
	var healed := p.hp
	World.request_cast(p.entity_id, "divine_aura")
	var before := p.hp
	World.damage(p, 50, target)
	print("level20: cleric: greater healing 1 -> %d hp; under divine aura a 50-point blow took %d" % [healed, before - p.hp])
	World.request_set_target(p.entity_id, target.entity_id)
	var t_hp := target.hp
	World.request_cast(p.entity_id, "sunfire")
	await _wait(3.4)
	print("level20: cleric: sunfire hit for %d" % (t_hp - target.hp))
	# wizard
	await ready.call("wizard", ["lightning_bolt", "frost_snare", "fireball"])
	other.global_position = target.global_position + Vector3(0, 0.3, 3.0)
	t_hp = target.hp
	World.request_cast(p.entity_id, "lightning_bolt")
	await _wait(3.2)
	var bolt := t_hp - target.hp
	World.request_cast(p.entity_id, "frost_snare")
	await _wait(1.9)
	var snared := target.snare_left
	said.clear()
	World.request_cast(p.entity_id, "fireball")
	await _wait(3.9)
	print("level20: wizard: lightning bolt %d; frost snare %.0f s; fireball splashed %s" % [bolt, snared, said.filter(func(t: String) -> bool: return "caught in the fireball" in t).size() > 0])
	# rogue
	await ready.call("rogue", ["hide", "assassinate", "blind", "deadly_poison"])
	p.equipment.clear()
	p.pack.clear()
	p.pack.add("iron_dagger")
	World.request_equip(p.entity_id, _where(p, "iron_dagger"))
	target.set_physics_process(false)
	said.clear()
	World.request_cast(p.entity_id, "assassinate")
	var refused: String = said.back() if not said.is_empty() else ""
	var fwd := -target.global_transform.basis.z
	fwd.y = 0.0
	p.global_position = target.global_position + fwd.normalized() * 30.0 + Vector3.UP
	await _wait(0.3)
	for m in World.get_mobs():
		m.hate.clear()
	World.request_cast(p.entity_id, "hide")
	await _wait(0.1)
	p.global_position = target.global_position - fwd.normalized() * 2.0 + Vector3.UP * 0.3
	await _wait(0.05)
	p.hidden = true  # the teleport counts as walking; we're testing the strike, not the sneak
	t_hp = target.hp
	World.request_cast(p.entity_id, "assassinate")
	await _wait(0.2)
	var hit := t_hp - target.hp
	target.set_physics_process(true)
	World.request_cast(p.entity_id, "blind")
	var stunned := target.stun_left
	World.request_cast(p.entity_id, "deadly_poison")
	print("level20: rogue: assassinate unhidden -> '%s'; from hiding %d damage; blind %.0f s; deadly poison up %s" % [refused, hit, stunned, p.buffs.has("deadly_poison")])
	World.log_message.disconnect(listen)
	target.hate.clear()
	other.hate.clear()
	other.set_physics_process(true)
	p.char_class = saved_class
	p.equipment.clear()
	p.level = 1
	p.recalc_stats()


## Bash can stun (never something more than 3 levels above you); being hit
## turns auto attack on; the camera zooms from the keyboard.
func _t_bash_stun() -> void:
	var main := get_parent()
	var p := World.local_player
	var kit := p.equipment.duplicate()
	var known := p.spells.duplicate()
	p.char_class = "warrior"
	p.level = 10
	p.spells = ["bash"]
	p.equipment["secondary"] = "round_shield"
	p.recalc_stats()
	var mob := _nearest_mob(p, "gnoll_pup")
	mob.set_physics_process(false)
	mob.max_hp = 100000
	mob.hp = mob.max_hp
	p.global_position = main.zone.ground(mob.global_position.x + 2.0, mob.global_position.z) + Vector3.UP
	World.request_set_target(p.entity_id, mob.entity_id)
	for over: int in [0, 5]:
		mob.level = p.level + over
		var stuns := 0
		for k in 40:
			p.cooldowns.clear()
			mob.stun_left = 0.0
			World.request_cast(p.entity_id, "bash")
			if mob.stun_left > 0.0:
				stuns += 1
		print("bash_stun: a target %d levels over you: stunned %d of 40 bashes" % [over, stuns])
	World.kill(mob, p)
	# a rat bites you from behind with nothing targeted and auto attack off
	World.request_set_target(p.entity_id, -1)
	p.auto_attack = false
	var rat := _nearest_mob(p, "large_rat")
	rat.max_hp = 100000
	rat.hp = rat.max_hp
	p.global_position = main.zone.ground(rat.global_position.x + 1.5, rat.global_position.z) + Vector3.UP
	p.face_toward(p.global_position + (p.global_position - rat.global_position))
	rat.add_hate(p, 5.0)
	await _wait(4.0)
	print("bash_stun: bitten from behind -> target %s, auto attack %s" % [p.target.display_name if p.target != null else "nothing", p.auto_attack])
	World.request_toggle_attack(p.entity_id)
	if is_instance_valid(rat) and not rat.dead:
		World.kill(rat, p)
	# zoom from the keyboard
	var press := func(action: String) -> void:
		var ev := InputEventAction.new()
		ev.action = action
		ev.pressed = true
		p._unhandled_input(ev)
	p.zoom = 6.0
	press.call("zoom_in")
	var z1 := p.zoom
	press.call("first_person")
	var z2 := p.zoom
	press.call("first_person")
	var z3 := p.zoom
	press.call("zoom_out")
	print("bash_stun: zoom 6 -> in %.0f -> Home %.0f -> Home %.0f -> out %.0f" % [z1, z2, z3, p.zoom])
	p.zoom = 6.0
	p.equipment = kit
	p.spells = known
	p.recalc_stats()


## Pets: summoned, they follow, attack on command (and taunt), back off,
## guard and sit; heals and buffs reach them; their kills are their owner's;
## they come back after vanishing (a zone, a login); /pet leave dismisses.
## And a table of every kind's stats at levels 1, 10, 18, 25.
func _t_pets() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	var saved_class := p.char_class
	for lvl: int in [1, 10, 18, 25]:
		p.level = lvl
		var row := []
		for kind: String in ["earth", "water", "fire", "air", "primal", "skeleton", "skeletal_knight"]:
			var spell := ""
			for sid: String in GameData.spells:
				if str(GameData.spells[sid].get("pet", "")) == kind:
					spell = sid
			var pet := Pet.new()
			pet.setup(p, spell)
			row.append("%s %d hp %d-%d ac %d %.1fs %s" % [kind, pet.max_hp, pet.dmg_min, pet.dmg_max, pet.ac, pet.attack_delay, pet.model_id])
			pet.free()
		print("pets: level %d: %s" % [lvl, ", ".join(row)])
	p.char_class = "magician"
	p.level = 10
	p.spells = ["call_of_earth", "renew_elements", "burnout"]
	p.recalc_stats()
	for sk: String in GameData.skills["skills"]:  # no fizzles in the test
		if World.skill_cap(p, sk) > 0:
			p.skills[sk] = World.skill_cap(p, sk)
	p.mana = p.max_mana
	p.cooldowns.clear()
	var home := z.ground(20, 60) + Vector3.UP
	p.global_position = home
	World.request_cast(p.entity_id, "call_of_earth")
	await _wait(5.4)
	var pet := World.get_object(p.pet_id) as Pet
	print("pets: summoned -> %s (%s), level %d, %d hp; window %s" % [pet.display_name if pet else "none", pet.kind if pet else "", pet.level if pet else 0,
			pet.max_hp if pet else 0, main.hud._pet_panel.visible])
	if pet == null:
		return
	# it follows
	p.global_position = home + Vector3(15, 0, 0)
	await _wait(4.0)
	print("pets: walked 15 m away -> the pet is %.1f m from you" % pet.distance_to(p))
	# attack on command, taunting
	var mob := _nearest_mob(p, "gnoll_pup")
	mob.set_physics_process(false)
	mob.max_hp = 100000
	mob.hp = mob.max_hp
	p.global_position = z.ground(mob.global_position.x + 6.0, mob.global_position.z) + Vector3.UP
	pet.global_position = z.ground(mob.global_position.x + 3.0, mob.global_position.z) + Vector3.UP
	World.request_set_target(p.entity_id, mob.entity_id)
	World.request_pet(p.entity_id, "attack")
	await _wait(6.0)
	print("pets: attack -> the pup took %d from the pet; the pup's top foe is %s" % [100000 - mob.hp, mob.top_hated().display_name if mob.top_hated() else "none"])
	World.request_pet(p.entity_id, "back")
	await _wait(0.3)
	print("pets: back off -> attacking %s" % pet.auto_attack)
	# heal and buff
	pet.hp = 10
	World.request_cast(p.entity_id, "renew_elements")
	await _wait(2.8)
	var healed := pet.hp
	var delay0 := pet.attack_delay
	World.request_cast(p.entity_id, "burnout")
	await _wait(3.3)
	print("pets: renew elements 10 -> %d hp; burnout delay %.2f -> %.2f" % [healed, delay0, pet.attack_delay])
	# guard and sit
	World.request_pet(p.entity_id, "guard")
	var spot := pet.global_position
	p.global_position += Vector3(12, 0, 0)
	await _wait(3.0)
	var guarded := pet.global_position.distance_to(spot)
	World.request_pet(p.entity_id, "sit")
	await _wait(0.3)
	print("pets: guard -> stayed within %.1f m of its spot as you left; sit -> sitting %s" % [guarded, pet.sitting])
	World.request_pet(p.entity_id, "follow")
	# a kill by the pet is its owner's
	mob.max_hp = 30
	mob.hp = 20
	mob.level = 8
	var xp0 := p.xp
	pet.global_position = z.ground(mob.global_position.x + 1.5, mob.global_position.z) + Vector3.UP
	World.request_pet(p.entity_id, "attack")
	await _wait(8.0)
	print("pets: the pet killed the pup: dead %s; your xp %d -> %d" % [mob.dead if is_instance_valid(mob) else true, xp0, p.xp])
	# it comes back after vanishing (zoning, logging in)
	var hp0 := pet.hp
	var old_id := pet.entity_id
	pet.queue_free()
	await _wait(0.5)
	var back := World.get_object(p.pet_id) as Pet
	print("pets: vanished -> back as a new pet %s, %d hp (was %d); saved %s" % [back != null and back.entity_id != old_id, back.hp if back else 0, hp0, p.to_save().get("pet", {})])
	World.request_chat(p.entity_id, "/pet leave")
	await _wait(0.3)
	print("pets: /pet leave -> pet %s, remembered spell '%s'" % [World.get_object(p.pet_id) != null, p.pet_spell])
	p.char_class = saved_class
	p.level = 1
	p.spells = GameData.classes[saved_class]["spells"].duplicate()
	p.recalc_stats()


## The Necromancer: a skeleton pet, lifetaps, a disease that ticks, a draining
## bond, fear (not on named foes), root and snare, and Feign Death.
func _t_necromancer() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	var saved_class := p.char_class
	p.char_class = "necromancer"
	p.level = 25
	p.spells = ["raise_bones", "lifetap", "disease_cloud", "dread", "feign_death", "bond_of_death", "clinging_darkness", "mass_dread", "raise_skeletal_knight"]
	p.recalc_stats()
	for sk: String in GameData.skills["skills"]:
		if World.skill_cap(p, sk) > 0:
			p.skills[sk] = World.skill_cap(p, sk)
	var cast := func(sid: String) -> void:
		p.cooldowns.clear()
		p.mana = p.max_mana
		World.request_cast(p.entity_id, sid)
		await _wait(float(GameData.spells[sid]["cast_time"]) + 0.3)
	p.global_position = z.ground(20, 60) + Vector3.UP
	await cast.call("raise_skeletal_knight")
	var pet := World.get_object(p.pet_id) as Pet
	print("necromancer: raised %s (%s, %d hp)" % [pet.display_name if pet else "nothing", pet.model_id if pet else "", pet.max_hp if pet else 0])
	World.request_pet(p.entity_id, "sit")
	var mob := _nearest_mob(p, "gnoll_scout")
	mob.max_hp = 100000
	mob.hp = mob.max_hp
	p.global_position = z.ground(mob.global_position.x + 8.0, mob.global_position.z) + Vector3.UP
	World.request_set_target(p.entity_id, mob.entity_id)
	p.hp = p.max_hp / 2
	var hp0 := p.hp
	await cast.call("lifetap")
	print("necromancer: lifetap -> you %d -> %d hp, the target lost %d" % [hp0, p.hp, 100000 - mob.hp])
	var t0 := mob.hp
	await cast.call("disease_cloud")
	await _wait(6.5)
	print("necromancer: disease cloud ticked %d damage over 6 s" % (t0 - mob.hp))
	p.hp = p.max_hp / 2
	hp0 = p.hp
	await cast.call("bond_of_death")
	await _wait(6.5)
	print("necromancer: bond of death healed you %d over 6 s" % (p.hp - hp0))
	await cast.call("clinging_darkness")
	print("necromancer: clinging darkness -> snared %.0f s" % mob.snare_left)
	mob.set_physics_process(true)
	var d0 := mob.distance_to(p)
	await cast.call("dread")
	var feared := mob.fear_left
	await _wait(3.0)
	print("necromancer: dread -> feared %.0f s; ran from %.1f to %.1f m away; swinging %s" % [feared, d0, mob.distance_to(p), mob.auto_attack])
	mob.fear_left = 0.0
	mob.add_hate(p, 50.0)
	await _wait(0.5)
	await cast.call("feign_death")
	print("necromancer: feign death -> lying there %s; the gnoll still hunting you %s" % [p.feigning, mob.hate.has(p.entity_id)])
	p.global_position += Vector3(1, 0, 0)
	await _wait(0.2)
	print("necromancer: moved -> still feigning %s" % p.feigning)
	var named := _nearest_mob(p, "rhagg")
	if named != null:
		World.request_set_target(p.entity_id, named.entity_id)
		p.global_position = z.ground(named.global_position.x + 8.0, named.global_position.z) + Vector3.UP
		await cast.call("dread")
		print("necromancer: dread on a named foe -> feared %.0f s" % named.fear_left)
		named.hate.clear()
	World.request_pet(p.entity_id, "leave")
	mob.hate.clear()
	p.char_class = saved_class
	p.level = 1
	p.spells = GameData.classes[saved_class]["spells"].duplicate()
	p.recalc_stats()


## Every pet kind at level 20, side by side with a magician and a necromancer.
func _t_pet_look() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	World.time_override = 12.0
	p.level = 20
	var at := z.ground(30, 60)
	var pets := []
	var i := 0
	for spell: String in ["call_of_earth", "call_of_water", "call_of_fire", "call_of_air", "call_of_the_primal", "raise_bones", "raise_skeletal_knight"]:
		var pet := Pet.new()
		pet.setup(p, spell)
		z.add_child(pet)
		pet.global_position = z.ground(at.x - 9.0 + i * 3.0, at.z) + Vector3.UP * 0.3
		pet.set_physics_process(false)
		pet.rotation.y = 0.0
		pets.append(pet)
		i += 1
	for cls: String in ["magician", "necromancer"]:
		var look := {"model": GameData.classes[cls]["model"], "weapon": "staff"}
		var body := Entity.make_visual(look)
		z.add_child(body)
		body.global_position = z.ground(at.x - 9.0 + i * 3.0, at.z)
		pets.append(body)
		i += 1
	p.global_position = z.ground(at.x, at.z + 14.0) + Vector3.UP
	p.face_toward(Vector3(at.x, p.global_position.y, at.z))
	p.camera_pivot.rotation.y = 0.0
	p.zoom = 8.0
	p.pitch = -0.1
	await _wait(1.0)
	await _shot("9zz_pets")
	for n: Node in pets:
		n.queue_free()
	World.time_override = -1.0
	p.level = 1


## Down the mausoleum stairs into the crypt, and back up.
func _t_crypt_door() -> void:
	if await _walk_border("crypt_door", "emberhold", Vector2(-32, -25), Vector2(0, -1), "emberhold_crypt"):
		await _walk_border("crypt_door", "emberhold_crypt", Vector2(0, 5), Vector2(0, 1), "emberhold")


## The necromancers' crypt under Emberhold, and its guildmaster.
func _t_crypt() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	print("crypt: %s, %d people %s" % [z.zone_name, _npcs().size(), _npcs().keys()])
	for view: Array in [[Vector3(0, 0, 6.3), Vector3(0, 0, -5), "door"], [Vector3(-3.5, 0, 1.5), Vector3(0, 0, -5.45), "morvath"]]:
		p.global_position = view[0] + Vector3.UP * 0.2
		p.face_toward(view[1])
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 5.0
		p.pitch = -0.15
		await _wait(1.0)
		await _shot("9zz_crypt_%s" % view[2])


## Tradeskills: every recipe names real items and containers; stations open
## only up close; cooking, tailoring (in a kit), smithing (the hammer stays)
## and alchemy combine; a wrong mix is refused; meals and potions are used,
## one meal at a time; walking away hands back what's left in a station.
func _t_tradeskills() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	var said: Array = []
	var listen := func(text: String, _c: Color) -> void: said.append(text)
	World.log_message.connect(listen)
	var bad := []
	var containers: Dictionary = GameData.recipes["containers"]
	for rid: String in GameData.recipes["recipes"]:
		var r: Dictionary = GameData.recipes["recipes"][rid]
		for id: String in (r["in"] as Dictionary).keys() + (r["out"] as Dictionary).keys():
			if not GameData.items.has(id):
				bad.append("%s: no item %s" % [rid, id])
		for c: String in r["containers"]:
			if not containers.has(c):
				bad.append("%s: no container %s" % [rid, c])
		if not GameData.skills["skills"].has(str(r["skill"])):
			bad.append("%s: no skill %s" % [rid, r["skill"]])
	var kinds := {}
	for st: Array in z.stations:
		kinds[st[0]] = int(kinds.get(st[0], 0)) + 1
	print("tradeskills: %d recipes, problems %s; stations in %s: %s" % [GameData.recipes["recipes"].size(), bad, z.zone_id, kinds])
	p.pack.clear()
	p.level = 10
	p.recalc_stats()
	var oven: Vector3 = z.stations.filter(func(st: Array) -> bool: return st[0] == "oven")[0][1]
	var fill := func(entries: Array) -> void:  # onto the cursor and into the station's slots, as a player would
		for i in entries.size():
			p.pack.add(entries[i][0], entries[i][1])
			World.request_click(p.entity_id, _where(p, entries[i][0]))
			World.request_click(p.entity_id, "c:%d" % i)
	# too far, then up close
	p.global_position = z.ground(oven.x + 20.0, oven.z) + Vector3.UP
	said.clear()
	World.request_station_open(p.entity_id, "oven")
	var far: String = said.back() if not said.is_empty() else ""
	p.global_position = z.ground(oven.x, oven.z + 2.5) + Vector3.UP
	World.request_station_open(p.entity_id, "oven")
	print("tradeskills: from 20 m -> '%s'; up close -> window %s" % [far, p.station_kind])
	# bread, then a wrong mix
	p.skills["cooking"] = 0
	fill.call([["bag_of_flour", 1], ["vial_of_water", 1]])
	said.clear()
	World.request_combine(p.entity_id, "c")
	print("tradeskills: flour + water -> '%s'; the oven holds %s" % [said.back() if not said.is_empty() else "", p.station_items.filter(func(e: Dictionary) -> bool: return not e.is_empty())])
	World.request_station_close(p.entity_id)
	World.request_station_open(p.entity_id, "oven")
	fill.call([["raw_meat", 1], ["vial_of_water", 1]])
	said.clear()
	World.request_combine(p.entity_id, "c")
	print("tradeskills: meat + water -> '%s'" % [said.back() if not said.is_empty() else ""])
	World.request_station_close(p.entity_id)
	# fifty roasts: the skill climbs until the recipe is trivial
	var made := 0
	for k in 50:
		p.pack.clear()
		World.request_station_open(p.entity_id, "oven")
		fill.call([["raw_meat", 1], ["jar_of_spices", 1]])
		World.request_combine(p.entity_id, "c")
		for e: Dictionary in p.station_items:
			if not e.is_empty() and e["item"] == "roast_meat":
				made += 1
		World.request_station_close(p.entity_id)
	print("tradeskills: 50 roasts -> %d made, cooking skill %d (trivial 12)" % [made, World.skill_value(p, "cooking")])
	# tailoring in a sewing kit
	p.pack.clear()
	p.pack.add_entry(Pack.entry("sewing_kit"))
	var kit := _where(p, "sewing_kit")
	p.pack.add("wolf_pelt", 1)
	World.request_click(p.entity_id, _where(p, "wolf_pelt"))
	World.request_click(p.entity_id, "b:%s:0" % kit.get_slice(":", 1))
	p.pack.add("tanning_salts", 1)
	World.request_click(p.entity_id, _where(p, "tanning_salts"))
	World.request_click(p.entity_id, "b:%s:1" % kit.get_slice(":", 1))
	p.skills["tailoring"] = 40
	World.request_combine(p.entity_id, kit)
	print("tradeskills: a wolf pelt and salts in the sewing kit -> %s" % [(p.pack.get_at(kit)["contents"] as Array).filter(func(e: Dictionary) -> bool: return not e.is_empty())])
	# smithing: the hammer stays in the forge
	var forge: Vector3 = z.stations.filter(func(st: Array) -> bool: return st[0] == "forge")[0][1]
	p.global_position = z.ground(forge.x + 2.5, forge.z) + Vector3.UP
	World.request_station_open(p.entity_id, "forge")
	p.skills["smithing"] = 60
	fill.call([["small_brick_of_ore", 1], ["water_flask", 1], ["smithy_hammer", 1]])
	World.request_combine(p.entity_id, "c")
	print("tradeskills: ore + flask + hammer in the forge -> %s" % [p.station_items.filter(func(e: Dictionary) -> bool: return not e.is_empty()).map(func(e: Dictionary) -> String: return e["item"])])
	# walking away hands everything back
	p.global_position = z.ground(forge.x + 20.0, forge.z) + Vector3.UP
	await _wait(0.3)
	print("tradeskills: walked away -> window %s; bar and hammer back in the pack: %d, %d" % ["open" if p.station_kind != "" else "closed", p.pack.count("iron_bar"), p.pack.count("smithy_hammer")])
	# eating and drinking
	p.pack.clear()
	p.buffs.clear()
	p.pack.add("roast_meat", 1)
	p.pack.add("hunters_pie", 1)
	p.pack.add("healing_potion", 2)
	p.pack.add("antidote", 1)
	World.request_use_item(p.entity_id, _where(p, "roast_meat"))
	var str0: int = p.attributes.get("str", 0)
	World.request_use_item(p.entity_id, _where(p, "hunters_pie"))
	var meals: Array = p.buffs.keys().filter(func(b: String) -> bool: return b.begins_with("meal_"))
	p.hp = 1
	World.request_use_item(p.entity_id, _where(p, "healing_potion"))
	var healed := p.hp
	said.clear()
	World.request_use_item(p.entity_id, _where(p, "healing_potion"))
	var again: String = said.back() if not said.is_empty() else ""
	p.dots.append({"spell": "rogue_venom", "caster_id": -1, "damage": 5, "ticks": 5, "next": 3.0})
	p.snare_left = 10.0
	World.request_use_item(p.entity_id, _where(p, "antidote"))
	print("tradeskills: meals -> %s (STR %d -> %d); a healing potion 1 -> %d hp; a second at once -> '%s'; antidote -> dots %d, snare %.0f" % [meals, str0,
			p.attributes.get("str", 0), healed, again, p.dots.size(), p.snare_left])
	# a recipe book's tooltip
	var tip: String = main.hud._item_tooltip("hearthside_cookbook")
	print("tradeskills: the cookbook reads:\n%s" % "\n".join(tip.split("\n").slice(0, 5)))
	World.log_message.disconnect(listen)
	p.pack.clear()
	p.buffs.clear()
	p.level = 1
	p.recalc_stats()


## The crafters' corners: the stations, the provisioner, the combine window
## and a sewing kit, to look at.
func _t_crafters_emberhold() -> void:
	await _crafters()


func _t_crafters_lanternhold() -> void:
	await _crafters()


func _t_crafters_rainhold() -> void:
	await _crafters()


func _crafters() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	World.time_override = 12.0
	var c := Vector3.ZERO
	for st: Array in z.stations:
		if st[0] != "campfire":
			c += (st[1] as Vector3) / 4.0
	var view := Vector3(c.x + 9.0, 0, c.z + 9.0)
	p.global_position = Vector3(view.x, z.surface_at(view.x, view.z) + 0.1, view.z)
	p.face_toward(Vector3(c.x, p.global_position.y, c.z))
	p.camera_pivot.rotation.y = 0.0
	p.zoom = 8.0
	p.pitch = -0.35
	await _wait(1.2)
	await _shot("9zy_crafters_%s" % z.zone_id)
	var oven: Vector3 = z.stations.filter(func(st: Array) -> bool: return st[0] == "oven")[0][1]
	var fwd := Vector3(oven.x - c.x, 0, oven.z - c.z).normalized()
	var at := Vector3(c.x, 0, c.z) + fwd * 2.0
	p.global_position = Vector3(at.x, z.surface_at(at.x, at.z) + 0.1, at.z)
	p.face_toward(Vector3(oven.x, p.global_position.y, oven.z))
	p.pack.clear()
	p.pack.add_entry(Pack.entry("sewing_kit"))
	p.pack.add("raw_meat", 3)
	p.pack.add("jar_of_spices", 3)
	p.pack.add("hearthside_cookbook", 1)
	World.request_station_open(p.entity_id, "oven")
	World.request_station_add(p.entity_id, _where(p, "raw_meat"))
	main.hud._toggle_bag(int(_where(p, "sewing_kit").get_slice(":", 1)))
	await _wait(0.8)
	await _shot("9zy_combine_%s" % z.zone_id)
	main.hud._close_all_bags()
	World.request_station_close(p.entity_id)
	p.pack.clear()
	World.time_override = -1.0


## Walks the player across one border: from a spot in the current zone, along
## a direction, until the next zone loads. Returns false if it started in the
## wrong zone.
func _walk_border(tag: String, from_zone: String, start: Vector2, dir: Vector2, to_zone: String) -> bool:
	var main := get_parent()
	var p := World.local_player
	if main.zone.zone_id != from_zone:
		print("%s: expected to be in %s, in %s" % [tag, from_zone, main.zone.zone_id])
		return false
	p.global_position = Vector3(start.x, main.zone.surface_at(start.x, start.y) + 1.0, start.y)
	for k in 400:
		if not is_instance_valid(main.zone) or main.zone.zone_id == to_zone:
			break
		p.velocity = Vector3(dir.x, 0, dir.y) * 7.0 + Vector3(0, p.velocity.y - 20.0 * get_physics_process_delta_time(), 0)
		p.move_and_slide()
		await get_tree().physics_frame
	await _wait(1.5)
	for k in 20:
		if is_instance_valid(main.zone) and main.zone.zone_id == to_zone:
			break
		await _wait(0.5)
	var z: Zone = main.zone
	print("%s: from %s -> now in %s at %s (on the ground: %s)" % [tag, from_zone, z.zone_id, Vector2(p.global_position.x, p.global_position.z),
			absf(p.global_position.y - z.surface_at(p.global_position.x, p.global_position.z)) < 1.5])
	return true


## The Long Monsoon's six crossings: Greenmoor - Rainhold - the Weeping Throat
## - Thornwood, every one both ways.
func _t_monsoon_borders() -> void:
	for leg: Array in [["greenmoor", Vector2(-165, 0), Vector2(-1, 0), "rainhold"], ["rainhold", Vector2(1.5, -60), Vector2(0, -1), "weeping_throat"],
			["weeping_throat", Vector2(190, 40), Vector2(1, 0), "thornwood"], ["thornwood", Vector2(-225, 40), Vector2(-1, 0), "weeping_throat"],
			["weeping_throat", Vector2(0, 190), Vector2(0, 1), "rainhold"], ["rainhold", Vector2(60, 0), Vector2(1, 0), "greenmoor"]]:
		if not await _walk_border("monsoon_borders", leg[0], leg[1], leg[2], leg[3]):
			return


## Rainhold: the stilt city over its lagoon. The decks carry you and everyone
## stands on them; the shrine blesses Jalendra's followers; five quests pay.
func _t_rainhold() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	World.time_override = 11.0
	# walk in from the Greenmoor road, down the east pier, onto the plaza
	p.global_position = Vector3(50, z.surface_at(50, 0) + 1.0, 0)
	var t0 := Time.get_ticks_msec()
	while Time.get_ticks_msec() - t0 < 7000 and p.global_position.x > 2.0:
		p.velocity = Vector3(-7, p.velocity.y - 20.0 * get_physics_process_delta_time(), 0)
		p.move_and_slide()
		await get_tree().physics_frame
	var deck := z.surface_at(1.5, 0)
	print("rainhold: walked the east pier to x %.1f; standing at y %.2f on a deck at %.2f (water %.2f); on floor %s" % [p.global_position.x,
			p.global_position.y, deck, z.water_level(1.5, 0), p.is_on_floor()])
	print("rainhold: bind point %s (deck %.2f)" % [z.bind_point, z.surface_at(z.bind_point.x, z.bind_point.z)])
	var off := []
	for n: Npc in _npcs().values():
		if absf(n.global_position.y - z.surface_at(n.global_position.x, n.global_position.z)) > 0.6:
			off.append("%s at %s (deck %.2f)" % [n.display_name, n.global_position, z.surface_at(n.global_position.x, n.global_position.z)])
	print("rainhold: %d people, standing off their decks: %s" % [_npcs().size(), off])
	for view: Array in [[Vector2(58, 4), Vector2(0, 0), "arrival"], [Vector2(1.5, -14), Vector2(-16.5, 2), "shrine"], [Vector2(1.5, 3), Vector2(15, -9), "halls"],
			[Vector2(1.5, 20), Vector2(1.5, 30), "dock"], [Vector2(8, -52), Vector2(1.5, -10), "north"]]:
		p.global_position = Vector3(view[0].x, z.surface_at(view[0].x, view[0].y) + 0.1, view[0].y)
		p.face_toward(Vector3(view[1].x, p.global_position.y, view[1].y))
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 10.0
		p.pitch = -0.2
		await _wait(1.0)
		await _shot("9zv_rainhold_%s" % view[2])
	var cam := Camera3D.new()
	get_tree().root.add_child(cam)
	cam.global_position = Vector3(70, 70, 80)
	cam.look_at(Vector3(0, 0, 0))
	cam.far = 800.0
	cam.make_current()
	await _wait(1.0)
	await _shot("9zv_rainhold_overview")
	cam.queue_free()
	World.time_override = 22.5
	p.global_position = Vector3(1.5, z.surface_at(1.5, -14) + 0.1, -14)
	p.face_toward(Vector3(-16.5, p.global_position.y, 2))
	await _wait(1.5)
	await _shot("9zv_rainhold_night")
	World.time_override = -1.0
	# the shrine's blessing, the city's services
	var npcs := _npcs()
	var said: Array = []
	var listen := func(text: String, _c: Color) -> void: said.append(text)
	World.log_message.connect(listen)
	var saved_deity := p.deity
	p.deity = "light"
	p.cooldowns.clear()
	p.buffs.erase("tide_trunk_blessing")
	_stand_by(p, npcs["tidepriest_nalini"])
	World.request_say(p.entity_id, "blessing")
	var refused := p.buffs.has("tide_trunk_blessing")
	p.deity = "water"
	World.request_say(p.entity_id, "blessing")
	print("rainhold: blessing -> a follower of Prabhagaj blessed: %s; a follower of Jalendra blessed: %s" % [refused, p.buffs.has("tide_trunk_blessing")])
	p.deity = saved_deity
	var trains := {}
	for id: String in ["gm_oruk", "gm_silt", "gm_imani", "gm_veyra"]:
		trains[id] = str(npcs[id].data["guildmaster"]["class"])
	print("rainhold: guildmasters %s; banker %s" % [trains, bool(npcs["banker_oduya"].data.get("banker", false))])
	# the quests
	p.level = 22
	p.recalc_stats()
	p.pack.clear()
	var asha: Npc = npcs["hunter_asha"]
	_stand_by(p, asha)
	for word in ["hail", "trolls", "tusks", "gorrak", "crocodile", "tooth"]:
		World.request_say(p.entity_id, word)
	p.pack.add("troll_tusk", 4)
	await _hand_in(p, asha, ["troll_tusk"])
	p.pack.add("gorraks_crown", 1)
	await _hand_in(p, asha, ["gorraks_crown"])
	p.pack.add("graveljaws_tooth", 1)
	await _hand_in(p, asha, ["graveljaws_tooth"])
	var nalini: Npc = npcs["tidepriest_nalini"]
	_stand_by(p, nalini)
	for word in ["hail", "storm", "heart"]:
		World.request_say(p.entity_id, word)
	p.pack.add("heart_of_the_storm", 1)
	await _hand_in(p, nalini, ["heart_of_the_storm"])
	var oji: Npc = npcs["fisher_oji"]
	_stand_by(p, oji)
	for word in ["hail", "fishing", "snapper"]:
		World.request_say(p.entity_id, word)
	p.pack.add("lagoon_snapper", 4)
	await _hand_in(p, oji, ["lagoon_snapper"])
	await _wait(0.3)
	print("rainhold: rewards: gloves %d, blade %d, leggings %d, charm %d, slicker %d; quests done %s" % [p.pack.count("trollhide_gloves"),
			p.pack.count("tidewarden_blade"), p.pack.count("crocscale_leggings"), p.pack.count("tide_trunk_charm"), p.pack.count("rain_slicker"),
			["troll_tusks", "the_stone_crown", "graveljaws_tooth", "heart_of_the_storm", "lagoon_snapper"].map(func(q: String) -> int: return int(p.quests.get(q, {}).get("completions", 0)))])
	World.log_message.disconnect(listen)
	p.level = 1
	p.recalc_stats()


## Fishing: a pole, worms, and open water in front of you.
func _t_fishing() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	var said: Array = []
	var listen := func(text: String, _c: Color) -> void: said.append(text)
	World.log_message.connect(listen)
	var kit := p.equipment.duplicate()
	p.pack.clear()
	p.equipment["primary"] = "fishing_pole"
	p.recalc_stats()
	var cast := func() -> String:
		p.cooldowns.clear()
		said.clear()
		World.request_item_click(p.entity_id, "primary")
		return " / ".join(said)
	# on the plaza, looking at planks; on the shore, looking inland; no worms
	p.global_position = Vector3(1.5, z.surface_at(1.5, 0) + 0.1, 0)
	p.face_toward(p.global_position + Vector3(0, 0, -5))
	p.pack.add("fishing_bait", 40)
	var planks: String = cast.call()
	p.global_position = Vector3(55, z.surface_at(55, 0) + 0.1, 0)
	p.face_toward(p.global_position + Vector3(5, 0, 0))
	var inland: String = cast.call()
	# at the end of the fishers' dock, facing the lagoon
	p.global_position = Vector3(1.5, z.surface_at(1.5, 31) + 0.1, 31)
	p.face_toward(p.global_position + Vector3(0, 0, 5))
	var caught := {}
	var skill0 := World.skill_value(p, "fishing")
	for k in 30:
		cast.call()
	for e: Dictionary in p.pack.entries():
		if e["item"] != "fishing_bait":
			caught[e["item"]] = int(caught.get(e["item"], 0)) + int(e["count"])
	var left := p.pack.count("fishing_bait")
	p.pack.remove("fishing_bait", left)
	var no_worms: String = cast.call()
	print("fishing: facing planks -> '%s'; facing land -> '%s'" % [planks, inland])
	print("fishing: 30 casts from the dock -> %s; worms left %d of 10; skill %d -> %d; without worms -> '%s'" % [caught, left, skill0,
			World.skill_value(p, "fishing"), no_worms])
	World.log_message.disconnect(listen)
	p.equipment = kit
	p.recalc_stats()


## The Weeping Throat: the jungle, the river, the temple of Jalendra, the troll camp.
func _t_weeping_throat() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	World.time_override = 11.0
	for view: Array in [[Vector2(199, 40), Vector2(150, 40), "arrival"], [Vector2(-92, -70), Vector2(-122, -100), "temple"],
			[Vector2(108, -36), Vector2(135, -58), "trolls"], [Vector2(60, 30), Vector2(20, 62), "river"], [Vector2(-128, 128), Vector2(-160, 160), "swamp"],
			[Vector2(72, 44), Vector2(40, 20), "giant_tree"], [Vector2(-30, -180), Vector2(-30, -200), "waterfall"]]:
		p.global_position = z.ground(view[0].x, view[0].y) + Vector3.UP
		p.face_toward(z.ground(view[1].x, view[1].y))
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 10.0
		p.pitch = -0.2
		await _wait(1.0)
		await _shot("9zw_throat_%s" % view[2])
	var cam := Camera3D.new()
	get_tree().root.add_child(cam)
	cam.global_position = Vector3(-40, 200, 250)
	cam.look_at(Vector3(10, 0, 0))
	cam.far = 1200.0
	cam.make_current()
	var env: Environment = (z.find_children("*", "WorldEnvironment", false, false)[0] as WorldEnvironment).environment
	env.fog_enabled = false
	await _wait(1.0)
	await _shot("9zw_throat_overview")
	env.fog_enabled = true
	cam.queue_free()
	World.time_override = 22.5
	p.global_position = z.ground(-92, -70) + Vector3.UP
	p.face_toward(z.ground(-122, -100))
	await _wait(1.5)
	await _shot("9zw_throat_temple_night")
	World.time_override = -1.0


## The Throat's monsters: all spawn, more elementals walk in the rain at night.
func _t_throat_life() -> void:
	var p := World.local_player
	var z: Zone = get_parent().zone
	World.time_override = 12.0
	await _wait(0.5)
	var counts := {}
	for m in World.get_mobs():
		counts[m.mob_id] = int(counts.get(m.mob_id, 0)) + 1
	print("throat_life: noon: %d monsters %s" % [World.get_mobs().size(), counts])
	World.time_override = 23.0
	await _wait(0.6)
	var night := World.get_mobs().filter(func(m: Mob) -> bool: return m.mob_id == "water_elemental").size()
	print("throat_life: water elementals at noon %d, at 23:00 %d" % [int(counts.get("water_elemental", 0)), night])
	World.time_override = 12.0
	var troll: Mob = _nearest_mob(p, "river_troll")
	if troll != null:
		troll.hp = troll.max_hp / 2
		var hp0 := troll.hp
		World._regen_tick()
		print("throat_life: a troll at half health regenerates %d a tick (hp_regen %d)" % [troll.hp - hp0, troll.hp_regen])
	for id: String in ["river_troll", "troll_chieftain", "water_elemental", "storm_elemental", "giant_frog", "river_croc", "ancient_croc"]:
		var m: Mob = _nearest_mob(p, id)
		if m == null:
			print("throat_life: no %s found" % id)
			continue
		m.set_physics_process(false)
		var at := m.global_position
		p.global_position = z.ground(at.x + 5.0, at.z + 4.0) + Vector3.UP
		p.face_toward(at)
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 6.0
		p.pitch = -0.15
		await _wait(0.8)
		await _shot("9zx_%s" % id)
		m.set_physics_process(true)
	World.time_override = -1.0


## The abilities for levels 21-25, each checked for what it does.
func _t_level25() -> void:
	var p := World.local_player
	var saved_class := p.char_class
	var said: Array = []
	var listen := func(text: String, _c: Color) -> void: said.append(text)
	World.log_message.connect(listen)
	var target: Mob = _nearest_mob(p, "giant_frog")
	var other: Mob = null
	for m in World.get_mobs():
		if m != target and not m.dead and (other == null or m.distance_to(target) < other.distance_to(target)):
			other = m
	for m: Mob in [target, other]:
		m.set_physics_process(false)
		m.max_hp = 100000
		m.hp = m.max_hp
		m.level = 22
	other.global_position = target.global_position + Vector3(0, 0.3, 2.5)
	var ready := func(cls: String, spells: Array) -> void:
		p.char_class = cls
		p.level = 25
		p.spells = spells
		p.cooldowns.clear()
		p.buffs.clear()
		p.equipment.clear()
		p.recalc_stats()
		p.hp = p.max_hp
		p.mana = p.max_mana
		for sk: String in GameData.skills["skills"]:
			if World.skill_cap(p, sk) > 0:
				p.skills[sk] = World.skill_cap(p, sk)
		for m in World.get_mobs():
			m.hate.clear()
		target.stun_left = 0.0
		target.snare_left = 0.0
		p.global_position = target.global_position + Vector3(2.0, 0.5, 0)
		World.request_set_target(p.entity_id, target.entity_id)
	var splashed := func(word: String) -> bool:
		return said.filter(func(t: String) -> bool: return ("caught in the " + word) in t).size() > 0
	# warrior
	await ready.call("warrior", ["shield_slam", "battle_fury", "whirlwind"])
	p.equipment["secondary"] = "tidesteel_shield"
	p.recalc_stats()
	var stuns := 0
	for k in 20:
		p.cooldowns.clear()
		target.stun_left = 0.0
		World.request_cast(p.entity_id, "shield_slam")
		if target.stun_left > 0.0:
			stuns += 1
	var delay0 := p.attack_delay
	World.request_cast(p.entity_id, "battle_fury")
	var delay1 := p.attack_delay
	said.clear()
	World.request_cast(p.entity_id, "whirlwind")
	print("level25: warrior: shield slam stunned %d of 20; battle fury delay %.2f -> %.2f; whirlwind splashed %s" % [stuns, delay0, delay1, splashed.call("whirlwind")])
	# cleric
	await ready.call("cleric", ["healing_tide", "word_of_awe", "armor_of_faith"])
	p.hp = 1
	World.request_cast(p.entity_id, "healing_tide")
	await _wait(4.4)
	var healed := p.hp
	World.request_cast(p.entity_id, "word_of_awe")
	await _wait(1.3)
	var awed := target.stun_left
	var ac0 := p.ac
	World.request_cast(p.entity_id, "armor_of_faith")
	await _wait(5.4)
	print("level25: cleric: healing tide 1 -> %d hp; word of awe stun %.1f s; armor of faith AC %d -> %d, regen %d" % [healed, awed, ac0, p.ac, p.hp_regen])
	# wizard
	await ready.call("wizard", ["chain_lightning", "arcane_harvest", "meteor"])
	said.clear()
	var t_hp := target.hp
	World.request_cast(p.entity_id, "chain_lightning")
	await _wait(3.2)
	var chain := t_hp - target.hp
	var chained: bool = splashed.call("chain lightning")
	var regen0 := p.mana_regen
	World.request_cast(p.entity_id, "arcane_harvest")
	await _wait(2.2)
	var regen1 := p.mana_regen
	p.mana = p.max_mana
	said.clear()
	t_hp = target.hp
	World.request_cast(p.entity_id, "meteor")
	await _wait(5.3)
	print("level25: wizard: chain lightning %d, spread %s; arcane harvest mana regen %d -> %d; meteor %d, splashed %s" % [chain, chained, regen0, regen1,
			t_hp - target.hp, splashed.call("meteor")])
	# rogue
	await ready.call("rogue", ["crippling_poison", "eviscerate", "vanish"])
	p.pack.clear()
	p.pack.add("coral_dirk")
	World.request_equip(p.entity_id, _where(p, "coral_dirk"))
	World.request_cast(p.entity_id, "crippling_poison")
	var procs := 0
	for k in 40:
		target.snare_left = 0.0
		World._try_buff_proc(p, target)
		if target.snare_left > 0.0:
			procs += 1
	t_hp = target.hp
	World.request_cast(p.entity_id, "eviscerate")
	var gutted := t_hp - target.hp
	target.add_hate(p, 500.0)
	other.add_hate(p, 200.0)
	World.request_cast(p.entity_id, "vanish")
	print("level25: rogue: crippling poison snared %d of 40 procs; eviscerate %d; vanish -> hidden %s, still hunted by %d" % [procs, gutted, p.hidden,
			World.get_mobs().filter(func(m: Mob) -> bool: return m.hate.has(p.entity_id)).size()])
	World.log_message.disconnect(listen)
	p.hidden = false
	for m: Mob in [target, other]:
		m.hate.clear()
		m.set_physics_process(true)
	p.char_class = saved_class
	p.equipment.clear()
	p.level = 1
	p.recalc_stats()


func _t_bleach_border() -> void:
	var main := get_parent()
	var p := World.local_player
	for leg: Array in [["sunward_steps", Vector2(0, -196), Vector2(0, -1), "the_bleach"], ["the_bleach", Vector2(0, 226), Vector2(0, 1), "sunward_steps"]]:
		if main.zone.zone_id != leg[0]:
			print("bleach_border: expected to be in %s, in %s" % [leg[0], main.zone.zone_id])
			return
		p.global_position = main.zone.ground(leg[1].x, leg[1].y) + Vector3.UP
		for k in 400:
			if not is_instance_valid(main.zone) or main.zone.zone_id == leg[3]:
				break
			p.velocity = Vector3(leg[2].x, 0, leg[2].y) * 7.0 + Vector3(0, p.velocity.y - 20.0 * get_physics_process_delta_time(), 0)
			p.move_and_slide()
			await get_tree().physics_frame
		await _wait(1.5)
		for k in 20:
			if is_instance_valid(main.zone) and main.zone.zone_id == leg[3]:
				break
			await _wait(0.5)
		var z: Zone = main.zone
		print("bleach_border: from %s -> now in %s at %s (on the ground: %s)" % [leg[0], z.zone_id, Vector2(p.global_position.x, p.global_position.z),
				absf(p.global_position.y - z.height_at(p.global_position.x, p.global_position.z)) < 1.5])


## The Bleach: the salt flats, the caravan camp, the titan's bones, the raider camp.
func _t_bleach() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	World.time_override = 11.0
	print("bleach: salt flat %s, mud %s, open ground %s" % [z.on_bare_patch(0, -20), z.on_bare_patch(-150, 90), z.on_bare_patch(-180, 180)])
	for view: Array in [[Vector2(0, 228), Vector2(0, 150), "arrival"], [Vector2(40, 195), Vector2(26, 208), "caravan"], [Vector2(20, 40), Vector2(0, -40), "flats"],
			[Vector2(-15, -95), Vector2(-42, -125), "ribcage"], [Vector2(125, -10), Vector2(155, -40), "raiders"], [Vector2(-130, 70), Vector2(-165, 95), "oasis"],
			[Vector2(100, -115), Vector2(135, -145), "queen"]]:
		p.global_position = z.ground(view[0].x, view[0].y) + Vector3.UP
		p.face_toward(z.ground(view[1].x, view[1].y))
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 10.0
		p.pitch = -0.2
		await _wait(1.0)
		await _shot("9zt_bleach_%s" % view[2])
	var cam := Camera3D.new()
	get_tree().root.add_child(cam)
	cam.global_position = Vector3(-40, 200, 250)
	cam.look_at(Vector3(10, 0, 0))
	cam.far = 1200.0
	cam.make_current()
	var env: Environment = (z.find_children("*", "WorldEnvironment", false, false)[0] as WorldEnvironment).environment
	env.fog_enabled = false
	await _wait(1.0)
	await _shot("9zt_bleach_overview")
	env.fog_enabled = true
	cam.queue_free()
	World.time_override = 22.5
	p.global_position = z.ground(-15, -95) + Vector3.UP
	p.face_toward(z.ground(-42, -125))
	await _wait(1.5)
	await _shot("9zt_bleach_ribcage_night")
	World.time_override = -1.0


## The Bleach's people and monsters: all spawn, the three quests pay out,
## more bones walk at night.
func _t_bleach_life() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	World.time_override = 12.0
	await _wait(0.5)
	var counts := {}
	for m in World.get_mobs():
		counts[m.mob_id] = int(counts.get(m.mob_id, 0)) + 1
	print("bleach_life: noon: %d monsters %s" % [World.get_mobs().size(), counts])
	p.level = 20
	p.recalc_stats()
	p.pack.clear()
	var npcs := _npcs()
	var suri: Npc = npcs["caravan_master_suri"]
	var ibrem: Npc = npcs["saltmaster_ibrem"]
	_stand_by(p, suri)
	for word in ["hail", "scorpions", "stingers", "raiders", "vashti"]:
		World.request_say(p.entity_id, word)
	p.pack.add("scorpion_stinger", 4)
	await _hand_in(p, suri, ["scorpion_stinger"])
	p.pack.add("scorpion_stinger", 4)
	await _hand_in(p, suri, ["scorpion_stinger"])
	p.pack.add("raider_warhorn", 1)
	await _hand_in(p, suri, ["raider_warhorn"])
	_stand_by(p, ibrem)
	for word in ["hail", "bones", "titan", "heart"]:
		World.request_say(p.entity_id, word)
	p.pack.add("titans_heart", 1)
	await _hand_in(p, ibrem, ["titans_heart"])
	await _wait(0.3)
	print("bleach_life: rewards: boots %d, blade %d, talisman %d; quests done %s" % [p.pack.count("sandstrider_boots"), p.pack.count("caravan_guards_blade"),
			p.pack.count("bone_talisman"), ["stingers_for_the_road", "the_salt_wolf", "heart_of_the_titan"].map(func(q: String) -> int: return int(p.quests.get(q, {}).get("completions", 0)))])
	World.time_override = 23.0
	await _wait(0.6)
	var night := 0
	for m in World.get_mobs():
		if m.mob_id == "bone_giant":
			night += 1
	print("bleach_life: bone giants at noon %d, at 23:00 %d" % [int(counts.get("bone_giant", 0)), night])
	World.time_override = 12.0
	for id: String in ["giant_scorpion", "scorpion_queen", "salt_basilisk", "bone_giant", "bone_titan", "salt_raider", "raider_chief"]:
		var m: Mob = _nearest_mob(p, id)
		if m == null:
			print("bleach_life: no %s found" % id)
			continue
		m.set_physics_process(false)
		var at := m.global_position
		p.global_position = z.ground(at.x + 4.0, at.z + 3.0) + Vector3.UP
		p.face_toward(at)
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 5.0
		p.pitch = -0.15
		await _wait(0.8)
		await _shot("9zu_%s" % id)
		m.set_physics_process(true)
	World.time_override = -1.0

## The Sunward Steps - Lanternhold border, walked both ways: in at the city's gate.
func _t_lanternhold_border() -> void:
	var main := get_parent()
	var p := World.local_player
	for leg: Array in [["sunward_steps", Vector2(200, 0), Vector2(1, 0), "lanternhold"], ["lanternhold", Vector2(-84, 0), Vector2(-1, 0), "sunward_steps"]]:
		if main.zone.zone_id != leg[0]:
			print("lanternhold_border: expected to be in %s, in %s" % [leg[0], main.zone.zone_id])
			return
		p.global_position = main.zone.ground(leg[1].x, leg[1].y) + Vector3.UP
		for k in 400:
			if not is_instance_valid(main.zone) or main.zone.zone_id == leg[3]:
				break
			p.velocity = Vector3(leg[2].x, 0, leg[2].y) * 7.0 + Vector3(0, p.velocity.y - 20.0 * get_physics_process_delta_time(), 0)
			p.move_and_slide()
			await get_tree().physics_frame
		await _wait(1.5)
		for k in 20:
			if is_instance_valid(main.zone) and main.zone.zone_id == leg[3]:
				break
			await _wait(0.5)
		var z: Zone = main.zone
		print("lanternhold_border: from %s -> now in %s at %s (on the ground: %s)" % [leg[0], z.zone_id, Vector2(p.global_position.x, p.global_position.z),
				absf(p.global_position.y - z.height_at(p.global_position.x, p.global_position.z)) < 1.5])


## Lanternhold: the gate, the shrine plaza by day and by night, the Dawn-Tusk's
## blessing (only for his followers, once an hour), guildmasters and the bank.
func _t_lanternhold() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	World.time_override = 11.0
	for view: Array in [[Vector2(-46, 0), Vector2(0, 0), "gate"], [Vector2(0, 26), Vector2(0, 0), "shrine"], [Vector2(30, 36), Vector2(0, 0), "street"]]:
		p.global_position = z.ground(view[0].x, view[0].y) + Vector3.UP
		p.face_toward(z.ground(view[1].x, view[1].y))
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 9.0
		p.pitch = -0.12
		await _wait(1.0)
		await _shot("9zs_lanternhold_%s" % view[2])
	World.time_override = 22.5
	for view: Array in [[Vector2(0, 26), Vector2(0, 0), "shrine_night"], [Vector2(-46, 0), Vector2(0, 0), "gate_night"]]:
		p.global_position = z.ground(view[0].x, view[0].y) + Vector3.UP
		p.face_toward(z.ground(view[1].x, view[1].y))
		await _wait(1.5)
		await _shot("9zs_lanternhold_%s" % view[2])
	World.time_override = -1.0
	var npcs := _npcs()
	var amaru: Npc = npcs["dawnpriest_amaru"]
	var said: Array = []
	var listen := func(text: String, _c: Color) -> void: said.append(text)
	World.log_message.connect(listen)
	var saved_deity := p.deity
	p.deity = "fire"
	p.cooldowns.clear()
	p.buffs.erase("dawn_tusk_blessing")
	_stand_by(p, amaru)
	World.request_say(p.entity_id, "blessing")
	var refused := p.buffs.has("dawn_tusk_blessing")
	p.deity = "light"
	World.request_say(p.entity_id, "blessing")
	var blessed := p.buffs.has("dawn_tusk_blessing")
	said.clear()
	World.request_say(p.entity_id, "blessing")
	print("lanternhold: blessing -> a follower of Agnavar blessed: %s; a follower of Prabhagaj blessed: %s (+%d AC); asking again: '%s'" % [refused, blessed,
			int(GameData.spells["dawn_tusk_blessing"]["stats"]["ac"]), said.filter(func(t: String) -> bool: return "within the hour" in t).size() > 0])
	p.deity = saved_deity
	var trains := {}
	for id: String in ["gm_idris", "gm_solenne", "gm_orrin", "gm_kestrel"]:
		trains[id] = str(npcs[id].data["guildmaster"]["class"])
	var bank_ok := bool(npcs["banker_tamsyn"].data.get("banker", false))
	print("lanternhold: guildmasters %s; banker %s; bind point %s (the shrine)" % [trains, bank_ok, z.bind_point])
	World.log_message.disconnect(listen)


## Encumbrance: what things weigh, a bag that lightens its load, coin that
## weighs until it's banked, and the slowdown past your limit.
func _t_encumbrance() -> void:
	var p := World.local_player
	var said: Array = []
	var listen := func(text: String, _c: Color) -> void: said.append(text)
	World.log_message.connect(listen)
	var saved_class := p.char_class
	p.char_class = "warrior"
	p.level = 9
	p.recalc_stats()
	p.pack.clear()
	p.equipment.clear()
	p.coin = 0
	p.bank_coin = 0
	var sample := {}
	for id: String in ["iron_dagger", "iron_short_sword", "oak_staff", "round_shield", "leather_tunic", "studded_tunic", "iron_greaves", "cloth_cap", "wolf_pelt", "crude_arrow", "tarnished_ring", "leather_backpack"]:
		sample[id] = GameData.item_weight(id)
	print("encumbrance: weights %s" % sample)
	print("encumbrance: a level 9 warrior carries %.1f of %d" % [p.carried_weight(), int(p.carry_capacity())])
	p.pack.add("wolf_pelt", 20)
	var loose := p.carried_weight()
	p.pack.clear()
	var bag := Pack.entry("leather_backpack")
	bag["contents"][0] = Pack.entry("wolf_pelt", 20)
	p.pack.slots[0] = bag
	print("encumbrance: 20 wolf pelts loose %.1f, in a leather backpack %.1f" % [loose, p.carried_weight()])
	p.pack.clear()
	p.coin = 500 * 1000  # 500 platinum
	await _wait(1.3)
	print("encumbrance: 500 platinum on hand -> %.1f of %d, speed x%.2f; told '%s'" % [p.carried_weight(), int(p.carry_capacity()), p.encumbrance_speed(),
			said.filter(func(t: String) -> bool: return "burden" in t).back() if said.any(func(t: String) -> bool: return "burden" in t) else "-"])
	p.coin = 900 * 1000
	said.clear()
	World.request_sprint(p.entity_id, true)
	print("encumbrance: 900 platinum -> speed x%.2f; sprinting %s (%s)" % [p.encumbrance_speed(), p.sprinting, said.back() if not said.is_empty() else "-"])
	p.bank_coin += p.coin  # the banker's vault weighs nothing
	p.coin = 0
	await _wait(1.3)
	print("encumbrance: banked -> %.1f, speed x%.2f; told '%s'" % [p.carried_weight(), p.encumbrance_speed(), said.back() if not said.is_empty() else "-"])
	World.log_message.disconnect(listen)
	p.bank_coin = 0
	p.char_class = saved_class
	p.level = 1
	p.recalc_stats()
