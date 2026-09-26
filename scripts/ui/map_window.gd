class_name MapWindow
extends PanelContainer
## The zone map (M), painted like an old parchment chart from the zone itself:
## ground colors washed into parchment, hills shaded, water in blue ink, roads
## as brown lines, the mountain ring darkened. On it: you (an arrow), your
## group and pet, the zone's exits, its landmarks, and town services
## (guildmasters, merchants, bankers, quest givers, crafting stations), with a
## legend beside it. Fog covers what this character hasn't walked near;
## explored ground is remembered per character on this computer.
##
## The painting is made the first time you open the map in a zone, a few rows
## a frame so the game never stalls, and kept for as long as you stay.

const RES := 256  # painted samples across the zone (the land only: water, roads and decks are drawn as shapes on top)
const VIEW := 560.0  # the map's size on screen
const FOG_CELLS := 40  # the fog grid across the zone
const REVEAL := 45.0  # meters around you that you've "seen"
const PARCHMENT := Color(0.9, 0.85, 0.72)
const WATER := Color(0.45, 0.62, 0.7)
const ROAD := Color(0.55, 0.37, 0.2)
const WOOD := Color(0.6, 0.43, 0.27)
const INK := Color(0.23, 0.16, 0.1)

var player: Player
var _zone: Zone
var _image: Image
var _texture: ImageTexture
var _row := 0
var _fog: Dictionary = {}  # zone id -> PackedByteArray (FOG_CELLS^2), 1 = explored
var _fog_texture: ImageTexture
var _fog_dirty := true
var _save_timer := 0.0
var _marks: Array = []  # [kind, Vector2 world, label, detail]
var _canvas: Control
var _title: Label
var _legend: VBoxContainer
var _highlight := -1
var _reveal_timer := 0.0
var _center := Vector2.ZERO  # the world point in the middle of the view
var _span := 384.0  # meters across the view (the wheel zooms, a drag pans)
var _dragging := false


func _init() -> void:
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.12, 0.09, 0.06, 0.94)
	sb.border_color = Color(0.62, 0.48, 0.25)
	sb.set_border_width_all(2)
	sb.set_corner_radius_all(4)
	sb.set_content_margin_all(10)
	add_theme_stylebox_override("panel", sb)
	mouse_filter = Control.MOUSE_FILTER_STOP
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	add_child(row)
	var left := VBoxContainer.new()
	left.add_theme_constant_override("separation", 6)
	row.add_child(left)
	var head := HBoxContainer.new()
	_title = UIKit.label("", 17, UIKit.GOLD)
	_title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(_title)
	var close := UIKit.button("x", Vector2(24, 22))
	close.pressed.connect(func() -> void: visible = false)
	head.add_child(close)
	left.add_child(head)
	_canvas = Control.new()
	_canvas.custom_minimum_size = Vector2(VIEW, VIEW)
	_canvas.clip_contents = true
	_canvas.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR  # smooth painting, soft fog edges
	_canvas.draw.connect(_draw_map)
	_canvas.mouse_filter = Control.MOUSE_FILTER_PASS
	_canvas.gui_input.connect(_canvas_input)
	left.add_child(_canvas)
	var right := VBoxContainer.new()
	right.custom_minimum_size.x = 210
	right.add_theme_constant_override("separation", 4)
	row.add_child(right)
	right.add_child(UIKit.label("Legend", 14, UIKit.GOLD))
	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(210, VIEW)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	right.add_child(scroll)
	_legend = VBoxContainer.new()
	_legend.add_theme_constant_override("separation", 2)
	_legend.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(_legend)
	visible = false


func toggle() -> void:
	visible = not visible
	if visible:
		_prepare()


func _process(delta: float) -> void:
	if player == null or not is_instance_valid(player):
		return
	var z := World.zone_of(player)
	if z == null:
		return
	_reveal_timer -= delta
	if _reveal_timer <= 0.0:  # fog lifts around you whether the map is open or not
		_reveal_timer = 1.0
		_reveal(z)
	_save_timer -= delta
	if _save_timer <= 0.0:
		_save_timer = 15.0
		_save_fog()
	if not visible:
		return
	position = ((get_parent() as Control).size - size) * 0.5  # always in the middle of the screen
	if z != _zone:
		_prepare()
	if _image != null and _row < RES:  # painting: a few rows a frame
		for k in 8:
			if _row >= RES:
				break
			_paint_row(_row)
			_row += 1
		_texture.update(_image)
	_canvas.queue_redraw()


