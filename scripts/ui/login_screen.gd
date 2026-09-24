class_name LoginScreen
extends CanvasLayer
## Playing on a server: connect, log in (or make an account), then pick a
## character, make a new one, or bring the offline one over. Entering the world
## is Net.joined, which main answers.

signal back  # leave for the title screen

var address := ""
var account := ""
var offline_save: Dictionary = {}  # the local character, offered for import
var logged_in := false  # true when we come back here from camping

var _login_box: VBoxContainer
var _chars_box: VBoxContainer
var _list: VBoxContainer
var _account_edit: LineEdit
var _pw_edit: LineEdit
var _status: Label
var _import_button: Button
var _names_here: Array = []
var _creator: CharCreate


func _ready() -> void:
	layer = 20  # above anything left of the world
	var bg := ColorRect.new()
	bg.color = Color(0.05, 0.06, 0.07)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(center)
	var v := VBoxContainer.new()
	v.custom_minimum_size.x = 460
	v.add_theme_constant_override("separation", 12)
	center.add_child(v)
	var title := UIKit.label("EMBERFALL", 52, UIKit.GOLD)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(title)
	var sub := UIKit.label("Server: %s" % address, 14, UIKit.DIM)
	sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(sub)
	v.add_child(HSeparator.new())

	_login_box = VBoxContainer.new()
	_login_box.add_theme_constant_override("separation", 10)
	v.add_child(_login_box)
	_login_box.add_child(UIKit.label("Account", 14, UIKit.GOLD))
	_account_edit = LineEdit.new()
	_account_edit.placeholder_text = "account name"
	_account_edit.text = account
	_account_edit.custom_minimum_size.y = 36
	_login_box.add_child(_account_edit)
	_pw_edit = LineEdit.new()
	_pw_edit.placeholder_text = "password"
	_pw_edit.secret = true
	_pw_edit.custom_minimum_size.y = 36
	_pw_edit.text_submitted.connect(func(_t: String) -> void: _login(false))
	_login_box.add_child(_pw_edit)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	for spec: Array in [["Log in", false], ["Create account", true]]:
		var b := UIKit.button(spec[0], Vector2(0, 40))
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.pressed.connect(_login.bind(spec[1]))
		row.add_child(b)
	_login_box.add_child(row)
	var note := UIKit.label("Your password is hashed before it leaves this computer, but the connection isn't encrypted: don't reuse an important one.", 11, UIKit.DIM)
	note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_login_box.add_child(note)

	_chars_box = VBoxContainer.new()
	_chars_box.add_theme_constant_override("separation", 10)
	_chars_box.visible = false
	v.add_child(_chars_box)
	_chars_box.add_child(UIKit.label("Characters", 16, UIKit.GOLD))
	_list = VBoxContainer.new()
	_list.add_theme_constant_override("separation", 6)
	_chars_box.add_child(_list)
	var create := UIKit.button("Create a new character", Vector2(0, 38))
	create.pressed.connect(_open_creator)
	_chars_box.add_child(create)
	_import_button = UIKit.button("", Vector2(0, 38))
	_import_button.pressed.connect(func() -> void: Net.import_character(offline_save))
	_chars_box.add_child(_import_button)

	_status = UIKit.label("", 13, UIKit.DIM)
	_status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	v.add_child(_status)
	var leave := UIKit.button("Back", Vector2(0, 36))
	leave.pressed.connect(func() -> void:
		Net.leave()
		back.emit())
	v.add_child(leave)

	Net.connected_ok.connect(_on_connected)
	Net.join_failed.connect(func(reason: String) -> void: _say(reason, true))
	Net.left_server.connect(func(reason: String) -> void:
		_show_login()
		_say(reason, true))
	Net.server_message.connect(_say)
	Net.characters_listed.connect(_on_characters)
	if logged_in:
		_say("Choose a character.")
	else:
		_say("Connecting to %s..." % address)
		Net.connect_to(address)


func _on_connected() -> void:
	_say("Connected. Log in, or create an account if this is your first time here.")
	_account_edit.grab_focus() if _account_edit.text == "" else _pw_edit.grab_focus()


func _login(create: bool) -> void:
	if Net.mode != "client":
		_say("Not connected yet.", true)
		return
	account = _account_edit.text.strip_edges()
	if account == "" or _pw_edit.text == "":
		_say("Enter an account name and password.", true)
		return
	_say("Creating account..." if create else "Logging in...")
	Net.login(account, _pw_edit.text, create)


func _on_characters(list: Array) -> void:
	logged_in = true
	_login_box.visible = false
	_chars_box.visible = true
	if _creator != null:
		_creator.queue_free()
		_creator = null
	for child in _list.get_children():
		child.queue_free()
	_names_here = []
	for c: Dictionary in list:
		_names_here.append(str(c["name"]))
		var cls: Dictionary = GameData.classes.get(str(c["class"]), {})
		var zone_name := str(GameData.load_zone(str(c["zone"])).get("name", c["zone"])) if str(c["zone"]) != "" else ""
		var b := UIKit.button("%s   level %d %s   %s" % [c["name"], int(c["level"]), cls.get("name", "?"), zone_name], Vector2(0, 42))
		b.pressed.connect(func() -> void:
			_say("Entering the world as %s..." % c["name"])
			Net.enter_world(str(c["name"])))
		_list.add_child(b)
	if list.is_empty():
		_list.add_child(UIKit.label("No characters yet on this server.", 13, UIKit.DIM))
	var offline_name := str(offline_save.get("name", ""))
	_import_button.visible = offline_name != "" and not offline_name in _names_here
	_import_button.text = "Bring over %s, your offline character" % offline_name
	_say("Choose a character." if not list.is_empty() else "Create a character, or bring your offline one over.")


func _open_creator() -> void:
	_creator = CharCreate.new()
	_creator.server_mode = true
	_creator.layer = 21
	_creator.confirmed.connect(func(s: Dictionary) -> void:
		Net.create_character(str(s["name"]), str(s["class"]), str(s.get("deity", ""))))
	_creator.canceled.connect(func() -> void:
		_creator.queue_free()
		_creator = null)
	add_child(_creator)
	Net.server_message.connect(func(text: String, is_error: bool) -> void:
		if _creator != null and is_instance_valid(_creator):
			_creator.set_status(text, is_error))


func _show_login() -> void:
	logged_in = false
	_login_box.visible = true
	_chars_box.visible = false


func _say(text: String, is_error := false) -> void:
	_status.text = text
	_status.add_theme_color_override("font_color", Color(1, 0.45, 0.35) if is_error else UIKit.DIM)
