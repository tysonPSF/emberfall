class_name CharCreate
extends CanvasLayer
## Title screen: continue the saved character or create a new one. Every
## character pledges to one of the five deities (data/deities.json) for a small
## benefit; a saved character from before deities existed pledges on Continue.

signal confirmed(save: Dictionary)

var server_address := ""  # "" plays offline; otherwise "host" or "host:port"
var _server_edit: LineEdit
var _status: Label

var existing: Dictionary = {}
var _name_edit: LineEdit
var _desc: Label
var _error: Label
var _selected := "warrior"
var _deity := ""
var _main: VBoxContainer
var _pledge: VBoxContainer


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
	v.custom_minimum_size.x = 560
	v.add_theme_constant_override("separation", 12)
	center.add_child(v)
	_main = v

	var title := UIKit.label("EMBERFALL", 60, UIKit.GOLD)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(title)
	var sub := UIKit.label("The world is dangerous. Bring friends.", 15, UIKit.DIM)
	sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(sub)
	v.add_child(HSeparator.new())

	var srv := HBoxContainer.new()
	srv.add_theme_constant_override("separation", 8)
	srv.add_child(UIKit.label("Server", 14, UIKit.GOLD))
	_server_edit = LineEdit.new()
	_server_edit.placeholder_text = "address, or leave blank to play offline"
	_server_edit.text = server_address
	_server_edit.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_server_edit.text_changed.connect(func(t: String) -> void: server_address = t.strip_edges())
	srv.add_child(_server_edit)
	v.add_child(srv)
	_status = UIKit.label("", 13, UIKit.DIM)
	_status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	v.add_child(_status)

	if not existing.is_empty():
		var cls: Dictionary = GameData.classes.get(existing.get("class", ""), {})
		var cont := UIKit.button("Continue as %s  (level %d %s)" % [existing.get("name", "?"), int(existing.get("level", 1)), cls.get("name", "?")], Vector2(0, 44))
		cont.pressed.connect(func() -> void:
			if GameData.deities.has(str(existing.get("deity", ""))):
				confirmed.emit(existing)
			else:
				_main.visible = false
				_pledge.visible = true)
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

	v.add_child(UIKit.label("Deity", 18, UIKit.GOLD))
	_deity_picker(v)

	var enter := UIKit.button("Enter World", Vector2(0, 44))
	enter.pressed.connect(_create)
	v.add_child(enter)
	_error = UIKit.label("", 13, Color(1, 0.45, 0.35))
	v.add_child(_error)
	_build_pledge(center)


## Older characters choose a deity before they carry on.
func _build_pledge(center: CenterContainer) -> void:
	_pledge = VBoxContainer.new()
	_pledge.custom_minimum_size.x = 560
	_pledge.add_theme_constant_override("separation", 12)
	_pledge.visible = false
	center.add_child(_pledge)
	var title := UIKit.label("The gods have noticed you, %s." % existing.get("name", "?"), 22, UIKit.GOLD)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_pledge.add_child(title)
	var sub := UIKit.label("Choose the deity you follow. This cannot be changed.", 13, UIKit.DIM)
	sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_pledge.add_child(sub)
	_deity_picker(_pledge)
	var go := UIKit.button("Pledge and continue", Vector2(0, 44))
	var err := UIKit.label("", 13, Color(1, 0.45, 0.35))
	go.pressed.connect(func() -> void:
		if _deity == "":
			err.text = "Choose a deity first."
			return
		var save := existing.duplicate(true)
		save["deity"] = _deity
		confirmed.emit(save))
	_pledge.add_child(go)
	_pledge.add_child(err)


## A row of portrait buttons, one per deity, above a label describing the
## chosen one.
func _deity_picker(parent: Container) -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	var group := ButtonGroup.new()
	var desc := UIKit.label("Choose one. Each grants a small blessing, and they will remember who followed them.", 13, UIKit.DIM)
	desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	desc.custom_minimum_size.y = 84
	for deity_id: String in GameData.deities:
		var d: Dictionary = GameData.deities[deity_id]
		var b := UIKit.button(str(d["name"]), Vector2(0, 118))
		b.toggle_mode = true
		b.button_group = group
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.icon = GameData.deity_portrait(deity_id)
		b.expand_icon = true
		b.icon_alignment = HORIZONTAL_ALIGNMENT_CENTER
		b.vertical_icon_alignment = VERTICAL_ALIGNMENT_TOP
		b.add_theme_font_size_override("font_size", 13)
		b.tooltip_text = "%s, %s" % [d["name"], d["title"]]
		b.pressed.connect(func() -> void:
			_deity = deity_id
			desc.text = "%s, %s\n%s\n%s" % [d["name"], d["title"], d["description"], d["bonus_text"]]
			desc.add_theme_color_override("font_color", UIKit.TEXT))
		row.add_child(b)
	parent.add_child(row)
	parent.add_child(desc)


## Connecting..., or why it failed.
func set_status(text: String, is_error := false) -> void:
	if _status != null:
		_status.text = text
		_status.add_theme_color_override("font_color", Color(1, 0.45, 0.35) if is_error else UIKit.DIM)


func _select(class_id: String) -> void:
	_selected = class_id
	_desc.text = GameData.classes[class_id]["description"]


func _create() -> void:
	var raw := _name_edit.text.strip_edges()
	var regex := RegEx.create_from_string("^[A-Za-z]{3,15}$")
	if regex.search(raw) == null:
		_error.text = "Names must be 3-15 letters, no spaces or numbers."
		return
	if _deity == "":
		_error.text = "Choose a deity."
		return
	confirmed.emit({"name": raw.to_lower().capitalize(), "class": _selected, "deity": _deity})
