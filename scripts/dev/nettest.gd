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
	if "--delete" in OS.get_cmdline_user_args():
		await _delete_test()
		get_tree().quit()
		return
	if not who in names:
		if "--wake" in OS.get_cmdline_user_args():
			Net.import_character({"name": who, "class": "warrior", "deity": "fire", "level": 5, "race": "human", "stats": {"str": 10, "sta": 10, "agi": 5},
					"zone": "greenmoor", "position": [0, 2, 20]})
		elif "--swing" in OS.get_cmdline_user_args():
			Net.import_character({"name": who, "class": "warrior", "deity": "fire", "level": 1, "race": "human", "stats": {"sta": 10},
					"zone": "greenmoor", "position": [0, 2, 20]})
		elif "--guild" in OS.get_cmdline_user_args():
			Net.import_character({"name": who, "class": "warrior", "deity": "fire", "level": 12, "coin": 20000, "race": "human", "stats": {"str": 10, "sta": 10, "agi": 5},
					"zone": "emberhold", "position": [8.0 if who == "Alpha" else 4.0, 2, 28]})
		elif "--homecoming" in OS.get_cmdline_user_args():  # a troll from before the Blackwater, logged out in Rainhold
			Net.import_character({"name": who, "class": "warrior", "deity": "dark", "level": 5, "race": "troll", "stats": {"str": 10, "sta": 10, "agi": 5},
					"zone": "rainhold", "bind": "rainhold", "position": [0, 2, 40]})
		elif "--share" in OS.get_cmdline_user_args():
			var qs := {"fang_bounty": {"active": true, "completions": 0}, "trail_pack_cord": {"active": true, "completions": 0},
					"trail_pack_hide": {"active": true, "completions": 0}, "rain_pack_needles": {"active": true, "completions": 0}} \
					if who == "Alpha" else {"rain_pack_needles": {"active": false, "completions": 1}}
			Net.import_character({"name": who, "class": "warrior", "deity": "fire", "level": 5, "race": "human", "stats": {"str": 10, "sta": 10, "agi": 5},
					"zone": "greenmoor", "position": [8.0 if who == "Alpha" else 4.0, 2, 20], "quests": qs})
		elif "--grove" in OS.get_cmdline_user_args():
			Net.import_character({"name": who, "class": "warrior", "deity": "light", "level": 5, "race": "human", "stats": {"str": 10, "sta": 10, "agi": 5},
					"zone": "the_grove", "position": [4.0 if who == "Alpha" else -4.0, 2, 30]})
		elif "--trade" in OS.get_cmdline_user_args():
			Net.import_character({"name": who, "class": "warrior", "deity": "fire", "level": 5, "coin": 800, "race": "human", "stats": {"str": 10, "sta": 10, "agi": 5},
					"inventory": ["gnoll_fang", "rusty_short_sword"] if who == "Alpha" else ["beetle_eye"], "equipment": {"primary": "rusty_short_sword"}})
		elif "--group" in OS.get_cmdline_user_args() and who in ["Alpha", "Bravo"]:
			Net.import_character({"name": who, "class": "warrior" if who == "Alpha" else "cleric", "deity": "fire",
					"level": 3 if who == "Alpha" else 5, "spells": ["kick", "taunt"] if who == "Alpha" else ["minor_healing", "circle_of_mending", "fire_bolt"],
					"equipment": {"primary": "rusty_short_sword"} if who == "Alpha" else {"primary": "worn_staff"}})
		elif who == "Petter":
			Net.import_character({"name": "Petter", "class": "magician", "deity": "fire", "level": 2, "spells": ["call_of_earth"], "equipment": {"primary": "worn_staff"}})
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
	elif "--grove" in OS.get_cmdline_user_args():
		await _grove_test(p)
	elif "--emotes" in OS.get_cmdline_user_args():
		await _emote_test(p)
	elif "--guild" in OS.get_cmdline_user_args():
		await _guild_test(p)
	elif "--share" in OS.get_cmdline_user_args():
		await _share_test(p)
	elif "--homecoming" in OS.get_cmdline_user_args():
		var first := (get_parent().zone as Zone).zone_id
		await _wait(6.0)
		print("[%s] homecoming: logged in to %s, now in %s at %s" % [who, first, (get_parent().zone as Zone).zone_id, p.global_position.snapped(Vector3.ONE)])
		await _shot("homecoming")
		get_tree().quit()
	elif "--swing" in OS.get_cmdline_user_args():
		# the swing timer reaches the client: attack something and watch it run down and restart
		var mob: Mob = null
		for m in World.get_mobs():
			if not m.dead and (mob == null or p.distance_to(m) < p.distance_to(mob)):
				mob = m
		if mob == null:
			print("[%s] swing: no monster here" % who)
		else:
			Input.action_press("move_forward")  # walk up to it (the server won't let a client jump)
			for k in 400:
				if p.distance_to(mob) < 2.5:
					break
				p.face_toward(mob.global_position)
				await get_tree().physics_frame
			Input.action_release("move_forward")
			await _wait(0.5)
			World.request_set_target(p.entity_id, mob.entity_id)
			World.request_toggle_attack(p.entity_id)
			var samples: Array = []
			for k in 40:
				await _wait(0.1)
				samples.append(snappedf(p.swing_timer, 0.1))
				if k == 12:
					await _shot("swing_bar")
			print("[%s] swing: delay %.1f s; timer over 4 s: %s" % [who, p.attack_delay, samples])
	elif "--trade" in OS.get_cmdline_user_args():
		await _trade_test(p)
	elif "--wake" in OS.get_cmdline_user_args():
		# into a zone that's gone to sleep on the server: its monsters must be there and moving
		await _wait(3.0)
		var mobs := World.get_mobs()
		var before := {}
		for m in mobs:
			before[m.entity_id] = m.global_position
		await _wait(8.0)
		var moved := 0
		for m in World.get_mobs():
			if before.has(m.entity_id) and m.global_position.distance_to(before[m.entity_id]) > 0.5:
				moved += 1
		print("[%s] wake: in %s; %d monsters here, %d moved in 8 s" % [who, World.zone.zone_id if World.zone else "-", mobs.size(), moved])
	elif "--stutter" in OS.get_cmdline_user_args():
		# run round the zone for 30 s online and log slow frames and any jump of our own position
		Input.action_press("move_forward")
		var t := 0.0
		var turn := 0.0
		var last := p.global_position
		var spikes := PackedStringArray()
		var jumps := PackedStringArray()
		var frames := 0
		while t < 30.0:
			var before := Time.get_ticks_usec()
			await get_tree().process_frame
			var ms := (Time.get_ticks_usec() - before) / 1000.0
			t += ms / 1000.0
			frames += 1
			turn += ms / 1000.0
			if turn > 3.0:
				turn = 0.0
				p.rotate_y(1.3)
			if ms > 25.0:
				spikes.append("%.1fs:%.0fms" % [t, ms])
			var moved := p.global_position.distance_to(last)
			if moved > 1.0:
				jumps.append("%.1fs:%.1fm" % [t, moved])
			last = p.global_position
		Input.action_release("move_forward")
		print("[%s] stutter: %d frames in %.0f s (%.0f fps); %d slow frames: %s; %d position jumps: %s" % [who, frames, t, frames / t, spikes.size(), ", ".join(spikes), jumps.size(), ", ".join(jumps)])
	elif who == "Petter":
		# a pet's swings must show on a client: summon, send it at a mob, sample the puppet's clip
		World.request_cast(p.entity_id, "call_of_earth")
		await _wait(6.0)
		var pet := World.get_object(p.pet_id) as Pet
		var mob: Mob = null
		for m in World.get_mobs():
			if not m.dead and m.level >= 3 and (mob == null or m.global_position.distance_to(p.global_position) < mob.global_position.distance_to(p.global_position)):
				mob = m
		print("[Petter] pet %s, nearest mob %s at %.1f m" % [pet.display_name if pet else "none", mob.display_name if mob else "none", mob.global_position.distance_to(p.global_position) if mob else -1.0])
		if pet != null and mob != null:
			World.request_set_target(p.entity_id, mob.entity_id)
			World.request_pet(p.entity_id, "attack")
			var clips := {}
			var mob_clips := {}
			for k in 300:
				await _wait(0.1)
				if pet.visual is CharacterModel:
					var c: String = (pet.visual as CharacterModel).anim.current_animation
					clips[c] = int(clips.get(c, 0)) + 1
				if is_instance_valid(mob) and mob.visual is CharacterModel:
					var mc: String = (mob.visual as CharacterModel).anim.current_animation
					mob_clips[mc] = int(mob_clips.get(mc, 0)) + 1
			print("[Petter] the pet's clips over 30 s on this client: %s; the mob's %s" % [clips, mob_clips])
	elif "--group" in OS.get_cmdline_user_args():
		await _group_test(p)
	elif "--chat" in OS.get_cmdline_user_args():
		await _wait(2.0)
		if who == "Alpha":
			for line in ["hello there", "/tell bravo psst, over here", "/ooc anyone want to group?", "/who all", "/lfg", "/random 20", "/tell nobody hi", "/bogus", "/afk back soon"]:
				World.request_chat(p.entity_id, line)
				await _wait(0.4)
			await _wait(3.0)
		else:
			await _wait(3.0)
			for line in ["/r got it", "/shout the whole zone hears this"]:
				World.request_chat(p.entity_id, line)
				await _wait(0.4)
			await _wait(2.0)
			for q in World.get_players():
				if q != p:
					print("[Bravo] Alpha's nameplate reads '%s'" % q.nameplate.text)
			World.request_chat(p.entity_id, "/tell alpha still there?")
			await _wait(1.0)
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
	elif who == "Zoner" and "--north" in OS.get_cmdline_user_args():
		# Greenmoor's north pass into Thornwood Vale, watching the height the whole way
		await _walk_to(p, Vector3(12, 0, 4))  # around the obelisk
		await _walk_to(p, Vector3(12, 0, -60))
		await _walk_to(p, Vector3(6, 0, -150))
		await _walk_to(p, Vector3(0, 0, -170))
		p.face_toward(Vector3(0, p.global_position.y, -300))
		Input.action_press("move_forward")  # run on through the zone line as a player would, while the server thinks
		for k in 60:
			print("[Zoner] t=%.2f zone %s pos %s on_floor %s" % [k * 0.25, World.zone.zone_id if World.zone != null else "-", p.global_position, p.is_on_floor()])
			if World.zone != null and World.zone.zone_id == "thornwood":
				Input.action_release("move_forward")
			await _wait(0.25)
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
## Two players trade: Alpha offers a gnoll fang and 250 copper, Bravo a beetle
## eye; both press Trade. Then a NO DROP item is refused, and a canceled trade
## gives everything back.
## Guilds and friends online: Alpha founds a guild at Emberhold's registrar
## and invites Bravo, who sees Alpha's tag and hears guild chat; Alpha
## befriends Bravo and hears when Bravo logs off.
## Sharing quests online: Alpha groups Bravo and shares four quests. Bravo
## takes one, is found ineligible for two (a quest line's later step, one
## already done), and declines the last.
func _share_test(p: Player) -> void:
	var other: Player = null
	for k in 60:
		for q in World.get_players():
			if q != p:
				other = q
		if other != null:
			break
		await _wait(0.25)
	if other == null:
		print("[%s] share: nobody else here" % who)
		return
	var heard: Array = []
	World.log_message.connect(func(t: String, _c: Color) -> void: heard.append(t))
	if who == "Alpha":
		World.request_chat(p.entity_id, "/invite Bravo")
		for k in 40:
			if p.group.size() > 1:
				break
			await _wait(0.25)
		for quest_id: String in ["fang_bounty", "trail_pack_hide", "rain_pack_needles", "trail_pack_cord"]:
			World.request_quest_share(p.entity_id, quest_id)
			await _wait(2.5)
		await _wait(2.0)
		print("[Alpha] share: heard %s" % [heard.filter(func(t: String) -> bool: return "Bravo" in t or "share" in t)])
	else:
		var offers: Array = []
		World.quest_offered.connect(func(f: String, q: String) -> void:
			if f != "":
				offers.append(q))
		await _wait(1.5)
		World.request_chat(p.entity_id, "/accept")
		for k in 60:
			if offers.size() >= 1:
				break
			await _wait(0.25)
		await _wait(0.5)
		await _shot("quest_share_offer")
		World.request_quest_share_answer(p.entity_id, true)
		for k in 60:
			if offers.size() >= 2:
				break
			await _wait(0.25)
		World.request_quest_share_answer(p.entity_id, false)
		await _wait(3.0)
		print("[Bravo] share: offered %s; my quests now %s; heard %s" % [offers, p.quests, heard.filter(func(t: String) -> bool: return "share" in t or "decline" in t or "given by" in t)])
		get_tree().quit()


