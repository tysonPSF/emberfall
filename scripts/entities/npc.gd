class_name Npc
extends Entity
## A townsperson from data/npcs.json: stands at its post, can be hailed, and
## answers keywords. What they say, the quests they run, and whether a player
## may attack them (only after choosing to, at a faction cost) are rules in the
## World autoload.
##
## Anyone attacked fights back, chasing a little way from their post. NPCs with
## a "guard" block also keep the peace: they run down mobs chasing players,
## players who attack townsfolk, and players their faction wants dead (KOS),
## using the same melee rules as everyone else, then walk back to their post.
##
## A guard given a patrol (waypoints from the zone file) walks it back and
## forth at "walk_speed" instead of standing at a post, pausing at each end
## and stopping to talk when hailed. Guard options: "assist_standing" (only
## help players at least this well regarded by the guard's faction) and
## "hunt_radius" (attack any monster that comes this close; with
## "hunt_aggressive_only", only monsters that attack on sight or are in a
## fight).

const NAME_COLOR := Color(0.55, 0.85, 1.0)
const SCAN_SECONDS := 0.5
const RESPAWN_SECONDS := 120.0

var npc_id := ""
var data: Dictionary = {}
var guard: Dictionary = {}  # radius, leash, speed, shouts; empty for plain townsfolk
var _face_timer := 0.0
var _post := Vector3.ZERO
var _post_yaw := 0.0
var _scan_timer := 0.0
var patrol: Array[Vector3] = []  # waypoints walked end to end and back; empty for a post
var _leg := 1  # waypoint being walked to
var _leg_step := 1
var _pause := 0.0
var _torch_check := 0.0
var _torch_light: OmniLight3D  # the guard's torch, lit at night
var _anchor := Vector3.ZERO  # where the current fight began; the leash is measured from here
var grove_deity := ""  # a god of the Grove, or one of its attendants: shown only to those who've earned it (World.sees)
var quest_gated := false  # "until_quest" / "after_quest": shown only to those at that point in a quest (World.quest_shows)
var seated := ""  # "chair": sits at its post (npcs.json "seated"), standing only to fight
var only_for := ""  # a player's name: shown to them alone (a scene for one player: World.sees)
var walk_to := Vector3.INF  # walks here, then leaves (Merrick heading out of the tavern)
var follow_id := -1  # a companion: the player it follows and fights beside (World._check_companion)
var companion_pet := false  # follows but never fights (Velassa): no taunts, no foes
var _companion_speed := 5.5
var _taunt_left := 0.0
var _pounce: Entity = null  # Velassa: the monster she's leapt behind while her player is hurt (World.velassa_backstab)
var _stab_left := 0.0
var _sight_check := 0.0
var _mark: Label3D  # a floating "!" (a quest for you) or "?" (one ready to hand in), over the name
var _mark_check := 0.0
var _mark_time := 0.0
var _pester_mark: Npc  # "pester": the npc it harries (Squawkzilla round Queenie)
var _pester_angle := 0.0
var _pester_turn := 1.0  # which way round it's going
var _pester_dive := 0.0  # seconds left of a dive at its mark
var _pester_next := 4.0  # till the next dive
var _pester_line := 8.0  # till it next says something to those nearby
var _perch_left := 0.0  # landed for this long ("sitting": a creature's sit clips are its landing)
var _perch_next := 25.0  # till it next lands


func setup(id: String, name_override := "") -> void:
	npc_id = id
	data = GameData.npcs[id]
	display_name = name_override if name_override != "" else str(data["name"])
	level = int(data.get("level", 10))
	faction = str(data.get("faction", "town"))
	grove_deity = str(data.get("grove_deity", ""))
	quest_gated = data.has("until_quest") or data.has("after_quest") or data.has("until_started") or data.has("after_started")
	seated = str(data.get("seated", ""))
	sitting = seated != ""
	guard = data.get("guard", {})
	if not guard.is_empty():  # guards stay out of reach: always this far over the level cap
		level = int(World.cfg("max_level", 10)) + int(World.cfg("guard_levels_over_cap", 15))
	var combat: Dictionary = data.get("combat", {})
	max_hp = int(combat.get("hp", 1000))
	hp = max_hp
	hp_regen = int(combat.get("hp_regen", 10))
	ac = int(combat.get("ac", 20))
	var dmg: Array = combat.get("dmg", [2, 6])
	dmg_min = int(dmg[0])
	dmg_max = int(dmg[1])
	attack_delay = float(combat.get("delay", 2.5))
	if not guard.is_empty():  # a guard hits, lasts and turns blows like an elite of its level, whatever npcs.json typed long ago
		var dps := GameData.typical_beyond("dps", level) * float(World.cfg("guard_damage_mult", 3.0))
		var avg := dps * attack_delay
		dmg_min = maxi(dmg_min, roundi(avg * 0.7))
		dmg_max = maxi(dmg_max, roundi(avg * 1.3))
		max_hp = maxi(max_hp, roundi(GameData.typical_beyond("hp", level) * float(World.cfg("guard_health_mult", 10.0))))
		hp = max_hp
		ac = maxi(ac, roundi(level * 2.4))
	attack_verb = combat.get("verb", ["slash", "slashes"])


