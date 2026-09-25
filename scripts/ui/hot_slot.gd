class_name HotSlot
extends Button
## One square hotbar button, EverQuest style: an icon on a gem colored by what
## it does, its key in the corner, a sweep that darkens it until it's ready,
## a dimmed look when it can't be used right now (no mana, no target, out of
## range), and a glow while a toggle is on (auto attack, sitting). The name
## is in the tooltip. Everything is drawn here; the HUD only sets the fields.

const SIZE := 48.0
const GEMS := {
	"damage": Color(0.72, 0.24, 0.2), "heal": Color(0.26, 0.62, 0.3), "buff": Color(0.28, 0.44, 0.8),
	"utility": Color(0.52, 0.38, 0.74), "ability": Color(0.62, 0.46, 0.24), "action": Color(0.34, 0.33, 0.31),
}

var key_text := ""
var count_text := ""  # a number in the bottom corner (arrows left, say)
var picture: Texture2D
var fallback := ""  # drawn when there's no picture: the name's initials
var gem := GEMS["action"]
var sweep := 0.0  # share of the recast still to wait, 0..1
var seconds := 0.0  # recast left, shown while sweeping
var usable := true
var lit := false
var lit_color := Color(1.0, 0.32, 0.25)


func _init() -> void:
	custom_minimum_size = Vector2(SIZE, SIZE)
	focus_mode = Control.FOCUS_NONE
	flat = true
	mouse_entered.connect(queue_redraw)
	mouse_exited.connect(queue_redraw)


## Sets the fields and redraws only when something changed.
func show_state(new_sweep: float, new_seconds: float, new_usable: bool, new_lit: bool) -> void:
	new_seconds = ceilf(new_seconds * 10.0) / 10.0
	if is_equal_approx(new_sweep, sweep) and is_equal_approx(new_seconds, seconds) and new_usable == usable and new_lit == lit:
		return
	sweep = new_sweep
	seconds = new_seconds
	usable = new_usable
	lit = new_lit
	queue_redraw()


func _draw() -> void:
	var r := Rect2(Vector2.ZERO, size)
	var face := StyleBoxFlat.new()
	face.set_corner_radius_all(6)
	face.bg_color = gem.darkened(0.45) if usable else gem.darkened(0.62).lerp(Color(0.2, 0.2, 0.2), 0.5)
	face.border_color = lit_color if lit else (UIKit.GOLD if is_hovered() else Color(0, 0, 0, 0.7))
	face.set_border_width_all(2 if lit or is_hovered() else 1)
	draw_style_box(face, r)
	var shine := StyleBoxFlat.new()  # a soft highlight on the gem's upper half
	shine.set_corner_radius_all(5)
	shine.bg_color = Color(1, 1, 1, 0.07)
	draw_style_box(shine, Rect2(Vector2(3, 3), Vector2(size.x - 6, size.y * 0.45)))
	var tint := Color.WHITE if usable else Color(0.62, 0.62, 0.62, 0.85)
	var inner := r.grow(-4)
	var font := get_theme_default_font()
	if picture != null:
		draw_texture_rect(picture, inner, false, tint)
	elif fallback != "":
		draw_string(font, Vector2(0, size.y * 0.62), fallback, HORIZONTAL_ALIGNMENT_CENTER, size.x, 15, tint)
	if sweep > 0.0:
		var c := size * 0.5
		var pts := PackedVector2Array([c])
		var steps := 24
		for k in steps + 1:  # clockwise from the top, covering what's left to wait
			var a := -PI / 2.0 + TAU * (1.0 - sweep) + TAU * sweep * k / steps
			pts.append(c + Vector2.from_angle(a) * size.x)
		var clip := PackedVector2Array()
		for q in pts:
			clip.append(Vector2(clampf(q.x, 2, size.x - 2), clampf(q.y, 2, size.y - 2)))
		draw_colored_polygon(clip, Color(0, 0, 0, 0.62))
		if seconds > 0.0:
			var t := ("%.1f" % seconds) if seconds < 10.0 else str(ceili(seconds))
			draw_string_outline(font, Vector2(0, size.y * 0.62), t, HORIZONTAL_ALIGNMENT_CENTER, size.x, 15, 4, Color(0, 0, 0, 0.9))
			draw_string(font, Vector2(0, size.y * 0.62), t, HORIZONTAL_ALIGNMENT_CENTER, size.x, 15, Color(1, 0.95, 0.8))
	if count_text != "":
		draw_string_outline(font, Vector2(0, size.y - 4), count_text, HORIZONTAL_ALIGNMENT_RIGHT, size.x - 4, 12, 3, Color(0, 0, 0, 0.9))
		draw_string(font, Vector2(0, size.y - 4), count_text, HORIZONTAL_ALIGNMENT_RIGHT, size.x - 4, 12, Color(1, 1, 1))
	if key_text != "":
		draw_string_outline(font, Vector2(4, 13), key_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, 3, Color(0, 0, 0, 0.9))
		draw_string(font, Vector2(4, 13), key_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UIKit.GOLD)
	if lit:
		var glow := StyleBoxFlat.new()
		glow.set_corner_radius_all(6)
		glow.bg_color = Color(lit_color, 0.14)
		draw_style_box(glow, r)
