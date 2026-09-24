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
	["wornlook", "greenmoor"],
	["itemwindow", "greenmoor"],
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
	for k in 4:
		p.inventory.append("gnoll_fang")
	p.inventory.append("rat_whiskers")
	p.inventory_changed.emit()
	World.request_hail(p.entity_id)  # he notices the fangs
	World.request_trade_open(p.entity_id)
	for item_id in ["gnoll_fang", "gnoll_fang", "gnoll_fang", "gnoll_fang", "rat_whiskers"]:
		World.request_trade_add(p.entity_id, p.inventory.find(item_id))  # the fifth is refused: 4 slots
	World.request_trade_remove(p.entity_id, 0)
	World.request_trade_add(p.entity_id, p.inventory.find("gnoll_fang"))
	await _wait(0.4)
	await _shot("1f_quest_trade")
	World.request_trade_remove(p.entity_id, 3)  # swap a fang for the whiskers
	World.request_trade_add(p.entity_id, p.inventory.find("rat_whiskers"))
	World.request_trade_give(p.entity_id)  # 3 fangs + whiskers: not enough, all handed back
	print("short give: fangs=%d whiskers=%d quests=%s" % [p.inventory.count("gnoll_fang"), p.inventory.count("rat_whiskers"), p.quests])
	World.request_trade_open(p.entity_id)
	for k in 4:
		World.request_trade_add(p.entity_id, p.inventory.find("gnoll_fang"))
	World.request_trade_give(p.entity_id)
	print("quest after turn-in: %s coin=%d xp=%d has_sword=%s fangs=%d whiskers=%d" % [p.quests, p.coin, p.xp,
			"wardens_short_sword" in p.inventory, p.inventory.count("gnoll_fang"), p.inventory.count("rat_whiskers")])
	await _wait(0.5)
	await _shot("1g_quest_done")
	p.inventory.erase("rat_whiskers")
	main.hud._toggle_inventory()
	p.inventory.erase("wardens_short_sword")
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
	var bag_before := p.inventory.duplicate()
	p.inventory.append_array(["rusty_short_sword", "tarnished_ring", "copper_band@fine", "leather_boots", "round_shield"])
	World.request_equip(p.entity_id, p.inventory.find("rusty_short_sword"))
	World.request_equip(p.entity_id, p.inventory.find("tarnished_ring"))
	World.request_equip(p.entity_id, p.inventory.find("copper_band@fine"))
	World.request_equip(p.entity_id, p.inventory.find("leather_boots"))
	World.request_equip(p.entity_id, p.inventory.find("round_shield"))
	print("items: wizard sword blocked=%s rings=%s/%s boots=%s shield blocked=%s attrs=%s mana=%d" % [
			p.equipment.get("primary") != "rusty_short_sword", p.equipment.get("ring1"), p.equipment.get("ring2"),
			p.equipment.get("feet"), not p.equipment.has("secondary"), p.attributes, p.max_mana])
	var lore_free := World.can_receive(p, "wardens_short_sword", true)
	p.bank_items.append("wardens_short_sword")
	print("items: lore sword receivable without one=%s, with one banked=%s; cleaver effectiveness at level %d=%.2f" % [
			lore_free, World.can_receive(p, "wardens_short_sword", true), p.level, p.item_effectiveness(GameData.item("grubnaks_cleaver"))])
	p.bank_items.erase("wardens_short_sword")
	for k in 25:
		p.inventory.append("bone_chips")
	print("items: 25 bone chips use %d slots; room for a 26th=%s" % [p.slots_used() - bag_before.size() - 2, p.room_for("bone_chips")])
	p.inventory.append("bonecarved_talisman")
	World.request_equip(p.entity_id, p.inventory.find("bonecarved_talisman"))
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
	p.inventory = bag_before
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
	print("respawned: dead=%s pos=%s inventory=%s equipment=%s" % [p.dead, p.global_position, p.inventory, p.equipment])
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
	for item_id in ["gnoll_fang", "gnoll_fang", "gnoll_fang", "rat_whiskers"]:
		p.inventory.append(item_id)
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
	World.request_sell(p.entity_id, p.inventory.find("gnoll_fang"))
	World.request_sell(p.entity_id, p.inventory.find("gnoll_fang"))
	World.request_buy(p.entity_id, "leather_cap")
	World.request_buy(p.entity_id, "gnoll_fang")  # buy one back from his stock
	print("shop: coin %d -> %d fangs=%d cap=%s stock=%s" % [coin0, p.coin, p.inventory.count("gnoll_fang"), "leather_cap" in p.inventory, World.merchant_stock])
	await _wait(0.5)
	await _shot("7h_shop")
	var odile: Npc = npcs["banker_odile"]
	p.global_position = odile.global_position + (-odile.global_transform.basis.z) * 2.5 + Vector3.UP * 0.5
	World.request_set_target(p.entity_id, odile.entity_id)
	World.request_interact(p.entity_id)
	World.request_bank_deposit(p.entity_id, p.inventory.find("rat_whiskers"))
	World.request_bank_deposit(p.entity_id, p.inventory.find("leather_cap"))
	World.request_bank_coin(p.entity_id, 500)
	World.request_bank_withdraw(p.entity_id, 1)
	print("bank: items=%s coin=%d purse=%d cap_back=%s" % [p.bank_items, p.bank_coin, p.coin, "leather_cap" in p.inventory])
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
		print("wornlook: %s -> look.worn %s" % [item if item != "" else "(bare)", p.look.get("worn")])
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
		print("wornlook: %s outfit -> %s" % [outfit, p.look.get("worn")])
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
	p.inventory.append("leather_boots@superior")
	p.inventory_changed.emit()
	hud._toggle_inventory()
	await _wait(0.3)
	var right := InputEventMouseButton.new()
	right.button_index = MOUSE_BUTTON_RIGHT
	right.pressed = true
	for b in hud._bag_grid.get_children():
		if (b as Button).text.begins_with("Superior Leather Boots"):
			b.gui_input.emit(right)
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
	p.inventory.erase("leather_boots@superior")

## Moves the tester through the zone line into this zone if it isn't there.
func _ensure_zone(zone_id: String) -> void:
	var main := get_parent()
	var p := World.local_player
	if main.zone.zone_id == zone_id:
		return
	if p.dead:
		await _wait(5.0)
	p.global_position = main.zone.ground(0, 181 if zone_id == "emberhold" else -97) + Vector3.UP
	await _wait(2.5)
	print("zone: %s at %s" % [main.zone.zone_id, p.global_position])


func _npcs() -> Dictionary:
	var out := {}
	for obj: Node3D in World.objects.values():
		if obj is Npc:
			out[(obj as Npc).npc_id] = obj
	return out


func _nearest_mob(p: Player, only_id := "") -> Mob:
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