func _ready() -> void:
	var extra := {}
	var body_scale := 1.0
	if data.has("race"):  # a troll or a dark elf, say: their skin, height and bolt-ons on the class body
		extra["race"] = str(data["race"])
		body_scale = float(GameData.races.get(str(data["race"]), {}).get("scale", 1.0))
	if data.has("gender"):
		extra["gender"] = str(data["gender"])
	if data.has("hair"):  # [style, color] as a player's, "" keeps the body's own head: Queenie's brown
		extra["hair"] = data["hair"]
	var body := "prop:" + str(data["prop"]) if data.has("prop") else "humanoid"  # a thing, not a person: the spring crystal
	build_body(body, Color.WHITE, body_scale, str(data.get("model", "")), str(data.get("weapon", "")), extra)
	if Net.dedicated:
		set_process(false)  # _process only lights guards' torches after dark: looks, which a server doesn't draw
	nameplate.text = display_name
	nameplate.modulate = NAME_COLOR
	if data.get("unnamed", false):  # a thing, not a person (the apple barrel): no name floats over it
		nameplate.visible = false
	if data.has("title") or data.has("guild"):  # EQ-style second line: <Warrior Guildmaster>, or a guild tag like a player's
		var title := Label3D.new()
		title.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		title.fixed_size = true
		title.pixel_size = nameplate.pixel_size
		title.font_size = 24
		title.outline_size = 6
		title.text = "<%s>" % str(data.get("guild", data.get("title"))).replace("{owner}", only_for)  # Velassa: <Tyson's cat>
		title.modulate = Color(0.6, 1.0, 0.75) if data.has("guild") else Color(0.78, 0.82, 0.9)  # guild green, as Player.show_guild_tag
		title.offset = Vector2(0, -30)  # screen pixels below the name, at any distance
		title.visibility_range_end = nameplate.visibility_range_end
		title.name = "Title"
		nameplate.add_child(title)
	if data.has("night_form") and not Net.dedicated:  # June: by night she's someone else
		_form_night = false
		_check_form(false)
	if data.has("size"):  # giants (the Grove's gods): a pick shape and nameplate to match the model
		_resize(float(data["size"][0]), float(data["size"][1]))
	elif data.has("name_height"):  # a creature whose wings would hide its name
		nameplate.position.y = float(data["name_height"])
	if not Net.dedicated and npc_id in World.quest_mark_npcs():
		_mark = Label3D.new()
		_mark.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		_mark.fixed_size = true
		_mark.pixel_size = nameplate.pixel_size
		_mark.font_size = 104
		_mark.outline_size = 26
		_mark.outline_modulate = Color(1.0, 0.72, 0.1, 0.35)  # a soft golden halo round it
		_mark.shaded = false
		_mark.no_depth_test = false
		_mark.visibility_range_end = nameplate.visibility_range_end
		_mark.offset = Vector2(0, 70)  # screen pixels above the name
		_mark.visible = false
		nameplate.add_child(_mark)
	_post = global_position
	_post_yaw = rotation.y
	if data.has("prop_after") and World.local_player != null:
		_update_prop()  # the freed crystal is freed from the first frame, not half a second in


## A body as big as its model ("size": [radius, height] in npcs.json): the
## capsule you click grows to fit, the nameplate rides above the head, and a
## solid pillar on the WORLD layer stops players walking through it.
func _resize(radius: float, height: float) -> void:
	for c in get_children():
		if c is CollisionShape3D and c.shape is CapsuleShape3D:
			var cap := CapsuleShape3D.new()
			cap.radius = radius
			cap.height = maxf(height, radius * 2.0)
			(c as CollisionShape3D).shape = cap
			(c as CollisionShape3D).position.y = cap.height * 0.5
	body_height = height
	nameplate.position.y = height + 0.6
	var solid := StaticBody3D.new()
	solid.collision_layer = Layers.WORLD
	solid.collision_mask = 0
	var col := CollisionShape3D.new()
	var cyl := CylinderShape3D.new()
	cyl.radius = radius * 0.8
	cyl.height = height
	col.shape = cyl
	col.position.y = height * 0.5
	solid.add_child(col)
	add_child(solid)
	add_collision_exception_with(solid)


