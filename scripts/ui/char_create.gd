class_name CharCreate
extends CanvasLayer
## Title screen: continue the saved character or create a new one. Every
## character pledges to one of the five deities (data/deities.json) for a small
## benefit; a saved character from before deities existed pledges on Continue.

signal confirmed(save: Dictionary)
signal connect_pressed  # the Server box's Connect button: play online
signal canceled  # server mode's Back button

var server_address := ""  # the Server box: "host" or "host:port"
var server_mode := false  # making a character on a server: just the new-character form
var _server_edit: LineEdit
var _status: Label

var existing: Dictionary = {}
var _name_edit: LineEdit
var _desc: Label
var _error: Label
var _selected := "warrior"
var _deity := ""
var _stats: StatPicker
var _race := "human"
var _deity_buttons := {}  # deity id -> its portrait button on the new-character page (some gods take only some races)
var _pledge_buttons := {}  # the same on the pledge page, for an older character's own race
var _gender := "male"
var _hair: HairPicker
var _race_desc: Label
var _class_buttons := {}  # class id -> its button (greyed when the race can't be it)
var _race_buttons := {}
var _main: VBoxContainer
var _preview_stage: Node3D  # the character as chosen so far, in its own little world
var _preview_key := ""
var _preview_turn := deg_to_rad(-20.0)  # a three-quarter view to start; drag to turn
var _preview_drag := false
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
	v.custom_minimum_size.x = 1400  # the new-character form: choices, the character, stats and god
	v.add_theme_constant_override("separation", 8)
	center.add_child(v)
	_main = v

	var title := UIKit.label("EMBERFALL", 50, UIKit.GOLD)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(title)
	var sub := UIKit.label("A new character for %s" % (Net.address if Net.address != "" else "this server") if server_mode else "The world is dangerous. Bring friends.", 15, UIKit.DIM)
	sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(sub)
	v.add_child(HSeparator.new())
	_status = UIKit.label("", 13, UIKit.DIM)
	_status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	if server_mode:
		_build_new_character(v)
		var cancel := UIKit.button("Back", Vector2(0, 36))
		cancel.pressed.connect(func() -> void: canceled.emit())
		v.add_child(cancel)
		v.add_child(_status)
		return

	var srv := HBoxContainer.new()
	srv.add_theme_constant_override("separation", 8)
	srv.add_child(UIKit.label("Server", 14, UIKit.GOLD))
	_server_edit = LineEdit.new()
	_server_edit.placeholder_text = "server address, to play online"
	_server_edit.text = server_address
	_server_edit.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_server_edit.text_changed.connect(func(t: String) -> void: server_address = t.strip_edges())
	_server_edit.text_submitted.connect(func(_t: String) -> void: connect_pressed.emit())
	srv.add_child(_server_edit)
	var go := UIKit.button("Connect", Vector2(110, 34))
	go.pressed.connect(func() -> void:
		if server_address == "":
			set_status("Type the server's address first.", true)
		else:
			connect_pressed.emit())
	srv.add_child(go)
	v.add_child(srv)
	v.add_child(_status)
	v.add_child(HSeparator.new())
	v.add_child(UIKit.label("Play offline", 18, UIKit.GOLD))

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

	_build_new_character(v)
	_build_pledge(center)


