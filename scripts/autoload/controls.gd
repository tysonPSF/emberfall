extends Node
## Registers default key bindings at startup so project.godot stays readable.

const BINDINGS := {
	"move_forward": [KEY_W, KEY_UP],
	"move_back": [KEY_S, KEY_DOWN],
	"turn_left": [KEY_A, KEY_LEFT],
	"turn_right": [KEY_D, KEY_RIGHT],
	"jump": [KEY_SPACE],
	"auto_attack": [KEY_Q],
	"target_next": [KEY_TAB],
	"target_self": [KEY_F1],
	"consider": [KEY_C],
	"sit": [KEY_X],
	"loot": [KEY_L],
	"hail": [KEY_E],
	"trade": [KEY_G],
	"inventory": [KEY_I],
	"help": [KEY_H],
	"cancel": [KEY_ESCAPE],
	"hotbar_1": [KEY_1],
	"hotbar_2": [KEY_2],
	"hotbar_3": [KEY_3],
	"hotbar_4": [KEY_4],
}


func _ready() -> void:
	for action: String in BINDINGS:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		for key: Key in BINDINGS[action]:
			var ev := InputEventKey.new()
			ev.physical_keycode = key
			InputMap.action_add_event(action, ev)
