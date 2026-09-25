extends Node
## Zone music, EverQuest style: each zone has a theme that loops while you're
## there ("music" in data/zones/<id>.json, a track in assets/music/), the title
## screen has its own, and moving between them crossfades. When a monster has
## you on its hate list (Player.threatened, set by the server) the combat
## theme fades in over the zone's, which fades out and waits; a few calm
## seconds after the last threat is gone they trade back. The tracks are
## composed by tools/audio/music.py.
##
## Buses: "MusicZone" and "MusicCombat" both feed "Music", whose volume is
## Controls.music_volume. A dedicated server plays nothing.

const FADE := 2.0  # between zone themes
const COMBAT_IN := 1.2
const COMBAT_OUT := 3.0
const CALM_SECONDS := 4.0  # out of danger this long before the zone theme returns

var _players: Array[AudioStreamPlayer] = []  # two zone players, for crossfades
var _combat: AudioStreamPlayer
var _current := ""
var _active := 0
var _in_combat := false
var _calm := 0.0
var _duck: Tween
var _mix := 0.0  # 0 = zone theme, 1 = combat theme
var _combat_stream: AudioStreamOggVorbis


func _ready() -> void:
	_bus("Music", "Master")
	_bus("MusicZone", "Music")
	_bus("MusicCombat", "Music")
	_set_mix(0.0)
	for i in 2:
		var p := AudioStreamPlayer.new()
		p.bus = "MusicZone"
		p.volume_db = -80.0
		add_child(p)
		_players.append(p)
	_combat = AudioStreamPlayer.new()
	_combat.bus = "MusicCombat"
	add_child(_combat)
	_combat_stream = _load("combat")  # ready ahead of the first fight, so it starts on the instant
	apply_volume()


func _bus(bus_name: String, send: String) -> void:
	if AudioServer.get_bus_index(bus_name) >= 0:
		return
	AudioServer.add_bus()
	AudioServer.set_bus_name(AudioServer.bus_count - 1, bus_name)
	AudioServer.set_bus_send(AudioServer.bus_count - 1, send)


## Sets the Music bus from Controls.music_volume (0..1); 0 mutes it. Test runs
## (autotest, nettest, lineup, flowtest) stay silent but still play.
func apply_volume() -> void:
	var bus := AudioServer.get_bus_index("Music")
	var v := clampf(Controls.music_volume, 0.0, 1.0)
	var testing := Array(OS.get_cmdline_user_args()).any(func(a: String) -> bool:
		return a.begins_with("--autotest") or a.begins_with("--nettest") or a.begins_with("--lineup") or a.begins_with("--flowtest"))
	AudioServer.set_bus_mute(bus, v <= 0.001 or testing)
	AudioServer.set_bus_volume_db(bus, linear_to_db(maxf(v, 0.001)))


## Plays a track by name (assets/music/<name>.ogg), crossfading from whatever
## is on. The same track again keeps playing where it is.
func play(track: String) -> void:
	if "--server" in OS.get_cmdline_user_args() or track == _current:
		return
	var stream := _load(track)
	if stream == null:
		return
	_current = track
	var old := _players[_active]
	_active = 1 - _active
	var new := _players[_active]
	new.stream = stream
	new.volume_db = -80.0
	new.play()
	var was_playing := old.playing
	var tw := create_tween()
	tw.tween_method(func(t: float) -> void:
		new.volume_db = _gain_db(sin(t * PI / 2.0))
		if was_playing:
			old.volume_db = _gain_db(cos(t * PI / 2.0)), 0.0, 1.0, FADE)
	if was_playing:
		tw.tween_callback(old.stop)


## Equal-power crossfades: one side's gain is cos, the other's sin, so the sum
## stays as loud all the way through (fading both in decibels leaves a hole
## in the middle that sounds like a pause).
static func _gain_db(gain: float) -> float:
	return linear_to_db(maxf(gain, 0.0001))


## The theme for a zone: its "music", else a track named after it.
func play_zone(zone_data: Dictionary, zone_id: String) -> void:
	play(str(zone_data.get("music", zone_id)))


func _load(track: String) -> AudioStreamOggVorbis:
	var path := "res://assets/music/%s.ogg" % track
	if not ResourceLoader.exists(path):
		return null
	var stream := load(path) as AudioStreamOggVorbis
	stream.loop = true
	return stream


func _process(delta: float) -> void:
	var p := World.local_player
	var threat := p != null and is_instance_valid(p) and p.threatened and not p.dead
	if threat:
		_calm = 0.0
		if not _in_combat:
			_set_combat(true)
	elif _in_combat:
		_calm += delta
		if _calm >= CALM_SECONDS:
			_set_combat(false)


## Trades the zone theme for the combat theme (or back) by fading their buses.
## The zone theme keeps playing underneath, so it picks up where it was.
func _set_combat(on: bool) -> void:
	_in_combat = on
	if on and not _combat.playing:
		if _combat_stream == null:
			return
		_combat.stream = _combat_stream
		_combat.play()
	if _duck != null and _duck.is_valid():
		_duck.kill()
	var target := 1.0 if on else 0.0
	var time := (COMBAT_IN if on else COMBAT_OUT) * absf(target - _mix)  # a fade cut short turns back from where it was
	_duck = create_tween()
	_duck.tween_method(_set_mix, _mix, target, maxf(time, 0.05))
	if not on:
		_duck.tween_callback(_combat.stop)  # the next fight starts the theme from the top


func _set_mix(m: float) -> void:
	_mix = m
	AudioServer.set_bus_volume_db(AudioServer.get_bus_index("MusicZone"), _gain_db(cos(m * PI / 2.0)))
	AudioServer.set_bus_volume_db(AudioServer.get_bus_index("MusicCombat"), _gain_db(sin(m * PI / 2.0)))
