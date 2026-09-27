class_name HairPicker
extends VBoxContainer
## A hairstyle row (models.json "hair_styles": the KayKit heads, any gender,
## plus "As born" for the head the body and gender give) and a row of hair
## color swatches ("hair_colors", plus "Natural"). Used by character creation
## and the character sheet's one restyle. `style` and `color` are what to save.

signal changed

var style := ""
var color := ""
var _style_buttons := {}  # style id ("" for as born) -> Button
var _color_buttons := {}  # color id ("" for natural) -> Button


func _init() -> void:
	add_theme_constant_override("separation", 4)


func _ready() -> void:
	var styles := HBoxContainer.new()
	styles.add_theme_constant_override("separation", 4)
	var style_group := ButtonGroup.new()
	var style_list: Array = [["", "As born"]]
	for id: String in GameData.models.get("hair_styles", {}):
		style_list.append([id, str(GameData.models["hair_styles"][id]["name"])])
	for pair: Array in style_list:
		var b := UIKit.button(pair[1], Vector2(0, 28))
		b.toggle_mode = true
		b.button_group = style_group
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.add_theme_font_size_override("font_size", 12)
		var id: String = pair[0]
		b.pressed.connect(func() -> void:
			style = id
			changed.emit())
		styles.add_child(b)
		_style_buttons[id] = b
	add_child(styles)
	var colors := HBoxContainer.new()
	colors.add_theme_constant_override("separation", 4)
	var color_group := ButtonGroup.new()
	var color_list: Array = [""]
	color_list.append_array(GameData.models.get("hair_colors", {}).keys())
	for id: String in color_list:
		var b := Button.new()
		b.toggle_mode = true
		b.button_group = color_group
		b.focus_mode = Control.FOCUS_NONE
		b.custom_minimum_size = Vector2(30, 26)
		b.tooltip_text = "Natural (the head's own color)" if id == "" else str(GameData.models["hair_colors"][id]["name"])
		if id == "":
			b.text = "–"
		else:
			for state: String in ["normal", "hover", "pressed", "hover_pressed"]:
				var sb := StyleBoxFlat.new()
				sb.bg_color = Color("#" + str(GameData.models["hair_colors"][id]["light"]))
				sb.set_corner_radius_all(4)
				sb.set_border_width_all(3 if state.contains("pressed") else 1)
				sb.border_color = UIKit.GOLD if state.contains("pressed") else Color(0, 0, 0, 0.6)
				b.add_theme_stylebox_override(state, sb)
		b.pressed.connect(func() -> void:
			color = id
			changed.emit())
		colors.add_child(b)
		_color_buttons[id] = b
	add_child(colors)
	set_hair(style, color)


## Shows a choice (unknown ids fall back to "").
func set_hair(new_style: String, new_color: String) -> void:
	style = new_style if _style_buttons.has(new_style) or _style_buttons.is_empty() else ""
	color = new_color if _color_buttons.has(new_color) or _color_buttons.is_empty() else ""
	if _style_buttons.has(style):
		(_style_buttons[style] as Button).button_pressed = true
	if _color_buttons.has(color):
		(_color_buttons[color] as Button).button_pressed = true
