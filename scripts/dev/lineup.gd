extends Node3D
## Art check: stands models side by side and screenshots them from a few angles.
##   godot --path . -- --lineup=gnoll,gnoll_brute,rat [--action=idle] --shots=/some/dir
## --worn=head:iron_coif,chest:studded_tunic dresses every model in that gear
## (models.json "gear" ids), to compare how it sits on different bodies.
## --tiers=crude,,fine,superior,masterwork gives each model in turn that
## quality's finish on everything it holds and wears; --weapon=sword_1handed
## puts a weapon in every right hand.
## --offhand=shield_round puts a models.json "weapons" entry in the left hand;
## --grip=x,y,z[,px,py,pz[,bone[,orient[,ox,oy,oz]]]] tries a rotation
## (degrees), offset, bone, orientation bone and outward offset for it before
## writing them to "grips".
## Model ids are data/models.json character ids. Quits when done.

const SPACING := 1.8
const VIEWS := {"front": 0.0, "three_quarter": 0.7, "side": PI / 2.0, "back": PI, "behind_left": PI - 0.45}


func _ready() -> void:
	var ids: PackedStringArray = []
	var action := "idle"
	var shots_dir := ""
	var worn := {}
	var offhand := ""
	var tiers: PackedStringArray = []
	var weapon := ""
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--lineup="):
			ids = a.substr(9).split(",", false)
		elif a.begins_with("--action="):
			action = a.substr(9)
		elif a.begins_with("--tiers="):
			tiers = a.substr(8).split(",")
		elif a.begins_with("--weapon="):
			weapon = a.substr(9)
		elif a.begins_with("--offhand="):
			offhand = a.substr(10)
		elif a.begins_with("--grip="):
			var g := a.substr(7).split(",")
			var grip := {"rot": [float(g[0]), float(g[1]), float(g[2])]}
			if g.size() >= 6:
				grip["pos"] = [float(g[3]), float(g[4]), float(g[5])]
			if g.size() >= 7:
				grip["bone"] = g[6]
			if g.size() >= 8:
				grip["orient"] = g[7]
			if g.size() >= 11:
				grip["out"] = [float(g[8]), float(g[9]), float(g[10])]
			GameData.models["grips"][offhand if offhand != "" else "shield_round"] = grip
		elif a.begins_with("--worn="):
			for pair in a.substr(7).split(",", false):
				worn[pair.get_slice(":", 0)] = pair.get_slice(":", 1)
		elif a.begins_with("--shots="):
			shots_dir = a.substr(8)

	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color("9fb3c8")
	env.environment.ambient_light_color = Color.WHITE
	env.environment.ambient_light_energy = 0.6
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, 30, 0)
	sun.shadow_enabled = true
	add_child(sun)
	var ground := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(40, 40)
	ground.mesh = plane
	var gm := StandardMaterial3D.new()
	gm.albedo_color = Color("6f8f5a")
	ground.material_override = gm
	add_child(ground)

	var width := SPACING * (ids.size() - 1)
	for i in ids.size():
		var m := CharacterModel.new()
		add_child(m)
		m.setup(ids[i], weapon, 1.0)
		if i < tiers.size():
			var every := {}
			for slot: String in ["primary", "secondary", "head", "chest", "arms", "hands", "legs", "feet", "waist"]:
				every[slot] = tiers[i]
			m.set_tiers(every)
		m.position.x = -width / 2.0 + i * SPACING
		m.rotation.y = PI  # face the camera
		if not worn.is_empty():
			m.set_worn(worn)
		if offhand != "":
			m.set_offhand(offhand)
		var clip := m._clip(action)
		if clip != "":
			m.anim.play(clip)
		var label := Label3D.new()
		label.text = ids[i] + (" (%s)" % tiers[i] if i < tiers.size() and tiers[i] != "" else "")
		label.fixed_size = true
		label.pixel_size = 0.0008
		label.font_size = 28
		label.position = Vector3(m.position.x, -0.15, 0.8)
		label.rotation.x = -PI / 2.0
		add_child(label)

	var pivot := Node3D.new()
	pivot.position.y = 1.1
	add_child(pivot)
	var cam := Camera3D.new()
	cam.position = Vector3(0, 0.4, width * 0.75 + 3.8)
	cam.fov = 35.0
	pivot.add_child(cam)
	cam.look_at_from_position(cam.position, Vector3(0, 0, 0))
	cam.current = true

	await get_tree().create_timer(0.8).timeout
	for view: String in VIEWS:
		pivot.rotation.y = VIEWS[view]
		await get_tree().create_timer(0.2).timeout
		await RenderingServer.frame_post_draw
		if shots_dir != "":
			get_viewport().get_texture().get_image().save_png("%s/lineup_%s.png" % [shots_dir, view])
	get_tree().quit()