# --- the painting -------------------------------------------------------------

func _prepare() -> void:
	var z := World.zone_of(player) if player != null else null
	if z == null:
		return
	if z != _zone:
		_zone = z
		_highlight = -1
		_title.text = z.zone_name
		if bool(z.data.get("interior", false)):
			_image = null
			_texture = null
		else:
			_image = Image.create(RES, RES, false, Image.FORMAT_RGB8)
			_image.fill(PARCHMENT)
			_texture = ImageTexture.create_from_image(_image)
			_row = 0
		_load_fog(z.zone_id)
		_fog_dirty = true
		_build_marks(z)
		_center = Vector2.ZERO
		var city := str(z.zone_id).ends_with("hold")
		_span = (z.size - 50.0) * (0.55 if city else 1.0)  # the land inside the mountains; a town closer in
		if city:
			_center = Vector2(player.global_position.x, player.global_position.z)
	_canvas.queue_redraw()


func _paint_row(j: int) -> void:
	var z := _zone
	var step := z.size / RES
	var sun := Vector2(-0.6, -0.8).normalized()  # light from the northwest, as on old maps
	for i in RES:
		var x := -z.half + (i + 0.5) * step
		var y := -z.half + (j + 0.5) * step
		var h := z.height_at(x, y)
		var hx := z.height_at(x + step, y) - z.height_at(x - step, y)
		var hy := z.height_at(x, y + step) - z.height_at(x, y - step)
		var shade := clampf(1.0 - (hx * sun.x + hy * sun.y) / (step * 2.0) * 0.55, 0.55, 1.35)
		var ground := z._ground_color(x, y, h)
		var c := PARCHMENT.lerp(Color(ground.r, ground.g, ground.b), 0.5)
		c = Color(c.r * shade, c.g * shade, c.b * shade)
		var edge := maxf(absf(x), absf(y)) - (z.half - 30.0)
		if edge > 0.0 and h > z.amp * 0.6:  # the mountain ring, darker toward the rim
			c = c.lerp(Color(0.42, 0.37, 0.32), clampf(edge / 30.0, 0.0, 0.75))
		_image.set_pixel(i, j, c)


# --- what's on it --------------------------------------------------------------

const LANDMARK_NAMES := {
	"obelisk": "Obelisk", "camp": "Camp", "ruins": "Ruins", "outpost": "Outpost", "watchtower": "Watchtower",
	"cave": "Cave", "sun_shrine": "Shrine", "waystation": "Waystation", "stilt_village": "Stilt village",
	"lizard_camp": "Lizardfolk camp", "sunken_ruins": "Sunken ruins", "windmill": "Windmill", "orchard": "Orchard",
	"cabin": "Cabin", "spider_nest": "Spider nest", "hearth_plaza": "Hearth", "dawn_plaza": "Shrine of Prabhagaj",
	"market": "Market", "bridge": "Bridge", "rockslide": "Pass closed",
}
const PROP_NAMES := {
	"jungle_temple": "Temple of Jalendra", "titan_ribcage": "Titan's bones", "waterfall": "Waterfall", "crypt_entrance": "Mausoleum",
	"jalendra_head_fallen": "Fallen head", "jungle_tree_giant": "Great tree", "tavern": "The Ember and Anvil", "well": "Well",
}