## Offline, a god you haven't earned stands in the Grove unseen and unclickable,
## as does an npc a quest has moved on (online the server never sends either:
## Net._replicate).
func _update_sight() -> void:
	var shown := World.sees(World.local_player, self)
	if visual.visible == shown and nameplate.visible == shown:
		return
	visual.visible = shown and not dead
	nameplate.visible = shown and not dead
	collision_layer = Layers.ENTITIES if shown else 0
	for c in get_children():
		if c is StaticBody3D:
			(c as StaticBody3D).collision_layer = Layers.WORLD if shown else 0


## The floating quest mark: checked twice a second against your quests, and
## bobbing and glowing gently while it shows.
var _mark_more := false
var _mark_repeat := false  # the mark is for a repeatable quest you have done


func _update_mark(delta: float) -> void:
	_mark_check -= delta
	if _mark_check <= 0.0:
		_mark_check = 0.5
		var m := World.quest_mark(World.local_player, npc_id) if not dead else ""
		_mark.text = m.left(1)
		_mark.visible = m != ""
		_mark_repeat = m.ends_with("r")  # a repeatable you've done: blue, "!" to do it again, "?" when you carry it all
		_mark_more = m == "!" and World.quest_mark_more(World.local_player, npc_id)  # more of their work: gray
	if not _mark.visible:
		return
	_mark_time += delta
	_mark.offset.y = 70.0 + sin(_mark_time * 2.4) * 8.0  # floating
	var glow := 0.85 + 0.15 * sin(_mark_time * 3.1)
	if _mark_repeat:
		_mark.modulate = Color(0.4, 0.72, 1.0) * ((1.15 if _mark.text == "?" else 0.95) * glow)  # blue: again, any time
	elif _mark_more:
		_mark.modulate = Color(0.72, 0.72, 0.74) * (0.95 + 0.05 * glow)  # gray, and barely breathing: you've taken something here
	else:
		_mark.modulate = Color(1.0, 0.86, 0.22) * (1.25 * glow) if _mark.text == "!" else Color(1.0, 0.95, 0.6) * (1.1 * glow)
	_mark.modulate.a = 1.0
	var halo := Color(0.3, 0.6, 1.0) if _mark_repeat else (Color(0.6, 0.6, 0.62) if _mark_more else Color(1.0, 0.72, 0.1))  # its halo in its own color
	_mark.outline_modulate = Color(halo, 0.22 + 0.2 * glow)  # and breathing with it


## How a seated npc sits for whoever is watching: "seated_after" {quest: action}
## changes it once the local player has finished that quest (Merrick sits up
## eager once you've brought the sinew; he stays grumpy for everyone else).
func seated_clip() -> String:
	var after: Dictionary = data.get("seated_after", {})
	var p := World.local_player
	if p != null:
		for quest_id: String in after:
			if World.quest_done(p, quest_id):
				return str(after[quest_id])
	return "sit_chair"


## A thing that changes with the watcher's quest ("prop_after" {quest: prop}):
## the spring crystal is cocooned in webs until you've freed it, then clean
## and shining ("light_after", a color), for you alone. Only a picture.
func _update_prop() -> void:
	var want := str(data.get("prop", ""))
	var lit := false
	var after: Dictionary = data["prop_after"]
	for quest_id: String in after:
		if World.quest_done(World.local_player, quest_id):
			want = str(after[quest_id])
			lit = true
	for stage: Array in data.get("prop_stages", []):  # the apple barrel: lower each few apples you've taken
		if World.apples_taken(World.local_player) >= int(stage[0]):
			want = str(stage[1])
	if str(look.get("shape", "")) == "prop:" + want:
		return
	look["shape"] = "prop:" + want
	var was_visible := visual.visible
	visual.queue_free()
	visual = make_visual(look)
	visual.visible = was_visible
	add_child(visual)
	var glow := get_node_or_null("Glow") as OmniLight3D
	if lit and data.has("light_after") and glow == null:
		glow = OmniLight3D.new()
		glow.name = "Glow"
		glow.light_color = Color.html(str(data["light_after"]))
		var light_size: Array = data.get("light_size", [2.5, 26.0, 4.0])  # [energy, range, height]: a city lamp is smaller than the spring crystal
		glow.light_energy = float(light_size[0])
		glow.omni_range = float(light_size[1])
		glow.position = Vector3(0, float(light_size[2]), 0)
		add_child(glow)
	elif not lit and glow != null:
		glow.queue_free()


