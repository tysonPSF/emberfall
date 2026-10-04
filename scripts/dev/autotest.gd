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
	["many_spells", "emberhold"],
	["bag_rainhold", "rainhold"],
	["bag_dewstep", "dewstep"],
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
	["zone_map", "greenmoor"],
	["zone_map_town", "rainhold"],
	["compass", "greenmoor"],
	["solid_logs", "greenmoor"],
	["quest_hints", "greenmoor"],
	["vale_quests", "thornwood"],
	["face_path", "harrowfield"],
	["shaman", "greenmoor"],
	["homeward", "greenmoor"],
	["grove", "greenmoor"],
	["emotes", "greenmoor"],
	["terrace_roads", "greenmoor"],
	["social", "greenmoor"],
	["exit_levels", "greenmoor"],
	["swing_bar", "greenmoor"],
	["crits", "greenmoor"],
	["journal", "greenmoor"],
	["alignment", "greenmoor"],
	["blackwater_borders", "rainhold"],
	["blackwater_life", "the_wallow"],
	["blackwater_views", "murkhold"],
	["west_march_life", "broken_march"],
	["deity_picker", "greenmoor"],
	["quest_share", "greenmoor"],
	["delete_guild", "greenmoor"],
	["evil_gods", "greenmoor"],
	["dusk_gods", "greenmoor"],
	["login_home", "rainhold"],
	["login_tavern", "emberhold"],
	["quest_marks", "greenmoor"],
	["high_terrace_ground", "high_terrace"],
	["starter_spawns", "greenmoor"],
	["item_ladder", "greenmoor"],
	["spawn_coverage", "greenmoor"],
	["zone_outlines", "greenmoor"],
	["named_scaling", "greenmoor"],
	["hubs_pilot", "thornwood"],
	["hubs_1024", "the_burn"],
	["hubs_768a", "silted_reach"],
	["hubs_768b", "hollow_air"],
	["hubs_small", "greenmoor"],
	["arrow_flight", "greenmoor"],
	["terrace_views", "high_terrace"],
	["flats_views", "mirror_flats"],
	["squawkzilla", "mirror_flats"],
	["rare_spawns", "thornwood"],
	["salt_islands", "mirror_flats"],
	["quest_areas", "thornwood"],
	["combat_audio", "greenmoor"],
	["summon_corpse", "greenmoor"],
	["evil_kin", "greenmoor"],
	["guild_bank", "emberhold"],
	["social_chat", "greenmoor"],
	["cinderpass_hubs", "cinderpass"],
	["lava_bridges", "cinderpass"],
	["guard_strength", "emberhold"],
	["talk_phrases", "cinderpass"],
	["food_tooltips", "greenmoor"],
	["pathcallers", "emberhold"],
	["look_controls", "greenmoor"],
	["forge_weapons", "greenmoor"],
	["map_zoom", "thornwood"],
	["living_roots", "greenmoor"],
	["blow_verbs", "greenmoor"],
	["repeat_quests", "greenmoor"],
	["bank_coin_amounts", "emberhold"],
	["compare_slots", "greenmoor"],
	["city_banks", "emberhold"],
	["room_floors", "emberhold"],
	["cast_bar_move", "greenmoor"],
	["bind_sitting", "greenmoor"],
	["player_cc", "greenmoor"],
	["dawn_line", "lanternhold"],
	["chat_resize", "greenmoor"],
	["june", "lanternhold"],
	["velassa", "greenmoor"],
	["velassa_pounce", "greenmoor"],
	["city_paths", "lanternhold"],
	["tuskway_borders", "harrowfield"],
	["tuskway_life", "the_tuskway"],
	["melee_swings", "greenmoor"],
	["plate_looks", "greenmoor"],
	["caster_stats", "greenmoor"],
	["boss_camp_respawn", "thornwood"],
	["giant_sizes", "the_bleach"],
	["grove_uniques", "greenmoor"],
	["bags_with_inventory", "greenmoor"],
	["camps", "greenmoor"],
	["bridges", "greenmoor"],
	["bone_chips", "greenmoor"],
	["pet_gear", "greenmoor"],
	["char_preview", "greenmoor"],
	["trainer_tabs", "greenmoor"],
	["ashfall_borders", "hollowmere"],
	["ranger", "greenmoor"],
	["cap30", "greenmoor"],
	["terrace_life", "high_terrace"],
	["cinder_life", "cinderpass"],
	["char_stats", "greenmoor"],
	["races", "greenmoor"],
	["group_window", "greenmoor"],
	["tooltips", "greenmoor"],
	["group_xp", "greenmoor"],
	["race_change", "greenmoor"],
	["gender", "greenmoor"],
	["pet_fixes", "greenmoor"],
	["drag_windows", "greenmoor"],
	["hair", "greenmoor"],
	["dewstep_borders", "lanternhold"],
	["dewstep_life", "dewstep"],
	["pet_anims", "greenmoor"],
	["afk", "greenmoor"],
	["cap35", "greenmoor"],
	["ashfall35_borders", "cinderpass"],
	["burn_life", "the_burn"],
	["glass_life", "blackglass"],
	["forgehold", "forgehold"],
	["part3_borders", "high_terrace"],
	["part3_borders_monsoon", "reedmere"],
	["dawnwatch_life", "dawnwatch"],
	["flats_life", "mirror_flats"],
	["reach_life", "silted_reach"],
	["tidemouth_life", "tidemouth"],
	["cap40", "greenmoor"],
	["sky_borders", "drownfast"],
	["windbreak_life", "windbreak"],
	["grass_life", "the_long_grass"],
	["galehold", "galehold"],
	["magician_nukes", "greenmoor"],
	["pet_messages", "greenmoor"],
	["hearth_borders", "forgehold"],
	["hearth_life", "agnavars_hearth"],
	["smoke_life", "smokewood"],
	["cap45", "greenmoor"],
	["sky_borders_2", "galehold"],
	["stonesail_life", "stonesail"],
	["hollow_life", "hollow_air"],
	["step_life", "vayukeths_step"],
	["cap50", "greenmoor"],
	["bone_borders", "hollow_air"],
	["fogfall_life", "fogfall"],
	["ivory_life", "ivory_field"],
	["unlit_life", "the_unlit"],
	["barrowhold", "barrowhold"],
	["bone_borders_2", "fogfall"],
	["lastwalk_life", "lastwalk"],
	["table_life", "timirajs_table"],
	["swimming", "rainhold"],
	["town_views", "rainhold"],
	["porch_reach", "rainhold"],
	["stutter", "rainhold"],
	["monsoon_west_borders", "weeping_throat"],
	["reedmere_life", "reedmere"],
	["drownfast_life", "drownfast"],
	["hotbars", "greenmoor"],
	["pets", "greenmoor"],
	["necromancer", "greenmoor"],
	["pet_look", "greenmoor"],
	["crypt_door", "emberhold"],
	["crypt", "emberhold_crypt"],
	["balance", "greenmoor"],
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
	["carry_limits", "greenmoor"],
	["strike_timer", "greenmoor"],
	["timer_speed", "greenmoor"],
	["elowen", "thornwood"],
	["signs", "greenmoor"],
	["river", "thornwood"],
	["landmarks_tw", "thornwood"],
	["camp", "greenmoor"],
	["zone_unload", "greenmoor"],
	["merricks_line", "emberhold_tavern"],
	["wellspring", "wellspring"],
	["wellspring_quest", "wellspring"],
	["corran", "greenmoor"],
	["corran_support", "greenmoor"],
	["corran_boss", "wellspring"],
	["dimming_line", "greenmoor"],
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
			(c as CharCreate).confirmed.emit({"name": "Tester", "class": "wizard", "deity": "wind", "zone": "greenmoor", "stats": {}, "race": "human"})
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
	# Merrick at the pond: hail, ask about the trout, then open his shop. He's
	# only back at the pond once his line is done (merricks_line tests the rest).
	for q in ["merricks_line_sinew", "merricks_line_spring", "merricks_line_word", "merricks_line_pond"]:
		p.quests[q] = {"active": false, "completions": 1}
	await _wait(0.7)  # Npc._update_sight shows him
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


## No cap on what you know: a level-16 warrior who knows his first eight
## abilities can still learn Provoke, his ninth (there was once a cap of eight).
func _t_many_spells() -> void:
	var p := World.local_player
	var npcs := _npcs()
	var saved := [p.char_class, p.level, p.spells.duplicate(), p.coin]
	p.char_class = "warrior"
	p.level = 16
	p.spells = ["kick", "taunt", "bind_wound", "bash", "battle_cry", "heroic_strike", "rally", "shield_wall"]
	p.coin = 5000
	p.recalc_stats()
	var gm: Npc = npcs["gm_brask"]
	p.global_position = gm.global_position + Vector3(0, 0.5, -2.5)
	World.request_set_target(p.entity_id, gm.entity_id)
	World.request_interact(p.entity_id)
	print("many_spells: knows %d; Provoke: %s" % [p.spells.size(), "ok" if World.train_block(p, "provoke") == "" else World.train_block(p, "provoke")])
	World.request_train(p.entity_id, "provoke")
	print("many_spells: learned Provoke -> %s (knows %d)" % ["provoke" in p.spells, p.spells.size()])
	World.request_service_close(p.entity_id)
	p.char_class = saved[0]; p.level = saved[1]; p.spells = saved[2]; p.coin = saved[3]
	p.recalc_stats()


## A starting city's bag quest line, every step in one zone: say the keyword to
## the first giver, then hand each giver what the step wants.
func _bag_chain(tag: String, keyword: String, steps: Array, bag: String) -> void:
	var p := World.local_player
	var npcs := _npcs()
	for q: String in ["rain_pack_needles", "rain_pack_net", "rain_pack_clasp", "picker_satchel_thread", "picker_satchel_body", "picker_satchel_clasp"]:
		p.quests.erase(q)
	_stand_by(p, npcs[steps[0][0]])
	World.request_say(p.entity_id, keyword)
	for s: Array in steps:
		var giver: Npc = npcs[s[0]]
		_stand_by(p, giver)
		var give: Array = []
		for item: String in (s[1] as Dictionary):
			p.pack.add(item, int(s[1][item]))
		for item: String in GameData.quests[s[2]]["wants"]:
			give.append(item)
		await _hand_in(p, giver, give)
		print("%s: %s done -> %s" % [tag, s[2], p.quests.get(s[2], {})])
	var place := _where(p, bag)
	print("%s: %s at %s, %d slots" % [tag, GameData.item_name(bag), place, int(GameData.item(bag).get("bag", 0)) if place != "" else 0])


func _t_bag_rainhold() -> void:
	await _bag_chain("bag_rainhold", "rainproof pack", [["provisioner_tamu", {"bone_chips": 4}, "rain_pack_needles"],
			["fisher_oji", {"lagoon_snapper": 2}, "rain_pack_net"], ["provisioner_tamu", {"gnoll_fang": 3}, "rain_pack_clasp"]], "tamus_rainproof_pack")


func _t_bag_dewstep() -> void:
	await _bag_chain("bag_dewstep", "satchel", [["tea_seller_moti", {"moth_wing": 4}, "picker_satchel_thread"],
			["headpicker_anjali", {"jackal_pelt": 2}, "picker_satchel_body"], ["tea_seller_moti", {"rice_beetle_shell": 2}, "picker_satchel_clasp"]], "motis_tea_pickers_satchel")


## Every race's carry limit at level 1 (a caster with no strength spent, and a
## warrior's recommended spread), and whether a first hour's loot slows them.
func _t_carry_limits() -> void:
	var p := World.local_player
	var saved := [p.race, p.char_class, p.level, p.stat_points.duplicate(), p.equipment.duplicate()]
	var rows := PackedStringArray()
	for race: String in GameData.races:
		p.race = race
		p.level = 1
		p.char_class = "wizard"
		p.stat_points = {"int": 15, "sta": 10}
		p.recalc_stats()
		var caster := p.carry_capacity()
		p.char_class = "warrior"
		p.stat_points = {"str": 10, "sta": 10, "agi": 5}
		p.recalc_stats()
		rows.append("%s %d/%d" % [race, int(caster), int(p.carry_capacity())])
	print("carry_limits: level 1, caster/warrior: %s" % ", ".join(rows))
	# a gnome wizard with a staff, a cloth robe and a first hour's pickings
	p.race = "gnome"
	p.char_class = "wizard"
	p.stat_points = {"int": 15, "sta": 10}
	p.pack.clear()
	p.equipment = {"primary": "worn_staff"}
	p.recalc_stats()
	for item: String in ["rat_whiskers", "gnoll_fang", "beetle_eye", "bone_chips"]:
		p.pack.add(item, 6)
	p.pack.add("blackpaw_pelt", 6)
	p.pack.add("rusty_short_sword", 2)
	print("carry_limits: gnome wizard after an hour's loot: %.1f of %d, speed x%.2f" % [p.carried_weight(), int(p.carry_capacity()), p.encumbrance_speed()])
	p.race = saved[0]; p.char_class = saved[1]; p.level = saved[2]; p.stat_points = saved[3]; p.equipment = saved[4]
	p.recalc_stats()


## One strike at a time (a shared timer for melee strikes, another for special
## shots), and a stun can't be followed by another until the immunity runs out.
func _t_strike_timer() -> void:
	var p := World.local_player
	var saved := [p.char_class, p.level, p.spells.duplicate()]
	p.char_class = "warrior"
	p.level = 50
	p.spells = ["kick", "heroic_strike", "eclipse_strike", "worldbreaker", "shield_slam"]
	p.recalc_stats()
	var mob := _nearest_mob(p, "gnoll_scout")
	mob.max_hp = 1000000
	mob.hp = mob.max_hp
	mob.set_physics_process(false)
	p.global_position = mob.global_position + Vector3(1.5, 0.5, 0)
	p.face_toward(mob.global_position)
	World.request_set_target(p.entity_id, mob.entity_id)
	p.cooldowns.clear()
	var hp0 := mob.hp
	World.request_cast(p.entity_id, "eclipse_strike")
	await _wait(0.2)
	var after_one := hp0 - mob.hp
	World.request_cast(p.entity_id, "worldbreaker")
	World.request_cast(p.entity_id, "heroic_strike")
	await _wait(0.2)
	print("strike_timer: first strike %d damage; two more straight after -> %d more (the shared timer: %.1f s left)" % [after_one, hp0 - mob.hp - after_one, float(p.cooldowns.get("group:strike", 0.0))])
	await _wait(float(World.cfg("strike_cooldown", 4.0)) + 0.2)
	var hp1 := mob.hp
	World.request_cast(p.entity_id, "worldbreaker")
	await _wait(0.2)
	print("strike_timer: after the timer, Worldbreaker lands -> %s" % (mob.hp < hp1))
	# stuns: one takes, the next inside the immunity doesn't (the rogue's Blind, landed straight)
	mob.stun_left = 0.0
	mob.stun_immune_left = 0.0
	World._finish_spell(p, "blind", mob, true)
	var first := mob.stun_left
	mob.stun_left = 0.0  # it wore off; the immunity hasn't
	World._finish_spell(p, "blind", mob, true)
	print("strike_timer: Blind stuns for %.1f s; a second one straight after -> stunned %.1f s (immune %.1f s more)" % [first, mob.stun_left, mob.stun_immune_left])
	mob.stun_immune_left = 0.0
	mob.set_physics_process(true)
	p.char_class = saved[0]; p.level = saved[1]; p.spells = saved[2]
	p.recalc_stats()


## Timers run at real speed: a skill's recast and the camp countdown, sampled against the clock.
func _t_timer_speed() -> void:
	var p := World.local_player
	p.spells.append("kick")
	p.cooldowns.clear()
	var mob := _nearest_mob(p, "gnoll_pup")
	p.global_position = mob.global_position + Vector3(1.5, 0.5, 0)
	World.request_set_target(p.entity_id, mob.entity_id)
	World.request_cast(p.entity_id, "kick")
	var t0 := Time.get_ticks_msec()
	var cd0 := float(p.cooldowns.get("kick", -1.0))
	var g0 := float(p.cooldowns.get("group:strike", -1.0))
	await get_tree().create_timer(3.0, true, false, true).timeout
	var real := (Time.get_ticks_msec() - t0) / 1000.0
	print("timer_speed: kick recast %.2f -> %.2f and strike timer %.2f -> %.2f over %.2f real seconds (time scale %.2f)" % [cd0, float(p.cooldowns.get("kick", 0.0)), g0, float(p.cooldowns.get("group:strike", 0.0)), real, Engine.time_scale])
	World.request_sit(p.entity_id, true)
	World.request_camp(p.entity_id)
	var c0 := p.camp_left
	t0 = Time.get_ticks_msec()
	await get_tree().create_timer(3.0, true, false, true).timeout
	real = (Time.get_ticks_msec() - t0) / 1000.0
	print("timer_speed: camp %.2f -> %.2f over %.2f real seconds" % [c0, p.camp_left, real])
	World.request_sit(p.entity_id, false)


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
	var bars := p.hotbar.duplicate()
	p.hotbar = Player.default_hotbar(p.spells)
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
	print("hotbar: slots shown %d; usable %s; ranged sweep %.2f" % [hud._spell_slots.filter(func(x: HotSlot) -> bool: return x.get_meta("spell", "-") != "-").size(),
			hud._spell_slots.slice(0, 8).map(func(x: HotSlot) -> String: return "%s=%s%s" % [x.get_meta("spell", "-"), "on" if x.usable else "dim", " (%.1fs)" % x.seconds if x.sweep > 0.0 else ""]), hud._ranged_slot.sweep])
	await _shot("9n_hotbar")
	p.hotbar = bars
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


## Thornwood's Bloodtusk and watchtower quests: Harlan's tusks (repeatable,
## a bracer the first time) and Grolthar's necklace (his blade), Elowen's
## signet (the Watch's pendant); the drops that feed them.
func _t_vale_quests() -> void:
	var p := World.local_player
	var harlan: Npc = _npcs()["vale_patrol"]
	var elowen: Npc = _npcs()["elowen"]
	print("vale_quests: Grolthar drops %s, Veyl drops %s" % [GameData.mobs["grolthar"]["loot"], GameData.mobs["captain_veyl"]["loot"]])
	_stand_by(p, harlan)
	for word in ["hail", "crossroads", "bloodtusk", "tusks", "grolthar"]:
		World.request_say(p.entity_id, word)
	print("vale_quests: Harlan's quests taken %s" % [["bloodtusk_tusks", "grolthars_necklace"].map(func(q: String) -> bool: return p.quests.get(q, {}).get("active", false))])
	for round in 2:
		p.pack.add("orc_tusk", 4)
		_stand_by(p, harlan)
		await _hand_in(p, harlan, ["orc_tusk"])
		print("vale_quests: tusks round %d -> tusks left %d, bracers %d, still active %s" % [round + 1, p.pack.count("orc_tusk"), p.pack.count("vale_patrol_bracer"), p.quests["bloodtusk_tusks"].get("active", false)])
	p.pack.add("grolthars_tusk_necklace", 1)
	_stand_by(p, harlan)
	await _hand_in(p, harlan, ["grolthars_tusk_necklace"])
	print("vale_quests: necklace -> blade %d, quest done %s" % [p.pack.count("harlans_watch_blade"), not p.quests["grolthars_necklace"].get("active", true)])
	_stand_by(p, elowen)
	for word in ["watchtower", "signet"]:
		World.request_say(p.entity_id, word)
	p.pack.add("hollow_watch_signet", 1)
	await _hand_in(p, elowen, ["hollow_watch_signet"])
	print("vale_quests: signet -> pendant %d, signet kept %d, quest done %s" % [p.pack.count("hollow_watch_pendant"), p.pack.count("hollow_watch_signet"), not p.quests["the_hollow_watch"].get("active", true)])
	var here := World.zone_of(p).zone_id
	for q: String in ["bloodtusk_tusks", "grolthars_necklace", "the_hollow_watch"]:
		print("vale_quests: hint " + QuestHints.giver_hint(q, here, p.global_position))
		for item_id: String in GameData.quests[q]["wants"]:
			print("vale_quests: hint " + " / ".join(QuestHints.item_hint(q, item_id, here, p.global_position)))
	await _shot("9zz_vale_quests")


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
	var bridge: Dictionary = main.zone.data["landmarks"].filter(func(l: Dictionary) -> bool: return l["type"] == "bridge")[0]
	var b := Vector2(bridge["pos"][0], bridge["pos"][1])
	var dir := (Vector2(bridge["face"][0], bridge["face"][1]) - b).normalized()  # along the road, north over the river
	var start := b - dir * 24.0
	p.global_position = main.zone.ground(start.x, start.y) + Vector3.UP
	var lowest := INF
	for k in 360:
		p.velocity = Vector3(dir.x, 0, dir.y) * 6.0 + Vector3(0, p.velocity.y - 20.0 * get_physics_process_delta_time(), 0)
		p.move_and_slide()
		await get_tree().physics_frame
		if Vector2(p.global_position.x, p.global_position.z).distance_to(b) < 8.0:
			lowest = minf(lowest, p.global_position.y)
	var level: float = main.zone._river_at(main.zone._rivers[0], b.x, b.y)[1]
	print("river: over the bridge from z %.0f to %.0f; lowest on the crossing %.2f, water level %.2f" % [start.y, p.global_position.z, lowest, level])
	p.global_position = main.zone.ground(b.x - 33.0, b.y + 24.0) + Vector3.UP
	var deepest := INF
	for k in 360:
		p.velocity = Vector3(0, p.velocity.y - 20.0 * get_physics_process_delta_time(), -6.0)
		p.move_and_slide()
		await get_tree().physics_frame
		deepest = minf(deepest, p.global_position.y)
	print("river: waded across at x %.0f to z %.0f; deepest %.2f (%.2f under the water)" % [b.x - 33.0, p.global_position.z, deepest, level - deepest])
	for view: Array in [[b + Vector2(-21.5, 22), b, "bridge"], [b + Vector2(-63.5, 19), b + Vector2(-103.5, -6), "banks"]]:
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
	print("groupchat: grouped -> window shown %s; it holds %d lines: %s" % [hud._group_log_panel.visible, int(hud._social_lines["all"]), (hud._social_logs["all"] as RichTextLabel).get_parsed_text().replace("\n", " | ")])
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
	var bridge: Array = main.zone.data["landmarks"].filter(func(l: Dictionary) -> bool: return l["type"] == "bridge")[0]["pos"]
	var b := Vector2(bridge[0], bridge[1])
	var lowest_on_bridge := INF
	var start := harlan.global_position.z
	var reached := 0.0
	for k in 400:  # down the road and over the bridge
		await _wait(0.5)
		var at := harlan.global_position
		reached = minf(reached, at.z) if reached != 0.0 else at.z
		if Vector2(at.x, at.z).distance_to(b) < 6.0:
			lowest_on_bridge = minf(lowest_on_bridge, at.y)
		if at.z < b.y - 20.0:
			break
	var level: float = main.zone._river_at(main.zone._rivers[0], b.x, b.y)[1]
	print("vale_patrol: Harlan (level %d) walked from z %.0f to z %.0f; on the bridge his lowest was %.2f (water %.2f)" % [harlan.level, start, reached, lowest_on_bridge, level])
	for k in 60:  # off the bridge (its railings would keep him from a wolf in the river)
		if harlan.global_position.z < b.y - 18.0:
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
	if zone_id == "wellspring" and not World.quest_started(p, "merricks_line_spring"):  # Watchman Corran lets nobody in before Merrick's step 2
		p.quests["merricks_line_sinew"] = {"active": false, "completions": 1}
		p.quests["merricks_line_spring"] = {"active": true, "completions": 0}
	if p.dead:
		await _wait(5.0)
	# step into the zone line that starts the shortest way there
	for hop in 12:
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
	for leg: Array in [["thornwood", Vector2(225, -20), Vector2(1, 0), "hollowmere"], ["hollowmere", Vector2(-193, -20), Vector2(-1, 0), "thornwood"]]:
		if not await _walk_border("hollowmere_border", leg[0], leg[1], leg[2], leg[3]):
			return


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
	for leg: Array in [["greenmoor", Vector2(170, 0), Vector2(1, 0), "harrowfield"], ["harrowfield", Vector2(0, -170), Vector2(0, -1), "hollowmere"],
			["hollowmere", Vector2(0, 202), Vector2(0, 1), "harrowfield"], ["harrowfield", Vector2(-170, 0), Vector2(-1, 0), "greenmoor"]]:
		if not await _walk_border("harrowfield_border", leg[0], leg[1], leg[2], leg[3]):
			return


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


## A mob pathing around a fence to reach you walks forward along its path
## (facing within 45 degrees of where it steps), then faces you in reach.
func _t_face_path() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	for k in 80:
		if z.nav_ready:
			break
		await _wait(0.25)
	p.level = 30
	p.recalc_stats()
	var boar: Mob = _nearest_mob(p, "wild_boar")
	for m in World.get_mobs():
		m.hate.clear()
	p.global_position = z.ground(85, -30) + Vector3.UP  # inside the east field; the boar starts outside its south fence
	boar.global_position = z.ground(88, 2) + Vector3.UP
	boar.home = boar.global_position
	boar.state = Mob.State.IDLE
	await _wait(0.3)
	boar.add_hate(p, 50.0)
	var moving := 0
	var off := 0
	var worst := 0.0
	var reached := false
	for k in 1800:  # the way round the field takes about 14 s
		await get_tree().physics_frame
		if not is_instance_valid(boar):
			break
		var v := Vector2(boar.velocity.x, boar.velocity.z)
		if v.length() > 0.5:
			var facing := -boar.global_basis.z
			var angle := rad_to_deg(absf(Vector2(facing.x, facing.z).angle_to(v)))
			moving += 1
			worst = maxf(worst, angle)
			if angle > 45.0:
				off += 1
		if boar.distance_to(p) <= World.melee_range() + 0.5:
			reached = true
			break
	await _wait(0.5)
	var to_you := (p.global_position - boar.global_position) * Vector3(1, 0, 1)
	var facing := -boar.global_basis.z
	print("face_path: reached %s; moving %d frames, %d facing more than 45 deg off its step (worst %.0f deg) -> %s; in reach it faces you within %.0f deg" % [
			reached, moving, off, worst, "PASS" if off <= moving / 20 else "FAIL", rad_to_deg(absf(Vector2(facing.x, facing.z).angle_to(Vector2(to_you.x, to_you.z))))])
	boar.hate.clear()
	boar.state = Mob.State.RETURN


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


## Merrick's line: grumbling at a tavern table (seated), hail and "sinew" take
## step 1, five rat sinews finish it: he jolts up (Sit_Chair_Shock), tells the
## story a line at a time and sits up eager for this player, and step 2 (the
## sour spring) starts once he's done talking. He stays in the tavern until
## step 2 is done; the pond is fouled.
func _t_merricks_line() -> void:
	var p := World.local_player
	for q in ["merricks_line_sinew", "merricks_line_spring", "merricks_line_word", "merricks_line_pond"]:
		p.quests.erase(q)
	await _wait(0.7)
	var merrick: Npc = _npcs().get("merrick_tavern")
	if merrick == null:
		print("merricks_line: FAIL no Merrick in %s" % get_parent().zone.zone_id)
		return
	var model := merrick.visual as CharacterModel
	var rat_drops: Array = GameData.mobs["large_rat"]["loot"].map(func(l: Dictionary) -> String: return "%s %s" % [l["item"], l["chance"]])
	print("merricks_line: large rat drops %s; sinew icon %s" % [rat_drops, GameData.item_icon("rat_sinew") != null])
	print("merricks_line: tavern Merrick seen=%s sitting=%s shown=%s; pond Merrick seen=%s" % [World.sees(p, merrick), merrick.sitting,
			merrick.visual.visible, World.quest_shows(p, GameData.npcs["merrick"])])
	World.request_set_target(p.entity_id, merrick.entity_id)
	p.global_position = merrick.global_position + Vector3(2.4, 0.5, -3.4)  # across the table from him, a little to the side
	p.face_toward(merrick.global_position)
	p.camera_pivot.rotation.y = 0.0
	p.zoom = 0.0  # first person, so you aren't in the way
	p.pitch = -0.25
	World.request_say(p.entity_id, "spring")
	print("merricks_line: 'spring' before the sinew -> step 2 %s" % p.quests.get("merricks_line_spring", {}))
	World.request_hail(p.entity_id)
	World.request_say(p.entity_id, "sinew")
	await _wait(1.0)
	print("merricks_line: seated clip %s; after 'sinew' active=%s" % [model.anim.current_animation, p.quests.get("merricks_line_sinew", {}).get("active", false)])
	await _shot("9zz_merrick_seated")
	p.pack.add("rat_sinew", 5)
	await _hand_in(p, merrick, ["rat_sinew"])
	await _wait(0.35)
	print("merricks_line: hand-in -> clip %s" % model.anim.current_animation)
	await _shot("9zz_merrick_shock")
	await _wait(0.6)
	await _shot("9zz_merrick_pump")
	await _wait(2.5)
	print("merricks_line: after the shock -> clip %s; step 1 %s; tavern Merrick seen=%s; pond Merrick seen=%s" % [model.anim.current_animation,
			p.quests.get("merricks_line_sinew", {}), World.sees(p, merrick), World.quest_shows(p, GameData.npcs["merrick"])])
	await _shot("9zz_merrick_eager")
	for k in 40:
		if p.quests.get("merricks_line_spring", {}).get("active", false):
			break
		await _wait(1.0)
	print("merricks_line: story told -> step 2 %s" % p.quests.get("merricks_line_spring", {}))
	World.request_hail(p.entity_id)
	await _wait(0.5)
	p.zoom = 6.0
	await _shot("9zz_merrick_story")
	await _ensure_zone("greenmoor")
	p.global_position = get_parent().zone.ground(-114, 157) + Vector3.UP
	p.face_toward(get_parent().zone.ground(-125, 145))
	p.camera_pivot.rotation.y = 0.0
	p.zoom = 7.0
	p.pitch = -0.35
	World.time_override = 13.0
	await _wait(1.5)
	await _shot("9zz_pond_fouled")
	World.time_override = -1.0


## The Wellspring, the cave under Greenmoor (Merrick's line): its passages,
## the fouled creek, and the spring cavern with the cocooned crystal, seen at
## points along the way; and that you can walk the main way from end to end.
func _t_wellspring() -> void:
	var main := get_parent()
	var p := World.local_player
	p.level = 50  # a gray-con visitor: the cave leaves you be while it's looked over
	p.recalc_stats()
	p.hp = p.max_hp
	var z: Zone = main.zone
	if z.tunnel == null:
		print("wellspring: FAIL no tunnel in %s" % z.zone_id)
		return
	var bp: Vector3 = z.bind_point
	print("wellspring: respawn point %s: in the passage %s, %.1f m over the floor, roof %.1f m above it" % [bp, z.tunnel.inside(bp.x, bp.z, 1.0), bp.y - z.tunnel.sample(bp.x, bp.z).y, z.tunnel.ceiling_at(bp.x, bp.z, 0.0) - bp.y])
	World.time_override = 12.0
	var views := [["entrance", Vector2(126, 127), Vector2(100, 121)], ["narrows", Vector2(20, 80), Vector2(2, 62)],
			["chamber", Vector2(-96, 14), Vector2(-104, -4)], ["creek", Vector2(-40, -30), Vector2(-62, -40)],
			["deadend", Vector2(-60, 104), Vector2(-74, 112)], ["cavern", Vector2(68, -114), Vector2(46, -130)]]
	for v: Array in views:
		p.global_position = z.ground(v[1].x, v[1].y) + Vector3.UP
		p.face_toward(z.ground(v[2].x, v[2].y))
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 5.0
		p.pitch = -0.15
		await _wait(0.8)
		var s := z.tunnel.sample(v[1].x, v[1].y)
		print("wellspring: %s floor %.1f clear %.1f roof %.1f above" % [v[0], s.y, s.x, z.tunnel.ceiling_at(v[1].x, v[1].y, 0.0) - z.height_at(v[1].x, v[1].y)])
		await _shot("9zw_%s" % v[0])
	# is the main way through one piece? ask the navigation mesh for a path end to end
	var map := z.get_world_3d().navigation_map
	for k in 40:
		if NavigationServer3D.map_get_iteration_id(map) > 0:
			break
		await _wait(0.5)
	var route := NavigationServer3D.map_get_path(map, z.ground(128, 127), z.ground(62, -118), true)
	var got := route[route.size() - 1] if route.size() > 0 else Vector3.INF
	var walked := 0.0
	for i in route.size() - 1:
		walked += route[i].distance_to(route[i + 1])
	print("wellspring: path entrance -> cavern: %d points, %.0f m, ends %.1f m from the cavern" % [route.size(), walked, got.distance_to(z.ground(62, -118))])
	# the chests at the ends of the side passages
	var chests: Array = z.get_children().filter(func(n: Node) -> bool: return n is Corpse and (n as Corpse).owner_name == "")
	for ch: Corpse in chests:
		print("wellspring: %s at %s: %d coin, %s" % [ch.display_name, Vector2(ch.global_position.x, ch.global_position.z), ch.coin,
				ch.entries.map(func(e: Dictionary) -> String: return "%s x%d" % [e["item"], int(e.get("count", 1))])])
	if not chests.is_empty():
		var ch: Corpse = chests[0]
		p.level = 50  # a gray-con visitor: the monsters by the chest leave you be
		p.recalc_stats()
		p.hp = p.max_hp
		p.global_position = ch.global_position + Vector3(2.5, 0.5, 2.5)
		p.face_toward(ch.global_position)
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 4.0
		await _wait(0.6)
		await _shot("9zw_chest")
		var coin := p.coin
		print("wellspring: opening %s: %.1f m away, coin %d, dead %s" % [ch.display_name, p.distance_to(ch), ch.coin, p.dead])
		var pos := ch.global_position
		World.request_loot_open(p.entity_id, ch.object_id)
		await _wait(0.2)
		var opened: Corpse = null
		for n: Node in z.get_children():
			if n is Corpse and (n as Corpse).global_position.distance_to(pos) < 0.5 and not (n as Corpse).is_queued_for_deletion():
				opened = n
		p.global_position = opened.global_position + Vector3(1.5, 0.5, 0)  # right at it (a monster may have shoved you off)
		World.request_loot_all(p.entity_id, opened.object_id)
		await _wait(0.3)
		print("wellspring: looted it: +%d coin; the chest still there %s, open %s, holding %d" % [p.coin - coin, is_instance_valid(opened), opened.look.get("open", false), opened.entries.size()])
		World.request_loot_close(p.entity_id)
		p.global_position = opened.global_position + opened.global_transform.basis.z * -2.6 + Vector3.UP * 0.5
		p.face_toward(opened.global_position)
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 0.0
		p.pitch = -0.45
		await _wait(0.4)
		await _shot("9zw_chest_open")
		p.zoom = 6.0
	World.time_override = -1.0


## Merrick's line, steps 2 to 4, played through: the Wellspring's monsters are
## all there; a web stops you until it's torn down (no corpse, no XP); the
## Blightmother brings her own music and drops her heart and venom sac; the
## heart frees the crystal (a vial for you, the cave's water clean for you);
## the venom sac sends Merrick walking out of the tavern; the vial poured into
## Greenmoor's pond clears it.
func _t_wellspring_quest() -> void:
	var main := get_parent()
	var p := World.local_player
	p.level = 50  # the cave's monsters leave a gray-con player be, so the test isn't a fight
	p.recalc_stats()
	p.hp = p.max_hp
	for q in ["merricks_line_spring", "merricks_line_word", "merricks_line_pond"]:
		p.quests.erase(q)
	p.quests["merricks_line_sinew"] = {"active": false, "completions": 1}
	p.quests["merricks_line_spring"] = {"active": true, "completions": 0}
	World.time_override = 12.0
	await _wait(1.0)
	var counts := {}
	for m in World.get_mobs():
		counts[m.mob_id] = int(counts.get(m.mob_id, 0)) + 1
	print("wellspring_quest: monsters %s" % counts)
	# a web across the passage
	var web := _nearest_mob(p, "thick_web")
	if web != null:
		var ahead := -web.global_transform.basis.z  # it faces down the passage
		p.global_position = web.global_position + ahead * 3.0 + Vector3.UP * 0.5
		p.face_toward(web.global_position)
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 5.0
		await _wait(0.5)
		await _shot("9zx_web")
		var start := p.global_position
		for k in 90:
			p.velocity = -ahead * 4.0
			p.move_and_slide()
			await get_tree().physics_frame
		print("wellspring_quest: walked at the web: %.1f m of 6 (blocked if under 3)" % start.distance_to(p.global_position))
		var xp := p.xp
		World.damage(web, 9999, p)
		await _wait(0.3)
		var corpses: int = main.zone.get_children().filter(func(c: Node) -> bool: return c is Corpse and (c as Corpse).global_position.distance_to(start) < 6.0).size()
		start = p.global_position
		for k in 90:
			p.velocity = -ahead * 4.0
			p.move_and_slide()
			await get_tree().physics_frame
		print("wellspring_quest: web torn: xp +%d, corpses %d, then walked %.1f m" % [p.xp - xp, corpses, start.distance_to(p.global_position)])
	# the Blightmother
	var boss := _nearest_mob(p, "blightmother")
	if boss == null:
		print("wellspring_quest: FAIL no Blightmother")
		World.time_override = -1.0
		return
	p.global_position = boss.global_position + Vector3(14, 0.5, -4)
	p.face_toward(boss.global_position)
	p.camera_pivot.rotation.y = 0.0
	p.zoom = 7.0
	p.pitch = -0.2
	await _wait(0.6)
	print("wellspring_quest: Blightmother level %d, %d hp, scale %.1f; fight music would be '%s'" % [boss.level, boss.max_hp, boss.body_scale, Music._boss_track(p)])
	await _shot("9zx_blightmother")
	var fell := boss.global_position
	World.damage(boss, 9999, p)
	await _wait(0.5)
	for c: Node in main.zone.get_children():
		if c is Corpse and (c as Corpse).global_position.distance_to(fell) < 2.0:
			p.global_position = fell + Vector3(1.5, 0.5, 0)
			World.request_loot_all(p.entity_id, (c as Corpse).object_id)
	await _wait(0.3)
	print("wellspring_quest: looted heart %d, venom sac %d" % [p.pack.count("blight_heart"), p.pack.count("blightmothers_venom_sac")])
	# the crystal
	var crystal: Npc = _npcs().get("spring_crystal")
	_stand_by(p, crystal)
	p.global_position = crystal.global_position + Vector3(7.2, 0.5, 5.4)  # on the bank, in reach
	p.global_position.y = main.zone.ground(p.global_position.x, p.global_position.z).y + 0.5
	p.face_toward(crystal.global_position)
	p.zoom = 7.0
	await _wait(0.6)
	print("wellspring_quest: crystal before: %s" % crystal.look.get("shape"))
	await _shot("9zx_crystal_cocooned")
	await _hand_in(p, crystal, ["blight_heart"])
	await _wait(1.6)
	var clean: bool = main.zone._foul.all(func(f: Dictionary) -> bool: return f["clean"])
	print("wellspring_quest: crystal after: %s; vial %d; cave water clean %s; step 2 %s" % [crystal.look.get("shape"), p.pack.count("vial_of_spring_water"), clean, p.quests.get("merricks_line_spring")])
	await _shot("9zx_crystal_freed")
	for k in 30:
		if p.quests.has("merricks_line_word"):
			break
		await _wait(1.0)
	print("wellspring_quest: step 3 %s" % p.quests.get("merricks_line_word"))
	# Merrick, in the tavern
	await _ensure_zone("emberhold_tavern")
	await _wait(1.0)
	var merrick: Npc = _npcs().get("merrick_tavern")
	p.global_position = merrick.global_position + Vector3(2.4, 0.5, -3.4)
	p.face_toward(merrick.global_position)
	p.camera_pivot.rotation.y = 0.0
	p.zoom = 0.0
	World.request_set_target(p.entity_id, merrick.entity_id)
	await _hand_in(p, merrick, ["blightmothers_venom_sac"])
	for k in 40:
		if p.quests.has("merricks_line_pond"):
			break
		await _wait(1.0)
	await _wait(1.2)
	var walker: Npc = _npcs().get("merrick_walker")
	print("wellspring_quest: step 4 %s; seated Merrick seen %s; walker %s" % [p.quests.get("merricks_line_pond"), World.sees(p, merrick), walker != null])
	p.zoom = 6.0
	await _shot("9zx_merrick_leaves")
	for k in 20:
		if not is_instance_valid(walker) or walker == null:
			break
		await _wait(0.5)
	print("wellspring_quest: walker gone %s" % (walker == null or not is_instance_valid(walker)))
	# the pond
	await _ensure_zone("greenmoor")
	print("wellspring_quest: the moment you're back in Greenmoor, the pond is clean: %s" % main.zone._foul.all(func(f: Dictionary) -> bool: return f["clean"]))
	await _wait(1.0)
	var pond_merrick: Npc = _npcs().get("merrick")
	print("wellspring_quest: pond Merrick seen %s" % World.sees(p, pond_merrick))
	_stand_by(p, pond_merrick)
	await _hand_in(p, pond_merrick, ["vial_of_spring_water"])
	await _wait(1.6)
	var pond_clean: bool = main.zone._foul.all(func(f: Dictionary) -> bool: return f["clean"])
	print("wellspring_quest: step 4 %s; pond clean %s" % [p.quests.get("merricks_line_pond"), pond_clean])
	print("wellspring_quest: hailing pond Merrick after the quest:")
	World.request_hail(p.entity_id)
	p.global_position = main.zone.ground(-114, 157) + Vector3.UP
	p.face_toward(main.zone.ground(-125, 145))
	p.camera_pivot.rotation.y = 0.0
	p.zoom = 7.0
	p.pitch = -0.35
	await _wait(1.0)
	await _shot("9zx_pond_clean")
	World.time_override = -1.0


## Naevys's line in Duskhold, played through as a dark elf cleric: four of the
## city's crystals are dark and she turns you back from the crack in the southwest
## wall; five moth wings start her talking and she comes down the Gloamvein
## with you; the Lamp-Glutton drops the stolen light and the lantern; the light
## wakes the Heartcrystal (a shard for you, and the cave's and the city's
## crystals lit for you); the lantern sends her walking off to the shrine
## island, where the shard earns the weapon for your class.
func _t_dimming_line() -> void:
	var main := get_parent()
	var p := World.local_player
	var steps := ["dimming_line_wings", "dimming_line_deep", "dimming_line_lantern", "dimming_line_shard"]
	var keep := [p.race, p.char_class, p.level, p.factions.duplicate(), p.alignment_mods.duplicate(), p.deity]
	p.race = "dark_elf"  # Duskhold's guards attack a human on sight
	p.deity = "dark"  # a god who takes dark elves, or the "Choose a new god" window covers every picture
	p.char_class = "cleric"
	p.level = 50  # gray to everything on the way and in the cave, so the test isn't a fight
	p.factions = {}
	p.alignment_mods = {}
	World.apply_alignment(p)
	p.recalc_stats()
	p.hp = p.max_hp
	for q: String in steps:
		p.quests.erase(q)
	World.time_override = 12.0
	await _ensure_zone("duskhold")
	if main.zone.zone_id != "duskhold":
		print("dimming_line: FAIL never reached Duskhold (in %s)" % main.zone.zone_id)
		World.time_override = -1.0
		return
	await _wait(1.0)
	var lamps := func() -> Array:
		var out := []
		for obj: Node3D in World.objects.values():
			if obj is Npc and (obj as Npc).npc_id == "dusk_dim_crystal" and World.zone_of(obj) == main.zone:
				out.append(str((obj as Npc).look.get("shape")).trim_prefix("prop:"))
		return out
	var naevys: Npc = _npcs().get("dusk_naevys")
	if naevys == null:
		print("dimming_line: FAIL no Naevys in Duskhold")
		World.time_override = -1.0
		return
	print("dimming_line: Naevys at her post seen=%s; on the island seen=%s; crystals %s" % [World.sees(p, naevys), World.quest_shows(p, GameData.npcs["dusk_naevys_shrine"]), lamps.call()])
	p.global_position = main.zone.ground(-50, 44) + Vector3.UP
	p.face_toward(main.zone.ground(-68, 58))
	p.camera_pivot.rotation.y = 0.0
	p.zoom = 9.0
	p.pitch = -0.25
	await _wait(0.8)
	await _shot("9zw_crack_and_naevys")
	p.global_position = main.zone.ground(-52, 14) + Vector3.UP
	p.face_toward(main.zone.ground(-36, 0))
	await _wait(0.6)
	await _shot("9zw_crystals_dark")
	# turned back at the crack
	var line := -1
	for i in (main.zone.data["zone_lines"] as Array).size():
		if str(main.zone.data["zone_lines"][i]["to"]) == "gloamvein":
			line = i
	var zl: Dictionary = main.zone.data["zone_lines"][line]
	p.global_position = main.zone.ground(float(zl["pos"][0]), float(zl["pos"][1])) + Vector3.UP * 0.3
	World.request_zone_line(p.entity_id, line)
	await _wait(1.0)
	print("dimming_line: before the quest -> still in %s, put back at %s" % [main.zone.zone_id, Vector2(p.global_position.x, p.global_position.z)])
	# step 1: the wings
	_stand_by(p, naevys)
	World.request_say(p.entity_id, "vein")
	print("dimming_line: 'vein' before the wings -> step 2 %s" % p.quests.get("dimming_line_deep", {}))
	World.request_hail(p.entity_id)
	for word: String in ["crystals", "moths", "wings"]:
		World.request_say(p.entity_id, word)
	await _wait(0.5)
	print("dimming_line: after 'wings' -> step 1 %s; gloomwing moths drop %s" % [p.quests.get("dimming_line_wings", {}), GameData.mobs["gloomwing_moth"]["loot"]])
	p.pack.add("moth_wing", 5)
	await _hand_in(p, naevys, ["moth_wing"])
	for k in 60:
		if p.quests.get("dimming_line_deep", {}).get("active", false):
			break
		await _wait(1.0)
	print("dimming_line: story told -> step 1 %s; step 2 %s" % [p.quests.get("dimming_line_wings", {}), p.quests.get("dimming_line_deep", {})])
	# down the Gloamvein with her: on foot, from where she turned you back, so the crack is somewhere you can walk to
	var mouth: Vector3 = main.zone.ground(-68, 58)
	var door: Vector3 = main.zone.ground(float(zl["pos"][0]), float(zl["pos"][1]))
	p.global_position = main.zone.ground(float(zl["refused_to"][0]), float(zl["refused_to"][1])) + Vector3.UP * 0.3
	print("dimming_line: ground at the cave mouth %.2f, 10 m in front %.2f, at its zone line %.2f; the mountains start %.1f m behind the line" % [mouth.y, p.global_position.y - 0.3, door.y, -main.zone.edge_depth(door.x, door.z)])
	var paces := 0
	while paces < 600 and main.zone.zone_id == "duskhold" and main.zone.zone_line_at(p.global_position) != line:
		var to := Vector3(door.x - p.global_position.x, 0, door.z - p.global_position.z)
		p.velocity = to.normalized() * 5.0 + Vector3.DOWN * 4.0
		p.move_and_slide()
		paces += 1
		await get_tree().physics_frame
	print("dimming_line: walked to the crack in %d steps: on its zone line %s" % [paces, main.zone.zone_id != "duskhold" or main.zone.zone_line_at(p.global_position) == line])
	if main.zone.zone_id == "duskhold":
		World.request_zone_line(p.entity_id, line)
	for k in 40:
		await _wait(0.5)
		if main.zone != null and main.zone.zone_id == "gloamvein" and World.get_object(p.companion_id) != null:
			break
	if main.zone.zone_id != "gloamvein" or main.zone.tunnel == null:
		print("dimming_line: FAIL not in the Gloamvein (in %s)" % main.zone.zone_id)
		World.time_override = -1.0
		return
	var escort := World.get_object(p.companion_id) as Npc
	print("dimming_line: in the Gloamvein at %s (in the passage %s); companion %s level %s" % [p.global_position, main.zone.tunnel.inside(p.global_position.x, p.global_position.z, 1.0),
			escort.display_name if escort != null else "none", escort.level if escort != null else 0])
	var counts := {}
	for m in World.get_mobs():
		counts[m.mob_id] = int(counts.get(m.mob_id, 0)) + 1
	print("dimming_line: monsters %s; crystals %s" % [counts, lamps.call()])
	for spawn: Dictionary in main.zone.data["spawns"]:  # every monster, chest and crystal stands in a passage, not in the rock
		if not main.zone.tunnel.inside(float(spawn["pos"][0]), float(spawn["pos"][1]), 0.5):
			print("dimming_line: FAIL spawn %s at %s is in the rock" % [spawn["pool"].keys(), spawn["pos"]])
	for spot: Dictionary in (main.zone.data["npcs"] as Array) + (main.zone.data["chests"] as Array):
		if not main.zone.tunnel.inside(float(spot["pos"][0]), float(spot["pos"][1]), 0.5):
			print("dimming_line: FAIL %s at %s is in the rock" % [spot.get("id", spot.get("name")), spot["pos"]])
	for k in 60:  # the cave's navigation is baked on another thread
		if main.zone.nav_ready:
			break
		await _wait(0.5)
	await _wait(0.5)
	var route := NavigationServer3D.map_get_path(main.zone.get_world_3d().navigation_map, main.zone.ground(128, 20), main.zone.ground(-66, 116), true)
	var walked := 0.0
	for i in range(1, route.size()):
		walked += route[i - 1].distance_to(route[i])
	print("dimming_line: path entrance -> the Heartcrystal's chamber: %d points, %.0f m, ends %.1f m from it" % [route.size(), walked,
			route[route.size() - 1].distance_to(main.zone.ground(-66, 116)) if not route.is_empty() else -1.0])
	p.face_toward(main.zone.ground(100, 30))
	p.camera_pivot.rotation.y = 0.0
	p.zoom = 6.0
	p.pitch = -0.15
	await _wait(0.8)
	await _shot("9zw_gloamvein_entrance")
	# the Lamp-Glutton
	var boss := _nearest_mob(p, "lamp_glutton")
	if boss == null:
		print("dimming_line: FAIL no Lamp-Glutton")
		World.time_override = -1.0
		return
	p.global_position = main.zone.ground(-64, 116) + Vector3.UP * 0.5
	p.face_toward(boss.global_position)
	p.zoom = 7.0
	p.pitch = -0.2
	await _wait(0.8)
	print("dimming_line: the Lamp-Glutton level %d, %d hp, scale %.1f; fight music would be '%s'" % [boss.level, boss.max_hp, boss.body_scale, Music._boss_track(p)])
	await _shot("9zw_lamp_glutton")
	var fell := boss.global_position
	World.damage(boss, 99999, p)
	await _wait(0.5)
	for c: Node in main.zone.get_children():
		if c is Corpse and (c as Corpse).global_position.distance_to(fell) < 2.0:
			p.global_position = fell + Vector3(1.5, 0.5, 0)
			World.request_loot_all(p.entity_id, (c as Corpse).object_id)
	await _wait(0.3)
	print("dimming_line: looted stolen light %d, lantern %d" % [p.pack.count("stolen_light"), p.pack.count("painted_lantern")])
	# the Heartcrystal
	var heart: Npc = _npcs().get("heartcrystal")
	p.global_position = main.zone.ground(heart.global_position.x + 6.0, heart.global_position.z - 5.0) + Vector3.UP * 0.5
	p.face_toward(heart.global_position)
	World.request_set_target(p.entity_id, heart.entity_id)
	await _wait(0.6)
	print("dimming_line: Heartcrystal before: %s" % heart.look.get("shape"))
	await _shot("9zw_heartcrystal_cocooned")
	await _hand_in(p, heart, ["stolen_light"])
	await _wait(1.6)
	print("dimming_line: Heartcrystal after: %s; shard %d; cave crystals %s; step 2 %s" % [heart.look.get("shape"), p.pack.count("heartcrystal_shard"), lamps.call(), p.quests.get("dimming_line_deep")])
	await _shot("9zw_heartcrystal_lit")
	for k in 30:
		if p.quests.has("dimming_line_lantern"):
			break
		await _wait(1.0)
	await _wait(1.5)
	print("dimming_line: step 3 %s; companion still here %s" % [p.quests.get("dimming_line_lantern"), World.get_object(p.companion_id) != null])
	# back up in Duskhold: the lamps are lit
	await _ensure_zone("duskhold")
	await _wait(1.5)
	print("dimming_line: back in %s at %s; crystals %s" % [main.zone.zone_id, Vector2(p.global_position.x, p.global_position.z), lamps.call()])
	p.global_position = main.zone.ground(-52, 14) + Vector3.UP
	p.face_toward(main.zone.ground(-36, 0))
	p.zoom = 9.0
	await _wait(0.8)
	await _shot("9zw_crystals_lit")
	naevys = _npcs().get("dusk_naevys")
	_stand_by(p, naevys)
	await _hand_in(p, naevys, ["painted_lantern"])
	for k in 60:
		if p.quests.has("dimming_line_shard"):
			break
		await _wait(1.0)
	await _wait(1.2)
	var walker: Npc = _npcs().get("dusk_naevys_walker")
	var shrine: Npc = _npcs().get("dusk_naevys_shrine")
	print("dimming_line: step 4 %s; Naevys at her post seen %s; walker %s; on the island seen %s" % [p.quests.get("dimming_line_shard"), World.sees(p, naevys), walker != null, World.sees(p, shrine)])
	await _shot("9zw_naevys_leaves")
	# the shrine island
	p.global_position = shrine.global_position + Vector3(-2.5, 0.5, -3.0)  # north of her, clear of the idol and the Lamp-Keeper
	p.face_toward(shrine.global_position)
	World.request_set_target(p.entity_id, shrine.entity_id)
	p.zoom = 6.0
	await _wait(0.8)
	await _shot("9zw_naevys_island")
	await _hand_in(p, shrine, ["heartcrystal_shard"])
	await _wait(2.0)
	print("dimming_line: step 4 %s; a cleric's reward: mace %d (blade %d, wand %d)" % [p.quests.get("dimming_line_shard"), p.pack.count("deepwatch_mace"), p.pack.count("deepwatch_blade"), p.pack.count("deepwatch_wand")])
	print("dimming_line: rewards by class %s" % [["warrior", "cleric", "rogue", "wizard", "magician", "necromancer"].map(func(c: String) -> String: return "%s: %s" % [c, GameData.item_name(World.quest_reward_item(GameData.quests["dimming_line_shard"], c))])])
	await _wait(30.0)  # her piece to the Lamp-Keeper
	print("dimming_line: hailing Naevys after the quest:")
	World.request_hail(p.entity_id)
	World.request_say(p.entity_id, "lantern")
	await _wait(0.5)
	p.race = keep[0]
	p.char_class = keep[1]
	p.level = keep[2]
	p.factions = keep[3]
	p.alignment_mods = keep[4]
	p.deity = keep[5]
	World.apply_alignment(p)
	p.recalc_stats()
	World.time_override = -1.0


## Watchman Corran: turns you back from the Wellspring before Merrick's step
## 2, goes in with you once it's under way (levelled to your class), follows
## a few steps behind, sits when you sit, fights only what you fight, takes
## your heals; and the cave's monsters stay dead.
func _t_corran() -> void:
	var main := get_parent()
	var p := World.local_player
	p.level = 6
	p.recalc_stats()
	p.hp = p.max_hp
	for q in ["merricks_line_sinew", "merricks_line_spring", "merricks_line_word", "merricks_line_pond"]:
		p.quests.erase(q)
	var line := -1
	for i in (main.zone.data["zone_lines"] as Array).size():
		if str(main.zone.data["zone_lines"][i]["to"]) == "wellspring":
			line = i
	var zl: Dictionary = main.zone.data["zone_lines"][line]
	p.global_position = main.zone.ground(float(zl["pos"][0]), float(zl["pos"][1])) + Vector3.UP * 0.3
	World.request_zone_line(p.entity_id, line)
	await _wait(1.0)
	print("corran: before the quest -> still in %s, put back at %s" % [main.zone.zone_id, Vector2(p.global_position.x, p.global_position.z)])
	var corran: Npc = _npcs().get("watchman_corran")
	p.face_toward(corran.global_position)
	p.camera_pivot.rotation.y = 0.0
	p.zoom = 6.0
	await _wait(0.4)
	await _shot("9zy_corran_refuses")
	p.quests["merricks_line_sinew"] = {"active": false, "completions": 1}
	p.quests["merricks_line_spring"] = {"active": true, "completions": 0}
	p.global_position = main.zone.ground(float(zl["pos"][0]), float(zl["pos"][1])) + Vector3.UP * 0.3
	World.request_zone_line(p.entity_id, line)
	for k in 30:
		await _wait(0.5)
		if main.zone != null and main.zone.zone_id == "wellspring" and World.get_object(p.companion_id) != null:
			break
	var c := World.get_object(p.companion_id) as Npc
	if c == null:
		print("corran: FAIL no companion in %s" % main.zone.zone_id)
		return
	World.request_set_target(p.entity_id, c.entity_id)
	var heals_him := World._resolve_spell_target(p, {"target": "friendly"}) == c
	World.request_set_target(p.entity_id, -1)
	print("corran: in %s with %s, level %d (a %s), %d hp, only for %s, your heals land on him: %s" % [main.zone.zone_id, c.display_name, c.level, p.char_class,
			c.max_hp, c.only_for, heals_him])
	await _wait(1.5)
	World.request_sit(p.entity_id, true)
	await _wait(1.5)
	print("corran: you sit (quiet entrance) -> he sits %s" % c.sitting)
	p.camera_pivot.rotation.y = PI
	await _shot("9zy_corran_rests")
	World.request_sit(p.entity_id, false)
	# follows, a few steps behind
	var z: Zone = main.zone
	for goal: Vector2 in [Vector2(112, 124), Vector2(100, 120)]:
		for k in 120:
			var to := Vector3(goal.x, p.global_position.y, goal.y) - p.global_position
			if Vector2(to.x, to.z).length() < 0.8:
				break
			p.velocity = to.normalized() * 5.0
			p.move_and_slide()
			await get_tree().physics_frame
	await _wait(2.5)
	print("corran: walked 30 m -> he's %.1f m behind" % c.distance_to(p))
	# a fight: nothing until you start it, then he's in
	var spider := _nearest_mob(p, "cave_spider")
	print("corran: a spider %.0f m off, minding its own business -> he's fighting: %s" % [spider.distance_to(p) if spider != null else -1.0, c.auto_attack])
	if spider != null:
		p.global_position = spider.global_position + Vector3(3, 0.5, 0)
		World.request_set_target(p.entity_id, spider.entity_id)
		if not p.auto_attack:
			World.request_toggle_attack(p.entity_id)
		await _wait(2.0)
		print("corran: you attack it -> he's on it: %s (target %s)" % [c.auto_attack, c.target == spider])
		await _shot("9zy_corran_fights")
		var sp: SpawnPoint = spider.spawn_point
		World.damage(spider, 9999, p)
		await _wait(0.5)
		print("corran: it died -> respawns in %s s" % sp._timer)
	# gone with a farewell once the step is done
	p.quests["merricks_line_spring"] = {"active": false, "completions": 1}
	await _wait(1.0)
	print("corran: step 2 done -> companion %s" % (World.get_object(p.companion_id) != null))


## The Blightmother with a cleric's Corran (level 8), fought twice. Alone (no
## heals, no help) he must lose; with the player behind him (Warm Hands every
## 4 s while the mana lasts, three Rebukes on her) they must win. The player
## circles the fight: Corran must hold his ground, not orbit with them, and
## F2 must find him.
func _t_corran_boss() -> void:
	var p := World.local_player
	var cls := p.char_class
	p.char_class = "cleric"  # Corran's level goes by class
	if World.get_object(p.companion_id) != null:  # made for the class it was: send him off to come back as a cleric's
		World.get_object(p.companion_id).queue_free()
		p.companion_id = -1
	p.level = 7
	p.recalc_stats()
	var boss := _nearest_mob(p, "blightmother")
	if boss == null:
		print("corran_boss: FAIL no Blightmother")
		p.char_class = cls
		return
	var sp := boss.spawn_point
	for m in World.get_mobs():  # just her: clear the way in
		if m != boss:
			m.queue_free()
	await _boss_round(p, sp, false)
	await _boss_round(p, sp, true)
	p.char_class = cls


func _boss_round(p: Player, sp: SpawnPoint, supported: bool) -> void:
	var label := "with you" if supported else "alone"
	if sp.mob != null and is_instance_valid(sp.mob):  # a fresh one each round
		sp.mob.queue_free()
		await get_tree().process_frame
	sp.spawn()
	var boss := sp.mob
	var boss_at := boss.global_position
	p.hp = p.max_hp
	p.companion_back_at = 0
	var old := World.get_object(p.companion_id)
	if old != null:
		old.queue_free()
		p.companion_id = -1
	p.global_position = boss_at + Vector3(9, 0.5, 4)
	await _wait(1.5)
	var c := World.get_object(p.companion_id) as Npc
	if c == null:
		print("corran_boss: FAIL no companion (%s)" % label)
		return
	c.global_position = p.global_position + Vector3(1.5, 0, 1.5)
	await _wait(0.3)
	World.damage(boss, 1, p)  # the pull
	var t := 0.0
	var heals := 0
	var rebukes := 0
	var held_at := Vector3.INF
	var moved := 0.0
	var angle := 0.0
	var shot := false
	while t < 240.0 and is_instance_valid(boss) and not boss.dead and not c.dead and not p.dead:
		await get_tree().physics_frame
		var dt := get_physics_process_delta_time()
		t += dt
		angle += dt * TAU / 40.0  # circle the fight 8 m out, a quarter turn every 10 s
		var goal := boss_at + Vector3(cos(angle), 0, sin(angle)) * 8.0
		var to := goal - p.global_position
		to.y = 0.0
		p.velocity = to.normalized() * minf(4.0, to.length() * 4.0)
		p.move_and_slide()
		if is_instance_valid(boss) and c.auto_attack and c.distance_to(boss) <= World.melee_range():
			if held_at == Vector3.INF:
				held_at = c.global_position
			moved = maxf(moved, Vector2(c.global_position.x - held_at.x, c.global_position.z - held_at.z).length())
		if supported:
			if fmod(t, 4.0) < dt and heals < 11:  # Warm Hands at level 7: 24-28, about ten casts on a mana bar
				c.hp = mini(c.max_hp, c.hp + randi_range(24, 28))
				heals += 1
			if rebukes < 3 and t > 10.0 + rebukes * 15.0:  # Rebuke at level 7: 13-16
				World.damage(boss, randi_range(13, 16), p)
				rebukes += 1
		if supported and not shot and t > 20.0:
			shot = true
			p.target_group_member(0)
			print("corran_boss: F2 -> target %s" % (p.target.display_name if p.target != null else "nothing"))
			p.face_toward(boss_at)
			p.camera_pivot.rotation.y = 0.0
			p.zoom = 9.0
			p.pitch = -0.35
			await _shot("9zy_corran_boss")
	var won := not is_instance_valid(boss) or boss.dead
	print("corran_boss: %s, after %.0f s: she's %s, Corran %s (%d/%d hp), you %s; %d heals, %d rebukes; while you circled he moved at most %.1f m" % [label, t,
			"dead" if won else "standing (%d/%d)" % [boss.hp, boss.max_hp], "down" if c.dead else "up", c.hp, c.max_hp, "down" if p.dead else "up", heals, rebukes, moved])


## Corran as a support player sees him: the player walks the cave and never
## swings; whatever comes at them, Corran must kill. Logs where he stands and
## what he does every second.
func _t_corran_support() -> void:
	var main := get_parent()
	var p := World.local_player
	p.level = 5
	p.recalc_stats()
	p.hp = p.max_hp
	p.quests["merricks_line_sinew"] = {"active": false, "completions": 1}
	p.quests["merricks_line_spring"] = {"active": true, "completions": 0}
	await _ensure_zone("wellspring")
	await _wait(1.5)
	var c := World.get_object(p.companion_id) as Npc
	if c == null:
		print("corran_support: FAIL no companion")
		return
	var route := [Vector2(120, 126), Vector2(106, 121), Vector2(96, 121), Vector2(88, 123), Vector2(80, 122), Vector2(70, 117), Vector2(58, 111), Vector2(46, 103), Vector2(34, 94), Vector2(24, 84), Vector2(14, 72), Vector2(2, 62)]
	var kills := 0
	var mobs_before := World.get_mobs().size()
	for goal: Vector2 in route:
		for k in 400:
			if p.dead:
				break
			var fighting := World.get_mobs().any(func(m: Mob) -> bool: return not m.dead and m.hate.has(p.entity_id))
			if fighting:
				p.velocity = Vector3.ZERO  # stand and let him work, as a healer does
				if k % 60 == 0:
					var t := c.valid_target_entity()
					print("corran_support: fight: he's %.1f m from you, attacking %s, target %s %.1f m off, hp %d/%d; you %d/%d" % [c.distance_to(p), c.auto_attack,
							t.display_name if t != null else "-", c.distance_to(t) if t != null else -1.0, c.hp, c.max_hp, p.hp, p.max_hp])
				p.hp = mini(p.max_hp, p.hp + 1)  # a trickle of healing on yourself
				await get_tree().physics_frame
				continue
			var web := _nearest_mob(p, "thick_web")
			if web != null and not web.dead and web.distance_to(p) < 4.0:  # hack through it, then stop swinging
				World.request_set_target(p.entity_id, web.entity_id)
				if not p.auto_attack:
					World.request_toggle_attack(p.entity_id)
				await _wait(0.5)
				if not is_instance_valid(web) or web.dead:
					if p.auto_attack:
						World.request_toggle_attack(p.entity_id)
					print("corran_support: tore a web; he's %.1f m from you" % c.distance_to(p))
				continue
			var to := Vector3(goal.x, p.global_position.y, goal.y) - p.global_position
			if Vector2(to.x, to.z).length() < 0.8:
				break
			p.velocity = to.normalized() * 5.0
			p.move_and_slide()
			await get_tree().physics_frame
		print("corran_support: reached %s: he's %.1f m behind (at %s, you at %s)" % [goal, c.distance_to(p), c.global_position, p.global_position])
	kills = mobs_before - World.get_mobs().size()
	print("corran_support: monsters gone %d; you dead %s; he dead %s" % [kills, p.dead, c.dead])
	p.camera_pivot.rotation.y = PI
	p.zoom = 5.0
	await _shot("9zy_corran_support")


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
	for leg: Array in [["hollowmere", Vector2(200, 0), Vector2(1, 0), "sunward_steps"], ["sunward_steps", Vector2(-196, 0), Vector2(-1, 0), "hollowmere"]]:
		if not await _walk_border("sunward_border", leg[0], leg[1], leg[2], leg[3]):
			return


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


## The zone map (M): painted from the zone a few rows a frame, fog lifting
## where you've walked, and marks for exits, landmarks and town services.
func _t_zone_map() -> void:
	var main := get_parent()
	var p := World.local_player
	var hud: Node = main.hud
	var m: MapWindow = hud._map
	var t0 := Time.get_ticks_msec()
	print("zone_map: when you open it, already painted: %s" % m._painted.has(main.zone.zone_id))
	var z0: Zone = main.zone
	var step := z0.size / MapWindow.RES
	var u := Time.get_ticks_usec()
	for i in MapWindow.RES + 2:
		z0.height_at(-z0.half + i * step, 10.0)
	var h_row := Time.get_ticks_usec() - u
	u = Time.get_ticks_usec()
	for i in MapWindow.RES:
		z0._ground_color(-z0.half + i * step, 10.0, 1.0)
	print("zone_map: one row of heights %.1f ms, one row of colors %.1f ms" % [h_row / 1000.0, (Time.get_ticks_usec() - u) / 1000.0])
	var worst := 0.0
	while not m._painted.has(main.zone.zone_id) and Time.get_ticks_msec() - t0 < 20000:  # the slowest frame while it paints
		await get_tree().process_frame
		worst = maxf(worst, get_process_delta_time())
	print("zone_map: painting in the background finished %d ms into the section; slowest frame meanwhile %.1f ms" % [Time.get_ticks_msec() - t0, worst * 1000.0])
	t0 = Time.get_ticks_msec()
	for spot: Vector2 in [Vector2(0, 0), Vector2(0, -80), Vector2(0, -170), Vector2(60, 20)]:  # a walk up the road
		p.global_position = main.zone.ground(spot.x, spot.y) + Vector3.UP
		m._reveal(main.zone)
	m.toggle()
	while not m._painted.has(main.zone.zone_id) and Time.get_ticks_msec() - t0 < 20000:
		await get_tree().process_frame
	var cells: PackedByteArray = m._fog.get(main.zone.zone_id, PackedByteArray())
	var seen := 0
	for c in cells:
		seen += c
	var kinds := {}
	for mk: Array in m._marks:
		kinds[mk[0]] = int(kinds.get(mk[0], 0)) + 1
	print("zone_map: painted in %d ms; %d of %d fog cells explored; marks %s" % [Time.get_ticks_msec() - t0, seen, cells.size(), kinds])
	await _wait(0.3)
	await _shot("9zz_map_greenmoor")
	m.toggle()
	m._save_fog()
	print("zone_map: fog saved -> %s" % FileAccess.file_exists(m._fog_path()))


## A town's map, all explored: guildmasters, the bank, merchants, quests and
## crafting stations, with one highlighted from the legend.
func _t_zone_map_town() -> void:
	var main := get_parent()
	var hud: Node = main.hud
	var m: MapWindow = hud._map
	m.toggle()
	var cells := PackedByteArray()
	cells.resize(MapWindow.FOG_CELLS * MapWindow.FOG_CELLS)
	cells.fill(1)
	m._fog[main.zone.zone_id] = cells
	m._fog_dirty = true
	var t0 := Time.get_ticks_msec()
	while not m._painted.has(main.zone.zone_id) and Time.get_ticks_msec() - t0 < 20000:
		await get_tree().process_frame
	for i in m._marks.size():
		if m._marks[i][0] == "bank":
			m._highlight = i
	await _wait(0.3)
	print("zone_map_town: %s painted in %d ms; %d marks" % [main.zone.zone_id, Time.get_ticks_msec() - t0, m._marks.size()])
	await _shot("9zz_map_%s" % main.zone.zone_id)
	m.toggle()


## The compass: headings that turn with you, the zone's name, a pass's name
## when you face it, your target, and the sun by day and the moon by night.
func _t_compass() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	var hud: Node = main.hud
	var mob := _nearest_mob(p, "large_rat")
	World.request_set_target(p.entity_id, mob.entity_id)
	for view: Array in [[12.0, Vector3(0, 0, -300), "north_noon"], [22.5, Vector3(300, 0, 0), "east_night"]]:
		World.time_override = view[0]
		p.global_position = z.ground(0, -120) + Vector3.UP
		p.face_toward(view[1])
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 8.0
		p.pitch = -0.15
		await _wait(1.0)
		var c: Compass = hud._compass
		print("compass: %s -> heading %.0f, zone '%s', exits %s, sky %s" % [view[2], c._heading, c._zone_name, c._exits.map(func(e: Array) -> String: return e[1]), c._sky_mark()])
		await _shot("9zz_compass_%s" % view[2])
	World.time_override = -1.0


## Fallen logs block you like rocks: walking square at one stops at it.
func _t_solid_logs() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	var counts := {}
	var log_shape: CollisionShape3D
	for body in z.get_children():
		if body is StaticBody3D and body.has_meta("clutter"):
			var id: String = body.get_meta("clutter")
			counts[id] = int(counts.get(id, 0)) + body.get_child_count()
			if id == "log_fallen" and log_shape == null:
				for cs: CollisionShape3D in body.get_children():
					if cs.global_position.length() > 40.0 and absf(z.height_at(cs.global_position.x, cs.global_position.z) - cs.global_position.y) < 1.5:
						log_shape = cs
						break
	print("solid_logs: solid clutter pieces %s" % counts)
	if log_shape == null:
		print("solid_logs: FAIL no log found")
		return
	var box := (log_shape.shape as BoxShape3D).size
	var b := log_shape.global_basis
	var long_axis := b.x if box.x >= box.z else b.z  # the log's length
	var across := long_axis.cross(Vector3.UP).normalized()  # walk into its side
	var center := log_shape.global_position
	var start := center + across * 4.0
	p.global_position = z.ground(start.x, start.z) + Vector3.UP * 0.3
	p.face_toward(center)
	p.camera_pivot.rotation.y = 0.0
	await _wait(0.5)
	Input.action_press("move_forward")
	await _wait(2.5)
	Input.action_release("move_forward")
	var past := (p.global_position - center).dot(across)  # > 0 still on our side
	print("solid_logs: log %.1f x %.1f x %.1f m, start 4.0 m out, now %.2f m out on the near side -> %s" % [box.x, box.y, box.z, past, "PASS blocked" if past > 0.2 else "FAIL walked through"])
	await _shot("9zz_solid_log")


## Quest hints: every item every quest wants says where it's found, every
## quest where its giver stands; a click on the tracker writes one to chat.
func _t_quest_hints() -> void:
	var main := get_parent()
	var p := World.local_player
	var here := World.zone_of(p).zone_id
	for quest_id: String in GameData.quests:
		print("quest_hints: " + QuestHints.giver_hint(quest_id, here, p.global_position))
		for item_id: String in GameData.quests[quest_id]["wants"]:
			for line in QuestHints.item_hint(quest_id, item_id, here, p.global_position):
				print("quest_hints:   " + line)
	p.quests["fang_bounty"] = {"active": true}
	main.hud._refresh_quests()
	main.hud._quest_label.meta_clicked.emit("item:fang_bounty:gnoll_fang")
	main.hud._quest_label.meta_clicked.emit("giver:fang_bounty")
	await _wait(0.5)
	await _shot("9zz_quest_hints")


## The two customizable hotbars: a new character's spells on the main bar;
## slots set, swapped and cleared; a spell, an item and an action used from
## them; a drop from the spellbook, an item placed from the cursor; the lock;
## and the layout kept in the save.
func _t_hotbars() -> void:
	var main := get_parent()
	var p := World.local_player
	var hud: Node = main.hud
	var fresh := Player.default_hotbar(["blast_of_frost", "gate"])
	print("hotbars: a new wizard's bars -> %s (%d slots)" % [fresh.slice(0, 3), fresh.size()])
	var kit := p.hotbar.duplicate()
	p.char_class = "wizard"
	p.level = 10
	p.spells = ["blast_of_frost", "gate", "burning_embers", "minor_shielding"]
	p.recalc_stats()
	p.mana = p.max_mana
	p.cooldowns.clear()
	World.request_hotbar_set(p.entity_id, 0, "spell:blast_of_frost")
	World.request_hotbar_set(p.entity_id, 1, "spell:burning_embers")
	World.request_hotbar_set(p.entity_id, 3, "spell:not_a_spell_i_know")
	World.request_hotbar_swap(p.entity_id, 0, 1)
	World.request_hotbar_set(p.entity_id, 2, "")
	print("hotbars: set, swap, clear -> %s; an unknown spell refused: %s" % [p.hotbar.slice(0, 3), p.hotbar[3] != "spell:not_a_spell_i_know"])
	# use a spell, an item and an action from the bars
	var mob := _nearest_mob(p, "large_rat")
	p.global_position = main.zone.ground(mob.global_position.x + 8.0, mob.global_position.z) + Vector3.UP
	World.request_set_target(p.entity_id, mob.entity_id)
	p.activate_hotbar(1)
	await _wait(0.2)
	var casting := str(p.cast.get("spell", "")) if not p.cast.is_empty() else ("done, on cooldown" if p.cooldowns.has("blast_of_frost") else "nothing")
	World.request_interrupt(p.entity_id)
	p.pack.clear()
	p.pack.add("healing_potion", 3)
	World.request_hotbar_set(p.entity_id, 10, "item:healing_potion")
	p.hp = 1
	p.activate_hotbar(10)
	var sitting0 := p.sitting
	World.request_hotbar_set(p.entity_id, 11, "act:sit")
	p.activate_hotbar(11)
	print("hotbars: key 2 -> casting %s; Shift+1 (a potion) -> %d hp, %d potions left; Shift+2 (sit) -> sitting %s -> %s" % [casting, p.hp,
			p.pack.count("healing_potion"), sitting0, p.sitting])
	World.request_sit(p.entity_id, false)
	# Ctrl+1 fires the top bar's first slot (not also the main bar's): a key press as the player would make it
	p.cooldowns.clear()
	p.hp = 1
	var cast_before := p.cooldowns.duplicate()
	var key := InputEventKey.new()
	key.physical_keycode = KEY_1
	key.keycode = KEY_1
	key.ctrl_pressed = true
	key.pressed = true
	p._unhandled_input(key)
	await _wait(0.1)
	print("hotbars: Ctrl+1 -> a potion (%d hp, %d potions left); the main bar's key 1 spell fired too: %s" % [p.hp, p.pack.count("healing_potion"),
			p.cooldowns.has("burning_embers") and not cast_before.has("burning_embers") or not p.cast.is_empty()])
	World.request_interrupt(p.entity_id)
	# the HUD: a drop from the spellbook, an item from the cursor
	hud._hot_drop(Vector2.ZERO, {"hotvalue": "act:hail"}, 12)
	p.pack.add("roast_meat", 2)
	World.request_click(p.entity_id, _where(p, "roast_meat"))
	hud._hot_pressed(13)
	print("hotbars: spellbook drop -> slot S3 = %s; cursor click -> slot S4 = %s, cursor now empty %s, meat back in the pack %d" % [p.hotbar[12],
			p.hotbar[13], p.cursor.is_empty(), p.pack.count("roast_meat")])
	# the lock
	Controls.hotbar_locked = true
	var drag: Variant = hud._hot_drag(Vector2.ZERO, 0)
	Controls.hotbar_locked = false
	print("hotbars: locked -> drag from a slot %s" % ("refused" if drag == null else "allowed"))
	# kept in the save
	var saved: Array = p.to_save()["hotbar"]
	var again := Player.new()
	again.from_save(p.to_save())
	print("hotbars: saved and loaded -> same bars %s" % (again.hotbar == p.hotbar))
	again.free()
	hud._toggle_spellbook()
	await _wait(0.5)
	await _shot("9zz_hotbars")
	hud._toggle_spellbook()
	p.hotbar = kit
	p.pack.clear()
	p.level = 1
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
## The Shaman: a spirit wolf at 20; slows that space out a monster's swings
## (half as much on a named one); buffs, haste and a heal over time; the
## guildmasters in all three cities; the caster staves.
func _t_shaman() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	var saved_class := p.char_class
	p.char_class = "shaman"
	p.level = 25
	p.spells = []
	for sid: String in GameData.spells:
		if GameData.spells[sid].get("classes", {}).has("shaman"):
			p.spells.append(sid)
	print("shaman: %d spells from 1 to 25: %s" % [p.spells.size(), ", ".join(p.spells.map(func(s: String) -> String: return "%s %d" % [GameData.spells[s]["name"], int(GameData.spells[s]["classes"]["shaman"])]))])
	p.recalc_stats()
	for sk: String in GameData.skills["skills"]:
		if World.skill_cap(p, sk) > 0:
			p.skills[sk] = World.skill_cap(p, sk)
	print("shaman: level 25 -> %d hp, %d mana, ac %d" % [p.max_hp, p.max_mana, p.ac])
	var cast := func(sid: String) -> void:
		p.cooldowns.clear()
		p.mana = p.max_mana
		World.request_cast(p.entity_id, sid)
		await _wait(float(GameData.spells[sid]["cast_time"]) + 0.3)
	p.global_position = z.ground(20, 60) + Vector3.UP
	await cast.call("spirit_of_the_wolf")
	var pet := World.get_object(p.pet_id) as Pet
	print("shaman: called %s (%s, %d hp, hits %d-%d)" % [pet.display_name if pet else "nothing", pet.model_id if pet else "", pet.max_hp if pet else 0, pet.dmg_min if pet else 0, pet.dmg_max if pet else 0])
	await _wait(0.5)
	await _shot("9zz_shaman_wolf")
	World.request_pet(p.entity_id, "leave")
	# buffs on yourself
	var str0 := int(p.attributes.get("str", 0))
	var delay0 := p.attack_delay
	var hp0 := p.max_hp
	World.request_set_target(p.entity_id, p.entity_id)
	for sid: String in ["strengthen", "quickness", "ancestral_ward"]:
		await cast.call(sid)
	print("shaman: strengthen str %d -> %d; quickness delay %.2f -> %.2f s; ancestral ward max hp %d -> %d, regen %d" % [str0, int(p.attributes.get("str", 0)), delay0, p.attack_delay, hp0, p.max_hp, p.hp_regen])
	p.hp = p.max_hp / 3
	var before := p.hp
	await cast.call("spirit_mend")
	await _wait(12.5)
	print("shaman: spirit mend (+ward) -> %d hp back over 12 s" % (p.hp - before))
	# slows: count a gnoll's swings at you for 15 s, then again under Hornet Plague
	var mob := _nearest_mob(p, "gnoll_scout")
	mob.max_hp = 100000
	mob.hp = mob.max_hp
	p.max_hp = 100000
	p.hp = p.max_hp
	p.global_position = z.ground(mob.global_position.x + 1.5, mob.global_position.z) + Vector3.UP
	World.request_set_target(p.entity_id, mob.entity_id)
	mob.add_hate(p, 100.0)
	var count_swings := func(seconds: float) -> int:
		var n := 0
		var last := mob.swing_timer
		var until := Time.get_ticks_msec() + int(seconds * 1000.0)
		while Time.get_ticks_msec() < until:
			await get_tree().physics_frame
			if mob.swing_timer > last + 0.05:
				n += 1
			last = mob.swing_timer
		return n
	await _wait(1.0)
	var plain: int = await count_swings.call(15.0)
	await cast.call("turgurs_insects")
	var slowed_pct := mob.slow_pct
	var slowed: int = await count_swings.call(15.0)
	print("shaman: gnoll (delay %.1f s) swung %d times in 15 s; under Hornet Plague (%d%%, %.0f s) %d times -> %s" % [
			mob.attack_delay, plain, slowed_pct, mob.slow_left, slowed, "PASS" if slowed < plain else "FAIL"])
	await cast.call("drowsy")
	print("shaman: a weaker slow on top -> still %d%%" % mob.slow_pct)
	mob.hate.clear()
	var named := _nearest_mob(p, "gnoll_pup")  # stands in for a named one
	named.data = named.data.duplicate()
	named.data["named"] = true
	World.request_set_target(p.entity_id, named.entity_id)
	p.global_position = z.ground(named.global_position.x + 8.0, named.global_position.z) + Vector3.UP
	await cast.call("turgurs_insects")
	print("shaman: Hornet Plague on a named foe -> %d%%" % named.slow_pct)
	named.hate.clear()
	# guildmasters and gear
	var gms := []
	for zone_id: String in QuestHints.zones():
		for n: Dictionary in QuestHints.zones()[zone_id].get("npcs", []):
			var g: Dictionary = GameData.npcs.get(str(n["id"]), {}).get("guildmaster", {})
			if str(g.get("class", "")) == "shaman":
				gms.append("%s in %s" % [GameData.npcs[str(n["id"])]["name"], zone_id])
	print("shaman: guildmasters %s" % [gms])
	for id: String in ["worn_staff", "oak_staff", "oak_staff@masterwork", "round_shield", "steel_dirk", "steel_breastplate"]:
		var it := GameData.item(id)
		var ok: bool = it.get("classes", []).is_empty() or "shaman" in it.get("classes", [])
		print("shaman: %s -> int %d wis %d mana %d, a shaman may use it %s" % [it["name"], int(it.get("int", 0)), int(it.get("wis", 0)), int(it.get("mana", 0)), ok])
	p.char_class = saved_class
	p.level = 1
	p.buffs.clear()
	p.recalc_stats()
	p.hp = p.max_hp


## Going home: every character carries a Homeward Stone and is bound to
## Emberhold at first; the stone (10 s, still) takes you there across zones and
## recharges; moving interrupts it and costs nothing; /bind works only at a
## city's bindstone, and a priest binds you when asked; Gate follows your bind
## too, and lands on Rainhold's decks.
func _t_homeward() -> void:
	var main := get_parent()
	var p := World.local_player
	var zone_now := func() -> String: return (main.zone as Zone).zone_id
	var wait_zone := func(zone_id: String) -> void:
		for k in 60:
			if zone_now.call() == zone_id and not main._changing_zone:
				break
			await _wait(0.25)
		await _wait(0.5)
	print("homeward: carries a stone %s; bound to %s" % ["homeward_stone" in p.owned_item_ids(), World.bind_zone_of(p)])
	World.request_chat(p.entity_id, "/bind")
	await _wait(0.2)
	print("homeward: /bind in Greenmoor -> still bound to %s" % World.bind_zone_of(p))
	# moving interrupts the stone, and it doesn't recharge
	World.request_use_item(p.entity_id, _where(p, "homeward_stone"))
	await _wait(2.0)
	p.global_position += Vector3(2, 0, 0)
	await _wait(0.3)
	print("homeward: moved while using it -> casting %s, recharging %s, still in %s" % [not p.cast.is_empty(), p.cooldowns.has("item:homeward_stone"), zone_now.call()])
	World.request_use_item(p.entity_id, _where(p, "homeward_stone"))
	await _wait(10.6)
	await wait_zone.call("emberhold")
	var home := main.zone as Zone
	print("homeward: stone -> now in %s, %.1f m from its bindstone; recharging %ds; still carry it %s" % [zone_now.call(),
			Vector2(p.global_position.x, p.global_position.z).distance_to(Vector2(home.bind_point.x, home.bind_point.z)), int(p.cooldowns.get("item:homeward_stone", 0)), "homeward_stone" in p.owned_item_ids()])
	await _shot("9zz_homeward_emberhold")
	World.request_use_item(p.entity_id, _where(p, "homeward_stone"))
	print("homeward: using it again at once -> casting %s" % (not p.cast.is_empty()))
	# bind in Rainhold with the priest, then drink a draught from Greenmoor
	World.zone_change.emit(p, "rainhold", Vector2.INF, Vector2.INF)
	await wait_zone.call("rainhold")
	var nalini: Npc = _npcs()["tidepriest_nalini"]
	_stand_by(p, nalini)
	World.request_say(p.entity_id, "bind")
	print("homeward: asked Tidepriest Nalini to bind -> bound to %s" % World.bind_zone_of(p))
	World.zone_change.emit(p, "greenmoor", Vector2(0, 10), Vector2(0, 0))
	await wait_zone.call("greenmoor")
	p.pack.add("draught_of_homecoming", 2)
	World.request_use_item(p.entity_id, _where(p, "draught_of_homecoming"))
	await _wait(10.6)
	await wait_zone.call("rainhold")
	var rain := main.zone as Zone
	print("homeward: draught -> in %s at height %.1f (bindstone deck %.1f, ground %.1f); draughts left %d" % [zone_now.call(), p.global_position.y,
			rain.bind_point.y, rain.height_at(p.global_position.x, p.global_position.z), p.pack.count("draught_of_homecoming")])
	await _shot("9zz_homeward_rainhold")
	# Gate follows the bind too (a wizard's)
	World.zone_change.emit(p, "greenmoor", Vector2(0, 10), Vector2(0, 0))
	await wait_zone.call("greenmoor")
	var saved_class := p.char_class
	p.char_class = "wizard"
	p.spells.append("gate")
	p.mana = p.max_mana
	p.cooldowns.erase("gate")
	World.request_cast(p.entity_id, "gate")
	await _wait(float(GameData.spells["gate"]["cast_time"]) + 0.4)
	await wait_zone.call("rainhold")
	print("homeward: gate from Greenmoor -> in %s" % zone_now.call())
	p.spells.erase("gate")
	p.char_class = saved_class
	p.bind_zone = ""
	World.zone_change.emit(p, "greenmoor", Vector2(0, 10), Vector2(0, 0))
	await wait_zone.call("greenmoor")


## High Terrace and Cinderpass's four borders, every one both ways: Hollowmere
## north, The Bleach west, Thornwood north, and the two new zones to each other.
func _t_ashfall_borders() -> void:
	for leg: Array in [["hollowmere", Vector2(0, -190), Vector2(0, -1), "high_terrace"], ["high_terrace", Vector2(-225, 0), Vector2(-1, 0), "cinderpass"],
			["cinderpass", Vector2(0, 195), Vector2(0, 1), "thornwood"], ["thornwood", Vector2(0, -225), Vector2(0, -1), "cinderpass"],
			["cinderpass", Vector2(195, 0), Vector2(1, 0), "high_terrace"], ["high_terrace", Vector2(225, 0), Vector2(1, 0), "the_bleach"],
			["the_bleach", Vector2(-225, 0), Vector2(-1, 0), "high_terrace"], ["high_terrace", Vector2(0, 225), Vector2(0, 1), "hollowmere"]]:
		if not await _walk_border("ashfall_borders", leg[0], leg[1], leg[2], leg[3]):
			return


## The Ranger: a new one starts with a bow and arrows; shots hit harder than
## anyone else's bow; Aimed Shot, Multishot (three foes) and Storm of Arrows;
## Track lists what's near and puts it on the compass; the hawk at 20.
func _t_ranger() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	var fresh := Player.new()
	fresh.from_save({"name": "Fresh", "class": "ranger"})
	print("ranger: a new ranger wears %s and carries %d arrows; spells %s" % [fresh.equipment, fresh.pack.count("crude_arrow"), fresh.spells])
	fresh.free()
	var saved_class := p.char_class
	p.char_class = "ranger"
	p.level = 30
	p.spells = []
	for sid: String in GameData.spells:
		if GameData.spells[sid].get("classes", {}).has("ranger"):
			p.spells.append(sid)
	p.equipment["range"] = "cinderwood_longbow"
	p.pack.add("crude_arrow", 100)
	p.recalc_stats()
	for sk: String in GameData.skills["skills"]:
		if World.skill_cap(p, sk) > 0:
			p.skills[sk] = World.skill_cap(p, sk)
	print("ranger: %d spells to 30; level 30 -> %d hp, %d mana; bow reach %.0f m (a warrior's %.0f)" % [p.spells.size(), p.max_hp, p.max_mana,
			World.ranged_reach(p), float(GameData.item("cinderwood_longbow")["range"])])
	var pups: Array = World.get_mobs().filter(func(m: Mob) -> bool: return m.mob_id in ["gnoll_pup", "gnoll_scout", "large_rat"])
	pups.sort_custom(func(a: Mob, b: Mob) -> bool: return a.global_position.distance_to(p.global_position) < b.global_position.distance_to(p.global_position))
	var t: Mob = pups[0]
	for m: Mob in World.get_mobs():  # three foes standing together, very tough so nothing dies mid-test
		m.max_hp = 100000
		m.hp = m.max_hp
	var near: Array = World.get_mobs().filter(func(m: Mob) -> bool: return m != t and not m.dead and World.zone_of(m) == World.zone_of(t))
	for k in mini(2, near.size()):
		(near[k] as Mob).global_position = t.global_position + Vector3(2.0 + k * 1.5, 0, 1.5)
		(near[k] as Mob).set_physics_process(false)
	t.set_physics_process(false)
	p.global_position = z.ground(t.global_position.x + 20.0, t.global_position.z) + Vector3.UP
	p.face_toward(t.global_position)
	World.request_set_target(p.entity_id, t.entity_id)
	var fire := func(what: String) -> Array:
		var before := {}
		for m: Mob in World.get_mobs():
			before[m] = m.hp
		var arrows := p.pack.count("crude_arrow")
		p.cooldowns.clear()
		if what == "bow":
			World.request_ranged(p.entity_id)
		else:
			World.request_cast(p.entity_id, what)
		await _wait(0.3)
		var hit := 0
		var dmg := 0
		for m: Mob in World.get_mobs():
			if before.has(m) and int(before[m]) > m.hp:
				hit += 1
				dmg += int(before[m]) - m.hp
		return [hit, dmg, arrows - p.pack.count("crude_arrow")]
	var plain := [0, 0]
	var aimed := [0, 0]
	for k in 12:
		var a: Array = await fire.call("bow")
		plain[0] += a[1]
		plain[1] += 1
		var b: Array = await fire.call("aimed_shot")
		aimed[0] += b[1]
		aimed[1] += 1
		if k == 0:
			print("ranger: first aimed shot: %s" % [b])
	print("ranger: 12 plain shots average %.0f, 12 aimed shots average %.0f" % [float(plain[0]) / plain[1], float(aimed[0]) / aimed[1]])
	var multi: Array = await fire.call("multishot")
	print("ranger: multishot -> hit %d foes, %d arrows used" % [multi[0], multi[2]])
	var storm: Array = await fire.call("storm_of_arrows")
	print("ranger: storm of arrows -> hit %d foes, %d arrows used" % [storm[0], storm[2]])
	p.pack.remove("crude_arrow", p.pack.count("crude_arrow"))
	p.cooldowns.clear()
	World.request_cast(p.entity_id, "aimed_shot")
	print("ranger: aimed shot with no arrows -> cooldown started %s" % p.cooldowns.has("aimed_shot"))
	p.pack.add("crude_arrow", 50)
	for m: Mob in [t] + near.slice(0, 2):
		m.set_physics_process(true)
		m.hate.clear()
	World.request_set_target(p.entity_id, p.entity_id)
	p.cooldowns.clear()
	World.request_cast(p.entity_id, "track")
	await _wait(0.4)
	var hud: Node = main.hud
	print("ranger: track -> window %s, radius %.0f m, %d monsters listed" % [hud._track_panel.visible, hud._track_radius, hud._track_list.get_child_count()])
	var first := hud._track_list.get_child(0) as Button
	if first != null:
		first.pressed.emit()
	await _wait(0.3)
	print("ranger: clicked the first -> the compass tracks %s" % (hud._compass.tracked.display_name if hud._compass.tracked else "nothing"))
	await _shot("9zz_ranger_track")
	hud._track_panel.visible = false
	p.mana = p.max_mana
	p.cooldowns.clear()
	World.request_cast(p.entity_id, "call_of_the_hawk")
	await _wait(5.5)
	var pet := World.get_object(p.pet_id) as Pet
	print("ranger: called %s (%s, %d hp, hits %d-%d)" % [pet.display_name if pet else "nothing", pet.model_id if pet else "", pet.max_hp if pet else 0, pet.dmg_min if pet else 0, pet.dmg_max if pet else 0])
	await _wait(0.5)
	await _shot("9zz_ranger_hawk")
	World.request_pet(p.entity_id, "leave")
	hud._compass.tracked = null
	p.equipment.erase("range")
	p.char_class = saved_class
	p.level = 1
	p.buffs.clear()
	p.recalc_stats()
	p.hp = p.max_hp


## Level cap 30: a character can reach it; every class's three new abilities
## (26, 28, 30) cast and land; the elemental lord and the bone colossus rise.
func _t_cap30() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	print("cap30: max level %d" % int(World.cfg("max_level", 0)))
	var saved_class := p.char_class
	var mob := _nearest_mob(p, "gnoll_scout")
	mob.max_hp = 1000000
	mob.hp = mob.max_hp
	mob.set_physics_process(false)
	for cls: String in GameData.classes:
		p.char_class = cls
		p.level = 30
		p.spells = []
		for sid: String in GameData.spells:
			if int(GameData.spells[sid].get("classes", {}).get(cls, 0)) >= 26:
				p.spells.append(sid)
		p.spells.sort_custom(func(a: String, b: String) -> bool: return str(GameData.spells[a]["type"]) == "pet" and str(GameData.spells[b]["type"]) != "pet")
		if cls == "ranger":
			p.spells.push_front("call_of_the_hawk")
		p.recalc_stats()
		for sk: String in GameData.skills["skills"]:
			if World.skill_cap(p, sk) > 0:
				p.skills[sk] = World.skill_cap(p, sk)
		var out := PackedStringArray()
		for sid: String in p.spells:
			var s: Dictionary = GameData.spells[sid]
			p.cooldowns.clear()
			p.mana = p.max_mana
			p.hp = p.max_hp
			p.hidden = s.get("requires_hidden", false)
			var tgt: Entity = mob
			if str(s.get("target", "")) in ["self", "group", "friendly"]:
				tgt = p
			if str(s["type"]) == "shot":
				p.equipment["range"] = "cinderwood_longbow"
				p.pack.add("crude_arrow", 20)
			p.global_position = z.ground(mob.global_position.x + (2.0 if float(s.get("range", 0)) < 5.0 and str(s["type"]) != "shot" else 12.0), mob.global_position.z) + Vector3.UP
			if s.get("from_behind", false) or s.get("requires_hidden", false):
				p.global_position = mob.global_position - (-mob.global_basis.z) * 2.0 + Vector3.UP * 0.5
			p.face_toward(mob.global_position)
			World.request_set_target(p.entity_id, tgt.entity_id)
			var hp0 := mob.hp
			mob.hate.clear()
			mob.auto_attack = false
			World.request_cast(p.entity_id, sid)
			await _wait(float(s.get("cast_time", 0)) + 0.4)
			var what := ""
			match str(s["type"]):
				"damage", "shot", "lifetap":
					what = "hit %d" % (hp0 - mob.hp)
				"dot":
					what = "dot %s" % mob.dots.any(func(d: Dictionary) -> bool: return d["spell"] == sid)
				"buff":
					var on: Entity = World.get_object(p.pet_id) as Entity if str(s.get("target", "")) == "pet" else p
					what = "buff %s" % (on != null and on.buffs.has(sid))
				"heal":
					what = "heal cast"
				"slow":
					what = "slow %d%%" % mob.slow_pct
				"pet":
					var pet := World.get_object(p.pet_id) as Pet
					what = "pet %s (%s, %d hp)" % [pet.display_name if pet else "none", pet.model_id if pet else "", pet.max_hp if pet else 0]
			out.append("%s: %s" % [GameData.spells[sid]["name"], what])
			if str(s["type"]) == "pet":
				await _wait(0.5)
				await _shot("9zz_cap30_%s" % sid)
		mob.dots.clear()
		mob.slow_left = 0.0
		print("cap30: %s -> %s" % [cls, "; ".join(out)])
		World.request_pet(p.entity_id, "leave")
		p.buffs.clear()
		p.hidden = false
		p.equipment.erase("range")
	mob.set_physics_process(true)
	p.char_class = saved_class
	p.level = 1
	p.recalc_stats()
	p.hp = p.max_hp


## High Terrace: every monster in place (and the ghost leopard at night), the
## pilgrims' rest's five quests, the terraces and the paddies.
func _t_terrace_life() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	World.time_override = 12.0
	await _wait(0.5)
	var counts := {}
	for m in World.get_mobs():
		counts[m.mob_id] = int(counts.get(m.mob_id, 0)) + 1
	print("terrace_life: noon: %d monsters %s" % [World.get_mobs().size(), counts])
	print("terrace_life: ground at the rest %.1f, mid %.1f, at the monastery %.1f; fields %d" % [z.height_at(-20, 200), z.height_at(0, 0), z.height_at(0, -205), z.data.get("fields", []).size()])
	var sloped := PackedStringArray()
	for lm: Dictionary in z.data["landmarks"] + z.data.get("fields", []):
		var worst := 0.0
		var r := 3.0 if lm.has("type") else maxf(float(lm["size"][0]), float(lm["size"][1])) * 0.5
		for k in 9:
			var at := Vector2(lm["pos"][0], lm["pos"][1]) + (Vector2.from_angle(k * TAU / 8) * r if k < 8 else Vector2.ZERO)
			worst = maxf(worst, z.terrace_face(at.x, at.y))
		if worst > 0.15:
			sloped.append("%s %s (%.2f)" % [lm.get("id", lm.get("type", lm.get("crop", "field"))), lm["pos"], worst])
	print("terrace_life: on a terrace slope: %s" % ", ".join(sloped))
	p.level = 23
	p.recalc_stats()
	p.pack.clear()
	var npcs := _npcs()
	var tenzin: Npc = npcs["brother_tenzin"]
	var pema: Npc = npcs["tea_mother_pema"]
	_stand_by(p, tenzin)
	for word in ["hail", "fallen", "beads", "abbot", "seal", "guardians", "colossus", "heartstone"]:
		World.request_say(p.entity_id, word)
	for pair: Array in [["prayer_bead", 4], ["prayer_bead", 4], ["abbots_seal", 1], ["colossus_heartstone", 1]]:
		p.pack.add(pair[0], pair[1])
		_stand_by(p, tenzin)
		await _hand_in(p, tenzin, [pair[0]])
	_stand_by(p, pema)
	for word in ["hail", "harpies", "talons", "griffons", "skyrend", "plume"]:
		World.request_say(p.entity_id, word)
	for pair: Array in [["harpy_talon", 4], ["skyrend_plume", 1]]:
		p.pack.add(pair[0], pair[1])
		_stand_by(p, pema)
		await _hand_in(p, pema, [pair[0]])
	await _wait(0.3)
	print("terrace_life: rewards: wraps %d, beads %d, ring %d, cloak %d; quests done %s" % [p.pack.count("monks_wraps"), p.pack.count("pilgrims_prayer_beads"),
			p.pack.count("heartstone_ring"), p.pack.count("skyrend_cloak"),
			["tenzins_beads", "the_abbots_seal", "the_colossus_heart", "pemas_talons", "skyrends_plume"].map(func(q: String) -> int: return int(p.quests.get(q, {}).get("completions", 0)))])
	World.time_override = 23.0
	await _wait(0.6)
	print("terrace_life: the ghost leopard at 23:00 %s" % (_nearest_mob(p, "ghost_leopard") != null))
	World.time_override = 12.0
	var paddy := Vector2(z.data["fields"][0]["pos"][0], z.data["fields"][0]["pos"][1])
	var sheets := z.get_children().filter(func(n: Node) -> bool: return n is MeshInstance3D and (n as MeshInstance3D).mesh is PlaneMesh \
			and z.in_field((n as Node3D).global_position.x, (n as Node3D).global_position.z, 1.0)).size()  # a plane on a paddy: its water (a camp's floor is a plane too)
	print("terrace_life: paddy water sheets %d of %d paddies" % [sheets, z.data["fields"].filter(func(f: Dictionary) -> bool: return f.get("water", false)).size()])
	var tea := Vector2(z.data["fields"][9]["pos"][0], z.data["fields"][9]["pos"][1])
	for spot: Array in [[Vector2(-20, 215), Vector2(-20, 190), "rest"], [paddy + Vector2(8, -34), paddy, "paddies"], [tea + Vector2(20, 16), tea, "tea"], [Vector2(0, -120), Vector2(0, -205), "monastery"]]:
		p.global_position = z.ground(spot[0].x, spot[0].y) + Vector3.UP * 2.0
		p.face_toward(Vector3(spot[1].x, 0, spot[1].y))
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 9.0
		p.pitch = -0.2
		await _wait(1.0)
		await _shot("9zv_terrace_%s" % spot[2])
	main.hud._inv_panel.visible = false
	for id: String in ["griffon", "harpy", "fallen_monk", "gargoyle", "terrace_golem", "snow_leopard", "mountain_yak", "mountain_troll", "fallen_abbot", "terrace_colossus", "griffon_matriarch", "harpy_matriarch"]:
		var m: Mob = _nearest_mob(p, id)
		if m == null:
			print("terrace_life: no %s found" % id)
			continue
		m.set_physics_process(false)
		var at := m.global_position
		p.global_position = z.ground(at.x + 4.0, at.z + 3.0) + Vector3.UP
		p.face_toward(at)
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 5.0
		p.pitch = -0.15
		await _wait(0.8)
		await _shot("9zw_%s" % id)
		m.set_physics_process(true)
	World.time_override = -1.0


## Cinderpass: its monsters (wraiths at night), the scouts' four quests, Tovar's
## wares, the lava that burns, the vents, the falling ash.
func _t_cinder_life() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	World.time_override = 12.0
	await _wait(0.5)
	var counts := {}
	for m in World.get_mobs():
		counts[m.mob_id] = int(counts.get(m.mob_id, 0)) + 1
	print("cinder_life: noon: %d monsters %s" % [World.get_mobs().size(), counts])
	print("cinder_life: ash falling %s; vents %d" % [z.find_children("*", "Rain", true, false).size() > 0, z.data["landmarks"].filter(func(l: Dictionary) -> bool: return l["type"] == "vent").size()])
	p.level = 30
	p.recalc_stats()
	p.pack.clear()
	var npcs := _npcs()
	var brenna: Npc = npcs["scout_captain_brenna"]
	var tovar: Npc = npcs["smith_tovar"]
	_stand_by(p, brenna)
	for word in ["hail", "ember", "ember sigil", "leader", "ashkar", "brand"]:
		World.request_say(p.entity_id, word)
	for pair: Array in [["ember_sigil", 4], ["ember_sigil", 4], ["ashkars_brand", 1]]:
		p.pack.add(pair[0], pair[1])
		_stand_by(p, brenna)
		await _hand_in(p, brenna, [pair[0]])
	_stand_by(p, tovar)
	for word in ["hail", "drake", "scales", "cindermaw", "heart"]:
		World.request_say(p.entity_id, word)
	for pair: Array in [["drake_scale", 4], ["cindermaw_heart", 1]]:
		p.pack.add(pair[0], pair[1])
		_stand_by(p, tovar)
		await _hand_in(p, tovar, [pair[0]])
	await _wait(0.3)
	print("cinder_life: rewards: signet %d, blade %d, cloak %d; quests done %s; Tovar sells %d things" % [p.pack.count("scouts_signet"), p.pack.count("cinderheart_blade"),
			p.pack.count("drakescale_cloak"), ["ember_sigils", "ashkars_brand", "drake_scales", "cindermaws_heart"].map(func(q: String) -> int: return int(p.quests.get(q, {}).get("completions", 0))),
			(GameData.npcs["smith_tovar"]["merchant"]["sells"] as Array).size()])
	# the lava burns
	var river: Dictionary = z.data["rivers"][0]
	var in_lava := Vector2(river["points"][2][0], river["points"][2][1])
	p.hp = p.max_hp
	var hp0 := p.hp
	p.global_position = Vector3(in_lava.x, z.surface_at(in_lava.x, in_lava.y) + 0.5, in_lava.y)
	await _wait(2.5)
	print("cinder_life: standing in lava at %s (lava_at %s) for 2.5 s -> %d of %d hp lost" % [in_lava, z.lava_at(in_lava.x, in_lava.y), hp0 - p.hp, p.max_hp])
	p.hp = p.max_hp
	World.time_override = 23.0
	await _wait(0.6)
	var wraiths := World.get_mobs().filter(func(m: Mob) -> bool: return m.mob_id in ["ash_wraith", "ash_wraith_lord"]).size()
	print("cinder_life: ash wraiths at noon %d, at 23:00 %d" % [int(counts.get("ash_wraith", 0)), wraiths])
	World.time_override = 12.0
	for spot: Array in [[Vector2(10, 215), Vector2(30, 178), "outpost"], [Vector2(-104, -44), Vector2(-125, -50), "lava"], [Vector2(100, 40), Vector2(140, 60), "cult"], [Vector2(40, -120), Vector2(60, -160), "vents"]]:
		p.global_position = z.ground(spot[0].x, spot[0].y) + Vector3.UP * 2.0
		p.face_toward(Vector3(spot[1].x, 0, spot[1].y))
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 9.0
		p.pitch = -0.2
		await _wait(1.0)
		await _shot("9zx_cinder_%s" % spot[2])
	for id: String in ["magma_golem", "wild_fire_elemental", "ash_drake", "lava_salamander", "ember_cultist", "charred_dead", "high_pyromancer", "cinder_drake", "magma_colossus"]:
		var m: Mob = _nearest_mob(p, id)
		if m == null:
			print("cinder_life: no %s found" % id)
			continue
		m.set_physics_process(false)
		var at := m.global_position
		p.global_position = z.ground(at.x + 4.0, at.z + 3.0) + Vector3.UP
		p.face_toward(at)
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 5.0
		p.pitch = -0.15
		await _wait(0.8)
		await _shot("9zy_%s" % id)
		m.set_physics_process(true)
	World.time_override = -1.0


## Starting stats: the creation screen's picker (a class's spread, limits,
## Enter World refused until all 25 are spent); points really change health,
## damage and mana; a cheated spread is cut back; a character from before
## stats gets the one-time window and can spend only once.
func _t_char_stats() -> void:
	var main := get_parent()
	var p := World.local_player
	var cc := CharCreate.new()
	cc.setup({"name": "Oldhand", "class": "cleric", "level": 12, "deity": "light"})  # with a saved character: the tallest the page gets
	cc.layer = 30
	main.add_child(cc)
	await _wait(0.4)
	var picker: StatPicker = cc._stats
	print("char_stats: warrior starts with %s (%d left)" % [picker.points, picker.points_left()])
	cc._select("wizard")
	print("char_stats: wizard -> %s" % [picker.points])
	for k in 20:
		picker._add("int", 1)
	print("char_stats: int can't pass +15 -> %d; points left %d" % [int(picker.points.get("int", 0)), picker.points_left()])
	picker.points = {}
	picker._refresh()
	cc._name_edit.text = "Statcheck"
	cc._deity = "wind"
	var made := []
	cc.confirmed.connect(func(s: Dictionary) -> void: made.append(s))
	cc._create()
	print("char_stats: enter with 25 unspent -> refused %s ('%s')" % [made.is_empty(), cc._error.text])
	cc._select("ranger")
	await _wait(0.3)
	await _shot("9zz_char_stats_create")
	cc._create()
	print("char_stats: with the ranger spread -> created %s" % [made[0].get("stats") if not made.is_empty() else "nothing"])
	cc.queue_free()
	var plain := Player.new()
	plain.from_save({"name": "Plain", "class": "warrior", "stats": {}})
	var built := Player.new()
	built.from_save({"name": "Built", "class": "warrior", "stats": {"sta": 15, "str": 10}})
	var cheat := Player.new()
	cheat.from_save({"name": "Cheat", "class": "wizard", "stats": {"sta": 99, "str": 50, "int": 7}})
	print("char_stats: warrior with STA 90, STR 85 -> hp %d vs %d, max damage %d vs %d; sheet STA %d" % [built.max_hp, plain.max_hp, built.dmg_max, plain.dmg_max, built.stat_value("sta")])
	print("char_stats: a cheated spread %s -> kept %s" % [{"sta": 99, "str": 50, "int": 7}, cheat.stat_points])
	for x: Player in [plain, built, cheat]:
		x.free()
	# a character from before stats
	p.stats_chosen = false
	p.stat_points = {}
	p.race = "human"
	main.hud._stats_later = false
	await _wait(0.4)
	print("char_stats: an older character -> the window opens %s" % main.hud._stats_panel.visible)
	await _shot("9zz_char_stats_window")
	var mana0 := p.max_mana
	World.request_set_stats(p.entity_id, {"int": 15, "sta": 10})
	World.request_set_stats(p.entity_id, {"str": 15, "agi": 10})
	await _wait(0.3)
	print("char_stats: spent -> %s (mana %d -> %d); a second spend ignored %s; window closed %s" % [p.stat_points, mana0, p.max_mana, not p.stat_points.has("str"), not main.hud._stats_panel.visible])
	p.stat_points = {}
	p.recalc_stats()


## Races: the data (every class open to some race, every race 375 stat
## points); race stats in the numbers; creation's race picker (classes it
## can't be greyed, a troll starts in Rainhold); the traits (human xp, troll
## regeneration, ogre stun immunity, halfling unnoticed, gnome mana); an older
## character chooses its race once, only one its class allows.
func _t_races() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	for cls: String in GameData.classes:
		var open := GameData.races.keys().filter(func(r: String) -> bool: return cls in GameData.races[r]["classes"])
		print("races: %s -> %s" % [cls, open])
	var sums := {}
	for r: String in GameData.races:
		var t := 0
		for v: Variant in (GameData.races[r]["stats"] as Dictionary).values():
			t += int(v)
		sums[r] = t
	print("races: stat totals %s" % [sums])
	var made := {}
	for pair: Array in [["human", "warrior"], ["ogre", "warrior"], ["human", "wizard"], ["gnome", "wizard"], ["human", "rogue"], ["halfling", "rogue"]]:
		var x := Player.new()
		x.from_save({"name": "Probe", "class": pair[1], "race": pair[0], "stats": {}})
		made["%s %s" % pair] = "hp %d, dmg %d-%d, mana %d, ac %d, STR %d AGI %d INT %d" % [x.max_hp, x.dmg_min, x.dmg_max, x.max_mana, x.ac, x.stat_value("str"), x.stat_value("agi"), x.stat_value("int")]
		x.free()
	for k: String in made:
		print("races: %s -> %s" % [k, made[k]])
	# creation
	var cc := CharCreate.new()
	cc.layer = 30
	main.add_child(cc)
	await _wait(0.4)
	cc._select_race("troll")
	var open_buttons := cc._class_buttons.keys().filter(func(c: String) -> bool: return not (cc._class_buttons[c] as Button).disabled)
	cc._select("wizard")
	print("races: a troll may be %s; picking wizard leaves %s; stats start %s" % [open_buttons, cc._selected, cc._stats._rows["str"][1].text])
	cc._name_edit.text = "Grukk"
	cc._deity = "fire"  # Agnavar won't take a troll: refused
	cc._create()
	print("races: a troll following Agnavar -> '%s'" % cc._error.text)
	cc._deity = "horn"
	var got := []
	cc.confirmed.connect(func(s: Dictionary) -> void: got.append(s))
	cc._create()
	print("races: created %s" % [got[0] if not got.is_empty() else "nothing"])
	await _wait(0.2)
	await _shot("9zz_races_create")
	cc.queue_free()
	# traits
	var saved_race := p.race
	var saved_class := p.char_class
	p.race = "human"
	p.level = 18  # past the Elders' blessing, and a bar long enough not to level mid-test
	p.xp = 0
	p.recalc_stats()
	var xp0 := p.xp
	p.add_xp(100)
	var human_xp := p.xp - xp0
	p.race = "dwarf"
	xp0 = p.xp
	p.add_xp(100)
	print("races: 100 experience -> a human gets %d, a dwarf %d" % [human_xp, p.xp - xp0])
	p.race = "troll"
	p.char_class = "warrior"
	p.recalc_stats()
	var troll_regen := p.hp_regen
	p.race = "human"
	p.recalc_stats()
	print("races: health regeneration, troll %d vs human %d" % [troll_regen, p.hp_regen])
	var gust: Dictionary = GameData.spells["gust_of_wind"]
	var mob := _nearest_mob(p, "gnoll_pup")
	for r: String in ["human", "ogre"]:
		p.race = r
		p.stun_left = 0.0
		World._land(mob, "gust_of_wind", p, gust, 0)
		print("races: a %s hit by a stunning gust -> stunned %.1f s" % [r, p.stun_left])
	p.stun_left = 0.0
	var beast: Mob = null
	for m in World.get_mobs():
		if m.aggressive and not m.dead:
			beast = m
			break
	if beast != null:
		p.level = 1
		for r: String in ["halfling", "human"]:
			p.race = r
			beast.hate.clear()
			beast.state = Mob.State.IDLE
			beast.set_physics_process(false)
			var at := beast.global_position + Vector3(beast.aggro_radius * 0.85, 0, 0)
			p.global_position = z.ground(at.x, at.z) + Vector3.UP
			beast._scan_timer = 0.0
			beast._scan_for_aggro(0.1)
			print("races: a %s at %.0f%% of a %s's notice range -> noticed %s" % [r, 85, beast.mob_id, beast.hate.has(p.entity_id)])
			beast.hate.clear()
		beast.set_physics_process(true)
	# an older character chooses once
	p.char_class = "wizard"
	p.race = ""
	p.stats_chosen = true
	main.hud._stats_later = false
	await _wait(0.4)
	print("races: an older character with no race -> the window opens %s, race row %s" % [main.hud._stats_panel.visible, main.hud._stats_race_row.visible])
	await _shot("9zz_races_window")
	World.request_set_stats(p.entity_id, {}, "troll")
	print("races: a wizard asks to be a troll -> race '%s'" % p.race)
	World.request_set_stats(p.entity_id, {}, "gnome")
	World.request_set_stats(p.entity_id, {}, "dark_elf")
	print("races: then a gnome -> '%s'; changing again -> still '%s'; mana %d" % [p.race, p.race, p.max_mana])
	p.race = saved_race
	p.char_class = saved_class
	p.recalc_stats()


## The Group & Tells window takes only group chat and tells: spell, combat
## and system lines stay in the main chat.
func _t_group_window() -> void:
	var hud: Node = get_parent().hud
	var before: int = int(hud._social_lines["all"])
	for pair: Array in [["You begin to use your homeward stone.", World.C_SPELL], ["You feel yourself pulled back to your bind point.", World.C_SPELL],
			["You hit a gnoll pup for 5 points of damage.", World.C_YOU_HIT], ["You have entered Emberhold.", World.C_SYSTEM], ["The rally's fire fades.", World.C_SPELL]]:
		hud.add_log(pair[0], pair[1])
	var after_other: int = int(hud._social_lines["all"])
	hud.add_log("Jewy tells the group, 'sweeet'", World.C_CHAT_GROUP)
	hud.add_log("Jewy tells you, 'meet at the bank'", World.C_CHAT_TELL)
	hud.add_log("You told Jewy, 'on my way'", World.C_CHAT_TELL)
	print("group_window: 5 spell/combat/system lines -> %d in the window; a group line and two tells -> %d" % [after_other - before, int(hud._social_lines["all"]) - after_other])
	hud._group_panel.visible = true
	await _wait(0.3)
	await _shot("9zz_group_window")


## Tooltips wrap: no line of any item's or spell's tooltip runs past ~60
## characters (the Homeward Stone's used to cross the whole screen).
func _t_tooltips() -> void:
	var hud: Node = get_parent().hud
	var longest := ["", 0]
	for id: String in GameData.items:
		for line in (hud._item_tooltip(id) as String).split("\n"):
			if line.length() > int(longest[1]):
				longest = [id, line.length()]
	for id: String in GameData.spells:
		for line in (hud.spell_tooltip(id) as String).split("\n"):
			if line.length() > int(longest[1]):
				longest = [id, line.length()]
	print("tooltips: the longest line in any item or spell tooltip: %d characters (%s)" % [longest[1], longest[0]])
	print("tooltips: the Homeward Stone:\n%s" % hud._item_tooltip("homeward_stone"))


## Group experience reaches members within 10 levels of the highest: a
## level 5 with a level 14 shares, a level 3 with a level 14 doesn't.
func _t_group_xp() -> void:
	var made := []
	for lv: int in [14, 5, 3]:
		var x := Player.new()
		x.from_save({"name": "L%d" % lv, "class": "warrior", "level": lv, "stats": {}, "race": "human"})
		made.append(x)
	var names := World.xp_eligible(made).map(func(x: Player) -> String: return "level %d" % x.level)
	print("group_xp: a group of levels 14, 5 and 3 -> experience for %s" % [names])
	for x: Player in made:
		x.free()


## The one change of race: the sheet's button, a race the class can't be is
## refused, a gnome wizard really gets a gnome's stats and body, and a
## second change is refused and the button gone.
func _t_race_change() -> void:
	var main := get_parent()
	var p := World.local_player
	var hud: Node = main.hud
	p.race = "human"
	p.race_changed = false
	p.look["race"] = "human"
	p.dress()
	hud._toggle_inventory()
	await _wait(0.4)
	print("races: the sheet offers a change %s" % hud._race_button.visible)
	hud._open_race_change()
	await _wait(0.2)
	var open: Array = hud._race_row.get_children().filter(func(b: Button) -> bool: return not b.disabled).map(func(b: Button) -> String: return b.get_meta("race"))
	print("race_change: a wizard may become %s" % [open])
	(hud._race_row.get_child(GameData.races.keys().find("gnome")) as Button).pressed.emit()
	await _shot("9zz_race_change_window")
	hud._race_panel.visible = false
	World.request_change_race(p.entity_id, "troll")
	print("race_change: to a troll -> '%s'" % p.race)
	var mana0 := p.max_mana
	var scale0 := p.visual.scale.x
	World.request_change_race(p.entity_id, "gnome")
	await _wait(0.4)
	print("race_change: to a gnome -> '%s', mana %d -> %d, height %.2f -> %.2f, used up %s" % [p.race, mana0, p.max_mana, scale0, p.visual.scale.x, p.race_changed])
	World.request_change_race(p.entity_id, "dark_elf")
	await _wait(0.4)
	print("race_change: again, to a dark elf -> still '%s'; the button shown %s" % [p.race, hud._race_button.visible])
	p.zoom = 5.0
	await _wait(0.3)
	await _shot("9zz_race_change_gnome")
	hud._toggle_inventory()
	p.race = "human"
	p.race_changed = false
	p.look["race"] = "human"
	p.dress()
	p.recalc_stats()



## Gender: a head swap on the class body, beards for men only, the sheet's one
## change (two clicks), saved and sent in the look.
func _t_gender() -> void:
	var main := get_parent()
	var p := World.local_player
	var hud: Node = main.hud
	p.gender = ""
	p.gender_changed = false
	p.look.erase("gender")
	p.dress()
	var heads := func() -> Array:
		var m := p.visual as CharacterModel
		return m._body_parts().values().filter(func(mi: Node) -> bool: return mi.name.ends_with("Head")).map(func(mi: Node) -> String: return str(mi.name))
	print("gender: a %s from before genders shows as '%s', head %s" % [p.char_class, p.shown_gender(), heads.call()])
	hud._toggle_inventory()
	await _wait(0.4)
	print("gender: the sheet offers '%s' (shown %s)" % [hud._gender_button.text, hud._gender_button.visible])
	hud._gender_button.pressed.emit()
	print("gender: one click -> '%s', still '%s'" % [hud._gender_button.text, p.gender])
	hud._gender_button.pressed.emit()
	await _wait(0.4)
	print("gender: two clicks -> '%s', used up %s, look '%s', head %s, button shown %s" % [p.gender, p.gender_changed, p.look.get("gender"), heads.call(), hud._gender_button.visible])
	World.request_change_gender(p.entity_id, "male")
	print("gender: again -> still '%s'; saved as '%s' / %s" % [p.gender, p.to_save()["gender"], p.to_save()["gender_changed"]])
	var beards := func(g: String) -> int:
		var v := Entity.make_visual({"model": "barbarian", "race": "dwarf", "gender": g}) as CharacterModel
		var n := v.skeleton.find_children("*", "BoneAttachment3D", false, false).size()
		v.free()
		return n
	print("gender: a dwarf's bolt-ons, man %d, woman %d (no beard)" % [beards.call("male"), beards.call("female")])
	var rogue := Entity.make_visual({"model": "rogue", "gender": "male"}) as CharacterModel
	print("gender: a male rogue's head %s" % [rogue._body_parts().values().filter(func(mi: Node) -> bool: return mi.name.ends_with("Head")).map(func(mi: Node) -> String: return str(mi.name))])
	rogue.free()
	hud._toggle_inventory()
	p.zoom = 4.0
	await _wait(0.3)
	await _shot("9zz_gender_female")
	var cc := CharCreate.new()
	cc.layer = 30
	main.add_child(cc)
	await _wait(0.4)
	cc._gender = "female"
	cc._name_edit.text = "Asha"
	cc._deity = "fire"
	var got := []
	cc.confirmed.connect(func(sv: Dictionary) -> void: got.append(sv))
	cc._create()
	print("gender: created %s" % [got[0].get("gender") if not got.is_empty() else "nothing"])
	await _shot("9zz_gender_create")
	cc.queue_free()
	p.gender = ""
	p.gender_changed = false
	p.look.erase("gender")
	p.dress()



## The pet window drags and stays where it's left; a pet whose owner has
## left the world goes too (it used to linger on the server as "<pet>").
func _t_pet_fixes() -> void:
	var main := get_parent()
	var p := World.local_player
	var hud: Node = main.hud
	var saved_class := p.char_class
	var saved_positions: Dictionary = Controls.window_positions.duplicate()
	p.char_class = "magician"
	p.level = 10
	p.recalc_stats()
	World.summon_pet(p, "call_of_earth")
	await _wait(0.6)
	var panel: Control = hud._pet_panel
	var before := panel.global_position
	var press := InputEventMouseButton.new()
	press.button_index = MOUSE_BUTTON_LEFT
	press.pressed = true
	press.global_position = before + Vector2(10, 10)
	panel.gui_input.emit(press)
	var drag := InputEventMouseMotion.new()
	drag.global_position = Vector2(60, 460)
	panel.gui_input.emit(drag)
	var release := press.duplicate() as InputEventMouseButton
	release.pressed = false
	panel.gui_input.emit(release)
	print("pet_fixes: dragged the window %s -> %s, saved %s" % [before, panel.global_position, Controls.window_positions.get("pet")])
	drag.global_position = Vector2(99999, 99999)
	panel.gui_input.emit(press)
	panel.gui_input.emit(drag)
	panel.gui_input.emit(release)
	print("pet_fixes: dragged off screen -> kept at %s (screen %s, window %s)" % [panel.global_position, panel.get_viewport_rect().size, panel.size])
	drag.global_position = Vector2(60, 460)
	panel.gui_input.emit(press)
	panel.gui_input.emit(drag)
	panel.gui_input.emit(release)
	await _shot("9zz_pet_window_moved")
	var pet := World.get_object(p.pet_id) as Pet
	pet.owner_id = 987654  # its owner is gone
	await _wait(0.3)
	print("pet_fixes: a pet with no owner left -> still there %s" % is_instance_valid(pet))
	p.pet_id = -1
	p.pet_spell = ""
	p.char_class = saved_class
	p.recalc_stats()
	Controls.window_positions = saved_positions
	Controls._save_setting("window_positions", saved_positions)



## Every HUD window can be dragged, stays put (the buffs and quest tracker
## stop laying themselves out), and Settings' reset puts them all back.
func _t_drag_windows() -> void:
	var main := get_parent()
	var p := World.local_player
	var hud: Node = main.hud
	var saved_positions: Dictionary = Controls.window_positions.duplicate()
	await _wait(0.4)
	var drag := func(panel: Control, to: Vector2) -> void:
		var press := InputEventMouseButton.new()
		press.button_index = MOUSE_BUTTON_LEFT
		press.pressed = true
		press.global_position = panel.global_position + Vector2(4, 4)
		panel.gui_input.emit(press)
		var move := InputEventMouseMotion.new()
		move.global_position = to + Vector2(4, 4)
		panel.gui_input.emit(move)
		var release := press.duplicate() as InputEventMouseButton
		release.pressed = false
		panel.gui_input.emit(release)
	var windows := {"player": hud._player_panel, "target": hud._target_panel, "quests": hud._quest_panel, "chat": hud._log_panel, "buffs": hud._buff_panel, "group": hud._group_panel}
	var homes := {}
	for key: String in windows:
		homes[key] = (windows[key] as Control).global_position
	var spots := {"player": Vector2(900, 300), "target": Vector2(40, 300), "quests": Vector2(700, 120), "chat": Vector2(1000, 600), "buffs": Vector2(300, 400), "group": Vector2(500, 500)}
	for key: String in windows:
		drag.call(windows[key], spots[key])
	await _wait(0.6)  # the layout code runs every frame: moved windows must stay moved
	for key: String in windows:
		print("drag_windows: %s %s -> %s (asked %s)" % [key, homes[key], (windows[key] as Control).global_position, spots[key]])
	print("drag_windows: saved %s" % [Controls.window_positions.keys()])
	await _shot("9zz_drag_windows")
	UIKit.reset_windows(hud.root)
	await _wait(0.3)
	var back := windows.keys().filter(func(k: String) -> bool:  # anchored as they started (a hidden window's size settles when it shows)
		var c: Control = windows[k]
		var h: Array = c.get_meta("drag_home")
		return c.global_position.distance_to(homes[k]) < 2.0 or [c.anchor_left, c.anchor_top, c.offset_left, c.offset_top] == [h[0], h[1], h[4], h[5]])
	print("drag_windows: reset -> back home %s of %d; saved %s" % [back, windows.size(), Controls.window_positions])
	Controls.window_positions = saved_positions
	Controls._save_setting("window_positions", saved_positions)



## Hair: a style (any KayKit head, any gender) and a color painted on the
## head's hair cells and on beards; picked at creation, restyled once from the
## sheet, saved and sent in the look.
func _t_hair() -> void:
	var main := get_parent()
	var p := World.local_player
	var hud: Node = main.hud
	p.hair_style = ""
	p.hair_color = ""
	p.hair_changed = false
	p.look.erase("hair")
	p.dress()
	var head_color := func() -> Color:  # the hair cell's middle, as painted on the head now
		var m := p.visual as CharacterModel
		var head: MeshInstance3D = m._body_parts().get("Head")
		var mat := (head.material_override if head.material_override != null else head.get_active_material(0)) as BaseMaterial3D
		var img := mat.albedo_texture.get_image()
		if img.is_compressed():
			img.decompress()
		return img.get_pixel(int(img.get_width() * 1.5 / 8), int(img.get_height() / 8))
	var before: Color = head_color.call()
	hud._toggle_inventory()
	await _wait(0.4)
	print("hair: the sheet offers a restyle %s" % hud._hair_button.visible)
	hud._open_hair_change()
	hud._hair_picker.set_hair("flowing", "copper")
	await _shot("9zz_hair_window")
	(hud._hair_panel.find_children("*", "Button", true, false).filter(func(b: Button) -> bool: return b.text == "Change")[0] as Button).pressed.emit()
	await _wait(0.4)
	var after: Color = head_color.call()
	print("hair: restyled -> %s / %s, used up %s, look %s, head %s, hair %s -> %s, button shown %s" % [p.hair_style, p.hair_color, p.hair_changed, p.look.get("hair"),
			(p.visual as CharacterModel)._body_parts()["Head"].name, before.to_html(false), after.to_html(false), hud._hair_button.visible])
	World.request_change_hair(p.entity_id, "short", "black")
	print("hair: again -> still %s / %s; saved %s %s" % [p.hair_style, p.hair_color, p.to_save()["hair"], p.to_save()["hair_changed"]])
	print("hair: cleaned %s %s" % [Player.clean_hair(["mohawk", "copper"]), Player.clean_hair("nonsense")])
	var dwarf := Entity.make_visual({"model": "barbarian", "race": "dwarf", "gender": "male", "hair": ["", "white"]}) as CharacterModel
	var beard: Array = dwarf.skeleton.find_children("*", "MeshInstance3D", true, false).filter(func(mi: MeshInstance3D) -> bool:
		return mi.material_override is BaseMaterial3D and (mi.material_override as BaseMaterial3D).albedo_texture == null)
	print("hair: a white-haired dwarf's beard %s" % [beard.map(func(mi: MeshInstance3D) -> String: return (mi.material_override as BaseMaterial3D).albedo_color.to_html(false))])
	dwarf.free()
	hud._toggle_inventory()
	p.zoom = 4.0
	await _wait(0.3)
	await _shot("9zz_hair_copper")
	var cc := CharCreate.new()
	cc.layer = 30
	main.add_child(cc)
	await _wait(0.4)
	cc._hair.set_hair("long", "white")
	cc._name_edit.text = "Ilyra"
	cc._deity = "light"
	cc._select_race("high_elf")
	var got := []
	cc.confirmed.connect(func(sv: Dictionary) -> void: got.append(sv))
	cc._create()
	print("hair: created %s" % [[got[0].get("hair"), got[0].get("race"), got[0].get("zone"), got[0].get("bind")] if not got.is_empty() else "nothing"])
	await _shot("9zz_hair_create")
	cc.queue_free()
	p.hair_style = ""
	p.hair_color = ""
	p.hair_changed = false
	p.look.erase("hair")
	p.dress()



## Dewstep's one border, Lanternhold's new south gate, both ways.
func _t_dewstep_borders() -> void:
	for leg: Array in [["lanternhold", Vector2(0, 80), Vector2(0, 1), "dewstep"], ["dewstep", Vector2(0, -168), Vector2(0, -1), "lanternhold"]]:
		if not await _walk_border("dewstep_borders", leg[0], leg[1], leg[2], leg[3]):
			return


## Dewstep, Lanternhold's beginner ground: its monsters by day and night, the
## ten quests handed in, and a look at each monster and at the tea house.
func _t_dewstep_life() -> void:
	var z: Zone = get_parent().zone
	var bridge: Array = z.data["landmarks"].filter(func(l: Dictionary) -> bool: return l["type"] == "bridge")[0]["pos"]
	print("dewstep_life: there's water to fish by the bridge %s" % z.fishable_at(float(bridge[0]) + 3.0, float(bridge[1])))
	await _zone_life("dewstep_life", {"headpicker_anjali": ["dewstep_moth_wings", "pilfers_bangle"], "hunter_kaveri": ["jackal_pelts", "cobra_fangs", "amberstripes_fang"],
			"warden_tashi": ["dustpaw_beads", "rattlejaws_necklace"], "brother_ravi": ["wisp_lights", "widows_lantern"]}, ["hungry_ghost", "lantern_widow"],
			["lantern_moth", "paddy_rat", "rice_beetle", "temple_monkey", "monkey_troop_king", "jackal", "hooded_cobra", "young_tiger", "amberstripe",
			"dustpaw_raider", "dustpaw_howler", "chief_rattlejaw", "lantern_wisp", "hungry_ghost", "lantern_widow"])
	var p := World.local_player
	for spot: Array in [[Vector2(10, -118), Vector2(-24, -142), "hub"], [Vector2(-92, -40), Vector2(-110, -52), "shrine"], [Vector2(95, 110), Vector2(124, 143), "dustpaw"], [Vector2(30, 5), Vector2(-20, 70), "paddies"],
			[Vector2(24, 30), Vector2(0, 10), "river"], [Vector2(20, -80), Vector2(42, -104), "tea"], [Vector2(30, 80), Vector2(0, 10), "aerial"]]:
		p.global_position = Vector3(spot[0].x, z.surface_at(spot[0].x, spot[0].y) + 2.0, spot[0].y)
		p.face_toward(Vector3(spot[1].x, 0, spot[1].y))
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 30.0 if spot[2] == "aerial" else 9.0
		p.pitch = -1.1 if spot[2] == "aerial" else -0.2
		await _wait(1.2)
		await _shot("9zv_dewstep_%s" % spot[2])



## A pet's swings show: each kind fights a monster that stands still, and
## what its model plays and how fast it moves are sampled.
func _t_pet_anims() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	var saved_class := p.char_class
	p.char_class = "magician"
	p.level = 20
	p.recalc_stats()
	for spell: String in ["call_of_earth", "call_of_fire"]:
		World.summon_pet(p, spell)
		await _wait(0.5)
		var pet := World.get_object(p.pet_id) as Pet
		var mob := _nearest_mob(p, "gnoll_pup")
		mob.set_physics_process(false)
		mob.max_hp = 100000
		mob.hp = mob.max_hp
		p.global_position = z.ground(mob.global_position.x + 8.0, mob.global_position.z) + Vector3.UP
		pet.global_position = z.ground(mob.global_position.x + 3.0, mob.global_position.z) + Vector3.UP
		World.request_set_target(p.entity_id, mob.entity_id)
		World.request_pet(p.entity_id, "attack")
		var clips := {}
		var moving := 0
		var samples := 0
		for i in 60:
			await _wait(0.1)
			var m := pet.visual as CharacterModel
			clips[m.anim.current_animation] = int(clips.get(m.anim.current_animation, 0)) + 1
			samples += 1
			if Vector2(pet.velocity.x, pet.velocity.z).length() > 0.3:
				moving += 1
		print("pet_anims: %s over 6 s: clips %s, moving %d of %d samples, the pup took %d" % [pet.kind, clips, moving, samples, 100000 - mob.hp])
		await _shot("9zz_pet_anim_%s" % pet.kind)
		World.dismiss_pet(p)
		mob.set_physics_process(true)
	p.char_class = saved_class
	p.recalc_stats()



## AFK: "/afk <message>" and back, the nameplate tag, tells answered, /who,
## going away on its own after config afk_minutes idle, and a key bringing you back.
func _t_afk() -> void:
	var p := World.local_player
	var lines: Array = []
	var grab := func(t: String, _c: Color) -> void: lines.append(t)
	World.log_message.connect(grab)
	World.request_chat(p.entity_id, "/afk gone fishing")
	await _wait(0.2)
	print("afk: /afk gone fishing -> afk %s, nameplate '%s', message '%s'" % [p.afk, p.nameplate.text, p.afk_message])
	World._chat_tell(p, p.display_name, "are you there?")
	World._chat_who(p, false)
	await _wait(0.2)
	print("afk: a tell answered %s; /who marks it %s" % [lines.any(func(l: String) -> bool: return l.ends_with("is AFK: gone fishing")),
			lines.any(func(l: String) -> bool: return l.contains(p.display_name) and l.ends_with("AFK"))])
	await _shot("9zz_afk_tag")
	var key := InputEventKey.new()
	key.pressed = true
	key.keycode = KEY_W
	p._input(key)
	await _wait(0.2)
	print("afk: a key -> afk %s, nameplate '%s'" % [p.afk, p.nameplate.text])
	p._idle = float(World.cfg("afk_minutes", 10)) * 60.0 + 1.0
	await _wait(0.2)
	print("afk: %d idle minutes -> afk %s" % [int(World.cfg("afk_minutes", 10)), p.afk])
	var move := InputEventMouseMotion.new()
	p._input(move)
	await _wait(0.2)
	print("afk: nudging the mouse leaves you away %s (idle reset %s)" % [p.afk, p._idle < 1.0])
	World.request_chat(p.entity_id, "/afk")
	await _wait(0.2)
	print("afk: /afk again -> afk %s" % p.afk)
	World.log_message.disconnect(grab)


## Level cap 35: every class's three new abilities (31/33/35) cast and land.
func _t_cap35() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	print("cap35: max level %d" % int(World.cfg("max_level", 0)))
	var saved_class := p.char_class
	var mob := _nearest_mob(p, "gnoll_scout")
	mob.max_hp = 1000000
	mob.hp = mob.max_hp
	mob.set_physics_process(false)
	for cls: String in GameData.classes:
		p.char_class = cls
		p.level = 35
		p.spells = []
		for sid: String in GameData.spells:
			if int(GameData.spells[sid].get("classes", {}).get(cls, 0)) >= 31:
				p.spells.append(sid)
		p.spells.sort_custom(func(a: String, b: String) -> bool: return str(GameData.spells[a]["type"]) == "pet" and str(GameData.spells[b]["type"]) != "pet")
		if cls == "ranger":
			p.spells.push_front("call_of_the_hawk")
		elif cls == "magician":
			p.spells.push_front("call_of_the_elemental_lord")
		elif cls == "necromancer":
			p.spells.push_front("raise_bone_colossus")
		p.recalc_stats()
		for sk: String in GameData.skills["skills"]:
			if World.skill_cap(p, sk) > 0:
				p.skills[sk] = World.skill_cap(p, sk)
		var out := PackedStringArray()
		for sid: String in p.spells:
			var s: Dictionary = GameData.spells[sid]
			p.cooldowns.clear()
			p.mana = p.max_mana
			p.hp = p.max_hp
			p.hidden = s.get("requires_hidden", false)
			var tgt: Entity = mob
			if str(s.get("target", "")) in ["self", "group", "friendly"]:
				tgt = p
			if str(s["type"]) == "shot":
				p.equipment["range"] = "forgehold_longbow"
				p.pack.add("crude_arrow", 20)
			p.global_position = z.ground(mob.global_position.x + (2.0 if float(s.get("range", 0)) < 5.0 and str(s["type"]) != "shot" else 12.0), mob.global_position.z) + Vector3.UP
			if s.get("from_behind", false) or s.get("requires_hidden", false):
				p.global_position = mob.global_position - (-mob.global_basis.z) * 2.0 + Vector3.UP * 0.5
			p.face_toward(mob.global_position)
			World.request_set_target(p.entity_id, tgt.entity_id)
			var hp0 := mob.hp
			mob.hate.clear()
			mob.auto_attack = false
			World.request_cast(p.entity_id, sid)
			await _wait(float(s.get("cast_time", 0)) + 0.4)
			var what := ""
			match str(s["type"]):
				"damage", "shot", "lifetap":
					what = "hit %d" % (hp0 - mob.hp)
				"dot":
					what = "dot %s" % mob.dots.any(func(d: Dictionary) -> bool: return d["spell"] == sid)
				"buff":
					var on: Entity = World.get_object(p.pet_id) as Entity if str(s.get("target", "")) == "pet" else p
					what = "buff %s" % (on != null and on.buffs.has(sid))
				"heal":
					what = "heal cast"
				"slow":
					what = "slow %d%%" % mob.slow_pct
				"root":
					what = "root %.0f s" % mob.root_left
				"pet":
					var pet := World.get_object(p.pet_id) as Pet
					what = "pet %s (%s, %d hp)" % [pet.display_name if pet else "none", pet.model_id if pet else "", pet.max_hp if pet else 0]
			out.append("%s: %s" % [GameData.spells[sid]["name"], what])
			if str(s["type"]) == "pet":
				await _wait(0.5)
				await _shot("9zz_cap35_%s" % sid)
		mob.dots.clear()
		mob.slow_left = 0.0
		print("cap35: %s -> %s" % [cls, "; ".join(out)])
		World.request_pet(p.entity_id, "leave")
		p.buffs.clear()
		p.hidden = false
		p.equipment.erase("range")
	mob.set_physics_process(true)
	p.char_class = saved_class
	p.level = 1
	p.recalc_stats()
	p.hp = p.max_hp


## The Ashfall's new borders, every one both ways: Cinderpass to The Burn,
## The Burn to Blackglass, Blackglass to Forgehold.
func _t_ashfall35_borders() -> void:
	for leg: Array in [["cinderpass", Vector2(0, -195), Vector2(0, -1), "the_burn"], ["the_burn", Vector2(0, -225), Vector2(0, -1), "blackglass"],
			["blackglass", Vector2(225, 0), Vector2(1, 0), "forgehold"], ["forgehold", Vector2(-80, 0), Vector2(-1, 0), "blackglass"],
			["blackglass", Vector2(0, 225), Vector2(0, 1), "the_burn"], ["the_burn", Vector2(0, 225), Vector2(0, 1), "cinderpass"]]:
		if not await _walk_border("ashfall35_borders", leg[0], leg[1], leg[2], leg[3]):
			return


## The Burn: its monsters, its four quest givers' quests, a look round.
func _t_burn_life() -> void:
	await _zone_life("burn_life", {"warden_dagny": ["giants_coals", "thanes_crown"], "sawyer_mott": ["imp_horns", "bottled_smoke", "cackleflames_crown"],
			"tracker_ilse": ["firehound_manes", "ashmaws_mane"], "ashseer_omari": ["firebird_feathers", "phoenix_ember"]}, [],
			["firehound", "ash_wolf", "firehound_alpha", "fire_imp", "smoke_spirit", "imp_lord", "ember_giant", "ember_giant_thane", "firebird", "phoenix"])
	await _zone_views("burn", [[Vector2(20, 175), Vector2(20, 200), "camp"], [Vector2(-100, 70), Vector2(-140, 60), "tallpine"],
			[Vector2(100, -40), Vector2(145, -70), "giants"], [Vector2(-20, -130), Vector2(-60, -150), "nests"]])


## Blackglass: its monsters by day and night; its quests are given in Forgehold.
func _t_glass_life() -> void:
	var z: Zone = get_parent().zone
	await _zone_life("glass_life", {}, ["glassbound_dead", "glassbound_captain"],
			["glass_golem", "glass_colossus", "obsidian_drake", "obsidian_wyrm", "glass_spider", "glass_brood_queen", "glassbound_dead"])
	await _zone_views("glass", [[Vector2(0, 40), Vector2(-40, -30), "fields"], [Vector2(-110, -100), Vector2(-150, -150), "spires"],
			[Vector2(110, -100), Vector2(150, -140), "spiders"], [Vector2(-100, 80), Vector2(-130, 110), "battlefield"]])


## Forgehold: binding, Agnavar's blessing, the guildmasters, the merchants,
## the Blackglass quests handed in, and a look round the city.
func _t_forgehold() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	print("forgehold: bindstone %s at %s" % [z.data.get("bindstone", false), z.bind_point])
	p.global_position = z.bind_point + Vector3.UP
	World.request_bind(p.entity_id)
	print("forgehold: bound to %s" % p.bind_zone)
	var gms := {}
	var npcs := _npcs()
	for id: String in npcs:
		if GameData.npcs[id].has("guildmaster"):
			gms[GameData.npcs[id]["guildmaster"]["class"]] = npcs[id].display_name
	print("forgehold: guildmasters %s" % [gms])
	var saved_deity := p.deity
	p.deity = "fire"
	_stand_by(p, npcs["flamekeeper_ashani"])
	World.request_say(p.entity_id, "blessing")
	await _wait(0.3)
	print("forgehold: a follower of Agnavar asks for his blessing -> %s" % p.buffs.has("ember_tusk_blessing"))
	p.deity = saved_deity
	p.buffs.erase("ember_tusk_blessing")
	for id: String in ["armorer_gunhild", "weaponsmith_teodor", "provisioner_bettany"]:
		var sells: Array = GameData.npcs[id]["merchant"]["sells"]
		print("forgehold: %s sells %d, unknown %s" % [id, sells.size(), sells.filter(func(i: String) -> bool: return GameData.item(i).is_empty())])
	await _zone_life("forgehold", {"glasswright_uzma": ["glass_cores", "colossus_heart"], "drakewarden_solveig": ["drake_scales", "vitrax_eye"],
			"alchemist_farid": ["glass_silk", "shardmothers_crown"], "captain_ragna": ["glassbound_insignia", "aldrics_banner"]}, [], [])
	await _zone_views("forgehold", [[Vector2(-40, 0), Vector2(0, -10), "plaza"], [Vector2(-50, 10), Vector2(-74, 0), "gate"],
			[Vector2(0, -40), Vector2(0, -88), "mine"], [Vector2(20, 20), Vector2(34, -52), "forges"]])


## Dawnwatch, Mirror Flats, the Silted Reach and Tidemouth: every new border both ways.
func _t_part3_borders() -> void:
	for leg: Array in [["high_terrace", Vector2(0, -225), Vector2(0, -1), "dawnwatch"], ["dawnwatch", Vector2(-195, 0), Vector2(-1, 0), "the_burn"],
			["the_burn", Vector2(225, 0), Vector2(1, 0), "dawnwatch"], ["dawnwatch", Vector2(195, 0), Vector2(1, 0), "mirror_flats"],
			["mirror_flats", Vector2(0, 225), Vector2(0, 1), "the_bleach"], ["the_bleach", Vector2(0, -225), Vector2(0, -1), "mirror_flats"],
			["mirror_flats", Vector2(-225, 0), Vector2(-1, 0), "dawnwatch"], ["dawnwatch", Vector2(0, -195), Vector2(0, -1), "forgehold"],
			["forgehold", Vector2(0, 80), Vector2(0, 1), "dawnwatch"], ["dawnwatch", Vector2(0, 195), Vector2(0, 1), "high_terrace"]]:
		if not await _walk_border("part3_borders", leg[0], leg[1], leg[2], leg[3]):
			return


func _t_part3_borders_monsoon() -> void:
	for leg: Array in [["reedmere", Vector2(0, -225), Vector2(0, -1), "silted_reach"], ["silted_reach", Vector2(225, 0), Vector2(1, 0), "drownfast"],
			["drownfast", Vector2(-225, 0), Vector2(-1, 0), "silted_reach"], ["silted_reach", Vector2(0, -225), Vector2(0, -1), "tidemouth"],
			["tidemouth", Vector2(0, 195), Vector2(0, 1), "silted_reach"], ["silted_reach", Vector2(0, 225), Vector2(0, 1), "reedmere"]]:
		if not await _walk_border("part3_borders", leg[0], leg[1], leg[2], leg[3]):
			return


func _t_dawnwatch_life() -> void:
	await _zone_life("dawnwatch_life", {"marshal_oyelaran": ["stonebrow_tusk_q", "uthraks_war_horn_q"], "beacon_keeper_lior": ["frozen_breath_q", "storm_crown_shard_q"],
			"falconer_mehr": ["roc_feather_q", "sunwing_plume_q"], "chaplain_beatrix": ["sentinels_sunbadge_q", "halvards_sun_banner_q"]}, ["fallen_sentinel", "knight_commander"],
			["stonebrow_ogre", "stonebrow_shaman", "stonebrow_warlord", "roc", "great_roc", "wyvern", "snow_spirit", "avalanche_elemental", "storm_crowned_spirit"])
	await _zone_views("dawnwatch", [[Vector2(0, 80), Vector2(0, 20), "gate"], [Vector2(-20, 0), Vector2(20, -40), "inside"],
			[Vector2(60, 40), Vector2(125, 90), "siege"], [Vector2(0, -110), Vector2(0, -170), "snowfields"]])


func _t_flats_life() -> void:
	await _zone_life("flats_life", {"caravan_guide_rahel": ["nomad_veil_q", "asras_salt_crown_q"], "mirror_scholar_anouk": ["mirror_shard_q", "cracked_mirror_face_q"],
			"saltcutter_bram": ["salt_crab_claw_q", "saltclaws_pearl_q"], "birdwatcher_kiri": ["wader_plume_q", "sky_ray_spine_q"]}, [],
			["mirror_image", "mirage_wisp", "the_reflection", "salt_crab", "brine_swarm", "old_saltclaw", "duneskiff_nomad", "nomad_queen", "salt_wader", "sky_ray", "great_sky_ray"])
	await _zone_views("flats", [[Vector2(0, 170), Vector2(0, 100), "camp"], [Vector2(-10, -10), Vector2(10, -100), "mirror"],
			[Vector2(-100, 60), Vector2(-150, 100), "nomads"], [Vector2(100, 40), Vector2(150, 110), "crabs"]])


func _t_reach_life() -> void:
	await _zone_life("reach_life", {"riverwarden_sione": ["whisker_barbel_q", "river_kings_pearl_crown_q"], "headman_obafemi": ["mud_charm_q", "shell_mask_q"],
			"snakecatcher_anh": ["serpent_scale_q", "coilmothers_fang_q"], "ferryman_cato": ["smugglers_token_q", "blackwaters_ledger_q"]}, [],
			["whiskerfolk", "river_hippo", "river_king", "mudfolk", "mud_shaman", "delta_serpent", "biting_swarm", "great_delta_serpent", "drowned_smuggler", "smuggler_captain"])
	await _zone_views("reach", [[Vector2(10, 220), Vector2(0, 170), "landing"], [Vector2(-40, 40), Vector2(-60, -60), "delta"],
			[Vector2(90, 40), Vector2(130, 90), "mudfolk"], [Vector2(-40, 100), Vector2(-80, 140), "barges"]])


func _t_tidemouth_life() -> void:
	await _zone_life("tidemouth_life", {"harbormaster_quilla": ["reaver_armring_q", "saltbeards_whalebone_crown_q"], "lamplighter_soren": ["bottled_lightning_q", "tempest_heart_q"],
			"diver_makoa": ["clawfolk_pincer_q", "horror_lure_q"], "harpooner_freya": ["sea_serpent_scale_q", "whitefins_fin_q"]}, [],
			["saltreaver", "saltreaver_king", "clawfolk", "deep_horror", "sea_serpent", "giant_gull", "sea_lion", "great_sea_serpent", "harbor_storm_spirit", "tempest_lord"])
	await _zone_views("tidemouth", [[Vector2(20, 100), Vector2(20, 30), "harbor"], [Vector2(0, 0), Vector2(-40, -20), "lighthouse"],
			[Vector2(-90, 100), Vector2(-130, 140), "reavers"], [Vector2(60, -100), Vector2(110, -160), "storm"]])


## Level cap 40: every class's three new abilities (36/38/40) cast and land.
func _t_cap40() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	print("cap40: max level %d" % int(World.cfg("max_level", 0)))
	var saved_class := p.char_class
	var mob := _nearest_mob(p, "gnoll_scout")
	mob.max_hp = 1000000
	mob.hp = mob.max_hp
	mob.set_physics_process(false)
	for cls: String in GameData.classes:
		p.char_class = cls
		p.level = 40
		p.spells = []
		for sid: String in GameData.spells:
			if int(GameData.spells[sid].get("classes", {}).get(cls, 0)) >= 36:
				p.spells.append(sid)
		p.spells.sort_custom(func(a: String, b: String) -> bool: return str(GameData.spells[a]["type"]) == "pet" and str(GameData.spells[b]["type"]) != "pet")
		if cls == "ranger":
			p.spells.push_front("call_of_the_hawk")
		elif cls == "magician":
			p.spells.push_front("call_of_the_elemental_lord")
		elif cls == "necromancer":
			p.spells.push_front("raise_bone_colossus")
		p.recalc_stats()
		for sk: String in GameData.skills["skills"]:
			if World.skill_cap(p, sk) > 0:
				p.skills[sk] = World.skill_cap(p, sk)
		var out := PackedStringArray()
		for sid: String in p.spells:
			var s: Dictionary = GameData.spells[sid]
			p.cooldowns.clear()
			p.mana = p.max_mana
			p.hp = p.max_hp
			p.hidden = s.get("requires_hidden", false)
			var tgt: Entity = mob
			if str(s.get("target", "")) in ["self", "group", "friendly"]:
				tgt = p
			if str(s["type"]) == "shot":
				p.equipment["range"] = "galehold_longbow"
				p.pack.add("crude_arrow", 20)
			p.global_position = z.ground(mob.global_position.x + (2.0 if float(s.get("range", 0)) < 5.0 and str(s["type"]) != "shot" else 12.0), mob.global_position.z) + Vector3.UP
			if s.get("from_behind", false) or s.get("requires_hidden", false):
				p.global_position = mob.global_position - (-mob.global_basis.z) * 2.0 + Vector3.UP * 0.5
			p.face_toward(mob.global_position)
			World.request_set_target(p.entity_id, tgt.entity_id)
			var hp0 := mob.hp
			mob.hate.clear()
			mob.auto_attack = false
			World.request_cast(p.entity_id, sid)
			await _wait(float(s.get("cast_time", 0)) + 0.4)
			var what := ""
			match str(s["type"]):
				"damage", "shot", "lifetap":
					what = "hit %d" % (hp0 - mob.hp)
				"dot":
					what = "dot %s" % mob.dots.any(func(d: Dictionary) -> bool: return d["spell"] == sid)
				"buff":
					var on: Entity = World.get_object(p.pet_id) as Entity if str(s.get("target", "")) == "pet" else p
					what = "buff %s" % (on != null and on.buffs.has(sid))
				"heal":
					what = "heal cast"
				"slow":
					what = "slow %d%%" % mob.slow_pct
				"root":
					what = "root %.0f s" % mob.root_left
				"snare":
					what = "snare %.0f s" % mob.snare_left
				"pet":
					var pet := World.get_object(p.pet_id) as Pet
					what = "pet %s (%s, %d hp)" % [pet.display_name if pet else "none", pet.model_id if pet else "", pet.max_hp if pet else 0]
			out.append("%s: %s" % [GameData.spells[sid]["name"], what])
			if str(s["type"]) == "pet":
				await _wait(0.5)
				await _shot("9zz_cap40_%s" % sid)
		mob.dots.clear()
		mob.slow_left = 0.0
		print("cap40: %s -> %s" % [cls, "; ".join(out)])
		World.request_pet(p.entity_id, "leave")
		p.buffs.clear()
		p.hidden = false
		p.equipment.erase("range")
	mob.set_physics_process(true)
	p.char_class = saved_class
	p.level = 1
	p.recalc_stats()
	p.hp = p.max_hp


## Galehold: binding, Vayuketh's breath, the guildmasters, the merchants, the Long Grass quests.
func _t_cap45() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	print("cap45: max level %d" % int(World.cfg("max_level", 0)))
	var saved_class := p.char_class
	var mob := _nearest_mob(p, "gnoll_scout")
	mob.max_hp = 1000000
	mob.hp = mob.max_hp
	mob.set_physics_process(false)
	for cls: String in GameData.classes:
		p.char_class = cls
		p.level = 45
		p.spells = []
		for sid: String in GameData.spells:
			if int(GameData.spells[sid].get("classes", {}).get(cls, 0)) >= 41:
				p.spells.append(sid)
		p.spells.sort_custom(func(a: String, b: String) -> bool: return str(GameData.spells[a]["type"]) == "pet" and str(GameData.spells[b]["type"]) != "pet")
		if cls == "ranger":
			p.spells.push_front("call_of_the_hawk")
		elif cls == "magician":
			p.spells.push_front("call_of_the_elemental_lord")
		elif cls == "necromancer":
			p.spells.push_front("raise_bone_colossus")
		p.recalc_stats()
		for sk: String in GameData.skills["skills"]:
			if World.skill_cap(p, sk) > 0:
				p.skills[sk] = World.skill_cap(p, sk)
		var out := PackedStringArray()
		for sid: String in p.spells:
			var s: Dictionary = GameData.spells[sid]
			p.cooldowns.clear()
			p.mana = p.max_mana
			p.hp = p.max_hp
			p.hidden = s.get("requires_hidden", false)
			var tgt: Entity = mob
			if str(s.get("target", "")) in ["self", "group", "friendly"]:
				tgt = p
			if str(s["type"]) == "shot":
				p.equipment["range"] = "summit_longbow"
				p.pack.add("crude_arrow", 20)
			p.global_position = z.ground(mob.global_position.x + (2.0 if float(s.get("range", 0)) < 5.0 and str(s["type"]) != "shot" else 12.0), mob.global_position.z) + Vector3.UP
			if s.get("from_behind", false) or s.get("requires_hidden", false):
				p.global_position = mob.global_position - (-mob.global_basis.z) * 2.0 + Vector3.UP * 0.5
			p.face_toward(mob.global_position)
			World.request_set_target(p.entity_id, tgt.entity_id)
			var hp0 := mob.hp
			mob.hate.clear()
			mob.auto_attack = false
			World.request_cast(p.entity_id, sid)
			await _wait(float(s.get("cast_time", 0)) + 0.4)
			var what := ""
			match str(s["type"]):
				"damage", "shot", "lifetap":
					what = "hit %d" % (hp0 - mob.hp)
				"dot":
					what = "dot %s" % mob.dots.any(func(d: Dictionary) -> bool: return d["spell"] == sid)
				"buff":
					var on: Entity = World.get_object(p.pet_id) as Entity if str(s.get("target", "")) == "pet" else p
					what = "buff %s" % (on != null and on.buffs.has(sid))
				"heal":
					what = "heal cast"
				"slow":
					what = "slow %d%%" % mob.slow_pct
				"root":
					what = "root %.0f s" % mob.root_left
				"snare":
					what = "snare %.0f s" % mob.snare_left
				"pet":
					var pet := World.get_object(p.pet_id) as Pet
					what = "pet %s (%s, %d hp)" % [pet.display_name if pet else "none", pet.model_id if pet else "", pet.max_hp if pet else 0]
			out.append("%s: %s" % [GameData.spells[sid]["name"], what])
			if str(s["type"]) == "pet":
				await _wait(0.5)
				await _shot("9zz_cap45_%s" % sid)
		mob.dots.clear()
		mob.slow_left = 0.0
		print("cap45: %s -> %s" % [cls, "; ".join(out)])
		World.request_pet(p.entity_id, "leave")
		p.buffs.clear()
		p.hidden = false
		p.equipment.erase("range")
	mob.set_physics_process(true)
	p.char_class = saved_class
	p.level = 1
	p.recalc_stats()
	p.hp = p.max_hp


## Galehold: binding, Vayuketh's breath, the guildmasters, the merchants, the Long Grass quests.

func _t_cap50() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	print("cap50: max level %d" % int(World.cfg("max_level", 0)))
	var saved_class := p.char_class
	var mob := _nearest_mob(p, "gnoll_scout")
	mob.max_hp = 1000000
	mob.hp = mob.max_hp
	mob.set_physics_process(false)
	for cls: String in GameData.classes:
		p.char_class = cls
		p.level = 50
		p.spells = []
		for sid: String in GameData.spells:
			if int(GameData.spells[sid].get("classes", {}).get(cls, 0)) >= 46:
				p.spells.append(sid)
		p.spells.sort_custom(func(a: String, b: String) -> bool: return str(GameData.spells[a]["type"]) == "pet" and str(GameData.spells[b]["type"]) != "pet")
		if cls == "ranger":
			p.spells.push_front("call_of_the_hawk")
		elif cls == "magician":
			p.spells.push_front("call_of_the_elemental_lord")
		elif cls == "necromancer":
			p.spells.push_front("raise_bone_colossus")
		p.recalc_stats()
		for sk: String in GameData.skills["skills"]:
			if World.skill_cap(p, sk) > 0:
				p.skills[sk] = World.skill_cap(p, sk)
		var out := PackedStringArray()
		for sid: String in p.spells:
			var s: Dictionary = GameData.spells[sid]
			p.cooldowns.clear()
			p.mana = p.max_mana
			p.hp = p.max_hp
			p.hidden = s.get("requires_hidden", false)
			var tgt: Entity = mob
			if str(s.get("target", "")) in ["self", "group", "friendly"]:
				tgt = p
			if str(s["type"]) == "shot":
				p.equipment["range"] = "barrowhold_longbow"
				p.pack.add("crude_arrow", 20)
			p.global_position = z.ground(mob.global_position.x + (2.0 if float(s.get("range", 0)) < 5.0 and str(s["type"]) != "shot" else 12.0), mob.global_position.z) + Vector3.UP
			if s.get("from_behind", false) or s.get("requires_hidden", false):
				p.global_position = mob.global_position - (-mob.global_basis.z) * 2.0 + Vector3.UP * 0.5
			p.face_toward(mob.global_position)
			World.request_set_target(p.entity_id, tgt.entity_id)
			var hp0 := mob.hp
			mob.hate.clear()
			mob.auto_attack = false
			World.request_cast(p.entity_id, sid)
			await _wait(float(s.get("cast_time", 0)) + 0.4)
			var what := ""
			match str(s["type"]):
				"damage", "shot", "lifetap":
					what = "hit %d" % (hp0 - mob.hp)
				"dot":
					what = "dot %s" % mob.dots.any(func(d: Dictionary) -> bool: return d["spell"] == sid)
				"buff":
					var on: Entity = World.get_object(p.pet_id) as Entity if str(s.get("target", "")) == "pet" else p
					what = "buff %s" % (on != null and on.buffs.has(sid))
				"heal":
					what = "heal cast"
				"slow":
					what = "slow %d%%" % mob.slow_pct
				"root":
					what = "root %.0f s" % mob.root_left
				"snare":
					what = "snare %.0f s" % mob.snare_left
				"pet":
					var pet := World.get_object(p.pet_id) as Pet
					what = "pet %s (%s, %d hp)" % [pet.display_name if pet else "none", pet.model_id if pet else "", pet.max_hp if pet else 0]
			out.append("%s: %s" % [GameData.spells[sid]["name"], what])
			if str(s["type"]) == "pet":
				await _wait(0.5)
				await _shot("9zz_cap50_%s" % sid)
		mob.dots.clear()
		mob.slow_left = 0.0
		print("cap50: %s -> %s" % [cls, "; ".join(out)])
		World.request_pet(p.entity_id, "leave")
		p.buffs.clear()
		p.hidden = false
		p.equipment.erase("range")
	mob.set_physics_process(true)
	p.char_class = saved_class
	p.level = 1
	p.recalc_stats()
	p.hp = p.max_hp


## Galehold: binding, Vayuketh's breath, the guildmasters, the merchants, the Long Grass quests.

func _t_galehold() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	print("galehold: bindstone %s at %s" % [z.data.get("bindstone", false), z.bind_point])
	p.global_position = z.bind_point + Vector3.UP
	World.request_bind(p.entity_id)
	print("galehold: bound to %s" % p.bind_zone)
	var gms := {}
	var npcs := _npcs()
	for id: String in npcs:
		if GameData.npcs[id].has("guildmaster"):
			gms[GameData.npcs[id]["guildmaster"]["class"]] = npcs[id].display_name
	print("galehold: guildmasters %s" % [gms])
	var saved_deity := p.deity
	p.deity = "wind"
	_stand_by(p, npcs["windspeaker_sabine"])
	World.request_say(p.entity_id, "blessing")
	await _wait(0.3)
	print("galehold: a follower of Vayuketh asks for his blessing -> %s" % p.buffs.has("vayuketh_breath"))
	p.deity = saved_deity
	p.buffs.erase("vayuketh_breath")
	for id: String in ["armorer_dagmar", "weaponsmith_ansel", "provisioner_maelle"]:
		var sells: Array = GameData.npcs[id]["merchant"]["sells"]
		print("galehold: %s sells %d, unknown %s" % [id, sells.size(), sells.filter(func(i: String) -> bool: return GameData.item(i).is_empty())])
	await _zone_life("galehold", {"plainswarden_hakon": ["horsetail_braid_q", "khans_horsetail_banner_q"], "huntress_zawadi": ["stalker_pelt_q", "tawnyjaws_fang_q"],
			"herdmaster_bolat": ["thunderhoof_horn_q", "herd_kings_horn_q"], "barrowkeeper_moira": ["barrow_bronze_q", "barrow_lords_death_mask_q"]}, [], [])
	await _zone_views("galehold", [[Vector2(40, 0), Vector2(0, -10), "plaza"], [Vector2(60, 10), Vector2(90, 0), "gate"],
			[Vector2(-50, 0), Vector2(-92, 0), "cliff"], [Vector2(20, 30), Vector2(-60, -50), "windmills"]])


## The Standing Sky's borders, every one both ways.
func _t_sky_borders() -> void:
	for leg: Array in [["drownfast", Vector2(0, -225), Vector2(0, -1), "windbreak"], ["windbreak", Vector2(-195, 0), Vector2(-1, 0), "tidemouth"],
			["tidemouth", Vector2(195, 0), Vector2(1, 0), "windbreak"], ["windbreak", Vector2(195, 0), Vector2(1, 0), "the_burn"],
			["the_burn", Vector2(-225, 0), Vector2(-1, 0), "windbreak"], ["windbreak", Vector2(0, -195), Vector2(0, -1), "the_long_grass"],
			["the_long_grass", Vector2(225, 0), Vector2(1, 0), "blackglass"], ["blackglass", Vector2(-225, 0), Vector2(-1, 0), "the_long_grass"],
			["the_long_grass", Vector2(-225, 0), Vector2(-1, 0), "galehold"], ["galehold", Vector2(0, 80), Vector2(0, 1), "tidemouth"],
			["tidemouth", Vector2(0, -195), Vector2(0, -1), "galehold"], ["galehold", Vector2(80, 0), Vector2(1, 0), "the_long_grass"],
			["the_long_grass", Vector2(0, 225), Vector2(0, 1), "windbreak"], ["windbreak", Vector2(0, 195), Vector2(0, 1), "drownfast"]]:
		if not await _walk_border("sky_borders", leg[0], leg[1], leg[2], leg[3]):
			return


func _t_windbreak_life() -> void:
	await _zone_life("windbreak_life", {"scout_leader_emeka": ["kite_silk_q", "tarns_painted_sail_q"], "stonecaller_hild": ["giants_standing_stone_q", "stackstones_capstone_q"],
			"windwatcher_reyes": ["gale_essence_q", "storm_eye_heart_q"], "falconer_ines": ["eagle_talon_q", "skarrows_crest_q"]}, [],
			["kitewing_bandit", "kitewing_chief", "stone_giant", "old_stackstone", "gale_spirit", "dust_devil", "storm_eye", "giant_eagle", "thunderbird", "skarrow_thunderbird", "cliff_drake"])
	await _zone_views("windbreak", [[Vector2(10, 170), Vector2(0, 140), "camp"], [Vector2(-80, -60), Vector2(-130, -110), "bandits"],
			[Vector2(90, -90), Vector2(135, -125), "giants"], [Vector2(0, 60), Vector2(-60, -60), "mesas"]])


func _t_grass_life() -> void:
	await _zone_life("grass_life", {}, ["barrow_wight", "barrow_lord"],
			["grass_stalker", "grass_howler", "tawnyjaw", "thunderhoof", "dirkhorn", "old_thunderhoof", "hoofborn_rider", "hoofborn_archer", "khan_oruk", "barrow_wight"])
	await _zone_views("grass", [[Vector2(-180, 10), Vector2(-100, 30), "entry"], [Vector2(20, 90), Vector2(50, 50), "herds"],
			[Vector2(110, -70), Vector2(150, -100), "hoofborn"], [Vector2(-90, -90), Vector2(-120, -130), "barrows"]])


## The magician's single-target damage line (4 to 29, then Forge Flare at 33):
## each is taught by the guildmasters, casts and lands.
func _t_magician_nukes() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	var saved_class := p.char_class
	p.char_class = "magician"
	var line := ["cinder_dart", "elemental_bolt", "earthen_shard", "scalding_torrent", "spear_of_flame", "storm_javelin", "forge_flare"]
	var taught := World.class_spells("magician").map(func(e: Dictionary) -> String: return str(e["spell"]))
	print("magician_nukes: the guild teaches them all %s" % line.all(func(id: String) -> bool: return id in taught))
	var mob := _nearest_mob(p, "gnoll_scout")
	mob.max_hp = 1000000
	mob.hp = mob.max_hp
	mob.set_physics_process(false)
	var out := PackedStringArray()
	for id: String in line:
		p.level = int(GameData.spells[id]["classes"]["magician"])
		p.spells = [id]
		p.recalc_stats()
		for sk: String in GameData.skills["skills"]:
			if World.skill_cap(p, sk) > 0:
				p.skills[sk] = World.skill_cap(p, sk)
		p.mana = p.max_mana
		p.cooldowns.clear()
		p.global_position = z.ground(mob.global_position.x + 12.0, mob.global_position.z) + Vector3.UP
		p.face_toward(mob.global_position)
		World.request_set_target(p.entity_id, mob.entity_id)
		var hp0 := mob.hp
		mob.hate.clear()
		World.request_cast(p.entity_id, id)
		await _wait(float(GameData.spells[id]["cast_time"]) + 0.4)
		out.append("L%d %s %d" % [p.level, GameData.spells[id]["name"], hp0 - mob.hp])
	print("magician_nukes: %s" % ", ".join(out))
	mob.set_physics_process(true)
	p.char_class = saved_class
	p.level = 1
	p.spells = []
	p.recalc_stats()


## A pet's fight shows in its owner's chat: its hits and misses, and what hits it.
func _t_pet_messages() -> void:
	var p := World.local_player
	var z: Zone = get_parent().zone
	var saved_class := p.char_class
	p.char_class = "magician"
	p.level = 12
	p.recalc_stats()
	World.summon_pet(p, "call_of_earth")
	await _wait(0.4)
	var pet := World.get_object(p.pet_id) as Pet
	var lines: Array = []
	var grab := func(t: String, c: Color) -> void: lines.append([t, c])
	World.log_message.connect(grab)
	var mob := _nearest_mob(p, "gnoll_scout")
	mob.max_hp = 100000
	mob.hp = mob.max_hp
	p.global_position = z.ground(mob.global_position.x + 10.0, mob.global_position.z) + Vector3.UP
	pet.global_position = z.ground(mob.global_position.x + 2.0, mob.global_position.z) + Vector3.UP
	World.request_set_target(p.entity_id, mob.entity_id)
	World.request_pet(p.entity_id, "attack")
	await _wait(8.0)
	World.log_message.disconnect(grab)
	var hits := lines.filter(func(l: Array) -> bool: return str(l[0]).begins_with(pet.display_name) and l[1] == World.C_PET_HIT)
	var hurt := lines.filter(func(l: Array) -> bool: return str(l[0]).contains(" " + pet.display_name + " for") and l[1] == World.C_PET_HURT)
	print("pet_messages: %d of the pet's hits, %d hits on it; e.g. '%s' / '%s'" % [hits.size(), hurt.size(), hits[0][0] if hits else "-", hurt[0][0] if hurt else "-"])
	World.dismiss_pet(p)
	p.char_class = saved_class
	p.level = 1
	p.recalc_stats()


## Agnavar's Hearth and Smokewood: every border both ways.
func _t_hearth_borders() -> void:
	for leg: Array in [["forgehold", Vector2(80, 0), Vector2(1, 0), "agnavars_hearth"], ["agnavars_hearth", Vector2(225, 0), Vector2(1, 0), "smokewood"],
			["smokewood", Vector2(-225, 0), Vector2(-1, 0), "agnavars_hearth"], ["agnavars_hearth", Vector2(0, 225), Vector2(0, 1), "mirror_flats"],
			["mirror_flats", Vector2(0, -225), Vector2(0, -1), "agnavars_hearth"], ["agnavars_hearth", Vector2(-225, 0), Vector2(-1, 0), "forgehold"]]:
		if not await _walk_border("hearth_borders", leg[0], leg[1], leg[2], leg[3]):
			return


func _t_hearth_life() -> void:
	await _zone_life("hearth_life", {"flamewarden_isak": ["court_signet_q", "brannaghs_molten_crown_q"], "pyre_priestess_olusola": ["salamander_scale_q", "scorchtongues_brazier_q"],
			"forge_sage_kalinda": ["heart_of_flame_q", "forgeheart_core_q"], "inquisitor_tobiah": ["heretics_charm_q", "stolen_ember_q"]}, [],
			["ember_court_guard", "ember_giant_queen", "salamander_kin", "salamander_priest", "scorchtongue", "greater_fire_elemental", "living_magma", "living_forgeheart", "fallen_fire_priest", "caldris_unburnt"])
	await _zone_views("hearth", [[Vector2(-170, 10), Vector2(-195, 0), "camp"], [Vector2(0, 30), Vector2(0, -40), "forge"],
			[Vector2(90, -70), Vector2(125, -120), "court"], [Vector2(90, 70), Vector2(125, 110), "salamanders"]])


func _t_smoke_life() -> void:
	await _zone_life("smoke_life", {"woodwarden_sefa": ["ember_heartwood_q", "emberhearts_heart_q"], "hunter_bartek": ["smoke_pelt_q", "ashen_antler_q"],
			"scout_liesl": ["soot_mask_fragment_q", "kolts_antlered_mask_q"], "moth_catcher_ondine": ["fire_moth_dust_q", "moth_queens_wing_q"]}, [],
			["ember_treant", "old_emberheart", "smoke_wolf", "smoke_bear", "smoke_stag", "ashen_stag", "sootmask_cultist", "sootmask_chief", "fire_moth", "walking_fungus", "cinder_moth_queen"])
	await _zone_views("smoke", [[Vector2(-170, 10), Vector2(-190, 0), "camp"], [Vector2(-40, 10), Vector2(10, -10), "treants"],
			[Vector2(100, 30), Vector2(145, 55), "sootmask"], [Vector2(0, 100), Vector2(20, 160), "moths"]])

func _t_sky_borders_2() -> void:
	for leg: Array in [["galehold", Vector2(-80, 0), Vector2(-1, 0), "stonesail"], ["stonesail", Vector2(225, 0), Vector2(1, 0), "galehold"],
			["galehold", Vector2(0, -80), Vector2(0, -1), "vayukeths_step"], ["vayukeths_step", Vector2(195, 0), Vector2(1, 0), "hollow_air"],
			["hollow_air", Vector2(0, 225), Vector2(0, 1), "the_long_grass"], ["the_long_grass", Vector2(0, -225), Vector2(0, -1), "hollow_air"],
			["hollow_air", Vector2(-225, 0), Vector2(-1, 0), "vayukeths_step"], ["vayukeths_step", Vector2(0, 195), Vector2(0, 1), "galehold"]]:
		if not await _walk_border("sky_borders_2", leg[0], leg[1], leg[2], leg[3]):
			return


func _t_stonesail_life() -> void:
	await _zone_life("stonesail_life", {"moorwarden_aldous": ["singing_stone_chip_q", "orlas_tuning_stone_q"], "hunter_wenna": ["moor_hide_q", "skathes_barbed_tail_q"],
			"runecarver_idris": ["rune_shard_q", "thrums_heartstone_q"], "hedge_witch_agathe": ["hags_hair_knot_q", "mirewhistles_ladle_q"]}, [],
			["stone_singer", "cantor_orla", "moor_wolf", "moor_wyvern", "skathe", "menhir", "old_thrum", "bog_hag", "granny_mirewhistle"])
	await _zone_views("stonesail", [[Vector2(170, 10), Vector2(190, 0), "camp"], [Vector2(50, 20), Vector2(0, 0), "circle"],
			[Vector2(30, -110), Vector2(0, -160), "singers"], [Vector2(-100, 90), Vector2(-150, 140), "bog"]])


func _t_hollow_life() -> void:
	await _zone_life("hollow_life", {"skywatcher_imani": ["tempest_mote_q", "hollow_winds_eye_q"], "serpent_hunter_kael": ["serpent_plume_q", "coilclouds_fang_q"],
			"cloudscholar_benedikt": ["cloudstone_q", "hauvars_mist_crown_q"], "bosun_tarrow": ["skyship_sailcloth_q", "mirelas_spyglass_q"]}, [],
			["tempest_elemental", "the_hollow_wind", "sky_serpent", "coilcloud", "cloud_giant", "cloudlord_hauvar", "sky_pirate", "captain_mirela"])
	await _zone_views("hollow", [[Vector2(10, 170), Vector2(0, 190), "camp"], [Vector2(0, 60), Vector2(0, 0), "rift"],
			[Vector2(0, -100), Vector2(0, -170), "hall"], [Vector2(-110, -20), Vector2(-165, -65), "skyship"]])


func _t_step_life() -> void:
	await _zone_life("step_life", {"stairwarden_hesketh": ["titans_thunderstone_q", "vorlaugs_thunder_torc_q"], "sister_mireille": ["temple_bronze_q", "first_guardians_seal_q"],
			"stormrider_kasimir": ["stormscale_q", "elder_drakes_stormheart_q"], "high_windspeaker_obiageli": ["shard_of_broken_breath_q", "fallen_breaths_sigh_q"]}, [],
			["storm_titan", "vorlaug", "sky_guardian", "first_guardian", "thunder_drake", "thunderwing", "fallen_zephyr", "fallen_breath"])
	await _zone_views("step", [[Vector2(10, 160), Vector2(0, 185), "camp"], [Vector2(8, 150), Vector2(0, 60), "stair"],
			[Vector2(0, -120), Vector2(0, -176), "temple"], [Vector2(-80, -60), Vector2(-125, -110), "titans"]])

func _t_bone_borders() -> void:
	for leg: Array in [["hollow_air", Vector2(225, 0), Vector2(1, 0), "fogfall"], ["fogfall", Vector2(0, 225), Vector2(0, 1), "blackglass"],
			["blackglass", Vector2(0, -225), Vector2(0, -1), "fogfall"], ["fogfall", Vector2(225, 0), Vector2(1, 0), "ivory_field"],
			["ivory_field", Vector2(0, 225), Vector2(0, 1), "forgehold"], ["forgehold", Vector2(0, -80), Vector2(0, -1), "ivory_field"],
			["ivory_field", Vector2(225, 0), Vector2(1, 0), "the_unlit"], ["the_unlit", Vector2(0, -225), Vector2(0, -1), "barrowhold"],
			["barrowhold", Vector2(0, 80), Vector2(0, 1), "the_unlit"], ["the_unlit", Vector2(0, 225), Vector2(0, 1), "agnavars_hearth"],
			["agnavars_hearth", Vector2(0, -225), Vector2(0, -1), "the_unlit"], ["the_unlit", Vector2(-225, 0), Vector2(-1, 0), "ivory_field"],
			["ivory_field", Vector2(-225, 0), Vector2(-1, 0), "fogfall"], ["fogfall", Vector2(-225, 0), Vector2(-1, 0), "hollow_air"]]:
		if not await _walk_border("bone_borders", leg[0], leg[1], leg[2], leg[3]):
			return


func _t_fogfall_life() -> void:
	await _zone_life("fogfall_life", {"loremaster_evander": ["tarnished_court_silver_q", "ismays_mourning_veil_q"], "mason_hilde": ["gargoyle_stone_q", "grimwatchs_stone_heart_q"],
			"kennelwarden_osric": ["fog_hound_pelt_q", "whitemaws_collar_q"], "warden_cassia": ["stolen_grave_goods_q", "crowes_black_lantern_q"]}, [],
			["fog_courtier", "fog_knight", "queen_ismay", "fog_gargoyle", "grimwatch", "fog_hound", "whitemaw", "grave_robber", "silas_crowe"])
	await _zone_views("fogfall", [[Vector2(10, 170), Vector2(0, 190), "camp"], [Vector2(0, -60), Vector2(0, -140), "throne"],
			[Vector2(90, -80), Vector2(140, -130), "gargoyles"], [Vector2(100, 60), Vector2(135, 105), "robbers"]])


func _t_ivory_life() -> void:
	await _zone_life("ivory_life", {"bonewarden_adaeze": ["ivory_shard_q", "ossuary_heartbone_q"], "ranger_tomas": ["poached_ivory_q", "vargas_tusk_saw_q"],
			"carrion_hunter_leif": ["carrion_feather_q", "gorgemaws_beak_q"], "sister_imelda": ["ghost_ivory_q", "grandmothers_tusk_q"]}, [],
			["ivory_colossus", "old_ossuary", "ivory_poacher", "tuskmonger_varga", "bone_vulture", "marrow_jackal", "gorgemaw", "herd_spirit", "herd_grandmother"])
	await _zone_views("ivory", [[Vector2(10, 170), Vector2(0, 190), "camp"], [Vector2(30, 0), Vector2(0, -60), "ribcage"],
			[Vector2(110, 60), Vector2(150, 100), "poachers"], [Vector2(-100, -80), Vector2(-140, -130), "herds"]])


func _t_unlit_life() -> void:
	await _zone_life("unlit_life", {"lampwarden_solenne": ["shade_essence_q", "nameless_echo_q"], "nighthunter_kwame": ["shadowhide_q", "starveils_eye_q"],
			"lepidarist_yuna": ["luminous_dust_q", "moon_moths_antenna_q"], "witch_hunter_aurelio": ["morvaine_crest_q", "countess_locket_q"]}, [],
			["shade", "nameless_shade", "night_stalker", "starveil", "moth_giant", "moon_moth", "morvaine_thrall", "morvaine_noble", "countess_morvaine"])
	await _zone_views("unlit", [[Vector2(10, 170), Vector2(0, 190), "camp"], [Vector2(20, 30), Vector2(0, 0), "well"],
			[Vector2(95, -95), Vector2(140, -168), "manor"], [Vector2(-80, 100), Vector2(-120, 130), "moths"]])


func _t_barrowhold() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	print("barrowhold: bindstone %s at %s" % [z.data.get("bindstone", false), z.bind_point])
	p.global_position = z.bind_point + Vector3.UP
	World.request_bind(p.entity_id)
	print("barrowhold: bound to %s" % p.bind_zone)
	var gms := {}
	var npcs := _npcs()
	for id: String in npcs:
		if GameData.npcs[id].has("guildmaster"):
			gms[GameData.npcs[id]["guildmaster"]["class"]] = npcs[id].display_name
	print("barrowhold: guildmasters %s" % [gms])
	var saved_deity := p.deity
	p.deity = "dark"
	_stand_by(p, npcs["umbral_priest_casimir"])
	World.request_say(p.entity_id, "blessing")
	await _wait(0.3)
	print("barrowhold: a follower of Timiraj asks for his blessing -> %s" % p.buffs.has("veil_of_the_unlit"))
	p.deity = saved_deity
	p.buffs.erase("veil_of_the_unlit")
	for id: String in ["armorer_ottilie", "weaponsmith_corvin", "provisioner_ilse"]:
		var sells: Array = GameData.npcs[id]["merchant"]["sells"]
		print("barrowhold: %s sells %d, unknown %s" % [id, sells.size(), sells.filter(func(i: String) -> bool: return GameData.item(i).is_empty())])
	await _zone_views("barrowhold", [[Vector2(0, 50), Vector2(0, -10), "shrine"], [Vector2(0, 40), Vector2(0, 90), "gate"],
			[Vector2(-20, 20), Vector2(40, -80), "observatory"], [Vector2(30, 40), Vector2(-60, -60), "towers"]])

func _t_bone_borders_2() -> void:
	for leg: Array in [["fogfall", Vector2(0, -225), Vector2(0, -1), "lastwalk"], ["lastwalk", Vector2(225, 0), Vector2(1, 0), "timirajs_table"],
			["timirajs_table", Vector2(225, 0), Vector2(1, 0), "barrowhold"], ["barrowhold", Vector2(-80, 0), Vector2(-1, 0), "timirajs_table"],
			["timirajs_table", Vector2(0, 225), Vector2(0, 1), "ivory_field"], ["ivory_field", Vector2(0, -225), Vector2(0, -1), "timirajs_table"],
			["timirajs_table", Vector2(-225, 0), Vector2(-1, 0), "lastwalk"], ["lastwalk", Vector2(0, 225), Vector2(0, 1), "fogfall"]]:
		if not await _walk_border("bone_borders_2", leg[0], leg[1], leg[2], leg[3]):
			return


func _t_lastwalk_life() -> void:
	await _zone_life("lastwalk_life", {"chronicler_mateo": ["godwar_insignia_q", "marshals_broken_standard_q"], "stonewright_freydis": ["petrified_shard_q", "champions_stone_crest_q"],
			"artificer_kanoa": ["divine_bronze_q", "godforged_core_q"], "relic_keeper_wilhelmina": ["stolen_relic_q", "oszkars_relic_crown_q"]}, [],
			["godwar_revenant", "last_marshal", "petrified_warrior", "unmoving_champion", "divine_construct", "godforged_engine", "relic_scavenger", "hierarch_oszkar"])
	await _zone_views("lastwalk", [[Vector2(10, 170), Vector2(0, 190), "camp"], [Vector2(30, 20), Vector2(-40, -60), "battlefield"],
			[Vector2(90, -80), Vector2(130, -130), "constructs"], [Vector2(-100, 70), Vector2(-130, 110), "scavengers"]])


func _t_table_life() -> void:
	var boss: Dictionary = GameData.mobs["the_uninvited"]
	print("table_life: the Uninvited: level %s, hp %d, hits %d-%d, ac %d (a level-51 named: hp %d)" % [boss["level"], int(boss["hp_base"]), int(boss["dmg_min"]), int(boss["dmg_max"]), int(boss["ac"]),
			int(GameData.mobs["astrael"]["hp_base"])])
	await _zone_life("table_life", {"steward_abelard": ["grave_gold_q", "long_table_goblet_q"], "starwatcher_imre": ["star_fragment_q", "astraels_star_heart_q"],
			"kennel_keeper_sabela": ["shadowfur_q", "nightjaws_fang_q"], "high_priestess_nadira": ["blackened_offering_q", "crown_of_the_uninvited_q"]}, [],
			["honored_dead", "lord_of_the_long_table", "star_giant", "astrael", "unlit_hound", "nightjaw", "uninvited_courtier", "the_uninvited"])
	await _zone_views("table", [[Vector2(10, 170), Vector2(0, 190), "camp"], [Vector2(30, 60), Vector2(0, -40), "table"],
			[Vector2(0, -100), Vector2(0, -165), "throne"], [Vector2(100, 80), Vector2(145, 125), "stars"]])

## Swimming: fall off a Rainhold dock into the lagoon, float up to the surface,
## swim, climb back onto a deck; the Swimming skill; /stuck.
func _t_swimming() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	# a deep spot in open water, and one under the city's decks
	var open := Vector2.INF
	var under := Vector2.INF
	for x in range(-40, 50, 2):
		for zz in range(-45, 52, 2):
			var lv := z.swim_level(x, zz)
			if lv == -INF or lv - z.height_at(x, zz) < 1.6:
				continue
			var decked := z.surface_at(x, zz) > z.height_at(x, zz) + 0.5
			if decked and under == Vector2.INF:
				under = Vector2(x, zz)
			elif not decked and open == Vector2.INF:
				open = Vector2(x, zz)
	print("swimming: open water at %s, under a deck at %s" % [open, under])
	p.global_position = Vector3(under.x, z.height_at(under.x, under.y) + 0.3, under.y)  # fell off the dock, down on the bottom
	p.velocity = Vector3.ZERO
	await _wait(2.0)
	var lv := z.swim_level(under.x, under.y)
	print("swimming: under the deck: swimming %s, feet %.2f under the surface (water %.2f deep), clip %s" % [p.swimming, lv - p.global_position.y, lv - z.height_at(under.x, under.y),
			(p.visual as CharacterModel).anim.current_animation if p.visual is CharacterModel else "-"])
	p.global_position = Vector3(open.x, z.height_at(open.x, open.y) + 0.3, open.y)
	await _wait(2.0)
	await _shot("9zs_swimming")
	print("swimming: open water: swimming %s, feet %.2f under the surface" % [p.swimming, z.swim_level(open.x, open.y) - p.global_position.y])
	p.face_toward(Vector3(10, p.global_position.y, 0))
	Input.action_press("move_forward")  # a few strokes out across the lagoon
	await _wait(1.2)
	var stroke: String = (p.visual as CharacterModel).anim.current_animation if p.visual is CharacterModel else "-"
	await _shot("9zs_stroke")
	Input.action_release("move_forward")
	print("swimming: swimming forward: clip %s, speed %.1f (a run is %.1f)" % [stroke, Vector2(p.velocity.x, p.velocity.z).length(), Player.RUN_SPEED])
	# climb out: face the nearest deck edge from the open water and swim at it
	var edge := Vector2.INF
	for k in 72:
		var d := Vector2.from_angle(k * TAU / 72.0)
		for r in range(1, 30):
			var q := open + d * r
			if z.surface_at(q.x, q.y) > z.height_at(q.x, q.y) + 0.5:
				if edge == Vector2.INF or open.distance_to(q) < open.distance_to(edge):
					edge = q
				break
	var dir := Vector3(edge.x - open.x, 0, edge.y - open.y).normalized()
	p.global_position = Vector3(edge.x, 0, edge.y) - dir * 1.2
	p.global_position.y = z.swim_level(edge.x, edge.y) - Entity.FLOAT_DEPTH
	p.face_toward(p.global_position + dir)
	await _wait(0.5)
	var climbed := p.climb_out(dir)
	await _wait(0.5)
	print("swimming: climb out at a deck edge %s -> %s, now %.2f above the water, swimming %s" % [edge, climbed, p.global_position.y - z.swim_level(edge.x, edge.y), p.swimming])
	await _shot("9zs_climbed")
	# the skill
	p.skills["swimming"] = 0
	var slow := p.swim_speed_share()
	p.global_position = Vector3(open.x, z.swim_level(open.x, open.y) - Entity.FLOAT_DEPTH, open.y)
	await _wait(0.5)
	for k in 40:
		World._check_swim(p, 5.1)
	print("swimming: skill 0 -> %d after 40 tries (cap %d); speed %.2f of a run untrained, %.2f now" % [int(p.skills.get("swimming", 0)), World.skill_cap(p, "swimming"), slow, p.swim_speed_share()])
	World.request_sit(p.entity_id, true)
	print("swimming: sitting in the water -> %s" % p.sitting)
	# /stuck from under the deck
	p.global_position = Vector3(under.x, z.height_at(under.x, under.y) + 0.3, under.y)
	p.cooldowns.erase("stuck")
	await _wait(1.0)
	World.request_chat(p.entity_id, "/stuck")
	await _wait(1.0)
	var at := Vector2(p.global_position.x, p.global_position.z)
	print("swimming: /stuck -> %s, dry %s, swimming %s" % [at, z.swim_level(at.x, at.y) == -INF, p.swimming])
	World.request_chat(p.entity_id, "/stuck")
	await _wait(0.3)

## Street-level views of a town, to see what stands in the way (TOWN_VIEWS="fx,fz,lx,lz;...").
func _t_town_views() -> void:
	var spots := []
	for s: String in OS.get_environment("TOWN_VIEWS").split(";", false):
		var v := s.split(",")
		spots.append([Vector2(float(v[0]), float(v[1])), Vector2(float(v[2]), float(v[3])), "v%d" % spots.size()])
	await _zone_views("town", spots)
	if OS.get_environment("TOP_AT") != "":  # and a look straight down on it
		var z: Zone = get_parent().zone
		var cam := Camera3D.new()
		cam.projection = Camera3D.PROJECTION_ORTHOGONAL
		cam.size = float(OS.get_environment("TOP_SIZE")) if OS.get_environment("TOP_SIZE") != "" else 60.0
		z.add_child(cam)
		var c := OS.get_environment("TOP_AT").split(",")
		cam.global_position = Vector3(float(c[0]), 80.0, float(c[1]))
		cam.rotation_degrees = Vector3(-90, 0, 0)
		cam.make_current()
		await _wait(0.5)
		await _shot("9zt_top_%s" % z.zone_id)
		cam.queue_free()

## Rainhold's porches: from the street in front of each guildmaster and merchant,
## walk straight at them; can you get close?
func _t_porch_reach() -> void:
	var p := World.local_player
	var z: Zone = get_parent().zone
	var npcs := _npcs()
	var stuck := PackedStringArray()
	for id: String in npcs:
		var n: Npc = npcs[id]
		if GameData.npcs[id].has("guard") or absf(n.global_position.z) < 3.0 or absf(n.global_position.z) > 8.0 or n.global_position.x < -13.0:
			continue  # the porch rows only (z about +-5.5); the far west end, behind the shrine, is walked below
		var start := Vector3(n.global_position.x, 0, 0.0)
		p.global_position = Vector3(start.x, z.surface_at(start.x, start.z) + 0.3, start.z)
		p.velocity = Vector3.ZERO
		await _wait(0.2)
		var t := 0.0
		while t < 4.0 and Vector2(n.global_position.x - p.global_position.x, n.global_position.z - p.global_position.z).length() > 1.2:
			var d := Vector3(n.global_position.x - p.global_position.x, 0, n.global_position.z - p.global_position.z).normalized()
			p.velocity.x = d.x * Player.RUN_SPEED
			p.velocity.z = d.z * Player.RUN_SPEED
			p.velocity.y -= 22.0 * get_physics_process_delta_time()
			p.move_and_slide()
			await get_tree().physics_frame
			t += get_physics_process_delta_time()
		var dist := Vector2(n.global_position.x - p.global_position.x, n.global_position.z - p.global_position.z).length()
		print("porch_reach: %s: %.1f m away" % [n.display_name, dist])
		if dist > 1.5:
			stuck.append(n.display_name)
	print("porch_reach: blocked %s" % [stuck])
	# the far ends: along the porch, and round the shrine to the tidepriest
	for route: Array in [[Vector2(-9, -3), Vector2(-9, -5.5), Vector2(-18, -5.5)], [Vector2(-7.5, 2), Vector2(-7.5, 4.8), Vector2(-16.5, 5.0), Vector2(-16.5, 6.5)]]:
		p.global_position = Vector3(route[0].x, z.surface_at(route[0].x, route[0].y) + 0.3, route[0].y)
		p.velocity = Vector3.ZERO
		await _wait(0.2)
		for w: Vector2 in route.slice(1):
			var t := 0.0
			while t < 4.0 and Vector2(w.x - p.global_position.x, w.y - p.global_position.z).length() > 0.4:
				var d := Vector3(w.x - p.global_position.x, 0, w.y - p.global_position.z).normalized()
				p.velocity.x = d.x * Player.RUN_SPEED
				p.velocity.z = d.z * Player.RUN_SPEED
				p.velocity.y -= 22.0 * get_physics_process_delta_time()
				p.move_and_slide()
				await get_tree().physics_frame
				t += get_physics_process_delta_time()
		var end: Vector2 = route[-1]
		print("porch_reach: route to %s: ended %.1f m off, on the deck %s" % [end, Vector2(end.x - p.global_position.x, end.y - p.global_position.z).length(),
				absf(p.global_position.y - z.surface_at(p.global_position.x, p.global_position.z)) < 0.5])

## Frame hitches: run around the zone for a while and log every slow frame (STUTTER_SECONDS, default 20).
func _t_stutter() -> void:
	var p := World.local_player
	var secs := float(OS.get_environment("STUTTER_SECONDS")) if OS.get_environment("STUTTER_SECONDS") != "" else 20.0
	Input.action_press("move_forward")
	var t := 0.0
	var spikes := PackedStringArray()
	var frames := 0
	var turn := 0.0
	var still := 0  # frames the camera didn't move although we were running
	var moving := 0
	var last_cam := p.camera.global_position
	while t < secs:
		var before := Time.get_ticks_usec()
		await get_tree().process_frame
		if t > 1.0 and Vector2(p.velocity.x, p.velocity.z).length() > 2.0 and p.camera.global_position.distance_to(last_cam) < 0.001:
			still += 1
		if t > 1.0 and Vector2(p.velocity.x, p.velocity.z).length() > 2.0:
			moving += 1
		last_cam = p.camera.global_position
		var ms := (Time.get_ticks_usec() - before) / 1000.0
		t += ms / 1000.0
		frames += 1
		turn += ms / 1000.0
		if turn > 3.0:
			turn = 0.0
			p.rotate_y(1.3)  # keep running round the zone, not into the mountains
		if ms > 25.0:
			spikes.append("%.1fs:%.0fms" % [t, ms])
	Input.action_release("move_forward")
	print("stutter: %s: %d frames in %.0f s (%.0f fps), %d over 25 ms: %s" % [get_parent().zone.zone_id, frames, t, frames / t, spikes.size(), ", ".join(spikes)])
	print("stutter: the camera stood still on %d frames while running (%.0f%%)" % [still, 100.0 * still / maxf(1.0, moving)])


## Screenshots from a few spots: [from, looking at, name].
func _zone_views(tag: String, spots: Array) -> void:
	var p := World.local_player
	var z: Zone = get_parent().zone
	for spot: Array in spots:
		p.global_position = Vector3(spot[0].x, z.surface_at(spot[0].x, spot[0].y) + 2.0, spot[0].y)
		p.face_toward(Vector3(spot[1].x, 0, spot[1].y))
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 9.0
		p.pitch = -0.2
		await _wait(1.2)
		await _shot("9zw_%s_%s" % [tag, spot[2]])


## Reedmere and Drownfast's three borders, every one both ways.
func _t_monsoon_west_borders() -> void:
	for leg: Array in [["weeping_throat", Vector2(-195, 0), Vector2(-1, 0), "reedmere"], ["reedmere", Vector2(225, 0), Vector2(1, 0), "weeping_throat"],
			["weeping_throat", Vector2(0, -195), Vector2(0, -1), "drownfast"], ["drownfast", Vector2(225, 0), Vector2(1, 0), "cinderpass"],
			["cinderpass", Vector2(-195, 0), Vector2(-1, 0), "drownfast"], ["drownfast", Vector2(0, 225), Vector2(0, 1), "weeping_throat"]]:
		if not await _walk_border("monsoon_west_borders", leg[0], leg[1], leg[2], leg[3]):
			return


## A zone's life: its monsters by day and night, each quest giver's quests
## handed in (twice for the repeatable ones), and a look at each monster.
func _zone_life(tag: String, givers: Dictionary, night_ids: Array, look_ids: Array) -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	World.time_override = 12.0
	await _wait(0.5)
	var counts := {}
	for m in World.get_mobs():
		counts[m.mob_id] = int(counts.get(m.mob_id, 0)) + 1
	print("%s: noon: %d monsters %s" % [tag, World.get_mobs().size(), counts])
	p.level = 30
	p.recalc_stats()
	p.pack.clear()
	var npcs := _npcs()
	var done := {}
	for giver: String in givers:
		var npc: Npc = npcs[giver]
		for i in p.pack.slots.size():  # room for the next giver's hand-ins (rewards pile up)
			p.pack.slots[i] = {}
		_stand_by(p, npc)
		World.request_say(p.entity_id, "hail")
		for q_id: String in givers[giver]:
			var q: Dictionary = GameData.quests[q_id]
			World.request_say(p.entity_id, str(q["start_keyword"]))
			for round in (2 if q.get("repeatable", false) else 1):
				for item_id: String in q["wants"]:
					p.pack.add(item_id, int(q["wants"][item_id]))
				_stand_by(p, npc)
				await _hand_in(p, npc, (q["wants"] as Dictionary).keys())
			done[q_id] = int(p.quests.get(q_id, {}).get("completions", 0))
	await _wait(0.3)
	print("%s: quests done %s" % [tag, done])
	World.time_override = 23.0
	await _wait(0.6)
	var night := {}
	for m in World.get_mobs():
		if m.mob_id in night_ids:
			night[m.mob_id] = int(night.get(m.mob_id, 0)) + 1
	print("%s: at 23:00 %s" % [tag, night])
	World.time_override = 12.0
	main.hud._inv_panel.visible = false
	for id: String in look_ids:
		var m: Mob = _nearest_mob(p, id)
		if m == null:
			print("%s: no %s found" % [tag, id])
			continue
		m.set_physics_process(false)
		var at := m.global_position
		p.global_position = Vector3(at.x + 4.0, z.surface_at(at.x + 4.0, at.z + 3.0) + 1.0, at.z + 3.0)
		p.face_toward(at)
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 5.5
		p.pitch = -0.15
		await _wait(0.8)
		await _shot("9zm_%s" % id)
		m.set_physics_process(true)


func _t_reedmere_life() -> void:
	var z: Zone = get_parent().zone
	print("reedmere_life: water at the middle %.1f over ground %.1f; Veyamar's decks stand at %.1f" % [z.water_level(0, -60), z.height_at(0, -60), z.surface_at(-10, 20)])
	await _zone_life("reedmere_life", {"reedcutter_pallavi": ["pondkin_fetishes", "bloatking_crown"], "boatwright_kesh": ["reedstalker_plumes", "stilt_legs_plume"],
			"priestess_amrit": ["sunken_charms", "headwomans_lotus", "marrowroot_heart"]}, ["sunken_villager", "sunken_headwoman"],
			["pondkin", "pondkin_mudcaller", "pondkin_bloatking", "reedstalker", "old_stilt_legs", "marsh_eel", "bogwing", "sunken_villager", "sedge_sister", "bog_lurker", "mother_marrowroot"])
	var p := World.local_player
	for spot: Array in [[Vector2(236, 20), Vector2(210, 0), "rest"], [Vector2(30, 60), Vector2(-10, 20), "veyamar"], [Vector2(-100, -80), Vector2(-130, -115), "pondkin"], [Vector2(-110, 150), Vector2(-140, 125), "coven"]]:
		p.global_position = Vector3(spot[0].x, z.surface_at(spot[0].x, spot[0].y) + 2.0, spot[0].y)
		p.face_toward(Vector3(spot[1].x, 0, spot[1].y))
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 9.0
		p.pitch = -0.2
		await _wait(1.0)
		await _shot("9zn_reedmere_%s" % spot[2])


func _t_drownfast_life() -> void:
	var z: Zone = get_parent().zone
	print("drownfast_life: water %.1f; the south causeway at %.1f, the east causeway at %.1f, the throne platform at %.1f" % [z.water_level(0, 100), z.surface_at(0, 100), z.surface_at(120, -10), z.surface_at(0, 13)])
	await _zone_life("drownfast_life", {"tidewarden_nkemi": ["tidesworn_insignias", "varundra_crown"], "pearl_diver_suriya": ["naga_scales", "sessavi_pearl"],
			"stormsage_obi": ["tempest_shards", "wardens_chain", "chitterjaw_claw"]}, [],
			["tidesworn", "tide_knight", "tideking_varundra", "naga_warrior", "naga_tidecaller", "naga_queen", "tempest_spirit", "stormbound_warden", "causeway_crab", "shellback", "old_chitterjaw"])
	var p := World.local_player
	for spot: Array in [[Vector2(20, 236), Vector2(0, 210), "camp"], [Vector2(12, 90), Vector2(0, -30), "causeway"], [Vector2(-100, -30), Vector2(-145, -60), "naga"], [Vector2(40, -110), Vector2(0, -150), "tower"]]:
		p.global_position = Vector3(spot[0].x, z.surface_at(spot[0].x, spot[0].y) + 2.0, spot[0].y)
		p.face_toward(Vector3(spot[1].x, 0, spot[1].y))
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 9.0
		p.pitch = -0.2
		await _wait(1.0)
		await _shot("9zn_drownfast_%s" % spot[2])


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
	var p := World.local_player
	var z: Zone = get_parent().zone
	World.time_override = 12.0
	p.global_position = z.ground(-27, -20) + Vector3.UP
	p.face_toward(z.ground(-32, -32))
	p.camera_pivot.rotation.y = 0.0
	p.zoom = 8.0
	p.pitch = -0.15
	await _wait(1.0)
	await _shot("9zz_mausoleum")
	World.time_override = -1.0
	if await _walk_border("crypt_door", "emberhold", Vector2(-32, -25), Vector2(0, -1), "emberhold_crypt"):
		await _walk_border("crypt_door", "emberhold_crypt", Vector2(0, 5), Vector2(0, 1), "emberhold")


## The balance simulator (scripts/dev/balance_sim.gd): every class against
## typical monsters at levels 5-25. Long; run it on its own, headless is fine.
func _t_balance() -> void:
	await load("res://scripts/dev/balance_sim.gd").new().run(self)


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
	# a wilderness zone may have grown since the leg was written: start 20 m short of its zone line
	for zl: Dictionary in main.zone.data.get("zone_lines", []):
		var at := Vector2(zl["pos"][0], zl["pos"][1])
		if str(zl["to"]) == to_zone and start.distance_to(at) > 45.0 and not main.zone.data.get("bindstone", false):
			start = at - dir * 20.0
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
	for leg: Array in [["sunward_steps", Vector2(0, -196), Vector2(0, -1), "the_bleach"], ["the_bleach", Vector2(0, 226), Vector2(0, 1), "sunward_steps"]]:
		if not await _walk_border("bleach_border", leg[0], leg[1], leg[2], leg[3]):
			return


## The Bleach: the salt flats, the caravan camp, the titan's bones, the raider camp.
func _t_bleach() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	World.time_override = 11.0
	var patches: Array = z.data["ground_patches"]
	print("bleach: salt flat %s, mud %s, open ground %s" % [z.on_bare_patch(patches[0]["pos"][0], patches[0]["pos"][1]), z.on_bare_patch(patches[1]["pos"][0], patches[1]["pos"][1]),
			z.on_bare_patch(-z.half * 0.7, z.half * 0.7)])
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
	for leg: Array in [["sunward_steps", Vector2(200, 0), Vector2(1, 0), "lanternhold"], ["lanternhold", Vector2(-84, 0), Vector2(-1, 0), "sunward_steps"]]:
		if not await _walk_border("lanternhold_border", leg[0], leg[1], leg[2], leg[3]):
			return


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
	p.coin = 1000 * 1000  # 1000 platinum
	await _wait(1.3)
	print("encumbrance: 1000 platinum on hand -> %.1f of %d, speed x%.2f; told '%s'" % [p.carried_weight(), int(p.carry_capacity()), p.encumbrance_speed(),
			said.filter(func(t: String) -> bool: return "burden" in t).back() if said.any(func(t: String) -> bool: return "burden" in t) else "-"])
	p.coin = 1600 * 1000
	said.clear()
	World.request_sprint(p.entity_id, true)
	print("encumbrance: 1600 platinum -> speed x%.2f; sprinting %s (%s)" % [p.encumbrance_speed(), p.sprinting, said.back() if not said.is_empty() else "-"])
	p.bank_coin += p.coin  # the banker's vault weighs nothing
	p.coin = 0
	await _wait(1.3)
	print("encumbrance: banked -> %.1f, speed x%.2f; told '%s'" % [p.carried_weight(), p.encumbrance_speed(), said.back() if not said.is_empty() else "-"])
	World.log_message.disconnect(listen)
	p.bank_coin = 0
	p.char_class = saved_class
	p.level = 1
	p.recalc_stats()


## What keeps a server's idle zone up (main._watch_idle_zones): Zone.keep_reason
## must name anything that taking the zone down and building it again would
## lose, and idle_seconds_to_unload must wait out its slowest respawn. Steps
## the player out of the zone for a moment to see the zone as a server would.
func _t_zone_unload() -> void:
	var z: Zone = get_parent().zone
	for k in 120:
		if z.nav_ready:
			break
		await _wait(0.25)
	var p := World.local_player
	print("zone_unload: player here -> '%s' (want 'occupied')" % z.keep_reason())
	var pos := p.global_position
	z.remove_child(p)
	print("zone_unload: nobody here -> '%s' (want '')" % z.keep_reason())
	var g := GroundItem.new()
	g.entry = {"item": "gnoll_fang", "count": 1}
	z.add_child(g)
	print("zone_unload: a dropped item -> '%s' (want 'a dropped item')" % z.keep_reason())
	z.remove_child(g)
	g.free()
	var mine := Corpse.new()
	mine.setup("Tester", {}, [], 0, 60.0, "Tester")
	z.add_child(mine)
	print("zone_unload: a player corpse -> '%s' (want 'a player corpse')" % z.keep_reason())
	z.remove_child(mine)
	mine.free()
	var mobs := Corpse.new()
	mobs.setup("a gnoll pup", {}, [], 0, 60.0)
	z.add_child(mobs)
	print("zone_unload: a monster's corpse -> '%s' (want '')" % z.keep_reason())
	z.remove_child(mobs)
	mobs.free()
	z.add_player(p, pos)
	var slowest := 0.0
	for child in z.get_children():
		if child is SpawnPoint:
			slowest = maxf(slowest, (child as SpawnPoint).respawn_time)
	print("zone_unload: slowest respawn %.0f s -> waits %.0f s empty (want max(900, %.0f))" % [slowest, z.idle_seconds_to_unload(900.0), slowest * 1.15 + 60.0])
	print("zone_unload: player back -> '%s' (want 'occupied')" % z.keep_reason())


## The Grove: the seed takes you there, the gods show only once earned, they
## can't be fought or reached when unseen, and the keeper walks you back.
func _t_grove() -> void:
	var main := get_parent()
	var p := World.local_player
	var zone_now := func() -> String: return (main.zone as Zone).zone_id
	var wait_zone := func(zone_id: String) -> void:
		for k in 80:
			if zone_now.call() == zone_id and not main._changing_zone:
				break
			await _wait(0.25)
		await _wait(0.8)
	p.grove_deities.clear()
	p.global_position = Vector3(20, main.zone.height_at(20, 30) + 1.0, 30)
	await _wait(0.3)
	var from := p.global_position
	World.request_chat(p.entity_id, "/grove seed")
	await _wait(0.2)
	print("grove: /grove seed -> carry a seed %s" % ("grove_seed" in p.owned_item_ids()))
	World.request_use_item(p.entity_id, _where(p, "grove_seed"))
	await _wait(10.6)
	await wait_zone.call("the_grove")
	var z := main.zone as Zone
	print("grove: seed -> now in %s, %.1f m from the arch's arrival; remembers %s" % [zone_now.call(),
			Vector2(p.global_position.x, p.global_position.z).distance_to(Vector2(z.bind_point.x, z.bind_point.z)), p.grove_return])
	await _wait(0.8)
	var npcs := _npcs()
	var shown := func() -> Array:
		var out: Array = []
		for id: String in npcs:
			var n := npcs[id] as Npc
			if n.grove_deity != "" and n.visual.visible:
				out.append(id)
		out.sort()
		return out
	print("grove: nothing earned -> shown %s" % [shown.call()])
	var god: Npc = npcs["grove_light"]
	var hidden_god: Npc = npcs["grove_water"]
	_stand_by(p, hidden_god)
	World.request_set_target(p.entity_id, hidden_god.entity_id)
	print("grove: target the unseen Jalendra -> target %s" % (p.target.display_name if p.target != null else "none"))
	World.request_chat(p.entity_id, "/grove unlock light")
	await _wait(0.8)
	print("grove: unlocked light -> shown %s" % [shown.call()])
	_stand_by(p, god)
	World.request_set_target(p.entity_id, god.entity_id)
	World.request_hail(p.entity_id)
	World.request_toggle_attack(p.entity_id)
	World.request_toggle_attack(p.entity_id)
	print("grove: hail Prabhagaj -> target %s; attack twice -> auto attack %s, hostile %s" % [p.target.display_name if p.target != null else "none", p.auto_attack, p.hostile_npcs.has(god.entity_id)])
	print("grove: save keeps %s" % [p.to_save().get("grove")])
	# every god, for the pictures
	World.request_chat(p.entity_id, "/grove unlock all")
	await _wait(1.0)
	print("grove: unlocked all -> shown %s" % [shown.call()])
	p.global_position = Vector3(z.bind_point.x, z.bind_point.y + 1.0, z.bind_point.z)
	p.face_toward(Vector3(0, 0, 0))
	p.camera_pivot.rotation.y = 0.0
	p.zoom = 9.0
	p.pitch = -0.12
	await _wait(1.5)
	await _shot("9grove_arrival")
	p.global_position = Vector3(0, z.surface_at(0, 30) + 1.0, 30)
	p.face_toward(Vector3(0, 0, -37))
	p.zoom = 12.0
	p.pitch = -0.18
	await _wait(1.2)
	await _shot("9grove_pond")
	for d: String in ["water", "fire", "wind", "dark", "light"]:
		var g: Npc = npcs["grove_" + d]
		var toward := Vector3(g.global_position.x, 0, g.global_position.z)
		var stand := toward * (22.0 / maxf(toward.length(), 1.0))
		p.global_position = Vector3(stand.x, z.surface_at(stand.x, stand.z) + 1.0, stand.z)
		p.face_toward(g.global_position)
		p.zoom = 7.0
		p.pitch = 0.05
		await _wait(0.8)
		await _shot("9grove_god_" + d)
	World.request_chat(p.entity_id, "/grove lock all")
	await _wait(0.8)
	print("grove: locked all -> shown %s" % [shown.call()])
	var keeper: Npc = npcs["grove_keeper"]
	_stand_by(p, keeper)
	World.request_set_target(p.entity_id, keeper.entity_id)
	World.request_say(p.entity_id, "return")
	await wait_zone.call("greenmoor")
	print("grove: keeper, return -> now in %s, %.1f m from where the seed was used" % [zone_now.call(), Vector2(p.global_position.x, p.global_position.z).distance_to(Vector2(from.x, from.z))])


## Social emotes: the lines (alone, at a target, a word-only one, an alias,
## /em), the clip each plays, and walking off cutting one short.
func _t_emotes() -> void:
	var p := World.local_player
	var lines: Array = []
	var grab := func(t: String, _c: Color) -> void: lines.append(t)
	World.log_message.connect(grab)
	var merrick: Npc = _npcs()["merrick"]
	p.target = null
	World.request_chat(p.entity_id, "/wave")
	await _wait(0.8)
	_stand_by(p, merrick)
	World.request_chat(p.entity_id, "/rude")
	await _wait(0.8)
	World.request_chat(p.entity_id, "/hello")
	await _wait(0.8)
	World.request_chat(p.entity_id, "/smile")
	await _wait(0.8)
	World.request_chat(p.entity_id, "/em juggles three apples.")
	World.request_chat(p.entity_id, "/notanemote")
	await _wait(0.2)
	World.log_message.disconnect(grab)
	print("emotes: lines %s" % [lines])
	var m := p.visual as CharacterModel
	p.target = null
	p.face_toward(p.global_position + Vector3(0, 0, 10))
	p.camera_pivot.rotation.y = PI  # look at the player's face
	p.zoom = 5.0
	p.pitch = -0.1
	var missing: Array = []
	for id: String in GameData.emotes:
		var e: Dictionary = GameData.emotes[id]
		if not e.has("anim"):
			continue
		if not m.anim.has_animation(str(e["anim"])):
			missing.append(e["anim"])
			continue
		await _wait(0.8)
		World.request_emote(p.entity_id, id)
		await _wait(minf(1.2, m.anim.get_animation(str(e["anim"])).length * 0.45))
		print("emotes: /%s -> playing %s" % [id, m.anim.current_animation])
		await _shot("9emote_" + id)
		await _wait(m._one_shot_left + 0.3)
	print("emotes: clips missing %s" % [missing])
	# walking off stops a dance
	await _wait(0.8)
	World.request_emote(p.entity_id, "dance")
	await _wait(0.5)
	var before := m.anim.current_animation
	Input.action_press("move_forward")
	await _wait(0.4)
	Input.action_release("move_forward")
	print("emotes: dancing (%s), walked off -> now %s" % [before, m.anim.current_animation])
	p.camera_pivot.rotation.y = 0.0


## Roads up terraces ramp instead of climbing a riser too steep to walk: the
## steepest point along every road in the terraced zones, then Dewstep's main
## road walked end to end, uphill.
func _t_terrace_roads() -> void:
	var main := get_parent()
	var p := World.local_player
	for zone_id: String in ["dewstep", "high_terrace", "sunward_steps"]:
		while main._changing_zone:
			await _wait(0.25)
		await _wait(0.5)
		World.zone_change.emit(p, zone_id, Vector2.INF, Vector2.INF)
		for k in 80:
			if (main.zone as Zone).zone_id == zone_id and not main._changing_zone:
				break
			await _wait(0.25)
		await _wait(0.5)
		var z := main.zone as Zone
		var worst := 0.0
		var worst_at := Vector2.ZERO
		for road: Dictionary in z.data.get("roads", []):
			var pts: Array = road["points"]
			for i in pts.size() - 1:
				var a := Vector2(pts[i][0], pts[i][1])
				var b := Vector2(pts[i + 1][0], pts[i + 1][1])
				var n := int(a.distance_to(b))
				for j in n:
					var q := a.lerp(b, float(j) / n)
					var dir := (b - a).normalized()
					var h0 := z.height_at(q.x - dir.x * 0.5, q.y - dir.y * 0.5)
					var h1 := z.height_at(q.x + dir.x * 0.5, q.y + dir.y * 0.5)
					var deg := rad_to_deg(atan(absf(h1 - h0)))
					if deg > worst:
						worst = deg
						worst_at = q
		print("terrace_roads: %s: steepest point on its roads %.0f degrees at %s" % [zone_id, worst, worst_at])
		if zone_id != "dewstep":
			continue
		# walk the main road from its far (low) end back up to the gate
		var road: Array = z.data["roads"][0]["points"]
		var start := Vector2(road[-1][0], road[-1][1])
		p.global_position = Vector3(start.x, z.height_at(start.x, start.y) + 1.0, start.y)
		await _wait(0.5)
		var t := 0.0
		var i := road.size() - 2
		var stuck := 0.0
		var last := p.global_position
		Input.action_press("move_forward")
		while i >= 0 and t < 120.0:
			if main._changing_zone or (main.zone as Zone).zone_id != "dewstep":
				i = -1  # through the gate: the road climbed all the way to Lanternhold
				break
			var goal := Vector3(road[i][0], p.global_position.y, road[i][1])
			if Vector2(p.global_position.x, p.global_position.z).distance_to(Vector2(goal.x, goal.z)) < 3.0:
				i -= 1
				continue
			p.face_toward(goal)
			await get_tree().physics_frame
			t += get_physics_process_delta_time()
			stuck = stuck + get_physics_process_delta_time() if p.global_position.distance_to(last) < 0.02 else 0.0
			last = p.global_position
			if stuck > 0.8 and stuck < 1.0:  # a lantern or a rock in the way: step round it, as a player would
				Input.action_press("move_right")
				await _wait(0.6)
				Input.action_release("move_right")
			if stuck > 3.0:
				break
		Input.action_release("move_forward")
		if i >= 0:
			p.zoom = 7.0
			p.pitch = -0.3
			await _wait(0.5)
			await _shot("9terrace_stuck")
			p.camera_pivot.rotation.y = PI * 0.5
			await _wait(0.3)
			await _shot("9terrace_stuck_side")
			p.camera_pivot.rotation.y = 0.0
		print("terrace_roads: dewstep: walked the road uphill -> %s after %.0f s at %s" % ["reached the gate" if i < 0 else "STUCK", t, p.global_position.snapped(Vector3.ONE)])


## Friends and guilds offline: the friends list, founding a guild at a
## registrar (level, fee, name), its tag, message of the day and chat, the
## windows, a guildmate's god showing in the Grove, and the last one out.
func _t_social() -> void:
	var main := get_parent()
	var p := World.local_player
	DirAccess.remove_absolute(ProjectSettings.globalize_path("user://guilds_autotest.json"))
	World._guild_store = null
	var lines: Array = []
	var grab := func(t: String, _c: Color) -> void: lines.append(t)
	World.log_message.connect(grab)
	p.friends.clear()
	World.request_chat(p.entity_id, "/friend Tester")
	World.request_chat(p.entity_id, "/friend Gerald")
	World.request_chat(p.entity_id, "/friend Mira")
	World.request_chat(p.entity_id, "/friend gerald")
	print("social: friends %s, saved %s" % [p.friends, p.to_save().get("friends")])
	World.request_chat(p.entity_id, "/guildcreate Ember Wardens")
	World.zone_change.emit(p, "emberhold", Vector2(6.2, 29.0), Vector2(6.2, 25.3))
	for k in 80:
		if (main.zone as Zone).zone_id == "emberhold" and not main._changing_zone:
			break
		await _wait(0.25)
	await _wait(0.8)
	var registrar: Npc = _npcs()["guild_registrar_emberhold"]
	_stand_by(p, registrar)
	World.request_hail(p.entity_id)
	World.request_chat(p.entity_id, "/guildcreate Ember Wardens")  # level 1
	p.level = 12
	p.coin = 5000
	World.request_chat(p.entity_id, "/guildcreate Ember Wardens")  # too poor
	p.coin = 25000
	World.request_chat(p.entity_id, "/guildcreate E!")  # a bad name
	World.request_chat(p.entity_id, "/guildcreate Ember Wardens")
	print("social: founded -> guild %s, rank %s, coin left %d, tag %s" % [p.guild_name, p.guild_rank, p.coin,
			p._guild_label.text if p._guild_label != null else "none"])
	World.request_chat(p.entity_id, "/guildmotd Muster at the fountain at dusk.")
	World.request_chat(p.entity_id, "/gu Hello, wardens!")
	World.request_chat(p.entity_id, "/guildinvite")  # no one targeted
	# a guildmate (offline) who has earned the Ember-Tusked: the Grove shows him to us too
	var key := World.guilds().key_of(p.display_name)
	World.guilds().join(key, {"name": "Brannoc", "level": 40, "class": "warrior", "zone": "forgehold", "seen": 0, "grove": ["fire"]}, "member")
	print("social: a guildmate earned fire -> we see fire %s, water %s" % [World.grove_sees(p, "fire"), World.grove_sees(p, "water")])
	World.request_guild(p.entity_id, "promote", "Brannoc")
	# the windows
	var hud: Node = get_tree().get_first_node_in_group("hud")
	hud._toggle_guild()
	hud._toggle_friends()
	await _wait(0.8)
	await _shot("9social_windows")
	hud._toggle_guild()
	hud._toggle_friends()
	p.camera_pivot.rotation.y = PI
	p.zoom = 4.0
	await _wait(0.4)
	await _shot("9social_tag")
	p.camera_pivot.rotation.y = 0.0
	World.request_chat(p.entity_id, "/guildleave")  # the leader, with a member: refused
	World.request_guild(p.entity_id, "remove", "Brannoc")
	World.request_chat(p.entity_id, "/guildleave")
	print("social: left -> guild %s, guild still exists %s" % [p.guild_name if p.guild_name != "" else "none", World.guilds().name_taken("Ember Wardens")])
	World.log_message.disconnect(grab)
	print("social: lines %s" % [lines])
	p.level = 1


## The compass names the exit you face, with its levels after the name.
func _t_exit_levels() -> void:
	var main := get_parent()
	var p := World.local_player
	var z := main.zone as Zone
	p.level = 8
	for zl: Dictionary in z.data.get("zone_lines", []):
		var at := Vector3(float(zl["pos"][0]), 0, float(zl["pos"][1]))
		var from := at * 0.6
		p.global_position = Vector3(from.x, z.height_at(from.x, from.z) + 1.0, from.z)
		p.face_toward(at)
		p.camera_pivot.rotation.y = 0.0
		await _wait(0.6)
		print("exit_levels: facing the line to %s" % zl["to"])
		await _shot("9exit_" + str(zl["to"]))
	p.level = 1


## The swing bar under the player window fills as the next swing comes up.
func _t_swing_bar() -> void:
	var p := World.local_player
	var mob: Mob = null
	for m in World.get_mobs():
		if not m.dead and (mob == null or p.distance_to(m) < p.distance_to(mob)):
			mob = m
	mob.max_hp = 100000
	mob.hp = 100000
	mob.set_physics_process(false)  # holds still for it
	p.global_position = mob.global_position + Vector3(1.5, 0.3, 0)
	p.face_toward(mob.global_position)
	World.request_set_target(p.entity_id, mob.entity_id)
	World.request_toggle_attack(p.entity_id)
	var seen: Array = []
	for k in 30:
		await _wait(0.1)
		seen.append(snappedf(get_tree().get_first_node_in_group("hud")._swing_bar.value, 0.05))
		if k == 14:
			await _shot("9swing_bar")
	print("swing_bar: row shown %s; bar over 3 s: %s" % [get_tree().get_first_node_in_group("hud")._swing_row.visible, seen])
	World.request_toggle_attack(p.entity_id)
	mob.set_physics_process(true)


## Critical hits: the chance each class gets (at 1 and 50), named monsters
## and ordinary ones, and the lines a melee crit, a spell crit and a heal
## crit give (the chance forced to 1 for the check).
func _t_crits() -> void:
	var p := World.local_player
	var saved_class := p.char_class
	var saved_level := p.level
	var table: Array = []
	for cls: String in GameData.classes:
		p.char_class = cls
		var row := "%s" % cls
		for lv in [1, 50]:
			p.level = lv
			row += " L%d m%.0f%% s%.0f%% h%.0f%%" % [lv, World.crit_chance(p, "melee") * 100, World.crit_chance(p, "spell") * 100, World.crit_chance(p, "heal") * 100]
		table.append(row)
	p.char_class = saved_class
	p.level = saved_level
	print("crits: %s" % [table])
	var named: Mob = null
	var plain: Mob = null
	for m in World.get_mobs():
		if m.data.get("named", false):
			named = m
		else:
			plain = m
	var was: Dictionary = plain.data
	plain.data = was.duplicate()
	plain.data["named"] = true
	var named_chance := World.crit_chance(plain, "melee")
	plain.data = was
	print("crits: a named monster %.0f%%, an ordinary one %.0f%%" % [named_chance * 100, World.crit_chance(plain, "melee") * 100])
	var lines: Array = []
	var grab := func(t: String, _c: Color) -> void: lines.append(t)
	World.log_message.connect(grab)
	for k: String in ["crit_melee", "crit_spell", "crit_heal"]:
		GameData.config[k] = [1.0, 0.0]
	var class_crit: Variant = GameData.classes[p.char_class].get("crit")
	GameData.classes[p.char_class].erase("crit")  # the config's forced chance, not the class's own
	var mob := plain
	mob.max_hp = 100000
	mob.hp = 100000
	World._swing(p, mob, "primary")
	World._swing(p, mob, "primary")
	World._land(p, "fire_bolt", mob, GameData.spells["fire_bolt"], 20)
	World._land(p, "minor_healing", p, GameData.spells["minor_healing"], 10)
	for k: String in ["crit_melee", "crit_spell", "crit_heal"]:
		GameData.config[k] = [0.03, 0.0004]
	if class_crit != null:
		GameData.classes[p.char_class]["crit"] = class_crit
	World.log_message.disconnect(grab)
	print("crits: lines %s" % [lines])


## The quest journal: active and completed quests, a quest line's step
## abandoned and offered back by hailing its giver, and a plain abandon.
## Who may take up a shared quest: what they're on, what they've done, a quest
## line's earlier step, and whether its giver would talk to them. The share
## button shows in the journal only in a group.
## A deleted character leaves its guild: a leader's guild passes to an
## officer before a member, and a guild of one closes.
## The elephant gods turn the evil races away (Timiraj takes anyone): who
## may follow whom, and a troll who followed Agnavar choosing again in the
## HUD's window, refused an elephant, taking a bog god.
## Character creation shows the character as it's chosen: race, class,
## gender and hair change the figure; a drag turns it.
func _t_char_preview() -> void:
	var cc := CharCreate.new()
	cc.setup({})
	get_parent().add_child(cc)
	await _wait(0.6)
	await _shot("9preview_default")
	for pick: Array in [["troll", "shaman", "male", "rugged", "white"], ["gnome", "wizard", "female", "long", "copper"],
			["ogre", "warrior", "male", "", ""], ["dark_elf", "necromancer", "female", "flowing", "white"]]:
		cc._select_race(pick[0])
		cc._select(pick[1])
		cc._gender = pick[2]
		cc._hair.set_hair(pick[3], pick[4])
		cc._refresh_preview()
		await _wait(0.5)
		print("char_preview: %s -> %s" % [pick, cc.preview_look()])
		await _shot("9preview_%s" % pick[0])
	var drag := InputEventMouseButton.new()
	drag.button_index = MOUSE_BUTTON_LEFT
	drag.pressed = true
	cc._on_preview_input(drag)
	var move := InputEventMouseMotion.new()
	move.relative = Vector2(180, 0)
	cc._on_preview_input(move)
	await _wait(0.3)
	print("char_preview: dragged -> turned %.0f degrees" % rad_to_deg(cc._preview_stage.rotation.y))
	await _shot("9preview_turned")
	cc.queue_free()


## The dark elves' own gods: who may follow them, Tantuvi's deeper poison,
## and both priests on Duskhold's island binding and blessing their own.
## Logging in where you don't belong: a troll still in Rainhold the first
## time after its people moved goes to Murkhold; a dark elf who logged out in
## Emberhold (bound there) is bound in Duskhold and taken there; a troll who
## already moved may stay in Rainhold; a human in Emberhold stays.
## The floating quest marks: "!" over Warden Holt while he has work for you,
## gone once you've taken it all, "?" when you carry what he wants, and
## nothing for someone his people won't talk to.
## Every bridge stands over its water, not in it: a walk across Duskhold's
## north bridge from the shore to the island without swimming, and a look at
## each of the world's bridges.
## A necromancer's servants take bone: a new one starts with three chips,
## Raise Bones is refused without one and uses one when it lands, an older
## necromancer is given three once, and provisioners sell them.
## Arming a pet, EverQuest style: a skeleton given a greatsword, a helm and
## a shield wields and wears them (stats and looks), hands back what it had,
## keeps it all through a save and a re-summon, and leaves it on a corpse only
## its owner may loot when it dies.
func _t_pet_gear() -> void:
	var p := World.local_player
	var keep := [p.char_class, p.spells.duplicate(), p.level, p.pet_gear.duplicate()]
	World.dismiss_pet(p)
	p.pet_gear = {}
	p.char_class = "necromancer"
	p.level = 20
	World.summon_pet(p, "raise_bones")
	var pet := World.get_object(p.pet_id) as Pet
	var before := "dmg %d-%d, ac %d" % [pet.dmg_min, pet.dmg_max, pet.ac]
	for item_id: String in ["ossuary_greatmaul", "rusty_short_sword", "iron_coif", "tempered_kite_shield"]:
		p.cursor = Pack.entry(item_id)
		World.request_give_pet(p.entity_id, pet.entity_id)
	print("pet_gear: a rusty sword (4 damage) -> dmg %d-%d (the pet's own is better)" % [pet.dmg_min, pet.dmg_max])
	p.cursor = Pack.entry("unlit_worldblade")
	World.request_give_pet(p.entity_id, pet.entity_id)
	print("pet_gear: %s -> gear %s; %s -> dmg %d-%d, ac %d; cursor now %s" % [pet.display_name, p.pet_gear, before, pet.dmg_min, pet.dmg_max, pet.ac, p.cursor])
	print("pet_gear: look weapon %s, offhand %s, worn %s" % [pet.look.get("weapon"), pet.look.get("offhand"), pet.look.get("worn")])
	p.cursor = {}
	p.cursor = Pack.entry("grove_seed")
	World.request_give_pet(p.entity_id, pet.entity_id)
	p.cursor = Pack.entry("crude_arrow", 5)
	World.request_give_pet(p.entity_id, pet.entity_id)
	p.cursor = {}
	pet.mode = Pet.Mode.SIT
	pet.global_position = p.global_position - p.global_basis.z * 4.0 + p.global_basis.x * 2.2
	pet.face_toward(p.global_position)
	get_tree().get_first_node_in_group("hud")._pet_panel.position = Vector2(620, 110)
	await _wait(0.8)
	await _shot("9pet_gear")
	# a save and a re-summon (as after logging in)
	var saved := p.to_save()
	var reborn := Player.new()
	reborn.from_save(saved)
	print("pet_gear: saved -> %s; loaded back -> %s" % [saved.get("pet", {}).get("gear"), reborn.pet_gear])
	reborn.free()
	World.dismiss_pet(p, false)
	World._check_pet(p)
	pet = World.get_object(p.pet_id) as Pet
	print("pet_gear: re-summoned %s wears %s, dmg %d-%d" % [pet.display_name, pet.gear.keys(), pet.dmg_min, pet.dmg_max])
	# its death: a corpse only you may loot
	var at := pet.global_position
	World._kill_pet(pet)
	await _wait(0.3)
	var corpse: Corpse = null
	for obj: Variant in World.objects.values():
		if obj is Corpse and (obj as Corpse).owner_name == p.display_name and (obj as Corpse).global_position.distance_to(at) < 1.0:
			corpse = obj
	print("pet_gear: slain -> gear left %s; corpse %s owned by %s holding %s" % [p.pet_gear, corpse.display_name if corpse else "none",
			corpse.owner_name if corpse else "-", corpse.entries.map(func(e: Dictionary) -> String: return str(e["item"])) if corpse else []])
	if corpse != null:
		p.global_position = corpse.global_position + Vector3(1, 0, 0)
		World.request_loot_open(p.entity_id, corpse.object_id)
		World.request_loot_all(p.entity_id, corpse.object_id)
		print("pet_gear: looted back -> greatsword %d, coif %d, shield %d" % [p.pack.count("unlit_worldblade"), p.pack.count("iron_coif"), p.pack.count("tempered_kite_shield")])
		for item_id: String in ["unlit_worldblade", "iron_coif", "tempered_kite_shield", "ossuary_greatmaul"]:
			p.pack.remove(item_id, p.pack.count(item_id))
	p.char_class = keep[0]
	p.spells = keep[1]
	p.level = keep[2]
	p.pet_gear = keep[3]


func _t_bone_chips() -> void:
	var fresh := Player.new()
	fresh.from_save({"name": "Probe", "class": "necromancer", "race": "human", "stats": {}})
	print("bone_chips: a new necromancer carries %d, given %s" % [fresh.pack.count("bone_chips"), fresh.given])
	var old := Player.new()
	old.from_save({"name": "Oldbones", "class": "necromancer", "race": "human", "stats": {}, "pack": fresh.pack.to_save()})
	old.pack.remove("bone_chips", old.pack.count("bone_chips"))
	print("bone_chips: an older necromancer's save -> carries %d, given %s" % [old.pack.count("bone_chips"), old.given])
	World._gifts(old)
	var once := old.pack.count("bone_chips")
	World._gifts(old)
	print("bone_chips: given once -> %d, again -> %d, given %s" % [once, old.pack.count("bone_chips"), old.given])
	fresh.free()
	old.free()
	var p := World.local_player
	var keep := [p.char_class, p.spells.duplicate(), p.mana, p.pack.count("bone_chips")]
	World.dismiss_pet(p)
	p.char_class = "necromancer"
	p.spells = ["raise_bones"]
	p.pack.remove("bone_chips", p.pack.count("bone_chips"))
	p.mana = 500
	p.cooldowns.erase("raise_bones")
	World.request_cast(p.entity_id, "raise_bones")
	print("bone_chips: no chips -> casting %s, pet %s" % [not p.cast.is_empty(), p.pet_id >= 0])
	print("bone_chips: tooltip says: %s" % [get_tree().get_first_node_in_group("hud").spell_tooltip("raise_bones").split("\n")[-1]])
	p.pack.add("bone_chips", 2)
	World.request_cast(p.entity_id, "raise_bones")
	var casting := not p.cast.is_empty()
	for k in 80:
		if p.cast.is_empty():
			break
		await _wait(0.1)
	print("bone_chips: with 2 -> casting %s, then pet %s, chips left %d" % [casting, World.get_object(p.pet_id) != null, p.pack.count("bone_chips")])
	var sellers := GameData.npcs.keys().filter(func(k: String) -> bool: return "bone_chips" in GameData.npcs[k].get("merchant", {}).get("sells", []))
	print("bone_chips: sold by %s" % [sellers])
	World.dismiss_pet(p)
	p.pack.remove("bone_chips", p.pack.count("bone_chips"))
	p.pack.add("bone_chips", keep[3]) if keep[3] > 0 else 0
	p.char_class = keep[0]
	p.spells = keep[1]
	p.mana = keep[2]


func _t_bridges() -> void:
	var main := get_parent()
	var p := World.local_player
	var keep := [p.race, p.factions.duplicate(), p.alignment_mods.duplicate(), p.deity]
	p.race = "dark_elf"  # Duskhold's guards would cut down anyone else
	p.deity = "dark"
	p.factions = {}
	p.alignment_mods = {}
	World.apply_alignment(p)
	var go := func(zone_id: String, at: Vector2) -> void:
		while main._changing_zone:
			await _wait(0.25)
		if (main.zone as Zone).zone_id != zone_id:
			World.zone_change.emit(p, zone_id, at, Vector2.ZERO)
			for k in 80:
				if (main.zone as Zone).zone_id == zone_id and not main._changing_zone:
					break
				await _wait(0.25)
		await _wait(0.8)
	await go.call("duskhold", Vector2(0, -44))
	var z: Zone = main.zone
	p.global_position = Vector3(0, z.surface_at(0, -44) + 0.5, -44)
	p.velocity = Vector3.ZERO
	await _wait(0.5)
	var swam := false
	var top := -INF
	p.face_toward(Vector3(0, p.global_position.y, 0))
	Input.action_press("move_forward")
	for k in 360:
		await get_tree().physics_frame
		p.face_toward(Vector3(0, p.global_position.y, 0))
		swam = swam or p.swimming
		top = maxf(top, p.global_position.y)
		if p.global_position.z > -12.0:
			break
	Input.action_release("move_forward")
	print("duskhold bridge: ground at the island end %.2f, the shore end %.2f" % [z.height_at(0, -13.5), z.height_at(0, -37.5)])
	print("duskhold bridge: water at %.2f; walked from z -44 to %.1f, highest %.2f, swam %s" % [z.water_level(0, -25), p.global_position.z, top, swam])
	await _zone_views("bridges_duskhold", [[Vector2(14, -40), Vector2(0, -25), "north"], [Vector2(-14, 40), Vector2(0, 25), "south"]])
	for spot: Array in [["cinderpass", Vector2(-119, 25), Vector2(-119, 5)], ["dewstep", Vector2(0, 30), Vector2(0, 10)],
			["thornwood", Vector2(3.5, 126), Vector2(3.5, 106)]]:
		await go.call(spot[0], spot[1])
		await _zone_views("bridges_" + str(spot[0]), [[spot[1], spot[2], "bridge"]])
	p.race = keep[0]
	p.factions = keep[1]
	p.alignment_mods = keep[2]
	p.deity = keep[3]


## High Terrace without its steps: how much of it (and a few other zones, to
## compare) is too steep to walk up, where its snow lies and who's on it.
func _t_high_terrace_ground() -> void:
	var main := get_parent()
	var p := World.local_player
	for zone_id: String in ["high_terrace", "thornwood", "cinderpass", "sunward_steps", "dewstep"]:
		while main._changing_zone:
			await _wait(0.25)
		if (main.zone as Zone).zone_id != zone_id:
			World.zone_change.emit(p, zone_id, Vector2.INF, Vector2.INF)
			for k in 80:
				if (main.zone as Zone).zone_id == zone_id and not main._changing_zone:
					break
				await _wait(0.25)
			await _wait(0.5)
		var z := main.zone as Zone
		var half := float(z.data.get("size", 512)) * 0.5 - 30.0
		var steep := 0
		var total := 0
		var x := -half
		while x < half:
			var y := -half
			while y < half:
				if z.edge_depth(x, y) > -2.0:  # the mountains round the zone (its ridges reach in) are steep on purpose
					y += 4.0
					continue
				var h := z.height_at(x, y)
				var dx := z.height_at(x + 1.0, y) - h
				var dy := z.height_at(x, y + 1.0) - h
				if rad_to_deg(atan(sqrt(dx * dx + dy * dy))) > 40.0:
					steep += 1
				total += 1
				y += 4.0
			x += 4.0
		print("high_terrace_ground: %s: %.1f%% of the ground too steep to walk up (over 40 degrees)" % [zone_id, 100.0 * steep / total])
		if zone_id == "high_terrace":
			var on_snow := 0
			var leopards := 0
			for m in World.get_mobs():
				if m.mob_id in ["snow_leopard", "ghost_leopard"]:
					leopards += 1
					if z.on_bare_patch(m.global_position.x, m.global_position.z):
						on_snow += 1
			print("high_terrace_ground: snow leopards %d, on the snow %d" % [leopards, on_snow])
			await _zone_views("high_terrace", [[Vector2(-160, 70), Vector2(-190, 60), "falls"], [Vector2(0, 150), Vector2(-60, 175), "paddies"], [Vector2(-40, -60), Vector2(-80, -160), "snowfields"],
					[Vector2(60, -140), Vector2(78, -205), "monastery"], [Vector2(20, 60), Vector2(0, -60), "climb"]])
		if zone_id == "sunward_steps":
			await _zone_views("sunward_steps", [[Vector2(-120, 60), Vector2(-160, 110), "mesas"], [Vector2(40, 20), Vector2(108, 88), "shrines"]])
		if zone_id == "dewstep":
			await _zone_views("dewstep", [[Vector2(20, 30), Vector2(0, 10), "bridge"], [Vector2(-40, -80), Vector2(-60, -30), "gardens"]])


## Hostile camps, bigger, spread out and each its own look: in each, the
## camp member nearest the edge is hit from range and we count who comes
## (only it and whoever is within ASSIST_RADIUS of it, no chain), then a look.
func _t_camps() -> void:
	var main := get_parent()
	var p := World.local_player
	World.time_override = 12.0
	for zone_id: String in ["greenmoor", "harrowfield", "thornwood", "sunward_steps", "the_bleach", "cinderpass"]:
		while main._changing_zone:
			await _wait(0.25)
		if (main.zone as Zone).zone_id != zone_id:
			World.zone_change.emit(p, zone_id, Vector2.INF, Vector2.INF)
			for k in 80:
				if (main.zone as Zone).zone_id == zone_id and not main._changing_zone:
					break
				await _wait(0.25)
			await _wait(1.5)
		var z := main.zone as Zone
		var lm: Dictionary = {}
		for l: Dictionary in z.data["landmarks"]:
			if l["type"] == "camp" and l.has("size"):
				lm = l
		var c := Vector3(float(lm["pos"][0]), 0, float(lm["pos"][1]))
		var camp: Array = World.get_mobs().filter(func(m: Mob) -> bool:
			return World.zone_of(m) == z and not m.dead and Vector2(m.global_position.x, m.global_position.z).distance_to(Vector2(c.x, c.z)) < 26.0)
		camp.sort_custom(func(a: Mob, b: Mob) -> bool:
			return Vector2(a.global_position.x, a.global_position.z).distance_to(Vector2(c.x, c.z)) > Vector2(b.global_position.x, b.global_position.z).distance_to(Vector2(c.x, c.z)))
		var outer: Mob = camp[0]
		var away := (outer.global_position - c).normalized() * 30.0
		p.global_position = outer.global_position + Vector3(away.x, 0, away.z) + Vector3.UP * 2.0
		p.level = 60  # nothing here kills the tester before we've counted
		p.recalc_stats()
		p.hp = p.max_hp
		await _wait(0.3)
		outer.add_hate(p, 5.0)
		await _wait(1.0)
		var came := camp.filter(func(m: Mob) -> bool: return not m.hate.is_empty()).size()
		print("camps: %s (%s x%.1f): %d in the camp, hitting the outermost brought %d" % [zone_id, lm.get("style", "war"), float(lm["size"]), camp.size(), came])
		for m: Mob in camp:
			m.hate.clear()
			m.state = Mob.State.RETURN
		var eye := c + (Vector3(_bind_dir(z, c).x, 0, _bind_dir(z, c).y) * 34.0)
		await _zone_views("camps_" + zone_id, [[Vector2(eye.x, eye.z), Vector2(c.x, c.z), "camp"]])
	p.level = 1
	p.recalc_stats()
	World.time_override = -1.0


func _bind_dir(z: Zone, c: Vector3) -> Vector2:
	return (Vector2(z.bind_point.x, z.bind_point.z) - Vector2(c.x, c.z)).normalized()


func _toggle_bag_for_shot(hud: Node, g: int) -> void:
	if not hud._bag_windows.has(g):
		hud._toggle_bag(g)


## Bags open with the character window open: right-clicking a bag in the
## General slots, and B, both open its window, on screen and in front.
func _t_bags_with_inventory() -> void:
	var hud: Node = get_tree().get_first_node_in_group("hud")
	var p := World.local_player
	var g := -1
	for i in Pack.GENERAL:
		if (p.pack.slots[i] as Dictionary).is_empty():
			g = i
			break
	p.pack.slots[g] = Pack.entry("leather_backpack")
	p.inventory_changed.emit()
	await _wait(0.2)
	if not hud._inv_panel.visible:
		hud._toggle_inventory()
	await _wait(0.4)
	var place := "g:%d" % g
	var buttons: Array = hud._slot_buttons[place]
	print("bags_with_inventory: %d buttons show %s: %s" % [buttons.size(), place, buttons.map(func(b: Button) -> String: return "%s visible %s at %s" % [b.get_parent().get_parent().name, b.is_visible_in_tree(), b.global_position])])
	for slot: Button in buttons:
		hud._close_all_bags()
		await _wait(0.1)
		var click := InputEventMouseButton.new()
		click.button_index = MOUSE_BUTTON_RIGHT
		click.pressed = true
		click.position = slot.size * 0.5
		slot.gui_input.emit(click)
		await _wait(0.3)
		print("bags_with_inventory: right-click on the button at %s -> bag window %s" % [slot.global_position, hud._bag_windows.has(g)])
	# and through the real input path: a right-click at the button's place on screen
	hud._close_all_bags()
	await _wait(0.1)
	for slot: Button in buttons:
		if not slot.is_visible_in_tree():
			continue
		var at := slot.get_global_rect().get_center()
		for pressed: bool in [true, false]:
			var ev := InputEventMouseButton.new()
			ev.button_index = MOUSE_BUTTON_RIGHT
			ev.pressed = pressed
			ev.position = at
			ev.global_position = at
			Input.parse_input_event(ev)
			await _wait(0.1)
		await _wait(0.3)
		print("bags_with_inventory: a real right-click at %s -> bag window %s" % [at, hud._bag_windows.has(g)])
		hud._close_all_bags()
		await _wait(0.1)
	# a Mac laptop's right-click: Control+click
	var ctrl := InputEventMouseButton.new()
	ctrl.button_index = MOUSE_BUTTON_LEFT
	ctrl.ctrl_pressed = true
	ctrl.pressed = true
	(buttons[0] as Button).gui_input.emit(ctrl)
	await _wait(0.3)
	print("bags_with_inventory: Control+click (%s) -> bag window %s, the bag still in its slot %s" % [OS.get_name(), hud._bag_windows.has(g),
			str(p.pack.slots[g].get("item", "")) == "leather_backpack"])
	hud._close_all_bags()
	_toggle_bag_for_shot(hud, g)
	await _wait(0.4)
	var win: Control = hud._bag_windows.get(g)
	print("bags_with_inventory: right-click with the window open -> bag window %s%s" % [win != null,
			" at %s size %s, screen %s, visible %s" % [win.position, win.size, hud.root.size, win.is_visible_in_tree()] if win != null else ""])
	await _shot("9bags_with_inventory")
	hud._close_all_bags()
	await _wait(0.2)
	var key := InputEventKey.new()
	key.keycode = KEY_B
	key.physical_keycode = KEY_B
	key.pressed = true
	Input.parse_input_event(key)
	await _wait(0.4)
	print("bags_with_inventory: B with the window open -> %d bag windows" % hud._bag_windows.size())
	hud._close_all_bags()
	hud._toggle_inventory()
	p.pack.slots[g] = {}
	p.inventory_changed.emit()


## Elephant Grove's uniques: made for the level they drop at, off a named
## kill (forced here), worn with their glow, and kept through a save.
func _t_grove_uniques() -> void:
	for lvl: int in [10, 30, 50]:
		var it := GameData.item("dragonfang_sword~%d" % lvl)
		print("grove_uniques: %s at %d -> dmg %d delay %.1f, str %d sta %d hp %d, rec %d, value %d, color %s" % [it["name"], lvl, it["dmg"], it["delay"],
				it.get("str", 0), it.get("sta", 0), it.get("hp", 0), it["rec_level"], it["value"], GameData.item_color("dragonfang_sword~%d" % lvl).to_html(false)])
	var merchant := GameData.item("eclipse_blade")
	print("grove_uniques: the best merchant sword, Eclipse Blade (47): dmg %d" % merchant["dmg"])
	var staff := GameData.item("dragonheart_staff~40")
	print("grove_uniques: Dragonheart Staff at 40: dmg %d int %d wis %d mana %d, classes %s" % [staff["dmg"], staff["int"], staff["wis"], staff["mana"], staff["classes"]])
	# a named kill with the chance forced
	var p := World.local_player
	var named: Mob = null
	for m in World.get_mobs():
		if not m.dead:
			named = m
	var was_named: bool = named.data.get("named", false)
	named.data["named"] = true  # stood in for a named one (none may be up)
	var keep: float = GameData.loot["unique"]["chance"]
	GameData.loot["unique"]["chance"] = 1.0
	var level := named.level
	var who := named.display_name
	var data: Dictionary = named.data
	World.damage(named, named.hp + 10, p)
	GameData.loot["unique"]["chance"] = keep
	if not was_named:
		data.erase("named")
	await _wait(0.3)
	var got := ""
	for obj: Variant in World.objects.values():
		if obj is Corpse:
			for e: Dictionary in (obj as Corpse).entries:
				if str(e["item"]).contains("~"):
					got = str(e["item"])
	print("grove_uniques: %s (level %d) dropped %s" % [who, level, got])
	# worn: its stats and glow
	var keep_eq := p.equipment.duplicate()
	var dmg0 := p.dmg_max
	p.equipment["primary"] = "dragonfang_sword~20"
	p.recalc_stats()
	p.inventory_changed.emit()
	await _wait(0.3)
	print("grove_uniques: wielding it at 20 -> max damage %d (was %d), look tiers %s" % [p.dmg_max, dmg0, p.look.get("tiers")])
	var back := Player.new()
	back.from_save(p.to_save())
	print("grove_uniques: saved and loaded -> primary %s" % back.equipment.get("primary"))
	back.free()
	p.equipment = keep_eq
	p.recalc_stats()
	p.inventory_changed.emit()


## Giants stand like giants: body height (and so nameplate and click box)
## for a player and the big monsters, and a bone giant beside the player.
func _t_giant_sizes() -> void:
	var p := World.local_player
	var out := {"player": snappedf(p.body_height, 0.01)}
	for mid: String in ["bone_giant", "bone_titan", "ember_giant", "cloud_giant", "terrace_colossus", "gnoll_scout"]:
		var d: Dictionary = GameData.mobs[mid]
		out[mid] = snappedf(1.85 * float(d.get("scale", 1.0)) * Entity._model_size(str(d.get("model", ""))), 0.01)  # as build_body sizes it
	print("giant_sizes: body heights %s" % [out])
	var giant: Mob = null
	for m in World.get_mobs():
		if m.mob_id == "bone_giant" and (giant == null or p.distance_to(m) < p.distance_to(giant)):
			giant = m
	if giant != null:
		giant.aggressive = false
		p.global_position = giant.global_position + Vector3(4, 0, 4)
		p.face_toward(giant.global_position)
		p.camera_pivot.rotation.y = 0.6
		await _wait(0.8)
		await _shot("9giant_beside")


## Swings by weapon: which one each weapon makes, then a dual-wielding rogue
## fighting, with every clip its body plays (the main hand's slash and the
## off hand's own cut), and a shot of each.
func _t_boss_camp_respawn() -> void:
	# a quest boss's camp comes back twice as slowly, so it can be cleared to reach him
	var z: Zone = get_parent().zone
	var boss_at := Vector3.INF
	for sp: Node in z.get_children():
		if sp is SpawnPoint and ((sp as SpawnPoint).pool.has("grolthar") or (sp as SpawnPoint).rare == "grolthar"):
			boss_at = (sp as SpawnPoint).position
	var rows := PackedStringArray()
	var far_ok := true
	for i in z.data["spawns"].size():
		var entry: Dictionary = z.data["spawns"][i]
		var sp: SpawnPoint = null
		for c: Node in z.get_children():
			if c is SpawnPoint and (c as SpawnPoint).pool == entry["pool"] and is_equal_approx((c as SpawnPoint).position.x, float(entry["pos"][0])) and is_equal_approx((c as SpawnPoint).position.z, float(entry["pos"][1])):
				sp = c
		if sp == null or sp.rare != "":
			continue  # a rare spawn's spot (SpawnPoint.rare) keeps its own, quicker time
		var d := Vector2(sp.position.x - boss_at.x, sp.position.z - boss_at.z).length()
		if d <= 28.0 and not sp.pool.has("grolthar"):
			rows.append("%s %.0f -> %.0f" % [",".join(sp.pool.keys()), float(entry.get("respawn", 60)), sp.respawn_time])
		elif d > 60.0 and not is_equal_approx(sp.respawn_time, float(entry.get("respawn", 60))) and not sp.has_meta("boss_guard"):
			far_ok = false
	print("boss_camp_respawn: Grolthar is a quest boss %s, Silkfang %s, a timber wolf %s" % [GameData.is_quest_boss("grolthar"), GameData.is_quest_boss("broodmother_silkfang"), GameData.is_quest_boss("timber_wolf")])
	print("boss_camp_respawn: around Grolthar: %s" % [rows])
	print("boss_camp_respawn: spawns away from any boss keep their time: %s" % far_ok)


func _t_caster_stats() -> void:
	# INT or WIS over 75: mana, mana regen, spell power (own spells only) and fewer fizzles
	var p := World.local_player
	var saved := [p.char_class, p.level, p.spells, p.stat_points, p.race]
	p.char_class = "wizard"
	p.level = 30
	p.race = "human"
	p.spells = ["fireball"]
	var rows := PackedStringArray()
	for n: int in [0, 15]:
		p.stat_points = {"int": n}
		p.recalc_stats()
		rows.append("int +%d: mana %d, regen %d, fireball x%.3f, kick x%.3f, not in book x%.3f" % [p.caster_over(), p.max_mana, p.mana_regen,
				World.spell_power(p, "fireball", GameData.spells["fireball"]), World.spell_power(p, "kick", GameData.spells["kick"]),
				World.spell_power(p, "fire_bolt", GameData.spells["fire_bolt"])])
	print("caster_stats: %s" % " | ".join(rows))
	p.char_class = "cleric"
	p.stat_points = {"int": 15}
	p.recalc_stats()
	print("caster_stats: a cleric's INT counts for nothing: over %d" % p.caster_over())
	print("caster_stats: creation text, wizard int 15: '%s'; cleric int 15: '%s'; 20 wis cleric: '%s'" % [StatPicker.effect_text("int", 15, GameData.classes["wizard"]),
			StatPicker.effect_text("int", 15, GameData.classes["cleric"]), StatPicker.effect_text("wis", 20, GameData.classes["cleric"])])
	p.char_class = saved[0]
	p.level = saved[1]
	p.spells = saved[2]
	p.stat_points = saved[3]
	p.race = saved[4]
	p.recalc_stats()


func _t_plate_looks() -> void:
	# plate (warrior and cleric only) must wear the knight's metal, never leather or cloth
	var looks: Dictionary = GameData.models.get("body_parts", {})
	var bad: Array = []
	for id: String in GameData.items:
		var it: Dictionary = GameData.items[id]
		if it.get("classes", []) != ["warrior", "cleric"] or str(it.get("slot", "")) not in ["chest", "arms", "legs", "hands", "feet", "head"]:
			continue
		var look: Dictionary = looks.get(str(it.get("wear", "")), {})
		if str(look.get("model", "")) not in ["knight", "skeleton_warrior"]:
			bad.append("%s (%s)" % [id, it.get("wear", "none")])
	print("plate_looks: plate pieces not in metal: %s" % [bad])
	var p := World.local_player
	var cm := p.visual as CharacterModel
	cm.set_worn({"chest": "plate_breastplate", "arms": "plate_vambraces", "hands": "iron_gauntlets"})
	await get_tree().process_frame
	var parts: Array = []
	for n: Node in cm.skeleton.get_children():
		if str(n.name).begins_with("Worn_"):
			parts.append(str(n.name))
	print("plate_looks: a dressed warrior wears %s" % [parts])
	if bad.is_empty() and "Worn_Knight_ArmLeft" in parts and "Worn_Knight_Body" in parts:
		print("plate_looks: OK")
	else:
		print("plate_looks: FAIL")


func _t_melee_swings() -> void:
	var picks := {}
	for w: String in ["sword_1handed", "dagger", "axe_2handed", "staff", "axe_1handed", "countess_rapier", "vorlaug_maul", "bow", ""]:
		picks[w] = Entity.swing_for(w)
	picks["dagger (off hand)"] = Entity.swing_for("dagger", true)
	for w: String in ["stonebrow_club", "ember_hammer", "court_maul", "miners_pick"]:  # a club or a short hammer swings one-armed; a maul with both
		picks[w] = Entity.swing_for(w)
	picks["court_maul (one-handed)"] = Entity.swing_for("court_maul", false, "1h_blunt")
	print("melee_swings: %s" % [picks])
	var p := World.local_player
	var keep := [p.char_class, p.level, p.equipment.duplicate(), p.skills.duplicate()]
	p.char_class = "rogue"
	p.level = 20
	p.equipment["primary"] = "steel_longsword"
	p.equipment["secondary"] = "steel_dirk"
	p.fill_skills()
	p.skills["dual_wield"] = GameData.skill_cap("rogue", "dual_wield", 20)
	p.recalc_stats()
	p.dress()
	var mob: Mob = null
	for m in World.get_mobs():
		if not m.dead and (mob == null or p.distance_to(m) < p.distance_to(mob)):
			mob = m
	mob.max_hp = 100000
	mob.hp = 100000
	p.global_position = mob.global_position + Vector3(1.6, 0, 0)
	p.face_toward(mob.global_position)
	World.request_set_target(p.entity_id, mob.entity_id)
	World.request_toggle_attack(p.entity_id)
	var seen := {}
	var shot := {}
	var m := p.visual as CharacterModel
	for k in 600:
		await get_tree().physics_frame
		var c := m.anim.current_animation
		if c != "":
			seen[c] = int(seen.get(c, 0)) + 1
			if c.begins_with("Attack_") and not shot.has(c) and m.anim.current_animation_position > 0.25:
				shot[c] = true
				await _shot("9swing_" + c)
	print("melee_swings: a dual-wielding rogue's body played %s" % [seen])
	World.request_toggle_attack(p.entity_id)
	p.char_class = keep[0]
	p.level = keep[1]
	p.equipment = keep[2]
	p.skills = keep[3]
	p.recalc_stats()
	p.dress()


## The filled-in zones (tools/zones/spawn_fill.py): every day spawn alive a
## few seconds in, none under the ground, in lava or in deep water, and none
## wandered far from its spot.
func _t_spawn_coverage() -> void:
	var main := get_parent()
	var p := World.local_player
	World.time_override = 12.0
	for zone_id: String in ["high_terrace", "agnavars_hearth", "hollow_air", "timirajs_table", "the_unlit", "mirror_flats", "cinderpass"]:
		while main._changing_zone:
			await _wait(0.25)
		World.zone_change.emit(p, zone_id, Vector2.INF, Vector2.INF)
		for k in 80:
			if (main.zone as Zone).zone_id == zone_id and not main._changing_zone:
				break
			await _wait(0.25)
		await _wait(4.0)
		var z := main.zone as Zone
		var day := 0
		for sp: Dictionary in z.data.get("spawns", []):
			if sp.get("when", "") != "night":
				day += 1
		var under := 0
		var hot := 0
		var wet := 0
		var strayed := 0
		var mobs := World.get_mobs().filter(func(m: Mob) -> bool: return World.zone_of(m) == z)
		for m: Mob in mobs:
			var at := m.global_position
			if at.y < z.height_at(at.x, at.z) - 3.0:
				under += 1
			if z.lava_at(at.x, at.z):
				hot += 1
				print("spawn_coverage:   in lava: %s at %s" % [m.mob_id, at.snapped(Vector3.ONE)])
			if m.swimming:
				wet += 1
			if m.spawn_point != null and Vector2(at.x, at.z).distance_to(Vector2(m.spawn_point.global_position.x, m.spawn_point.global_position.z)) > 40.0:
				strayed += 1
		print("spawn_coverage: %s: %d day spawns, %d monsters up; under the ground %d, in lava %d, swimming %d, strayed %d" % [zone_id, day, mobs.size(), under, hot, wet, strayed])
	World.time_override = -1.0


## Mirror Flats' shore and water by day: the shoreline, the camp at the
## entry, Glasswater Camp on its island, the Duneskiff camp on the west shore.
func _t_flats_views() -> void:
	World.time_override = 11.0
	var z: Zone = get_parent().zone
	var wet := 0
	for n: Dictionary in z.data["npcs"]:
		if z.swim_level(n["pos"][0], n["pos"][1]) > z.height_at(n["pos"][0], n["pos"][1]) + 0.05:
			wet += 1
	print("flats_views: npcs standing in water %d of %d" % [wet, z.data["npcs"].size()])
	await _wait(1.0)
	await _zone_views("mirror_flats", [[Vector2(10, 330), Vector2(0, 0), "from_entry"], [Vector2(-20, -20), Vector2(-60, -60), "glasswater"],
			[Vector2(-200, 260), Vector2(-294, 198), "duneskiff"], [Vector2(330, 60), Vector2(200, -100), "east_shore"]])
	World.time_override = -1.0


## /summoncorpse: an admin brings a player's corpses to their feet, from far
## off in this zone and (offline) from another zone's saved ones, with what's
## on them; someone else's stay where they lie.
func _t_summon_corpse() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	p.global_position = z.ground(10, 10) + Vector3.UP
	var far := z.ground(150, -120)
	z.restore_corpses([{"owner": p.display_name, "look": {}, "entries": [{"item": "iron_dagger"}], "coin": 120, "decay_left": 3000.0, "position": [far.x, far.y, far.z]},
			{"owner": "Somebody", "look": {}, "entries": [], "coin": 5, "decay_left": 3000.0, "position": [far.x + 2, far.y, far.z]}])
	main._corpses_by_zone["thornwood"] = [{"owner": p.display_name, "look": {}, "entries": [{"item": "wolf_pelt"}], "coin": 0, "decay_left": 3000.0, "position": [0, 0, 0]}]
	await _wait(0.3)
	var n := World.summon_corpses(p, "")
	await _wait(0.3)
	var near := 0
	var items := []
	var stranger_stayed := false
	for c in z.get_children():
		if c is Corpse:
			var cc := c as Corpse
			if cc.owner_name == p.display_name and cc.global_position.distance_to(p.global_position) < 4.0:
				near += 1
				for e: Dictionary in cc.entries:
					items.append(e["item"])
			if cc.owner_name == "Somebody" and cc.global_position.distance_to(far) < 3.0:
				stranger_stayed = true
	print("summon_corpse: moved %d, %d at your feet holding %s, the other zone's left %d, a stranger's stayed %s" % [n, near, items,
			(main._corpses_by_zone.get("thornwood", []) as Array).size(), stranger_stayed])
	for c in z.get_children():
		if c is Corpse and (c as Corpse).owner_name != "":
			World.remove_corpse(c)


## The fight you can hear (Sfx, Music): a monster's challenge, swings and
## hits by weapon, what a body rings like, a death cry, the cast hum, spells
## landing, a bow's twang and the arrow's thunk on arrival, the level-up
## fanfare, the combat sting; every voice has its three cries, and every
## monster in the game gets a voice (the spread is printed).
func _t_combat_audio() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	Sfx.heard.clear()
	p.global_position = z.ground(40, 40) + Vector3.UP
	var mobs := {}
	for id: String in ["gnoll_scout", "decaying_skeleton"]:
		var d: Dictionary = (GameData.mobs[id] as Dictionary).duplicate(true)
		d.erase("gear")
		var m := Mob.new()
		m.setup(id, d, null)
		m.aggressive = false
		m.position = z.ground(40, 37 - mobs.size() * 3) + Vector3.UP * 0.2
		z.add_child(m)
		m.set_physics_process(false)
		mobs[id] = m
	await _wait(0.3)
	var gnoll: Mob = mobs["gnoll_scout"]
	var bones: Mob = mobs["decaying_skeleton"]
	gnoll.add_hate(p, 1.0)
	bones.add_hate(p, 1.0)
	await _wait(0.1)
	var after_aggro := Sfx.heard.duplicate()
	p.animate("slash")
	gnoll.animate("sfx:hit_slash")
	bones.animate("sfx:hit_blunt!")
	await _wait(0.1)
	var after_hits := Sfx.heard.duplicate()
	p.cast = {"spell": "minor_healing" if GameData.spells.has("minor_healing") else GameData.spells.keys()[0]}
	SpellFx.update_cast(p)
	var humming := Sfx._casts.has(p)
	p.cast = {}
	SpellFx.update_cast(p)
	var heal_id := ""
	var nuke_id := ""
	for sid: String in GameData.spells:
		var kind := str(GameData.spells[sid].get("fx", {}).get("kind", ""))
		if kind == "heal" and heal_id == "":
			heal_id = sid
		if kind == "burst" and nuke_id == "":
			nuke_id = sid
	World.spell_fx.emit(p, p, heal_id)
	World.spell_fx.emit(p, gnoll, nuke_id)
	p.animate("shoot:bow_basic")
	gnoll.animate("sfx:hit_arrow@19")
	var before_arrow := Sfx.heard.count("hit_arrow")
	await _wait(0.8)
	var arrow_late := before_arrow == 0 and Sfx.heard.count("hit_arrow") == 1
	World.kill(gnoll, p)
	await _wait(0.3)
	p.level += 1
	await _wait(0.2)
	p.level -= 1
	Music._sting_at = -1000.0
	Music._set_combat(true)
	var stung := Music._sting.playing
	Music._set_combat(false)
	print("combat_audio: aggro %s" % [after_aggro])
	print("combat_audio: hits %s" % [after_hits.slice(after_aggro.size())])
	print("combat_audio: all heard %s" % [Sfx.heard])
	print("combat_audio: cast hum %s, arrow thunk late %s, sting %s" % [humming, arrow_late, stung])
	var missing := []
	for v in ["humanoid", "beast", "small", "bug", "undead", "big", "stone", "slime", "bird", "player"]:
		for w in ["hurt", "death"] + ([] if v == "player" else ["aggro"]):
			if not Sfx.has_sound("%s_%s" % [v, w]):
				missing.append("%s_%s" % [v, w])
	for snd in ["swing", "swing_light", "swing_heavy", "swing_claw", "hit_slash", "hit_pierce", "hit_blunt", "hit_claw", "hit_arrow", "crit",
			"mat_bone", "mat_stone", "mat_metal", "block", "parry", "bow_release", "sling", "cast_loop", "level_up"]:
		if not Sfx.has_sound(snd):
			missing.append(snd)
	print("combat_audio: sounds missing %s" % [missing])
	var spread := {}
	var samples := {}
	for id: String in GameData.mobs:
		var fake := Mob.new()
		fake.mob_id = id
		fake.look = {"model": str(GameData.mobs[id].get("model", ""))}
		var v := Sfx.voice_of(fake)
		spread[v] = int(spread.get(v, 0)) + 1
		if (samples.get(v, []) as Array).size() < 6:
			var l: Array = samples.get(v, [])
			l.append(id)
			samples[v] = l
		fake.free()
	print("combat_audio: voices %s" % [spread])
	for v: String in samples:
		print("combat_audio:   %s e.g. %s" % [v, samples[v]])
	for m in mobs.values():
		if is_instance_valid(m):
			(m as Node).queue_free()


## Where a quest's monsters are: the hint names a rare spawn's placeholder,
## a click on the tracker opens the map on a loose circle round the spot (it
## really holds it), the tracker line goes gold inside it; and across every
## zone, every named that carries a quest item gets a circle that holds its spot.
func _t_quest_areas() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	World._accept_quest(p, "grolthars_necklace")
	var hint := "\n".join(QuestHints.item_hint("grolthars_necklace", "grolthars_tusk_necklace", z.zone_id, p.global_position))
	print("quest_areas: hint: %s" % hint)
	var spot := Vector2.ZERO
	for e: Dictionary in z.data["spawns"]:
		if (e["pool"] as Dictionary).has("grolthar"):
			spot = Vector2(e["pos"][0], e["pos"][1])
	var a: Dictionary = QuestHints.areas("grolthars_necklace", "grolthars_tusk_necklace")[0]
	print("quest_areas: circle %s, %.0f m across, %.0f m from his spot (holds it %s)" % [a["label"], float(a["radius"]) * 2.0,
			spot.distance_to(a["center"]), spot.distance_to(a["center"]) < float(a["radius"])])
	p.global_position = Vector3(0, z.height_at(0, 0) + 1.0, 0)
	main.hud._on_quest_hint("item:grolthars_necklace:grolthars_tusk_necklace")
	await _wait(1.5)
	print("quest_areas: map open %s on the circle %s" % [main.hud._map.visible, main.hud._map._area_focus >= 0])
	await _shot("9zw_quest_area_map")
	main.hud._map.visible = false
	var c: Vector2 = a["center"]
	p.global_position = Vector3(c.x, z.surface_at(c.x, c.y) + 1.0, c.y)
	await _wait(2.5)
	print("quest_areas: tracker inside the circle: %s" % main.hud._quest_label.text.contains("(here)"))
	await _shot("9zw_quest_area_tracker")
	# every named quest-item carrier in the world: a circle holding its spot
	var missing := []
	var with_ph := 0
	var total := 0
	for zone_id: String in QuestHints.zones():
		var zd: Dictionary = QuestHints.zones()[zone_id]
		for e: Dictionary in zd.get("spawns", []):
			for mob_id: String in (e["pool"] as Dictionary):
				if not GameData.is_quest_boss(mob_id):
					continue
				var pos := Vector2(e["pos"][0], e["pos"][1])
				for qid: String in GameData.quests:
					for item_id: String in GameData.quests[qid]["wants"]:
						if not (GameData.mobs[mob_id].get("loot", []) as Array).any(func(l: Dictionary) -> bool: return str(l.get("item", "")) == item_id):
							continue
						total += 1
						if not QuestHints.areas(qid, item_id).any(func(ar: Dictionary) -> bool: return ar["zone"] == zone_id and pos.distance_to(ar["center"]) < float(ar["radius"])):
							missing.append("%s/%s" % [zone_id, mob_id])
				if not SpawnPoint.rare_spot(zd["spawns"], e).is_empty():
					with_ph += 1
	print("quest_areas: %d named quest drops, %d without a circle holding the spot %s; %d rare spots" % [total, missing.size(), missing.slice(0, 5), with_ph])
	World.request_quest_abandon(p.entity_id, "grolthars_necklace")


## Mirror Flats' salt-crust islands are solid ("hull"): you walk up the rim
## onto the plates and across, not through them, and nothing catches your feet.
func _t_salt_islands() -> void:
	var z: Zone = get_parent().zone
	var p := World.local_player
	var c := Vector2(40, 120)
	var ground := z.height_at(c.x, c.y)
	p.global_position = Vector3(c.x - 12.0, z.surface_at(c.x - 12.0, c.y) + 0.5, c.y)
	p.velocity = Vector3.ZERO
	var top := -INF
	for k in 360:  # 6 s east at 4 m/s: 24 m, right over it
		p.velocity = Vector3(4.0, p.velocity.y - 20.0 * get_physics_process_delta_time(), 0)
		p.move_and_slide()
		if absf(p.global_position.x - c.x) < 3.0:
			top = maxf(top, p.global_position.y - ground)
		if k == 170:
			p.face_toward(p.global_position + Vector3(1, 0, 0))
			await _shot("9zw_salt_island")
		await get_tree().physics_frame
	print("salt_islands: stood %.2f m over the flats on top (the plates are 0.37-0.41), crossed to %.1f m past (want 12)" % [top, p.global_position.x - c.x])


## A quest boss's spot is a rare spawn: a placeholder from its camp, the named
## one time in five (never more than 8 placeholders running), coming back five
## times as fast; group bosses and finales stand always.
func _t_rare_spawns() -> void:
	var z: Zone = get_parent().zone
	var sp: SpawnPoint = null
	var rares := 0
	for c in z.get_children():
		if c is SpawnPoint and (c as SpawnPoint).rare != "":
			rares += 1
			print("rare_spawns:   %s <- %s every %.0f s" % [(c as SpawnPoint).rare, (c as SpawnPoint).pool, (c as SpawnPoint).respawn_time])
			if (c as SpawnPoint).rare == "grolthar":
				sp = c
	if sp == null:
		print("rare_spawns: FAIL no rare spot for Grolthar")
		return
	var entry_respawn := 0.0
	for e: Dictionary in z.data["spawns"]:
		if (e["pool"] as Dictionary).has("grolthar"):
			entry_respawn = float(e.get("respawn", 60))
	SpawnPoint.always_rare = false
	var named := 0
	var streak := 0
	var worst := 0
	var placeholders := {}
	for i in 1000:
		if sp.mob != null and is_instance_valid(sp.mob):
			sp.mob.free()
		sp.mob = null
		sp.spawn()
		if sp.mob.mob_id == "grolthar":
			named += 1
			streak = 0
		else:
			placeholders[sp.mob.mob_id] = true
			streak += 1
			worst = maxi(worst, streak)
	SpawnPoint.always_rare = true
	sp.mob.free()
	sp.mob = null
	sp.spawn()  # Grolthar back where the other checks look for him
	print("rare_spawns: %d rare spots in Thornwood; Grolthar's placeholders %s, respawn %.0f -> %.0f s" % [rares, placeholders.keys(), entry_respawn, sp.respawn_time])
	print("rare_spawns: named %.0f%% of 1000 spawns, at most %d placeholders in a row" % [named / 10.0, worst])
	var always := []
	for f in ["vayukeths_step", "timirajs_table"]:
		var d: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://data/zones/%s.json" % f))
		for e: Dictionary in d["spawns"]:
			for id: String in e["pool"]:
				if id in ["fallen_breath", "morcant_the_uninvited"] or GameData.mobs[id].has("min_players"):
					always.append(id)
	print("rare_spawns: always up: %s (always_up %s, min_players %s)" % [always, GameData.mobs["fallen_breath"].get("always_up", false), always.any(func(id: String) -> bool: return GameData.mobs[id].has("min_players"))])


## Squawkzilla, the angry gull, stands by Mirror-Scholar Queenie (once Anouk)
## with a guild tag on his nameplate, and Queenie's hair is brown.
func _t_squawkzilla() -> void:
	World.time_override = 11.0
	var z: Zone = get_parent().zone
	await _wait(1.0)
	var gull: Npc = null
	var queenie: Npc = null
	for c in z.get_children():
		if c is Npc and (c as Npc).npc_id == "squawkzilla":
			gull = c
		elif c is Npc and (c as Npc).npc_id == "mirror_scholar_anouk":
			queenie = c
	var tag := ""
	if gull != null:
		for l in gull.nameplate.get_children():
			if l is Label3D:
				tag = (l as Label3D).text
	print("squawkzilla: gull %s, tag %s, %.1f m from %s, her hair %s" % [gull != null, tag, gull.distance_to(queenie) if gull and queenie else -1.0,
			queenie.display_name if queenie else "?", str(queenie.look.get("hair")) if queenie else "?"])
	await _zone_views("mirror_flats", [[Vector2(24, 386), Vector2(18, 398), "squawkzilla"]])
	# he runs rings round her and dives in now and then
	var swept := 0.0
	var nearest := 99.0
	var farthest := 0.0
	var last := 0.0
	var first := true
	for i in 150:
		await _wait(0.1)
		if gull == null or queenie == null:
			break
		var off := gull.global_position - queenie.global_position
		var a := atan2(off.z, off.x)
		if not first:
			swept += absf(wrapf(a - last, -PI, PI))
		first = false
		last = a
		var d := Vector2(off.x, off.z).length()
		nearest = minf(nearest, d)
		farthest = maxf(farthest, d)
		if i == 40 or i == 100:
			await _shot("9zw_squawkzilla_%d" % i)
	print("squawkzilla: circled %.1f turns in 15 s, %.1f to %.1f m from her" % [swept / TAU, nearest, farthest])
	# he lands now and then, and when hailed
	gull._perch_next = 0.0
	await _wait(1.5)
	var landed := gull.sitting
	var still := gull.velocity.length() < 0.1
	await _shot("9zw_squawkzilla_landed")
	gull._perch_left = 0.5
	await _wait(1.0)
	var flew := not gull.sitting
	gull.greet(World.local_player)
	await _wait(0.5)
	print("squawkzilla: landed %s (still %s), took off %s, lands when hailed %s" % [landed, still, flew, gull.sitting])
	World.time_override = -1.0


## High Terrace from the pilgrims' road toward the monastery, by day: how far the haze lets you see.
func _t_terrace_views() -> void:
	World.time_override = 13.0
	await _wait(1.0)
	await _zone_views("high_terrace", [[Vector2(-10, -90), Vector2(-1, -240), "monastery"], [Vector2(40, 60), Vector2(280, -40), "east"]])
	World.time_override = -1.0


## An arrow flies head first along its path, not standing up: its head
## (the model's +z, turned by Projectile.launch) points where it's going.
func _t_arrow_flight() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	p.global_position = z.ground(40, 40) + Vector3.UP
	p.face_toward(Vector3(40, 0, 10))
	var d: Dictionary = (GameData.mobs["gnoll_scout"] as Dictionary).duplicate(true)
	d.erase("gear")
	var mob := Mob.new()
	mob.setup("gnoll_scout", d, null)
	mob.aggressive = false
	mob.position = z.ground(40, 10) + Vector3.UP * 0.2
	z.add_child(mob)
	mob.set_physics_process(false)
	await _wait(0.5)
	Projectile.launch(p, mob, "arrow")
	await _wait(0.3)
	var arrow: Projectile = null
	for c in z.get_children():
		if c is Projectile:
			arrow = c
	if arrow == null:
		print("arrow_flight: no arrow in the air")
	else:
		var model := arrow.get_child(0) as Node3D
		var head := model.global_basis.z.normalized()  # the model's head end
		var going := (mob.global_position + Vector3.UP * 0.7 - arrow.global_position).normalized()
		print("arrow_flight: head along the flight %.2f (1 = straight at it), head up %.2f (0 = level)" % [head.dot(going), head.y])
		p.global_position = z.ground(55, 25) + Vector3.UP
		p.face_toward(arrow.global_position)
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 4.0
		p.pitch = 0.0
		for k in 3:
			Projectile.launch(mob, p, "arrow")
		await _wait(0.12)
		await _shot("9arrow_flight")
	mob.queue_free()


## The grown zones' forward camps, guard huts and places (tools/zones/hubs.py):
## in each of the three pilot zones the new quests are taken up and handed in,
## the forward camp's scout takes the hand-in of a quest someone else gave, and
## a look at the camp, a hut and each new place and monster.
func _t_hubs_pilot() -> void:
	await _hubs_zones([["thornwood", "tw", {"tw_hob_woodcutter": ["tw_tusker_tusks", "tw_old_greyback"], "tw_corporal_brannic": ["tw_prayer_beads", "tw_brother_vesk"]},
			["tw_tusker_boar", "tw_old_greyback", "tw_forsworn_acolyte", "tw_brother_vesk"], "tw_corporal_brannic", "bloodtusk_tusks"],
			["the_long_grass", "lg", {"lg_outrider_temperance": ["lg_stone_chips", "lg_ringwarden"], "lg_herdwife_saule": ["lg_jackal_ears", "lg_old_rakemaw"]},
			["lg_ringstone_sentinel", "lg_ringwarden", "lg_carrion_jackal", "lg_old_rakemaw"], "lg_outrider_temperance", "stalker_pelt_q"],
			["the_bleach", "bl", {"bl_outrider_kofi": ["bl_mine_tags", "bl_foreman_dask"], "bl_trader_oyelowo": ["bl_crab_claws", "bl_wreck_shell"]},
			["bl_brine_miner", "bl_foreman_dask", "bl_wreck_crab", "bl_wreck_shell"], "bl_outrider_kofi", "the_salt_wolf"]])


## The same for the four other 1024 m zones (hubs.py batch 2).
func _t_hubs_1024() -> void:
	await _hubs_zones([["the_burn", "burn", {"burn_ashrunner_beppe": ["burn_kindled_husk_q", "burn_kindled_deacon_q"],
			"burn_prospector_renske": ["burn_cinder_newt_q", "burn_old_blisterback_q"]},
			["burn_kindled_husk", "burn_kindled_deacon", "burn_cinder_newt", "burn_old_blisterback"], "burn_ashrunner_beppe", "giants_coals"],
			["mirror_flats", "mf", {"mf_skiffscout_imara": ["mf_drowned_salter_q", "mf_skiffmaster_dunmore_q"], "mf_glassseeker_wenzel": ["mf_saltglass_sentinel_q", "mf_pillarmother_q"]},
			["mf_drowned_salter", "mf_skiffmaster_dunmore", "mf_saltglass_sentinel", "mf_pillarmother"], "mf_skiffscout_imara", "nomad_veil_q"],
			["ivory_field", "if", {"if_pathfinder_anselm": ["if_starving_shade_q", "if_hollow_mahout_q"], "if_bonecarver_ulrike": ["if_marrow_beetle_q", "if_marrow_queen_q"]},
			["if_starving_shade", "if_hollow_mahout", "if_marrow_beetle", "if_marrow_queen"], "if_pathfinder_anselm", "ivory_shard_q"],
			["reedmere", "rm", {"rm_reedwatcher_achebe": ["rm_drowned_ringer_q", "rm_bellwarden_q"], "rm_fisher_makena": ["rm_weir_eel_q", "rm_eel_mother_q"]},
			["rm_drowned_ringer", "rm_bellwarden", "rm_weir_eel", "rm_eel_mother"], "rm_reedwatcher_achebe", "pondkin_fetishes"]])


## And the first four 768 m zones (hubs.py batch 3).
func _t_hubs_768a() -> void:
	await _hubs_zones([["silted_reach", "sr", {"sr_channelwatch_ioana": ["sr_delta_toad_q", "sr_gulmog_q"], "sr_herbalist_ama": ["sr_mangrove_lurker_q", "sr_old_tanglefoot_q"]},
			["sr_delta_toad", "sr_gulmog", "sr_mangrove_lurker", "sr_old_tanglefoot"], "sr_channelwatch_ioana", "whisker_barbel_q"],
			["blackglass", "bg", {"bg_glasswalker_hrafn": ["bg_obsidian_borer_q", "bg_sable_borer_q"], "bg_glassdiviner_tovi": ["bg_glass_wisp_q", "bg_prism_heart_q"]},
			["bg_obsidian_borer", "bg_sable_borer", "bg_glass_wisp", "bg_prism_heart"], "bg_glasswalker_hrafn", "drake_scales"],
			["smokewood", "sw", {"sw_woodrunner_kasia": ["sw_spore_shambler_q", "sw_rotcap_q"], "sw_charcoal_burner_ottokar": ["sw_kiln_imp_q", "sw_old_bellows_q"]},
			["sw_spore_shambler", "sw_rotcap", "sw_kiln_imp", "sw_old_bellows"], "sw_woodrunner_kasia", "smoke_pelt_q"],
			["stonesail", "ss", {"ss_moorrunner_edric": ["ss_moor_harrier_q", "ss_old_talonmere_q"], "ss_stonereader_mabyn": ["ss_cairn_wight_q", "ss_cairn_king_q"]},
			["ss_moor_harrier", "ss_old_talonmere", "ss_cairn_wight", "ss_cairn_king"], "ss_moorrunner_edric", "moor_hide_q"]])


## And the rest of the 768 m zones (hubs.py batch 4).
func _t_hubs_768b() -> void:
	await _hubs_zones([["hollow_air", "ha", {"ha_skyrunner_odile": ["ha_cloud_ray_q", "ha_old_stormbarb_q"], "ha_kitewright_sunniva": ["ha_gale_sprite_q", "ha_gustmother_q"]},
			["ha_cloud_ray", "ha_old_stormbarb", "ha_gale_sprite", "ha_gustmother"], "ha_skyrunner_odile", "tempest_mote_q"],
			["fogfall", "ff", {"ff_lanternrunner_quill": ["ff_fog_wraith_q", "ff_veiled_chaplain_q"], "ff_quarryman_bertil": ["ff_rubble_golem_q", "ff_old_cairnback_q"]},
			["ff_fog_wraith", "ff_veiled_chaplain", "ff_rubble_golem", "ff_old_cairnback"], "ff_lanternrunner_quill", "gargoyle_stone_q"],
			["the_unlit", "un", {"un_lampbearer_ines": ["un_morvaine_hound_q", "un_blackfang_q"], "un_wellwarden_oriel": ["un_well_wisp_q", "un_pale_keeper_q"]},
			["un_morvaine_hound", "un_blackfang", "un_well_wisp", "un_pale_keeper"], "un_lampbearer_ines", "shade_essence_q"],
			["lastwalk", "lw", {"lw_vigilrunner_tamsin": ["lw_blade_sentinel_q", "lw_blades_warden_q"], "lw_excavator_ingrith": ["lw_godwar_hound_q", "lw_ashfang_q"]},
			["lw_blade_sentinel", "lw_blades_warden", "lw_godwar_hound", "lw_ashfang"], "lw_vigilrunner_tamsin", "godwar_insignia_q"],
			["high_terrace", "ht", {"ht_pilgrim_lobsang": ["ht_forsaken_pilgrim_q", "ht_unshriven_q"], "ht_herder_dolkar": ["ht_high_wolf_q", "ht_old_frostjaw_q"]},
			["ht_forsaken_pilgrim", "ht_unshriven", "ht_high_wolf", "ht_old_frostjaw"], "ht_pilgrim_lobsang", "tenzins_beads"]])


## The smaller open zones' places (hubs.py batch 5): no forward camp, one place and its npc each.
func _t_hubs_small() -> void:
	var legs: Array = []
	for row: Array in [["greenmoor", "gm", "gm_farmwife_gudrun", "gm_grain_weevil", "gm_granary_queen"], ["harrowfield", "hf", "hf_crofter_ewan", "hf_field_crow", "hf_old_blackwing"],
			["hollowmere", "hm", "hm_reedcutter_olwen", "hm_marsh_gnats", "hm_droning_mother"], ["dewstep", "ds", "ds_tea_roller_sunita", "ds_bamboo_viper", "ds_jade_eye"],
			["sunward_steps", "su", "su_water_seeker_anil", "su_dust_scarab", "su_old_dunebore"], ["weeping_throat", "wt", "wt_tracker_mbali", "wt_rain_panther", "wt_silkpaw"],
			["cinderpass", "cp", "cp_carter_hodd", "cp_ash_beetle", "cp_cinderback"], ["windbreak", "wb", "wb_arch_warden_petra", "wb_crag_lizard", "wb_old_sunbask"],
			["the_wallow", "wl", "wl_bog_wife_grunna", "wl_bog_crawdad", "wl_old_pinchmud"], ["duskwood", "dk", "dk_moth_seer_lirael", "dk_duskwing", "dk_pale_mothmother"],
			["the_rotfen", "rf", "rf_fen_priest_orun", "rf_bloated_dead", "rf_barge_warden"], ["broken_march", "bm", "bm_beacon_keeper_hesk", "bm_cairn_raven", "bm_grimquill"]]:
		var race: String = {"the_wallow": "troll", "duskwood": "dark_elf"}.get(row[0], "human")  # the evil homelands' folk won't talk to a human
		legs.append([row[0], row[1], {row[2]: [row[3] + "_q", row[4] + "_q"]}, [row[3], row[4]], "", "", race])
	await _hubs_zones(legs)


func _hubs_zones(legs: Array) -> void:
	var main := get_parent()
	var p := World.local_player
	p.god_mode = true
	for leg: Array in legs:
		while main._changing_zone:
			await _wait(0.25)
		if main.zone.zone_id != leg[0]:
			World.zone_change.emit(p, leg[0], Vector2.INF, Vector2.INF)
			for k in 160:
				if (main.zone as Zone).zone_id == leg[0] and not main._changing_zone:
					break
				await _wait(0.25)
		await _wait(1.0)
		var z: Zone = main.zone
		var tag := "hubs_%s" % leg[1]
		if leg.size() > 6 and p.race != str(leg[6]):
			p.race = str(leg[6])
			World.apply_alignment(p)
		var on_ground := 0
		var npcs := _npcs()
		for n: Dictionary in z.data["npcs"]:
			if n.get("hubs", false) and npcs.has(n["id"]):
				var at: Vector3 = (npcs[n["id"]] as Npc).global_position
				on_ground += 1 if absf(at.y - z.surface_at(at.x, at.z)) < 1.5 else 0
		print("%s: %d new npcs, %d standing on the ground" % [tag, z.data["npcs"].filter(func(n: Dictionary) -> bool: return n.get("hubs", false)).size(), on_ground])
		await _zone_life(tag, leg[2], [], leg[3])
		if str(leg[4]) == "":  # a smaller zone has no forward camp
			continue
		# a quest someone else gave, handed in at the forward camp
		var scout: Npc = _npcs()[leg[4]]
		var q_id: String = leg[5]
		var q: Dictionary = GameData.quests[q_id]
		p.quests[q_id] = {"active": true, "completions": 0}
		for i in p.pack.slots.size():
			p.pack.slots[i] = {}
		for item_id: String in q["wants"]:
			p.pack.add(item_id, int(q["wants"][item_id]))
		_stand_by(p, scout)
		var mark := World.quest_mark(p, scout.npc_id)
		await _hand_in(p, scout, (q["wants"] as Dictionary).keys())
		print("%s: %s's quest %s handed in to %s (mark was '%s') -> done %d time(s)" % [tag, QuestHints._npc_name(str(q["giver"])), q_id, scout.display_name, mark,
				int(p.quests.get(q_id, {}).get("completions", 0))])
		print("%s: hint -> %s" % [tag, QuestHints.giver_hint(q_id, z.zone_id, p.global_position)])
		var views: Array = []
		for lm: Dictionary in z.data["landmarks"]:
			if lm.get("hubs", false) and str(lm["type"]) in ["waystation", "outpost", "cabin", "ruins", "watchtower"]:
				views.append([Vector2(lm["pos"][0], lm["pos"][1]) + Vector2(18, 16), Vector2(lm["pos"][0], lm["pos"][1]), "%s_%d" % [lm["type"], views.size()]])
		await _zone_views(tag, views)
	if p.race != "human":
		p.race = "human"
		World.apply_alignment(p)
	p.god_mode = false


## Named monsters by one rule (config named_health, named_damage) and
## growing with the fight: a second player grouped with the first, close by,
## raises its health (its wounds kept as a share) and a little its damage; it
## doesn't shrink when they leave, and goes back to its own size on a reset.
## Morcant faces at least three even alone.
func _t_named_scaling() -> void:
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	p.god_mode = true
	var d: Dictionary = (GameData.mobs["raider_chief"] as Dictionary).duplicate(true)
	d.erase("gear")
	var mob := Mob.new()
	mob.setup("raider_chief", d, null)
	print("named_scaling: Vashti at %d: health %d (an ordinary monster there %d, x%.2f), hits %d-%d every %.1f s (ordinary %.1f a second, x%.2f)" % [mob.level, mob.max_hp,
			GameData.typical_hp(mob.level), mob.max_hp / GameData.typical_hp(mob.level), mob.dmg_min, mob.dmg_max, mob.attack_delay, GameData.typical_dps(mob.level),
			(mob.dmg_min + mob.dmg_max) * 0.5 / mob.attack_delay / GameData.typical_dps(mob.level)])
	mob.aggressive = false
	mob.position = z.ground(p.global_position.x + 4.0, p.global_position.z) + Vector3.UP * 0.2
	z.add_child(mob)
	var solo := mob.max_hp
	mob.add_hate(p, 1.0)
	await _wait(1.5)
	print("named_scaling: alone -> facing %d, health %d" % [mob.facing_players, mob.max_hp])
	mob.hp = int(mob.max_hp * 0.6)
	var q := Player.new()
	q.from_save({"name": "Helper", "class": "cleric", "level": 21, "stats": {}, "race": "human"})
	q.position = p.global_position + Vector3(-8, 0, 0)
	z.add_child(q)
	q.god_mode = true
	await _wait(0.2)
	World.groups[9901] = {"leader": p.entity_id, "members": [p.entity_id, q.entity_id]}
	p.group_id = 9901
	q.group_id = 9901
	await _wait(1.5)
	print("named_scaling: a groupmate 8 m off -> facing %d, health %d (x%.2f of alone), wounds %.0f%%, hits %d-%d" % [mob.facing_players, mob.max_hp, float(mob.max_hp) / solo,
			100.0 - 100.0 * mob.hp / mob.max_hp, mob.dmg_min, mob.dmg_max])
	print("named_scaling: its experience grows by x%.2f (health x%.2f)" % [World.named_growth(mob), float(mob.max_hp) / solo])
	World.groups.erase(9901)
	p.group_id = 0
	q.group_id = 0
	await _wait(1.5)
	print("named_scaling: the groupmate leaves -> facing %d (never shrinks mid-fight)" % mob.facing_players)
	mob._reset()
	print("named_scaling: reset -> facing %d, health %d" % [mob.facing_players, mob.max_hp])
	mob.queue_free()
	q.queue_free()
	var boss := Mob.new()
	var bd: Dictionary = (GameData.mobs["the_uninvited"] as Dictionary).duplicate(true)
	boss.setup("the_uninvited", bd, null)
	print("named_scaling: Morcant alone -> facing %d, health %d (x%.1f an ordinary level %d monster)" % [boss.facing_players, boss.max_hp, boss.max_hp / GameData.typical_hp(boss.level), boss.level])
	boss.free()
	p.god_mode = false


## The zones' uneven mountain edges (tools/zones/outline.py): in every
## outdoor zone nothing placed stands under a ridge (npcs, the bind point,
## landmarks, arrivals from other zones), and in a few built zones every
## spawn stands on open ground and each zone line's pass is still low enough
## to walk; each built zone's map is saved to look at the shape.
func _t_zone_outlines() -> void:
	var main := get_parent()
	var p := World.local_player
	var outlines: Dictionary = GameData._load("res://data/zone_outlines.json")
	var arrivals := {}
	for f: String in DirAccess.get_files_at("res://data/zones"):
		for zl: Dictionary in GameData.load_zone(f.get_basename()).get("zone_lines", []):
			if zl.get("arrive") is Array:
				(arrivals.get_or_add(str(zl["to"]), []) as Array).append(Vector2(zl["arrive"][0], zl["arrive"][1]))
	var buried := 0
	for id: String in outlines:
		var d := GameData.load_zone(id)
		var z := Zone.new()
		z.half = float(d.get("size", 384)) * 0.5
		var ext: Array = d.get("extent", [z.half * 2.0, z.half * 2.0])
		z.half_x = float(ext[0]) * 0.5
		z.half_z = float(ext[1]) * 0.5
		z._outline = outlines[id]
		var pts: Array = [[Vector2(d.get("bind_point", [0, 0])[0], d.get("bind_point", [0, 0])[1]), "bind point"]]
		for n: Dictionary in d.get("npcs", []):
			pts.append([Vector2(n["pos"][0], n["pos"][1]), str(n["id"])])
		for lm: Dictionary in d.get("landmarks", []):
			pts.append([Vector2(lm["pos"][0], lm["pos"][1]), str(lm["type"])])
		for at: Vector2 in arrivals.get(id, []):
			pts.append([at, "arrival"])
		for pt: Array in pts:
			var now := z.edge_depth(pt[0].x, pt[0].y)
			var square := maxf(absf(pt[0].x) - (z.half_x - 28.0), absf(pt[0].y) - (z.half_z - 28.0))  # a pass's signpost, a city's wall stood in the ring already
			if now > -8.0 and now > square + 0.5:
				buried += 1
				print("zone_outlines:   %s: %s at %s is under a ridge (%.1f)" % [id, pt[1], pt[0], now])
		z.free()
	print("zone_outlines: %d outlined zones, %d things under a ridge" % [outlines.size(), buried])
	var hud: Hud = main.hud
	World.time_override = 12.0
	for zone_id: String in ["greenmoor", "thornwood", "harrowfield", "the_long_grass", "stonesail", "stormcut_gorge"]:
		while main._changing_zone:
			await _wait(0.25)
		var started := Time.get_ticks_msec()
		World.zone_change.emit(p, zone_id, Vector2.INF, Vector2.INF)
		for k in 160:
			if (main.zone as Zone).zone_id == zone_id and not main._changing_zone:
				break
			await _wait(0.25)
		var z := main.zone as Zone
		print("zone_outlines: %s (%d m) built in about %.1f s, %d monsters" % [zone_id, int(z.size), (Time.get_ticks_msec() - started) / 1000.0,
				World.get_mobs().filter(func(m: Mob) -> bool: return World.zone_of(m) == z).size()])
		await _wait(1.0)
		var covered := 0
		var moved := 0
		for sp: Node in z.get_children():
			if sp is SpawnPoint:
				var at := Vector2(sp.global_position.x, sp.global_position.z)
				if z.edge_depth(at.x, at.y) > -4.0:
					covered += 1
				if not z.data.get("spawns", []).any(func(e: Dictionary) -> bool: return Vector2(e["pos"][0], e["pos"][1]).distance_to(at) < 0.5):
					moved += 1
		var steep := 0
		for zl: Dictionary in z.data.get("zone_lines", []):
			var at := Vector2(zl["pos"][0], zl["pos"][1])
			var inward := -at.normalized() * 40.0
			var rise := z.height_at(at.x, at.y) - z.height_at(at.x + inward.x, at.y + inward.y)
			if rise > 12.0:
				steep += 1
				print("zone_outlines:   %s: the pass to %s climbs %.1f m in 40 m" % [zone_id, zl["to"], rise])
		print("zone_outlines: %s: spawns under a ridge %d, walked off one %d, steep passes %d" % [zone_id, covered, moved, steep])
		# the foot of the mountains, all the way round: too steep to climb except in a pass
		var climbable := 0
		var tallest := 0.0
		var lowest := 999.0
		var along := -z.half + 4.0
		while along < z.half - 4.0:
			for side: Array in [[Vector2(along, 0), Vector2(0, -1), z.half_x, z.half_z], [Vector2(along, 0), Vector2(0, 1), z.half_x, z.half_z],
					[Vector2(0, along), Vector2(1, 0), z.half_z, z.half_x], [Vector2(0, along), Vector2(-1, 0), z.half_z, z.half_x]]:
				if absf(along) > float(side[2]) - 4.0:  # past the end of a shorter side
					continue
				var out: Vector2 = side[1]
				var at: Vector2 = side[0] + out * (float(side[3]) - 1.0)
				var walked := 0
				while z.edge_depth(at.x, at.y) > 0.0 and walked < int(side[3]):  # in to the foot (a corner's other side may hold it all the way)
					at -= out
					walked += 1
				if walked >= int(side[3]) or z._pass_factor(at.x, at.y) < 1.0:
					continue
				var up := Vector2(z.edge_depth(at.x + 0.5, at.y) - z.edge_depth(at.x - 0.5, at.y), z.edge_depth(at.x, at.y + 0.5) - z.edge_depth(at.x, at.y - 0.5)).normalized()  # into the mountains, the steepest way
				var worst := 99.0
				var where := at
				for k in 5:
					var a := at + up * (1.5 + k * 2.5)
					if z.edge_depth(a.x, a.y) > Zone.MOUNTAIN_BAND - 1.5:  # past the steep band: only reached by climbing it
						break
					var grad := Vector2(z.height_at(a.x + 1.0, a.y) - z.height_at(a.x - 1.0, a.y), z.height_at(a.x, a.y + 1.0) - z.height_at(a.x, a.y - 1.0)) / 2.0
					if grad.length() < worst:
						worst = grad.length()
						where = a
				if worst < 1.0:
					climbable += 1
					if climbable <= 5:
						print("zone_outlines:   %s: a slope of %.2f at %s" % [zone_id, worst, where.snapped(Vector2.ONE)])
				var top := z.height_at(at.x + up.x * 26.0, at.y + up.y * 26.0) - z.height_at(at.x, at.y)
				tallest = maxf(tallest, top)
				lowest = minf(lowest, top)
			along += 8.0
		print("zone_outlines: %s: the mountains' foot climbable at %d spots; 26 m in they stand %.0f to %.0f m over it" % [zone_id, climbable, lowest, tallest])
		var map: MapWindow = hud._map
		for k in 4000:
			if map._painted.has(zone_id):
				break
			map._paint_some(z)
		if shots_dir != "" and map._painted.has(zone_id):
			(map._painted[zone_id] as ImageTexture).get_image().save_png("%s/9outline_%s.png" % [shots_dir, zone_id])
		p.global_position = z.ground(z.bind_point.x, z.bind_point.z) + Vector3.UP * 2.0
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 9.0
		p.pitch = -0.15
		for dir: Vector2 in [Vector2(0, -1), Vector2(1, 0)]:
			p.face_toward(p.global_position + Vector3(dir.x, 0, dir.y))
			await _wait(1.2)
			await _shot("9outline_%s_%s" % [zone_id, "north" if dir.y < 0 else "east"])
	# the range between Greenmoor and Thornwood from both sides of the pass
	for view: Array in [["greenmoor", Vector2(-40, -120), Vector2(-40, -400)], ["thornwood", Vector2(40, 400), Vector2(40, 900)],
			["stormcut_gorge", Vector2(60, 330), Vector2(20, -400)], ["stormcut_gorge", Vector2(-20, -300), Vector2(20, 400)]]:
		while main._changing_zone:
			await _wait(0.25)
		World.zone_change.emit(p, view[0], view[1], view[2])
		for k in 160:
			if (main.zone as Zone).zone_id == view[0] and not main._changing_zone:
				break
			await _wait(0.25)
		await _wait(2.0)
		var z := main.zone as Zone
		p.global_position = z.ground(view[1].x, view[1].y) + Vector3.UP * 2.0
		p.face_toward(Vector3(view[2].x, 0, view[2].y))
		p.camera_pivot.rotation.y = 0.0
		p.zoom = 9.0
		p.pitch = -0.1
		await _wait(1.5)
		await _shot("9outline_border_%s_%d" % [view[0], int(view[1].y)])
	World.time_override = -1.0


## Gear that climbs with the mob wearing it: what a level 1 skeleton, a level
## 15 and 17 sun cultist and a level 46 revenant spawn wearing, rolled many
## times through the real World.roll_gear (tiered tables, then the ladders).
func _t_item_ladder() -> void:
	for pair: Array in [["decaying_skeleton", 1], ["sun_cultist", 15], ["sun_cultist", 17], ["godwar_revenant", 46]]:
		var data: Dictionary = GameData.mobs[pair[0]]
		var seen := {}
		var lowest := 99
		for k in 400:
			var gear := World.roll_gear(data, int(pair[1]))
			for slot: String in gear:
				var base := GameData.base_item(str(gear[slot]))
				seen[base] = true
				lowest = mini(lowest, int(GameData.item(base).get("rec_level", 0)))
		var names: Array = seen.keys()
		names.sort()
		print("item_ladder: %s at %d wears (lowest rec %d): %s" % [pair[0], pair[1], lowest, names])


## The beginners' calm monsters, levels 1 to 5, in each starting zone.
func _t_starter_spawns() -> void:
	for zone_id: String in ["greenmoor", "the_wallow", "duskwood", "dewstep"]:
		var d := GameData.load_zone(zone_id)
		var calm := 0.0
		var quick := 0
		for sp: Dictionary in d.get("spawns", []):
			if sp.get("when", "") == "night":
				continue
			var pool: Dictionary = sp["pool"]
			var total := 0.0
			for w: Variant in pool.values():
				total += float(w)
			for mob_id: String in pool:
				var m: Dictionary = GameData.mobs.get(mob_id, {})
				if not m.get("aggressive", true) and not m.get("named", false) and int((m.get("level", [0, 0]) as Array)[0]) <= 5:
					calm += float(pool[mob_id]) / total
			if float(sp.get("respawn", 60)) <= 30.0:
				quick += 1
		print("starter_spawns: %s: %.0f calm beginners' monsters, %d spots back in 30 s" % [zone_id, calm, quick])


func _t_quest_marks() -> void:
	var p := World.local_player
	var holt: Npc = _npcs()["warden_holt"]
	var keep := [p.quests.duplicate(true), p.factions.duplicate()]
	var mark := func() -> String:
		holt._mark_check = 0.0
		holt._update_mark(0.016)
		return holt._mark.text if holt._mark.visible else "(none)"
	p.quests.clear()
	print("quest_marks: fresh -> '%s' (gray %s)" % [mark.call(), holt._mark_more])
	_stand_by(p, holt)
	p.global_position += Vector3(0, 0, 4)
	p.face_toward(holt.global_position)
	await _wait(0.6)
	await _shot("9quest_mark_bang")
	# one of an npc's two quests taken, the other still to ask for: the "!" goes gray, and a hail names the word
	var gudrun: Npc = _npcs()["gm_farmwife_gudrun"]
	var hers: Array = World._quests_of_npc("gm_farmwife_gudrun")
	World._accept_quest(p, hers[0])
	gudrun._mark_check = 0.0
	gudrun._update_mark(0.016)
	print("quest_marks: one of Gudrun's %d taken -> '%s' (gray %s)" % [hers.size(), gudrun._mark.text if gudrun._mark.visible else "(none)", gudrun._mark_more])
	var heard: Array[String] = []
	var listen := func(t: String, _c: Color) -> void: heard.append(t)
	World.log_message.connect(listen)
	_stand_by(p, gudrun)
	World.request_say(p.entity_id, "hail")
	await _wait(0.3)
	World.log_message.disconnect(listen)
	print("quest_marks: hailed her -> %s" % [heard.filter(func(t: String) -> bool: return "There's more" in t)])
	_stand_by(p, holt)
	for quest_id: String in World._quests_of_npc("warden_holt"):
		if str(GameData.quests[quest_id].get("start_keyword", "")) != "":
			World._accept_quest(p, quest_id)
	print("quest_marks: every quest of his taken -> '%s'" % mark.call())
	p.pack.add_entry(Pack.entry("gnoll_fang", 4))
	print("quest_marks: carrying four gnoll fangs -> '%s'" % mark.call())
	await _wait(0.3)
	await _shot("9quest_mark_ready")
	p.pack.remove("gnoll_fang", 4)
	for quest_id: String in World._quests_of_npc("warden_holt"):
		p.quests[quest_id] = {"active": false, "completions": 1}
	print("quest_marks: all done -> '%s'" % mark.call())
	p.quests.clear()
	p.factions[str(holt.faction)] = -3000
	print("quest_marks: at -3000 with %s -> '%s'" % [holt.faction, mark.call()])
	var marked := 0
	for n: Npc in _npcs().values():
		if n._mark != null:
			marked += 1
	print("quest_marks: %d npcs here can show a mark" % marked)
	p.quests = keep[0]
	p.factions = keep[1]


func _t_login_home() -> void:
	var main := get_parent()
	var p := World.local_player
	var keep := [p.race, p.deity, p.bind_zone, p.home_seen, p.factions.duplicate(), p.alignment_mods.duplicate()]
	var go := func(zone_id: String, at: Vector2) -> void:
		while main._changing_zone:
			await _wait(0.25)
		World.zone_change.emit(p, zone_id, at, Vector2.ZERO)
		for k in 80:
			if (main.zone as Zone).zone_id == zone_id and not main._changing_zone:
				break
			await _wait(0.25)
		await _wait(0.5)
	var login := func(label: String, race: String, zone_id: String, at: Vector2, bind: String, seen: String) -> void:
		await go.call(zone_id, at)
		p.race = race
		p.deity = "dark"
		p.bind_zone = bind
		p.home_seen = seen
		p.factions = {}
		p.alignment_mods = {}
		World.player_entered(p)
		await _wait(1.5)
		for k in 40:
			if not main._changing_zone:
				break
			await _wait(0.25)
		await _wait(0.5)
		print("login_home: %s -> in %s, bound in %s" % [label, (main.zone as Zone).zone_id, World.bind_zone_of(p)])
	await login.call("a troll in Rainhold, first login since the move", "troll", "rainhold", Vector2(0, 40), "rainhold", "")
	await login.call("a dark elf in Emberhold, bound there", "dark_elf", "emberhold", Vector2(0, 10), "emberhold", "duskhold")
	await login.call("a troll visiting Rainhold, already moved", "troll", "rainhold", Vector2(0, 40), "murkhold", "murkhold")
	await login.call("a human in Emberhold", "human", "emberhold", Vector2(0, 10), "emberhold", "emberhold")
	p.race = keep[0]
	p.deity = keep[1]
	p.bind_zone = keep[2]
	p.home_seen = keep[3]
	p.factions = keep[4]
	p.alignment_mods = keep[5]


## Logging in inside a city's room (the Ember and Anvil) counts as being in
## that city: an evil character left in the tavern from before alignment goes
## home instead of walking out into the guards; a human stays at the bar.
func _t_login_tavern() -> void:
	var main := get_parent()
	var p := World.local_player
	var keep := [p.race, p.deity, p.bind_zone, p.home_seen, p.factions.duplicate(), p.alignment_mods.duplicate()]
	print("login_tavern: the tavern is part of %s, the crypt of %s, Duskhold of %s" % [World.city_of("emberhold_tavern"), World.city_of("emberhold_crypt"), World.city_of("duskhold")])
	for row: Array in [["a dark elf in the tavern, first login since the move", "dark_elf", "", ""], ["a human in the tavern", "human", "emberhold", "emberhold"]]:
		while main._changing_zone or p.dead:  # login_home can leave the tester slain by a guard: the dead aren't sent home
			await _wait(0.25)
		while main._changing_zone:
			await _wait(0.25)
		World.zone_change.emit(p, "emberhold_tavern", Vector2(0, 0), Vector2.ZERO)
		for k in 80:
			if (main.zone as Zone).zone_id == "emberhold_tavern" and not main._changing_zone:
				break
			await _wait(0.25)
		await _wait(0.5)
		p.race = row[1]
		p.deity = "dark"
		p.bind_zone = row[2]
		p.home_seen = row[3]
		p.factions = {}
		p.alignment_mods = {}
		World.player_entered(p)
		await _wait(1.5)
		for k in 40:
			if not main._changing_zone:
				break
			await _wait(0.25)
		await _wait(0.5)
		print("login_tavern: %s -> in %s, bound in %s" % [row[0], (main.zone as Zone).zone_id, World.bind_zone_of(p)])
	p.race = keep[0]
	p.deity = keep[1]
	p.bind_zone = keep[2]
	p.home_seen = keep[3]
	p.factions = keep[4]
	p.alignment_mods = keep[5]


func _t_dusk_gods() -> void:
	var main := get_parent()
	var p := World.local_player
	var table := {}
	for race: String in ["dark_elf", "human", "troll"]:
		table[race] = GameData.deities.keys().filter(func(d: String) -> bool: return GameData.deity_allows(d, race))
	print("dusk_gods: who takes whom %s" % [table])
	var keep := [p.race, p.deity, p.char_class, p.level, p.factions.duplicate(), p.alignment_mods.duplicate(), p.bind_zone]
	p.race = "dark_elf"
	p.char_class = "necromancer"
	p.level = 20
	p.factions = {}
	p.alignment_mods = {}
	World.apply_alignment(p)
	# the poison: the same dot from a follower of Timiraj and of Tantuvi
	var mob: Mob = null
	for m in World.get_mobs():
		if not m.dead and (mob == null or p.distance_to(m) < p.distance_to(mob)):
			mob = m
	var ticks := {}
	for god: String in ["dark", "web"]:
		p.deity = god
		p.recalc_stats()
		World._land(p, "venom_bolt", mob, GameData.spells["venom_bolt"], 0)
		for d: Dictionary in mob.dots:
			if d["spell"] == "venom_bolt" and d["caster_id"] == p.entity_id:
				ticks[god] = d["damage"]
		mob.dots.clear()
	print("dusk_gods: venom_bolt per tick -> Timiraj %s, Tantuvi %s" % [ticks.get("dark"), ticks.get("web")])
	p.deity = "moth"
	var m0 := p.max_mana
	p.recalc_stats()
	p.deity = "dark"
	p.recalc_stats()
	var m1 := p.max_mana
	p.deity = "moth"
	p.recalc_stats()
	print("dusk_gods: max mana Timiraj %d, Dipanti %d" % [m1, p.max_mana])
	# the priests
	while main._changing_zone:
		await _wait(0.25)
	World.zone_change.emit(p, "duskhold", Vector2(0, -20), Vector2(0, 0))
	for k in 80:
		if (main.zone as Zone).zone_id == "duskhold" and not main._changing_zone:
			break
		await _wait(0.25)
	await _wait(1.0)
	var npcs := _npcs()
	var lines: Array = []
	var grab := func(t: String, _c: Color) -> void: lines.append(t)
	World.log_message.connect(grab)
	for pair: Array in [["dusk_priest_tantuvi", "web", "tantuvi_blessing"], ["dusk_priest_dipanti", "moth", "dipanti_blessing"]]:
		var priest: Npc = npcs.get(pair[0])
		if priest == null:
			print("dusk_gods: %s missing" % pair[0])
			continue
		_stand_by(p, priest)
		p.deity = "dark"
		p.cooldowns.erase("blessed_" + str(pair[2]))
		World._talk(p, priest, "blessing")
		var refused := not p.buffs.has(pair[2])
		p.deity = pair[1]
		World._talk(p, priest, "blessing")
		p.bind_zone = ""
		World._talk(p, priest, "bind")
		print("dusk_gods: %s -> refuses Timiraj's %s, blesses her own %s, binds -> %s" % [priest.display_name, refused, p.buffs.has(pair[2]), p.bind_zone])
		p.buffs.erase(pair[2])
	World.log_message.disconnect(grab)
	await _zone_views("dusk_gods", [[Vector2(0, -34), Vector2(0, 0), "island"], [Vector2(-10, -12), Vector2(-10, 2), "tantuvi"],
			[Vector2(10, -12), Vector2(10, 2), "dipanti"]])
	p.race = keep[0]
	p.deity = keep[1]
	p.char_class = keep[2]
	p.level = keep[3]
	p.factions = keep[4]
	p.alignment_mods = keep[5]
	p.bind_zone = keep[6]
	p.recalc_stats()


func _t_evil_gods() -> void:
	var table := {}
	for race: String in ["human", "high_elf", "dark_elf", "troll"]:
		table[race] = GameData.deities.keys().filter(func(d: String) -> bool: return GameData.deity_allows(d, race))
	print("evil_gods: who takes whom %s" % [table])
	var p := World.local_player
	var hud: Node = get_tree().get_first_node_in_group("hud")
	var keep := [p.race, p.deity, p.factions.duplicate(), p.alignment_mods.duplicate()]
	p.race = "troll"
	p.deity = "fire"
	var lines: Array = []
	var grab := func(t: String, _c: Color) -> void: lines.append(t)
	World.log_message.connect(grab)
	World._check_deity(p)
	await _wait(0.5)
	var offered: Array = hud._deity_row.get_children().filter(func(b: Node) -> bool: return not b.is_queued_for_deletion()).map(func(b: Button) -> String: return b.text)
	print("evil_gods: a troll of Agnavar -> window %s, offered %s" % [hud._deity_panel.visible, offered])
	(hud._deity_row.get_child(offered.find("Mahishra")) as Button).pressed.emit()
	await _wait(0.2)
	await _shot("9evil_gods_window")
	World.request_change_deity(p.entity_id, "light")
	print("evil_gods: asked for Prabhagaj -> deity %s" % p.deity)
	var hp0 := p.max_hp
	World.request_change_deity(p.entity_id, "horn")
	await _wait(0.5)
	print("evil_gods: asked for Mahishra -> deity %s, max hp %d -> %d, window %s" % [p.deity, hp0, p.max_hp, hud._deity_panel.visible])
	World.request_change_deity(p.entity_id, "dark")
	print("evil_gods: asked again with a god who takes them -> deity %s (no second change)" % p.deity)
	World.log_message.disconnect(grab)
	print("evil_gods: lines %s" % [lines])
	p.race = keep[0]
	p.deity = keep[1]
	p.factions = keep[2]
	p.alignment_mods = keep[3]
	p.recalc_stats()


func _t_delete_guild() -> void:
	var gs := World.guilds()
	for k: String in ["delete test"]:
		if gs.guilds.has(k):
			gs.disband(k)
	gs.found("Delete Test", {"name": "Aleader"})
	gs.join("delete test", {"name": "Bmember"}, "member")
	gs.join("delete test", {"name": "Cofficer"}, "officer")
	World.character_deleted("Aleader")
	print("delete_guild: leader deleted -> Aleader in %s; Cofficer %s, Bmember %s" % [gs.key_of("Aleader") if gs.key_of("Aleader") != "" else "none", gs.rank_of("Cofficer"), gs.rank_of("Bmember")])
	World.character_deleted("Cofficer")
	print("delete_guild: new leader deleted -> Bmember %s" % gs.rank_of("Bmember"))
	World.character_deleted("Bmember")
	print("delete_guild: last one deleted -> guild still there %s" % gs.guilds.has("delete test"))
	World.character_deleted("Nobody")  # in no guild: nothing happens
	print("delete_guild: someone in no guild -> fine")


func _t_quest_share() -> void:
	var m := Player.new()
	m.from_save({"name": "Probe", "class": "warrior", "level": 5, "stats": {}, "race": "human"})
	var why := func(q: String) -> String: return World.quest_share_blocked(m, q)
	print("quest_share: fresh -> fang_bounty '%s', trail_pack_cord '%s', trail_pack_hide '%s', merricks_line_spring '%s'" % [why.call("fang_bounty"), why.call("trail_pack_cord"), why.call("trail_pack_hide"), why.call("merricks_line_spring")])
	m.quests["trail_pack_cord"] = {"active": false, "completions": 1}
	m.quests["fang_bounty"] = {"active": true, "completions": 0}
	print("quest_share: after the cord -> trail_pack_hide '%s', trail_pack_cord '%s', fang_bounty '%s' (you: '%s')" % [why.call("trail_pack_hide"), why.call("trail_pack_cord"), why.call("fang_bounty"), World.quest_share_blocked(m, "fang_bounty", true)])
	m.quests["fang_bounty"] = {"active": false, "completions": 3}
	print("quest_share: repeatable fang_bounty done 3 times -> '%s'" % why.call("fang_bounty"))
	var faction := str(GameData.npcs["warden_holt"].get("faction", ""))
	m.factions[faction] = -3000
	print("quest_share: at -3000 with %s -> fang_bounty '%s'" % [faction, why.call("fang_bounty")])
	m.free()
	var p := World.local_player
	var hud: Node = get_tree().get_first_node_in_group("hud")
	p.quests["fang_bounty"] = {"active": true, "completions": 0}
	p.group = []
	hud._toggle_journal()
	hud._journal_pick = "fang_bounty"
	hud._refresh_journal()
	print("quest_share: solo -> share button %s" % hud._journal_share.visible)
	p.group = [{"id": p.entity_id, "name": p.display_name, "level": p.level, "class": p.char_class, "hp": p.hp, "max_hp": p.max_hp, "mana": p.mana, "max_mana": p.max_mana, "leader": true, "zone": "greenmoor", "dead": false},
			{"id": -5, "name": "Nick", "level": 5, "class": "cleric", "hp": 60, "max_hp": 60, "mana": 40, "max_mana": 40, "leader": false, "zone": "greenmoor", "dead": false}]
	hud._refresh_journal()
	await _wait(0.3)
	print("quest_share: grouped -> share button %s" % hud._journal_share.visible)
	await _shot("9journal_share")
	hud._toggle_journal()
	hud._on_quest_offered("Nick", "fang_bounty")
	await _wait(0.3)
	await _shot("9quest_offer")
	hud._on_quest_offered("", "")
	p.group = []
	# solo: a share is refused
	var lines: Array = []
	var grab := func(t: String, _c: Color) -> void: lines.append(t)
	World.log_message.connect(grab)
	World.request_quest_share(p.entity_id, "fang_bounty")
	World.log_message.disconnect(grab)
	print("quest_share: solo share -> %s" % [lines])


func _t_journal() -> void:
	var p := World.local_player
	var hud: Node = get_tree().get_first_node_in_group("hud")
	var lines: Array = []
	var grab := func(t: String, _c: Color) -> void: lines.append(t)
	World.log_message.connect(grab)
	p.quests.clear()
	p.quests["trail_pack_cord"] = {"active": false, "completions": 1}  # step one done...
	World._accept_quest(p, "trail_pack_hide")  # ...so Warden Holt's step is on
	var own := "fang_bounty"
	World._accept_quest(p, own)
	p.quests["rain_pack_needles"] = {"active": false, "completions": 1}  # something for the Completed tab
	hud._toggle_journal()
	await _wait(0.6)
	await _shot("9journal_active")
	hud._journal_pick = own
	hud._refresh_journal()
	await _wait(0.3)
	await _shot("9journal_keyword")
	hud._journal_done_tab = true
	hud._refresh_journal()
	await _wait(0.3)
	await _shot("9journal_done")
	hud._toggle_journal()
	World.request_quest_abandon(p.entity_id, own)
	World.request_quest_abandon(p.entity_id, "trail_pack_hide")
	print("journal: abandoned -> %s active %s, trail_pack_hide active %s" % [own, p.quests[own]["active"], p.quests["trail_pack_hide"]["active"]])
	var holt: Npc = _npcs()["warden_holt"]
	_stand_by(p, holt)
	World.request_hail(p.entity_id)
	print("journal: hailed Warden Holt -> trail_pack_hide active %s" % p.quests["trail_pack_hide"]["active"])
	World.log_message.disconnect(grab)
	print("journal: lines %s" % [lines.filter(func(t: String) -> bool: return "abandon" in t or "pack" in t.to_lower() or "hide" in t.to_lower())])


## Alignment: an evil race starts hostile with the good cities (guards attack,
## townsfolk refuse), a necromancer is distrusted, logging in again changes
## nothing, and a change of race moves you to the new side.
func _t_alignment() -> void:
	var p := World.local_player
	var keep := [p.race, p.char_class, p.factions.duplicate(), p.alignment_mods.duplicate()]
	var show := func(label: String) -> void:
		print("alignment: %s (%s %s, %s): Emberhold %d, Watch %d, Lanternhold %d, Rainhold %d; Watch guards attack %s, Emberhold refuses %s" % [label,
				p.race, p.char_class, World.alignment_of(p), World.standing(p, "emberhold"), World.standing(p, "watch"), World.standing(p, "lanternhold"),
				World.standing(p, "rainhold"), World.npc_kos(p, "watch"), World.standing(p, "emberhold") < World.REFUSE_BELOW])
	p.factions = {}
	p.alignment_mods = {}
	p.race = "dark_elf"
	World.apply_alignment(p)
	show.call("a new dark elf")
	World.apply_alignment(p)
	show.call("logged in again")
	p.factions = {}
	p.alignment_mods = {}
	p.race = "human"
	p.char_class = "necromancer"
	World.apply_alignment(p)
	show.call("a new human necromancer")
	p.race = "troll"
	World.apply_alignment(p)
	show.call("changed race to troll")
	p.race = "high_elf"
	World.apply_alignment(p)
	show.call("changed race to high elf")
	p.race = keep[0]
	p.char_class = keep[1]
	p.factions = keep[2]
	p.alignment_mods = keep[3]


## Food and potions say what they do: a meal its stats and how long, a potion how much it heals or restores.
func _t_food_tooltips() -> void:
	var hud = get_parent().hud
	for id in ["hunters_pie", "roast_meat", "terrace_tea"]:
		print("food_tooltips: %s" % hud._item_tooltip(id).replace("\n", " | "))
	for id: String in GameData.items:
		var it: Dictionary = GameData.items[id]
		if it is Dictionary and it.has("use") and GameData.spells.get(str(it["use"].get("spell", "")), {}).get("type", "") in ["heal", "restore_mana"]:
			print("food_tooltips: %s" % hud._item_tooltip(id).replace("\n", " | "))
			break


## A link or a phrase finds the npc's keyword inside it: Odalys's
## "[Slag hounds]" starts her hounds quest, "[Old Clinkerjaw]" her Clinkerjaw one.
func _t_talk_phrases() -> void:
	var p := World.local_player
	await _wait(0.5)
	var odalys: Npc = _npcs()["cp_ventrunner_odalys"]
	for q in ["cp_slag_hound_q", "cp_old_clinkerjaw_q"]:
		p.quests.erase(q)
	_stand_by(p, odalys)
	World.request_say(p.entity_id, "Slag hounds")
	World.request_say(p.entity_id, "Old Clinkerjaw")
	await _wait(0.3)
	print("talk_phrases: 'Slag hounds' -> hounds quest %s; 'Old Clinkerjaw' -> Clinkerjaw quest %s" % [
			p.quests.get("cp_slag_hound_q", {}).get("active", false), p.quests.get("cp_old_clinkerjaw_q", {}).get("active", false)])


## Guards are an elite of their level (cap + 20): their damage, health and
## armor come off the monster curve carried past the cap, so one cuts down an
## ordinary monster of any zone in seconds, not minutes.
func _t_guard_strength() -> void:
	var z: Zone = get_parent().zone
	var guard: Npc = null
	for c in z.get_children():
		if c is Npc and not (c as Npc).guard.is_empty():
			guard = c
			break
	print("guard_strength: %s level %d, %d-%d every %.1f s, %d hp, ac %d" % [guard.display_name, guard.level, guard.dmg_min, guard.dmg_max,
			guard.attack_delay, guard.max_hp, guard.ac])
	var rows := []
	for id in ["dire_wolf", "magma_golem", "ivory_colossus"]:
		var d: Dictionary = (GameData.mobs[id] as Dictionary).duplicate(true)
		var m := Mob.new()
		m.setup(id, d, null)
		m.aggressive = false
		z.add_child(m)
		m.global_position = guard.global_position + guard.global_basis.z * -2.0 + Vector3.UP * 0.3
		await _wait(0.2)
		guard.fight(m)
		var t := 0.0
		while is_instance_valid(m) and not m.dead and t < 120.0:
			await get_tree().physics_frame
			t += 1.0 / 60.0
		rows.append("%s (level %d, %d hp) in %.0f s" % [id, m.level if is_instance_valid(m) else 0, m.max_hp if is_instance_valid(m) else 0, t])
		guard.auto_attack = false
		guard.target = null
		guard.hp = guard.max_hp
		await _wait(1.0)
	print("guard_strength: killed %s" % [rows])


## Cinderpass's bridges are stone and you can cross them unburned (only
## standing in the lava burns), the east road has one now, and the lava
## rivers end round, not square.
func _t_lava_bridges() -> void:
	World.time_override = 12.0
	var main := get_parent()
	var p := World.local_player
	var z: Zone = main.zone
	await _wait(0.5)
	var bridges := []
	for c in z.get_children():
		if c is StaticBody3D:
			for m in c.get_children():
				if m is Node3D and str(m.scene_file_path).contains("bridge_"):
					bridges.append([str(m.scene_file_path).get_file().get_basename(), Vector2(c.position.x, c.position.z).round()])
	var burns := func(at: Vector3, seconds: float) -> int:
		p.global_position = at
		p.velocity = Vector3.ZERO
		p.hp = p.max_hp
		var before := p.hp
		for k in int(seconds * 60):
			World._check_lava(p, 1.0 / 60.0)
			await get_tree().physics_frame
		return before - p.hp
	var on_bridge: int = await burns.call(Vector3(-178.8, z.lava_level(-178.8, 7.5) + 1.3, 7.5), 3.0)
	var on_east: int = await burns.call(Vector3(286.1, z.lava_level(286.1, 12.7) + 1.3, 12.7), 3.0)
	var at := Vector2(-200, -60)  # on the western river, away from the bridge
	var r: Array = z._river_at(z._rivers[0], at.x, at.y)
	var pts: Array[Vector2] = z._rivers[0]["points"]
	var mid := pts[1].lerp(pts[2], 0.5)
	var in_lava: int = await burns.call(Vector3(mid.x, z.lava_level(mid.x, mid.y) - 0.5, mid.y), 3.0)
	print("lava_bridges: bridges %s; on the west bridge burned %d, on the east bridge %d, standing in the lava %d" % [bridges, on_bridge, on_east, in_lava])
	p.hp = p.max_hp
	await _zone_views("cinderpass_lava", [[Vector2(-178.8, 40), Vector2(-178.8, 7.5), "west_bridge"], [Vector2(286, 45), Vector2(286.1, 12.7), "east_bridge"],
			[Vector2(pts[-1].x + 20, pts[-1].y + 30), pts[-1], "river_end"]])
	World.time_override = -1.0


## The Tuskway's three borders, every one both ways, chained: in from
## Harrowfield, out to Dewstep and back, up to Sunward Steps and back, home to Harrowfield.
func _t_tuskway_borders() -> void:
	for leg: Array in [["harrowfield", Vector2(200, 0), Vector2(1, 0), "the_tuskway"], ["the_tuskway", Vector2(250, 4), Vector2(1, 0), "dewstep"],
			["dewstep", Vector2(-200, 0), Vector2(-1, 0), "the_tuskway"], ["the_tuskway", Vector2(0, -250), Vector2(0, -1), "sunward_steps"],
			["sunward_steps", Vector2(0, 250), Vector2(0, 1), "the_tuskway"], ["the_tuskway", Vector2(-250, 0), Vector2(-1, 0), "harrowfield"]]:
		if not await _walk_border("tuskway_borders", leg[0], leg[1], leg[2], leg[3]):
			return


## The Tuskway's life: its monsters by day and night, each giver's quests
## handed in (the far ones at the Dawnward Watch too), a look at each
## monster, and the Caravanserai, the Watch, the Fallen Tusk, the Ochre Hand
## and the tigers' bamboo.
func _t_tuskway_life() -> void:
	await _zone_life("tuskway_life", {"tw_keeper_anvesha": ["tw_offerings", "tw_jackal_hides"], "tw_warden_tarun": ["tw_ochre_tokens", "tw_rhaz"],
			"tw_brother_kesav": ["tw_beads", "tw_abbess"], "tw_huntress_devi": ["tw_tiger_pelts", "tw_saffronclaw"],
			"tw_herbalist_ila": ["tw_cobra_fangs", "tw_beetle_shells"]},
			["tw_pilgrim_shade", "tw_lost_abbess"],
			["tw_bamboo_monkey", "tw_red_jackal", "tw_road_beetle", "tw_king_cobra", "tw_striped_tiger", "tw_ochre_cutthroat", "tw_pilgrim_shade",
			"tw_saffronclaw", "tw_rhaz_ochrehand", "tw_lost_abbess"])
	# the Dawnward Watch takes the north end's hand-ins
	var p := World.local_player
	var meera: Npc = _npcs()["tw_scout_meera"]
	var before := int(p.quests.get("tw_tiger_pelts", {}).get("completions", 0))
	for i in p.pack.slots.size():
		p.pack.slots[i] = {}
	p.pack.add("tw_striped_pelt", 4)
	_stand_by(p, meera)
	await _hand_in(p, meera, ["tw_striped_pelt"])
	await _wait(0.3)
	print("tuskway_life: Scout Meera took four pelts: completions %d -> %d" % [before, int(p.quests.get("tw_tiger_pelts", {}).get("completions", 0))])
	World.time_override = 12.0
	await _zone_views("tuskway", [[Vector2(10, 90), Vector2(10, 40), "caravanserai"], [Vector2(-10, -190), Vector2(-50, -230), "watch"],
			[Vector2(140, -110), Vector2(170, -150), "fallen_tusk"], [Vector2(-130, 130), Vector2(-170, 170), "ochre_hand"],
			[Vector2(-150, -130), Vector2(-200, -160), "bamboo"], [Vector2(-200, 10), Vector2(-60, 36), "road"]])
	World.time_override = -1.0


## Cinderpass's north road: Ventwatch takes the zone's hand-ins (Brenna's,
## Tovar's, Carter Hodd's and its own), its people stand clear of lava, and
## the abandoned smelter to the west has its slag hounds and Old Clinkerjaw.
func _t_cinderpass_hubs() -> void:
	World.time_override = 12.0
	var z: Zone = get_parent().zone
	await _wait(1.0)
	var npcs := _npcs()
	var odalys: Npc = npcs.get("cp_ventrunner_odalys")
	var takes := []
	for qid in ["ember_sigils", "ashkars_brand", "cindermaws_heart", "cp_ash_beetle_q", "cp_cinderback_q", "cp_slag_hound_q", "cp_old_clinkerjaw_q"]:
		if odalys != null and World.takes_hand_in(GameData.quests[qid], odalys.npc_id):
			takes.append(qid)
	var burning := []
	for id in ["cp_ventrunner_odalys", "cp_sutler_hadley", "cp_ventrunner_odalys_guard"]:
		var n: Npc = npcs.get(id)
		if n == null or z.lava_at(n.global_position.x, n.global_position.z):
			burning.append(id)
	var hounds := 0
	var clinker := 0
	for sp in z.get_children():
		if sp is SpawnPoint:
			if (sp as SpawnPoint).pool.has("cp_slag_hound"):
				hounds += 1
			if (sp as SpawnPoint).pool.has("cp_old_clinkerjaw") or (sp as SpawnPoint).rare == "cp_old_clinkerjaw":
				clinker += 1
	var walk := Vector2(odalys.global_position.x, odalys.global_position.z).distance_to(Vector2(-117, -308)) if odalys != null else -1.0
	print("cinderpass_hubs: Odalys takes %d of 7 %s; on lava or missing %s; smelter: %d hound spots, Clinkerjaw %d; Ventwatch to Cindermaw %.0f m (the outpost was ~590)" % [
			takes.size(), takes, burning, hounds, clinker, walk])
	await _zone_views("cinderpass", [[Vector2(-30, -195), Vector2(-30, -215), "ventwatch"], [Vector2(-100, -130), Vector2(-130, -150), "smelter"]])
	World.time_override = -1.0


## The guild bank at a city banker: the leader puts items and coin in and
## takes them out; a member may put in but not take out (nor swap); NO DROP
## stays out; everything is logged and saved with the guild; the Guild tab
## shows 40 slots; a guild with things in its bank can't be disbanded.
func _t_guild_bank() -> void:
	var main := get_parent()
	var p := World.local_player
	DirAccess.remove_absolute(ProjectSettings.globalize_path("user://guilds_autotest.json"))
	World._guild_store = null
	var gs := World.guilds()
	gs.found("Vault Keepers", World._roster_line(p))
	World._set_guild_tag(p)
	var key := gs.key_of(p.display_name)
	var banker: Npc = _npcs()["banker_odile"]
	_stand_by(p, banker)
	World.request_interact(p.entity_id)
	await _wait(0.3)
	var hud = main.hud
	hud._bank_guild_tab = true
	hud._refresh_service()
	var tab_shown: bool = hud._bank_tabs.visible and hud._gbank_box.visible
	var slots: int = hud._gbank_grid.get_child_count()
	# the leader: in by the cursor, in by shift-click, coin in, then one out
	p.pack.add("iron_dagger")
	p.pack.add("bone_chips", 5)
	p.cursor = Pack.entry("iron_dagger")
	p.pack.remove("iron_dagger", 1)
	World.request_click(p.entity_id, "gk:0")
	var chips_at := ""
	for i in p.pack.slots.size():
		if str((p.pack.slots[i] as Dictionary).get("item", "")) == "bone_chips":
			chips_at = "g:%d" % i
	World.request_guild_bank_deposit(p.entity_id, chips_at)
	p.coin = 1000
	World.request_guild_bank_coin(p.entity_id, 600)
	var g := gs.bank_of(key)
	var after_in := [str(g["bank"][0].get("item", "")), str(g["bank"][1].get("item", "")), int(g["bank_coin"]), p.coin]
	World.request_guild_bank_withdraw(p.entity_id, 1)
	var leader_took := p.pack.count("bone_chips") == 5 and (g["bank"][1] as Dictionary).is_empty()
	# a member: may put in, not take out
	gs.set_rank(p.display_name, "member")
	World.request_guild_bank_withdraw(p.entity_id, 0)
	World.request_click(p.entity_id, "gk:0")
	var member_kept_out := p.cursor.is_empty() and str(g["bank"][0].get("item", "")) == "iron_dagger"
	World.request_guild_bank_coin(p.entity_id, -100)
	var coin_stayed := int(g["bank_coin"]) == 600
	p.cursor = Pack.entry("bone_chips", 2)
	p.pack.remove("bone_chips", 2)
	World.request_click(p.entity_id, "gk:0")  # a taken slot: no swap for a member
	var no_swap := str(g["bank"][0].get("item", "")) == "iron_dagger" and str(p.cursor.get("item", "")) == "bone_chips"
	World.request_click(p.entity_id, "gk:5")  # an empty one: fine
	var member_put := str(g["bank"][5].get("item", "")) == "bone_chips"
	p.cursor = Pack.entry("abbots_seal")
	World.request_click(p.entity_id, "gk:6")
	var no_drop_out := (g["bank"][6] as Dictionary).is_empty()
	p.cursor = {}
	await _wait(0.3)
	await _shot("9zw_guild_bank")
	gs.set_rank(p.display_name, "leader")
	var saved: Variant = JSON.parse_string(FileAccess.get_file_as_string("user://guilds_autotest.json"))
	var on_disk := str((saved as Dictionary).get(key, {}).get("bank", [{}])[0].get("item", ""))
	World.request_guild(p.entity_id, "disband")
	World.request_guild(p.entity_id, "disband")
	var still := gs.guilds.has(key)
	print("guild_bank: Guild tab %s with %d slots; leader put in %s" % [tab_shown, slots, after_in])
	print("guild_bank: leader took one out %s; a member kept from taking %s, from coin %s, from swapping %s, may put in %s; NO DROP kept out %s" % [leader_took,
			member_kept_out, coin_stayed, no_swap, member_put, no_drop_out])
	print("guild_bank: saved to disk %s; %d log lines, newest: %s; disband refused while it holds things %s" % [on_disk, (g["bank_log"] as Array).size(),
			(g["bank_log"] as Array).back(), still])
	World.request_service_close(p.entity_id)
	gs.disband(key)
	World._set_guild_tag(p)


## The chat window: tells, group and guild lines in their tabs and in All,
## unread counts on the others, a tell fills To:, the main chat leaves them
## out when Settings says, and the guild tab talks to the guild.
func _t_social_chat() -> void:
	var main := get_parent()
	var p := World.local_player
	var hud = main.hud
	hud._show_social_tab("group")
	hud.add_log("Ilvara tells you, 'meet me at the bridge'", World.C_CHAT_TELL)
	hud.add_log("Brannoc tells the guild, 'raid at dusk'", World.C_CHAT_GUILD)
	hud.add_log("Corran tells the group, 'pull'", World.C_CHAT_GROUP)
	var unread: Dictionary = hud._social_unread.duplicate()
	var to: String = hud._social_to.text
	var shown: bool = hud._group_log_panel.visible
	var keep_main: bool = Controls.social_in_main
	Controls.social_in_main = false
	var main_before: String = hud._log.get_parsed_text()
	hud.add_log("Ilvara tells you, 'hurry'", World.C_CHAT_TELL)
	var main_clean: bool = hud._log.get_parsed_text() == main_before
	Controls.social_in_main = keep_main
	hud._show_social_tab("tell")
	var tells: String = (hud._social_logs["tell"] as RichTextLabel).get_parsed_text().replace("\n", " | ")
	DirAccess.remove_absolute(ProjectSettings.globalize_path("user://guilds_autotest.json"))
	World._guild_store = null
	World.guilds().found("Chatty Folk", World._roster_line(p))
	World._set_guild_tag(p)
	hud._show_social_tab("guild")
	hud._send_social("hello, guild")
	await _wait(0.2)
	var guild_log: String = (hud._social_logs["guild"] as RichTextLabel).get_parsed_text()
	print("social_chat: unread while on Group %s; To: %s; window shown %s; main chat left out when asked %s" % [unread, to, shown, main_clean])
	print("social_chat: tells tab: %s" % tells)
	print("social_chat: talked in the guild tab -> %s" % ("You say to your guild, 'hello, guild'" in guild_log))
	await _shot("9zw_social_chat")
	World.guilds().disband(World.guilds().key_of(p.display_name))
	World._set_guild_tag(p)


## The evil races among their own: a fresh dark elf, troll and ogre, of every
## class each may be, stand with Murkhold and Duskhold alike, so neither
## city's guards attack them and neither city's people turn them away.
func _t_evil_kin() -> void:
	var p := World.local_player
	var keep := [p.race, p.char_class, p.factions.duplicate(), p.alignment_mods.duplicate()]
	var bad := []
	var rows := []
	for race in ["dark_elf", "troll", "ogre"]:
		for cls: String in GameData.races[race].get("classes", []):
			p.factions = {}
			p.alignment_mods = {}
			p.race = race
			p.char_class = cls
			World.apply_alignment(p)
			var line := "%s %s: Murkhold %d, Duskhold %d" % [race, cls, World.standing(p, "murkhold"), World.standing(p, "duskhold")]
			for city in ["murkhold", "duskhold"]:
				if World.city_hostile(p, city) or World.npc_kos(p, city) or World.standing(p, city) < World.REFUSE_BELOW:
					bad.append("%s %s in %s" % [race, cls, city])
			rows.append(line)
	for r: String in rows:
		print("evil_kin:   " + r)
	print("evil_kin: turned away or attacked by their own side: %s" % [bad])
	p.race = keep[0]
	p.char_class = keep[1]
	p.factions = keep[2]
	p.alignment_mods = keep[3]


## The Blackwater and the ground between it and Rainhold, chained: eighteen
## crossings, every border of Murkhold, the Wallow, the Rotfen, Duskwood (and
## the cave down to Duskhold), the Broken March and Stormcut Gorge both ways,
## ending back in Rainhold.
func _t_blackwater_borders() -> void:
	var p := World.local_player
	var keep := [p.race, p.factions.duplicate(), p.alignment_mods.duplicate()]
	p.race = "troll"  # a human walking into Murkhold is cut down by its guards (which is the point of it)
	World.apply_alignment(p)
	for leg: Array in [["rainhold", Vector2(-60, 0), Vector2(-1, 0), "stormcut_gorge"], ["stormcut_gorge", Vector2(-190, 0), Vector2(-1, 0), "broken_march"],
			["broken_march", Vector2(-190, 0), Vector2(-1, 0), "the_wallow"], ["the_wallow", Vector2(-165, 0), Vector2(-1, 0), "murkhold"],
			["murkhold", Vector2(80, 0), Vector2(1, 0), "the_wallow"], ["the_wallow", Vector2(0, 165), Vector2(0, 1), "the_rotfen"],
			["the_rotfen", Vector2(200, 0), Vector2(1, 0), "duskwood"], ["duskwood", Vector2(162, 120), Vector2(-1, 0), "duskhold"],
			["duskhold", Vector2(0, -86), Vector2(0, -1), "duskwood"], ["duskwood", Vector2(0, -165), Vector2(0, -1), "broken_march"],
			["broken_march", Vector2(0, 190), Vector2(0, 1), "duskwood"], ["duskwood", Vector2(-165, 0), Vector2(-1, 0), "the_rotfen"],
			["the_rotfen", Vector2(0, -200), Vector2(0, -1), "the_wallow"], ["the_wallow", Vector2(165, 0), Vector2(1, 0), "broken_march"],
			["broken_march", Vector2(190, 0), Vector2(1, 0), "stormcut_gorge"], ["stormcut_gorge", Vector2(0, -190), Vector2(0, -1), "reedmere"],
			["reedmere", Vector2(0, 225), Vector2(0, 1), "stormcut_gorge"], ["stormcut_gorge", Vector2(190, 0), Vector2(1, 0), "rainhold"]]:
		if not await _walk_border("blackwater_borders", leg[0], leg[1], leg[2], leg[3]):
			break
	p.race = keep[0]
	p.factions = keep[1]
	p.alignment_mods = keep[2]


## The Blackwater's life: each zone's monsters and quests, the cities' guards
## against a human and a troll, the bog gods' races, and an existing troll's
## bind following its people to Murkhold.
func _t_blackwater_life() -> void:
	var main := get_parent()
	var p := World.local_player
	var keep_race := [p.race, p.factions.duplicate(), p.alignment_mods.duplicate()]
	p.race = "troll"
	World.apply_alignment(p)
	var go := func(zone_id: String, arrive: Vector2) -> void:
		while main._changing_zone:
			await _wait(0.25)
		World.zone_change.emit(p, zone_id, arrive, Vector2.ZERO)
		for k in 80:
			if (main.zone as Zone).zone_id == zone_id and not main._changing_zone:
				break
			await _wait(0.25)
		await _wait(0.8)
	await _zone_life("blackwater_life_wallow", {"wallow_hunter_snikk": ["wallow_pondkin_beads", "wallow_wetbelly", "wallow_gulpmaw"]}, ["bog_wisp"],
			["bog_rat", "wallow_toad", "swamp_leech", "pondkin_forager", "pondkin_mudslinger", "mud_turtle", "bog_wisp", "chief_wetbelly", "gulpmaw"])
	await _zone_views("wallow", [[Vector2(-130, -40), Vector2(-150, -30), "camp"], [Vector2(90, -90), Vector2(126, -122), "pondkin"], [Vector2(20, 20), Vector2(60, 40), "pools"]])
	await go.call("duskwood", Vector2(160, 140))
	await _zone_life("blackwater_life_duskwood", {"dusk_sentinel_vaelith": ["dusk_scout_badges", "dusk_aldren", "dusk_silkmother"]}, ["lesser_shade"],
			["gloom_rat", "dusk_spiderling", "restless_bones", "gloomfang_wolf", "lesser_shade", "hearth_scout", "hearth_archer", "silkmother_vyss", "scout_captain_aldren"])
	await _zone_views("duskwood", [[Vector2(175, 150), Vector2(150, 120), "cave"], [Vector2(20, 0), Vector2(-40, 0), "wood"], [Vector2(90, -80), Vector2(120, -110), "scouts"]])
	await go.call("the_rotfen", Vector2(40, -20))
	await _zone_life("blackwater_life_rotfen", {"fen_warden_grisk": ["rotfen_scales", "rotfen_sisska", "rotfen_mudjaw"],
			"blade_sister_nyssa": ["rotfen_hag_charms", "rotfen_gristlewort"]}, [],
			["plague_rat", "fen_eel", "rotfen_lurker", "rotfen_mirescale", "rotfen_mirescale_shaman", "gristle_hag", "feral_fen_troll", "chief_sisska", "mother_gristlewort", "old_mudjaw"])
	await _zone_views("rotfen", [[Vector2(60, -20), Vector2(40, -40), "camp"], [Vector2(-110, -40), Vector2(-140, -60), "lizards"], [Vector2(120, 120), Vector2(140, 140), "coven"]])
	for city: Array in [["murkhold", Vector2(46, 0), "murkhold_guard", ["murk_outfitter", "bogtanner_skins"]], ["duskhold", Vector2(0, -80), "duskhold_guard", ["dusk_outfitter", "silkweave_silk"]]]:
		await go.call(city[0], city[1])
		var npcs := _npcs()
		var kinds := {}
		for n: Npc in npcs.values():
			var k := "guildmaster:" + str(n.data["guildmaster"]["class"]) if n.data.has("guildmaster") else ("banker" if n.data.get("banker", false) else
					("merchant" if n.data.has("merchant") else ("guard" if n.data.has("guard") else ("binds" if n.data.get("binds", false) else "other"))))
			kinds[k] = int(kinds.get(k, 0)) + 1
		print("blackwater_life: %s: %d npcs %s; bindstone %s" % [city[0], npcs.size(), kinds, main.zone.data.get("bindstone", false)])
		var race0 := p.race
		for race: String in ["human", "troll", "dark_elf"]:
			p.race = race
			p.factions = {}
			p.alignment_mods = {}
			World.apply_alignment(p)
			print("blackwater_life: %s: a %s -> %s %d, guards attack %s" % [city[0], race, city[0], World.standing(p, city[0]), World.npc_kos(p, city[0])])
		p.race = race0
		p.factions = {}
		p.alignment_mods = {}
		World.apply_alignment(p)
		await _zone_views(city[0], [[city[1], Vector2(0, 0), "gate"], [Vector2(20, 22) if city[0] == "murkhold" else Vector2(0, 40), Vector2(0, 0), "heart"]])
	# the bog gods take trolls and ogres; an old troll bound in Rainhold is moved home
	print("blackwater_life: Makarosh takes a troll %s, a human %s; Mahishra takes an ogre %s, a dark elf %s" % [GameData.deity_allows("mire", "troll"),
			GameData.deity_allows("mire", "human"), GameData.deity_allows("horn", "ogre"), GameData.deity_allows("horn", "dark_elf")])
	var keep := [p.race, p.bind_zone, p.home_seen]
	p.race = "troll"
	p.bind_zone = "rainhold"
	p.home_seen = ""
	World._follow_home(p)
	print("blackwater_life: an old troll bound in Rainhold -> bound in %s (home seen %s); again -> %s" % [p.bind_zone, p.home_seen, (func() -> String:
		World._follow_home(p)
		return p.bind_zone).call()])
	p.race = keep[0]
	p.bind_zone = keep[1]
	p.home_seen = keep[2]
	p.race = keep_race[0]
	p.factions = keep_race[1]
	p.alignment_mods = keep_race[2]


## The Broken March and Stormcut Gorge: every quest handed in (repeatables
## twice), night spawns, and a look round each.
func _t_west_march_life() -> void:
	var main := get_parent()
	var p := World.local_player
	await _zone_life("west_march_life_march", {"marchwarden_hale": ["march_pelts", "march_tokens", "march_corvel", "march_scythewing"],
			"gravekeeper_ossa": ["march_grave_iron", "march_marshal"]}, ["restless_soldier", "hollow_marshal"],
			["march_wolf", "brambleback_boar", "marchreaver_cutthroat", "restless_soldier", "crag_wyvern", "redhand_corvel", "hollow_marshal", "scythewing"])
	await _zone_views("march", [[Vector2(40, 40), Vector2(20, 10), "post"], [Vector2(-90, -90), Vector2(-130, -120), "keep"],
			[Vector2(90, -100), Vector2(135, -140), "crags"], [Vector2(-100, 90), Vector2(-135, 122), "reavers"]])
	while main._changing_zone:
		await _wait(0.25)
	World.zone_change.emit(p, "stormcut_gorge", Vector2(170, 20), Vector2.ZERO)
	for k in 80:
		if (main.zone as Zone).zone_id == "stormcut_gorge" and not main._changing_zone:
			break
		await _wait(0.25)
	await _wait(0.8)
	await _zone_life("west_march_life_gorge", {"ropewarden_mbeki": ["gorge_tusks", "gorge_grukk", "gorge_feathers", "gorge_stormcrest"],
			"tidepriestess_lirien": ["gorge_essence", "gorge_voice"]}, ["falls_spirit"],
			["canyon_adder", "gorge_croc", "stonefist_troll", "gorge_griffon", "falls_spirit", "chief_grukk", "stormcrest", "voice_of_the_falls"])
	await _zone_views("gorge", [[Vector2(160, 40), Vector2(140, 24), "watch"], [Vector2(18, 12), Vector2(-5, 0), "bridge"],
			[Vector2(40, 150), Vector2(40, 206), "falls"], [Vector2(-70, 60), Vector2(-115, 95), "trolls"], [Vector2(90, -110), Vector2(135, -150), "griffons"]])


## A look round the two cities (for art checks).
func _t_blackwater_views() -> void:
	var main := get_parent()
	var p := World.local_player
	p.race = "troll"
	World.apply_alignment(p)
	World.time_override = 12.0
	await _zone_views("murkhold", [[Vector2(46, 0), Vector2(0, 0), "gate"], [Vector2(24, 24), Vector2(-10, -8), "idols"], [Vector2(-20, 20), Vector2(-52, -6), "longhouse"]])
	while main._changing_zone:
		await _wait(0.25)
	World.zone_change.emit(p, "duskhold", Vector2(0, -80), Vector2.ZERO)
	for k in 80:
		if (main.zone as Zone).zone_id == "duskhold" and not main._changing_zone:
			break
		await _wait(0.25)
	await _wait(0.8)
	await _zone_views("duskhold", [[Vector2(0, -80), Vector2(0, 0), "gate"], [Vector2(0, -44), Vector2(0, 0), "bridge"], [Vector2(-40, 40), Vector2(40, -40), "across"], [Vector2(0, 0), Vector2(0, -96), "back"]])


## Character creation with seven gods: the bog gods offered to a troll,
## grayed out for a human (and a choice of one cleared on changing race).
func _t_deity_picker() -> void:
	var cc := CharCreate.new()
	cc.setup({})
	get_parent().add_child(cc)
	await _wait(0.5)
	cc._select_race("troll")
	cc._deity_buttons["mire"].pressed.emit()
	await _wait(0.3)
	print("deity_picker: a troll: mire open %s, chose %s" % [not cc._deity_buttons["mire"].disabled, cc._deity])
	await _shot("9deity_troll")
	cc._select_race("human")
	await _wait(0.3)
	print("deity_picker: a human: mire open %s, horn open %s, light open %s, choice now '%s'" % [not cc._deity_buttons["mire"].disabled,
			not cc._deity_buttons["horn"].disabled, not cc._deity_buttons["light"].disabled, cc._deity])
	await _shot("9deity_human")
	cc.queue_free()


## A guildmaster's window: what's left to learn (what you can buy now in
## green) and what you already know, on two tabs.
func _t_trainer_tabs() -> void:
	var main := get_parent()
	var p := World.local_player
	var hud: Node = get_tree().get_first_node_in_group("hud")
	World.zone_change.emit(p, "emberhold", Vector2(0, 10), Vector2(0, 0))
	for k in 80:
		if (main.zone as Zone).zone_id == "emberhold" and not main._changing_zone:
			break
		await _wait(0.25)
	await _wait(0.8)
	var gm: Npc = null
	for n: Npc in _npcs().values():
		if str(n.data.get("guildmaster", {}).get("class", "")) == p.char_class:
			gm = n
	p.level = 12
	p.coin = 20000
	_stand_by(p, gm)
	World.request_interact(p.entity_id)
	await _wait(0.6)
	print("trainer_tabs: %s -> %s | %s" % [gm.display_name, hud._train_tab_learn.text, hud._train_tab_known.text])
	await _shot("9trainer_learn")
	hud._train_known_tab = true
	hud._refresh_service()
	await _wait(0.3)
	await _shot("9trainer_known")
	World.request_service_close(p.entity_id)
	p.level = 1


## The Pathcallers: an older save is seeded with the zones up to its level, the
## fee grows with the zone's top level squared, the window lists the roads, and
## a road is refused unvisited, too dear or while fighting; paid, it zones you.
func _t_pathcallers() -> void:
	var main := get_parent()
	var p := World.local_player
	var old_level := p.level
	p.level = 12
	p.visited = []
	p.visited_seeded = false
	World._seed_visits(p)
	var seeded := ["greenmoor", "harrowfield", "thornwood", "the_tuskway", "emberhold"].all(func(z: String) -> bool: return z in p.visited)
	var not_seeded := ["cinderpass", "the_grove", "duskhold", "emberhold_tavern"].all(func(z: String) -> bool: return not z in p.visited)
	var fees := [World.teleport_fee("greenmoor"), World.teleport_fee("cinderpass"), World.teleport_fee("emberhold")]
	var oren: Npc = _npcs()["pc_oren"]
	_stand_by(p, oren)
	World.request_interact(p.entity_id)
	await _wait(0.4)
	var hud = main.hud
	var opened: bool = p.service == "teleport" and hud._service_panel.visible
	var rows: int = hud._shop_list.get_child_count()
	var roads: Array = World.teleport_destinations(p)
	await _shot("9zx_pathcaller")
	World.request_teleport(p.entity_id, "cinderpass")
	var unvisited: bool = World.zone.zone_id == "emberhold" and not main._changing_zone
	p.coin = 50
	World.request_teleport(p.entity_id, "greenmoor")
	var too_poor: bool = p.coin == 50 and not main._changing_zone
	p.coin = 500
	p.threatened = true
	World.request_teleport(p.entity_id, "greenmoor")
	var fighting: bool = p.coin == 500 and not main._changing_zone
	p.threatened = false
	World.request_teleport(p.entity_id, "greenmoor")
	var paid := p.coin
	for k in 80:
		if (main.zone as Zone).zone_id == "greenmoor" and not main._changing_zone:
			break
		await _wait(0.25)
	await _wait(0.5)
	var arrived := (main.zone as Zone).zone_id
	p.visited.erase("greenmoor")
	p.remove_meta("visit_checked")  # as a first step into it does
	await _wait(0.5)
	var noted := "greenmoor" in p.visited
	print("pathcallers: seeded to level 12 %s, nothing past it or off the road %s; fees greenmoor/cinderpass/city %s" % [seeded, not_seeded, fees])
	print("pathcallers: window opened %s, %d rows for %d roads, cheapest %s" % [opened, rows, roads.size(), roads[0] if not roads.is_empty() else {}])
	print("pathcallers: refused unvisited %s, too poor %s, while fighting %s; paid 500 -> %d, arrived in %s; a new zone noted %s" % [unvisited, too_poor,
			fighting, paid, arrived, noted])
	# Rainhold's stands on the deck before the bank hall
	World.zone_change.emit(p, "rainhold", Vector2.INF, Vector2.INF)
	for k in 80:
		if (main.zone as Zone).zone_id == "rainhold" and not main._changing_zone:
			break
		await _wait(0.25)
	await _wait(0.5)
	var ndidi: Npc = _npcs()["pc_ndidi"]
	_stand_by(p, ndidi)
	await _wait(1.0)
	print("pathcallers: Pathcaller Ndidi stands at height %.2f over water at %.2f" % [ndidi.global_position.y, (main.zone as Zone).water_level(ndidi.global_position.x, ndidi.global_position.z)])
	await _shot("9zx_pathcaller_rainhold")
	p.level = old_level


## Looking without mouselook: Page Up / Page Down tilt the view, End levels it,
## a right drag turns and tilts; and the inventory portrait turns when dragged.
func _t_look_controls() -> void:
	var main := get_parent()
	var p := World.local_player
	var was_mouse := Controls.mouse_look
	Controls.mouse_look = false
	await _wait(0.2)
	p.pitch = Player.PITCH_REST
	Input.action_press("look_up")
	await _wait(0.4)
	Input.action_release("look_up")
	var up := p.pitch
	Input.action_press("look_down")
	await _wait(0.8)
	Input.action_release("look_down")
	var down := p.pitch
	var center := InputEventAction.new()
	center.action = "look_center"
	center.pressed = true
	p._unhandled_input(center)
	var leveled := is_equal_approx(p.pitch, Player.PITCH_REST)
	var yaw := p.rotation.y
	p._start_right_drag(Vector2(400, 300))
	var mm := InputEventMouseMotion.new()
	mm.relative = Vector2(60, -40)
	p._input(mm)
	var release := InputEventMouseButton.new()
	release.button_index = MOUSE_BUTTON_RIGHT
	release.pressed = false
	p._input(release)
	var dragged := not is_equal_approx(p.rotation.y, yaw) and p.pitch > Player.PITCH_REST and not p._right_drag
	p.pitch = Player.PITCH_REST
	var hud = main.hud
	hud._inv_panel.visible = true
	hud._refresh_inventory()
	await _wait(0.5)
	var press := InputEventMouseButton.new()
	press.button_index = MOUSE_BUTTON_LEFT
	press.pressed = true
	var box: Control = hud._doll_view.get_parent()
	hud._on_doll_input(press, box)
	var turn := InputEventMouseMotion.new()
	turn.relative = Vector2(130, 0)
	hud._on_doll_input(turn, box)
	var turned: float = hud._doll_stage.rotation.y
	await _shot("9zy_doll_turned")
	press.pressed = false
	hud._on_doll_input(press, box)
	var double := InputEventMouseButton.new()
	double.button_index = MOUSE_BUTTON_LEFT
	double.pressed = true
	double.double_click = true
	hud._on_doll_input(double, box)
	var faced: float = hud._doll_stage.rotation.y
	double.pressed = false
	hud._on_doll_input(double, box)
	hud._inv_panel.visible = false
	Controls.mouse_look = was_mouse
	print("look_controls: Page Up raised the view %s (%.2f), Page Down lowered it %s (%.2f), End leveled it %s; a right drag turned and tilted %s" % [up > Player.PITCH_REST,
			up, down < up, down, leveled, dragged])
	print("look_controls: the portrait turned %.2f rad when dragged, a double-click faced it front %s" % [turned, is_zero_approx(faced)])


## The Forge's unique weapons: every item of the set wears its own model, each
## loads, each swings as its kind should (the bow and wand shoot and zap, the
## fist blades punch, the great weapons chop), and the arrow flies as itself.
func _t_forge_weapons() -> void:
	var want := {"dragonfang_sword": "slash", "dragontooth_dagger": "thrust", "dragonclaw_axe": "slash", "dragonmaw_mace": "slash",
			"dragontail_flail": "slash", "dragonclaw_fists": "thrust", "dragoneye_wand": "attack", "dragonfang_greatsword": "chop",
			"dragonclaw_great_axe": "chop", "dragonmaw_great_mace": "chop", "dragontail_great_flail": "chop", "dragontongue_spear": "thrust",
			"dragonheart_staff": "chop", "dragonwing_bow": "attack", "sword_of_the_endless_nightmare": "slash",
			"greatsword_of_the_endless_nightmare": "chop"}
	var wrong := []
	var unloaded := []
	for item_id: String in want:
		var it: Dictionary = GameData.items[item_id]
		var model := str(it.get("model", ""))
		if model != item_id:
			wrong.append("%s wears %s" % [item_id, model])
		var path := str(GameData.models["weapons"].get(model, ""))
		if path == "" or not ResourceLoader.exists(path) or not load(path) is PackedScene:
			unloaded.append(item_id)
		var swing := Entity.swing_for(model, false, str(it.get("skill", "")))
		if swing != want[item_id]:
			wrong.append("%s swings %s" % [item_id, swing])
	var arrow := str(GameData.models["projectiles"].get(str(GameData.items["dragonbone_arrow"].get("projectile", "")), ""))
	var p := World.local_player
	p.pack.add("dragonheart_staff~30")
	World.request_equip(p.entity_id, _where(p, "dragonheart_staff~30"))
	World.time_override = 12.0
	p.zoom = 2.2
	await _wait(1.0)
	await _shot("9zz_forge_staff")
	print("forge_weapons: %d weapons, all on their own models and swings %s %s, all load %s %s; the arrow flies as %s; worn: %s" % [want.size(),
			wrong.is_empty(), wrong, unloaded.is_empty(), unloaded, arrow.get_file(), p.look.get("weapon", "")])


## The map zooms back out after a quest click closes it in: its buttons, the
## zoom keys, a trackpad's scroll and pinch, and "Whole zone".
func _t_map_zoom() -> void:
	var main := get_parent()
	var p := World.local_player
	var map = main.hud._map
	map.visible = true
	map._prepare()
	var whole: float = map._zone.size - 50.0  # the land inside the mountains
	map._span = 160.0  # as a quest click leaves it
	map._zoom(1.25, map._canvas.size * 0.5)
	var button_out: float = map._span
	var key := InputEventAction.new()
	key.action = "zoom_out"
	key.pressed = true
	map._input(key)
	var key_out: float = map._span
	var pan := InputEventPanGesture.new()
	pan.delta = Vector2(0, 2)
	map._canvas_input(pan)
	var pan_out: float = map._span
	var pinch := InputEventMagnifyGesture.new()
	pinch.factor = 1.5
	map._canvas_input(pinch)
	var pinch_in: float = map._span
	map._whole_view()
	var back: float = map._span
	await _shot("9zz_map_whole")
	map.visible = false
	print("map_zoom: from 160 m the - button %.0f, the - key %.0f, a trackpad scroll %.0f, a pinch in %.0f; Whole zone back to %.0f (the zone %.0f) %s" % [button_out,
			key_out, pan_out, pinch_in, back, whole, is_equal_approx(back, whole)])


## The Living Roots line: ten weapons on their own glowing models, a hit that
## may root the target, among the named kills' uniques, and now and then (any
## unique) from an ordinary monster that carries weapons, never one that doesn't.
func _t_living_roots() -> void:
	var main := get_parent()
	var p := World.local_player
	var ids := ["roots_shortsword", "roots_longsword", "roots_dagger", "roots_hand_axe", "roots_mace", "roots_quarterstaff",
			"roots_greatsword", "roots_great_axe", "roots_maul", "roots_spear"]
	var bad := []
	for id: String in ids:
		var it := GameData.item(id + "~20")
		var path := str(GameData.models["weapons"].get(str(it.get("model", "")), ""))
		if it.is_empty() or path == "" or not load(path) is PackedScene or not id in GameData.loot["unique"]["items"] \
				or str(it.get("proc", {}).get("spell", "")) != "grasping_roots" or not GameData.models["weapon_fx"].has(id):
			bad.append(id)
	var sample := GameData.item("roots_longsword~30")
	# the root on a hit
	var mob: Mob = null
	for m in World.get_mobs():
		if not m.dead and p.distance_to(m) < 80.0:
			mob = m
			break
	p.equipment["primary"] = "roots_dagger~20"
	p.recalc_stats()
	p.inventory_changed.emit()
	var proc: Dictionary = GameData.items["roots_dagger"]["proc"]
	var odds := float(proc["chance"])
	proc["chance"] = 1.0
	World._try_proc(p, mob)
	proc["chance"] = odds
	var rooted := mob.root_left
	var mob_name := mob.display_name
	mob.root_left = 0.0
	mob.hate.clear()
	# drops: an ordinary monster that carries weapons, then one that doesn't
	var u: Dictionary = GameData.loot["unique"]
	var keep := float(u["common_chance"])
	u["common_chance"] = 1.0
	var armed: Mob = null
	var bare: Mob = null
	for m in World.get_mobs():
		if m.dead or m.data.get("named", false):
			continue
		if m.data.has("gear") and armed == null:
			armed = m
		elif not m.data.has("gear") and bare == null and m != mob:
			bare = m
	var gave_gear := false
	if armed == null:  # none here carries weapons: one stands in
		armed = mob
		armed.data["gear"] = ["weapons"]
		gave_gear = true
	var from_armed: String = await _unique_from(armed, p)
	if gave_gear:
		armed.data.erase("gear")
	var from_bare := "(none to try)"
	if bare != null:
		from_bare = await _unique_from(bare, p)
	u["common_chance"] = keep
	# how they look, held
	World.time_override = 12.0
	p.zoom = 1.7
	p.pitch = -0.15
	p.visual.rotation.y += PI * 0.55  # side-on, the weapon hand toward the camera
	await _wait(1.5)
	await _shot("9zz_roots_dagger")
	var cm := p.visual as CharacterModel
	for id: String in ["roots_longsword", "roots_great_axe", "roots_quarterstaff"]:
		cm.set_weapon(id)
		cm.set_tiers({"primary": "unique"})
		await _wait(1.5)
		await _shot("9zz_" + id)
	p.visual.rotation.y -= PI * 0.55
	p.equipment.erase("primary")
	p.recalc_stats()
	p.inventory_changed.emit()
	print("living_roots: %d weapons, all on their own glowing models with the root proc and in the unique roll %s %s" % [ids.size(), bad.is_empty(), bad])
	print("living_roots: Longsword of Living Roots at 30: dmg %d delay %.1f sta %d str %d hp %d hp regen %d" % [sample["dmg"], sample["delay"],
			sample.get("sta", 0), sample.get("str", 0), sample.get("hp", 0), sample.get("hp_regen", 0)])
	print("living_roots: a hit's proc rooted %s for %.0f s; with the odds forced, an ordinary monster that carries weapons dropped %s, one that doesn't %s" % [
			mob_name, rooted, from_armed, from_bare if from_bare != "" else "nothing"])


## Kills m and returns the unique (an id with "~") its corpse holds, or "".
func _unique_from(m: Mob, p: Player) -> String:
	var who := m.display_name.trim_prefix("a ").trim_prefix("an ")  # the mob is gone once it dies
	World.damage(m, m.hp + 10, p)
	await _wait(0.3)
	for obj: Variant in World.objects.values():
		if obj is Corpse and (obj as Corpse).display_name.contains(who):
			for e: Dictionary in (obj as Corpse).entries:
				if str(e["item"]).contains("~"):
					return str(e["item"])
	return ""


## Mighty Blow says what the weapon in your hand does: a sword slashes, a mace crushes.
func _t_blow_verbs() -> void:
	var p := World.local_player
	var heard := []
	var listen := func(text: String, _c: Color) -> void: heard.append(text)
	World.log_message.connect(listen)
	var said := {}
	for weapon: String in ["rusty_short_sword", "mudjaw_tooth_club"]:
		var mob: Mob = null
		for m in World.get_mobs():
			if not m.dead and p.distance_to(m) < 80.0:
				mob = m
				break
		p.equipment["primary"] = weapon
		p.recalc_stats()
		heard.clear()
		World._finish_spell(p, "mighty_blow", mob, true)
		said[weapon] = heard.filter(func(l: String) -> bool: return " for " in l and "damage" in l)
		mob.hate.clear()
	World.log_message.disconnect(listen)
	p.equipment.erase("primary")
	p.recalc_stats()
	print("blow_verbs: Mighty Blow with %s" % [said])


## A repeatable quest leaves the log once done; its giver floats a blue "!"
## (a blue "?" while you carry another set) and still takes more; older saves
## that kept a finished one in the log are tidied once.
func _t_repeat_quests() -> void:
	var p := World.local_player
	var holt: Npc = _npcs()["warden_holt"]
	var keep := p.quests.duplicate(true)
	var mark := func() -> String:
		holt._mark_check = 0.0
		holt._update_mark(0.016)
		return (holt._mark.text + (" blue" if holt._mark_repeat else "")) if holt._mark.visible else "(none)"
	p.quests.clear()
	for quest_id: String in World._quests_of_npc("warden_holt"):  # everything else of his done, so his mark is the bounty's alone
		if quest_id != "fang_bounty":
			p.quests[quest_id] = {"active": false, "completions": 1}
	_stand_by(p, holt)
	World._accept_quest(p, "fang_bounty")
	var logged: bool = "fang_bounty" in main_hud()._journal_quests(false)
	p.pack.add_entry(Pack.entry("gnoll_fang", 4))
	var ready_in_log: String = mark.call()
	await _hand_in(p, holt, ["gnoll_fang"])
	var st: Dictionary = p.quests.get("fang_bounty", {})
	var after := [int(st.get("completions", 0)), st.get("active", false), "fang_bounty" in main_hud()._journal_quests(false), "fang_bounty" in main_hud()._journal_quests(true)]
	var done_mark: String = mark.call()
	p.global_position += Vector3(0, 0, 4)
	p.face_toward(holt.global_position)
	await _wait(0.6)
	await _shot("9zz_repeat_blue")
	_stand_by(p, holt)
	p.pack.add_entry(Pack.entry("gnoll_fang", 4))
	var again_mark: String = mark.call()
	var waiting: bool = World._hand_in_waiting(p, holt)
	await _hand_in(p, holt, ["gnoll_fang"])
	var twice := int(p.quests["fang_bounty"].get("completions", 0))
	# an older save: done twice and still in the log
	p.quests["fang_bounty"]["active"] = true
	p.given.erase("repeatables_out_of_log")
	World._tidy_repeatables(p)
	var tidied: bool = not p.quests["fang_bounty"]["active"]
	p.quests = keep
	print("repeat_quests: taken -> in the log %s, carrying the fangs '%s'; handed in -> done %d, active %s, in the log %s, in Completed %s; mark '%s'" % [logged,
			ready_in_log, after[0], after[1], after[2], after[3], done_mark])
	print("repeat_quests: four more fangs -> mark '%s', G trades %s; handed in out of the log -> done %d; an old save tidied %s" % [again_mark, waiting, twice, tidied])


func main_hud() -> Node:
	return get_parent().hud


## Both banks move as much coin as you type (platinum, gold, silver, copper),
## never more than there is, or all of it.
func _t_bank_coin_amounts() -> void:
	var main := get_parent()
	var p := World.local_player
	var hud = main.hud
	var banker: Npc = _npcs()["banker_odile"]
	_stand_by(p, banker)
	World.request_interact(p.entity_id)
	await _wait(0.3)
	p.coin = 5000
	p.bank_coin = 0
	var amounts: HBoxContainer = hud._bank_box.get_child(hud._bank_box.get_child_count() - 2)
	var buttons: HBoxContainer = hud._bank_box.get_child(hud._bank_box.get_child_count() - 1)
	var boxes := amounts.get_children()
	(boxes[0] as SpinBox).value = 1  # 1 platinum, 2 gold, 3 copper: 1203
	(boxes[1] as SpinBox).value = 2
	(boxes[3] as SpinBox).value = 3
	(buttons.get_child(0) as Button).pressed.emit()  # Deposit
	var after_in := [p.coin, p.bank_coin, (boxes[0] as SpinBox).value]
	(boxes[1] as SpinBox).value = 5
	var outs: HBoxContainer = buttons.get_child(2)
	(outs.get_child(0) as Button).pressed.emit()  # Withdraw 500
	var after_out := [p.coin, p.bank_coin]
	(boxes[0] as SpinBox).value = 9  # more than is banked: only what's there
	(outs.get_child(0) as Button).pressed.emit()
	var capped := [p.coin, p.bank_coin]
	(boxes[1] as SpinBox).get_line_edit().grab_focus()
	(boxes[1] as SpinBox).get_line_edit().text = "3"  # typed, never entered
	(buttons.get_child(0) as Button).pressed.emit()
	var typed := [p.coin, p.bank_coin]
	(buttons.get_child(1) as Button).pressed.emit()  # Deposit all
	var all_in := [p.coin, p.bank_coin]
	await _shot("9zz_bank_coin")
	World.request_service_close(p.entity_id)
	print("bank_coin_amounts: typed 1pp 2gp 3cp, Deposit -> pack %d bank %d (boxes cleared %s); Withdraw 5gp -> %s; Withdraw 9pp with less banked -> %s; typed 3 gold without Enter, Deposit -> %s; Deposit all -> %s" % [
			after_in[0], after_in[1], after_in[2] == 0, after_out, capped, typed, all_in])


## Gear with two places to go compares against both: a ring against each ring,
## a one-handed weapon against the main hand and (dual wielding) the off hand.
func _t_compare_slots() -> void:
	var main := get_parent()
	var p := World.local_player
	var hud = main.hud
	var keep := [p.char_class, p.level, p.equipment.duplicate()]
	p.equipment["ring1"] = "copper_band"
	p.equipment["ring2"] = "tarnished_ring"
	var ring_lines: Array = hud._compare_lines("tarnished_ring@fine", false)
	p.equipment.erase("ring2")
	var one_ring: Array = hud._compare_lines("tarnished_ring@fine", false)
	p.char_class = "warrior"
	p.level = 20
	p.equipment["primary"] = "rusty_short_sword"
	p.equipment["secondary"] = "iron_dagger"
	var dual: Array = hud._compare_lines("roots_shortsword~20", false)
	p.char_class = "wizard"
	var single: Array = hud._compare_lines("roots_shortsword~20", false)
	p.char_class = keep[0]
	p.level = keep[1]
	p.equipment = keep[2]
	p.recalc_stats()
	var heads := func(lines: Array) -> Array: return lines.filter(func(l: String) -> bool: return l.begins_with("Compared"))
	print("compare_slots: a ring with two worn -> %s" % [ring_lines.filter(func(l: String) -> bool: return l != "")])
	print("compare_slots: one ring slot empty -> %s" % [heads.call(one_ring)])
	print("compare_slots: a warrior dual wielding, a new shortsword -> %s" % [dual.filter(func(l: String) -> bool: return l != "")])
	print("compare_slots: a wizard (no dual wield) -> %s" % [heads.call(single)])


## Every city's bank: the building stands where it was put, the banker,
## registrar and Pathcaller are inside it, and you can walk up to the counter
## and bank across it.
func _t_city_banks() -> void:
	var main := get_parent()
	var p := World.local_player
	var bankers := {"emberhold": "banker_odile", "lanternhold": "banker_tamsyn", "rainhold": "banker_oduya", "forgehold": "banker_hollis",
			"galehold": "banker_corwin", "barrowhold": "banker_severin", "murkhold": "murk_banker", "duskhold": "dusk_banker"}
	World.time_override = 12.0
	p.god_mode = true  # the human tester isn't welcome in Murkhold or Duskhold: the guards would cut the visit short
	var only := OS.get_environment("BANKS_ONLY")
	for zone_id: String in bankers:
		if only != "" and not zone_id in only.split(","):
			continue
		var faction := str(GameData.npcs[bankers[zone_id]].get("faction", ""))
		var keep_standing: Variant = p.factions.get(faction)
		p.factions[faction] = 1000  # and the banker would refuse them
		while main._changing_zone:
			await _wait(0.25)
		if (main.zone as Zone).zone_id != zone_id:
			World.zone_change.emit(p, zone_id, Vector2.INF, Vector2.INF)
			for k in 120:
				if (main.zone as Zone).zone_id == zone_id and not main._changing_zone:
					break
				await _wait(0.25)
			await _wait(1.0)
		var z := main.zone as Zone
		var banker: Npc = _npcs()[bankers[zone_id]]
		var at := Vector2(banker.global_position.x, banker.global_position.z)
		var center := Vector2.INF  # the bank's middle: its landmark, or Rainhold's piece of the stilt city
		for lm: Dictionary in z.data.get("landmarks", []):
			if str(lm.get("id", "")) == "bank_" + zone_id:
				center = Vector2(lm["pos"][0], lm["pos"][1])
			for piece: Array in lm.get("pieces", []):
				if str(piece[0]) == "bank_" + zone_id:
					center = Vector2(piece[1], piece[2])
		var out := (center - at).normalized()  # the banker stands at the back: the doors are this way
		# out front, looking in
		var front := at + out * (9.0 if zone_id == "rainhold" else 13.0)  # Rainhold's walkway is narrow: the hall across it is close
		p.global_position = Vector3(front.x, z.surface_at(front.x, front.y) + 0.1, front.y)
		p.face_toward(banker.global_position)
		p.zoom = 5.5
		p.pitch = -0.25
		await _wait(1.2)
		await _shot("9zz_bank_" + zone_id)
		# walk up to the counter and bank across it
		var counter := at + out * 2.0
		p.global_position = Vector3(counter.x, z.surface_at(counter.x, counter.y) + 0.1, counter.y)
		p.face_toward(banker.global_position)
		await _wait(0.3)
		World.request_set_target(p.entity_id, banker.entity_id)
		World.request_interact(p.entity_id)
		await _wait(0.3)
		var opened := p.service == "bank"
		World.request_service_close(p.entity_id)
		p.zoom = 1.6
		await _wait(0.6)
		await _shot("9zz_bank_inside_" + zone_id)
		if keep_standing == null:
			p.factions.erase(faction)
		else:
			p.factions[faction] = keep_standing
		print("city_banks: %s - banker at %s, the bank opened across the counter %s (%.1f m away)" % [zone_id, at, opened,
				p.global_position.distance_to(banker.global_position)])
	p.god_mode = false


## A room with its own floor (the crypt) doesn't draw the ground under it, which
## flickered through the tiles; its walking surface is unchanged.
func _t_room_floors() -> void:
	var main := get_parent()
	var p := World.local_player
	World.zone_change.emit(p, "emberhold_crypt", Vector2(0, 2), Vector2(0, -4))  # inside, clear of the stair
	for k in 80:
		if (main.zone as Zone).zone_id == "emberhold_crypt" and not main._changing_zone:
			break
		await _wait(0.25)
	await _wait(1.0)
	var z := main.zone as Zone
	var ground_drawn := false
	for c in z.get_children():
		if c is MeshInstance3D and (c as MeshInstance3D).mesh != null and c.visible and (c as MeshInstance3D).get_aabb().size.x > z.size * 0.9:
			ground_drawn = true
	p.pitch = -0.6
	p.zoom = 4.0
	await _wait(0.8)
	await _shot("9zz_crypt_floor")
	print("room_floors: the crypt's ground drawn %s; standing at %.2f" % [ground_drawn, p.global_position.y])


## The cast bar moves like the other windows: it shows while Settings is open
## so it can be dragged, and keeps where it was left.
func _t_cast_bar_move() -> void:
	var hud = get_parent().hud
	var hidden_before: bool = not hud._cast_panel.visible
	hud._settings_panel.visible = true
	hud._update_cast()
	var shown: bool = hud._cast_panel.visible
	var draggable: bool = hud._cast_panel.has_meta("drag_key")
	await _wait(0.2)
	await _shot("9zz_cast_bar_settings")
	hud._settings_panel.visible = false
	hud._update_cast()
	print("cast_bar_move: draggable %s; hidden when not casting %s, shown with Settings open %s, hidden again %s" % [draggable, hidden_before, shown,
			not hud._cast_panel.visible])


## Bind Wound while resting: you stay sitting (and resting) while you bandage.
## Prabhagaj's line to the Grove (docs/grove-questline.md): only his followers
## at 46+ are offered it; a relic falls only for someone on its step; the last
## relics open the Dawnreach through Amaru; the Dimming's ember, given to the
## Dawn-Tusk, gives the seed and the pendant and brings him to the Grove; the
## keeper walks you home.
func _t_dawn_line() -> void:
	var main := get_parent()
	var p := World.local_player
	var keep := [p.deity, p.level, p.quests.duplicate(true), p.grove_deities.duplicate()]
	var heard: Array[String] = []
	var listen := func(text: String, _c: Color) -> void: heard.append(text)
	World.log_message.connect(listen)
	var said := func(bit: String) -> bool: return heard.any(func(l: String) -> bool: return l.contains(bit))
	for q in ["dawn_1", "dawn_2", "dawn_3", "dawn_4", "dawn_5", "dawn_6"]:
		p.quests.erase(q)
	p.grove_deities.erase("light")
	var amaru: Npc = _npcs()["dawnpriest_amaru"]
	_stand_by(p, amaru)
	# another god's follower, or too young: nothing offered, the word refused
	p.deity = "fire"
	p.level = 50
	heard.clear()
	World.request_hail(p.entity_id)
	World.request_say(p.entity_id, "stirring")
	var fire_refused: bool = not p.quests.has("dawn_1") and not said.call("[stirring]") and World.open_quests(p, "dawnpriest_amaru").is_empty()
	p.deity = "light"
	p.level = 40
	World.request_say(p.entity_id, "stirring")
	var young_refused := not p.quests.has("dawn_1")
	p.level = 50
	heard.clear()
	World.request_hail(p.entity_id)
	var offered: bool = said.call("[stirring]") and World.quest_mark(p, "dawnpriest_amaru") == "!"
	World.request_say(p.entity_id, "stirring")
	var took: bool = p.quests.get("dawn_1", {}).get("active", false)
	# a relic only falls for someone on its step
	var drops := func(mob_id: String) -> bool:
		var m := Mob.new()
		var d: Dictionary = (GameData.mobs[mob_id] as Dictionary).duplicate(true)
		d.erase("gear")
		m.setup(mob_id, d, null)
		m.position = main.zone.ground(30, 30) + Vector3.UP * 0.3
		main.zone.add_child(m)
		await _wait(0.1)
		m.set_meta("damage_by", {p.entity_id: 1})
		World.kill(m, p)
		await _wait(0.2)
		var found := false
		for c in main.zone.get_children():
			if c is Corpse and (c as Corpse).entries.any(func(e: Dictionary) -> bool: return str(e["item"]).begins_with("dl_")):
				found = true
				c.queue_free()
		return found
	var drops_on_step: bool = await drops.call("herd_grandmother")
	var drops_off_step: bool = await drops.call("queen_ismay")  # dawn_2 isn't taken yet
	# steps 2-4 elsewhere: done, their relics in hand; step 5 is Amaru's
	for q in ["dawn_1", "dawn_2", "dawn_3", "dawn_4"]:
		p.quests[q] = {"active": false, "completions": 1}
	p.quests["dawn_5"] = {"active": true, "completions": 0}
	for it in ["dl_attuned_sunstone", "dl_lit_dawn_lamp", "dl_hallowed_spearhead"]:
		p.pack.add(it)
	World.request_say(p.entity_id, "dawn")
	var shut_before := World.zone.zone_id == "lanternhold"
	await _hand_in(p, amaru, ["dl_attuned_sunstone", "dl_lit_dawn_lamp", "dl_hallowed_spearhead"])
	await _wait(1.0)
	var step5: bool = World.quest_done(p, "dawn_5") and p.quests.get("dawn_6", {}).get("active", false)
	World.request_say(p.entity_id, "dawn")
	for k in 80:
		if main.zone.zone_id == "dawnreach" and not main._changing_zone:
			break
		await _wait(0.25)
	await _wait(2.0)
	var inside: bool = main.zone.zone_id == "dawnreach"
	# the realm: from the gate, the crater, the temple
	var z: Zone = main.zone
	for view: Array in [[Vector3(0, 0, 214), Vector3(0, 0, 150), 6.0, -0.15, "gate"], [Vector3(0, 0, 40), Vector3(0, 0, -40), 14.0, -0.45, "crater"],
			[Vector3(0, 0, -140), Vector3(0, 0, -205), 10.0, -0.2, "temple"], [Vector3(-120, 0, 60), Vector3(-175, 0, 30), 12.0, -0.35, "roost"],
			[Vector3(120, 0, 60), Vector3(175, 0, 30), 12.0, -0.35, "cloister"]]:
		p.global_position = z.ground(view[0].x, view[0].z) + Vector3.UP * 0.3
		p.face_toward(view[1])
		p.zoom = view[2]
		p.pitch = view[3]
		await _wait(1.5)
		await _shot("9zz_dawnreach_%s" % view[4])
	var dimming: Mob = null
	for c in z.get_children():
		if c is Mob and (c as Mob).mob_id == "the_dimming":
			dimming = c
	var dimming_up := dimming != null and not dimming.dead
	var elite_ok := false
	for c in z.get_children():
		if c is Mob and (c as Mob).mob_id == "dr_dimmling":
			var m := c as Mob
			elite_ok = m.elite == 4.5 and absf(m.max_hp - GameData.typical_hp(m.level) * 4.5) < 2.0
			print("dawn_line: a dimmling (level %d): %d health (an ordinary monster's %d), elite %.1f" % [m.level, m.max_hp, GameData.typical_hp(m.level), m.elite])
			break
	p.global_position = z.ground(0, -160) + Vector3.UP * 0.3  # the Dawn-Tusk at his temple, from down the road
	p.face_toward(Vector3(0, 0, -194))
	p.zoom = 12.0
	p.pitch = -0.1
	await _wait(1.0)
	await _shot("9zz_dawnreach_god")
	var av: Npc = _npcs()["dawn_avatar"]
	p.global_position = z.ground(14, -176) + Vector3.UP * 0.3
	p.face_toward(av.global_position)
	p.zoom = 6.0
	await _wait(1.0)
	await _shot("9zz_dawnreach_god_near")
	# the ember, to the Dawn-Tusk
	p.pack.add("dl_ember_of_first_light")
	var avatar: Npc = _npcs()["dawn_avatar"]
	_stand_by(p, avatar)
	await _hand_in(p, avatar, ["dl_ember_of_first_light"])
	await _wait(1.0)
	var seed := "grove_seed" in p.owned_item_ids()
	var pendant := "dl_pendant_of_the_last_dawn" in p.owned_item_ids()
	var god := "light" in p.grove_deities
	await _shot("9zz_dawnreach_avatar")
	# and home
	var keeper: Npc = _npcs()["dawnkeeper_ilaya"]
	_stand_by(p, keeper)
	World.request_say(p.entity_id, "return")
	for k in 80:
		if main.zone.zone_id == "lanternhold" and not main._changing_zone:
			break
		await _wait(0.25)
	var home: bool = main.zone.zone_id == "lanternhold"
	World.log_message.disconnect(listen)
	print("dawn_line: refused fire=%s young=%s; offered=%s took=%s; relic on step=%s off step=%s; the way shut before=%s, step5=%s, inside the Dawnreach=%s, the Dimming up=%s (min players %d), its monsters elite=%s; seed=%s pendant=%s god=%s; home=%s" % [
		fire_refused, young_refused, offered, took, drops_on_step, drops_off_step, shut_before, step5, inside,
		dimming_up, int(GameData.mobs["the_dimming"].get("min_players", 0)), elite_ok, seed, pendant, god, home])
	p.deity = keep[0]
	p.level = keep[1]
	p.quests = keep[2]
	p.grove_deities = keep[3]


## A stun holds a player still, breaks the spell they're casting and stops
## spells, shots and items until it passes; a root holds them still but lets
## them cast. The debuff window shows both.
func _t_player_cc() -> void:
	var p := World.local_player
	var z := World.zone
	var walk := func(seconds: float) -> float:
		var from := p.global_position
		Input.action_press("move_forward")
		await _wait(seconds)
		Input.action_release("move_forward")
		await _wait(0.2)
		return Vector2(p.global_position.x - from.x, p.global_position.z - from.z).length()
	p.global_position = z.ground(40, 40) + Vector3.UP * 0.3
	await _wait(0.5)
	var free: float = await walk.call(0.8)
	# a stun mid-cast
	var spell := ""
	for id: String in p.spells:
		if float(GameData.spells[id].get("cast_time", 0)) > 0.5 and str(GameData.spells[id].get("target", "")) == "self" or str(GameData.spells[id].get("type", "")) == "buff":
			spell = id
			break
	p.mana = p.max_mana
	p.cooldowns.clear()
	World.request_cast(p.entity_id, spell)
	var casting := not p.cast.is_empty()
	World._stun(p, 2.5)
	var broken := p.cast.is_empty()
	World.request_cast(p.entity_id, spell)
	var refused := p.cast.is_empty()
	var hud = get_parent().hud
	var stun_shown: bool = hud._debuff_list().any(func(d: Array) -> bool: return d[0] == "stunned")
	var stunned: float = await walk.call(0.8)
	await _wait(1.8)  # it passes
	var after: float = await walk.call(0.8)
	# a root: no walking, but casting is fine
	p.root_left = 2.0
	var rooted: float = await walk.call(0.8)
	p.cooldowns.clear()
	World.request_cast(p.entity_id, spell)
	var casts_rooted := not p.cast.is_empty()
	p.cast = {}
	print("player_cc: walked %.1f m free, %.2f stunned, %.1f after, %.2f rooted; %s cast %s, broken by the stun %s, refused while stunned %s, casts rooted %s; debuff shown %s" % [free, stunned, after, rooted, spell, casting, broken, refused, casts_rooted, stun_shown])


func _t_bind_sitting() -> void:
	var p := World.local_player
	var keep := [p.char_class, p.level, p.spells.duplicate(), p.cooldowns.duplicate()]
	p.char_class = "warrior"
	p.level = 10
	p.recalc_stats()
	if not "bind_wound" in p.spells:
		p.spells.append("bind_wound")
	p.cooldowns.erase("bind_wound")
	p.hp = maxi(1, p.max_hp / 3)
	World.request_sit(p.entity_id, true)
	var hp0 := p.hp
	World.request_cast(p.entity_id, "bind_wound")
	var casting := not p.cast.is_empty()
	var sat_casting := p.sitting
	await _wait(4.6)
	var healed := p.hp - hp0
	var still := p.sitting
	await _shot("9zz_bind_sitting")
	World.request_sit(p.entity_id, false)
	p.char_class = keep[0]
	p.level = keep[1]
	p.spells = keep[2]
	p.cooldowns = keep[3]
	p.recalc_stats()
	p.hp = p.max_hp
	print("bind_sitting: sat down, Bind Wound -> casting %s still sitting %s; done -> healed %d (with resting), still sitting %s" % [casting, sat_casting, healed, still])


## The text windows resize by their corner grip: bigger up and right, the
## bottom-left corner held; the size is kept; Reset puts it back.
func _t_chat_resize() -> void:
	var hud = get_parent().hud
	var panel: Control = hud._log_panel
	var keep_sizes: Dictionary = Controls.window_sizes.duplicate()
	var keep_pos: Dictionary = Controls.window_positions.duplicate()
	await _wait(0.3)
	var grip: Control = null
	for c in panel.get_children():
		if c is Control and (c as Control).top_level:
			grip = c
	var before: Vector2 = hud._log.custom_minimum_size
	var corner := panel.global_position + Vector2(0, panel.size.y)
	var at := grip.global_position + Vector2(8, 8)
	var press := InputEventMouseButton.new()
	press.button_index = MOUSE_BUTTON_LEFT
	press.pressed = true
	press.global_position = at
	grip.gui_input.emit(press)
	var move := InputEventMouseMotion.new()
	move.global_position = at + Vector2(140, -90)  # up and to the right: bigger
	grip.gui_input.emit(move)
	await _wait(0.2)
	press.pressed = false
	grip.gui_input.emit(press)
	await _wait(0.2)
	var after: Vector2 = hud._log.custom_minimum_size
	var corner_after := panel.global_position + Vector2(0, panel.size.y)
	var saved: Variant = Controls.window_sizes.get("chat")
	await _shot("9zz_chat_resized")
	UIKit.reset_windows(hud.root)
	await _wait(0.2)
	var reset: Vector2 = hud._log.custom_minimum_size
	Controls.window_sizes = keep_sizes  # the test leaves your own settings as they were
	Controls._save_setting("window_sizes", keep_sizes)
	Controls.window_positions = keep_pos
	Controls._save_setting("window_positions", keep_pos)
	print("chat_resize: text area %s -> %s (saved %s), bottom-left corner %s -> %s; reset -> %s; grip on the chat window too %s" % [before, after, saved,
			corner, corner_after, reset, hud._group_log_panel.get_children().any(func(c: Node) -> bool: return c is Control and (c as Control).top_level)])


## June, Lanternhold's unicorn: her coat runs through the rainbow (the shader on
## every surface, and it shifts with time), she strolls round the plaza, and
## nobody can attack her.
func _t_june() -> void:
	var main := get_parent()
	var p := World.local_player
	if (main.zone as Zone).zone_id != "lanternhold":
		World.zone_change.emit(p, "lanternhold", Vector2.INF, Vector2.INF)
		for k in 120:
			if (main.zone as Zone).zone_id == "lanternhold" and not main._changing_zone:
				break
			await _wait(0.25)
		await _wait(1.0)
	World.time_override = 12.0
	if not _npcs().has("june"):
		print("june: not placed in Lanternhold (she's hidden for now: put her entry back in lanternhold.json's npcs)")
		return
	var june: Npc = _npcs()["june"]
	june._form_check = 0.0  # by day she's June, whatever hour the test began at
	await _wait(1.2)
	var rainbow := 0
	for mi: MeshInstance3D in june.visual.find_children("*", "MeshInstance3D", true, false):
		for i in mi.get_surface_override_material_count():
			if mi.get_surface_override_material(i) is ShaderMaterial:
				rainbow += 1
	var start := june.global_position
	var side := june.global_position + june.global_basis.x * 6.0
	p.global_position = Vector3(side.x, june.global_position.y + 0.1, side.z)
	p.face_toward(june.global_position)
	p.zoom = 3.0
	p.pitch = -0.15
	await _wait(1.5)
	await _shot("9zz_june_a")
	await _wait(4.0)
	p.face_toward(june.global_position)
	await _wait(0.5)
	await _shot("9zz_june_b")
	var walked := june.global_position.distance_to(start)
	print("june: %d rainbow surfaces, walked %.1f m of her round in 6 s, attackable %s, %d stops on her round" % [rainbow, walked,
			World.can_attack(p, june), june.patrol.size()])
	# after dark she's Fresnebagcdrs: an elf with black pigtails, the cat on her shoulder, her own lines
	World.time_override = 21.4
	june._form_check = 0.0
	await _wait(1.5)
	var cm := june.visual as CharacterModel
	var pigtails := cm != null and cm.find_child("hair_pigtails*", true, false) != null
	var cat := cm != null and cm.find_child("june_cat_shoulder*", true, false) != null
	var heard: Array[String] = []
	var listen := func(text: String, _c: Color) -> void: heard.append(text)
	World.log_message.connect(listen)
	_stand_by(p, june)
	World.request_set_target(p.entity_id, june.entity_id)
	World.request_say(p.entity_id, "hail")
	await _wait(0.3)
	World.log_message.disconnect(listen)
	var side2 := june.global_position + june.global_basis.x * 3.5
	p.global_position = Vector3(side2.x, june.global_position.y + 0.1, side2.z)
	p.face_toward(june.global_position)
	p.zoom = 2.0
	await _wait(0.6)
	await _shot("9zz_june_night")
	var night_name := june.display_name
	var night_look: Dictionary = june.look.duplicate()
	World.time_override = 9.0
	june._form_check = 0.0
	await _wait(1.5)
	print("june: after dark -> '%s' (%s %s %s, hair %s), pigtails %s, cat on her shoulder %s, says %s" % [night_name, night_look.get("race"), night_look.get("gender"),
			night_look.get("model"), night_look.get("hair"), pigtails, cat, heard.filter(func(l: String) -> bool: return "says" in l).slice(0, 1)])
	print("june: morning -> '%s' (%s) again" % [june.display_name, june.look.get("model")])


## Velassa's rogue side: her player badly hurt, she leaps behind the monster on
## them and backstabs it; the hate stays theirs; well again, she's back at heel.
func _t_velassa_pounce() -> void:
	var p := World.local_player
	var z := World.zone
	p.global_position = z.ground(40, 40) + Vector3.UP
	p.equipment["companion"] = "velassas_collar"
	await _wait(1.5)
	var cat := World.get_object(p.velassa_id) as Npc
	var d: Dictionary = (GameData.mobs["gnoll_scout"] as Dictionary).duplicate(true)
	d.erase("gear")
	var mob := Mob.new()
	mob.setup("gnoll_scout", d, null)
	mob.position = z.ground(40, 37) + Vector3.UP * 0.2
	z.add_child(mob)
	await _wait(0.3)
	mob.max_hp = 99999
	mob.hp = mob.max_hp
	p.max_hp = 99999
	p.hp = 20000  # badly hurt, and not about to die
	mob.add_hate(p, 50.0)
	var lines: Array[String] = []
	var listen := func(text: String, _c: Color) -> void: lines.append(text)
	World.log_message.connect(listen)
	await _wait(6.0)
	var leapt := lines.any(func(l: String) -> bool: return l.contains("leaps into the fight"))
	var stabs := lines.filter(func(l: String) -> bool: return l.begins_with("Velassa backstabs")).size()
	var behind := cat != null and World.behind(cat, mob)
	var still_you := mob.top_hated() == p
	p.zoom = 4.0
	p.face_toward(mob.global_position)
	await _shot("9zz_velassa_pounce")
	p.hp = p.max_hp  # well again: she comes back to heel
	await _wait(2.0)
	var home := cat != null and cat._pounce == null
	World.log_message.disconnect(listen)
	print("velassa_pounce: leapt=%s stabs=%d (6 s) behind=%s hurt=%d hate stays yours=%s back at heel=%s" % [leapt, stabs, behind, mob.max_hp - mob.hp, still_you, home])
	mob.queue_free()
	p.equipment.erase("companion")


func _t_city_paths() -> void:
	var p := World.local_player
	for city in ["lanternhold", "emberhold", "forgehold", "galehold", "barrowhold"]:
		if World.zone.zone_id != city:
			World.zone_change.emit(p, city, Vector2(0, 30), Vector2(0, 0))
			await _wait(4.0)
		p = World.local_player
		var z := World.zone
		var views: Array = [[Vector3(18, 0, 34), Vector3(0, 0, 10), 30.0, -1.2]]
		if city == "lanternhold":
			views += [[Vector3(0, 0, 26), Vector3.ZERO, 6.0, -0.25], [Vector3(-9.5, 0, 0), Vector3.ZERO, 3.0, -0.1]]
		for k in views.size():
			var view: Array = views[k]
			p.global_position = z.ground(view[0].x, view[0].z) + Vector3.UP * 0.2
			p.face_toward(view[1])
			p.zoom = view[2]
			p.pitch = view[3]
			await _wait(1.0)
			await _shot("9zz_city_paths_%s_%d" % [city, k])
	print("city_paths: shots taken")


## Greenmoor's apple barrel: twenty apples, a line each, Velassa climbs out of
## the bottom; her collar calls her and sends her home; with her at your heel
## your ranged attacks hit 5% harder; the barrel is empty for you after.
func _t_velassa() -> void:
	var p := World.local_player
	var barrel: Npc = _npcs()["apple_barrel"]
	var keep := [p.quests.duplicate(true), p.equipment.duplicate()]
	p.quests.erase("apple_barrel")
	for i in p.pack.slots.size():
		p.pack.slots[i] = {}
	var heard: Array[String] = []
	var listen := func(text: String, _c: Color) -> void: heard.append(text)
	World.log_message.connect(listen)
	var bramble: Npc = _npcs()["orchard_bramble"]
	_stand_by(p, bramble)
	World.request_set_target(p.entity_id, bramble.entity_id)
	for word: String in ["hail", "barrel", "bottom"]:
		World.request_say(p.entity_id, word)
	var bramble_said := heard.filter(func(l: String) -> bool: return l.begins_with("Orchardkeeper Bramble says"))
	heard.clear()
	var unnamed := not barrel.nameplate.visible
	var in_cycle := false
	for k in 5:
		p._cycle_interact()
		in_cycle = in_cycle or p.target == barrel
	_stand_by(p, barrel)
	var stages := []
	for k in 20:
		World.request_take_apple(p.entity_id, barrel.entity_id)
		if k % 5 == 4:
			barrel._update_prop()
			stages.append(str(barrel.look.get("shape", "")).trim_prefix("prop:"))
	World.request_take_apple(p.entity_id, barrel.entity_id)  # the 21st: empty
	World.log_message.disconnect(listen)
	await _wait(1.0)
	var apples := p.pack.count("greenmoor_apple")
	var collar := 1 if p.equipment.get("companion", "") == "velassas_collar" else 0  # put straight on, in the companion slot
	var out := World.velassa_with(p)
	var cat := World.get_object(p.velassa_id) as Npc
	var title := ""
	if cat != null and cat.nameplate.get_child_count() > 0:
		title = (cat.nameplate.get_child(0) as Label3D).text
	p.global_position += Vector3(3, 0, 3)
	await _wait(1.5)
	var follows := cat != null and cat.distance_to(p) < 4.0
	get_parent().hud._inv_panel.visible = true
	get_parent().hud._refresh_inventory()
	await _wait(0.4)
	await _shot("9zz_velassa_slot")
	get_parent().hud._inv_panel.visible = false
	if cat != null:  # look at her
		p.face_toward(cat.global_position)
		p.rotate_y(PI)
	p.zoom = 2.6
	p.pitch = -0.35
	await _wait(0.4)
	await _shot("9zz_velassa")
	# the bonus: the same shot with and without her
	var rat: Mob = null
	for m in World.get_mobs():
		if not m.dead and World.zone_of(m) == World.zone_of(p):
			rat = m
			break
	var rat_was := rat.global_position
	rat.global_position = p.global_position - p.global_basis.z * 8.0  # brought over for the shot: nothing lives in this corner
	rat.set_physics_process(false)
	p.equipment["range"] = "leather_sling"  # thrown: no arrows needed
	p.pack.add("sling_stone", 99)
	p.pack.add("sling_stone", 99)
	p.pack.add("sling_stone", 99)
	p.pack.add("sling_stone", 99)
	p.pack.add("sling_stone", 99)
	var skills0: Dictionary = p.skills.duplicate()
	var shoot := func() -> int:  # the smallest hit of 150 shots at the same skill (x10, so 5% shows past the rounding)
		p.skills = skills0.duplicate()
		seed(7)
		var total := 0
		for k in 150:
			rat.max_hp = 99999
			rat.hp = rat.max_hp
			p.cooldowns.erase("ranged")
			World._ranged_shot(p, rat, 10.0)
			var hit := rat.max_hp - rat.hp
			if hit > 0:
				total = hit if total == 0 else mini(total, hit)  # the smallest landed hit: no misses, no crits
		return total
	var with_her: int = shoot.call()
	World.request_unequip(p.entity_id, "companion")  # the collar off: home she goes
	await _wait(0.3)
	var home := not World.velassa_with(p)
	var hud = get_parent().hud
	var buff_gone: bool = not hud._buff_list().any(func(b: Array) -> bool: return b[0] == "velassas_company")
	var without: int = shoot.call()
	World.request_equip(p.entity_id, _where(p, "velassas_collar"))  # and on again: she comes back
	await _wait(0.3)
	var back := World.velassa_with(p)
	var worn_again: bool = p.equipment.get("companion", "") == "velassas_collar"
	var buff_back: bool = hud._buff_list().any(func(b: Array) -> bool: return b[0] == "velassas_company")
	hud._update_buffs()
	await _wait(0.2)
	await _shot("9zz_velassa_buff")
	barrel._update_prop()
	var empty_look := str(barrel.look.get("shape", ""))
	var back_from_save := Player.new()
	back_from_save.from_save(p.to_save())
	var remembered := back_from_save.velassa_out
	back_from_save.free()
	# the orchard, from a little way off
	p.global_position = barrel.global_position + Vector3(-32, 0.5, 30)
	p.face_toward(barrel.global_position)
	var zone := World.zone_of(p)
	p.global_position.y = zone.height_at(p.global_position.x, p.global_position.z) + 0.2
	p.zoom = 3.0
	p.pitch = -0.12
	await _wait(1.0)
	await _shot("9zz_apple_orchard")
	# a magician with an elemental out keeps it when Velassa comes, and the other way round
	var cls0 := p.char_class
	p.char_class = "magician"
	World._finish_spell(p, "call_of_earth", p, true)
	await _wait(0.5)
	var pet_out := World.get_object(p.pet_id) is Pet
	await _wait(0.3)
	var both := World.get_object(p.pet_id) is Pet and World.velassa_with(p)
	await _shot("9zz_velassa_and_pet")
	var power := func(id: String) -> float:  # with her, from the caster's own book
		var had: bool = id in p.spells
		if not had:
			p.spells.append(id)
		var f := World.spell_power(p, id, GameData.spells[id])
		if not had:
			p.spells.erase(id)
		return f
	var with_nuke: float = power.call("cinder_dart")
	var with_heal: float = power.call("minor_healing")
	World.request_unequip(p.entity_id, "companion")  # home for a moment
	await _wait(0.2)
	var without_nuke: float = power.call("cinder_dart")
	World.request_equip(p.entity_id, _where(p, "velassas_collar"))
	await _wait(0.3)
	print("velassa: a damage spell's power with her x%.3f, without x%.3f; a heal's with her x%.3f" % [with_nuke, without_nuke, with_heal])
	World.request_pet(p.entity_id, "leave")
	await _wait(0.3)
	var still_her := World.velassa_with(p)
	p.char_class = cls0
	print("velassa: a magician's earth elemental out %s, then Velassa called: both at once %s; the elemental dismissed, Velassa stays %s" % [pet_out, both, still_her])
	World.request_unequip(p.entity_id, "companion")
	rat.hate.clear()
	rat.global_position = rat_was
	rat.set_physics_process(true)
	p.quests = keep[0]
	p.equipment = keep[1]
	print("velassa: Bramble the orchard keeper says %s" % [bramble_said.map(func(l: String) -> String: return l.left(90))])
	print("velassa: the barrel has no name over it %s, and T never picks it %s" % [unnamed, not in_cycle])
	print("velassa: 20 apples taken -> %d in the bags, the lines %s" % [apples, heard.slice(0, 3)])
	print("velassa: the 20th -> %s" % [heard.filter(func(l: String) -> bool: return "violet eyes" in l or "climbs out" in l)])
	print("velassa: the 21st -> '%s'; collar %d; she's out %s, titled '%s', follows %s" % [heard.back(), collar, out, title, follows])
	print("velassa: smallest hit with her %d, without %d (+%.0f%%); the collar sent her home %s and called her back %s, and is worn again %s" % [with_her, without,
			100.0 * (float(with_her) / maxf(1.0, float(without)) - 1.0), home, back, worn_again])
	print("velassa: the barrel empties as you go %s; her buff shows while she's out %s, gone when she's home %s" % [stages, buff_back, buff_gone])
	print("velassa: the barrel shows you %s once emptied; after a save and load she comes back with you %s" % [empty_look, remembered])
