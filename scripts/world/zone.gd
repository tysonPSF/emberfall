class_name Zone
extends Node3D
## Builds a zone from data/zones/<id>.json: sky, terrain, props, landmarks,
## and spawn points. The terrain is generated from a seeded noise function,
## so the same zone file always produces the same world.

const GRID := 128
const CLUTTER_CHUNK := 32.0
const CLUTTER_SHADER := preload("res://scripts/world/clutter.gdshader")
const WATER_SHADER := preload("res://scripts/world/water.gdshader")

var zone_id := ""
var data: Dictionary = {}
var zone_name := ""
var size := 384.0
var half := 192.0
var amp := 10.0
var flat_radius := 26.0
var bind_point := Vector3.ZERO

var _noise := FastNoiseLite.new()
var _detail := FastNoiseLite.new()
var _rng := RandomNumberGenerator.new()
var _bind_xz := Vector2.ZERO
var _flat_spots: Array[Vector2] = []
var _passes: Array = []  # [x, z, half-width]: gaps in the mountain ring
var _roads: Array = []  # [{points: [Vector2...], width}]
var _ponds: Array = []  # [{center: Vector2, radius, depth, level}]: bowls carved into the ground
var _clear_radius := 0.0  # no scattered trees or rocks inside this (city walls)
var _prop_scenes: Dictionary = {}  # prop id -> PackedScene
var _prop_aabbs: Dictionary = {}  # prop id -> unscaled AABB
var _prop_tris: Dictionary = {}  # prop id -> unscaled collision faces


func load_zone(id: String) -> void:
	zone_id = id
	data = GameData.load_zone(id)
	if Net.mode != "server":
		Music.play_zone(data, id)
	zone_name = data.get("name", id)
	size = float(data.get("size", 384))
	half = size * 0.5
	amp = float(data.get("height_amplitude", 10))
	flat_radius = float(data.get("flat_radius", 26))
	var zone_seed := int(data.get("seed", 1))
	_noise.seed = zone_seed
	_noise.frequency = 0.006
	_noise.fractal_octaves = 4
	_detail.seed = zone_seed + 1
	_detail.frequency = 0.05
	_rng.seed = zone_seed
	var bp: Array = data.get("bind_point", [0, 0])
	_bind_xz = Vector2(bp[0], bp[1])
	for lm: Dictionary in data.get("landmarks", []):
		var spot := Vector2(lm["pos"][0], lm["pos"][1])
		_flat_spots.append(spot)
		if lm["type"] == "pond":
			# the landmark flattens the ground to this height; the water sits a little below it
			var flat := _noise.get_noise_2d(spot.x, spot.y) * amp * 0.5
			_ponds.append({"center": spot, "radius": float(lm.get("radius", 12)), "depth": float(lm.get("depth", 1.6)), "level": flat - 0.25})
	for ps: Array in data.get("passes", []):
		_passes.append([float(ps[0]), float(ps[1]), float(ps[2]) if ps.size() > 2 else 9.0])
	for road: Dictionary in data.get("roads", []):
		var pts: Array[Vector2] = []
		for pt: Array in road["points"]:
			pts.append(Vector2(pt[0], pt[1]))
		_roads.append({"points": pts, "width": float(road.get("width", 3.0))})
	_clear_radius = float(data.get("clear_radius", 0.0))
	bind_point = ground(_bind_xz.x, _bind_xz.y + 4.0)  # just south of the obelisk
	World.zone = self

	_build_environment()
	_build_terrain()
	_build_landmarks()
	_build_props()
	if DisplayServer.get_name() != "headless":  # a dedicated server draws nothing
		_build_clutter()
	_build_road_lamps()
	if Net.is_authority():  # a client's mobs and npcs come from the server
		_build_spawns()
		_build_npcs()
		_build_zone_lines()


func height_at(x: float, z: float) -> float:
	var h := _noise.get_noise_2d(x, z) * amp + _detail.get_noise_2d(x, z) * 0.35
	h = lerpf(h * 0.1, h, smoothstep(flat_radius, flat_radius + 25.0, Vector2(x, z).distance_to(_bind_xz)))
	for spot in _flat_spots:
		var d := Vector2(x, z).distance_to(spot)
		if d < 30.0:
			h = lerpf(_noise.get_noise_2d(spot.x, spot.y) * amp * 0.5, h, smoothstep(14.0, 30.0, d))
	for pond: Dictionary in _ponds:
		var d := Vector2(x, z).distance_to(pond["center"])
		var r: float = pond["radius"]
		h -= float(pond["depth"]) * (1.0 - smoothstep(r * 0.25, r + 1.5, d))
	# Mountains ring the zone so you can't walk off the edge.
	var edge := maxf(absf(x), absf(z)) - (half - 28.0)
	if edge > 0.0:
		h += (edge * 1.3 + edge * edge * 0.08) * _pass_factor(x, z)
	return h


## 0 inside a mountain pass, 1 where the ring of mountains stands. A pass on
## the north or south edge is a gap in x; on the east or west edge, in z.
func _pass_factor(x: float, z: float) -> float:
	var f := 1.0
	for ps: Array in _passes:
		var across := absf(x - ps[0]) if absf(ps[1]) >= absf(ps[0]) else absf(z - ps[1])
		f = minf(f, smoothstep(ps[2], ps[2] + 14.0, across))
	return f


## Distance from a point to the nearest road's centerline, minus its half width.
func road_distance(x: float, z: float) -> float:
	var best := INF
	var p := Vector2(x, z)
	for road: Dictionary in _roads:
		var pts: Array[Vector2] = road["points"]
		for i in pts.size() - 1:
			var closest := Geometry2D.get_closest_point_to_segment(p, pts[i], pts[i + 1])
			best = minf(best, p.distance_to(closest) - float(road["width"]) * 0.5)
	return best


func ground(x: float, z: float) -> Vector3:
	return Vector3(x, height_at(x, z), z)


func add_player(p: Player, pos: Vector3) -> void:
	p.position = pos
	add_child(p)


func player_corpses_for(owner: String) -> Array:
	var out: Array = []
	for child in get_children():
		if child is Corpse and (child as Corpse).owner_name == owner:
			out.append((child as Corpse).to_save())
	return out


