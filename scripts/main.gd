extends Node
## Entry point. Three ways to run:
##   offline (default)  title screen, then the zone, player and HUD, all here.
##   client             the title screen's Server box names a server; the world
##                      is a mirror of the server's and our player is sent up.
##   --server           dedicated and headless: loads the starting zone and
##                      waits for players (--port=7777, --zone=<id>).
## Characters are saved to user://character.json on the player's own machine,
## including when they play on a server (the server sends saves back).

const SAVE_PATH := "user://character.json"
const AUTOTEST_SAVE_PATH := "user://autotest_character.json"
const SETTINGS_PATH := "user://settings.json"
const AUTOSAVE_SECONDS := 30.0

var save_path := SAVE_PATH
var zone: Zone
var player: Player
var hud: Hud
var _save_timer := 0.0
var _corpses_by_zone: Dictionary = {}  # zone id -> saved player corpses left there
var _changing_zone := false
var _server_zones: Dictionary = {}  # server: zone id -> Zone, every zone that is running
var _start_zone := ""  # server: where new characters (and unknown zones) land


func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	for a in args:
		if a.begins_with("--lineup="):
			add_child(load("res://scripts/dev/lineup.gd").new())
			return
	if "--server" in args:
		_start_server(args)
		return
	var autotest := "--autotest" in args
	if autotest:
		save_path = AUTOTEST_SAVE_PATH
	for a in args:
		if a.begins_with("--nettest="):
			save_path = "user://nettest_%s.json" % a.substr(10)
	if not autotest and not save_path.begins_with("user://nettest_") and not OS.has_feature("template"):
		var reloader: Node = load("res://scripts/dev/reloader.gd").new()
		reloader.save_game = func() -> bool:
			_save()
			return player != null
		add_child(reloader)
	Net.left_server.connect(_on_left_server)
	Net.camp_done.connect(_on_client_camped)
	Net.zone_moved.connect(_on_client_zone_moved)
	Net.joined.connect(_start_client)
	var save := {} if autotest else _load_save()
	var title := _show_title(save)
	if autotest:
		add_child(load("res://scripts/dev/autotest.gd").new())
	elif save_path.begins_with("user://nettest_"):
		add_child(load("res://scripts/dev/nettest.gd").new())
	elif "--resume" in args and str(_settings().get("mode", "")) == "online":
		_show_login()  # reloaded after an update: back to the server's login
	elif "--resume" in args and GameData.deities.has(str(save.get("deity", ""))):
		_play(save, title)  # reloaded after an update: straight back in (older saves stop to pick a deity)


func _show_title(save: Dictionary, status := "", is_error := false) -> CharCreate:
	var title := CharCreate.new()
	title.setup(save)
	title.server_address = str(_settings().get("server", ""))
	title.confirmed.connect(func(s: Dictionary) -> void: _play(s, title))
	title.connect_pressed.connect(func() -> void:
		var settings := _settings()
		settings["server"] = title.server_address
		_write_json(SETTINGS_PATH, settings)
		title.queue_free()
		_show_login())
	add_child(title)
	title.set_status(status, is_error)
	return title


## The title screen said go, offline.
func _play(save: Dictionary, title: CharCreate) -> void:
	var settings := _settings()
	settings["mode"] = "offline"
	_write_json(SETTINGS_PATH, settings)
	_start_game(save, title)


## Playing online: connect and log in (or, after camping, straight to
## character select on the connection we already have).
func _show_login(logged_in := false) -> void:
	var settings := _settings()
	settings["mode"] = "online"
	_write_json(SETTINGS_PATH, settings)
	var login := LoginScreen.new()
	login.address = str(settings.get("server", ""))
	login.account = str(settings.get("account", ""))
	login.offline_save = _load_save()
	login.logged_in = logged_in
	login.back.connect(func() -> void:
		login.queue_free()
		var s := _settings()
		s["mode"] = "offline"
		_write_json(SETTINGS_PATH, s)
		_show_title(_load_save()))
	login.tree_exiting.connect(func() -> void:
		if login.account != "":
			var s := _settings()
			s["account"] = login.account
			_write_json(SETTINGS_PATH, s))
	add_child(login)


