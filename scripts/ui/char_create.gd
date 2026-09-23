class_name CharCreate
extends CanvasLayer
## Title screen: continue the saved character or create a new one.

signal confirmed(save: Dictionary)

var existing: Dictionary = {}
var _name_edit: LineEdit
var _desc: Label
var _error: Label
var _selected := "warrior"


func setup(save: Dictionary) -> void:
	existing = save


func _ready() -> void:
	var bg := ColorRect.new()
	bg.color = Color(0.05, 0.06, 0.07)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(center)
	var v := VBoxContainer.new()
	v.custom_minimum_size.x = 520
	v.add_theme_constant_override("separation", 12)
	center.add_child(v)

	var title := UIKit.label("EMBERFALL", 60, UIKit.GOLD)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(title)
	var sub := UIKit.label("The world is dangerous. Bring friends.", 15, UIKit.DIM)
	sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(sub)
	v.add_child(HSeparator.new())

	if not existing.is_empty():
		var cls: Dictionary = GameData.classes.get(existing.get("class", ""), {})
		var cont := UIKit.button("Continue as %s  (level %d %s)" % [existing.get("name", "?"), int(existing.get("level", 1)), cls.get("name", "?")], Vector2(0, 44))
		cont.pressed.connect(func() -> void: confirmed.emit(existing))
		v.add_child(cont)
		v.add_child(UIKit.label("Creating a new character replaces this one.", 12, UIKit.DIM))
		v.add_child(HSeparator.new())

	v.add_child(UIKit.label("New character", 18, UIKit.GOLD))
	_name_edit = LineEdit.new()
	_name_edit.placeholder_text = "Name (letters only)"
	_name_edit.max_length = 15
	_name_edit.custom_minimum_size.y = 36
	_name_edit.text_submitted.connect(func(_t: String) -> void: _create())
	v.add_child(_name_edit)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	var group := ButtonGroup.new()
	for class_id: String in GameData.classes:
		var b := UIKit.button(GameData.classes[class_id]["name"], Vector2(0, 40))
		b.toggle_mode = true
		b.button_group = group
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.button_pressed = class_id == _selected
		b.pressed.connect(func() -> void: _select(class_id))
		row.add_child(b)
	v.add_child(row)
	_desc = UIKit.label("", 13, UIKit.TEXT)
	_desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_desc.custom_minimum_size.y = 40
	v.add_child(_desc)
	_select(_selected)

	var enter := UIKit.button("Enter World", Vector2(0, 44))
	enter.pressed.connect(_create)
	v.add_child(enter)
	_error = UIKit.label("", 13, Color(1, 0.45, 0.35))
	v.add_child(_error)


func _select(class_id: String) -> void:
	_selected = class_id
	_desc.text = GameData.classes[class_id]["description"]


func _create() -> void:
	var raw := _name_edit.text.strip_edges()
	var regex := RegEx.create_from_string("^[A-Za-z]{3,15}$")
	if regex.search(raw) == null:
		_error.text = "Names must be 3-15 letters, no spaces or numbers."
		return
	confirmed.emit({"name": raw.to_lower().capitalize(), "class": _selected})
