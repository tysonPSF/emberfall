extends Node
## Sound effects: the fight you can hear. Built by tools/audio/sfx.py into
## assets/sfx/<sound>_<n>.wav (several of each, one picked at random and
## pitched a little each time). Everything plays where it happens, in 3D,
## heard within MAX_DISTANCE of the camera; a dedicated server plays nothing.
##
## What triggers them, on every machine that draws the game:
##   Entity.animate: a swing ("slash", "chop"...) swooshes by its weapon, a
##     flinch ("hit") may draw a cry (now and then, never twice in a breath),
##     a bow shot twangs; "sfx:<sound>" events are sent by the rules for what
##     only the server knows: a blow landing ("sfx:hit_slash", "!" on the end
##     for a critical), a block or parry, an arrow striking, a monster coming
##     for you ("sfx:aggro").
##   World.spell_fx: a spell landing, by its look (SpellFx kinds).
##   SpellFx.update_cast: the hum while someone casts.
##   CharacterModel.pose_dead: a death cry.
##   your own level going up: the fanfare.
## A body's voice (humanoid, beast, bug...) and what it rings like when struck
## (flesh, bone, stone, metal) come from data/sfx.json by its mob id and model.
##
## Bus "Sfx" under Master, its volume Controls.sfx_volume.

const MAX_DISTANCE := 45.0
const POOL := 24
const HURT_EVERY := 1800  # msec: one body's cries, at most this often
const HURT_CHANCE := 0.35

var _sounds: Dictionary = {}  # sound name -> Array[AudioStream]
var _pool: Array[AudioStreamPlayer3D] = []
var _next := 0
var _ui: AudioStreamPlayer
var _casts: Dictionary = {}  # entity -> AudioStreamPlayer3D, the hum while they cast
var _hurt_at: Dictionary = {}  # entity id -> msec of its last cry
var _table: Dictionary = {}  # data/sfx.json
var _kinds: Dictionary = {}  # "voice:<key>" / "material:<key>" -> worked out once
var _level := -1  # the local player's, for the fanfare
var _silent := false
var heard: Array[String] = []  # the last sounds played, newest last (tests read it)


func _ready() -> void:
	_silent = "--server" in OS.get_cmdline_user_args()
	if AudioServer.get_bus_index("Sfx") < 0:
		AudioServer.add_bus()
		AudioServer.set_bus_name(AudioServer.bus_count - 1, "Sfx")
		AudioServer.set_bus_send(AudioServer.bus_count - 1, "Master")
	apply_volume()
	if _silent:
		set_process(false)
		return
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string("res://data/sfx.json"))
	_table = parsed if parsed is Dictionary else {}
	_index()
	for i in POOL:
		var p := AudioStreamPlayer3D.new()
		p.bus = "Sfx"
		p.unit_size = 7.0
		p.max_distance = MAX_DISTANCE
		p.attenuation_model = AudioStreamPlayer3D.ATTENUATION_INVERSE_DISTANCE
		p.panning_strength = 0.8
		add_child(p)
		_pool.append(p)
	_ui = AudioStreamPlayer.new()
	_ui.bus = "Sfx"
	add_child(_ui)
	World.spell_fx.connect(_on_spell_fx)


## Every assets/sfx/<name>_<n>.wav, by name. An exported game lists its
## imports (".wav.import"), so those count too.
func _index() -> void:
	var dir := "res://assets/sfx/"
	for f in DirAccess.get_files_at(dir):
		var file := f.trim_suffix(".import").trim_suffix(".remap")
		if not file.ends_with(".wav"):
			continue
		var base := file.get_basename()
		var cut := base.rfind("_")
		if cut <= 0 or not base.substr(cut + 1).is_valid_int():
			continue
		var name := base.left(cut)
		var list: Array = _sounds.get(name, [])
		if not list.any(func(s: Dictionary) -> bool: return s["path"] == dir + file):
			list.append({"path": dir + file, "stream": null})
		_sounds[name] = list


func _stream(name: String) -> AudioStream:
	var list: Array = _sounds.get(name, [])
	if list.is_empty():
		return null
	var pick: Dictionary = list.pick_random()
	if pick["stream"] == null:
		pick["stream"] = load(pick["path"])
	return pick["stream"]


func has_sound(name: String) -> bool:
	return _sounds.has(name)