func _start_game(save: Dictionary, title: CharCreate) -> void:
	title.queue_free()
	_corpses_by_zone = (save.get("corpses_by_zone", {}) as Dictionary).duplicate(true)
	var zone_id := str(save.get("zone", World.cfg("starting_zone", "greenmoor")))
	if save.has("corpses"):  # older saves kept one list, for the zone they were in
		_corpses_by_zone[zone_id] = save["corpses"]

	player = Player.new()
	player.from_save(save)
	var pos := Vector3.INF
	if save.has("position"):
		var a: Array = save["position"]
		pos = Vector3(a[0], float(a[1]) + 0.5, a[2])
	_enter_zone(zone_id, pos)
	zone.restore_corpses(_corpses_by_zone.get(zone_id, []))
	_start_hud()
	if not World.zone_change.is_connected(_on_zone_change):
		World.zone_change.connect(_on_zone_change)
		World.camped.connect(_on_camped)
	_save()


func _start_hud() -> void:
	hud = Hud.new()
	add_child(hud)
	hud.bind_player(player)
	var marker := TargetMarker.new()
	marker.player = player
	add_child(marker)
	hud.show_banner("Entering %s" % zone.zone_name)
	World.say(player, "Welcome to %s, %s. Click the gear (top right) or press H for controls." % [zone.zone_name, player.display_name])


## Builds a zone and puts the player in it: at `pos`, or at its bind point.
func _enter_zone(zone_id: String, pos: Vector3, face := Vector2.INF) -> void:
	zone = Zone.new()
	add_child(zone)
	zone.load_zone(zone_id)
	if pos == Vector3.INF:
		pos = zone.bind_point + Vector3.UP
	zone.add_player(player, pos)
	if face != Vector2.INF:
		var d := face - Vector2(pos.x, pos.z)
		player.rotation.y = atan2(-d.x, -d.y)


## Leaves the world (offline camp) and goes back to the character screen.
func _leave_world(status := "", is_error := false) -> void:
	_teardown_world()
	_show_title(_load_save(), status, is_error)


func _teardown_world() -> void:
	for node: Node in [hud, zone]:
		if node != null:
			node.queue_free()
	for child in get_children():
		if child is TargetMarker:
			child.queue_free()
	if player != null and player.get_parent() != null:
		player.get_parent().remove_child(player)
	if player != null:
		player.queue_free()
	player = null
	zone = null
	hud = null
	World.local_player = null
	World.zone = null


## Camping finished: save, leave the world, and go back to the character screen.
func _on_camped(p: Player) -> void:
	if p != player:
		return
	_save()
	_leave_world()


func _on_zone_change(p: Player, zone_id: String, arrive: Vector2, face: Vector2) -> void:
	if p != player or _changing_zone:
		return
	_changing_zone = true
	hud.show_banner("Loading...")
	await get_tree().process_frame
	await get_tree().process_frame
	_corpses_by_zone[zone.zone_id] = zone.player_corpses_for(player.display_name)
	zone.remove_child(player)
	zone.queue_free()
	World.zone = null
	await get_tree().process_frame
	_enter_zone(zone_id, Vector3(arrive.x, 0, arrive.y), face)
	zone.restore_corpses(_corpses_by_zone.get(zone_id, []))
	player.global_position = zone.ground(arrive.x, arrive.y) + Vector3.UP
	player.velocity = Vector3.ZERO
	hud.show_banner("Entering %s" % zone.zone_name)
	World.say(player, "You have entered %s." % zone.zone_name)
	_changing_zone = false
	_save()


# --- client ------------------------------------------------------------------

