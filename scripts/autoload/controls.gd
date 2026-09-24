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
	"target_next": [KEY_TAB],
	"target_interact": [KEY_T],
	"target_self": [KEY_F1],
	"settings": [KEY_O],
	"settings_mouse_look": [KEY_M],
	"consider": [KEY_C],
	"sit": [KEY_X],
	"loot": [KEY_L],
	"hail": [KEY_E],
	"trade": [KEY_G],
	"inventory": [KEY_I],
	"help": [KEY_H],
	"reload": [KEY_F5],
	"cancel": [KEY_ESCAPE],
	"hotbar_1": [KEY_1],
	"hotbar_2": [KEY_2],
	"hotbar_3": [KEY_3],
	"hotbar_4": [KEY_4],
	"hotbar_5": [KEY_5],
	"hotbar_6": [KEY_6],
	"hotbar_7": [KEY_7],
	"hotbar_8": [KEY_8],
}


## Off puts the game back on the keyboard: the cursor stays out, A/D turn rather
## than strafe, and you click to target instead of aiming. Saved per machine,
## like the bindings, not per character.
var mouse_look := true


func set_mouse_look(on: bool) -> void:
	mouse_look = on
	var f := FileAccess.open(SETTINGS_PATH, FileAccess.WRITE)
	if f != null:
		f.store_string(JSON.stringify({"mouse_look": mouse_look}, "  "))


func _load_settings() -> void:
	if not FileAccess.file_exists(SETTINGS_PATH):
		return
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(SETTINGS_PATH))
	if typeof(parsed) == TYPE_DICTIONARY:
		mouse_look = bool((parsed as Dictionary).get("mouse_look", true))


func _ready() -> void:
	_load_settings()
	for action: String in BINDINGS:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		for key: Key in BINDINGS[action]:
			var ev := InputEventKey.new()
			ev.physical_keycode = key
			InputMap.action_add_event(action, ev)