func restore_corpses(saved: Array) -> void:
	for d: Dictionary in saved:
		var c := Corpse.new()
		var owner := str(d["owner"])
		c.setup(owner, d.get("look", {}), d["entries"], int(d["coin"]), float(d["decay_left"]), owner, true)
		c.position = Vector3(d["position"][0], d["position"][1], d["position"][2])
		add_child(c)


# --- builders ---------------------------------------------------------------

func _build_environment() -> void:
	# Interiors get no sky and no sun: lit warm and close, so the only light in
	# the room is the light the room itself carries.
	if bool(data.get("interior", false)):
		var ienv := Environment.new()
		ienv.background_mode = Environment.BG_COLOR
		ienv.background_color = Color(0.03, 0.025, 0.02)
		ienv.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
		ienv.ambient_light_color = Color(0.62, 0.58, 0.54)
		ienv.ambient_light_energy = 0.34
		ienv.tonemap_mode = Environment.TONE_MAPPER_FILMIC
		ienv.fog_enabled = true
		ienv.fog_light_color = Color(0.1, 0.07, 0.05)
		ienv.fog_density = 0.022
		var iwe := WorldEnvironment.new()
		iwe.environment = ienv
		add_child(iwe)
		return

	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.32, 0.5, 0.8)
	sky_mat.sky_horizon_color = Color(0.72, 0.78, 0.84)
	sky_mat.ground_horizon_color = Color(0.72, 0.78, 0.84)
	sky_mat.ground_bottom_color = Color(0.3, 0.32, 0.3)
	var sky := Sky.new()
	sky.sky_material = sky_mat
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.7
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.fog_enabled = true
	env.fog_light_color = Color(0.7, 0.76, 0.82)
	env.fog_density = 0.006
	env.fog_sky_affect = 0.25
	var world_env := WorldEnvironment.new()
	world_env.environment = env
	add_child(world_env)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50.0, -35.0, 0.0)
	sun.light_energy = 1.1
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 110.0
	add_child(sun)


func _build_terrain() -> void:
	var n := GRID + 1
	var cell := size / GRID
	var heights := PackedFloat32Array()
	heights.resize(n * n)
	for j in n:
		for i in n:
			heights[j * n + i] = height_at(-half + i * cell, -half + j * cell)

	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for j in GRID:
		for i in GRID:
			for c: Vector2i in [Vector2i(0, 0), Vector2i(1, 0), Vector2i(0, 1), Vector2i(1, 0), Vector2i(1, 1), Vector2i(0, 1)]:
				var ii := i + c.x
				var jj := j + c.y
				var x := -half + ii * cell
				var z := -half + jj * cell
				var h := heights[jj * n + ii]
				st.set_color(_ground_color(x, z, h))
				st.add_vertex(Vector3(x, h, z))
	st.index()
	st.generate_normals()
	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.vertex_color_is_srgb = true
	mat.roughness = 1.0
	st.set_material(mat)
	var mesh_instance := MeshInstance3D.new()
	mesh_instance.mesh = st.commit()
	add_child(mesh_instance)

	# Physics heightmap: 1 unit spacing, so scale uniformly by the cell size.
	var scaled := PackedFloat32Array()
	scaled.resize(n * n)
	for k in n * n:
		scaled[k] = heights[k] / cell
	var shape := HeightMapShape3D.new()
	shape.map_width = n
	shape.map_depth = n
	shape.map_data = scaled
	var body := StaticBody3D.new()
	body.collision_layer = Layers.WORLD
	body.collision_mask = 0
	var cs := CollisionShape3D.new()
	cs.shape = shape
	cs.scale = Vector3.ONE * cell
	body.add_child(cs)
	add_child(body)


func _ground_color(x: float, z: float, h: float) -> Color:
	var n := _detail.get_noise_2d(x * 0.6, z * 0.6) * 0.5 + 0.5
	var c := Color(0.27, 0.4, 0.17).lerp(Color(0.4, 0.52, 0.22), n)
	var d := Vector2(x, z).distance_to(_bind_xz)
	if d < flat_radius:
		c = c.lerp(Color(0.45, 0.38, 0.26), 0.55 * (1.0 - d / flat_radius))
	var tint: Dictionary = data.get("ground_tint", {})
	if not tint.is_empty():
		var inside := 1.0 - smoothstep(float(tint["radius"]) - 4.0, float(tint["radius"]) + 4.0, Vector2(x, z).length())
		c = c.lerp(Color.html(tint["color"]), inside * float(tint.get("amount", 0.5)) * (0.75 + 0.5 * n))
	for pond: Dictionary in _ponds:
		var pd := Vector2(x, z).distance_to(pond["center"])
		var r: float = pond["radius"]
		c = c.lerp(Color(0.42, 0.36, 0.24), 1.0 - smoothstep(r - 1.5, r + 2.0, pd))  # muddy bank
		c = c.lerp(Color(0.22, 0.21, 0.15), 1.0 - smoothstep(r * 0.4, r - 1.0, pd))  # silt on the bottom
	var road := road_distance(x, z)
	if road < 1.5:
		c = c.lerp(Color(0.46, 0.38, 0.27), clampf(1.0 - road / 1.5, 0.0, 1.0) * 0.85)
	var edge := (maxf(absf(x), absf(z)) - (half - 30.0)) * _pass_factor(x, z)
	if edge > 0.0 or h > amp * 1.2:
		c = c.lerp(Color(0.44, 0.42, 0.4), clampf(maxf(edge / 10.0, (h - amp * 1.2) / 4.0), 0.0, 1.0))
	return c


func _build_landmarks() -> void:
	for lm: Dictionary in data.get("landmarks", []):
		var p := ground(lm["pos"][0], lm["pos"][1])
		match str(lm["type"]):
			"obelisk":
				_build_obelisk(p)
			"camp":
				_build_camp(p)
			"ruins":
				_build_ruins(p)
			"outpost":
				_build_outpost(p)
			"wall_ring":
				_build_wall_ring(p, lm)
			"hearth_plaza":
				_build_hearth_plaza(p)
			"house":
				_build_house(p, _landmark_yaw(lm), int(lm.get("size", 2)), true)
			"market":
				_build_market(p, _landmark_yaw(lm))
			"tavern_room":
				_build_tavern_room(p, _landmark_yaw(lm))
			"pond":
				_build_pond(lm)
			"signpost":
				_build_signpost(p, _landmark_yaw(lm), lm.get("labels", []))
			"prop":
				_prop(lm["id"], p, _landmark_yaw(lm), float(lm.get("scale", 1.0)), str(lm.get("collide", "box")))


