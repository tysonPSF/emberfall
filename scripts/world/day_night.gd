class_name DayNight
extends Node
## An outdoor zone's sky through the day: the sun crosses from east to west,
## warms at dawn and dusk and sets; a blue moon lights the night. Sky, fog and
## ambient light follow. The zone's own colors (sun_energy, fog_color) are its
## midday; night is the same everywhere. Lights in the "night_lights" group
## (lit windows, guards' torches) fade in after dusk and out after dawn.

const NIGHT_SKY_TOP := Color(0.03, 0.045, 0.11)
const NIGHT_SKY_HORIZON := Color(0.09, 0.12, 0.2)
const NIGHT_FOG := Color(0.07, 0.09, 0.15)
const MOON_COLOR := Color(0.62, 0.72, 1.0)
const MOON_ENERGY := 0.5
const DUSK_COLOR := Color(1.0, 0.56, 0.3)
const SUNRISE := 6.0
const SUNSET := 20.0
const NIGHT_AMBIENT := 1.5  # the night sky is dark, so the ambient it gives is turned up to stay playable

var env: Environment
var sky_mat: ProceduralSkyMaterial
var sun: DirectionalLight3D
var moon: DirectionalLight3D
var _day: Dictionary = {}  # the zone's midday values
var _timer := 0.0


func setup(environment: Environment, sky_material: ProceduralSkyMaterial, sun_light: DirectionalLight3D) -> void:
	env = environment
	sky_mat = sky_material
	sun = sun_light
	_day = {"top": sky_mat.sky_top_color, "horizon": sky_mat.sky_horizon_color, "fog": env.fog_light_color,
			"sun": sun.light_energy, "ambient": env.ambient_light_energy}
	moon = DirectionalLight3D.new()
	moon.light_color = MOON_COLOR
	moon.shadow_enabled = true
	moon.directional_shadow_max_distance = 50.0
	moon.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS  # soft moonlight needs less detail than the sun
	moon.rotation_degrees = Vector3(-55.0, 150.0, 0.0)
	moon.light_angular_distance = 1.2  # a small disc in the sky
	sun.add_sibling.call_deferred(moon)
	update(true)


func _process(delta: float) -> void:
	_timer -= delta
	if _timer <= 0.0:
		_timer = 0.25
		update()


## How high the sun is for an hour: 0 at sunrise (6:00) and sunset (20:00),
## 1 at 13:00, down to -1 at 1:00; twilight lasts about an hour either side.
static func sun_height(hour: float) -> float:
	var h := fposmod(hour - SUNRISE, 24.0)
	var up := SUNSET - SUNRISE
	return sin(PI * h / up) if h < up else -sin(PI * (h - up) / (24.0 - up))


func update(_force := false) -> void:
	var h := World.game_hour()
	var e := sun_height(h)
	var day := smoothstep(-0.2, 0.22, e)  # 0 at night, 1 in full day
	var glow := clampf(1.0 - absf(e) / 0.3, 0.0, 1.0)  # dawn and dusk
	# the sun rises in the east (+x) and sets in the west, low in the morning and evening
	sun.rotation_degrees = Vector3(-lerpf(4.0, 62.0, clampf(e, 0.0, 1.0)), lerpf(-110.0, 60.0, clampf((h - SUNRISE) / (SUNSET - SUNRISE), 0.0, 1.0)), 0.0)
	sun.light_energy = float(_day["sun"]) * day
	sun.light_color = Color.WHITE.lerp(DUSK_COLOR, glow * 0.8)
	sun.visible = day > 0.01
	sun.shadow_enabled = day > 0.3
	moon.light_energy = MOON_ENERGY * (1.0 - day)
	moon.visible = day < 0.99
	moon.shadow_enabled = day < 0.3
	sky_mat.sky_top_color = NIGHT_SKY_TOP.lerp(_day["top"], day)
	var horizon: Color = NIGHT_SKY_HORIZON.lerp(_day["horizon"], day)
	sky_mat.sky_horizon_color = horizon.lerp(DUSK_COLOR, glow * 0.55)
	sky_mat.ground_horizon_color = sky_mat.sky_horizon_color
	env.fog_light_color = NIGHT_FOG.lerp(_day["fog"], day).lerp(DUSK_COLOR.darkened(0.3), glow * 0.3)
	env.ambient_light_energy = lerpf(NIGHT_AMBIENT, float(_day["ambient"]), day)
	var lit := 1.0 - smoothstep(-0.12, 0.08, e)  # lamps come on in the dusk, before full dark
	for n in get_tree().get_nodes_in_group("night_lights"):  # every pass: guards and their torches come and go
		if not _same_zone(n):
			continue
		if n is Light3D:
			(n as Light3D).light_energy = float(n.get_meta("full_energy", 1.0)) * lit
			(n as Light3D).visible = lit > 0.01
		elif n is Node3D:
			(n as Node3D).visible = lit > 0.3


## Night lights belong to this zone's world (zones run side by side on a server).
func _same_zone(n: Node) -> bool:
	return get_parent().is_ancestor_of(n)
