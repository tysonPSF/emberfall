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
			(c as CharCreate).confirmed.emit({"name": "Tester", "class": "wizard"})
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
