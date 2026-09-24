extends Node
## Two-player network check, run against a local dedicated server:
##   godot --headless --path . -- --server --port=7788 --zone=greenmoor
##   godot --path . -- --nettest=Alpha --port=7788 --shots=<dir>
##   godot --path . -- --nettest=Bravo --port=7788 --shots=<dir>
## Alpha fights a mob and loots it; Bravo watches; both then camp out.

var who := ""
var port := Net.DEFAULT_PORT
var shots_dir := ""


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
	var title: CharCreate = null
	for c in main.get_children():
		if c is CharCreate:
			title = c
	title.server_address = "127.0.0.1:%d" % port
	var cls := "warrior" if who == "Alpha" else "cleric"
	main._play({"name": who, "class": cls, "deity": "fire", "zone": "greenmoor", "position": [4.0 if who == "Alpha" else -4.0, 1.0, 10.0]}, title)
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

	if who == "Sprinter":
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
		await _shot("net_zoner_emberhold")
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
		print("[Alpha] inventory now %s coin %d" % [p.inventory, p.coin])
	else:
		await _wait(6.0)
		var alpha: Player = null
		for q in World.get_players():
			if q != p:
				alpha = q
		print("[Bravo] sees Alpha: %s at %s" % [alpha != null, alpha.global_position if alpha != null else "-"])
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
	print("[%s] camped: back at title = %s, save on disk level %s" % [who, World.local_player == null, main._load_save().get("level", "?")])
	print("NETTEST DONE %s" % who)
	get_tree().quit()


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