## Sets the Sfx bus from Controls.sfx_volume (0..1); 0 mutes it. Test runs stay silent.
func apply_volume() -> void:
	var bus := AudioServer.get_bus_index("Sfx")
	var v := clampf(Controls.sfx_volume, 0.0, 1.0)
	var testing := Array(OS.get_cmdline_user_args()).any(func(a: String) -> bool:
		return a.begins_with("--autotest") or a.begins_with("--nettest") or a.begins_with("--lineup") or a.begins_with("--flowtest"))
	AudioServer.set_bus_mute(bus, v <= 0.001 or testing)
	AudioServer.set_bus_volume_db(bus, linear_to_db(maxf(v, 0.001)))


## Plays one of `name`'s variants at a point in the world; nothing past
## MAX_DISTANCE from the camera. Returns the player (null when nothing played).
func play_at(name: String, at: Vector3, gain_db := 0.0, pitch := 0.06) -> AudioStreamPlayer3D:
	if _silent or Net.dedicated or _pool.is_empty():
		return null
	var cam := get_viewport().get_camera_3d()
	if cam != null and cam.global_position.distance_to(at) > MAX_DISTANCE:
		return null
	var stream := _stream(name)
	if stream == null:
		return null
	var p: AudioStreamPlayer3D = null
	for k in POOL:  # a free one, else the one that started longest ago
		var c := _pool[(_next + k) % POOL]
		if not c.playing:
			p = c
			break
	if p == null:
		p = _pool[_next]
	_next = (_pool.find(p) + 1) % POOL
	heard.append(name)
	if heard.size() > 64:
		heard.remove_at(0)
	p.stream = stream
	p.global_position = at
	p.volume_db = gain_db
	p.pitch_scale = 1.0 + randf_range(-pitch, pitch)
	p.play()
	return p


## Plays on the entity, at chest height.
func play_on(e: Entity, name: String, gain_db := 0.0, pitch := 0.06) -> AudioStreamPlayer3D:
	if e == null or not is_instance_valid(e) or not e.is_inside_tree():
		return null
	return play_at(name, e.global_position + Vector3.UP * 1.1, gain_db, pitch)


## A sound for you alone, not in the world (the fanfare).
func play_ui(name: String, gain_db := 0.0) -> void:
	if _silent or Net.dedicated or _ui == null:
		return
	var stream := _stream(name)
	if stream != null:
		heard.append(name)
		_ui.stream = stream
		_ui.volume_db = gain_db
		_ui.play()


# --- what triggers them ---------------------------------------------------------

## Entity.animate calls this with every event it plays (and every "sfx:" one).
func on_anim(e: Entity, event: String) -> void:
	if _silent or Net.dedicated:
		return
	match event:
		"slash", "slash_off":
			play_on(e, "swing", -2.0)
		"thrust":
			play_on(e, "swing_light", -2.0)
		"chop", "kick", "bash":
			play_on(e, "swing_heavy", -1.0)
		"attack":
			play_on(e, "swing_claw" if _own_rig(e) else "swing_light", -3.0)
		"sling":
			play_on(e, "sling", -2.0)
		"hit":
			_maybe_cry(e)
		_ when event.begins_with("shoot"):
			play_on(e, "bow_release")
		_ when event.begins_with("sfx:"):
			_event(e, event.substr(4))


## The rules' own events: a blow landing (and how it rings on what it struck),
## a crit's weight, a block, a parry, a monster's challenge.
func _event(e: Entity, what: String) -> void:
	var crit := what.ends_with("!")
	what = what.trim_suffix("!")
	if what.contains("@"):  # "hit_arrow@24": struck from 24 m, heard when the arrow (Projectile.SPEED) arrives
		var meters := float(what.get_slice("@", 1))
		what = what.get_slice("@", 0)
		if meters > 2.0:
			await get_tree().create_timer(meters / Projectile.SPEED).timeout
			if not is_instance_valid(e):
				return
	if what == "aggro" or what == "death":
		voice(e, what)
		return
	play_on(e, what)
	if what.begins_with("hit_"):
		var mat := material_of(e)
		if mat != "flesh":
			play_on(e, "mat_" + mat, -3.0)
		if crit:
			play_on(e, "crit", 1.0, 0.03)


## Someone struck cries out, now and then (a long fight isn't a scream a second).
func _maybe_cry(e: Entity) -> void:
	if e.dead:
		return
	var now := Time.get_ticks_msec()
	if now - int(_hurt_at.get(e.entity_id, -HURT_EVERY)) < HURT_EVERY or randf() > HURT_CHANCE:
		return
	_hurt_at[e.entity_id] = now
	voice(e, "hurt")


