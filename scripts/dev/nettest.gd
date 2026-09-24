extends Node
## Two-player network check, run against a local dedicated server:
##   godot --headless --path . -- --server --port=7788 --zone=greenmoor
##   godot --path . -- --nettest=Alpha --port=7788 --shots=<dir>
##   godot --path . -- --nettest=Bravo --port=7788 --shots=<dir>
## Alpha fights a mob and loots it; Bravo watches; both then camp out.

var who := ""
var port := Net.DEFAULT_PORT
var shots_dir := ""
var _list: Array = []
var _listed_once := false


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--nettest="):
			who = a.substr(10)
		elif a.begins_with("--port="):
			port = int(a.substr(7))
		elif a.begins_with("--shots="):
			shots_dir = a.substr(8)
	World.log_message.connect(func(t: String, _c: Color) -> void: print("[%s log] %s" % [who, t]))
	_run()


func _run() -> void:
	var main := get_parent()
	await _wait(0.5)
	for c in main.get_children():
		if c is CharCreate:
			c.queue_free()
	# connect, make (or reuse) an account, make (or pick) the character, enter
	Net.connect_to("127.0.0.1:%d" % port)
	await Net.connected_ok
	Net.characters_listed.connect(func(l: Array) -> void:
		_list = l
		_listed_once = true)
	Net.server_message.connect(func(t: String, e: bool) -> void: print("[%s] server says: %s%s" % [who, t, " (error)" if e else ""]))
	Net.login(who.to_lower(), "hunter2", true)
	await _wait(1.0)
	if not _listed_once:
		Net.login(who.to_lower(), "hunter2", false)  # the account already existed
		await _wait(1.0)
	var names := _list.map(func(c: Dictionary) -> String: return str(c["name"]))
	print("[%s] logged in; characters: %s" % [who, names])
	if not who in names:
		if "--group" in OS.get_cmdline_user_args() and who in ["Alpha", "Bravo"]:
			Net.import_character({"name": who, "class": "warrior" if who == "Alpha" else "cleric", "deity": "fire",
					"level": 3 if who == "Alpha" else 5, "spells": ["kick", "taunt"] if who == "Alpha" else ["minor_healing", "circle_of_mending", "fire_bolt"],
					"equipment": {"primary": "rusty_short_sword"} if who == "Alpha" else {"primary": "worn_staff"}})
		elif who == "Importer":
			Net.import_character({"name": "Importer", "class": "cleric", "deity": "water", "level": 4, "xp": 50,
					"inventory": ["gnoll_fang", "not_a_real_item"], "equipment": {"primary": "worn_staff"}})
		else:
			var cls := "warrior" if who == "Alpha" else "cleric"
			if "--wear" in OS.get_cmdline_user_args() and who == "Alpha":
				Net.import_character({"name": "Alpha", "class": "warrior", "deity": "fire", "equipment": {"head": "cloth_cap", "primary": "rusty_short_sword"}})
			else:
				Net.create_character(who, cls, "fire")
		await _wait(1.0)
		print("[%s] after creating: %s" % [who, _list.map(func(c: Dictionary) -> String: return "%s L%d" % [c["name"], c["level"]])])
	Net.enter_world(who)
	for k in 40:
		if World.local_player != null:
			break
		await _wait(0.25)
	var p := World.local_player
	if p == null:
		print("[%s] never joined" % who)
		get_tree().quit(1)
		return
	await _wait(2.0)
	var counts := {}
	for obj: Node3D in World.objects.values():
		var kind := "player" if obj is Player else ("mob" if obj is Mob else ("npc" if obj is Npc else "corpse"))
		counts[kind] = int(counts.get(kind, 0)) + 1
	print("[%s] joined as id %d; mirrored %s" % [who, p.entity_id, counts])
	p.zoom = 9.0
	p.pitch = -0.35

	if "--wear" in OS.get_cmdline_user_args():
		if who == "Alpha":
			await _wait(3.0)
			World.request_unequip(p.entity_id, "head")
			await _wait(3.0)
			var at := ""
			for place: String in p.pack.places():
				if p.pack.get_at(place).get("item", "") == "cloth_cap":
					at = place
			World.request_equip(p.entity_id, at)
			await _wait(4.0)
		else:
			for k in 8:
				await _wait(1.5)
				for q in World.get_players():
					if q != p:
						var attached := (q.visual as CharacterModel)._worn.keys() if q.visual is CharacterModel else []
						print("[Bravo] t=%.1fs Alpha look.worn=%s on model=%s" % [(k + 1) * 1.5, q.look.get("worn"), attached])
	elif "--group" in OS.get_cmdline_user_args():
		await _group_test(p)
	elif "--chat" in OS.get_cmdline_user_args():
		await _wait(2.0)
		if who == "Alpha":
			for line in ["hello there", "/tell bravo psst, over here", "/ooc anyone want to group?", "/who all", "/lfg", "/random 20", "/tell nobody hi", "/bogus"]:
				World.request_chat(p.entity_id, line)
				await _wait(0.4)
			await _wait(3.0)
		else:
			await _wait(3.0)
			for line in ["/r got it", "/shout the whole zone hears this"]:
				World.request_chat(p.entity_id, line)
				await _wait(0.4)
			await _wait(2.0)
	elif who == "Sprinter":
		# hold forward and Shift like a player would; the server must accept the speed
		var start := p.global_position
		var stam0 := p.stamina
		Input.action_press("move_forward")
		Input.action_press("sprint")
		await _wait(2.0)
		var mid_sprinting := p.sprinting
		var mid_stam := p.stamina
		Input.action_release("sprint")
		Input.action_release("move_forward")
		await _wait(1.0)
		print("[Sprinter] ran %.1f m in 2 s (walk would be 14); sprinting=%s stamina %.0f -> %.0f; snapped back=%s" % [
				Vector2(p.global_position.x - start.x, p.global_position.z - start.z).length(), mid_sprinting, stam0, mid_stam,
				Vector2(p.global_position.x - start.x, p.global_position.z - start.z).length() < 5.0])
	elif who == "Zoner":
		# walk into the pass to Emberhold; for now the whole server follows
		await _walk_to(p, Vector3(0, 0, 150))
		await _walk_to(p, Vector3(0, 0, 182))
		for k in 40:
			if World.zone != null and World.zone.zone_id == "emberhold":
				break
			await _wait(0.25)
		await _wait(3.0)
		var mobs := World.get_mobs().size()
		var npcs := 0
		for obj: Node3D in World.objects.values():
			npcs += 1 if obj is Npc else 0
		print("[Zoner] zone now %s at %s; mirrored %d mobs, %d npcs, %d players" % [World.zone.zone_id, p.global_position, mobs, npcs, World.get_players().size()])
		if "--round-trip" in OS.get_cmdline_user_args():
			await _wait(4.0)
			await _walk_to(p, Vector3(0, 0, -99))  # Emberhold's gate back out to Greenmoor
			for k in 40:
				if World.zone != null and World.zone.zone_id == "greenmoor":
					break
				await _wait(0.25)
			await _wait(3.0)
			print("[Zoner] back in %s; mirrored %d mobs, %d players" % [World.zone.zone_id, World.get_mobs().size(), World.get_players().size()])
	elif who == "Alpha":
		# walk a few steps; Bravo should see it
		for k in 20:
			p.global_position += Vector3(0, 0, -0.25)
			await get_tree().physics_frame
		await _wait(1.0)
		var mob: Mob = null
		for m in World.get_mobs():
			if mob == null or p.distance_to(m) < p.distance_to(mob):
				mob = m
		print("[Alpha] nearest mob %s (id %d) at %.1f m" % [mob.display_name, mob.entity_id, p.distance_to(mob)])
		await _walk_to(p, mob.global_position + Vector3(0, 0, 2.0))
		World.request_set_target(p.entity_id, mob.entity_id)
		World.request_toggle_attack(p.entity_id)
		for k in 5400:  # chase it down: mobs wander and flee
			if not is_instance_valid(mob) or mob.dead:
				break
			if p.distance_to(mob) > 2.2:
				var d := Vector2(mob.global_position.x - p.global_position.x, mob.global_position.z - p.global_position.z)
				var step := d.normalized() * 6.5 * get_physics_process_delta_time()
				p.global_position += Vector3(step.x, 0, step.y)
			p.face_toward(mob.global_position)
			await get_tree().physics_frame
		print("[Alpha] mob gone: %s; my hp %d/%d xp %d" % [not is_instance_valid(mob), p.hp, p.max_hp, p.xp])
		await _wait(1.0)
		var corpse: Corpse = null
		for obj: Node3D in World.objects.values():
			if obj is Corpse and (corpse == null or p.distance_to(obj) < p.distance_to(corpse)):
				corpse = obj
		if corpse != null:
			await _walk_to(p, corpse.global_position + Vector3(0, 0, 1.5))
			await _wait(0.5)
			World.request_loot_open(p.entity_id, corpse.object_id)
			await _wait(1.0)
			await _shot("net_alpha_loot")
			print("[Alpha] corpse %s holds %s" % [corpse.display_name, corpse.entries])
			World.request_loot_all(p.entity_id, corpse.object_id)
			await _wait(1.0)
		print("[Alpha] inventory now %s coin %d" % [p.pack.item_ids(), p.coin])
	else:
		await _wait(6.0)
		var alpha: Player = null
		for q in World.get_players():
			if q != p:
				alpha = q
		print("[Bravo] sees Alpha: %s at %s" % [alpha != null, alpha.global_position if alpha != null else "-"])
		if "--stay" in OS.get_cmdline_user_args():
			for k in 16:
				await _wait(2.5)
				print("[Bravo] t=%ds zone %s, players seen %d, mobs %d" % [(k + 1) * 5 / 2, World.zone.zone_id, World.get_players().size(), World.get_mobs().size()])
		if "--wait-zone" in OS.get_cmdline_user_args():
			for k in 120:
				if World.zone != null and World.zone.zone_id == "emberhold":
					break
				await _wait(0.5)
			print("[Bravo] followed to %s" % World.zone.zone_id)
		if alpha != null:
			await _walk_to(p, alpha.global_position + Vector3(3, 0, 4))
			p.face_toward(alpha.global_position)
		await _wait(8.0)
		await _shot("net_bravo_view")

	await _wait(3.0)
	World.request_camp(p.entity_id)
	for k in 60:
		if World.local_player == null:
			break
		await _wait(0.5)
	print("[%s] camped: back at character select = %s" % [who, World.local_player == null])
	if "--reenter" in OS.get_cmdline_user_args() and World.local_player == null:
		Net.enter_world(who)
		for k in 40:
			if World.local_player != null:
				break
			await _wait(0.25)
		await _wait(1.0)
		var q := World.local_player
		print("[%s] re-entered: level %d xp %d inventory %s" % [who, q.level, q.xp, q.pack.item_ids()])
	print("NETTEST DONE %s" % who)
	get_tree().quit()