## Deleting a character from the character screen (no world): two made, a
## wrong name typed is refused, someone else's is refused, the right one goes,
## and its name is free again.
func _delete_test() -> void:
	var heard: Array = []
	Net.server_message.connect(func(t: String, _e: bool) -> void: heard.append(t))
	var names := func() -> Array: return _list.map(func(c: Dictionary) -> String: return str(c["name"]))
	for n: String in ["Keeper", "Goner"]:
		if not n in names.call():
			Net.create_character(n, "warrior", "fire", {}, "human")
			await _wait(1.0)
	print("[%s] delete: made %s" % [who, names.call()])
	var screen := LoginScreen.new()
	screen.address = "127.0.0.1:%d" % port
	screen.account = who.to_lower()
	screen.logged_in = true
	get_parent().add_child(screen)
	await _wait(0.3)
	screen._on_characters(_list)
	screen._ask_delete("Goner")
	screen._delete_edit.text = "Gone"
	screen._delete_edit.text_changed.emit("Gone")
	print("[%s] delete: typed 'Gone' -> button enabled %s" % [who, not screen._delete_button.disabled])
	screen._delete_edit.text = "goner"
	screen._delete_edit.text_changed.emit("goner")
	print("[%s] delete: typed 'goner' -> button enabled %s" % [who, not screen._delete_button.disabled])
	await _wait(0.3)
	await _shot("delete_confirm")
	Net.delete_character("Goner", "Gone")  # the server checks the typing too
	await _wait(1.0)
	Net.delete_character("Stranger", "Stranger")  # not ours
	await _wait(1.0)
	screen._confirm_delete()
	await _wait(1.5)
	print("[%s] delete: after -> %s; heard %s" % [who, names.call(), heard])
	await _shot("delete_after")
	Net.create_character("Goner", "cleric", "light", {}, "human")  # the name is free again
	await _wait(1.0)
	print("[%s] delete: made Goner again -> %s" % [who, names.call()])