## The bind point: a rune-carved obelisk inside a ring of standing stones.
func _build_obelisk(p: Vector3) -> void:
	_prop("obelisk", p)
	for k in 8:
		var a := k * TAU / 8.0
		_prop("standing_stone", p + Vector3(cos(a) * 7.0, 0, sin(a) * 7.0), _rng.randf() * TAU)
	_light(p + Vector3(0, 7.3, 0), Color(0.6, 0.8, 1.0), 14.0)


## Gnoll camp: hide tents around a fire, clutter, torches, and a palisade with
## its gate facing the bind point.
func _build_camp(p: Vector3) -> void:
	var center := Vector2(p.x, p.z)
	var gate := center.direction_to(_bind_xz).angle()
	_prop("campfire", p, 0.0, 1.0, "none")
	_light(p + Vector3(0, 1.2, 0), Color(1.0, 0.55, 0.2), 12.0, 1.2)
	for k in 4:
		var a := gate + PI / 4.0 + k * TAU / 4.0
		_prop("tent", _ring(p, a, 9.0), _face_center(a))

	# palisade ring, open at the gate and at a back gap
	var segments := 22
	for k in segments:
		var a := k * TAU / segments
		if absf(angle_difference(a, gate)) < 0.3 or absf(angle_difference(a, gate + PI)) < 0.15:
			continue
		_prop("palisade", _ring(p, a, 14.0), _face_center(a) + _rng.randf_range(-0.04, 0.04))
	for s: float in [-1.0, 1.0]:
		var a := gate + s * 0.36
		_torch(_ring(p, a, 14.2))
		_prop("banner_pole", _ring(p, a + s * 0.08, 15.5), _face_center(a), 1.0, "none")
		_prop("banner_brown", _ring(p, a + s * 0.08, 15.5) + Vector3(0, 0.32, 0), _face_center(a) + PI, 1.0, "none")
	for k in 3:
		_torch(_ring(p, gate + PI / 2.0 + k * TAU / 3.0, 4.2))

	# clutter between the tents
	var clutter := [["barrel_large", 1.0], ["barrel_small_stack", 1.0], ["crates_stacked", 1.0], ["box_large", 0.9],
			["keg_decorated", 1.0], ["barrel_small", 1.0], ["box_small", 1.0], ["trunk_medium_A", 1.0]]
	for k in clutter.size():
		var a := gate + (k + 0.5) * TAU / clutter.size() + _rng.randf_range(-0.12, 0.12)
		if absf(angle_difference(a, gate)) < 0.35:
			a += 0.5
		_prop(clutter[k][0], _ring(p, a, _rng.randf_range(10.5, 12.0)), _rng.randf() * TAU, clutter[k][1])
	var table_a := gate + PI
	_prop("table_long_decorated_A", _ring(p, table_a, 5.5), _face_center(table_a) + PI / 2.0)
	for s: float in [-1.0, 1.0]:
		_prop("stool", _ring(p, table_a + s * 0.18, 4.4), 0.0, 1.0, "none")
		_prop("stool", _ring(p, table_a + s * 0.18, 6.6), 0.0, 1.0, "none")
	_prop("chest", _ring(p, gate + PI + 0.9, 7.0), _face_center(gate + PI + 0.9))


## Crumbling hall: a cracked tile floor inside broken walls, pillars and rubble.
func _build_ruins(p: Vector3) -> void:
	const TILE := 3.0  # dungeon pieces are 4 m at scale 0.75
	var cols := 6
	var rows := 4
	var origin := p + Vector3(-TILE * cols / 2.0, 0.03, -TILE * rows / 2.0)
	var smalls := ["floor_tile_small", "floor_tile_small_broken_A", "floor_tile_small_broken_B",
			"floor_tile_small_weeds_A", "floor_tile_small_weeds_B"]
	for cx in cols:
		for cz in rows:
			var c := origin + Vector3((cx + 0.5) * TILE, 0, (cz + 0.5) * TILE)
			var roll := _rng.randf()
			if roll < 0.12:
				continue  # grass shows through
			elif roll < 0.35:
				for q in 4:
					if _rng.randf() < 0.85:
						var off := Vector3((q % 2 - 0.5) * TILE * 0.5, 0, (q / 2 - 0.5) * TILE * 0.5)
						_prop(smalls[_rng.randi() % smalls.size()], c + off, _rng.randi() % 4 * PI / 2.0, 1.0, "none")
			else:
				_prop("floor_tile_large" if roll < 0.8 else "floor_tile_large_rocks", c, _rng.randi() % 4 * PI / 2.0, 1.0, "none")

	# walls: back wall mostly standing, sides patchy, front nearly gone
	var back := ["wall", "wall_cracked", "wall_arched", "wall_broken", "wall", "wall_cracked"]
	for k in cols:
		if _rng.randf() < 0.15:
			continue
		var at := origin + Vector3((k + 0.5) * TILE, 0, 0)
		_prop(back[k] if _rng.randf() < 0.75 else "wall_half", at, 0.0)
	for side: float in [0.0, 1.0]:
		for k in rows:
			if _rng.randf() < 0.45:
				continue
			var at := origin + Vector3(side * cols * TILE, 0, (k + 0.5) * TILE)
			_prop(["wall_broken", "wall_half", "wall_cracked"][_rng.randi() % 3], at, PI / 2.0)
	for k in cols:
		if _rng.randf() < 0.3:
			_prop("wall_half", origin + Vector3((k + 0.5) * TILE, 0, rows * TILE), 0.0)
	for corner: Vector3 in [Vector3.ZERO, Vector3(cols * TILE, 0, 0), Vector3(0, 0, rows * TILE), Vector3(cols * TILE, 0, rows * TILE)]:
		_prop("pillar", origin + corner, 0.0, 1.0 if corner.z == 0.0 else 0.6)

	# a colonnade down the middle, mostly toppled
	for k in 4:
		var at := p + Vector3(-6.0 + k * 4.0, 0, 0)
		if _rng.randf() < 0.6:
			_prop("column", at, _rng.randf() * TAU, _rng.randf_range(0.8, 1.2))
	_prop("rubble_large", p + Vector3(5.0, 0, 7.5), 0.3)
	_prop("rubble_half", p + Vector3(-10.5, 0, 2.0), 1.9, 0.8)
	_prop("rubble_half", p + Vector3(2.0, 0, -8.0), PI, 0.7)