## Turns to face whoever is talking to it for a while, then back to its post.
func greet(who: Entity) -> void:
	if data.get("fixed", false):
		return  # a god on its dais doesn't swing round to look at you
	face_toward(who.global_position)
	_face_timer = 12.0


## Guards carry a torch in the left hand from sunset to sunrise (outdoors).
## Only a picture, so every machine decides from its own clock.
## An npc with a "night_form" (June the unicorn by day, Fresnebagcdrs the elf
## after dark: {name, title, model, race, gender, hair, attach, scale,
## dialogue}) is that other self while it's night. The hour comes from the
## shared clock, so the server (her name, her lines) and every client (her
## body) agree without a message.
var _form_night := false
var _form_check := 0.0


func is_night_form() -> bool:
	return data.has("night_form") and World.is_night()


## What she's like now: npcs.json's entry, with the night form's over it after dark.
func form() -> Dictionary:
	if not is_night_form():
		return data
	var d := data.duplicate()
	d.merge(data["night_form"], true)
	return d


## Her name as it is now (the server's lines say it).
func shown_name() -> String:
	return str(form().get("name", display_name)) if data.has("night_form") else display_name


## Turns into the other self when the hour has crossed dusk or dawn: a new body, name and
## title, with a burst of rainbow light (when `fx`).
func _check_form(fx: bool) -> void:
	var night := is_night_form()
	if night == _form_night and fx:
		return
	_form_night = night
	var f := form()
	var extra := {}
	var body_scale := float(f.get("scale", 1.0))
	if f.has("race"):
		extra["race"] = str(f["race"])
		body_scale *= float(GameData.races.get(str(f["race"]), {}).get("scale", 1.0))
	if f.has("gender"):
		extra["gender"] = str(f["gender"])
	if f.has("hair"):
		extra["hair"] = f["hair"]
	var new_look := {"shape": "humanoid", "color": "#ffffff", "scale": body_scale, "model": str(f.get("model", "")), "weapon": ""}
	new_look.merge(extra, true)
	if visual != null:
		visual.queue_free()
	look = new_look
	visual = make_visual(look)
	add_child(visual)
	if visual is CharacterModel:
		for part_id: String in f.get("attach", []):
			(visual as CharacterModel).pin_part(part_id)
	display_name = str(f.get("name", data["name"]))
	show_name()
	var title := nameplate.get_node_or_null("Title") as Label3D
	if title != null:
		title.text = "<%s>" % str(f.get("title", ""))
	nameplate.position.y = float(f.get("name_height", body_height + 0.45))
	if fx:
		for c: String in ["#ff9ae8", "#8ad8ff", "#ffe27a"]:  # a shimmer of rainbow light
			var burst := SpellFx.new()
			add_child(burst)
			burst._build("burst", Color.html(c), self)


func _process(delta: float) -> void:
	if _mark != null:
		_update_mark(delta)
	if data.has("night_form"):
		_form_check -= delta
		if _form_check <= 0.0:
			_form_check = 1.0
			_check_form(true)
	if data.has("pester") and data.has("name_height"):  # landed, the name comes down with it
		var h := float(data["name_height"]) * (0.6 if sitting else 1.0)
		nameplate.position.y = move_toward(nameplate.position.y, h, delta * 2.0)
	if (grove_deity != "" or quest_gated or data.has("prop_after")) and World.local_player != null:
		_sight_check -= delta
		if _sight_check <= 0.0:
			_sight_check = 0.5
			if Net.is_authority() and (grove_deity != "" or quest_gated):
				_update_sight()
			if data.has("prop_after"):
				_update_prop()
	_torch_check -= delta
	if _torch_check > 0.0 or guard.is_empty() or not (visual is CharacterModel):
		return
	_torch_check = 1.0
	var z := World.zone_of(self)
	var want := not dead and z != null and not bool(z.data.get("interior", false)) and DayNight.sun_height(World.game_hour()) < 0.0
	if want == (_torch_light != null):
		return
	(visual as CharacterModel).set_offhand("torch" if want else "")
	if want:
		_torch_light = OmniLight3D.new()
		_torch_light.light_color = Color(1.0, 0.62, 0.3)
		_torch_light.light_energy = 1.3
		_torch_light.omni_range = 7.0
		_torch_light.position = Vector3(0, 1.9, 0)
		add_child(_torch_light)
	else:
		_torch_light.queue_free()
		_torch_light = null


