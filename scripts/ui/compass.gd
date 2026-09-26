class_name Compass
extends Control
## The compass across the top of the screen: a strip of headings that scrolls
## as you turn (N in ember, the rest in gold, ticks every 15 degrees), the
## zone's name on a ribbon beneath it (with its levels, from the zone's
## "levels"), and live marks on the strip: your
## target (in its con color), your pet, the zone's exits (a gold diamond,
## named when you face one), and the sun or the moon where they are in the sky.
## Everything is drawn here; the HUD only sets `player`.

const WIDTH := 460.0
const BAND := 30.0  # height of the heading strip
const SPAN := 100.0  # degrees either side of straight ahead that the strip shows
const GOLD := Color(0.86, 0.72, 0.42)
const EMBER := Color(1.0, 0.45, 0.28)
const INK := Color(0.04, 0.04, 0.06)

var player: Player
var _heading := 0.0
var _zone_name := ""
var _levels := ""  # "Levels 6 - 14"; empty for cities and interiors
var _exits: Array = []  # [Vector2 position, "Thornwood Vale"]
var _exits_zone: Zone


func _init() -> void:
	custom_minimum_size = Vector2(WIDTH, BAND + 54.0)
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _process(_delta: float) -> void:
	if player == null or not is_instance_valid(player) or player.camera == null or not player.camera.is_inside_tree():
		return
	var fwd := -player.camera.global_basis.z
	var h := rad_to_deg(atan2(fwd.x, -fwd.z))  # 0 north (-z), 90 east (+x)
	var z := World.zone_of(player)
	if z != _exits_zone:
		_exits_zone = z
		_exits.clear()
		_zone_name = z.zone_name if z != null else ""
		var lv: Array = z.data.get("levels", []) if z != null else []
		_levels = "Levels %d \u2013 %d" % [int(lv[0]), int(lv[1])] if lv.size() == 2 else ""
		if z != null:
			for zl: Dictionary in z.data.get("zone_lines", []):
				var to := str(zl.get("to", ""))
				var name := to.capitalize()
				var path := "res://data/zones/%s.json" % to
				if FileAccess.file_exists(path):
					var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
					if parsed is Dictionary:
						name = str((parsed as Dictionary).get("name", name))
				_exits.append([Vector2(float(zl["pos"][0]), float(zl["pos"][1])), name])
	if absf(wrapf(h - _heading, -180.0, 180.0)) > 0.05 or Engine.get_process_frames() % 10 == 0:
		_heading = h
		queue_redraw()


## Where a compass bearing sits on the strip (x), and how visible it is there.
func _place(bearing: float) -> Vector2:
	var rel := wrapf(bearing - _heading, -180.0, 180.0)
	var x := WIDTH * 0.5 + rel / SPAN * WIDTH * 0.5
	var fade := clampf(1.0 - pow(absf(rel) / SPAN, 3.0), 0.0, 1.0)
	return Vector2(x, fade if absf(rel) <= SPAN else 0.0)


func _bearing_to(at: Vector3) -> float:
	var d := at - player.global_position
	return rad_to_deg(atan2(d.x, -d.z))


