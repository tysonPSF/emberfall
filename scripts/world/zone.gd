class_name Zone
extends Node3D
## Builds a zone from data/zones/<id>.json: sky, terrain, props, landmarks,
## and spawn points. The terrain is generated from a seeded noise function,
## so the same zone file always produces the same world.

const GRID := 128

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
var _prop_scenes: Dictionary = {}  # prop id -> PackedScene
var _prop_aabbs: Dictionary = {}  # prop id -> unscaled AABB
var _prop_tris: Dictionary = {}  # prop id -> unscaled collision faces


func load_zone(id: String) -> void:
	zone_id = id
	data = GameData.load_zone(id)
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
		_flat_spots.append(Vector2(lm["pos"][0], lm["pos"][1]))
	bind_point = ground(_bind_xz.x, _bind_xz.y + 4.0)  # just south of the obelisk
	World.zone = self

	_build_environment()
	_build_terrain()
	_build_landmarks()
	_build_props()
	_build_spawns()
	_build_npcs()


func height_at(x: float, z: float) -> float:
	var h := _noise.get_noise_2d(x, z) * amp + _detail.get_noise_2d(x, z) * 0.35
	h = lerpf(h * 0.1, h, smoothstep(flat_radius, flat_radius + 25.0, Vector2(x, z).distance_to(_bind_xz)))
	for spot in _flat_spots:
		var d := Vector2(x, z).distance_to(spot)
		if d < 30.0:
			h = lerpf(_noise.get_noise_2d(spot.x, spot.y) * amp * 0.5, h, smoothstep(14.0, 30.0, d))
	# Mountains ring the zone so you can't walk off the edge.
	var edge := maxf(absf(x), absf(z)) - (half - 28.0)
	if edge > 0.0:
		h += edge * 1.3 + edge * edge * 0.08
	return h


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
	var edge := maxf(absf(x), absf(z)) - (half - 30.0)
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


## Watch house: a 2x2 room of Dungeon walls with a door facing the bind point,
## a gable roof, and some watch clutter. Walls use mesh collision so the door
## and windows are open.
func _build_outpost(p: Vector3) -> void:
	var to_bind := _bind_xz - Vector2(p.x, p.z)
	var yaw := atan2(to_bind.x, to_bind.y)  # local +Z (the door side) faces the bind point
	var xf := Transform3D(Basis(Vector3.UP, yaw), p)
	var put := func(id: String, local: Vector3, local_yaw := 0.0, collide := "box", scale_ := 1.0) -> void:
		_prop(id, xf * local, yaw + local_yaw, scale_, collide)
	for x: float in [-1.5, 1.5]:
		for z: float in [-1.5, 1.5]:
			put.call("floor_wood_large", Vector3(x, 0.06, z), 0.0, "none")
	put.call("wall", Vector3(-1.5, 0, -3), 0.0, "mesh")
	put.call("wall_window_closed", Vector3(1.5, 0, -3), 0.0, "mesh")
	put.call("wall_window_open", Vector3(-3, 0, -1.5), PI / 2.0, "mesh")
	put.call("wall", Vector3(-3, 0, 1.5), PI / 2.0, "mesh")
	put.call("wall", Vector3(3, 0, -1.5), PI / 2.0, "mesh")
	put.call("wall_window_open", Vector3(3, 0, 1.5), PI / 2.0, "mesh")
	put.call("wall", Vector3(-1.5, 0, 3), 0.0, "mesh")
	put.call("wall_doorway", Vector3(1.5, 0, 3), 0.0, "mesh")
	for x: float in [-3.0, 3.0]:
		for z: float in [-3.0, 3.0]:
			put.call("pillar", Vector3(x, 0, z))
	put.call("roof_gable", Vector3(0, 3.0, 0), 0.0, "none")
	put.call("banner_shield_blue", Vector3(-1.5, 0.1, 3.18), 0.0, "none")
	# inside: a table and chair by the window, a sea chest, supplies
	put.call("table_medium", Vector3(-1.2, 0.06, -1.3))
	put.call("chair", Vector3(-1.2, 0.06, -0.1), PI, "none")
	put.call("trunk_small_A", Vector3(1.9, 0.06, -2.0), 0.0)
	put.call("barrel_small", Vector3(-2.1, 0.06, 1.9))
	# outside: a torch by the door, crates and barrels along the wall
	_torch(xf * Vector3(3.6, 0, 3.9))
	put.call("crates_stacked", Vector3(-4.2, 0, -1.8), 0.4)
	put.call("barrel_large", Vector3(-4.1, 0, 0.6))
	put.call("barrel_small_stack", Vector3(0.8, 0, -4.1), PI)


func _build_npcs() -> void:
	for entry: Dictionary in data.get("npcs", []):
		var npc := Npc.new()
		npc.setup(entry["id"])
		npc.position = ground(entry["pos"][0], entry["pos"][1]) + Vector3.UP * 0.1
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
		if xz.distance_to(_bind_xz) < flat_radius + 6.0:
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