## Watch house: a house whose door faces the bind point, with supplies outside.
func _build_outpost(p: Vector3) -> void:
	var to_bind := _bind_xz - Vector2(p.x, p.z)
	var yaw := atan2(to_bind.x, to_bind.y)
	var xf := _build_house(p, yaw, 2, false)
	_prop("banner_shield_blue", xf * Vector3(-1.5, 0.1, 3.18), yaw, 1.0, "none")
	_prop("table_medium", xf * Vector3(-1.2, 0.06, -1.3), yaw)
	_prop("chair", xf * Vector3(-1.2, 0.06, -0.1), yaw + PI, 1.0, "none")
	_prop("trunk_small_A", xf * Vector3(1.9, 0.06, -2.0), yaw)
	_torch(xf * Vector3(3.6, 0, 3.9))
	_prop("crates_stacked", xf * Vector3(-4.2, 0, -1.8), yaw + 0.4)
	_prop("barrel_large", xf * Vector3(-4.1, 0, 0.6), yaw)
	_prop("barrel_small_stack", xf * Vector3(0.8, 0, -4.1), yaw + PI)


## A room of Dungeon walls (size x size segments of 3 m) under a gable roof,
## door in the front (+Z) wall. Walls use mesh collision so the door is open.
## Returns the house transform.
func _build_house(p: Vector3, yaw: float, size: int, furnish: bool) -> Transform3D:
	var xf := Transform3D(Basis(Vector3.UP, yaw), p)
	var half_w := size * 1.5
	var put := func(id: String, local: Vector3, local_yaw := 0.0, collide := "box", scale_ := 1.0) -> void:
		_prop(id, xf * local, yaw + local_yaw, scale_, collide)
	var door := size / 2  # middle segment of the front wall
	for i in size:
		var c := -half_w + 1.5 + i * 3.0
		for j in size:
			put.call("floor_wood_large", Vector3(c, 0.06, -half_w + 1.5 + j * 3.0), 0.0, "none")
		var back := "wall_window_closed" if _rng.randf() < 0.4 else "wall"
		put.call(back, Vector3(c, 0, -half_w), 0.0, "mesh")
		put.call("wall_doorway" if i == door else "wall", Vector3(c, 0, half_w), 0.0, "mesh")
		for side: float in [-1.0, 1.0]:
			var id := "wall_window_open" if _rng.randf() < 0.45 else "wall"
			put.call(id, Vector3(side * half_w, 0, c), PI / 2.0, "mesh")
	for x: float in [-half_w, half_w]:
		for z: float in [-half_w, half_w]:
			put.call("pillar", Vector3(x, 0, z))
	put.call("roof_gable", Vector3(0, 3.0, 0), 0.0, "mesh", size / 2.0)  # solid so the camera can't slip inside
	if furnish:
		put.call("table_medium", Vector3(-half_w + 1.8, 0.06, -half_w + 1.8))
		put.call("chair", Vector3(-half_w + 1.8, 0.06, -half_w + 3.0), PI, "none")
		put.call(["barrel_small", "trunk_small_A", "box_small"][_rng.randi() % 3], Vector3(half_w - 1.2, 0.06, -half_w + 1.2))
		if _rng.randf() < 0.5:
			put.call("barrel_small_stack", Vector3(-half_w - 1.4, 0, _rng.randf_range(-1.5, 1.5)), PI / 2.0)
	return xf


## City wall: straight runs of wall between towers around a polygon, with a
## gatehouse in the middle of each side named in "gates" (degrees; -90 = north).
func _build_wall_ring(p: Vector3, lm: Dictionary) -> void:
	var radius := float(lm.get("radius", 50))
	var sides := int(lm.get("sides", 12))
	var gates: Array = lm.get("gates", [])
	var corners: Array[Vector2] = []
	for k in sides:
		var a := k * TAU / sides + PI / sides  # sides, not corners, face the cardinal directions
		corners.append(Vector2(p.x, p.z) + Vector2(cos(a), sin(a)) * radius)
	for k in sides:
		var a0 := corners[k]
		var a1 := corners[(k + 1) % sides]
		_prop("city_tower", ground(a0.x, a0.y), 0.0)
		var mid := (a0 + a1) * 0.5
		var mid_angle := rad_to_deg(atan2(mid.y - p.z, mid.x - p.x))
		var has_gate := false
		for g: float in gates:
			if absf(angle_difference(deg_to_rad(mid_angle), deg_to_rad(g))) < PI / sides:
				has_gate = true
		var dir := (a1 - a0).normalized()
		if has_gate:
			_wall_run(a0 + dir * 2.4, mid - dir * 6.0)
			_prop("city_gate", ground(mid.x, mid.y), atan2(-dir.y, dir.x), 1.0, "mesh")
			_wall_run(mid + dir * 6.0, a1 - dir * 2.4)
		else:
			_wall_run(a0 + dir * 2.4, a1 - dir * 2.4)


## Fills a straight line with 6 m wall pieces (the last few overlap a little).
func _wall_run(from: Vector2, to: Vector2) -> void:
	var length := from.distance_to(to)
	if length < 0.5:
		return
	var n := ceili(length / 6.0)
	var dir := (to - from) / length
	var yaw := atan2(-dir.y, dir.x)
	for i in n:
		var c := from + dir * minf(3.0 + i * 6.0, length - 3.0) if length >= 6.0 else (from + to) * 0.5
		_prop("city_wall", ground(c.x, c.y), yaw)


## Paved square around the eternal hearth, ringed by lamps.
func _build_hearth_plaza(p: Vector3) -> void:
	_prop("hearth", p, 0.0, 1.0, "mesh")
	_light(p + Vector3(0, 3.5, 0), Color(1.0, 0.6, 0.25), 16.0, 1.6)
	for i in 9:
		for j in 9:
			var off := Vector3(-12.0 + i * 3.0, 0.04, -12.0 + j * 3.0)
			if Vector2(off.x, off.z).length() < 14.5:
				_prop("floor_tile_large", p + off, _rng.randi() % 4 * PI / 2.0, 1.0, "none")
	for k in 8:
		var a := k * TAU / 8.0 + TAU / 16.0
		_lamp(p + Vector3(cos(a) * 12.5, 0, sin(a) * 12.5), -a + PI / 2.0)


