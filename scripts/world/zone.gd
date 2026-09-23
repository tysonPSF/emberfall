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
				_box(p + Vector3(0, 3.0, 0), Vector3(1.2, 6.0, 1.2), Color(0.55, 0.55, 0.6))
				for k in 8:
					var a := k * TAU / 8.0
					_box(p + Vector3(cos(a) * 7.0, 0.5, sin(a) * 7.0), Vector3(0.9, 1.4, 0.9), Color(0.5, 0.5, 0.52), a)
				_light(p + Vector3(0, 6.8, 0), Color(0.6, 0.8, 1.0), 14.0)
			"camp":
				for k in 4:
					var a := k * TAU / 4.0 + 0.4
					_tent(p + Vector3(cos(a) * 9.0, 0, sin(a) * 9.0), -a)
				_box(p + Vector3(0, 0.2, 0), Vector3(1.6, 0.4, 1.6), Color(0.2, 0.15, 0.1))
				_light(p + Vector3(0, 1.2, 0), Color(1.0, 0.55, 0.2), 16.0)
			"ruins":
				_box(p + Vector3(0, 0.1, 0), Vector3(22, 0.4, 16), Color(0.45, 0.44, 0.42))
				for k in 10:
					var side := -1.0 if k % 2 == 0 else 1.0
					var h := _rng.randf_range(1.0, 5.0)
					_box(p + Vector3(-9.0 + (k / 2) * 4.5, h * 0.5, side * 7.0), Vector3(1.1, h, 1.1), Color(0.52, 0.5, 0.47))
				for k in 4:
					_box(p + Vector3(_rng.randf_range(-8, 8), 0.5, _rng.randf_range(-5, 5)),
							Vector3(1.0, 1.0, 3.0), Color(0.5, 0.48, 0.45), _rng.randf() * TAU)


func _build_props() -> void:
	var bark := _mat(Color(0.35, 0.25, 0.16))
	var leaves := _mat(Color(0.18, 0.34, 0.16))
	var stone := _mat(Color(0.46, 0.45, 0.43))
	var trunk_mesh := CylinderMesh.new()
	trunk_mesh.top_radius = 0.22
	trunk_mesh.bottom_radius = 0.35
	trunk_mesh.height = 3.0
	var leaf_mesh := CylinderMesh.new()
	leaf_mesh.top_radius = 0.0
	leaf_mesh.bottom_radius = 2.2
	leaf_mesh.height = 4.5
	leaf_mesh.radial_segments = 8
	var rock_mesh := SphereMesh.new()
	rock_mesh.radial_segments = 8
	rock_mesh.rings = 5

	for k in int(data.get("trees", 150)):
		var xz := _open_spot()
		var s := _rng.randf_range(0.8, 1.5)
		var tree := StaticBody3D.new()
		tree.collision_layer = Layers.WORLD
		tree.position = ground(xz.x, xz.y) - Vector3.UP * 0.2
		_mesh(tree, trunk_mesh, bark, Vector3(0, 1.5 * s, 0), Vector3.ONE * s)
		_mesh(tree, leaf_mesh, leaves, Vector3(0, 4.6 * s, 0), Vector3.ONE * s)
		_mesh(tree, leaf_mesh, leaves, Vector3(0, 6.3 * s, 0), Vector3.ONE * s * 0.7)
		var trunk_shape := CylinderShape3D.new()
		trunk_shape.radius = 0.35 * s
		trunk_shape.height = 3.0 * s
		var cs := CollisionShape3D.new()
		cs.shape = trunk_shape
		cs.position.y = 1.5 * s
		tree.add_child(cs)
		add_child(tree)

	for k in int(data.get("rocks", 50)):
		var xz := _open_spot()
		var s := _rng.randf_range(0.6, 2.2)
		var rock := StaticBody3D.new()
		rock.collision_layer = Layers.WORLD
		rock.position = ground(xz.x, xz.y)
		rock.rotation.y = _rng.randf() * TAU
		_mesh(rock, rock_mesh, stone, Vector3.ZERO, Vector3(1.4, 0.8, 1.1) * s)
		var sphere := SphereShape3D.new()
		sphere.radius = 0.7 * s
		var cs := CollisionShape3D.new()
		cs.shape = sphere
		rock.add_child(cs)
		add_child(rock)


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


func _mat(color: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = 0.95
	return m


func _mesh(parent: Node3D, mesh: Mesh, mat: Material, pos: Vector3, scl: Vector3) -> void:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = mat
	mi.position = pos
	mi.scale = scl
	parent.add_child(mi)


func _box(center: Vector3, box_size: Vector3, color: Color, yaw := 0.0) -> void:
	var body := StaticBody3D.new()
	body.collision_layer = Layers.WORLD
	body.position = center
	body.rotation.y = yaw
	var bm := BoxMesh.new()
	bm.size = box_size
	_mesh(body, bm, _mat(color), Vector3.ZERO, Vector3.ONE)
	var shape := BoxShape3D.new()
	shape.size = box_size
	var cs := CollisionShape3D.new()
	cs.shape = shape
	body.add_child(cs)
	add_child(body)


func _tent(base: Vector3, yaw: float) -> void:
	var body := StaticBody3D.new()
	body.collision_layer = Layers.WORLD
	body.position = base + Vector3(0, 1.5, 0)
	body.rotation.y = yaw
	var pm := PrismMesh.new()
	pm.size = Vector3(4.0, 3.0, 4.5)
	_mesh(body, pm, _mat(Color(0.5, 0.38, 0.24)), Vector3.ZERO, Vector3.ONE)
	var shape := BoxShape3D.new()
	shape.size = Vector3(3.0, 3.0, 4.5)
	var cs := CollisionShape3D.new()
	cs.shape = shape
	body.add_child(cs)
	add_child(body)


func _light(pos: Vector3, color: Color, light_range: float) -> void:
	var l := OmniLight3D.new()
	l.position = pos
	l.light_color = color
	l.omni_range = light_range
	l.light_energy = 2.0
	add_child(l)