func _build_marks(z: Zone) -> void:
	_marks.clear()
	for zl: Dictionary in z.data.get("zone_lines", []):
		var to := str(zl.get("to", ""))
		var name := to.capitalize()
		var path := "res://data/zones/%s.json" % to
		if FileAccess.file_exists(path):
			var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
			if parsed is Dictionary:
				name = str((parsed as Dictionary).get("name", name))
		_marks.append(["exit", Vector2(zl["pos"][0], zl["pos"][1]), "To " + name, ""])
	for lm: Dictionary in z.data.get("landmarks", []):
		var kind := str(lm.get("type", ""))
		var label := ""
		if kind == "prop":
			label = str(PROP_NAMES.get(str(lm.get("id", "")), ""))
		elif kind == "stilt_city":
			label = z.zone_name
		else:
			label = str(LANDMARK_NAMES.get(kind, ""))
		if label != "":
			_marks.append(["landmark", Vector2(lm["pos"][0], lm["pos"][1]), label, ""])
	for st: Array in z.stations:
		_marks.append(["craft", Vector2((st[1] as Vector3).x, (st[1] as Vector3).z), World.container_name(str(st[0])), "Crafting station"])
	var quest_givers := {}
	for qid: String in GameData.quests:
		quest_givers[str(GameData.quests[qid]["giver"])] = true
	for n: Dictionary in z.data.get("npcs", []):
		var id := str(n["id"])
		var d: Dictionary = GameData.npcs.get(id, {})
		var name := str(n.get("name", d.get("name", id)))
		var kind := ""
		var detail := str(d.get("title", ""))
		if d.has("guildmaster"):
			kind = "guild"
		elif d.get("banker", false):
			kind = "bank"
		elif d.has("merchant"):
			kind = "shop"
		elif quest_givers.has(id) or d.has("blesses"):
			kind = "quest"
		if kind != "":
			_marks.append([kind, Vector2(n["pos"][0], n["pos"][1]), name, detail])
	_marks.sort_custom(func(a: Array, b: Array) -> bool: return str(a[0]) + str(a[2]) < str(b[0]) + str(b[2]))
	for c in _legend.get_children():
		c.queue_free()
	var headings := {"exit": "Ways out", "guild": "Guildmasters", "bank": "Bank", "shop": "Merchants", "quest": "Quests", "craft": "Crafting", "landmark": "Places"}
	var last := ""
	for i in _marks.size():
		var m: Array = _marks[i]
		if m[0] != last:
			last = m[0]
			var h := UIKit.label(str(headings.get(last, last)), 12, UIKit.DIM)
			_legend.add_child(h)
		var b := Button.new()
		b.flat = true
		b.focus_mode = Control.FOCUS_NONE
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.text = "%s  %s" % [_glyph(str(m[0])), m[2]]
		b.tooltip_text = str(m[3]) if str(m[3]) != "" else str(m[2])
		b.add_theme_font_size_override("font_size", 12)
		b.add_theme_color_override("font_color", _mark_color(str(m[0])).lightened(0.35))
		var idx := i
		b.pressed.connect(func() -> void:
			_highlight = idx if _highlight != idx else -1
			_canvas.queue_redraw())
		_legend.add_child(b)
	if _marks.is_empty():
		_legend.add_child(UIKit.label("Nothing marked here yet.", 12, UIKit.DIM))


static func _glyph(kind: String) -> String:
	return {"exit": ">", "guild": "G", "bank": "B", "shop": "$", "quest": "!", "craft": "C", "landmark": "*"}.get(kind, "*")


static func _mark_color(kind: String) -> Color:
	return {"exit": Color(0.55, 0.3, 0.1), "guild": Color(0.35, 0.25, 0.6), "bank": Color(0.55, 0.42, 0.1), "shop": Color(0.2, 0.42, 0.22),
			"quest": Color(0.7, 0.45, 0.05), "craft": Color(0.45, 0.28, 0.18), "landmark": INK}.get(kind, INK)


# --- the fog -------------------------------------------------------------------

func _fog_path() -> String:
	return "user://map_%s.json" % player.display_name.to_lower()


func _load_fog(zone_id: String) -> void:
	if _fog.is_empty() and FileAccess.file_exists(_fog_path()):
		var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(_fog_path()))
		if parsed is Dictionary:
			for k: String in parsed:
				_fog[k] = Marshalls.base64_to_raw(str(parsed[k]))
	if not _fog.has(zone_id) or (_fog[zone_id] as PackedByteArray).size() != FOG_CELLS * FOG_CELLS:
		var fresh := PackedByteArray()
		fresh.resize(FOG_CELLS * FOG_CELLS)
		_fog[zone_id] = fresh


func _save_fog() -> void:
	if player == null or _fog.is_empty():
		return
	var out := {}
	for k: String in _fog:
		out[k] = Marshalls.raw_to_base64(_fog[k])
	var f := FileAccess.open(_fog_path(), FileAccess.WRITE)
	if f != null:
		f.store_string(JSON.stringify(out))