## Name, class and description on the left; starting stats and deity on the
## right; then Enter World.
func _build_new_character(page: VBoxContainer) -> void:
	page.add_child(UIKit.label("New character", 18, UIKit.GOLD))
	var cols := HBoxContainer.new()
	cols.add_theme_constant_override("separation", 30)
	page.add_child(cols)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 10)
	v.custom_minimum_size.x = 530
	cols.add_child(v)
	_build_preview(cols)
	var right := VBoxContainer.new()
	right.add_theme_constant_override("separation", 8)
	right.custom_minimum_size.x = 550
	cols.add_child(right)
	_name_edit = LineEdit.new()
	_name_edit.placeholder_text = "Name (letters only)"
	_name_edit.max_length = 15
	_name_edit.custom_minimum_size.y = 36
	_name_edit.text_submitted.connect(func(_t: String) -> void: _create())
	v.add_child(_name_edit)

	var genders := HBoxContainer.new()
	genders.add_theme_constant_override("separation", 6)
	var gender_group := ButtonGroup.new()
	for g: Array in [["male", "Male"], ["female", "Female"]]:
		var gb := UIKit.button(g[1], Vector2(0, 30))
		gb.toggle_mode = true
		gb.button_group = gender_group
		gb.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		gb.add_theme_font_size_override("font_size", 13)
		gb.button_pressed = g[0] == _gender
		gb.pressed.connect(func() -> void:
			_gender = g[0]
			_refresh_preview())
		genders.add_child(gb)
	v.add_child(genders)
	_hair = HairPicker.new()
	_hair.changed.connect(_refresh_preview)
	v.add_child(_hair)

	var races := GridContainer.new()  # the race first: it decides which classes are open
	races.columns = 5
	races.add_theme_constant_override("h_separation", 6)
	races.add_theme_constant_override("v_separation", 6)
	var race_group := ButtonGroup.new()
	for race_id: String in GameData.races:
		var rb := UIKit.button(GameData.races[race_id]["name"], Vector2(0, 34))
		rb.toggle_mode = true
		rb.button_group = race_group
		rb.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		rb.add_theme_font_size_override("font_size", 13)
		rb.button_pressed = race_id == _race
		rb.pressed.connect(func() -> void: _select_race(race_id))
		races.add_child(rb)
		_race_buttons[race_id] = rb
	v.add_child(races)
	_race_desc = UIKit.label("", 13, UIKit.TEXT)
	_race_desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	v.add_child(_race_desc)

	var row := GridContainer.new()  # three to a row: six classes don't fit in one
	row.columns = 3
	row.add_theme_constant_override("h_separation", 8)
	row.add_theme_constant_override("v_separation", 6)
	var group := ButtonGroup.new()
	for class_id: String in GameData.classes:
		var b := UIKit.button(GameData.classes[class_id]["name"], Vector2(0, 40))
		b.toggle_mode = true
		b.button_group = group
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.button_pressed = class_id == _selected
		b.pressed.connect(func() -> void: _select(class_id))
		row.add_child(b)
		_class_buttons[class_id] = b
	v.add_child(row)
	_desc = UIKit.label("", 13, UIKit.TEXT)
	_desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_desc.custom_minimum_size.y = 40
	v.add_child(_desc)
	right.add_child(UIKit.label("Starting stats", 16, UIKit.GOLD))
	_stats = StatPicker.new()
	right.add_child(_stats)
	_select(_selected)

	right.add_child(UIKit.label("Deity", 16, UIKit.GOLD))
	_deity_picker(right)
	_select_race(_race)

	v = page
	var enter := UIKit.button("Create character" if server_mode else "Enter World", Vector2(0, 44))
	enter.pressed.connect(_create)
	v.add_child(enter)
	_error = UIKit.label("", 13, Color(1, 0.45, 0.35))
	v.add_child(_error)


## The character as chosen so far (race, class, gender, hair), standing in
## its own lit world; drag to turn it. Rebuilt when a choice changes it.
func _build_preview(cols: HBoxContainer) -> void:
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 4)
	col.custom_minimum_size.x = 260
	cols.add_child(col)
	var box := SubViewportContainer.new()
	box.stretch = true
	box.custom_minimum_size = Vector2(260, 440)
	box.mouse_filter = Control.MOUSE_FILTER_STOP
	box.gui_input.connect(_on_preview_input)
	col.add_child(box)
	var view := SubViewport.new()
	view.own_world_3d = true
	view.transparent_bg = true
	view.msaa_3d = Viewport.MSAA_4X
	box.add_child(view)
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_CLEAR_COLOR
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.72, 0.74, 0.82)
	env.environment.ambient_light_energy = 0.8
	view.add_child(env)
	for spec: Array in [[Vector3(-30, 150, 0), 1.1], [Vector3(-15, -60, 0), 0.35]]:  # a key light and a soft fill from the other side
		var light := DirectionalLight3D.new()
		light.rotation_degrees = spec[0]
		light.light_energy = spec[1]
		view.add_child(light)
	var floor_disc := MeshInstance3D.new()  # something to stand on
	var disc := CylinderMesh.new()
	disc.top_radius = 0.75
	disc.bottom_radius = 0.75
	disc.height = 0.04
	floor_disc.mesh = disc
	floor_disc.position.y = -0.02
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.16, 0.17, 0.2)
	mat.roughness = 1.0
	floor_disc.material_override = mat
	view.add_child(floor_disc)
	_preview_stage = Node3D.new()
	view.add_child(_preview_stage)
	var cam := Camera3D.new()
	cam.fov = 30.0
	view.add_child(cam)
	cam.look_at_from_position(Vector3(0, 1.45, -7.6), Vector3(0, 1.1, 0))  # room for an ogre's head, a gnome's feet
	var hint := UIKit.label("Drag to turn", 11, UIKit.DIM)
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	col.add_child(hint)