## The server let us in: build its zone (scenery only; it sends the rest) and
## our player, under the id the server gave it.
func _start_client(pid: int, zone_id: String, pos: Vector3, rot: float, save: Dictionary) -> void:
	for child in get_children():
		if child is LoginScreen or child is CharCreate:
			child.queue_free()
	player = Player.new()
	player.from_save(save)
	player.entity_id = pid
	zone = Zone.new()
	add_child(zone)
	zone.load_zone(zone_id)
	zone.add_player(player, pos)
	player.rotation.y = rot
	_start_hud()
	World.say(player, "You are playing on %s." % _settings().get("server", "the server"), World.C_SYSTEM)


func _on_client_zone_moved(zone_id: String, pos: Vector3) -> void:
	if player == null:
		return
	_changing_zone = true
	hud.show_banner("Loading...")
	zone.remove_child(player)
	zone.queue_free()  # every mirror goes with it; the server sends the new zone's
	World.zone = null
	await get_tree().process_frame
	zone = Zone.new()
	add_child(zone)
	zone.load_zone(zone_id)
	zone.add_player(player, pos)
	player.velocity = Vector3.ZERO
	hud.show_banner("Entering %s" % zone.zone_name)
	_changing_zone = false


## Camped out on a server: back to character select, still logged in.
func _on_client_camped() -> void:
	_teardown_world()
	_show_login(true)


func _on_left_server(reason: String) -> void:
	if player == null:
		return  # the login screen shows it
	_teardown_world()
	_show_title(_load_save(), reason, true)


# --- dedicated server ----------------------------------------------------------

func _start_server(args: PackedStringArray) -> void:
	var port := Net.DEFAULT_PORT
	var zone_id := str(World.cfg("starting_zone", "greenmoor"))
	for a in args:
		if a.begins_with("--port="):
			port = int(a.substr(7))
		elif a.begins_with("--zone="):
			zone_id = a.substr(7)
	if "--dev-loot" in args:  # testing: every mob drops everything it can
		for mob: Dictionary in GameData.mobs.values():
			for entry: Dictionary in mob.get("loot", []) + mob.get("gear", []):
				entry["chance"] = 1.0
	var data_dir := "user://server"
	for a in args:
		if a.begins_with("--data="):
			data_dir = a.substr(7)
	_start_zone = zone_id
	_server_zone(zone_id)
	Net.accounts = AccountStore.new(data_dir)
	Net.start_zone = zone_id
	Net.make_player = _make_remote_player
	Net.save_of = _server_save_of
	Net.remove_player = _on_remote_left
	print("Accounts and characters are kept in %s" % ProjectSettings.globalize_path(data_dir))
	World.zone_change.connect(_on_server_zone_change)
	World.camped.connect(_on_server_camped)
	var err := Net.host(port)
	if err != OK:
		push_error("Could not open UDP port %d: %s" % [port, error_string(err)])
		get_tree().quit(1)


## A server keeps every zone someone has visited running, each inside its own
## SubViewport world so their physics (and overlapping coordinates) never meet.
func _server_zone(zone_id: String) -> Zone:
	if _server_zones.has(zone_id):
		return _server_zones[zone_id]
	var holder := SubViewport.new()
	holder.name = "zone_" + zone_id
	holder.own_world_3d = true
	holder.size = Vector2i(2, 2)
	holder.render_target_update_mode = SubViewport.UPDATE_DISABLED
	add_child(holder)
	var z := Zone.new()
	holder.add_child(z)
	z.load_zone(zone_id)
	_server_zones[zone_id] = z
	print("zone up: %s" % zone_id)
	return z