func _reveal(z: Zone) -> void:
	if bool(z.data.get("interior", false)):
		return
	_load_fog(z.zone_id)
	var cells: PackedByteArray = _fog[z.zone_id]
	var cell := z.size / FOG_CELLS
	var at := Vector2(player.global_position.x, player.global_position.z)
	var r := ceili(REVEAL / cell)
	var ci := int((at.x + z.half) / cell)
	var cj := int((at.y + z.half) / cell)
	var changed := false
	for dj in range(-r, r + 1):
		for di in range(-r, r + 1):
			var i := ci + di
			var j := cj + dj
			if i < 0 or j < 0 or i >= FOG_CELLS or j >= FOG_CELLS or cells[j * FOG_CELLS + i] == 1:
				continue
			var center := Vector2(-z.half + (i + 0.5) * cell, -z.half + (j + 0.5) * cell)
			if center.distance_to(at) <= REVEAL + cell * 0.5:
				cells[j * FOG_CELLS + i] = 1
				changed = true
	if changed:
		_fog[z.zone_id] = cells
		if z == _zone:
			_fog_dirty = true


func _explored(world: Vector2) -> bool:
	var cells: PackedByteArray = _fog.get(_zone.zone_id, PackedByteArray())
	if cells.is_empty():
		return false
	var cell := _zone.size / FOG_CELLS
	var i := clampi(int((world.x + _zone.half) / cell), 0, FOG_CELLS - 1)
	var j := clampi(int((world.y + _zone.half) / cell), 0, FOG_CELLS - 1)
	return cells[j * FOG_CELLS + i] == 1


func _fog_tex() -> ImageTexture:
	if _fog_dirty or _fog_texture == null:
		_fog_dirty = false
		var cells: PackedByteArray = _fog.get(_zone.zone_id, PackedByteArray())
		var img := Image.create(FOG_CELLS + 2, FOG_CELLS + 2, false, Image.FORMAT_RGBA8)
		img.fill(Color(0.86, 0.8, 0.66, 0.94))  # a fogged border, so the edge of the map fades too
		for j in FOG_CELLS:
			for i in FOG_CELLS:
				if not cells.is_empty() and cells[j * FOG_CELLS + i] == 1:
					img.set_pixel(i + 1, j + 1, Color(0.86, 0.8, 0.66, 0.0))
		img.resize(FOG_CELLS * 2, FOG_CELLS * 2, Image.INTERPOLATE_BILINEAR)  # soften twice: clouds, not squares
		img.resize(FOG_CELLS * 8, FOG_CELLS * 8, Image.INTERPOLATE_CUBIC)
		_fog_texture = ImageTexture.create_from_image(img)
	return _fog_texture


# --- drawing -------------------------------------------------------------------

func _to_view(world: Vector2) -> Vector2:
	return (world - _center) / _span * VIEW + Vector2(VIEW, VIEW) * 0.5


func _to_world(view: Vector2) -> Vector2:
	return (view - Vector2(VIEW, VIEW) * 0.5) * _span / VIEW + _center


## Draws a zone-sized texture so it lines up with the current view.
func _draw_zone_texture(tex: Texture2D) -> void:
	var top_left := _to_view(Vector2(-_zone.half, -_zone.half))
	var size := Vector2(_zone.size, _zone.size) / _span * VIEW
	_canvas.draw_texture_rect(tex, Rect2(top_left, size), false)