func _on_preview_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and (event as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT:
		_preview_drag = (event as InputEventMouseButton).pressed
	elif event is InputEventMouseMotion and _preview_drag:
		_preview_turn += (event as InputEventMouseMotion).relative.x * 0.012
		if _preview_stage != null:
			_preview_stage.rotation.y = _preview_turn


## What the preview shows: the class's body and starting weapon, with the
## race's height, skin and bolt-ons, the gender and the hair.
func preview_look() -> Dictionary:
	var cls: Dictionary = GameData.classes.get(_selected, {})
	var weapon_item := str(cls.get("starting_items", {}).get("primary", ""))
	return {"model": str(cls.get("model", "")), "weapon": str(GameData.item(weapon_item).get("model", "")) if weapon_item != "" else "",
			"race": _race, "gender": _gender, "hair": [_hair.style if _hair != null else "", _hair.color if _hair != null else ""],
			"scale": float(GameData.races.get(_race, {}).get("scale", 1.0))}


func _refresh_preview() -> void:
	if _preview_stage == null:
		return
	var look := preview_look()
	var key := JSON.stringify(look)
	if key == _preview_key:
		return
	_preview_key = key
	for child in _preview_stage.get_children():
		child.queue_free()
	var model := Entity.make_visual(look)
	_preview_stage.add_child(model)
	_preview_stage.rotation.y = _preview_turn
	if model is CharacterModel:
		var idle := (model as CharacterModel)._clip("idle")
		if idle != "":
			(model as CharacterModel).anim.play(idle)


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
	_deity_picker(_pledge, true)
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
func _deity_picker(parent: Container, pledge := false) -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	var group := ButtonGroup.new()
	var desc := UIKit.label("Choose one. Each grants a small blessing, and they will remember who followed them.", 13, UIKit.DIM)
	desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	desc.custom_minimum_size.y = 64
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
		(_pledge_buttons if pledge else _deity_buttons)[deity_id] = b
		b.pressed.connect(func() -> void:
			_deity = deity_id
			desc.text = "%s, %s\n%s\n%s" % [d["name"], d["title"], d["description"], d["bonus_text"]]
			desc.add_theme_color_override("font_color", UIKit.TEXT))
		row.add_child(b)
	parent.add_child(row)
	parent.add_child(desc)
	_fit_deities()


## Gods who don't take a race ("races" and "alignments" in deities.json: the
## bog gods take only trolls and ogres, the elephants no evil race) are grayed
## out for it: the race being made, or on the pledge page the older
## character's own; a choice that no longer fits is cleared.
func _fit_deities() -> void:
	var pledging := _pledge != null and _pledge.visible
	_fit_row(_deity_buttons, _race, not pledging)
	_fit_row(_pledge_buttons, str(existing.get("race", "")), pledging)


## One row of gods; only the row in use may clear the choice (they share it).
func _fit_row(buttons: Dictionary, race: String, in_use: bool) -> void:
	for deity_id: String in buttons:
		var b: Button = buttons[deity_id]
		if not is_instance_valid(b):
			continue
		var ok := GameData.deity_allows(deity_id, race)
		b.disabled = not ok
		b.modulate.a = 1.0 if ok else 0.4
		if not ok and in_use and _deity == deity_id:
			_deity = ""
			b.button_pressed = false


## Connecting..., or why it failed.
func set_status(text: String, is_error := false) -> void:
	if _status != null:
		_status.text = text
		_status.add_theme_color_override("font_color", Color(1, 0.45, 0.35) if is_error else UIKit.DIM)


## Picks a race: its classes open (the rest grey out; the class moves to an
## open one if it must), its stats become the picker's starting values.
func _select_race(race_id: String) -> void:
	_race = race_id
	_fit_deities()
	var r: Dictionary = GameData.races[race_id]
	var open: Array = r.get("classes", [])
	for class_id: String in _class_buttons:
		(_class_buttons[class_id] as Button).disabled = not class_id in open
	(_race_buttons[race_id] as Button).button_pressed = true
	var home := str(r.get("home", "emberhold"))
	_race_desc.text = "%s  %s  Starts in %s." % [r["description"], r["trait_text"], home.capitalize()]
	if _stats != null:
		_stats.set_race(race_id)
	if not _selected in open:
		_select(str(open[0]))
	_refresh_preview()


func _select(class_id: String) -> void:
	if not class_id in GameData.races.get(_race, {}).get("classes", [class_id]):
		return
	_selected = class_id
	if _class_buttons.has(class_id):
		(_class_buttons[class_id] as Button).button_pressed = true
	_desc.text = GameData.classes[class_id]["description"]
	if _stats != null:
		_stats.set_class(class_id, true)  # a new class starts from its own spread
	_refresh_preview()


func _create() -> void:
	var raw := _name_edit.text.strip_edges()
	var regex := RegEx.create_from_string("^[A-Za-z]{3,15}$")
	if regex.search(raw) == null:
		_error.text = "Names must be 3-15 letters, no spaces or numbers."
		return
	if _deity == "" or not GameData.deity_allows(_deity, _race):
		_error.text = "Choose a deity." if _deity == "" else "%s does not take a %s." % [GameData.deities[_deity]["name"], GameData.races[_race]["name"]]
		return
	if _stats.points_left() > 0:
		_error.text = "Spend all your stat points (%d left)." % _stats.points_left()
		return
	var home := str(GameData.races[_race].get("home", World.cfg("starting_zone", "emberhold")))
	confirmed.emit({"name": raw.to_lower().capitalize(), "class": _selected, "deity": _deity, "stats": _stats.points.duplicate(),
			"race": _race, "gender": _gender, "hair": [_hair.style, _hair.color], "zone": home, "bind": home})