func _guild_test(p: Player) -> void:
	var other: Player = null
	for k in 60:
		for q in World.get_players():
			if q != p:
				other = q
		if other != null:
			break
		await _wait(0.25)
	if other == null:
		print("[%s] guild: nobody else here" % who)
		return
	var heard: Array = []
	World.log_message.connect(func(t: String, _c: Color) -> void: heard.append(t))
	if who == "Alpha":
		World.request_chat(p.entity_id, "/guildcreate Test Company")
		await _wait(1.0)
		World.request_chat(p.entity_id, "/friend Bravo")
		World.request_chat(p.entity_id, "/guildinvite Bravo")
		for k in 40:  # until Bravo has joined
			if heard.any(func(t: String) -> bool: return "has joined the guild" in t):
				break
			await _wait(0.25)
		World.request_chat(p.entity_id, "/gu Welcome aboard!")
		await _wait(12.0)
		print("[Alpha] guild: I am %s of <%s>; heard %s" % [p.guild_rank, p.guild_name, heard.filter(func(t: String) -> bool: return "Bravo" in t)])
	else:
		await _wait(3.0)
		World.request_chat(p.entity_id, "/guildaccept")
		await _wait(6.0)
		print("[Bravo] guild: I am %s of <%s>; Alpha's tag here reads %s; heard %s" % [p.guild_rank, p.guild_name,
				other._guild_label.text if other._guild_label != null else "nothing", heard.filter(func(t: String) -> bool: return "guild" in t or "Welcome" in t)])
		await _shot("guild_tag")
		get_tree().quit()  # logs off: Alpha's friend alert


