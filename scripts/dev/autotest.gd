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
	# step into the zone line that leads there, or toward Greenmoor, which links them all
	for hop in 3:
		if main.zone.zone_id == zone_id:
			break
		var lines: Array = main.zone.data.get("zone_lines", [])
		var line: Dictionary = {}
		for zl: Dictionary in lines:
			if zl["to"] == zone_id:
				line = zl
		if line.is_empty():
			for zl: Dictionary in lines:
				if zl["to"] == "greenmoor":
					line = zl
		if line.is_empty():
			break
		p.global_position = main.zone.ground(line["pos"][0], line["pos"][1]) + Vector3.UP
		await _wait(2.5)
	print("zone: %s at %s" % [main.zone.zone_id, p.global_position])


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