func _physics_process(delta: float) -> void:
	if not Net.is_authority():
		puppet(delta)
		return
	apply_gravity(delta)
	var move := Vector3.ZERO
	var speed := float(guard.get("speed", 5.5))
	if follow_id >= 0:  # a companion (Watchman Corran in the Wellspring): follows its player, fights beside them
		if not dead:
			move = _think_companion(delta)
		speed = _companion_speed
	elif not dead:
		move = _think(delta)
	if not patrol.is_empty() and not auto_attack:
		speed = float(guard.get("walk_speed", 2.0))
	if data.has("pester") and auto_attack:
		sitting = false  # up off the ground to fight
	if data.has("pester") and not auto_attack:
		speed = float(data["pester"].get("speed", 4.5)) * (1.6 if _pester_dive > 0.0 else 1.0)
	if walk_to != Vector3.INF and not dead:  # on its way out: walks to the door and is gone
		if _flat(global_position, walk_to) < 0.9:
			queue_free()
			return
		move = nav_dir(walk_to, delta)
		speed = 2.6
	velocity.x = move.x * speed
	velocity.z = move.z * speed
	if move != Vector3.ZERO or not is_on_floor():  # standing still on the ground needs no collision sweep
		move_and_slide()
	if move != Vector3.ZERO:
		face_toward(global_position + move)  # walks forward, even on a path around something; faces its target once in reach
	if seated != "" and not auto_attack and not dead and move == Vector3.ZERO:
		sitting = true  # back in the chair once the fight's over
	if _face_timer > 0.0 and not auto_attack:
		_face_timer -= delta
		if _face_timer <= 0.0:
			rotation.y = _post_yaw


## Returns the direction to walk this frame (zero to stand still).
func _think(delta: float) -> Vector3:
	if auto_attack:
		var t := valid_target_entity()
		if t == null or _flat(t.global_position, _anchor) > float(guard.get("leash", 20.0)):
			auto_attack = false
			target = null
			return Vector3.ZERO
		face_toward(t.global_position)
		return nav_dir(t.global_position, delta) if distance_to(t) > World.melee_range() * 0.7 else Vector3.ZERO
	if data.has("pester"):
		return _pester(delta)
	_scan_timer -= delta
	if not patrol.is_empty():
		if _scan_timer <= 0.0:
			_scan_timer = SCAN_SECONDS
			_look_for_trouble()
		return _walk_patrol(delta)
	if _flat(global_position, _post) > 0.8:
		var dir := nav_dir(_post, delta)
		if _flat(global_position, _post) < 1.5:
			rotation.y = _post_yaw
		return dir
	if _scan_timer <= 0.0 and not guard.is_empty():
		_scan_timer = SCAN_SECONDS
		_look_for_trouble()
	return Vector3.ZERO


