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


## Breaks long lines at spaces so a tooltip stays a readable column
## (Godot's tooltips never wrap on their own). Words longer than the width
## stay whole; BBCode tags have no spaces, so they survive.
static func wrap(text: String, width := 60) -> String:
	var out := PackedStringArray()
	for line in text.split("\n"):
		var cur := ""
		for word in line.split(" "):
			if cur != "" and cur.length() + 1 + word.length() > width:
				out.append(cur)
				cur = word
			else:
				cur = word if cur == "" else cur + " " + word
		out.append(cur)
	return "\n".join(out)


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
## Lets a panel be dragged by its background (buttons still click) and
## remembers where it was left (Controls.window_positions[key], per machine),
## kept on screen. Call after placing it and adding it to the tree.
static func draggable(c: Control, key: String) -> void:
	c.set_meta("drag_key", key)
	c.set_meta("drag_home", [c.anchor_left, c.anchor_top, c.anchor_right, c.anchor_bottom,
			c.offset_left, c.offset_top, c.offset_right, c.offset_bottom, c.grow_horizontal, c.grow_vertical])
	if c.tooltip_text == "":
		c.tooltip_text = "Drag to move."
	c.mouse_default_cursor_shape = Control.CURSOR_MOVE
	for child: Node in c.find_children("*", "Container", true, false):
		(child as Control).mouse_filter = Control.MOUSE_FILTER_PASS  # clicks between buttons reach the panel
	var grab := [null]  # where the mouse took hold, relative to the corner, while dragging
	c.gui_input.connect(func(ev: InputEvent) -> void:
		if ev is InputEventMouseButton and (ev as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT:
			if ev.pressed:
				grab[0] = (ev as InputEventMouseButton).global_position - c.global_position
			elif grab[0] != null:
				grab[0] = null
				Controls.set_window_position(key, c.global_position)
			c.accept_event()
		elif ev is InputEventMouseMotion and grab[0] != null:
			_move_to(c, (ev as InputEventMouseMotion).global_position - grab[0])
			c.accept_event())
	var saved: Variant = Controls.window_positions.get(key)
	if saved is Array and (saved as Array).size() == 2:
		(func() -> void: _move_to(c, Vector2(float(saved[0]), float(saved[1])))).call_deferred()


## A grip in a window's top-right corner that resizes it: dragging it up and
## right makes the text area bigger (every one of `areas`, e.g. a chat's tabs,
## takes the same size), down and left smaller, the window's bottom-left
## corner staying put. The size is kept per machine (Controls.window_sizes[key])
## and Reset window positions puts it back. Call after draggable().
static func resizable(c: Control, key: String, areas: Array, smallest := Vector2(220, 70)) -> void:
	var home: Vector2 = (areas[0] as Control).custom_minimum_size
	c.set_meta("size_key", key)
	c.set_meta("size_home", home)
	c.set_meta("size_areas", areas)
	var grip := Control.new()
	grip.top_level = true  # outside the panel's layout: it rides the corner
	grip.custom_minimum_size = Vector2(16, 16)
	grip.size = Vector2(16, 16)
	grip.mouse_default_cursor_shape = Control.CURSOR_BDIAGSIZE
	grip.tooltip_text = "Drag to resize."
	grip.mouse_filter = Control.MOUSE_FILTER_STOP
	c.add_child(grip)
	grip.draw.connect(func() -> void:
		for k in 3:  # three diagonal strokes, a resize corner
			var o := 4.0 + k * 4.0
			grip.draw_line(Vector2(o, 1), Vector2(15, 16 - o), Color(0.85, 0.75, 0.5, 0.75), 1.5))
	var follow := func() -> void:
		grip.global_position = c.global_position + Vector2(c.size.x - 17, 1)
	c.item_rect_changed.connect(follow)
	c.visibility_changed.connect(follow)
	var grab := [null]  # [mouse at the start, area size at the start, the window's bottom-left corner]
	grip.gui_input.connect(func(ev: InputEvent) -> void:
		if ev is InputEventMouseButton and (ev as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT:
			if ev.pressed:
				grab[0] = [(ev as InputEventMouseButton).global_position, (areas[0] as Control).custom_minimum_size, c.global_position + Vector2(0, c.size.y)]
			elif grab[0] != null:
				grab[0] = null
				Controls.set_window_size(key, (areas[0] as Control).custom_minimum_size)
				if c.has_meta("drag_key"):
					Controls.set_window_position(str(c.get_meta("drag_key")), c.global_position)
			grip.accept_event()
		elif ev is InputEventMouseMotion and grab[0] != null:
			var d: Vector2 = (ev as InputEventMouseMotion).global_position - grab[0][0]
			var screen := c.get_viewport_rect().size
			var want: Vector2 = (grab[0][1] + Vector2(d.x, -d.y)).clamp(smallest, screen * 0.85)
			_size_areas(c, want)
			c.size = Vector2.ZERO  # shrink to fit the new size, then put the bottom-left corner back
			(func() -> void: _move_to(c, Vector2(grab[0][2].x, grab[0][2].y - c.size.y)) if grab[0] != null else null).call_deferred()
			grip.accept_event())
	var saved: Variant = Controls.window_sizes.get(key)
	if saved is Array and (saved as Array).size() == 2:
		_size_areas(c, Vector2(float(saved[0]), float(saved[1])))
	follow.call_deferred()


static func _size_areas(c: Control, s: Vector2) -> void:
	for a: Control in c.get_meta("size_areas", []):
		a.custom_minimum_size = s


## Whether a draggable window has been moved from where it started (its
## layout code leaves it alone then).
static func moved(c: Control) -> bool:
	return Controls.window_positions.has(str(c.get_meta("drag_key", "")))


## Every dragged window under `root` back where it started.
static func reset_windows(root: Node) -> void:
	for c: Node in root.find_children("*", "Control", true, false):
		if c.has_meta("drag_home") and moved(c):
			var h: Array = c.get_meta("drag_home")
			c.anchor_left = h[0]
			c.anchor_top = h[1]
			c.anchor_right = h[2]
			c.anchor_bottom = h[3]
			c.offset_left = h[4]
			c.offset_top = h[5]
			c.offset_right = h[6]
			c.offset_bottom = h[7]
			c.grow_horizontal = h[8]
			c.grow_vertical = h[9]
	Controls.window_positions = {}
	Controls._save_setting("window_positions", {})
	for c: Node in root.find_children("*", "Control", true, false):  # and every resized one back to its size
		if c.has_meta("size_home"):
			_size_areas(c, c.get_meta("size_home"))
			(c as Control).size = Vector2.ZERO
	Controls.window_sizes = {}
	Controls._save_setting("window_sizes", {})


## Pins a control's top-left corner at `at` (screen pixels), inside the screen.
static func _move_to(c: Control, at: Vector2) -> void:
	var screen := c.get_viewport_rect().size
	at = at.clamp(Vector2.ZERO, (screen - c.size).max(Vector2.ZERO))
	c.set_anchors_preset(Control.PRESET_TOP_LEFT)
	c.grow_horizontal = Control.GROW_DIRECTION_END
	c.grow_vertical = Control.GROW_DIRECTION_END
	c.position = at


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
