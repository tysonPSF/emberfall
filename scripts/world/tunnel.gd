class_name Tunnel
extends RefCounted
## A cave zone's shape ("tunnel" in data/zones/<id>.json): passages you walk
## through solid rock, built on the zone's ordinary height field so rivers,
## lakes, navigation and spawns all work as they do outdoors.
##
##   "tunnel": {
##     "paths": [{"points": [[x, z, width], ...]}, ...],  the first is the main way
##                through; the others are side passages (their floor starts at
##                the height of wherever on an earlier path they branch from)
##     "rooms": [{"pos": [x, z], "radius": r}],  round chambers on a path
##     "rise": 0.02,   how much the floor climbs per meter along a path
##     "wall": 18      how high the walls stand above the floor
##   }
##
## Inside a passage the ground is its floor; past its edge the walls climb
## steeply into rock. A ceiling (ceiling_at) closes over every passage at a
## height that grows with its width, lower near the walls like a vault.
## Everything is worked out once onto a grid (CELL m) and read back bilinearly.

const CELL := 1.0
const MARGIN := 10.0  # how far past a passage's edge the grid knows its floor

var wall := 18.0
var _n := 0
var _half := 0.0
var _clear := PackedFloat32Array()  # meters past the nearest passage's edge (negative inside)
var _floor := PackedFloat32Array()  # that passage's floor
var _head := PackedFloat32Array()  # its headroom
var paths: Array = []  # [{points: Array[Vector2], widths: Array[float], floors: Array[float]}]
var rooms: Array = []  # [{pos: Vector2, radius, floor}]


func _init(spec: Dictionary, zone_size: float) -> void:
	wall = float(spec.get("wall", 18.0))
	var rise := float(spec.get("rise", 0.02))
	for path: Dictionary in spec.get("paths", []):
		var pts: Array[Vector2] = []
		var widths: Array[float] = []
		for pt: Array in path["points"]:
			pts.append(Vector2(pt[0], pt[1]))
			widths.append(float(pt[2]) if pt.size() > 2 else 6.0)
		var start := 0.0
		if not paths.is_empty():
			start = _floor_along(pts[0])  # a side passage starts level with where it leaves
		var floors: Array[float] = [start]
		for i in range(1, pts.size()):
			floors.append(floors[i - 1] + pts[i - 1].distance_to(pts[i]) * rise)
		paths.append({"points": pts, "widths": widths, "floors": floors})
	for room: Dictionary in spec.get("rooms", []):
		var at := Vector2(room["pos"][0], room["pos"][1])
		rooms.append({"pos": at, "radius": float(room["radius"]), "floor": float(room.get("floor", _floor_along(at)))})
	_half = zone_size * 0.5
	_n = int(zone_size / CELL) + 1
	_clear.resize(_n * _n)
	_clear.fill(99.0)
	_floor.resize(_n * _n)
	_head.resize(_n * _n)
	_head.fill(8.0)
	for path: Dictionary in paths:
		var pts: Array[Vector2] = path["points"]
		for i in pts.size() - 1:
			_stamp_segment(pts[i], pts[i + 1], path["widths"][i] * 0.5, path["widths"][i + 1] * 0.5, path["floors"][i], path["floors"][i + 1])
	for room: Dictionary in rooms:
		_stamp_segment(room["pos"], room["pos"], room["radius"], room["radius"], room["floor"], room["floor"])


## Headroom for a passage this wide: tall chambers, low crawls.
static func headroom(half_width: float) -> float:
	return clampf(half_width * 1.5 + 2.5, 5.5, 18.0)


## The floor of the nearest point on the paths built so far.
func _floor_along(p: Vector2) -> float:
	var best := INF
	var out := 0.0
	for path: Dictionary in paths:
		var pts: Array[Vector2] = path["points"]
		for i in pts.size() - 1:
			var seg := pts[i + 1] - pts[i]
			var t := clampf((p - pts[i]).dot(seg) / seg.length_squared(), 0.0, 1.0)
			var d := p.distance_to(pts[i] + seg * t)
			if d < best:
				best = d
				out = lerpf(path["floors"][i], path["floors"][i + 1], t)
	return out


