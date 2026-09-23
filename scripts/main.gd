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
	zone = Zone.new()
	add_child(zone)
	zone.load_zone(str(save.get("zone", World.cfg("starting_zone", "greenmoor"))))

	player = Player.new()
	player.from_save(save)
	var pos := zone.bind_point + Vector3.UP
	if save.has("position"):
		var a: Array = save["position"]
		pos = Vector3(a[0], float(a[1]) + 0.5, a[2])
	zone.add_player(player, pos)
	zone.restore_corpses(save.get("corpses", []))

	hud = Hud.new()
	add_child(hud)
	hud.bind_player(player)
	hud.show_banner("Entering %s" % zone.zone_name)
	World.say(player, "Welcome to %s, %s. Press H for controls." % [zone.zone_name, player.display_name])
	_save()


func _process(delta: float) -> void:
	if player == null:
		return
	_save_timer += delta
	if _save_timer >= AUTOSAVE_SECONDS:
		_save_timer = 0.0
		_save()


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST:
		_save()


func _save() -> void:
	if player == null:
		return
	var d := player.to_save()
	if player.dead:
		d["position"] = [zone.bind_point.x, zone.bind_point.y, zone.bind_point.z]
	d["zone"] = zone.zone_id
	d["corpses"] = zone.player_corpses_for(player.display_name)
	var f := FileAccess.open(save_path, FileAccess.WRITE)
	if f != null:
		f.store_string(JSON.stringify(d, "  "))


func _load_save() -> Dictionary:
	if not FileAccess.file_exists(save_path):
		return {}
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(save_path))
	return parsed if typeof(parsed) == TYPE_DICTIONARY else {}