## A row of market stalls with crates and barrels between them.
func _build_market(p: Vector3, yaw: float) -> void:
	var xf := Transform3D(Basis(Vector3.UP, yaw), p)
	for i in 3:
		_prop("market_stall", xf * Vector3(-4.5 + i * 4.5, 0, 0), yaw + PI)
		if i < 2:
			_prop(["barrel_small", "box_small", "crates_stacked"][_rng.randi() % 3], xf * Vector3(-2.25 + i * 4.5, 0, -1.2), _rng.randf() * TAU, 0.8)


## The taproom inside the Ember and Anvil: 21 x 18 m and 6 m to the ceiling, bar
## across the back, door on the +Z side where the zone line out sits. Built from
## the same Dungeon pieces the houses use, so it matches the rest of the city
## indoors as well as out; the counter itself is our own prop.
func _build_tavern_room(p: Vector3, yaw: float) -> void:
	var xf := Transform3D(Basis(Vector3.UP, yaw), p)
	var put := func(id: String, local: Vector3, local_yaw := 0.0, collide := "box", scale_ := 1.0) -> void:
		_prop(id, xf * local, yaw + local_yaw, scale_, collide)
	var lamp := func(local: Vector3, energy := 2.2) -> void:
		_light(xf * local, Color(1.0, 0.78, 0.52), 11.0, energy)
	var hw := 10.5
	var hd := 9.0

	# --- shell: floor, ceiling, walls -----------------------------------------
	# Two courses of wall, so the taproom is 6 m to the ceiling. One course left
	# the third-person camera nothing to work with: it needs room to swing.
	for i in 7:
		var x := -9.0 + i * 3.0
		for j in 6:
			put.call("floor_wood_large", Vector3(x, 0.06, -7.5 + j * 3.0), 0.0, "none")
			# The ceiling collides. Without that the camera rides straight up
			# through it and you end up looking at the roof from outside.
			put.call("ceiling_tile", Vector3(x, 6.02, -7.5 + j * 3.0), 0.0, "box")
		for y: float in [0.0, 3.0]:
			put.call("wall", Vector3(x, y, -hd), 0.0, "mesh")
			put.call("wall_doorway" if i == 3 and y == 0.0 else "wall", Vector3(x, y, hd), 0.0, "mesh")
	for j in 6:
		var z := -7.5 + j * 3.0
		for side: float in [-1.0, 1.0]:
			var id := "wall_window_closed" if j == 2 or j == 3 else "wall"
			put.call(id, Vector3(side * hw, 0, z), PI / 2.0, "mesh")
			put.call("wall", Vector3(side * hw, 3.0, z), PI / 2.0, "mesh")
	for x: float in [-hw, hw]:
		for z: float in [-hd, hd]:
			for y: float in [0.0, 3.0]:
				put.call("pillar", Vector3(x, y, z))
	for post: Array in [[-3.0, -2.0], [3.0, -2.0], [-3.0, 4.0], [3.0, 4.0]]:
		for y: float in [0.0, 3.0]:   # posts holding the ceiling up mid-room
			put.call("pillar", Vector3(post[0], y, post[1]))

	# --- the bar --------------------------------------------------------------
	put.call("tavern_bar", Vector3(0, 0.06, -6.8), 0.0, "mesh")
	lamp.call(Vector3(0, 3.1, -5.6), 3.0)
	for i in 5:                    # stools along the counter
		put.call("stool", Vector3(-3.2 + i * 1.6, 0.06, -5.3), PI, "none")
	put.call("barrel_large", Vector3(-9.4, 0.06, -7.4))
	put.call("crates_stacked", Vector3(9.3, 0.06, -7.6), PI / 5.0)

	# --- tables to sit at, for whoever the night brings in --------------------
	for spot: Array in [[-6.6, 5.6], [6.6, 5.6], [-6.6, 1.0], [6.6, 1.0], [-6.6, -3.6], [6.6, -3.6]]:
		var t := Vector3(spot[0], 0.06, spot[1])
		put.call("table_medium", t)
		put.call("chair", t + Vector3(0, 0, 1.35), PI, "none")
		put.call("chair", t + Vector3(0, 0, -1.35), 0.0, "none")
		put.call("stool", t + Vector3(1.35, 0, 0), 0.0, "none")
		put.call("stool", t + Vector3(-1.35, 0, 0), 0.0, "none")
		put.call("candle_lit", t + Vector3(0.25, 0.86, 0.1), 0.0, "none")
		put.call("mug_full", t + Vector3(-0.3, 0.86, -0.2), 0.0, "none")
		lamp.call(t + Vector3(0, 3.0, 0), 1.8)

	# --- dressing -------------------------------------------------------------
	put.call("shelf_small", Vector3(-hw + 0.5, 0.06, 2.5), PI / 2.0)
	put.call("barrel_small_stack", Vector3(hw - 0.7, 0.06, 3.6), -PI / 2.0)
	put.call("chest", Vector3(-hw + 0.7, 0.06, -5.4), PI / 2.0)
	# The long table down the middle, dishes and all. The door arrives to one
	# side of it so walking in does not put it straight into your chest.
	put.call("table_long_decorated_A", Vector3(0, 0.06, 2.0))
	for i in 4:
		put.call("stool", Vector3(-2.4 + i * 1.6, 0.06, 3.5), PI, "none")
		put.call("stool", Vector3(-2.4 + i * 1.6, 0.06, 0.5), 0.0, "none")
	lamp.call(Vector3(0, 3.0, 2.0), 1.8)
	for side: float in [-1.0, 1.0]:
		for z: float in [-2.5, 3.5]:
			put.call("torch_lit", Vector3(side * (hw - 0.35), 1.9, z), side * PI / 2.0, "none")
			_light(xf * Vector3(side * (hw - 0.9), 2.1, z), Color(1.0, 0.62, 0.3), 7.5, 1.8)
		put.call("banner_brown", Vector3(side * (hw - 0.3), 2.3, 7.0), side * PI / 2.0, "none")
	lamp.call(Vector3(0, 3.0, 7.4), 1.6)