## Emotes online: Alpha waves at Bravo; Bravo reads the line and sees
## Alpha's character play the wave.
func _emote_test(p: Player) -> void:
	var other: Player = null
	for k in 60:
		for q in World.get_players():
			if q != p:
				other = q
		if other != null:
			break
		await _wait(0.25)
	if other == null:
		print("[%s] emotes: nobody else here" % who)
		return
	if who == "Alpha":
		p.global_position = other.global_position + Vector3(3, 0, 0)
		await _wait(1.5)
		World.request_set_target(p.entity_id, other.entity_id)
		await _wait(0.5)
		World.request_chat(p.entity_id, "/wave")
		await _wait(6.0)
	else:
		var heard: Array = []
		World.log_message.connect(func(t: String, _c: Color) -> void: heard.append(t))
		var played := ""
		for k in 60:
			var m := other.visual as CharacterModel
			if m != null and m.anim.current_animation.begins_with("Emote_"):
				played = m.anim.current_animation
				break
			await _wait(0.1)
		await _shot("emote_seen")
		print("[Bravo] emotes: heard %s; Alpha played %s" % [heard.filter(func(t: String) -> bool: return "Alpha" in t), played if played != "" else "nothing"])


## The Grove online (run with <data>/admins.json = ["alpha"]): Alpha earns the
## Dawn-Tusk; Bravo sees nothing until grouped with Alpha, and loses him again
## on leaving the group.
func _grove_test(p: Player) -> void:
	var other: Player = null
	for k in 60:
		for q in World.get_players():
			if q != p:
				other = q
		if other != null:
			break
		await _wait(0.25)
	var gods := func() -> Array:
		var out: Array = []
		for obj: Variant in World.objects.values():
			if obj is Npc and (obj as Npc).grove_deity != "":
				out.append((obj as Npc).npc_id)
		out.sort()
		return out
	print("[%s] grove: in %s, sees %s; gods here %s" % [who, World.zone.zone_id if World.zone else "-", other.display_name if other else "nobody", gods.call()])
	if who == "Alpha":
		World.request_chat(p.entity_id, "/grove unlock light")
		await _wait(3.0)
		print("[Alpha] grove: unlocked light -> gods here %s" % [gods.call()])
		World.request_chat(p.entity_id, "/invite Bravo")
		await _wait(12.0)
		print("[Alpha] grove: end -> gods here %s" % [gods.call()])
	else:
		await _wait(3.0)
		print("[Bravo] grove: Alpha unlocked light, not grouped -> gods here %s" % [gods.call()])
		await _wait(1.5)
		World.request_chat(p.entity_id, "/accept")
		await _wait(3.0)
		print("[Bravo] grove: grouped with Alpha -> gods here %s" % [gods.call()])
		await _shot("grove_grouped")
		World.request_chat(p.entity_id, "/disband")
		await _wait(3.0)
		print("[Bravo] grove: left the group -> gods here %s" % [gods.call()])