func _group_test(p: Player) -> void:
	var said := func(line: String) -> void: World.request_chat(p.entity_id, line)
	if who == "Alpha":
		await _wait(3.0)
		said.call("/invite bravo")
		await _wait(3.0)
		print("[Alpha] group now %s" % [p.group.map(func(m: Dictionary) -> String: return "%s%s" % ["*" if m["leader"] else "", m["name"]])])
		said.call("/g ready when you are")
		await _wait(1.0)
		var mob: Mob = null
		for m in World.get_mobs():
			if m.level >= 2 and (mob == null or p.distance_to(m) < p.distance_to(mob)):
				mob = m
		print("[Alpha] pulling %s level %d" % [mob.display_name, mob.level])
		World.request_set_target(p.entity_id, mob.entity_id)
		World.request_toggle_attack(p.entity_id)
		for k in 5400:
			if not is_instance_valid(mob) or mob.dead:
				break
			if p.distance_to(mob) > 2.2:
				var d := Vector2(mob.global_position.x - p.global_position.x, mob.global_position.z - p.global_position.z)
				var step := d.normalized() * 6.5 * get_physics_process_delta_time()
				p.global_position += Vector3(step.x, 0, step.y)
			p.face_toward(mob.global_position)
			await get_tree().physics_frame
		await _wait(6.0)
		var corpse: Corpse = null
		for obj: Node3D in World.objects.values():
			if obj is Corpse and (corpse == null or p.distance_to(obj) < p.distance_to(corpse)):
				corpse = obj
		if corpse != null:
			await _walk_to(p, corpse.global_position + Vector3(0, 0, 1.5))
			World.request_loot_open(p.entity_id, corpse.object_id)
			await _wait(1.0)
			World.request_loot_all(p.entity_id, corpse.object_id)
		await _wait(8.0)
		print("[Alpha] level %d xp %d coin %d hp %d/%d" % [p.level, p.xp, p.coin, p.hp, p.max_hp])
		await _wait(6.0)
	elif who == "Bravo":
		var invited := [""]
		World.group_invited.connect(func(from: String) -> void: invited[0] = from if from != "" else invited[0])
		for k in 40:
			if invited[0] != "":
				break
			await _wait(0.25)
		print("[Bravo] invite popup from %s; spells %s" % [invited[0], p.spells])
		World.request_group_accept(p.entity_id)
		await _wait(1.5)
		p.target_group_member(0)
		await _wait(0.8)
		print("[Bravo] F2 targets %s" % (p.target.display_name if p.target is Entity else "nothing"))
		p.start_follow()
		await _wait(5.0)
		var alpha := p.target as Entity
		print("[Bravo] following: %.1f m behind %s" % [p.distance_to(alpha) if alpha != null else -1.0, alpha.display_name if alpha != null else "-"])
		said.call("/assist alpha")
		await _wait(1.0)
		print("[Bravo] assist target: %s" % (p.target.display_name if p.target is Entity else "nothing"))
		await _wait(10.0)
		p.stop_follow()
		World.request_cast(p.entity_id, "circle_of_mending")
		await _wait(4.5)
		print("[Bravo] level %d xp %d coin %d" % [p.level, p.xp, p.coin])
		await _wait(8.0)
		said.call("/disband")
		await _wait(1.0)
		print("[Bravo] group after disband: %d" % p.group.size())
	else:  # Outsider: shadows Alpha, then tries to loot Alpha's kill
		var kill_seen := [false]
		World.log_message.connect(func(t: String, _c: Color) -> void:
			if t.contains("slain by Alpha"):
				kill_seen[0] = true)
		var alpha: Player = null
		for k in 3600:
			if kill_seen[0]:
				break
			if alpha == null:
				for q in World.get_players():
					if q.display_name == "Alpha":
						alpha = q
			elif p.distance_to(alpha) > 4.0:
				var d := Vector2(alpha.global_position.x - p.global_position.x, alpha.global_position.z - p.global_position.z)
				var step := d.normalized() * 6.5 * get_physics_process_delta_time()
				p.global_position += Vector3(step.x, 0, step.y)
			await get_tree().physics_frame
		await _wait(0.8)
		var corpse: Corpse = null
		for obj: Node3D in World.objects.values():
			if obj is Corpse and (corpse == null or p.distance_to(obj) < p.distance_to(corpse)):
				corpse = obj
		print("[Outsider] saw the kill: %s; nearest corpse %s at %.1f m" % [kill_seen[0], corpse.display_name if corpse else "-", p.distance_to(corpse) if corpse else -1.0])
		if corpse != null:
			World.request_loot_open(p.entity_id, corpse.object_id)
			await _wait(1.0)
		await _wait(6.0)


## Walks at a normal run, so the server's speed check lets it through.
func _walk_to(p: Player, goal: Vector3) -> void:
	var zone_at_start := World.zone
	for k in 4000:
		if World.zone != zone_at_start:
			return  # zoned: the goal was in the old zone
		var d := Vector2(goal.x - p.global_position.x, goal.z - p.global_position.z)
		if d.length() < 0.5 or not is_instance_valid(p):
			return
		var step := d.normalized() * minf(d.length(), 6.5 * get_physics_process_delta_time())
		p.global_position += Vector3(step.x, 0, step.y)
		p.face_toward(goal)
		await get_tree().physics_frame


func _wait(seconds: float) -> void:
	await get_tree().create_timer(seconds).timeout


func _shot(name_: String) -> void:
	if shots_dir == "":
		return
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png("%s/%s.png" % [shots_dir, name_])