## Water in a bowl carved by height_at, ringed by reeds, with lily pads and a
## dock on the bank at angle "dock" (degrees; 0 = east, -90 = north) running
## out toward the middle. Crates, a barrel and a torch stand at its foot.
func _build_pond(lm: Dictionary) -> void:
	var pond: Dictionary = {}
	for pd: Dictionary in _ponds:
		if pd["center"] == Vector2(lm["pos"][0], lm["pos"][1]):
			pond = pd
	var center: Vector2 = pond["center"]
	var r: float = pond["radius"]
	var level: float = pond["level"]

	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	st.set_normal(Vector3.UP)
	const SEGMENTS := 40
	for k in SEGMENTS:
		var a0 := k * TAU / SEGMENTS
		var a1 := (k + 1) * TAU / SEGMENTS
		st.add_vertex(Vector3.ZERO)
		st.add_vertex(Vector3(cos(a1), 0, sin(a1)) * (r + 1.0))
		st.add_vertex(Vector3(cos(a0), 0, sin(a0)) * (r + 1.0))
	var water := MeshInstance3D.new()
	water.mesh = st.commit()
	var mat := ShaderMaterial.new()
	mat.shader = WATER_SHADER
	water.material_override = mat
	water.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	water.position = Vector3(center.x, level, center.y)
	add_child(water)

	var dock_a := deg_to_rad(float(lm.get("dock", 0.0)))
	var dir := Vector2(cos(dock_a), sin(dock_a))
	var base := center + dir * (r - 0.5)
	var yaw := atan2(-dir.x, -dir.y)
	_prop("dock", ground(base.x, base.y), yaw, 1.0, "mesh")
	var xf := Transform3D(Basis(Vector3.UP, yaw), ground(base.x, base.y))
	var on_bank := func(local: Vector3) -> Vector3:
		var w := xf * local
		return ground(w.x, w.z)
	_prop("barrel_small", on_bank.call(Vector3(3.1, 0, -1.0)), yaw + 0.4, 0.9)
	_prop("box_small", on_bank.call(Vector3(2.9, 0, -2.7)), yaw - 0.3, 0.9)
	_prop("crates_stacked", on_bank.call(Vector3(-2.3, 0, -1.8)), yaw + 0.2)
	_prop("stool", xf * Vector3(0.4, 0.35, 6.6), 0.0, 1.0, "none")
	_torch(on_bank.call(Vector3(-1.3, 0, -0.5)))

	for k in 26:
		var a := _rng.randf() * TAU
		if absf(angle_difference(a, dock_a)) < 0.3:
			continue
		var at := center + Vector2(cos(a), sin(a)) * r * _rng.randf_range(0.84, 0.98)
		_prop("reeds", ground(at.x, at.y), _rng.randf() * TAU, _rng.randf_range(0.8, 1.2), "none")
	for k in 7:
		var a := _rng.randf() * TAU
		if absf(angle_difference(a, dock_a)) < 0.4:
			continue
		var at := center + Vector2(cos(a), sin(a)) * r * _rng.randf_range(0.25, 0.7)
		_prop("lily_pads", Vector3(at.x, level + 0.01, at.y), _rng.randf() * TAU, _rng.randf_range(0.8, 1.3), "none")


func _build_signpost(p: Vector3, yaw: float, labels: Array) -> void:
	var post := _prop("signpost", p, yaw, 1.0, "none")
	var boards := [[Vector3(0.5, 2.25, 0.11), 0.0], [Vector3(-0.45, 1.75, -0.11), PI]]
	for i in mini(labels.size(), boards.size()):
		var l := Label3D.new()
		l.text = str(labels[i])
		l.font_size = 40
		l.pixel_size = 0.0045
		l.modulate = Color(0.2, 0.13, 0.08)
		l.outline_size = 0
		l.double_sided = false
		l.position = boards[i][0]
		l.rotation.y = boards[i][1]
		post.add_child(l)


## Lamp posts every so often along each road, alternating sides, skipping
## plazas (which place their own) and the stretch outside the map edge.
func _build_road_lamps() -> void:
	var spacing := float(data.get("road_lamps", 0))
	if spacing <= 0.0:
		return
	var plazas: Array[Vector2] = []
	for lm: Dictionary in data.get("landmarks", []):
		if lm["type"] == "hearth_plaza":
			plazas.append(Vector2(lm["pos"][0], lm["pos"][1]))
	var side := 1.0
	for road: Dictionary in _roads:
		var pts: Array[Vector2] = road["points"]
		for i in pts.size() - 1:
			var seg := pts[i + 1] - pts[i]
			var dir := seg.normalized()
			var normal := Vector2(-dir.y, dir.x)
			var t := spacing * 0.5
			while t < seg.length():
				var at: Vector2 = pts[i] + dir * t + normal * side * (float(road["width"]) * 0.5 + 1.2)
				var skip := maxf(absf(at.x), absf(at.y)) > half - 30.0
				for pl in plazas:
					skip = skip or at.distance_to(pl) < 16.0
				if not skip:
					_lamp(ground(at.x, at.y), atan2(normal.x * side, normal.y * side))
				side = -side
				t += spacing


## A lamp post whose lantern arm points along `yaw`'s forward (+Z), with light.
func _lamp(pos: Vector3, yaw: float) -> void:
	_prop("lamp_post", pos, yaw, 1.0, "none")
	var lantern := Transform3D(Basis(Vector3.UP, yaw), pos) * Vector3(0, 2.86, 0.62)
	_light(lantern, Color(1.0, 0.72, 0.4), 8.0, 0.7)


## Invisible triggers at the zone's edges that move a player to another zone.
func _build_zone_lines() -> void:
	var lines: Array = data.get("zone_lines", [])
	for i in lines.size():
		var zl: Dictionary = lines[i]
		var area := Area3D.new()
		area.collision_layer = 0
		area.collision_mask = Layers.ENTITIES
		area.position = ground(zl["pos"][0], zl["pos"][1]) + Vector3.UP * 2.0
		var box := BoxShape3D.new()
		box.size = Vector3(zl["size"][0], 6.0, zl["size"][1])
		var cs := CollisionShape3D.new()
		cs.shape = box
		area.add_child(cs)
		area.body_entered.connect(func(body: Node3D) -> void:
			if body is Player:
				World.request_zone_line((body as Player).entity_id, i))
		add_child(area)