func _draw() -> void:
	if player == null:
		return
	var font := get_theme_default_font()
	var mid := WIDTH * 0.5
	# the band: dark glass fading out at both ends, gold hairlines above and below (one smooth gradient)
	var pts := PackedVector2Array()
	var cols := PackedColorArray()
	var lines_top := PackedVector2Array()
	var steps := 32
	for i in steps + 1:
		var x := WIDTH * i / steps
		var a := clampf(1.0 - pow(absf(x - mid) / mid, 2.2), 0.0, 1.0)
		pts.append(Vector2(x, 0))
		cols.append(Color(INK, 0.86 * a))
		lines_top.append(Vector2(x, a))
	for i in range(steps, -1, -1):
		var x := WIDTH * i / steps
		var a := clampf(1.0 - pow(absf(x - mid) / mid, 2.2), 0.0, 1.0)
		pts.append(Vector2(x, BAND))
		cols.append(Color(INK, 0.86 * a))
	draw_polygon(pts, cols)
	for i in steps:
		var c0 := Color(GOLD, 0.9 * lines_top[i].y)
		var c1 := Color(GOLD, 0.9 * lines_top[i + 1].y)
		var x0 := lines_top[i].x
		var x1 := lines_top[i + 1].x
		draw_polyline_colors(PackedVector2Array([Vector2(x0, 0), Vector2(x1, 0)]), PackedColorArray([c0, c1]), 1.0)
		draw_polyline_colors(PackedVector2Array([Vector2(x0, BAND), Vector2(x1, BAND)]), PackedColorArray([c0, c1]), 1.0)
	# ticks and headings
	var names := {0: "N", 45: "NE", 90: "E", 135: "SE", 180: "S", 225: "SW", 270: "W", 315: "NW"}
	for deg in range(0, 360, 15):
		var at := _place(deg)
		if at.y <= 0.0:
			continue
		if names.has(deg):
			var label: String = names[deg]
			var cardinal := label.length() == 1
			var size := 17 if cardinal else 11
			var col := (EMBER if deg == 0 else GOLD) if cardinal else Color(0.8, 0.76, 0.66)
			var w := font.get_string_size(label, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
			var y := BAND * 0.5 + size * 0.36
			draw_string_outline(font, Vector2(at.x - w * 0.5, y), label, HORIZONTAL_ALIGNMENT_LEFT, -1, size, 4, Color(0, 0, 0, 0.8 * at.y))
			draw_string(font, Vector2(at.x - w * 0.5, y), label, HORIZONTAL_ALIGNMENT_LEFT, -1, size, Color(col, at.y))
		else:
			draw_line(Vector2(at.x, BAND - 7), Vector2(at.x, BAND - 2), Color(GOLD, 0.55 * at.y), 1.0)
			draw_line(Vector2(at.x, 2), Vector2(at.x, 5), Color(GOLD, 0.35 * at.y), 1.0)
	# the sun or the moon, where they are
	var sky := _sky_mark()
	if not sky.is_empty():
		var at := _place(float(sky[0]))
		if at.y > 0.0:
			var sun: bool = sky[1]
			var c := Vector2(at.x, 7)
			if sun:
				draw_circle(c, 4.5, Color(1.0, 0.85, 0.4, at.y))
				for k in 8:
					var dir := Vector2.from_angle(k * TAU / 8)
					draw_line(c + dir * 6.0, c + dir * 8.5, Color(1.0, 0.8, 0.35, 0.8 * at.y), 1.2)
			else:
				draw_circle(c, 4.5, Color(0.82, 0.86, 0.95, at.y))
				draw_circle(c + Vector2(2.2, -1.2), 3.8, Color(INK, at.y))
	# the zone's exits: a gold diamond, named when it's near straight ahead
	for ex: Array in _exits:
		var at := _place(_bearing_to(Vector3((ex[0] as Vector2).x, 0, (ex[0] as Vector2).y)))
		if at.y <= 0.0:
			continue
		var c := Vector2(at.x, BAND - 7)
		draw_colored_polygon(PackedVector2Array([c + Vector2(0, -5), c + Vector2(4, 0), c + Vector2(0, 5), c + Vector2(-4, 0)]), Color(GOLD, at.y))
		if absf(at.x - mid) < 40.0:
			var n: String = ex[1]
			var w := font.get_string_size(n, HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x
			var fade := 1.0 - absf(at.x - mid) / 40.0
			draw_string_outline(font, Vector2(at.x - w * 0.5, BAND + 15), n, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, 3, Color(0, 0, 0, 0.9 * fade))
			draw_string(font, Vector2(at.x - w * 0.5, BAND + 15), n, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, Color(GOLD, 0.95 * fade))
	# your pet (green) and your target (its con color), as pips on the strip
	var pet := World.get_object(player.pet_id) as Entity if player.pet_id >= 0 else null
	if pet != null and not pet.dead:
		var at := _place(_bearing_to(pet.global_position))
		if at.y > 0.0:
			draw_circle(Vector2(at.x, BAND - 5), 3.5, Color(0.45, 0.95, 0.5, at.y))
	var t := player.valid_target_entity()
	if t != null and t != player:
		var at := _place(_bearing_to(t.global_position))
		if at.y > 0.0:
			var col: Color = World.CON_COLORS[World.con_of(player.level, t.level)] if t is Mob else Color(0.55, 0.85, 1.0)
			var c := Vector2(at.x, 5)
			draw_colored_polygon(PackedVector2Array([c + Vector2(-5, -3), c + Vector2(5, -3), c + Vector2(0, 5)]), Color(col, at.y))
	# straight ahead: a gold notch top and bottom
	draw_colored_polygon(PackedVector2Array([Vector2(mid - 6, -4), Vector2(mid + 6, -4), Vector2(mid, 4)]), GOLD)
	draw_colored_polygon(PackedVector2Array([Vector2(mid - 5, BAND + 4), Vector2(mid + 5, BAND + 4), Vector2(mid, BAND - 3)]), Color(GOLD, 0.8))
	# the zone's name on a ribbon beneath
	if _zone_name != "":
		var size := 15
		var w := font.get_string_size(_zone_name, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
		var y := BAND + 36
		var half := w * 0.5 + 16.0
		for side: float in [-1.0, 1.0]:  # hairlines running out from the name, with a diamond at the end
			var from := mid + side * (half + 2.0)
			var to := mid + side * (half + 46.0)
			draw_line(Vector2(from, y - 5), Vector2(to, y - 5), Color(GOLD, 0.7), 1.0)
			var d := Vector2(to + side * 4.0, y - 5)
			draw_colored_polygon(PackedVector2Array([d + Vector2(0, -3), d + Vector2(3, 0), d + Vector2(0, 3), d + Vector2(-3, 0)]), Color(GOLD, 0.8))
		draw_string_outline(font, Vector2(mid - w * 0.5, y), _zone_name, HORIZONTAL_ALIGNMENT_LEFT, -1, size, 5, Color(0, 0, 0, 0.9))
		draw_string(font, Vector2(mid - w * 0.5, y), _zone_name, HORIZONTAL_ALIGNMENT_LEFT, -1, size, Color(0.95, 0.88, 0.7))
		if _levels != "":
			var lw := font.get_string_size(_levels, HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x
			draw_string_outline(font, Vector2(mid - lw * 0.5, y + 15), _levels, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, 4, Color(0, 0, 0, 0.85))
			draw_string(font, Vector2(mid - lw * 0.5, y + 15), _levels, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, _level_color())


## The levels in gold when the zone suits you, dimmer when you've outgrown
## it, reddish when it's still above you.
func _level_color() -> Color:
	var z := World.zone_of(player)
	var lv: Array = z.data.get("levels", []) if z != null else []
	if lv.size() != 2 or player.level > int(lv[1]):
		return Color(0.7, 0.68, 0.62)
	if player.level < int(lv[0]):
		return Color(1.0, 0.55, 0.42)
	return GOLD


## The sun's (or, at night, the moon's) compass bearing, and which it is; [] indoors.
func _sky_mark() -> Array:
	var z := World.zone_of(player)
	if z == null or bool(z.data.get("interior", false)):
		return []
	var dn := z.find_children("*", "DayNight", true, false)
	if dn.is_empty():
		return []
	var cycle := dn[0] as DayNight
	for pair: Array in [[cycle.sun, true], [cycle.moon, false]]:
		var light := pair[0] as DirectionalLight3D
		if light == null or not light.visible or light.light_energy <= 0.05:
			continue
		var to_sky := light.global_basis.z  # a light shines along -z: the sky is the other way
		if to_sky.y > 0.0:
			return [rad_to_deg(atan2(to_sky.x, -to_sky.z)), pair[1]]
	return []
