extends Node
## Replays a title-screen path and reports what's in the tree afterwards:
##   godot --path . -- --flowtest
## Connect to an unreachable server, go Back, Continue offline in Emberhold,
## (double-clicked), walk out through the gate to Greenmoor, then count zones
## and HUDs. There should be one of each at every step.


func _ready() -> void:
	_run()


func _run() -> void:
	var main := get_parent()
	await _wait(0.5)
	var title := _find(main, "CharCreate") as CharCreate
	title.server_address = "no-such-host.invalid:7787"
	title.connect_pressed.emit()
	await _wait(2.5)
	var login := _find(main, "LoginScreen") as LoginScreen
	print("flow: login screen up=%s" % [login != null])
	login.back.emit()
	await _wait(0.5)
	title = _find(main, "CharCreate") as CharCreate
	print("flow: back at title=%s; titles in tree: %d" % [title != null, _all(main, "CharCreate").size()])
	var save := {"name": "Flower", "class": "warrior", "deity": "fire", "zone": "emberhold", "position": [0.0, 1.0, -80.0]}
	title.confirmed.emit(save)
	title.confirmed.emit(save)  # a double-click: both clicks land before the title is freed
	await _wait(2.0)
	_report(main, "in Emberhold")
	var p := World.local_player
	for k in 600:
		if World.zone != null and World.zone.zone_id == "greenmoor":
			break
		p.global_position += Vector3(0, 0, -6.5 * get_physics_process_delta_time())
		await get_tree().physics_frame
	await _wait(2.0)
	_report(main, "after zoning to Greenmoor")
	# Reloaded while online (--resume with mode "online"), Back from the login,
	# Continue offline: no title screen may be left over the world.
	main._teardown_world()
	var title2 := main._show_title({"name": "Flower", "class": "warrior", "deity": "fire", "zone": "greenmoor", "position": [0.0, 1.0, 0.0]}) as CharCreate
	main._resume_online(title2)
	await _wait(2.0)
	var login2 := _find(main, "LoginScreen") as LoginScreen
	login2.back.emit()
	await _wait(0.5)
	var title3 := _find(main, "CharCreate") as CharCreate
	title3.confirmed.emit({"name": "Flower", "class": "warrior", "deity": "fire", "zone": "greenmoor", "position": [0.0, 1.0, 0.0]})
	await _wait(2.0)
	print("flow: resumed online, back, continue offline: titles left in the tree %d, in the world %s" % [
			_all(main, "CharCreate").filter(func(n: Node) -> bool: return not n.is_queued_for_deletion()).size(), World.local_player != null])
	get_tree().quit()


func _report(main: Node, when: String) -> void:
	var zones := get_tree().root.find_children("*", "Zone", true, false)
	print("flow: %s: zones %s, HUDs %d, players %d" % [when, zones.map(func(z: Zone) -> String: return z.zone_id + (" (freeing)" if z.is_queued_for_deletion() else "")),
			_all(main, "Hud").size(), World.get_players().size()])


func _find(root: Node, cls: String) -> Node:
	var all := _all(root, cls)
	return all[0] if not all.is_empty() else null


func _all(root: Node, cls: String) -> Array:
	return root.get_children().filter(func(n: Node) -> bool: return n.get_class() == cls or (n.get_script() != null and n.get_script().get_global_name() == cls))


func _wait(seconds: float) -> void:
	await get_tree().create_timer(seconds).timeout
