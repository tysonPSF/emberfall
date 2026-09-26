class_name UIKit
## Small helpers so every window shares the same look.

const GOLD := Color(0.86, 0.72, 0.42)
const TEXT := Color(0.9, 0.88, 0.82)
const DIM := Color(0.62, 0.6, 0.56)


static func panel() -> PanelContainer:
	var p := PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.05, 0.05, 0.07, 0.82)
	sb.border_color = Color(0.55, 0.45, 0.25, 0.9)
	sb.set_border_width_all(1)
	sb.set_corner_radius_all(4)
	sb.set_content_margin_all(8)
	p.add_theme_stylebox_override("panel", sb)
	p.mouse_filter = Control.MOUSE_FILTER_STOP
	return p


static func label(text: String, font_size := 14, color := TEXT) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", font_size)
	l.add_theme_color_override("font_color", color)
	l.add_theme_color_override("font_outline_color", Color.BLACK)
	l.add_theme_constant_override("outline_size", 3)
	return l


static func bar(color: Color, width := 220.0, height := 14.0) -> ProgressBar:
	var b := ProgressBar.new()
	b.show_percentage = false
	b.custom_minimum_size = Vector2(width, height)
	var bg := StyleBoxFlat.new()
	bg.bg_color = Color(0, 0, 0, 0.65)
	bg.set_corner_radius_all(2)
	var fg := StyleBoxFlat.new()
	fg.bg_color = color
	fg.set_corner_radius_all(2)
	b.add_theme_stylebox_override("background", bg)
	b.add_theme_stylebox_override("fill", fg)
	b.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return b


static func button(text: String, min_size := Vector2(0, 30)) -> Button:
	var b := Button.new()
	b.text = text
	b.focus_mode = Control.FOCUS_NONE
	b.custom_minimum_size = min_size
	return b


## Gives a button a framed face: dark with a gold edge, lighter under the
## mouse, sunk when pressed. `lit` keeps it glowing (a toggle that's on).
static func frame(b: Button, lit := false) -> void:
	var looks := {"normal": [0.13, 0.55], "hover": [0.2, 0.9], "pressed": [0.07, 0.9], "disabled": [0.1, 0.3]}
	for state: String in looks:
		var sb := StyleBoxFlat.new()
		sb.bg_color = Color(0.3, 0.22, 0.1, 0.9) if lit and state != "hover" else Color(looks[state][0], looks[state][0] * 0.95, looks[state][0] * 0.85, 0.92)
		sb.border_color = Color(GOLD, 1.0 if lit else looks[state][1])
		sb.set_border_width_all(1)
		sb.border_width_bottom = 1 if state == "pressed" else 2
		sb.set_corner_radius_all(4)
		sb.content_margin_left = 10
		sb.content_margin_right = 10
		sb.content_margin_top = 2
		sb.content_margin_bottom = 2
		b.add_theme_stylebox_override(state, sb)
	b.add_theme_color_override("font_color", GOLD if lit else TEXT)
	b.add_theme_color_override("font_hover_color", Color(1, 0.95, 0.8))
	b.add_theme_color_override("font_pressed_color", GOLD)


## Anchors a control to a point on screen (0..1 on each axis) plus a pixel
## offset, growing away from the nearest edge as its content sizes it.
static func place(c: Control, anchor: Vector2, offset: Vector2) -> void:
	c.anchor_left = anchor.x
	c.anchor_right = anchor.x
	c.anchor_top = anchor.y
	c.anchor_bottom = anchor.y
	c.offset_left = offset.x
	c.offset_right = offset.x
	c.offset_top = offset.y
	c.offset_bottom = offset.y
	c.grow_horizontal = _grow(anchor.x)
	c.grow_vertical = _grow(anchor.y)


static func _grow(a: float) -> Control.GrowDirection:
	if a >= 1.0:
		return Control.GROW_DIRECTION_BEGIN
	if a <= 0.0:
		return Control.GROW_DIRECTION_END
	return Control.GROW_DIRECTION_BOTH
