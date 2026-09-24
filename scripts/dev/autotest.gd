extends Node
## Scripted smoke test. Creates a throwaway wizard, fights, loots, dies,
## respawns, and saves screenshots along the way. Run with:
##   godot --path . -- --autotest --shots=/some/dir

var shots_dir := ""


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--shots="):
			shots_dir = a.substr(8)
	World.log_message.connect(func(t: String, _c: Color) -> void: print("[log] ", t))
	_run()


func _run() -> void:
	var main := get_parent()
	await _wait(0.6)
	await _shot("0_title")
	for c in main.get_children():
		if c is CharCreate:
			(c as CharCreate).confirmed.emit({"name": "Tester", "class": "wizard", "zone": "greenmoor"})
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
	World.request_hail(p.entity_id)
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

	main.hud._toggle_inventory()
	await _wait(0.4)
	await _shot("4_inventory")
	main.hud._toggle_inventory()

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

	World.damage(p, 9999, _nearest_mob(p))
	await _wait(1.0)
	await _shot("5_dead")
	await _wait(4.5)
	print("respawned: dead=%s pos=%s inventory=%s equipment=%s" % [p.dead, p.global_position, p.inventory, p.equipment])
	p.zoom = 0.0
	await _wait(0.6)
	await _shot("6_first_person")

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

	p.global_position = main.zone.ground(0, -97) + Vector3.UP
	await _wait(2.5)
	print("zone after return: %s at %s" % [main.zone.zone_id, p.global_position])
	await _shot("7g_back_in_greenmoor")

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
	print("AUTOTEST DONE")
	get_tree().quit()


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
