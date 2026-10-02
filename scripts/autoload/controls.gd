extends Node
## Registers default key bindings at startup so project.godot stays readable,
## and holds the few settings that change how input itself behaves.

const SETTINGS_PATH := "user://settings.json"

const BINDINGS := {
	"move_forward": [KEY_W, KEY_UP],
	"move_back": [KEY_S, KEY_DOWN],
	"move_left": [KEY_A],
	"move_right": [KEY_D],
	"turn_left": [KEY_LEFT],
	"turn_right": [KEY_RIGHT],
	"free_cursor": [KEY_ALT],
	"sprint": [KEY_SHIFT],
	"jump": [KEY_SPACE],
	"auto_attack": [KEY_Q],
	"ranged": [KEY_R],
	"target_next": [KEY_TAB],
	"target_interact": [KEY_T],
	"target_self": [KEY_F1],
	"target_group_1": [KEY_F2],
	"target_group_2": [KEY_F3],
	"target_group_3": [KEY_F4],
	"target_group_4": [KEY_F5],
	"target_group_5": [KEY_F6],
	"settings": [KEY_O],
	"map": [KEY_M],
	"settings_music_down": [KEY_BRACKETLEFT],
	"settings_music_up": [KEY_BRACKETRIGHT],
	"consider": [KEY_C],
	"sit": [KEY_X],
	"zoom_in": [KEY_EQUAL],  # the mouse wheel does it too
	"zoom_out": [KEY_MINUS],
	"look_up": [KEY_PAGEUP],  # as in EQ; with the mouse, hold the right button and drag
	"look_down": [KEY_PAGEDOWN],
	"look_center": [KEY_END],
	"first_person": [KEY_HOME],
	"loot": [KEY_L],
	"hail": [KEY_E],
	"trade": [KEY_G],
	"inventory": [KEY_I],
	"bags": [KEY_B],
	"skills": [KEY_K],
	"help": [KEY_H],
	"reload": [KEY_F9],  # F2-F6 target group members, as in EQ
	"cancel": [KEY_ESCAPE],
	"hotbar_1": [KEY_1],
	"hotbar_2": [KEY_2],
	"hotbar_3": [KEY_3],
	"hotbar_4": [KEY_4],
	"hotbar_5": [KEY_5],
	"hotbar_6": [KEY_6],
	"hotbar_7": [KEY_7],
	"hotbar_8": [KEY_8],
	"hotbar_9": [KEY_9],
	"hotbar_10": [KEY_0],
	"spellbook": [KEY_P],
	"friends": [KEY_F],
	"guild": [KEY_U],
	"chat_window": [KEY_Y],
	"journal": [KEY_J],
}

## Ctrl+M: mouselook on or off, anywhere.
const CTRL_BINDINGS := {"settings_mouse_look": KEY_M}

## The second hotbar: Ctrl and the same number keys (under your little finger,
## and no clash with Shift's sprint), or Shift.
const SHIFT_BINDINGS := {
	"hotbar2_1": KEY_1, "hotbar2_2": KEY_2, "hotbar2_3": KEY_3, "hotbar2_4": KEY_4, "hotbar2_5": KEY_5,
	"hotbar2_6": KEY_6, "hotbar2_7": KEY_7, "hotbar2_8": KEY_8, "hotbar2_9": KEY_9, "hotbar2_10": KEY_0,
}


## Off puts the game back on the keyboard: the cursor stays out, A/D turn rather
## than strafe, and you click to target instead of aiming. Saved per machine,
## like the bindings, not per character.
var mouse_look := true


## Music loudness, 0..1 (0 is off). Saved per machine.
var music_volume := 0.25
## Sound effects' loudness, 0..1 (0 is off). Saved per machine.
var sfx_volume := 0.7
## Tells, group and guild lines in the main chat as well as the chat window (Y). Saved per machine.
var social_in_main := true

## Hotbars locked: no dragging slots around or off by accident. Saved per machine.
var hotbar_locked := false


## Windows moved by dragging: key -> [x, y], the top-left corner on screen. Saved per machine.
var window_positions: Dictionary = {}


func set_window_position(key: String, pos: Vector2) -> void:
	window_positions[key] = [roundi(pos.x), roundi(pos.y)]
	_save_setting("window_positions", window_positions)


## Text windows resized by their corner grip: key -> [width, height] of the
## text area. Saved per machine.
var window_sizes: Dictionary = {}


func set_window_size(key: String, size: Vector2) -> void:
	window_sizes[key] = [roundi(size.x), roundi(size.y)]
	_save_setting("window_sizes", window_sizes)


func set_hotbar_locked(on: bool) -> void:
	hotbar_locked = on
	_save_setting("hotbar_locked", on)


func set_mouse_look(on: bool) -> void:
	mouse_look = on
	_save_setting("mouse_look", on)


func set_music_volume(v: float) -> void:
	music_volume = clampf(snappedf(v, 0.05), 0.0, 1.0)
	_save_setting("music_volume", music_volume)
	Music.apply_volume()


func set_social_in_main(on: bool) -> void:
	social_in_main = on
	_save_setting("social_in_main", on)


func set_sfx_volume(v: float) -> void:
	sfx_volume = clampf(snappedf(v, 0.05), 0.0, 1.0)
	_save_setting("sfx_volume", sfx_volume)
	Sfx.apply_volume()


## settings.json is shared (main keeps the server, account and mode there too),
## so a change rewrites one key and keeps the rest.
func _save_setting(key: String, value: Variant) -> void:
	var d := {}
	if FileAccess.file_exists(SETTINGS_PATH):
		var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(SETTINGS_PATH))
		if typeof(parsed) == TYPE_DICTIONARY:
			d = parsed
	d[key] = value
	var f := FileAccess.open(SETTINGS_PATH, FileAccess.WRITE)
	if f != null:
		f.store_string(JSON.stringify(d, "  "))


func _load_settings() -> void:
	if not FileAccess.file_exists(SETTINGS_PATH):
		return
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(SETTINGS_PATH))
	if typeof(parsed) == TYPE_DICTIONARY:
		mouse_look = bool((parsed as Dictionary).get("mouse_look", true))
		music_volume = clampf(float((parsed as Dictionary).get("music_volume", 0.25)), 0.0, 1.0)
		sfx_volume = clampf(float((parsed as Dictionary).get("sfx_volume", 0.7)), 0.0, 1.0)
		social_in_main = bool((parsed as Dictionary).get("social_in_main", true))
		hotbar_locked = bool((parsed as Dictionary).get("hotbar_locked", false))
		var wp: Variant = (parsed as Dictionary).get("window_positions", {})
		window_positions = wp if wp is Dictionary else {}
		var ws: Variant = (parsed as Dictionary).get("window_sizes", {})
		window_sizes = ws if ws is Dictionary else {}


func _ready() -> void:
	_load_settings()
	for action: String in BINDINGS:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		for key: Key in BINDINGS[action]:
			var ev := InputEventKey.new()
			ev.physical_keycode = key
			InputMap.action_add_event(action, ev)
	for action: String in CTRL_BINDINGS:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		var cev := InputEventKey.new()
		cev.physical_keycode = CTRL_BINDINGS[action]
		cev.ctrl_pressed = true
		InputMap.action_add_event(action, cev)
	for action: String in SHIFT_BINDINGS:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		for mod: String in ["ctrl", "shift"]:
			var sev := InputEventKey.new()
			sev.physical_keycode = SHIFT_BINDINGS[action]
			sev.ctrl_pressed = mod == "ctrl"
			sev.shift_pressed = mod == "shift"
			InputMap.action_add_event(action, sev)