func _draw_map() -> void:
	var font := get_theme_default_font()
	var rect := Rect2(Vector2.ZERO, Vector2(VIEW, VIEW))
	_canvas.draw_rect(rect, PARCHMENT)
	if _zone == null:
		return
	if _texture == null:
		var msg := "No map of indoor places."
		_canvas.draw_string(font, Vector2(0, VIEW * 0.5), msg, HORIZONTAL_ALIGNMENT_CENTER, VIEW, 16, INK)
		return
	_draw_zone_texture(_texture)
	_draw_shapes()
	_draw_zone_texture(_fog_tex())  # soft clouds over what you haven't seen
	# a thin gold frame and a compass rose in the corner
	_canvas.draw_rect(rect.grow(-1), Color(0.75, 0.6, 0.32, 0.9), false, 1.5)
	var rose := Vector2(VIEW - 34, 34)
	_canvas.draw_circle(rose, 17.0, Color(PARCHMENT, 0.75))
	_canvas.draw_arc(rose, 17.0, 0, TAU, 32, Color(INK, 0.5), 1.0, true)
	_canvas.draw_colored_polygon(PackedVector2Array([rose + Vector2(0, -14), rose + Vector2(4, 0), rose + Vector2(0, 14), rose + Vector2(-4, 0)]), Color(INK, 0.7))
	_canvas.draw_colored_polygon(PackedVector2Array([rose + Vector2(0, -14), rose + Vector2(4, 0), rose + Vector2(-4, 0)]), Color(0.78, 0.22, 0.14))
	_canvas.draw_string(font, rose + Vector2(-4, -20), "N", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, INK)
	# marks, only where you've been (exits always: you know where the passes are)
	for i in _marks.size():
		var m: Array = _marks[i]
		var world: Vector2 = m[1]
		if m[0] != "exit" and not _explored(world):
			continue
		var p := _to_view(world)
		var col := _mark_color(str(m[0]))
		var big := i == _highlight
		var r := 10.0 if big else 7.5
		if m[0] == "exit":  # a chevron pointing out of the zone
			var out := (world - Vector2.ZERO).normalized()
			var side := Vector2(-out.y, out.x)
			var tip := p + out * 7.0
			var chevron := PackedVector2Array([tip, p - out * 5.0 + side * 7.0, p - out * 1.0, p - out * 5.0 - side * 7.0])
			_canvas.draw_colored_polygon(chevron + PackedVector2Array(), Color(0, 0, 0, 0.25))
			_canvas.draw_colored_polygon(chevron, col)
		elif m[0] == "landmark":
			_canvas.draw_circle(p + Vector2(0, 1.5), 4.5, Color(0, 0, 0, 0.2))
			_canvas.draw_circle(p, 4.0, Color(INK, 0.85))
			_canvas.draw_circle(p, 1.6, Color(PARCHMENT, 0.9))
		else:  # a pin: soft shadow, a light disc, a colored ring, the glyph
			_canvas.draw_circle(p + Vector2(0, 2), r + 1.0, Color(0, 0, 0, 0.22))
			_canvas.draw_circle(p, r, Color(1, 0.98, 0.93))
			_canvas.draw_arc(p, r - 1.0, 0, TAU, 24, col, 2.2, true)
			var g := _glyph(str(m[0]))
			var gw := font.get_string_size(g, HORIZONTAL_ALIGNMENT_LEFT, -1, 12).x
			_canvas.draw_string(font, p + Vector2(-gw * 0.5, 4.5), g, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, col)
		if big or m[0] in ["exit", "landmark"]:
			var label: String = m[2]
			var w := font.get_string_size(label, HORIZONTAL_ALIGNMENT_LEFT, -1, 12).x
			var at := p + Vector2(-w * 0.5, -r - 5)
			at.x = clampf(at.x, 6, VIEW - w - 6)
			at.y = clampf(at.y, 16, VIEW - 6)
			_canvas.draw_string_outline(font, at, label, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, 4, Color(1, 0.97, 0.9, 0.85))
			_canvas.draw_string(font, at, label, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, INK if not big else col)
	# your group and your pet
	for g: Dictionary in player.group:
		var other := World.get_object(int(g["id"])) as Player
		if other != null and other != player and World.zone_of(other) == _zone:
			var gp := _to_view(Vector2(other.global_position.x, other.global_position.z))
			_canvas.draw_circle(gp, 5.0, Color(0.2, 0.45, 0.8))
			_canvas.draw_string_outline(font, gp + Vector2(7, 4), other.display_name, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, 3, Color(PARCHMENT, 0.9))
			_canvas.draw_string(font, gp + Vector2(7, 4), other.display_name, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, Color(0.15, 0.3, 0.6))
	var pet := World.get_object(player.pet_id) as Entity if player.pet_id >= 0 else null
	if pet != null and World.zone_of(pet) == _zone:
		_canvas.draw_circle(_to_view(Vector2(pet.global_position.x, pet.global_position.z)), 4.0, Color(0.25, 0.6, 0.25))
	# you: an arrow pointing the way you face
	var me := _to_view(Vector2(player.global_position.x, player.global_position.z))
	var fwd := -player.global_basis.z
	var dir := Vector2(fwd.x, fwd.z).normalized()
	var side := Vector2(-dir.y, dir.x)
	var arrow := PackedVector2Array([me + dir * 11.0, me - dir * 7.0 + side * 7.0, me - dir * 3.0, me - dir * 7.0 - side * 7.0])
	_canvas.draw_colored_polygon(arrow, Color(0.75, 0.12, 0.08))
	_canvas.draw_polyline(arrow + PackedVector2Array([arrow[0]]), Color(PARCHMENT, 0.9), 1.5)