## A client joined with this character: put it in the world.
func _make_remote_player(_peer: int, save: Dictionary) -> Player:
	var name := str(save.get("name", ""))
	if RegEx.create_from_string("^[A-Za-z]{3,15}$").search(name) == null \
			or not GameData.classes.has(str(save.get("class", ""))):
		return null
	var p := Player.new()
	p.is_local = false
	p.from_save(save)
	var zone_id := str(save.get("zone", _start_zone))
	if not FileAccess.file_exists("res://data/zones/%s.json" % zone_id):
		zone_id = _start_zone
	var z := _server_zone(zone_id)
	var pos := z.bind_point + Vector3.UP
	if str(save.get("zone", "")) == zone_id and save.has("position"):
		var a: Array = save["position"]
		pos = Vector3(a[0], float(a[1]) + 0.5, a[2])
	z.add_player(p, pos)
	# their corpses come back wherever they fell, unless those are still lying there
	var corpses: Dictionary = save.get("corpses_by_zone", {})
	for cz: String in corpses:
		if (corpses[cz] as Array).is_empty() or not FileAccess.file_exists("res://data/zones/%s.json" % cz):
			continue
		var holder := _server_zone(cz)
		if holder.player_corpses_for(name).is_empty():
			holder.restore_corpses(corpses[cz])
	World.say(p, "Welcome to %s, %s." % [z.zone_name, name])
	return p


func _server_save_of(p: Player) -> Dictionary:
	var z := World.zone_of(p)
	var d := p.to_save()
	if p.dead:
		d["position"] = [z.bind_point.x, z.bind_point.y, z.bind_point.z]
	d["zone"] = z.zone_id
	var corpses := {}
	for zone_id: String in _server_zones:
		var list: Array = (_server_zones[zone_id] as Zone).player_corpses_for(p.display_name)
		if not list.is_empty():
			corpses[zone_id] = list
	d["corpses_by_zone"] = corpses
	return d


func _on_remote_left(p: Player) -> void:
	World.request_trade_cancel(p.entity_id)
	p.queue_free()


func _on_server_camped(p: Player) -> void:
	Net.camped_out(p)


## One player walked through a zone line: only they move.
func _on_server_zone_change(p: Player, zone_id: String, arrive: Vector2, face: Vector2) -> void:
	if p.has_meta("zoning"):
		return
	p.set_meta("zoning", true)
	await get_tree().physics_frame  # not in the middle of the trigger's physics callback
	if not is_instance_valid(p):
		return
	var from := World.zone_of(p)
	var to := _server_zone(zone_id)
	from.remove_child(p)
	to.add_player(p, to.ground(arrive.x, arrive.y) + Vector3.UP)
	var d := face - arrive
	p.rotation.y = atan2(-d.x, -d.y)
	Net.send_zone(p, zone_id)
	World.say(p, "You have entered %s." % to.zone_name)
	p.remove_meta("zoning")
	Net.save_player(p)


# --- saving ------------------------------------------------------------------

func _process(delta: float) -> void:
	if player == null or _changing_zone:
		return
	_save_timer += delta
	if _save_timer >= AUTOSAVE_SECONDS:
		_save_timer = 0.0
		_save()


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST:
		_save()


func _save() -> void:
	if Net.mode == "client":
		return  # online characters live on the server
	if player == null or zone == null or _changing_zone:
		return
	var d := player.to_save()
	if player.dead:
		d["position"] = [zone.bind_point.x, zone.bind_point.y, zone.bind_point.z]
	d["zone"] = zone.zone_id
	_corpses_by_zone[zone.zone_id] = zone.player_corpses_for(player.display_name)
	d["corpses_by_zone"] = _corpses_by_zone
	_write_json(save_path, d)


func _load_save() -> Dictionary:
	return _read_json(save_path)


func _settings() -> Dictionary:
	return _read_json(SETTINGS_PATH)


func _read_json(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	return parsed if typeof(parsed) == TYPE_DICTIONARY else {}


func _write_json(path: String, d: Dictionary) -> void:
	var f := FileAccess.open(path, FileAccess.WRITE)
	if f != null:
		f.store_string(JSON.stringify(d, "  "))