## A companion's turn (World._check_companion makes them). It never leads:
## it keeps a few steps behind its player and only fights what is fighting
## either of them, or what the player is attacking; it stops when they stop,
## sits when they sit, runs to catch up when left behind, and drops a fight
## that pulls it far from them.
func _think_companion(delta: float) -> Vector3:
	var lead := World.get_object(follow_id) as Player
	_companion_speed = 5.5
	if lead == null or lead.dead or World.zone_of(lead) != World.zone_of(self):
		auto_attack = false
		target = null
		return Vector3.ZERO
	var apart := _flat(global_position, lead.global_position)
	if apart > 45.0:  # lost (a long fall, a wrong turn): back to their side
		global_position = lead.global_position + lead.global_transform.basis.z * 2.0  # a step behind them (clients follow npc positions as sent)
		return Vector3.ZERO
	if companion_pet:  # Velassa: at your heel, or curled up beside you when you stop
		auto_attack = false
		if _pounce_on(lead) != null:
			return _pounce_move(lead, delta)
		var gap := _flat(global_position, lead.global_position)
		if gap > 2.6:
			sitting = false
			_companion_speed = 8.0 if gap > 9.0 else 5.6
			return nav_dir(lead.global_position, delta)
		if gap < 1.1:
			sitting = false
			_companion_speed = 2.5
			var away := Vector3(global_position.x - lead.global_position.x, 0, global_position.z - lead.global_position.z)
			return away.normalized() if away.length() > 0.1 else lead.global_transform.basis.z
		sitting = lead.velocity.length() < 0.3
		return Vector3.ZERO
	if auto_attack:
		var t := valid_target_entity()
		if t == null or t.dead or _flat(t.global_position, lead.global_position) > 25.0:
			auto_attack = false
			target = null
		else:
			# Once he can reach it he holds his ground, so walking round the fight
			# (to see him past a big boss and heal him) doesn't drag him round with
			# you. Getting in, he takes the monster's flank, off to one side of
			# the line between it and you, and never stands inside you.
			sitting = false
			_companion_speed = 6.2
			# A tank for a healer: every few seconds he takes back whatever is on
			# you, and makes sure what he's fighting is fighting him.
			_taunt_left -= delta
			if _taunt_left <= 0.0:
				_taunt_left = 3.0
				var on_you := _mob_on(lead)
				if on_you != null and on_you != t:
					_engage(on_you)
					t = on_you
				if t is Mob:
					_taunt(t as Mob)
			face_toward(t.global_position)
			if distance_to(t) <= World.melee_range() * 0.85 and _flat(global_position, lead.global_position) > 1.6:
				return Vector3.ZERO
			var line := Vector3(t.global_position.x - lead.global_position.x, 0, t.global_position.z - lead.global_position.z)
			if line.length() < 0.3:
				line = -t.global_transform.basis.z
			var side := line.normalized().cross(Vector3.UP)
			if side.dot(global_position - t.global_position) < 0.0:
				side = -side  # the flank on his side of it: no walking round
			var spot := nav_snap(t.global_position + (side * 0.85 + line.normalized() * 0.5).normalized() * 1.8)
			return nav_dir(spot, delta)
	_scan_timer -= delta
	if _scan_timer <= 0.0:
		_scan_timer = 0.3
		var foe := _companion_foe(lead)
		if foe != null:
			_engage(foe)
			return Vector3.ZERO
	if apart > 3.5:  # follow, a few steps behind
		sitting = false
		_companion_speed = 7.0 if apart > 12.0 else 5.5
		return nav_dir(lead.global_position, delta)
	if apart < 1.6:  # never stands inside you: a step back out of your way
		sitting = false
		_companion_speed = 3.0
		var off := Vector3(global_position.x - lead.global_position.x, 0, global_position.z - lead.global_position.z)
		if off.length() < 0.2:
			off = lead.global_transform.basis.z
		return nav_dir(nav_snap(lead.global_position + off.normalized() * 2.6), delta)
	if lead.sitting and not sitting:  # resting with you
		sitting = true
	elif not lead.sitting and sitting:
		sitting = false
	return Vector3.ZERO


## Velassa's rogue side: when her player falls under velassa_pounce_below
## (35%) health with a monster on them, she leaps in behind it and backstabs it
## every velassa_stab_seconds until it's dead, it lets them be, or they're back
## over velassa_pounce_until (60%). Returns the monster, or null.
func _pounce_on(lead: Player) -> Entity:
	if _pounce != null and (not is_instance_valid(_pounce) or _pounce.dead or lead.hp > lead.max_hp * float(World.cfg("velassa_pounce_until", 0.6)) \
			or _flat(_pounce.global_position, lead.global_position) > 25.0 or (_pounce is Mob and (_pounce as Mob).top_hated() != lead)):
		_pounce = null
	if _pounce == null and lead.hp < lead.max_hp * float(World.cfg("velassa_pounce_below", 0.35)):
		_pounce = _mob_on(lead)
		if _pounce != null:
			_stab_left = 0.0
			velocity.y = 5.5  # the leap
			World.say(lead, "Velassa hisses and leaps into the fight!", World.C_PET_HIT)
	return _pounce


## Into the gap behind her monster's back, then a backstab each time her timer comes round.
func _pounce_move(lead: Player, delta: float) -> Vector3:
	sitting = false
	_stab_left -= delta
	var back := nav_snap(_pounce.global_position + _pounce.global_transform.basis.z * 1.4)  # its face is -Z
	if _flat(global_position, back) > 0.6:
		_companion_speed = 11.0
		return nav_dir(back, delta)
	face_toward(_pounce.global_position)
	if _stab_left <= 0.0:
		_stab_left = float(World.cfg("velassa_stab_seconds", 4.0))
		World.velassa_backstab(self, _pounce, lead)
	return Vector3.ZERO


## A monster near p that is going for p (p on top of its hate).
func _mob_on(lead: Player) -> Mob:
	for m in World.get_mobs():
		if not m.dead and World.zone_of(m) == World.zone_of(self) and _flat(m.global_position, lead.global_position) < 20.0 and m.top_hated() == lead:
			return m
	return null