func _stamp_segment(a: Vector2, b: Vector2, ha: float, hb: float, fa: float, fb: float) -> void:
	var reach := maxf(ha, hb) + MARGIN
	var lo := Vector2(minf(a.x, b.x), minf(a.y, b.y)) - Vector2.ONE * reach
	var hi := Vector2(maxf(a.x, b.x), maxf(a.y, b.y)) + Vector2.ONE * reach
	var i0 := maxi(0, int((lo.x + _half) / CELL))
	var i1 := mini(_n - 1, int((hi.x + _half) / CELL) + 1)
	var j0 := maxi(0, int((lo.y + _half) / CELL))
	var j1 := mini(_n - 1, int((hi.y + _half) / CELL) + 1)
	var seg := b - a
	var len2 := seg.length_squared()
	for j in range(j0, j1 + 1):
		for i in range(i0, i1 + 1):
			var p := Vector2(-_half + i * CELL, -_half + j * CELL)
			var t := clampf((p - a).dot(seg) / len2, 0.0, 1.0) if len2 > 0.0001 else 0.0
			var hw := lerpf(ha, hb, t)
			var clear := p.distance_to(a + seg * t) - hw
			var k := j * _n + i
			if clear < _clear[k]:
				_clear[k] = clear
				_floor[k] = lerpf(fa, fb, t)
				_head[k] = headroom(hw)


## [clearance past the nearest passage's edge, its floor, its headroom] at x, z.
func sample(x: float, z: float) -> Vector3:
	var fx := clampf((x + _half) / CELL, 0.0, _n - 1.001)
	var fz := clampf((z + _half) / CELL, 0.0, _n - 1.001)
	var i := int(fx)
	var j := int(fz)
	var tx := fx - i
	var tz := fz - j
	var k := j * _n + i
	return Vector3(_bi(_clear, k, tx, tz), _bi(_floor, k, tx, tz), _bi(_head, k, tx, tz))


func _bi(arr: PackedFloat32Array, k: int, tx: float, tz: float) -> float:
	return lerpf(lerpf(arr[k], arr[k + 1], tx), lerpf(arr[k + _n], arr[k + _n + 1], tx), tz)


## The rock at x, z: the passage floor inside, climbing walls outside.
## `wobble` roughens the walls' line (from the zone's noise).
func height(x: float, z: float, wobble: float, detail: float) -> float:
	var s := sample(x, z)
	var clear := s.x + wobble * 1.3
	if clear <= 0.0:
		return s.y + detail * 0.12 + 0.3 * smoothstep(-2.0, 0.0, clear)
	return s.y + wall * smoothstep(0.0, 3.5, clear) + clear * 0.8 + detail * 0.9


## The ceiling over x, z: flat over the middle of a passage, coming down
## toward its walls, with lumps where stalactites grow.
func ceiling_at(x: float, z: float, detail: float) -> float:
	var s := sample(x, z)
	return s.y + s.z - maxf(0.0, s.x + 2.5) * 0.9 - absf(detail) * 0.8


## Whether x, z is open passage (not in the walls), with this much room to spare.
func inside(x: float, z: float, spare := 0.0) -> bool:
	return sample(x, z).x < -spare


## Points spaced along every path (and round each room): for dressing the cave.
func walk(step: float) -> Array:
	var out: Array = []  # [point, direction, half width]
	for path: Dictionary in paths:
		var pts: Array[Vector2] = path["points"]
		for i in pts.size() - 1:
			var n := maxi(1, int(pts[i].distance_to(pts[i + 1]) / step))
			for k in n:
				var t := float(k) / n
				out.append([pts[i].lerp(pts[i + 1], t), (pts[i + 1] - pts[i]).normalized(), lerpf(path["widths"][i], path["widths"][i + 1], t) * 0.5])
	for room: Dictionary in rooms:
		var r: float = room["radius"]
		for k in int(TAU * r / step):
			var a := k * step / r
			out.append([room["pos"] + Vector2.from_angle(a) * r * 0.5, Vector2.from_angle(a + PI / 2.0), r * 0.5])
	return out