## A body's cry: "aggro", "hurt" or "death", in its own voice.
func voice(e: Entity, what: String) -> void:
	if _silent or Net.dedicated or e == null or not is_instance_valid(e):
		return
	var v := "player" if e is Player else voice_of(e)
	if v == "player" and what == "aggro":
		return
	var name := "%s_%s" % [v, what]
	if not has_sound(name):
		name = "humanoid_" + what
	play_on(e, name, 0.0 if what != "hurt" else -2.0, 0.08)


## A spell landing: its look's sound where it lands (a heal on the healed,
## a fireball on its target).
func _on_spell_fx(from: Entity, to: Entity, spell_id: String) -> void:
	var s: Dictionary = GameData.spells.get(spell_id, {})
	if s.is_empty():
		return
	var kind := str(s.get("fx", {}).get("kind", SpellFx.DEFAULTS.get(str(s.get("type", "")), ["burst"])[0]))
	var name := "spell_" + kind
	if not has_sound(name):
		name = "spell_impact" if kind in ["impact", "burst"] else "spell_buff"
	var at: Entity = to if to != null and is_instance_valid(to) else from
	play_on(at, name, -1.0)


## The hum while e casts (SpellFx.update_cast tells us when it starts and stops).
func cast_changed(e: Entity, casting: bool) -> void:
	if _silent or Net.dedicated:
		return
	var p: AudioStreamPlayer3D = _casts.get(e)
	if casting and p == null:
		var stream := _stream("cast_loop")
		if stream == null:
			return
		if stream is AudioStreamWAV:  # made to wrap without a click (sfx.py hum)
			var w := stream as AudioStreamWAV
			w.loop_mode = AudioStreamWAV.LOOP_FORWARD
			w.loop_begin = 0
			w.loop_end = int(w.get_length() * w.mix_rate)
		p = AudioStreamPlayer3D.new()
		p.bus = "Sfx"
		p.stream = stream
		p.unit_size = 5.0
		p.max_distance = 30.0
		p.volume_db = -6.0
		e.add_child(p)
		p.position = Vector3.UP * 1.1
		p.play()
		_casts[e] = p
	elif not casting and p != null:
		_casts.erase(e)
		if is_instance_valid(p):
			p.queue_free()


func _process(_delta: float) -> void:
	var me := World.local_player
	if me == null or not is_instance_valid(me):
		_level = -1
		return
	if _level >= 0 and me.level > _level:
		play_ui("level_up")
	_level = me.level
	for e: Variant in _casts.keys():  # a caster gone mid-cast (zoned, slain)
		if not is_instance_valid(e):
			_casts.erase(e)


# --- who sounds like what ------------------------------------------------------

## A body's voice: humanoid (people, and the default), beast, small, bug,
## undead, big, stone, slime, bird (data/sfx.json "voices").
func voice_of(e: Entity) -> String:
	return _kind_of(e, "voice", "voices", "humanoid")


## What a body rings like when struck: flesh (the default), bone, stone, metal.
func material_of(e: Entity) -> String:
	return _kind_of(e, "material", "materials", "flesh")


func _kind_of(e: Entity, field: String, table: String, fallback: String) -> String:
	var id := ""
	var own := ""
	if e is Mob:
		id = (e as Mob).mob_id
		own = str(GameData.mobs.get(id, {}).get(field, ""))
	elif e is Npc:
		id = (e as Npc).npc_id
		own = str(GameData.npcs.get(id, {}).get(field, ""))
	elif e is Pet:
		id = str(e.look.get("model", "pet"))
	else:
		return fallback
	if own != "":
		return own
	var key := "%s:%s" % [field, id]
	if _kinds.has(key):
		return _kinds[key]
	var words := "%s %s" % [id, str(e.look.get("model", ""))]
	var tokens := words.replace(" ", "_").split("_", false)
	var found := fallback
	var lists: Dictionary = _table.get(table, {})
	for kind: String in lists:  # a word that starts one of the name's (spider: spiderling, not a croc's "roc"), or a "two_word" one anywhere
		if (lists[kind] as Array).any(func(w: String) -> bool:
				return words.contains(w) if w.contains("_") else Array(tokens).any(func(t: String) -> bool: return t.begins_with(w))):
			found = kind
			break
	_kinds[key] = found
	return found


func _own_rig(e: Entity) -> bool:
	var spec: Variant = GameData.models["characters"].get(str(e.look.get("model", "")), {})
	return spec is Dictionary and str((spec as Dictionary).get("rig", "")) == "own"