## Puts this companion on top of m's hate, as a pet's taunt does.
func _taunt(m: Mob) -> void:
	var top := 0.0
	for v: float in m.hate.values():
		top = maxf(top, v)
	if float(m.hate.get(entity_id, 0.0)) < top + 5.0:
		m.hate[entity_id] = top + 15.0


## What a companion should fight: what its player is attacking, else whatever
## is fighting its player or itself nearby. Never a monster minding its own business.
func _companion_foe(lead: Player) -> Mob:
	var t := lead.valid_target_entity()
	if t is Mob and not t.dead and (lead.auto_attack or (t as Mob).hate.has(lead.entity_id)) and _flat(t.global_position, lead.global_position) < 25.0:
		return t as Mob
	for m in World.get_mobs():
		if m.dead or World.zone_of(m) != World.zone_of(self) or _flat(m.global_position, lead.global_position) > 20.0:
			continue
		if m.hate.has(lead.entity_id) or m.hate.has(entity_id):
			return m
	return null


## "pester" ({npc, radius, speed, lines}): it runs rings round another npc,
## the way it likes, now and then diving in to peck at them (they flinch and
## turn on it), landing beside them every half minute or so (and whenever
## someone talks to it: its "sit" clips are the landing), and every so often one of its "lines" goes out to everyone
## within earshot ({gull} and {mark} are their names). Quiet while you talk
## to it; a fight comes first.
func _pester(delta: float) -> Vector3:
	var spec: Dictionary = data["pester"]
	if _pester_mark == null or not is_instance_valid(_pester_mark):
		_pester_mark = null
		var z := World.zone_of(self)
		for c in (z.get_children() if z != null else []):
			if c is Npc and (c as Npc).npc_id == str(spec["npc"]):
				_pester_mark = c
		if _pester_mark == null:
			return nav_dir(_post, delta) if _flat(global_position, _post) > 0.8 else Vector3.ZERO
	if _face_timer > 0.0:  # someone's talking to it: it lands, and stays down a moment after
		_perch_left = maxf(_perch_left, 2.0)
		sitting = true
		return Vector3.ZERO
	var m := _pester_mark
	if _perch_left > 0.0:  # landed: glaring about, till it takes off again
		_perch_left -= delta
		if _perch_left <= 0.0:
			sitting = false
			_perch_next = randf_range(25.0, 45.0)
		return Vector3.ZERO
	_perch_next -= delta
	if _perch_next <= 0.0 and _pester_dive <= 0.0:
		_perch_left = randf_range(6.0, 12.0)
		sitting = true
		face_toward(m.global_position)
		return Vector3.ZERO
	var to_me := Vector3(global_position.x - m.global_position.x, 0, global_position.z - m.global_position.z)
	_pester_line -= delta
	if _pester_dive > 0.0:  # in at them
		_pester_dive -= delta
		if to_me.length() < 1.4 or _pester_dive <= 0.0:
			_pester_dive = 0.0
			face_toward(m.global_position)
			animate("attack")
			m.face_toward(global_position)
			m.animate("hit")
			m._face_timer = 2.5  # glares after it a moment, then back to her work
			_pester_angle = atan2(to_me.z, to_me.x)
			if randf() < 0.3:
				_pester_turn = -_pester_turn
			if _pester_line <= 0.0:
				_pester_line = randf_range(18.0, 32.0)
				var lines: Array = spec.get("lines", [])
				if not lines.is_empty():
					var text := str(lines.pick_random()).replace("{gull}", display_name).replace("{mark}", m.display_name.get_slice(" ", m.display_name.get_slice_count(" ") - 1))
					for q in World.get_players():
						if q.distance_to(self) <= World.SAY_RANGE:
							World.say(q, text, World.C_EMOTE)
			return Vector3.ZERO
		return nav_dir(m.global_position, delta)
	_pester_next -= delta
	if _pester_next <= 0.0:
		_pester_next = randf_range(5.0, 10.0)
		_pester_dive = 2.0
	var r := float(spec.get("radius", 3.5))
	_pester_angle += delta * _pester_turn * float(spec.get("speed", 4.5)) * 0.7 / r
	var reach := r * (1.0 + 0.3 * sin(_pester_angle * 2.3))  # loops wide and tight
	var spot := m.global_position + Vector3(cos(_pester_angle), 0, sin(_pester_angle)) * reach
	if _flat(global_position, spot) < 0.4:
		return Vector3.ZERO
	return nav_dir(spot, delta)