## The zone line a position is standing in, or -1.
func zone_line_at(pos: Vector3) -> int:
	var lines: Array = data.get("zone_lines", [])
	for i in lines.size():
		var zl: Dictionary = lines[i]
		if absf(pos.x - float(zl["pos"][0])) <= float(zl["size"][0]) * 0.5 + 1.0 \
				and absf(pos.z - float(zl["pos"][1])) <= float(zl["size"][1]) * 0.5 + 1.0:
			return i
	return -1


## Yaw for a landmark: "yaw" in degrees, or "face": [x, z] to turn its front (+Z) toward.
func _landmark_yaw(lm: Dictionary) -> float:
	if lm.has("face"):
		return atan2(float(lm["face"][0]) - float(lm["pos"][0]), float(lm["face"][1]) - float(lm["pos"][1]))
	return deg_to_rad(float(lm.get("yaw", 0.0)))


func _build_npcs() -> void:
	for entry: Dictionary in data.get("npcs", []):
		var npc := Npc.new()
		npc.setup(entry["id"], str(entry.get("name", "")))
		npc.position = ground(entry["pos"][0], entry["pos"][1]) + Vector3.UP * float(entry.get("y", 0.1))
		for pt: Array in entry.get("patrol", []):
			npc.patrol.append(ground(pt[0], pt[1]))
		if entry.has("face"):
			var d := Vector2(entry["face"][0], entry["face"][1]) - Vector2(entry["pos"][0], entry["pos"][1])
			npc.rotation.y = atan2(-d.x, -d.y)
		add_child(npc)


func _build_props() -> void:
	var trees := ["pine_a", "pine_a", "pine_b", "pine_b", "tree_round"]
	for k in int(data.get("trees", 150)):
		var xz := _open_spot()
		var s := _rng.randf_range(0.8, 1.5)
		_prop(trees[_rng.randi() % trees.size()], ground(xz.x, xz.y) - Vector3.UP * 0.1, _rng.randf() * TAU, s, "trunk")

	var rocks := ["boulder_a", "boulder_b", "boulder_c", "rubble_half"]
	for k in int(data.get("rocks", 50)):
		var xz := _open_spot()
		var id: String = rocks[_rng.randi() % rocks.size()]
		var s := _rng.randf_range(0.6, 1.6) * (0.4 if id == "rubble_half" else 1.0)
		_prop(id, ground(xz.x, xz.y) - Vector3.UP * 0.15 * s, _rng.randf() * TAU, s)


## Grass, flowers, ferns, bushes and the like from the zone's "clutter" table:
## {prop_id: {density (per m²), patch (0-1 clumping), sway, range, shadow,
## tint ("ground" to match the terrain), scale [min, max], city (density
## factor inside clear_radius)}}. Drawn as one MultiMesh per type per chunk so
## far chunks are skipped; nothing collides.
func _build_clutter() -> void:
	var table: Dictionary = data.get("clutter", {})
	if table.is_empty():
		return
	var rng := RandomNumberGenerator.new()
	rng.seed = int(data.get("seed", 1)) + 7919
	var patches := FastNoiseLite.new()
	patches.seed = int(data.get("seed", 1)) + 31
	patches.frequency = 0.045
	var chunks := ceili(size / CLUTTER_CHUNK)
	for id: String in table:
		var spec: Dictionary = table[id]
		var source := _clutter_source(id, float(spec.get("sway", 0.0)))
		if source.is_empty():
			continue
		var density := float(spec.get("density", 0.1))
		var patch := float(spec.get("patch", 0.5))
		var city := float(spec.get("city", 0.0))
		var by_ground := str(spec.get("tint", "")) == "ground"
		var scale_range: Array = spec.get("scale", [0.8, 1.2])
		patches.seed += 1  # each type clumps in its own places
		for cx in chunks:
			for cz in chunks:
				var x0 := -half + cx * CLUTTER_CHUNK
				var z0 := -half + cz * CLUTTER_CHUNK
				var xforms: Array[Transform3D] = []
				var colors: Array[Color] = []
				var tries := int(density * CLUTTER_CHUNK * CLUTTER_CHUNK) + (1 if rng.randf() < fmod(density * CLUTTER_CHUNK * CLUTTER_CHUNK, 1.0) else 0)
				for k in tries:
					var x := x0 + rng.randf() * CLUTTER_CHUNK
					var z := z0 + rng.randf() * CLUTTER_CHUNK
					var keep := lerpf(1.0, smoothstep(-0.15, 0.35, patches.get_noise_2d(x, z)) * 1.6, patch)
					if Vector2(x, z).length() < _clear_radius:
						keep *= city
					if rng.randf() >= keep or not _clutter_spot_ok(x, z):
						continue
					var h := height_at(x, z)
					var s := rng.randf_range(float(scale_range[0]), float(scale_range[1]))
					var basis := Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3.ONE * s)
					xforms.append(Transform3D(basis, Vector3(x, h - 0.02, z)))
					if by_ground:
						var g := _ground_color(x, z, h)
						colors.append(Color(g.r * 1.45, g.g * 1.4, g.b * 1.3) * rng.randf_range(0.9, 1.1))
					else:
						colors.append(Color.WHITE * rng.randf_range(0.88, 1.08))
				if xforms.is_empty():
					continue
				var mm := MultiMesh.new()
				mm.transform_format = MultiMesh.TRANSFORM_3D
				mm.use_colors = true
				mm.mesh = source["mesh"]
				mm.instance_count = xforms.size()
				for i in xforms.size():
					mm.set_instance_transform(i, xforms[i])
					mm.set_instance_color(i, colors[i])
				var mmi := MultiMeshInstance3D.new()
				mmi.multimesh = mm
				mmi.material_override = source["material"]
				mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if spec.get("shadow", false) else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
				mmi.visibility_range_end = float(spec.get("range", 60.0))
				mmi.visibility_range_end_margin = 10.0
				mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
				add_child(mmi)


