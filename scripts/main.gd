extends Node
## Entry point: title screen, then load the zone, player and HUD.
## Saves the character to user://character.json periodically and on quit.

const SAVE_PATH := "user://character.json"
const AUTOTEST_SAVE_PATH := "user://autotest_character.json"
const AUTOSAVE_SECONDS := 30.0

var save_path := SAVE_PATH
var zone: Zone
var player: Player
var hud: Hud
var _save_timer := 0.0
var _corpses_by_zone: Dictionary = {}  # zone id -> saved player corpses left there
var _changing_zone := false


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--lineup="):
			add_child(load("res://scripts/dev/lineup.gd").new())
			return
	var autotest := "--autotest" in OS.get_cmdline_user_args()
	if autotest:
		save_path = AUTOTEST_SAVE_PATH
	var title := CharCreate.new()
	title.setup({} if autotest else _load_save())
	title.confirmed.connect(_start_game.bind(title))
	add_child(title)
	if autotest:
		add_child(load("res://scripts/dev/autotest.gd").new())


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

	hud = Hud.new()
	add_child(hud)
	hud.bind_player(player)
	var marker := TargetMarker.new()
	marker.player = player
	add_child(marker)
	hud.show_banner("Entering %s" % zone.zone_name)
	World.say(player, "Welcome to %s, %s. Press H for controls." % [zone.zone_name, player.display_name])
	World.zone_change.connect(_on_zone_change)
	_save()


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
	zone.restore_corpses(_corpses_by_zone.get(zone_id, []))


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
	player.global_position = zone.ground(arrive.x, arrive.y) + Vector3.UP
	player.velocity = Vector3.ZERO
	hud.show_banner("Entering %s" % zone.zone_name)
	World.say(player, "You have entered %s." % zone.zone_name)
	_changing_zone = false
	_save()


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
	if player == null or zone == null or _changing_zone:
		return
	var d := player.to_save()
	if player.dead:
		d["position"] = [zone.bind_point.x, zone.bind_point.y, zone.bind_point.z]
	d["zone"] = zone.zone_id
	_corpses_by_zone[zone.zone_id] = zone.player_corpses_for(player.display_name)
	d["corpses_by_zone"] = _corpses_by_zone
	var f := FileAccess.open(save_path, FileAccess.WRITE)
	if f != null:
		f.store_string(JSON.stringify(d, "  "))


func _load_save() -> Dictionary:
	if not FileAccess.file_exists(save_path):
		return {}
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(save_path))
	return parsed if typeof(parsed) == TYPE_DICTIONARY else {}