## Next step along the patrol: on to the next waypoint, turning back at either
## end after a pause, and standing still while talking to someone.
func _walk_patrol(delta: float) -> Vector3:
	if _face_timer > 0.0 or patrol.size() < 2:
		return Vector3.ZERO
	if _pause > 0.0:
		_pause -= delta
		return Vector3.ZERO
	var goal := patrol[_leg]
	if _flat(global_position, goal) < 1.0:
		if _leg + _leg_step < 0 or _leg + _leg_step >= patrol.size():
			_leg_step = -_leg_step
			_pause = float(guard.get("patrol_pause", 5.0))
		_leg += _leg_step
		return Vector3.ZERO
	return nav_dir(goal, delta)


## Hit by someone: fight back (and a townsperson calls the guards).
func add_hate(src: Entity, _amount: float) -> void:
	if dead or src == null or src.dead or (auto_attack and valid_target_entity() != null):
		return
	if src is Player:
		(src as Player).hostile_npcs[entity_id] = true
	fight(src)
	World.call_guards(self, src)


## Turns on someone: targets and swings at them until they fall, flee past the
## leash, or it's knocked out.
func fight(who: Entity, shout := false) -> void:
	_engage(who)
	if shout and who is Player:
		var lines: Array = guard.get("shouts_player", ["Stop right there, {name}!"])
		World.shout(self, "%s shouts, '%s'" % [display_name, str(lines[randi() % lines.size()]).format({"name": who.display_name})])


func _engage(who: Entity) -> void:
	target = who
	auto_attack = true
	sitting = false
	_face_timer = 0.0
	_anchor = global_position if not patrol.is_empty() else _post


## Engages the nearest mob within reach that is chasing or fighting a player
## the guard is willing to help; failing that, a player to arrest; failing
## that, any monster inside the hunt radius.
func _look_for_trouble() -> void:
	var radius := float(guard.get("radius", 22.0))
	var best: Mob = null
	var victim: Player = null
	for m in World.get_mobs():
		if m.dead or distance_to(m) > radius or not (m.state in [Mob.State.COMBAT, Mob.State.FLEE]):
			continue
		var t := m.top_hated()
		if t is Player and _will_assist(t as Player) and (best == null or distance_to(m) < distance_to(best)):
			best = m
			victim = t
	if best != null:
		_engage(best)
		_shout("shouts", victim.display_name, best.display_name)
		return
	for p in World.get_players():  # players this faction wants dead, or who attacked townsfolk
		if p.dead or p.hidden or p.feigning or distance_to(p) > radius:
			continue
		if World.npc_kos(p, faction) or not p.hostile_npcs.is_empty():
			fight(p, true)
			return
	var hunt := float(guard.get("hunt_radius", 0.0))
	var only_aggressive := bool(guard.get("hunt_aggressive_only", false))  # leave rats and bears be
	for m in World.get_mobs():
		var hostile := m.aggressive or m.state == Mob.State.COMBAT  # attacks on sight, or is fighting someone right now
		if not m.dead and distance_to(m) <= hunt and (hostile or not only_aggressive) \
				and (best == null or distance_to(m) < distance_to(best)):
			best = m
	if best != null:
		_engage(best)
		_shout("hunt_shouts", "", best.display_name)


func _will_assist(p: Player) -> bool:
	return not guard.has("assist_standing") or World.standing(p, faction) >= int(guard["assist_standing"])


func _shout(key: String, who: String, mob: String) -> void:
	var lines: Array = guard.get(key, [])
	if not lines.is_empty():
		var line := str(lines[randi() % lines.size()]).format({"name": who, "mob": mob})
		World.shout(self, "%s shouts, '%s'" % [display_name, line])


## Called by World.kill: falls, then returns to its post a while later.
func on_killed() -> void:
	target = null
	if visual is CharacterModel:
		(visual as CharacterModel).pose_dead()
	if follow_id >= 0:  # a companion lies there a moment, then is gone (World._check_companion brings him back later)
		get_tree().create_timer(6.0).timeout.connect(queue_free)
		return
	get_tree().create_timer(RESPAWN_SECONDS).timeout.connect(_return_to_post)


func _return_to_post() -> void:
	dead = false
	hp = max_hp
	global_position = _post
	rotation.y = _post_yaw
	_leg = 1
	_leg_step = 1
	visual.queue_free()
	visual = make_visual(look)
	add_child(visual)
	stats_changed.emit()


func _dir_to(pos: Vector3) -> Vector3:
	var d := pos - global_position
	d.y = 0.0
	return d.normalized() if d.length_squared() > 0.0001 else Vector3.ZERO


static func _flat(a: Vector3, b: Vector3) -> float:
	return Vector2(a.x, a.z).distance_to(Vector2(b.x, b.z))