## The mesh and a wind-aware material for one clutter prop.
func _clutter_source(id: String, sway: float) -> Dictionary:
	if not GameData.models["props"].has(id):
		push_warning("clutter: unknown prop %s" % id)
		return {}
	var scene: Node = (load(GameData.models["props"][id]["path"]) as PackedScene).instantiate()
	var mi := scene.find_children("*", "MeshInstance3D", true, false)[0] as MeshInstance3D
	var mesh := mi.mesh
	var base := mesh.surface_get_material(0) as BaseMaterial3D
	scene.free()
	var mat := ShaderMaterial.new()
	mat.shader = CLUTTER_SHADER
	mat.set_shader_parameter("albedo_tex", base.albedo_texture if base != null else null)
	mat.set_shader_parameter("sway", sway)
	return {"mesh": mesh, "material": mat}


## Clutter stays off roads, landmarks, the bind circle and mountainsides.
func _clutter_spot_ok(x: float, z: float) -> bool:
	var p := Vector2(x, z)
	if p.distance_to(_bind_xz) < 9.0 or road_distance(x, z) < 0.6:
		return false
	if (maxf(absf(x), absf(z)) - (half - 30.0)) * _pass_factor(x, z) > 0.0:
		return false
	for pond: Dictionary in _ponds:
		if p.distance_to(pond["center"]) < float(pond["radius"]) + 1.5:
			return false
	for spot in _flat_spots:
		if p.distance_to(spot) < 12.5:
			return false
	return true


func _build_spawns() -> void:
	for entry: Dictionary in data.get("spawns", []):
		var sp := SpawnPoint.new()
		sp.zone = self
		sp.pool = entry["pool"]
		sp.respawn_time = float(entry.get("respawn", 60))
		sp.wander_radius = float(entry.get("wander", 8))
		sp.position = ground(entry["pos"][0], entry["pos"][1])
		add_child(sp)


# --- helpers ----------------------------------------------------------------

func _open_spot() -> Vector2:
	for attempt in 30:
		var xz := Vector2(_rng.randf_range(-half + 30.0, half - 30.0), _rng.randf_range(-half + 30.0, half - 30.0))
		if xz.distance_to(_bind_xz) < flat_radius + 6.0 or xz.length() < _clear_radius or road_distance(xz.x, xz.y) < 3.0:
			continue
		var clear := true
		for spot in _flat_spots:
			if xz.distance_to(spot) < 18.0:
				clear = false
				break
		if clear:
			return xz
	return Vector2(half - 35.0, half - 35.0)


## Places a prop from data/models.json "props". `collide` is "box" (the model's
## bounds), "mesh" (exact triangles, for walls with doors), "trunk" (a thin post
## for trees) or "none".
func _prop(id: String, pos: Vector3, yaw := 0.0, scale_ := 1.0, collide := "box") -> Node3D:
	var spec: Dictionary = GameData.models["props"][id]
	if not _prop_scenes.has(id):
		_prop_scenes[id] = load(spec["path"])
	var s := float(spec.get("scale", 1.0)) * scale_
	var model: Node3D = (_prop_scenes[id] as PackedScene).instantiate()
	model.scale = Vector3.ONE * s
	for mi: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	var root: Node3D = model if collide == "none" else StaticBody3D.new()
	root.position = pos
	root.rotation.y = yaw
	if collide != "none":
		(root as StaticBody3D).collision_layer = Layers.WORLD
		root.add_child(model)
		var cs := CollisionShape3D.new()
		var raw := _prop_bounds(id, model)
		var bounds := AABB(raw.position * s, raw.size * s)
		if collide == "mesh":
			var faces := _prop_faces(id, model)
			var scaled := PackedVector3Array()
			scaled.resize(faces.size())
			for i in faces.size():
				scaled[i] = faces[i] * s
			var tri := ConcavePolygonShape3D.new()
			tri.set_faces(scaled)
			cs.shape = tri
		elif collide == "trunk":
			var cyl := CylinderShape3D.new()
			cyl.radius = 0.3 * s
			cyl.height = 3.0 * s
			cs.shape = cyl
			cs.position.y = 1.5 * s
		else:
			var box := BoxShape3D.new()
			box.size = bounds.size
			cs.shape = box
			cs.position = bounds.get_center()
		root.add_child(cs)
	add_child(root)
	return root


## Unscaled triangles of a prop's meshes, cached per id.
func _prop_faces(id: String, model: Node3D) -> PackedVector3Array:
	if not _prop_tris.has(id):
		var out := PackedVector3Array()
		for mi: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
			var xf := _relative_xform(mi, model)
			for v in mi.mesh.get_faces():
				out.append(xf * v)
		_prop_tris[id] = out
	return _prop_tris[id]


func _relative_xform(node: Node3D, ancestor: Node3D) -> Transform3D:
	var xf := Transform3D.IDENTITY
	var n: Node = node
	while n != ancestor:
		xf = (n as Node3D).transform * xf
		n = n.get_parent()
	return xf


## Unscaled bounds of a prop's meshes, cached per id.
func _prop_bounds(id: String, model: Node3D) -> AABB:
	if not _prop_aabbs.has(id):
		var box := AABB()
		var first := true
		for mi: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
			var a := _relative_xform(mi, model) * mi.get_aabb()
			box = a if first else box.merge(a)
			first = false
		_prop_aabbs[id] = box
	return _prop_aabbs[id]


## A standing torch: post, a pack torch in its cup, and a small light.
func _torch(pos: Vector3) -> void:
	_prop("torch_post", pos, 0.0, 1.0, "none")
	_prop("torch_lit", pos + Vector3(0, 1.72, 0), 0.0, 1.0, "none")
	_light(pos + Vector3(0, 2.3, 0), Color(1.0, 0.6, 0.25), 6.0, 0.8)


func _ring(center: Vector3, angle: float, radius: float) -> Vector3:
	return ground(center.x + cos(angle) * radius, center.z + sin(angle) * radius)


## Yaw that turns a prop's front (+Z) toward the center of a ring it sits on.
func _face_center(angle: float) -> float:
	return atan2(-cos(angle), -sin(angle))


func _light(pos: Vector3, color: Color, light_range: float, energy := 2.0) -> void:
	var l := OmniLight3D.new()
	l.position = pos
	l.light_color = color
	l.omni_range = light_range
	l.light_energy = energy
	add_child(l)