## Water, roads and decks as smooth shapes from the zone's own data, so their
## edges stay sharp at any zoom.
func _draw_shapes() -> void:
	var k := VIEW / _span  # pixels per meter
	for lake: Dictionary in _zone._lakes:
		var shore := PackedVector2Array()
		for pt: Vector2 in lake["shore"]:
			shore.append(_to_view(pt))
		_canvas.draw_colored_polygon(shore, WATER)
		_canvas.draw_polyline(shore + PackedVector2Array([shore[0]]), WATER.darkened(0.3), 1.5, true)
		for isl: Array in lake.get("islands", []):
			_canvas.draw_circle(_to_view(isl[0]), float(isl[1]) * k, PARCHMENT.lerp(Color(0.55, 0.62, 0.4), 0.35))
	for river: Dictionary in _zone._rivers:
		var line := PackedVector2Array()
		for pt: Vector2 in river["points"]:
			line.append(_to_view(pt))
		var w := maxf(2.0, float(river["width"]) * k)
		if river["dry"]:
			_canvas.draw_polyline(line, Color(0.62, 0.5, 0.36, 0.7), w, true)
		else:
			_canvas.draw_polyline(line, WATER.darkened(0.25), w + 1.5, true)
			_canvas.draw_polyline(line, WATER, w, true)
	for road: Dictionary in _zone._roads:
		var line := PackedVector2Array()
		for pt: Vector2 in road["points"]:
			line.append(_to_view(pt))
		var w := maxf(2.2, float(road["width"]) * k)
		_canvas.draw_polyline(line, ROAD.darkened(0.2), w + 1.0, true)
		_canvas.draw_polyline(line, ROAD.lightened(0.15), w * 0.55, true)
	for deck: Array in _zone._decks:
		var xf: Transform3D = deck[0]
		var hs: Vector2 = deck[1]
		var corners := PackedVector2Array()
		for c: Vector2 in [Vector2(-hs.x, -hs.y), Vector2(hs.x, -hs.y), Vector2(hs.x, hs.y), Vector2(-hs.x, hs.y)]:
			var w3 := xf * Vector3(c.x, 0, c.y)
			corners.append(_to_view(Vector2(w3.x, w3.z)))
		_canvas.draw_colored_polygon(corners, WOOD)
		_canvas.draw_polyline(corners + PackedVector2Array([corners[0]]), WOOD.darkened(0.3), 1.0, true)


func _canvas_input(ev: InputEvent) -> void:
	if ev is InputEventMouseButton and (ev as InputEventMouseButton).pressed:
		var mb := ev as InputEventMouseButton
		if mb.button_index in [MOUSE_BUTTON_WHEEL_UP, MOUSE_BUTTON_WHEEL_DOWN]:  # zoom toward the mouse
			var before := _to_world(mb.position)
			_span = clampf(_span * (0.8 if mb.button_index == MOUSE_BUTTON_WHEEL_UP else 1.25), 60.0, _zone.size)
			_center += before - _to_world(mb.position)
			_canvas.queue_redraw()
			_canvas.accept_event()
			return
		if mb.button_index == MOUSE_BUTTON_LEFT:
			_dragging = true
	if ev is InputEventMouseButton and not (ev as InputEventMouseButton).pressed and (ev as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT:
		_dragging = false
	if ev is InputEventMouseMotion and _dragging:  # drag to pan
		_center -= (ev as InputEventMouseMotion).relative * _span / VIEW
		_canvas.queue_redraw()
		return
	if ev is InputEventMouseMotion:  # a mark's name when you hover it
		var at := (ev as InputEventMouseMotion).position
		_canvas.tooltip_text = ""
		for m: Array in _marks:
			if (m[0] == "exit" or _explored(m[1])) and _to_view(m[1]).distance_to(at) < 9.0:
				_canvas.tooltip_text = str(m[2]) + ("\n" + str(m[3]) if str(m[3]) != "" else "")
				break
