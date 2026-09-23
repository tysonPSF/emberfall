class_name TargetMarker
extends Decal
## Rune circle under the local player's target, tinted by con color. It is a
## decal, so it hugs slopes and skips character meshes (Layers.RENDER_ENTITIES).
## Client-side only: it reads state, never changes it.

const TEX_SIZE := 384
const SLOTS := 16  # rune glyphs around the band
const SPIN := 0.35  # radians per second
const FRIEND_COLOR := Color(0.55, 0.8, 1.0)
const CORPSE_COLOR := Color(0.6, 0.6, 0.6)

static var _texture: ImageTexture

var player: Player
var _time := 0.0


func _ready() -> void:
	texture_albedo = rune_texture()
	texture_emission = texture_albedo
	emission_energy = 1.6
	albedo_mix = 1.0
	upper_fade = 0.25
	lower_fade = 0.25
	cull_mask = 0xFFFFF & ~Layers.RENDER_ENTITIES
	visible = false


func _process(delta: float) -> void:
	var t: Node3D = player.target if player != null and is_instance_valid(player.target) else null
	if t == null or t == player and player.dead:
		visible = false
		return
	visible = true
	_time += delta
	global_position = t.global_position + Vector3.UP * 0.35
	rotation.y = wrapf(_time * SPIN, 0.0, TAU)
	var d := 1.4
	var color := CORPSE_COLOR
	if t is Entity:
		var e := t as Entity
		var low_and_long := str(e.look.get("shape", "")) == "beetle"  # rats and beetles: size by footprint
		d = clampf(2.4 * float(e.look.get("scale", 1.0)) if low_and_long else e.body_height + 0.4, 1.3, 3.6)
		if e is Mob:
			color = World.CON_COLORS[World.con_of(player.level, e.level)]
		else:
			color = FRIEND_COLOR
		if e.dead:
			color = CORPSE_COLOR
	size = Vector3(d, 1.2, d)
	color.a = 0.8 + 0.2 * sin(_time * 3.0)
	modulate = color


## White rune ring on transparent, drawn once: a bold outer band, a thin inner
## ring, and a glyph in each slot between them. The decal tints it.
static func rune_texture() -> ImageTexture:
	if _texture != null:
		return _texture
	var img := Image.create(TEX_SIZE, TEX_SIZE, false, Image.FORMAT_RGBA8)
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	# each glyph: a few strokes in slot-local coords (x across the slot, y outward), both in -1..1
	var shapes := [
		[[Vector2(0, -1), Vector2(0, 1)], [Vector2(0, 0.2), Vector2(0.7, 0.9)]],
		[[Vector2(-0.6, -1), Vector2(0, 1)], [Vector2(0, 1), Vector2(0.6, -1)]],
		[[Vector2(0, -1), Vector2(0, 1)], [Vector2(0, 1), Vector2(0.7, 0.4)], [Vector2(0.7, 0.4), Vector2(0, -0.1)]],
		[[Vector2(-0.6, 1), Vector2(0.6, -1)], [Vector2(-0.6, -1), Vector2(0.6, 1)]],
		[[Vector2(0, -1), Vector2(0, 1)], [Vector2(-0.6, 0.5), Vector2(0.6, 0.5)]],
		[[Vector2(-0.5, -1), Vector2(-0.5, 1)], [Vector2(-0.5, 0), Vector2(0.6, 0.8)], [Vector2(-0.5, 0), Vector2(0.6, -0.8)]],
	]
	var glyphs: Array = []
	for k in SLOTS:
		glyphs.append(shapes[rng.randi() % shapes.size()])
	var half := TEX_SIZE / 2.0
	for py in TEX_SIZE:
		for px in TEX_SIZE:
			var p := (Vector2(px, py) + Vector2(0.5, 0.5) - Vector2(half, half)) / half
			var r := p.length()
			var a := 0.0
			a = maxf(a, _band(r, 0.9, 0.97))
			a = maxf(a, _band(r, 0.68, 0.705))
			a = maxf(a, _band(r, 0.3, 0.315) * 0.6)
			if r > 0.72 and r < 0.88:
				var ang := fposmod(atan2(p.y, p.x), TAU)
				var slot := int(ang / TAU * SLOTS)
				var mid := (slot + 0.5) * TAU / SLOTS
				# slot-local coords: x along the arc, y along the radius
				var local := Vector2(angle_difference(mid, ang) * 0.8 / (TAU / SLOTS) * 2.0, (r - 0.8) / 0.065)
				for stroke: Array in glyphs[slot]:
					var dist := _seg_dist(local, stroke[0], stroke[1])
					a = maxf(a, 1.0 - smoothstep(0.12, 0.26, dist))
			img.set_pixel(px, py, Color(a, a, a, a))  # rgb too: emission ignores alpha
	_texture = ImageTexture.create_from_image(img)
	return _texture


## 1 inside [lo, hi] with soft edges, 0 outside.
static func _band(r: float, lo: float, hi: float) -> float:
	var e := 2.0 / TEX_SIZE
	return smoothstep(lo - e, lo + e, r) * (1.0 - smoothstep(hi - e, hi + e, r))


static func _seg_dist(p: Vector2, a: Vector2, b: Vector2) -> float:
	var ab := b - a
	var t := clampf((p - a).dot(ab) / ab.length_squared(), 0.0, 1.0)
	return p.distance_to(a + ab * t)