func _trade_test(p: Player) -> void:
	var other: Player = null
	for k in 40:
		for q in World.get_players():
			if q != p:
				other = q
		if other != null:
			break
		await _wait(0.25)
	print("[%s] trade: sees %s; pack %s, coin %d" % [who, other.display_name if other else "nobody", p.pack.item_ids(), p.coin])
	if other == null:
		return
	var place_of := func(item: String) -> String:
		for place: String in p.pack.places():
			if str(p.pack.get_at(place).get("item", "")) == item:
				return place
		return ""
	if who == "Alpha":
		p.global_position = other.global_position + Vector3(2, 0, 0)
		await _wait(1.0)
		World.request_set_target(p.entity_id, other.entity_id)
		World.request_interact(p.entity_id)  # G on a player: a trade
		await _wait(1.0)
		print("[Alpha] trade open with %d" % p.trade_partner_id)
		World.request_trade_add(p.entity_id, place_of.call("gnoll_fang"))
		World.request_trade_coin(p.entity_id, 250)
		World.request_trade_add(p.entity_id, place_of.call("homeward_stone"))  # NO DROP: refused
		await _wait(3.0)
		print("[Alpha] sees Bravo offer %s, accepted %s" % [p.partner_offer.map(func(e: Dictionary) -> String: return e["item"]), p.partner_accept])
		await _shot("trade_window")
		World.request_trade_give(p.entity_id)
		await _wait(2.0)
		print("[Alpha] after the trade: pack %s, coin %d, trading %s" % [p.pack.item_ids(), p.coin, p.trade_partner_id >= 0])
		# a trade that Bravo cancels
		World.request_interact(p.entity_id)
		await _wait(1.0)
		World.request_trade_add(p.entity_id, place_of.call("rusty_short_sword"))
		await _wait(3.0)
		print("[Alpha] after Bravo canceled: pack %s, trading %s" % [p.pack.item_ids(), p.trade_partner_id >= 0])
	else:
		for k in 40:
			if p.trade_partner_id >= 0:
				break
			await _wait(0.25)
		print("[Bravo] a trade opened: %s" % (p.trade_partner_id >= 0))
		World.request_trade_add(p.entity_id, place_of.call("beetle_eye"))
		await _wait(1.0)
		World.request_trade_give(p.entity_id)  # Trade
		await _wait(3.5)
		print("[Bravo] after the trade: pack %s, coin %d" % [p.pack.item_ids(), p.coin])
		for k in 40:
			if p.trade_partner_id >= 0:
				break
			await _wait(0.25)
		await _wait(1.5)
		print("[Bravo] Alpha offers %s; canceling" % [p.partner_offer.map(func(e: Dictionary) -> String: return e["item"])])
		World.request_trade_cancel(p.entity_id)
		await _wait(3.0)


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
